# Knowledge Source

The `knowledge_source/` directory provides a way to inject domain-specific knowledge into the AI's code generation process. This is a form of Retrieval-Augmented Generation (RAG).

## How it Works

Before the planning phase, the `KnowledgeIndexNode` reads all the `.txt` and `.md` files in the `knowledge_source/` directory. It then generates embeddings for each file, creating a searchable vector index.

When the user selects a specification, the `KnowledgeRetrievalNode` compares the specification to the indexed knowledge and retrieves the most relevant document. This document is then passed to the planning and code generation agents.

## How to Add New Knowledge

To add new knowledge, simply create a new `.txt` or `.md` file in the `knowledge_source/` directory. The file should contain information that you want the AI to consider when generating code. This could include:

-   **Coding standards:** A document outlining the coding style and conventions for the project.
-   **Simulator-specific rules:** Information about the quirks or limitations of a particular simulator.
-   **Project-specific information:** Details about the project's architecture or common modules.
-   **Examples:** Snippets of code that the AI can use as a reference.
