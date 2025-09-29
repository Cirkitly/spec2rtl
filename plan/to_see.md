### 1. New Directory Structure

First, here is the new directory structure for your project. The key additions are the `prompts/` directory and the `utils/prompt_loader.py` file.

```
spec2rtl/
│   ├── requirements.txt
│   ├── nodes.py                 # <-- Will be modified
│   ├── tui.py
│   ├── .env
│   ├── llm_cache.json
│   ├── flow.py
│   ├── main.py
│   ├── README.md
│   ├── .gitignore
│   ├── .env.example
│   ├── prompts/                 # <-- NEW FOLDER
│   │   ├── rules/
│   │   │   └── iverilog_compatibility.md
│   │   ├── planning/
│   │   │   └── main_prompt.md
│   │   ├── code_generator/
│   │   │   ├── generate_rtl.md
│   │   │   └── generate_testbench.md
│   │   ├── critique/
│   │   │   └── main_prompt.md
│   │   └── debug_and_refine/
│   │       └── main_prompt.md
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── call_llm.py
│   │   ├── get_embedding.py
│   │   ├── prompt_loader.py     # <-- NEW FILE
│   │   └── __pycache__/ [EXCLUDED]
... (rest of your folders)
```

---

### 2. New Utility File: `utils/prompt_loader.py`

Create this new file inside your `utils` directory. This utility will handle reading the prompt templates from the `prompts/` folder.

```python
# spec2rtl/utils/prompt_loader.py

import os

PROMPTS_DIR = "prompts"

def load_prompt(file_path: str) -> str:
    """
    Loads a prompt template from the prompts directory.
    The file_path is relative to the 'prompts/' directory.
    """
    full_path = os.path.join(PROMPTS_DIR, file_path)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Prompt template not found at: {full_path}")
    
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()
```

---

### 3. New Prompt Template Files

Create the `prompts` directory and the subdirectories as shown above. Then, create the following files with the specified content.

#### `prompts/rules/iverilog_compatibility.md`

```markdown
# Icarus Verilog (iverilog) Compatibility Rules

Here are critical rules for writing SystemVerilog that is compatible with the `iverilog` compiler.

1.  **`task` vs. `function` for Time Consumption:**
    *   A `function` must execute in zero time. It CANNOT contain time-consuming statements like delays (`#10`), event controls (`@(posedge clk)`), or `wait` statements. Use functions for immediate calculations.
    *   A `task` is used for procedures that consume time. Any procedure that needs to wait for a clock edge or has a delay MUST be a `task`.

2.  **`for` Loop Variable Declaration:**
    *   DO NOT declare loop variables inside the `for` loop declaration (e.g., `for (int i = 0; ...)`). This is not fully supported.
    *   You MUST declare the loop variable as an `integer` before the loop begins (e.g., `integer i; for (i = 0; ...)`).

3.  **VCD Dumping:**
    *   Use the standard `$dumpfile("filename.vcd");` and `$dumpvars(0, module_instance);` system tasks to create waveform dumps.
```

#### `prompts/planning/main_prompt.md`
```markdown
You are a lead verification engineer. Your task is to create a high-level plan for generating Verilog code and a testbench based on the provided specification and context.

### Specification ###
{spec_content}

### Relevant Knowledge ###
{knowledge}

### Plan ###
Create a list of high-level tasks to be completed. The valid tasks are: 'generate_rtl', 'generate_testbench'.
Output ONLY a YAML list where each item is a dictionary with 'task' and 'description' keys.

Correct YAML Example:
```yaml
- task: generate_rtl
  description: "Generate the synthesizable Verilog RTL for the module."
- task: generate_testbench
  description: "Create a SystemVerilog testbench to verify the RTL."
```
```

#### `prompts/code_generator/generate_rtl.md`
```markdown
You are an expert digital design engineer specializing in synthesizable Verilog-2001. Your task is to write the RTL code for the module described in the specification.

