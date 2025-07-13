# spec2test/flow.py

import asyncio
from pocketflow import AsyncFlow, AsyncParallelBatchFlow
from nodes import (
    KnowledgeIndexNode,
    SpecSelectionNode,
    KnowledgeRetrievalNode,
    PlanningAgentNode,
    CodeGenerationAgentNode,
    ValidationNode,
    DebugAndRefineNode,
    CritiqueAgentNode,
    HumanApprovalNode,
    FileParserAndWriterNode,
    SimulationScriptGeneratorNode
)

# --- START OF FIX ---
# The sub-flow must be async to match its async start node.
generation_agent_node = CodeGenerationAgentNode()
generation_sub_flow = AsyncFlow(start=generation_agent_node)
# --- END OF FIX ---

class GenerationParallelFlow(AsyncParallelBatchFlow):
    """
    This flow now correctly inherits from AsyncParallelBatchFlow and relies on its
    base implementation to gather results from the async sub-flow.
    """
    async def prep_async(self, shared):
        return shared.get("execution_plan", [])

    async def post_async(self, shared, _, exec_res_list):
        # The exec_res_list now correctly contains the dictionaries from each parallel run.
        artifacts = {}
        for res_dict in exec_res_list:
            if isinstance(res_dict, dict):
                artifacts.update(res_dict)
        shared["generated_artifacts"] = artifacts
        return None

def create_spec2test_flow():
    indexer = KnowledgeIndexNode()
    selector = SpecSelectionNode()
    retriever = KnowledgeRetrievalNode()
    planner = PlanningAgentNode()
    # The parallel generator now starts the ASYNC sub-flow
    parallel_generator = GenerationParallelFlow(start=generation_sub_flow)
    validator = ValidationNode()
    critiquer = CritiqueAgentNode()
    debugger = DebugAndRefineNode()
    approver = HumanApprovalNode()
    writer = FileParserAndWriterNode()
    script_gen = SimulationScriptGeneratorNode()

    # The connections remain the same, but the underlying execution is now correct.
    (indexer >> selector >> retriever >> planner)
    planner >> parallel_generator
    parallel_generator >> validator
    
    validator - "success" >> critiquer
    validator - "failure" >> debugger
    
    critiquer - "success" >> approver
    critiquer - "failure" >> debugger
    
    debugger >> validator
    debugger - "max_attempts_reached" >> approver
    
    (approver >> writer >> script_gen)

    return AsyncFlow(start=indexer)

spec2test_flow = create_spec2test_flow()