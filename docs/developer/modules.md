# Modules

This page provides a high-level overview of the key Python modules in the Spec2RTL project.

## `main.py`

This is the main entry point for the application. It is responsible for:

- Initializing the application.
- Kicking off the main execution flow (`spec2test_flow`).
- Handling the final output and user messages.

## `flow.py`

This module defines the core execution logic of the application using the `pocketflow` library. It constructs a directed acyclic graph (DAG) of nodes to represent the multi-agent workflow.

The flow is defined as follows:

1.  **Planning:**
    -   `KnowledgeIndexNode`: Indexes any provided knowledge files.
    -   `SpecSelectionNode`: Prompts the user to select a hardware specification.
    -   `KnowledgeRetrievalNode`: Retrieves relevant information from the knowledge base.
    -   `PlanningAgentNode`: Creates a high-level plan for code generation.
2.  **Generation:**
    -   `RTLGeneratorNode`: Generates the Verilog RTL code.
    -   `TestbenchGeneratorNode`: Generates the SystemVerilog testbench.
3.  **Validation & Refinement (Self-Correction Loop):**
    -   `ValidationNode`: Compiles and simulates the generated code using `iverilog`.
    -   `CritiqueAgentNode`: An AI agent reviews the code for issues.
    -   `DebugAndRefineNode`: If issues are found, another AI agent attempts to fix them.
4.  **Finalization:**
    -   `HumanApprovalNode`: Prompts the user to approve the generated code.
    -   `FileParserAndWriterNode`: Writes the approved code to files.
    -   `SimulationScriptGeneratorNode`: Generates a shell script to run the simulation.

## `nodes.py`

This module contains the implementation of all the nodes used in the `flow.py` module. Each node is a self-contained unit of work. The nodes are categorized by the phase of the workflow they belong to:

-   **Phase 1: Planning:** Nodes for indexing knowledge, selecting specs, retrieving knowledge, and planning.
-   **Phase 2: Generation:** Nodes for generating RTL and testbench code.
-   **Phase 3: Validation & Self-Critique:** Nodes for validating the code, having an AI critique it, and debugging any issues.
-   **Phase 4: Finalization:** Nodes for getting human approval and writing the final files.
