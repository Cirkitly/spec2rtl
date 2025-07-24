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
