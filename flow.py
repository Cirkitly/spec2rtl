# spec2test/flow.py

from pocketflow import AsyncFlow
from nodes import (
    KnowledgeIndexNode,
    SpecSelectionNode,
    KnowledgeRetrievalNode,
    PlanningAgentNode,
    RTLGeneratorNode,
    TestbenchGeneratorNode,
    ValidationNode,
    DebugAndRefineNode,
    CritiqueAgentNode,
    HumanApprovalNode,
    FileParserAndWriterNode,
    SimulationScriptGeneratorNode
)

def create_spec2test_flow():
    # Phase 1: Planning
    indexer = KnowledgeIndexNode()
    selector = SpecSelectionNode()
    retriever = KnowledgeRetrievalNode()
    planner = PlanningAgentNode()

    # Phase 2: Sequential Generation
    rtl_generator = RTLGeneratorNode()
    tb_generator = TestbenchGeneratorNode()

    # Phase 3: Validation & Refinement
    validator = ValidationNode()
    critiquer = CritiqueAgentNode()
    debugger = DebugAndRefineNode()

    # Phase 4: Finalization
    approver = HumanApprovalNode()
    writer = FileParserAndWriterNode()
    script_gen = SimulationScriptGeneratorNode()

    # Define the flow graph:
    # Planning -> RTL Gen -> TB Gen -> Validation Loop -> Approval -> File Write
    (
        indexer >> selector >> retriever >> planner >>
        rtl_generator >> tb_generator >> validator
    )
    
    # Validation and self-correction loop
    validator - "success" >> critiquer
    validator - "failure" >> debugger
    
    critiquer - "success" >> approver
    critiquer - "failure" >> debugger
    
    debugger >> validator # Loop back to validation
    debugger - "max_attempts_reached" >> approver
    
    # Finalization
    (approver >> writer >> script_gen)

    # The entire flow is asynchronous because it contains async nodes
    return AsyncFlow(start=indexer)

spec2test_flow = create_spec2test_flow()