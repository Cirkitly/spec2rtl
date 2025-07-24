# spec2test/nodes.py

import os
import glob
import subprocess
import tempfile
import shutil
import numpy as np
import asyncio
import yaml
from sklearn.metrics.pairwise import cosine_similarity
from pocketflow import Node, AsyncNode, BaseNode
from utils.call_llm import call_llm
from utils.get_embedding import get_embedding
from utils.prompt_loader import load_prompt
from tui import (
    console, print_step, prompt_for_input, prompt_for_choice, 
    status, prompt_for_confirmation, print_plan, print_code, print_critique
)

# --- Phase 1: Planning ---
class KnowledgeIndexNode(Node):
    def exec(self, _):
        knowledge_dir = 'knowledge_source'
        if not os.path.isdir(knowledge_dir):
            console.print("[warning]Knowledge source directory not found. Skipping RAG.[/warning]")
            return {"index": None, "chunks": []}
        files = glob.glob(os.path.join(knowledge_dir, '*.txt')) + glob.glob(os.path.join(knowledge_dir, '*.md'))
        if not files:
            console.print("[warning]No knowledge files (.txt, .md) found. Skipping RAG.[/warning]")
            return {"index": None, "chunks": []}
        print_step(f"Indexing {len(files)} knowledge source file(s)...")
        chunks = [open(f, 'r', encoding='utf-8').read() for f in files]
        with status("Generating embeddings for knowledge base..."):
            embeddings = [get_embedding(chunk) for chunk in chunks]
        return {"index": np.array(embeddings), "chunks": chunks}

    def post(self, shared, _, exec_res):
        shared["knowledge_index"] = exec_res["index"]
        shared["knowledge_chunks"] = exec_res["chunks"]

class SpecSelectionNode(Node):
    def exec(self, _):
        spec_dir = 'specs'
        if not os.path.isdir(spec_dir): raise NotADirectoryError(f"Specification directory not found: '{spec_dir}'")
        spec_files = glob.glob(os.path.join(spec_dir, '*.md'))
        if not spec_files: raise FileNotFoundError("No specification files (.md) found in 'specs/' directory.")
        print_step("Found the following specifications:")
        for i, spec in enumerate(spec_files):
            console.print(f"  [prompt][{i+1}][/prompt] [path]{os.path.basename(spec)}[/path]")
        choice = prompt_for_choice("Which spec would you like to generate tests for?", spec_files)
        selected_spec_path = spec_files[choice - 1]
        with open(selected_spec_path, 'r', encoding='utf-8') as f: content = f.read()
        return {"name": os.path.basename(selected_spec_path), "content": content}
    
    def post(self, shared, _, exec_res):
        shared["target_spec_name"] = exec_res["name"]
        shared["target_spec_content"] = exec_res["content"]

class KnowledgeRetrievalNode(Node):
    def prep(self, shared):
        if shared.get("knowledge_index") is None or len(shared.get("knowledge_chunks", [])) == 0: return None
        return {"spec_content": shared["target_spec_content"], "knowledge_index": shared["knowledge_index"], "knowledge_chunks": shared["knowledge_chunks"]}
    def exec(self, inputs):
        if inputs is None: return "No relevant knowledge found."
        spec_content, knowledge_index, knowledge_chunks = inputs.values()
        print_step("Searching knowledge base for relevant context...")
        query_embedding = get_embedding(spec_content)
        similarities = cosine_similarity([query_embedding], knowledge_index)[0]
        top_idx = np.argmax(similarities)
        if similarities[top_idx] > 0.3: return knowledge_chunks[top_idx]
        return "No relevant knowledge found."
    def post(self, shared, _, exec_res):
        shared["retrieved_knowledge"] = exec_res

