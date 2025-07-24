import pytest
import asyncio
import numpy as np
import yaml
from unittest.mock import MagicMock, mock_open, patch, ANY

from nodes import (
    KnowledgeIndexNode, SpecSelectionNode, KnowledgeRetrievalNode, PlanningAgentNode,
    RTLGeneratorNode, TestbenchGeneratorNode, ValidationNode, CritiqueAgentNode, 
    DebugAndRefineNode, HumanApprovalNode, FileParserAndWriterNode, 
    SimulationScriptGeneratorNode
)

# --- Reusable Test Data ---
DUMMY_RTL_CODE = "module rtl_design; /* RTL code */ endmodule"
DUMMY_TB_CODE = "module tb_design; /* Testbench code */ endmodule"
DUMMY_SPEC_CONTENT = "This is a detailed specification for a hardware module."
DUMMY_ARTIFACTS = {"generate_rtl": DUMMY_RTL_CODE, "generate_testbench": DUMMY_TB_CODE}

# Force pytest-anyio to only use the 'asyncio' backend for this file.
@pytest.fixture
def anyio_backend():
    return 'asyncio'


# --- Test KnowledgeIndexNode ---
class TestKnowledgeIndexNode:
    @patch("nodes.os.path.isdir", return_value=True)
    @patch("nodes.glob.glob", return_value=["knowledge_source/doc1.txt"])
    @patch("nodes.get_embedding", return_value=np.array([0.1, 0.2, 0.3]))
    def test_exec_success(self, mock_get_embedding, mock_glob, mock_isdir, mocker):
        mocker.patch("nodes.print_step")
        mocker.patch("nodes.status")
        m = mock_open(read_data="some knowledge content")
        with patch("builtins.open", m):
            result = KnowledgeIndexNode().exec(None)
        assert "index" in result and "chunks" in result

    @patch("nodes.os.path.isdir", return_value=False)
    def test_exec_dir_not_found(self, mock_isdir, mocker):
        mocker.patch("nodes.console.print")
        result = KnowledgeIndexNode().exec(None)
        assert result == {"index": None, "chunks": []}

    def test_post(self):
        shared = {}
        exec_res = {"index": np.array([1]), "chunks": ["chunk1"]}
        KnowledgeIndexNode().post(shared, None, exec_res)
        assert np.array_equal(shared["knowledge_index"], exec_res["index"])
        assert shared["knowledge_chunks"] == exec_res["chunks"]


# --- Test SpecSelectionNode ---
class TestSpecSelectionNode:
    @patch("nodes.os.path.isdir", return_value=True)
    @patch("nodes.glob.glob", return_value=["specs/test_spec.md"])
    @patch("nodes.prompt_for_choice", return_value=1)
    def test_exec_success(self, mock_prompt, mock_glob, mock_isdir, mocker):
        mocker.patch("nodes.console.print")
        mocker.patch("nodes.print_step")
        m = mock_open(read_data=DUMMY_SPEC_CONTENT)
        with patch("builtins.open", m):
            result = SpecSelectionNode().exec(None)
        assert result["name"] == "test_spec.md"
        assert result["content"] == DUMMY_SPEC_CONTENT

    @patch("nodes.os.path.isdir", return_value=False)
    def test_exec_dir_not_found(self, mock_isdir):
        with pytest.raises(NotADirectoryError):
            SpecSelectionNode().exec(None)

    def test_post(self):
        shared = {}
        exec_res = {"name": "spec.md", "content": "spec content"}
        SpecSelectionNode().post(shared, None, exec_res)
        assert shared["target_spec_name"] == "spec.md"


# --- Test KnowledgeRetrievalNode ---
class TestKnowledgeRetrievalNode:
    def test_prep_with_knowledge(self):
        shared = {"knowledge_index": np.array([[1,2]]), "knowledge_chunks": ["c1"], "target_spec_content": "s"}
        assert KnowledgeRetrievalNode().prep(shared) is not None

    def test_prep_without_knowledge(self):
        assert KnowledgeRetrievalNode().prep({"target_spec_content": "s"}) is None

    @patch("nodes.get_embedding", return_value=np.array([1, 1]))
    @patch("nodes.cosine_similarity", return_value=np.array([[0.9, 0.1]]))
    def test_exec_finds_match(self, mock_sim, mock_embed, mocker):
        mocker.patch("nodes.print_step")
        inputs = {"spec_content":"s", "knowledge_index":np.array([[1,1],[0,0]]), "knowledge_chunks":["a","b"]}
        assert KnowledgeRetrievalNode().exec(inputs) == "a"


