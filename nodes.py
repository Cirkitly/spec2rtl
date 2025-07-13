# spec2test/nodes.py

import os
import glob
import subprocess
import tempfile
import shutil
import numpy as np
import asyncio
from sklearn.metrics.pairwise import cosine_similarity
from pocketflow import Node, AsyncNode, BaseNode
from utils.call_llm import call_llm
from utils.get_embedding import get_embedding
from tui import (
    console, print_step, prompt_for_input, prompt_for_choice, 
    status, prompt_for_confirmation, print_plan, print_code, print_critique
)
import yaml

# --- Phase 1: Planning ---
class KnowledgeIndexNode(Node):
    def exec(self, _):
        knowledge_dir = 'knowledge_source'
        if not os.path.isdir(knowledge_dir):
            console.print("[warning]Knowledge source directory not found. Skipping RAG.[/warning]")
            return {"index": None, "chunks": []}
        files = glob.glob(os.path.join(knowledge_dir, '*.txt'))
        if not files:
            console.print("[warning]No knowledge files (.txt) found. Skipping RAG.[/warning]")
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
            prompt = f"""
            You are a lead verification engineer. Your task is to create a high-level plan for generating Verilog code and a testbench based on the provided specification and context.
            ### Specification ###\n{inputs['spec_content']}\n\n### Relevant Knowledge ###\n{inputs['knowledge']}
            ### Plan ###
            Create a list of high-level tasks to be completed. The valid tasks are: 'generate_rtl', 'generate_testbench'.
            Output ONLY a YAML list where each item is a dictionary with 'task' and 'description' keys.
            Correct YAML Example:\n```yaml\n- task: generate_rtl\n  description: "..."\n- task: generate_testbench\n  description: "..."\n```
            """
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

# --- Phase 2: Parallel Generation ---
class CodeGenerationAgentNode(AsyncNode):
    async def prep_async(self, shared):
        return {"task": self.params['task'], "spec_content": shared["target_spec_content"], "knowledge": shared["retrieved_knowledge"]}
    async def exec_async(self, inputs):
        task = inputs["task"]
        prompt_templates = {
            'generate_rtl': "Generate the synthesizable Verilog-2001 RTL code...",
            'generate_testbench': "Generate a complete SystemVerilog testbench..."
        }
        prompt_template = prompt_templates.get(task, f"Generate the content for the task: '{task}'...")
        prompt = prompt_template.format(**inputs)
        print_step(f"Executing async task: {task}...")
        loop = asyncio.get_running_loop()
        code = await loop.run_in_executor(None, call_llm, prompt, False, 4096)
        if "```" in code:
            code = code.split("```", 2)[1]
            if code.lstrip().startswith(('verilog', 'systemverilog')):
                code = code[code.find('\n'):].strip()
        return {task: code}
    async def post_async(self, shared, _, exec_res):
        return exec_res

# --- START OF FIX ---
# --- Phase 3: Validation & Self-Critique ---
class ValidationNode(Node):
    def prep(self, shared):
        return shared.get("generated_artifacts", {})

    def exec(self, artifacts):
        """Compiles the generated code using iverilog to check for syntax errors."""
        rtl_code = artifacts.get("generate_rtl")
        tb_code = artifacts.get("generate_testbench")

        if not rtl_code or not tb_code:
            return {"passed": False, "error_log": "RTL or Testbench code was not generated."}

        with tempfile.TemporaryDirectory() as temp_dir:
            rtl_path = os.path.join(temp_dir, "design.v")
            tb_path = os.path.join(temp_dir, "testbench.v")

            with open(rtl_path, "w") as f: f.write(rtl_code)
            with open(tb_path, "w") as f: f.write(tb_code)

            # Use iverilog to compile. -t null checks syntax without creating an output file.
            # -g2005-sv supports SystemVerilog constructs often used in testbenches.
            command = ["iverilog", "-t", "null", "-g2005-sv", rtl_path, tb_path]
            
            print_step(f"Validating generated code with command: `{' '.join(command)}`")
            
            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0:
                print_step("Code validation successful (no syntax errors found).")
                return {"passed": True, "error_log": None}
            else:
                error_log = result.stderr or result.stdout
                console.print(f"[warning]Code validation failed:[/warning]\n{error_log}")
                return {"passed": False, "error_log": error_log}

    def post(self, shared, _, exec_res):
        shared["validation_result"] = exec_res
        if exec_res["passed"]:
            return "success"
        else:
            shared["error_log"] = exec_res["error_log"]
            return "failure"
# --- END OF FIX ---


class CritiqueAgentNode(Node):
    def prep(self, shared): return shared["generated_artifacts"]
    def exec(self, artifacts):
        with status("AI is performing a self-critique..."):
            rtl_code = artifacts.get("generate_rtl", "N/A")
            tb_code = artifacts.get("generate_testbench", "N/A")
            prompt = f"You are a senior hardware verification reviewer... [review code] ... If high quality, respond with 'No issues found'."
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
        return {"spec": shared["target_spec_content"], "artifacts": shared["generated_artifacts"], "feedback": feedback}
    def exec(self, inputs):
        with status("Attempting to self-correct..."):
            prompt = f"""
            You are an expert Verilog engineer. Your previous code generation attempt failed with the following feedback.
            Your task is to regenerate ALL artifacts (RTL, Testbench, etc.) in a single YAML block, fully addressing the feedback.
            ### Original Specification ###\n{inputs['spec']}
            ### Feedback to Address ###\n{inputs['feedback']}
            ### Previous Faulty Code ###\n{yaml.dump(inputs['artifacts'], allow_unicode=True)}
            Now, provide the complete, corrected set of artifacts. CRITICAL: Your entire response must start with ```yaml and end with ```.
            Example of the required YAML format:\n```yaml\ngenerate_rtl: |\n  module ...\n  endmodule\ngenerate_testbench: |\n  module ...\n  endmodule\n```
            """
            response = call_llm(prompt, use_cache=False, max_tokens=8192)
        print_step("A new version of the code has been generated.")
        try:
            yaml_str = response.split("```yaml", 1)[1].rsplit("```", 1)[0]
            parsed_response = yaml.safe_load(yaml_str)
            if not isinstance(parsed_response, dict): raise yaml.YAMLError("LLM response was not a valid YAML mapping.")
            return parsed_response
        except (IndexError, yaml.YAMLError) as e:
            console.print(f"[danger]Error parsing refined YAML from LLM: {e}[/danger]")
            return inputs['artifacts']
    def post(self, shared, _, exec_res):
        shared["generated_artifacts"] = exec_res
        shared["debug_attempt_count"] = shared.get("debug_attempt_count", 0) + 1
        shared.pop("error_log", None); shared.pop("critique_feedback", None)
        if shared["debug_attempt_count"] >= 2:
            console.print("[danger]Max debug attempts reached. Proceeding to manual review.[/danger]")
            return "max_attempts_reached"
        return "default"

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
        script_content = f"#!/bin/bash\niverilog -o sim_output.vvp {rtl_file} {tb_file}\nvvp sim_output.vvp\n"
        script_path = os.path.join(output_dir, "run_sim.sh")
        with open(script_path, 'w', encoding='utf-8') as f: f.write(script_content)
        os.chmod(script_path, 0o755)
        return f"Simulation script generated at [path]{script_path}[/path]"
    def post(self, shared, _, exec_res): shared["simulation_script_status"] = exec_res