class PlanningAgentNode(Node):
    def prep(self, shared):
        return {"spec_content": shared["target_spec_content"], "knowledge": shared.get("retrieved_knowledge", "None")}
    def exec(self, inputs):
        with status("Creating a high-level plan..."):
            prompt_template = load_prompt('planning/main_prompt.md')
            prompt = prompt_template.format(**inputs)
            response = call_llm(prompt, use_cache=False)
            try:
                plan = yaml.safe_load(response)
                if not (isinstance(plan, list) and all(isinstance(item, dict) and 'task' in item for item in plan)):
                    raise yaml.YAMLError("Parsed YAML is not a list of task dictionaries.")
            except (yaml.YAMLError, IndexError, AttributeError):
                console.print("[warning]LLM did not return the expected plan structure. Defaulting to standard plan.[/warning]")
                plan = [
                    {'task': 'generate_rtl', 'description': 'Generate the synthesizable Verilog RTL for the module.'},
                    {'task': 'generate_testbench', 'description': 'Create a SystemVerilog testbench to verify the RTL.'}
                ]
        print_step("High-level plan created."); print_plan(yaml.dump(plan, allow_unicode=True))
        return plan
    def post(self, shared, _, exec_res):
        shared["execution_plan"] = exec_res

# --- Phase 2: Sequential Generation ---
class RTLGeneratorNode(AsyncNode):
    async def prep_async(self, shared):
        return {
            "spec_content": shared["target_spec_content"],
            "knowledge": shared.get("retrieved_knowledge", "None"),
            "placeholder": ""
        }
    
    async def exec_async(self, inputs):
        print_step("Generating Verilog RTL...")
        prompt_template = load_prompt('code_generator/generate_rtl.md')
        final_prompt = prompt_template.format(**inputs)
        
        loop = asyncio.get_running_loop()
        code = await loop.run_in_executor(None, call_llm, final_prompt, False, 4096)
        
        if "```" in code:
            code = code.split("```", 2)[1]
            if code.lstrip().startswith(('verilog', 'systemverilog')):
                code = code[code.find('\n'):].strip()
        
        return code

    async def post_async(self, shared, _, exec_res):
        shared["generated_artifacts"] = {"generate_rtl": exec_res}

class TestbenchGeneratorNode(AsyncNode):
    async def prep_async(self, shared):
        return {
            "spec_content": shared["target_spec_content"],
            "iverilog_rules": load_prompt('rules/iverilog_compatibility.md'),
            "rtl_code": shared.get("generated_artifacts", {}).get("generate_rtl", "RTL not yet generated."),
            "placeholder": ""
        }
    
    async def exec_async(self, inputs):
        if inputs['rtl_code'] == "RTL not yet generated.":
            console.print("[danger]Cannot generate testbench: RTL code is missing.[/danger]")
            return "# ERROR: RTL code was not provided to testbench generator."

        print_step("Generating SystemVerilog Testbench...")
        prompt_template = load_prompt('code_generator/generate_testbench.md')
        final_prompt = prompt_template.format(**inputs)

        loop = asyncio.get_running_loop()
        code = await loop.run_in_executor(None, call_llm, final_prompt, False, 4096)
        
        if "```" in code:
            code = code.split("```", 2)[1]
            if code.lstrip().startswith(('verilog', 'systemverilog')):
                code = code[code.find('\n'):].strip()
        
        return code

    async def post_async(self, shared, _, exec_res):
        shared["generated_artifacts"]["generate_testbench"] = exec_res