**CRITICAL INSTRUCTIONS:**
- The Verilog MUST be synthesizable and strictly follow the Verilog-2001 standard.
- Use non-blocking assignments (`<=`) for all sequential logic (inside `always @(posedge i_clk)`).
- Use an active-high synchronous reset.
- Do not use any `initial` blocks in the RTL module.
- Ensure the module has a parameter for `BAUD_RATE_DIVIDER` as specified.

### Original Specification ###
{spec_content}

### Relevant Knowledge (if any) ###
{knowledge}

Produce ONLY the Verilog code inside a single markdown code block.
```verilog
{placeholder}
```
```

#### `prompts/code_generator/generate_testbench.md`
```markdown
You are an expert verification engineer. Your task is to write a comprehensive SystemVerilog testbench.

**CRITICAL INSTRUCTIONS:**
- The testbench must be self-checking and print "PASS" or "FAIL" messages.
- You MUST follow all the `iverilog` compatibility rules provided.
- Create a clock generator and a VCD dump for waveform analysis.
- The test should cover key functional requirements and edge cases (e.g., reset, back-to-back operations).

### Original Specification ###
{spec_content}

### Verilog RTL to be Tested ###
```verilog
{rtl_code}
```

### Icarus Verilog (iverilog) Compatibility Rules ###
{iverilog_rules}

Based on all the information above, generate ONLY the SystemVerilog testbench code. Do not add any explanations. The output must be a single, complete SystemVerilog code block.
```systemverilog
{placeholder}
```
```

#### `prompts/critique/main_prompt.md`
```markdown
You are a meticulous Senior Hardware Verification Engineer. Your task is to review the provided Verilog RTL and SystemVerilog Testbench for quality, correctness, and adherence to best practices.

**Your review checklist:**
1.  **RTL Correctness:** Does the FSM have a default case to prevent latches? Are blocking (`=`) and non-blocking (`<=`) assignments used correctly? Is the reset logic synchronous and correct?
2.  **Testbench Quality:** Does the testbench check for the `o_busy` signal behavior correctly? Does it cover edge cases like back-to-back transmissions and resets? Are the `iverilog` compatibility rules followed?
3.  **Spec Adherence:** Does the generated code meet every functional requirement from the original specification? List any missing features.

**Review the following files:**

### Original Specification ###
{spec_content}

### Verilog RTL ###
```verilog
{rtl_code}
```

### SystemVerilog Testbench ###
```systemverilog
{testbench_code}
```

**Output your review:**
- If there are CRITICAL issues, describe them clearly and concisely.
- If the code is of high quality and meets all requirements, respond ONLY with the phrase "No issues found."
```

#### `prompts/debug_and_refine/main_prompt.md`
```markdown
You are an expert Verilog engineer. Your previous code generation attempt failed with the following feedback. Your task is to regenerate ALL artifacts (RTL, Testbench, etc.) in a single YAML block, fully addressing the feedback.

### Original Specification ###
{spec}

### Feedback to Address ###
{feedback}

### Previous Faulty Code ###
{artifacts}

Now, provide the complete, corrected set of artifacts. CRITICAL: Your entire response must start with ```yaml and end with ```.

Example of the required YAML format:
```yaml
generate_rtl: |
  module ...
  endmodule
generate_testbench: |
  module ...
  endmodule
```
```

---

### 4. Updated `nodes.py` File

This is the main change. Replace the entire content of `nodes.py` with the following refactored code. It now uses the `prompt_loader` utility, making the node logic much cleaner.

```python
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
from utils.prompt_loader import load_prompt  # <-- NEW IMPORT
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

