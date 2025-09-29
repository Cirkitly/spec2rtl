# Prompt Engineering

The `prompts/` directory contains the core prompt templates used by the various AI agents in the system. Each subdirectory is dedicated to a specific agent or task.

## `code_generator/`

-   **`generate_rtl.md`**: The prompt template for the `RTLGeneratorNode`. It instructs the AI on how to generate Verilog RTL from a given specification.
-   **`generate_testbench.md`**: The prompt template for the `TestbenchGeneratorNode`. It guides the AI in creating a SystemVerilog testbench to verify the generated RTL.

## `critique/`

-   **`main_prompt.md`**: The prompt for the `CritiqueAgentNode`. This prompt asks the AI to act as a peer reviewer, checking the generated code for logical flaws, coverage gaps, and inconsistencies.

## `debug_and_refine/`

-   **`main_prompt.md`**: The prompt for the `DebugAndRefineNode`. This prompt is used when the validation or critique phase fails. It provides the AI with the original code, the error log or critique, and asks it to fix the issues.

## `planning/`

-   **`main_prompt.md`**: The prompt for the `PlanningAgentNode`. This prompt instructs the AI to create a high-level plan for the code generation process based on the user's specification.

## `rules/`

-   **`iverilog_compatibility.md`**: A set of rules and guidelines for generating `iverilog`-compatible SystemVerilog. This is injected into the `TestbenchGeneratorNode`'s prompt to improve the quality of the generated testbench.