# --- Test PlanningAgentNode ---
class TestPlanningAgentNode:
    @patch("nodes.call_llm")
    def test_exec_success(self, mock_call_llm, mocker):
        mocker.patch("nodes.print_plan"); mocker.patch("nodes.print_step"); mocker.patch("nodes.status")
        mock_call_llm.return_value = "- task: a\n  description: 'b'"
        result = PlanningAgentNode().exec({"spec_content": "s", "knowledge": "k"})
        assert result == [{"task": "a", "description": "b"}]

    @patch("nodes.call_llm")
    def test_exec_bad_yaml_fallback(self, mock_call_llm, mocker):
        mocker.patch("nodes.console.print"); mocker.patch("nodes.print_plan"); mocker.patch("nodes.print_step"); mocker.patch("nodes.status")
        mock_call_llm.return_value = "not yaml"
        result = PlanningAgentNode().exec({"spec_content": "s", "knowledge": "k"})
        assert result[0]['task'] == 'generate_rtl'

# --- START: NEW TESTS FOR REFACTORED NODES ---
@pytest.mark.anyio
class TestRTLGeneratorNode:
    async def test_prep_async(self):
        node = RTLGeneratorNode()
        shared = {"target_spec_content": "spec", "retrieved_knowledge": "knowledge"}
        result = await node.prep_async(shared)
        assert result["spec_content"] == "spec"
        assert result["knowledge"] == "knowledge"

    @patch("nodes.call_llm", return_value=f"```verilog\n{DUMMY_RTL_CODE}\n```")
    async def test_exec_async(self, mock_call_llm, mocker):
        mocker.patch("nodes.print_step")
        mocker.patch("asyncio.get_running_loop", return_value=asyncio.get_running_loop())
        node = RTLGeneratorNode()
        result = await node.exec_async({})
        mock_call_llm.assert_called_once()
        assert result == DUMMY_RTL_CODE

    async def test_post_async(self):
        node = RTLGeneratorNode()
        shared = {}
        await node.post_async(shared, None, DUMMY_RTL_CODE)
        assert shared["generated_artifacts"] == {"generate_rtl": DUMMY_RTL_CODE}


@pytest.mark.anyio
class TestTestbenchGeneratorNode:
    @patch("nodes.load_prompt", return_value="iverilog rules")
    async def test_prep_async(self, mock_load_prompt):
        node = TestbenchGeneratorNode()
        shared = {
            "target_spec_content": "spec",
            "generated_artifacts": {"generate_rtl": DUMMY_RTL_CODE}
        }
        result = await node.prep_async(shared)
        assert result["spec_content"] == "spec"
        assert result["rtl_code"] == DUMMY_RTL_CODE
        assert result["iverilog_rules"] == "iverilog rules"
        mock_load_prompt.assert_called_once_with('rules/iverilog_compatibility.md')

    @patch("nodes.call_llm", return_value=f"```systemverilog\n{DUMMY_TB_CODE}\n```")
    async def test_exec_async(self, mock_call_llm, mocker):
        mocker.patch("nodes.print_step")
        mocker.patch("asyncio.get_running_loop", return_value=asyncio.get_running_loop())
        node = TestbenchGeneratorNode()
        result = await node.exec_async({'rtl_code': DUMMY_RTL_CODE})
        mock_call_llm.assert_called_once()
        assert result == DUMMY_TB_CODE

    async def test_post_async(self):
        node = TestbenchGeneratorNode()
        shared = {"generated_artifacts": {"generate_rtl": DUMMY_RTL_CODE}}
        await node.post_async(shared, None, DUMMY_TB_CODE)
        assert shared["generated_artifacts"] == {
            "generate_rtl": DUMMY_RTL_CODE,
            "generate_testbench": DUMMY_TB_CODE
        }
# --- END: NEW TESTS ---


# --- Test ValidationNode ---
class TestValidationNode:
    @patch("nodes.subprocess.run")
    def test_exec_success(self, mock_run, mocker):
        mocker.patch("nodes.print_step")
        # Simulate both compile and run succeeding
        mock_run.side_effect = [
            MagicMock(returncode=0, stderr="", stdout=""), # compile ok
            MagicMock(returncode=0, stderr="", stdout="PASS: All tests finished.") # run ok
        ]
        result = ValidationNode().exec(DUMMY_ARTIFACTS)
        assert mock_run.call_count == 2
        assert result == {"passed": True, "error_log": None}

    @patch("nodes.subprocess.run")
    def test_exec_compile_failure(self, mock_run, mocker):
        mocker.patch("nodes.console.print"); mocker.patch("nodes.print_step")
        mock_run.return_value = MagicMock(returncode=1, stderr="Syntax Error", stdout="")
        result = ValidationNode().exec(DUMMY_ARTIFACTS)
        assert mock_run.call_count == 1
        assert result == {"passed": False, "error_log": "Syntax Error"}

    @patch("nodes.subprocess.run")
    def test_exec_sim_failure(self, mock_run, mocker):
        mocker.patch("nodes.console.print"); mocker.patch("nodes.print_step")
        mock_run.side_effect = [
            MagicMock(returncode=0, stderr="", stdout=""), # compile ok
            MagicMock(returncode=0, stderr="", stdout="FAIL: Test case 1") # run fail
        ]
        result = ValidationNode().exec(DUMMY_ARTIFACTS)
        assert mock_run.call_count == 2
        assert result == {"passed": False, "error_log": "FAIL: Test case 1"}

    def test_post_success(self):
        shared = {}
        result = ValidationNode().post(shared, None, exec_res={"passed": True})
        assert result == "success"

    def test_post_failure(self):
        shared = {}
        exec_res = {"passed": False, "error_log": "error"}
        result = ValidationNode().post(shared, None, exec_res)
        assert result == "failure"
        assert shared["error_log"] == "error"