# --- Phase 2: Parallel Generation ---
class CodeGenerationAgentNode(AsyncNode):
    async def prep_async(self, shared):
        task_type = self.params['task']
        prep_data = {
            "task": task_type,
            "spec_content": shared["target_spec_content"],
            "knowledge": shared.get("retrieved_knowledge", "None"),
            "rtl_code": shared.get("generated_artifacts", {}).get("generate_rtl", "RTL not yet generated."),
            "placeholder": "" # For prompts that need an empty placeholder
        }
        return prep_data
    
    async def exec_async(self, inputs):
        task = inputs["task"]
        prompt_file_map = {
            'generate_rtl': 'code_generator/generate_rtl.md',
            'generate_testbench': 'code_generator/generate_testbench.md'
        }
        
        prompt_template = load_prompt(prompt_file_map.get(task, ""))
        if not prompt_template:
            raise ValueError(f"No prompt template found for task: {task}")
            
        # For testbench, we also need to load the iverilog rules
        if task == 'generate_testbench':
            inputs['iverilog_rules'] = load_prompt('rules/iverilog_compatibility.md')
            # Ensure RTL is available for the testbench prompt
            if inputs['rtl_code'] == "RTL not yet generated.":
                 # This is a fallback, ideally the flow ensures RTL is generated first
                 # or that testbench generation depends on it.
                 # For now, we'll try to find it in the shared state if another parallel task finished.
                 # A more robust solution would involve explicit dependencies in the flow.
                 pass

        final_prompt = prompt_template.format(**inputs)

        print_step(f"Executing async task: {task}...")
        loop = asyncio.get_running_loop()
        code = await loop.run_in_executor(None, call_llm, final_prompt, False, 4096)
        
        if "```" in code:
            code = code.split("```", 2)[1]
            if code.lstrip().startswith(('verilog', 'systemverilog')):
                code = code[code.find('\n'):].strip()
        
        return {task: code}

    async def post_async(self, shared, _, exec_res):
        # This post method now runs for each parallel task.
        # We need a way to merge results. We will do this in the parallel flow's post method.
        # So we just return the result to be collected.
        return exec_res

# --- Phase 3: Validation & Self-Critique ---
class ValidationNode(Node):
    def prep(self, shared):
        return shared.get("generated_artifacts", {})

    def exec(self, artifacts):
        rtl_code = artifacts.get("generate_rtl")
        tb_code = artifacts.get("generate_testbench")

        if not rtl_code or not tb_code:
            return {"passed": False, "error_log": "RTL or Testbench code was not generated."}

        with tempfile.TemporaryDirectory() as temp_dir:
            rtl_path = os.path.join(temp_dir, "design.v")
            tb_path = os.path.join(temp_dir, "testbench.v")

            with open(rtl_path, "w") as f: f.write(rtl_code)
            with open(tb_path, "w") as f: f.write(tb_code)
            
            command = ["iverilog", "-t", "null", "-g2005-sv", rtl_path, tb_path]
            print_step(f"Validating generated code with command: `{' '.join(command)}`")
            result = subprocess.run(command, capture_output=True, text=True, check=False)

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
        
        script_content = f"#!/bin/bash\niverilog -o sim_output.vvp {rtl_file} {tb_file}\nvvp sim_output.vvp\n"
        script_path = os.path.join(output_dir, "run_sim.sh")
        
        with open(script_path, 'w', encoding='utf-8') as f: f.write(script_content)
        os.chmod(script_path, 0o755)
        
        return f"Simulation script generated at [path]{script_path}[/path]"
        
    def post(self, shared, _, exec_res): shared["simulation_script_status"] = exec_res
```

---

### Summary of Changes and Next Steps

1.  **Prompts are Externalized:** All major prompts have been moved from Python f-strings into markdown files inside the new `prompts/` directory.
2.  **Cleaner Node Logic:** The `exec` methods in your nodes are now much shorter and more readable. They focus on loading a template and formatting it with data, not on defining the prompt text itself.
3.  **Modular & Reusable Prompts:** The `iverilog` compatibility rules are now in their own file and are dynamically loaded into the testbench generation prompt, demonstrating modularity.
4.  **No Other Changes Needed:** Your other files (`main.py`, `flow.py`, `tui.py`, etc.) do not need any changes, as this refactoring was contained to the `nodes.py` logic.

You can now easily experiment with and improve your AI's behavior by simply editing the text files in the `prompts/` directory. This is a huge step forward for the maintainability and power of your project