# --- Phase 3: Validation & Self-Critique ---
class ValidationNode(Node):
    def prep(self, shared):
        return shared.get("generated_artifacts", {})

    def exec(self, artifacts):
        rtl_code = artifacts.get("generate_rtl")
        tb_code = artifacts.get("generate_testbench")

        if not rtl_code or not tb_code:
            return {"passed": False, "error_log": "RTL or Testbench code was not generated."}

        # Use a temporary directory to avoid cluttering the project
        with tempfile.TemporaryDirectory() as temp_dir:
            rtl_path = os.path.join(temp_dir, "design.v")
            tb_path = os.path.join(temp_dir, "testbench.v")
            sim_output_path = os.path.join(temp_dir, "sim.vvp")

            with open(rtl_path, "w", encoding='utf-8') as f: f.write(rtl_code)
            with open(tb_path, "w", encoding='utf-8') as f: f.write(tb_code)
            
            # 1. Compile the code
            compile_cmd = ["iverilog", "-o", sim_output_path, "-g2005-sv", rtl_path, tb_path]
            print_step(f"Validating (compiling) generated code: `{' '.join(compile_cmd)}`")
            compile_result = subprocess.run(compile_cmd, capture_output=True, text=True, check=False)

            if compile_result.returncode != 0:
                error_log = compile_result.stderr or compile_result.stdout
                console.print(f"[warning]Code compilation failed:[/warning]\n{error_log}")
                return {"passed": False, "error_log": error_log}

            # 2. Run the simulation
            sim_cmd = ["vvp", sim_output_path]
            print_step(f"Validating (running simulation): `{' '.join(sim_cmd)}`")
            try:
                # Use a timeout to prevent hangs
                sim_result = subprocess.run(sim_cmd, capture_output=True, text=True, check=False, timeout=15)
            except subprocess.TimeoutExpired as e:
                error_log = f"Simulation timed out after 15 seconds. This likely indicates an infinite loop in the testbench.\n\nCaptured output:\n{e.stdout}"
                console.print(f"[danger]Simulation timed out.[/danger]\n{error_log}")
                return {"passed": False, "error_log": error_log}

            # 3. Check for runtime errors in the simulation output
            sim_output = sim_result.stdout
            # Use lowercase for robust matching of failure keywords
            if "error" in sim_output.lower() or "fail" in sim_output.lower():
                console.print(f"[warning]Simulation ran but test failed:[/warning]\n{sim_output}")
                # The whole simulation log is valuable feedback for the debug agent
                return {"passed": False, "error_log": sim_output}

            print_step("Simulation validation successful (compiled and ran without errors).")
            return {"passed": True, "error_log": None}

    def post(self, shared, _, exec_res):
        shared["validation_result"] = exec_res
        if exec_res["passed"]:
            return "success"
        else:
            shared["error_log"] = exec_res["error_log"]
            return "failure"

class CritiqueAgentNode(Node):
    def prep(self, shared):
        return {
            "artifacts": shared.get("generated_artifacts", {}),
            "spec_content": shared.get("target_spec_content", "")
        }
        
    def exec(self, inputs):
        with status("AI is performing a self-critique..."):
            prompt_template = load_prompt('critique/main_prompt.md')
            prompt = prompt_template.format(
                spec_content=inputs['spec_content'],
                rtl_code=inputs['artifacts'].get("generate_rtl", "N/A"),
                testbench_code=inputs['artifacts'].get("generate_testbench", "N/A")
            )
            critique = call_llm(prompt, use_cache=False)
            
        if "no issues found" in critique.lower():
            print_step("AI self-critique found no major issues.")
            return None
        else:
            print_step("AI self-critique found issues to address."); print_critique(critique)
            return critique
            
    def post(self, shared, _, exec_res):
        if exec_res is None: return "success"
        shared["critique_feedback"] = exec_res
        return "failure"