# --- Remaining tests for other nodes (unchanged) ---
class TestCritiqueAgentNode:
    @patch("nodes.call_llm", return_value="No issues found.")
    def test_exec_no_issues(self, mock_call_llm, mocker):
        mocker.patch("nodes.status"); mocker.patch("nodes.print_step")
        result = CritiqueAgentNode().exec(DUMMY_ARTIFACTS)
        assert result is None

    @patch("nodes.call_llm", return_value="This is a major problem.")
    def test_exec_issues_found(self, mock_call_llm, mocker):
        mocker.patch("nodes.status"); mocker.patch("nodes.print_step"); mocker.patch("nodes.print_critique")
        result = CritiqueAgentNode().exec(DUMMY_ARTIFACTS)
        assert result == "This is a major problem."


class TestDebugAndRefineNode:
    def test_prep_prioritizes_error_log(self):
        shared = {"target_spec_content":"s", "generated_artifacts":{}, "error_log":"e", "critique_feedback":"c"}
        assert DebugAndRefineNode().prep(shared)["feedback"] == "e"

    @patch("nodes.call_llm")
    def test_exec_success(self, mock_call_llm, mocker):
        mocker.patch("nodes.status"); mocker.patch("nodes.print_step")
        yaml_response = f"```yaml\ngenerate_rtl: |\n  {DUMMY_RTL_CODE}\n```"
        mock_call_llm.return_value = yaml_response
        result = DebugAndRefineNode().exec({"spec": "s", "artifacts": {}, "feedback": "e"})
        assert result["generate_rtl"].strip() == DUMMY_RTL_CODE.strip()

    def test_post_max_attempts(self):
        shared = {"debug_attempt_count": 1}
        result = DebugAndRefineNode().post(shared, None, {})
        assert result == "max_attempts_reached"


class TestHumanApprovalNode:
    @patch("nodes.prompt_for_confirmation", return_value=True)
    def test_exec_approves(self, mock_prompt, mocker):
        mocker.patch("nodes.print_code"); mocker.patch("nodes.print_step")
        node = HumanApprovalNode()
        node.flow_control = MagicMock(stop_flow=False)
        node.exec(DUMMY_ARTIFACTS)
        assert node.flow_control.stop_flow is False

    @patch("nodes.prompt_for_confirmation", return_value=False)
    def test_exec_rejects(self, mock_prompt, mocker):
        mocker.patch("nodes.print_code"); mocker.patch("nodes.print_step")
        node = HumanApprovalNode()
        node.flow_control = MagicMock(stop_flow=False)
        node.exec(DUMMY_ARTIFACTS)
        assert node.flow_control.stop_flow is True


class TestFileParserAndWriterNode:
    @patch("nodes.os.makedirs")
    def test_prep(self, mock_makedirs):
        shared = {"target_spec_name": "d.md", "generated_artifacts": DUMMY_ARTIFACTS}
        result = FileParserAndWriterNode().prep(shared)
        assert len(result) == 2
        assert result[0]["path"] == "output/d/d.v"

    @patch("builtins.open", new_callable=mock_open)
    def test_exec(self, mock_file, mocker):
        mocker.patch("nodes.print_step")
        files_to_write = [{"path": "f.v", "content": "c"}]
        result = FileParserAndWriterNode().exec(files_to_write)
        mock_file.assert_called_with("f.v", 'w', encoding='utf-8')
        assert result == ["f.v"]


class TestSimulationScriptGeneratorNode:
    @patch("builtins.open", new_callable=mock_open)
    @patch("nodes.os.chmod")
    def test_exec_success(self, mock_chmod, mock_file):
        file_paths = ["output/d/d.v", "output/d/d_tb.v"]
        SimulationScriptGeneratorNode().exec(file_paths)
        mock_file.assert_called_with("output/d/run_sim.sh", 'w', encoding='utf-8')
        mock_chmod.assert_called_with("output/d/run_sim.sh", 0o755)

    def test_exec_no_files_written(self):
        result = SimulationScriptGeneratorNode().exec([])
        assert "No files were written" in result