class DebugAndRefineNode(Node):
    def prep(self, shared):
        feedback = shared.get("error_log") or shared.get("critique_feedback")
        return {
            "spec": shared["target_spec_content"], 
            "artifacts": yaml.dump(shared["generated_artifacts"], allow_unicode=True), 
            "feedback": feedback
        }
        
    def exec(self, inputs):
        with status("Attempting to self-correct..."):
            prompt_template = load_prompt('debug_and_refine/main_prompt.md')
            prompt = prompt_template.format(**inputs)
            response = call_llm(prompt, use_cache=False, max_tokens=8192)
            
        print_step("A new version of the code has been generated.")
        try:
            yaml_str = response.split("```yaml", 1)[1].rsplit("```", 1)[0]
            parsed_response = yaml.safe_load(yaml_str)
            if not isinstance(parsed_response, dict): raise yaml.YAMLError("LLM response was not a valid YAML mapping.")
            return parsed_response
        except (IndexError, yaml.YAMLError) as e:
            console.print(f"[danger]Error parsing refined YAML from LLM: {e}[/danger]")
            return yaml.safe_load(inputs['artifacts'])
            
    def post(self, shared, _, exec_res):
        shared["generated_artifacts"] = exec_res
        shared["debug_attempt_count"] = shared.get("debug_attempt_count", 0) + 1
        shared.pop("error_log", None); shared.pop("critique_feedback", None)
        if shared["debug_attempt_count"] >= 2:
            console.print("[danger]Max debug attempts reached. Proceeding to manual review.[/danger]")
            return "max_attempts_reached"
        return "default"

# --- Phase 4: Finalization ---
class HumanApprovalNode(Node):
    def prep(self, shared): return shared.get("generated_artifacts", {})
    
    def exec(self, artifacts):
        console.print()
        print_step("Generated artifacts are ready for your review:")
        rtl_code = artifacts.get("generate_rtl", "Not generated.")
        tb_code = artifacts.get("generate_testbench", "Not generated.")
        print_code(rtl_code, "verilog", "Verilog RTL"); print_code(tb_code, "systemverilog", "SystemVerilog Testbench")
        
        if not prompt_for_confirmation("Does this code look correct? Shall I write the files?"):
            print_step("Aborting based on user input. No files will be written.")
            self.flow_control.stop_flow = True
            
    def post(self, shared, _, __): pass

class FileParserAndWriterNode(Node):
    def prep(self, shared):
        spec_name_base = os.path.splitext(shared["target_spec_name"])[0]
        output_dir = os.path.join("output", spec_name_base)
        os.makedirs(output_dir, exist_ok=True)
        files_to_write = []
        artifacts = shared.get("generated_artifacts", {})
        if rtl_code := artifacts.get("generate_rtl"): files_to_write.append({"path": os.path.join(output_dir, f"{spec_name_base}.v"), "content": rtl_code})
        if tb_code := artifacts.get("generate_testbench"): files_to_write.append({"path": os.path.join(output_dir, f"{spec_name_base}_tb.v"), "content": tb_code})
        return files_to_write
        
    def exec(self, files_to_write):
        written_paths = []
        for file_info in files_to_write:
            with open(file_info["path"], 'w', encoding='utf-8') as f: f.write(file_info["content"])
            written_paths.append(file_info["path"])
        return written_paths
        
    def post(self, shared, _, exec_res):
        shared["output_file_paths"] = exec_res
        for path in exec_res: print_step(f"File written to [path]{path}[/path]")

class SimulationScriptGeneratorNode(Node):
    def prep(self, shared): return shared.get("output_file_paths", [])
    
    def exec(self, file_paths):
        if not file_paths: return "No files were written, skipping simulation script."
        output_dir = os.path.dirname(file_paths[0])
        rtl_file = os.path.basename(next((p for p in file_paths if not p.endswith("_tb.v")), None))
        tb_file = os.path.basename(next((p for p in file_paths if p.endswith("_tb.v")), None))
        if not rtl_file or not tb_file: return "Could not identify RTL and Testbench files."
        
        # Add the -g2005-sv flag to enable SystemVerilog features during compilation.
        script_content = f"#!/bin/bash\niverilog -o sim_output.vvp -g2005-sv {rtl_file} {tb_file}\nvvp sim_output.vvp\n"
        script_path = os.path.join(output_dir, "run_sim.sh")
        
        with open(script_path, 'w', encoding='utf-8') as f: f.write(script_content)
        os.chmod(script_path, 0o755)
        
        return f"Simulation script generated at [path]{script_path}[/path]"
        
    def post(self, shared, _, exec_res): shared["simulation_script_status"] = exec_res