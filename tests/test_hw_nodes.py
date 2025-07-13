# tests/test_hw_nodes.py

import pytest
import asyncio
import numpy as np
import yaml
from unittest.mock import MagicMock, mock_open, patch, ANY

from nodes import (
    KnowledgeIndexNode, SpecSelectionNode, KnowledgeRetrievalNode, PlanningAgentNode,
    CodeGenerationAgentNode, ValidationNode, CritiqueAgentNode, DebugAndRefineNode,
    HumanApprovalNode, FileParserAndWriterNode, SimulationScriptGeneratorNode
)

# --- Reusable Test Data ---
DUMMY_RTL_CODE = "module rtl_design; /* RTL code */ endmodule"
DUMMY_TB_CODE = "module tb_design; /* Testbench code */ endmodule"
DUMMY_SPEC_CONTENT = "This is a detailed specification for a hardware module."
DUMMY_ARTIFACTS = {"generate_rtl": DUMMY_RTL_CODE, "generate_testbench": DUMMY_TB_CODE}

# Force pytest-anyio to only use the 'asyncio' backend for this file.
# This prevents it from trying to run tests against 'trio', which is not
# installed and not used by the application code.
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
        node = KnowledgeIndexNode()
        m = mock_open(read_data="some knowledge content")
        with patch("builtins.open", m):
            result = node.exec(None)
        mock_isdir.assert_called_with('knowledge_source')
        mock_glob.assert_called_with('knowledge_source/*.txt')
        m.assert_called_once_with('knowledge_source/doc1.txt', 'r', encoding='utf-8')
        mock_get_embedding.assert_called_with("some knowledge content")
        assert "index" in result
        assert isinstance(result["index"], np.ndarray)
        assert result["chunks"] == ["some knowledge content"]

    @patch("nodes.os.path.isdir", return_value=False)
    def test_exec_dir_not_found(self, mock_isdir, mocker):
        mock_console_print = mocker.patch("nodes.console.print")
        node = KnowledgeIndexNode()
        result = node.exec(None)
        mock_console_print.assert_called_with("[warning]Knowledge source directory not found. Skipping RAG.[/warning]")
        assert result == {"index": None, "chunks": []}

    def test_post(self):
        node = KnowledgeIndexNode()
        shared = {}
        exec_res = {"index": np.array([1]), "chunks": ["chunk1"]}
        node.post(shared, None, exec_res)
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
        node = SpecSelectionNode()
        m = mock_open(read_data=DUMMY_SPEC_CONTENT)
        with patch("builtins.open", m):
            result = node.exec(None)
        mock_isdir.assert_called_with('specs')
        mock_glob.assert_called_with('specs/*.md')
        m.assert_called_once_with('specs/test_spec.md', 'r', encoding='utf-8')
        mock_prompt.assert_called_once()
        assert result["name"] == "test_spec.md"
        assert result["content"] == DUMMY_SPEC_CONTENT

    @patch("nodes.os.path.isdir", return_value=False)
    def test_exec_dir_not_found(self, mock_isdir):
        node = SpecSelectionNode()
        with pytest.raises(NotADirectoryError):
            node.exec(None)

    def test_post(self):
        node = SpecSelectionNode()
        shared = {}
        exec_res = {"name": "spec.md", "content": "spec content"}
        node.post(shared, None, exec_res)
        assert shared["target_spec_name"] == "spec.md"
        assert shared["target_spec_content"] == "spec content"


# --- Test KnowledgeRetrievalNode ---
class TestKnowledgeRetrievalNode:
    def test_prep_with_knowledge(self):
        node = KnowledgeRetrievalNode()
        shared = {
            "knowledge_index": np.array([[1, 2]]), "knowledge_chunks": ["chunk1"], "target_spec_content": "spec"
        }
        result = node.prep(shared)
        assert result is not None
        assert result["spec_content"] == "spec"

    def test_prep_without_knowledge(self):
        node = KnowledgeRetrievalNode()
        shared = {"target_spec_content": "spec"}
        result = node.prep(shared)
        assert result is None

    @patch("nodes.get_embedding", return_value=np.array([1, 1]))
    @patch("nodes.cosine_similarity", return_value=np.array([[0.9, 0.1]]))
    def test_exec_finds_match(self, mock_sim, mock_embed, mocker):
        mocker.patch("nodes.print_step")
        node = KnowledgeRetrievalNode()
        inputs = {
            "spec_content": "spec",
            "knowledge_index": np.array([[1, 1], [0, 0]]),
            "knowledge_chunks": ["relevant chunk", "irrelevant chunk"]
        }
        result = node.exec(inputs)
        assert result == "relevant chunk"


# --- Test PlanningAgentNode ---
class TestPlanningAgentNode:
    @patch("nodes.call_llm")
    def test_exec_success(self, mock_call_llm, mocker):
        mocker.patch("nodes.print_plan")
        mocker.patch("nodes.print_step")
        mocker.patch("nodes.status")
        node = PlanningAgentNode()
        yaml_plan = "- task: generate_rtl\n  description: 'Generate RTL code'"
        mock_call_llm.return_value = yaml_plan
        result = node.exec({"spec_content": "spec", "knowledge": "knowledge"})
        mock_call_llm.assert_called_once()
        assert result == [{"task": "generate_rtl", "description": "Generate RTL code"}]

    @patch("nodes.call_llm")
    def test_exec_bad_yaml_fallback(self, mock_call_llm, mocker):
        mocker.patch("nodes.console.print")
        mocker.patch("nodes.print_plan")
        mocker.patch("nodes.print_step")
        mocker.patch("nodes.status")
        node = PlanningAgentNode()
        mock_call_llm.return_value = "this is not: valid yaml"
        result = node.exec({"spec_content": "spec", "knowledge": "knowledge"})
        assert len(result) == 2
        assert result[0]['task'] == 'generate_rtl'
        assert result[1]['task'] == 'generate_testbench'


# --- Test CodeGenerationAgentNode (Async) ---
@pytest.mark.anyio
class TestCodeGenerationAgentNode:
    async def test_prep_async(self):
        """Tests the asynchronous prep method."""
        node = CodeGenerationAgentNode()
        node.params = {'task': 'generate_rtl'}
        
        shared = {"target_spec_content": "spec", "retrieved_knowledge": "knowledge"}
        result = await node.prep_async(shared)
        assert result["task"] == "generate_rtl"
        assert result["spec_content"] == "spec"

    @patch("nodes.call_llm", return_value="```verilog\nmodule test; endmodule\n```")
    async def test_exec_async_strips_codeblock(self, mock_call_llm, mocker):
        """Tests that the exec method correctly strips markdown code blocks."""
        mocker.patch("nodes.print_step")
        mocker.patch("asyncio.get_running_loop", return_value=asyncio.get_running_loop())
        node = CodeGenerationAgentNode()
        inputs = {"task": "generate_rtl", "spec_content": "spec", "knowledge": "knowledge"}
        result = await node.exec_async(inputs)
        mock_call_llm.assert_called_once()
        assert result == {"generate_rtl": "module test; endmodule"}


# --- Test ValidationNode ---
class TestValidationNode:
    @patch("nodes.subprocess.run")
    def test_exec_success(self, mock_run, mocker):
        mocker.patch("nodes.print_step")
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        node = ValidationNode()
        result = node.exec(DUMMY_ARTIFACTS)
        mock_run.assert_called_once()
        cmd_args = mock_run.call_args[0][0]
        assert "iverilog" in cmd_args
        assert result == {"passed": True, "error_log": None}

    @patch("nodes.subprocess.run")
    def test_exec_failure(self, mock_run, mocker):
        mocker.patch("nodes.console.print")
        mocker.patch("nodes.print_step")
        mock_run.return_value = MagicMock(returncode=1, stderr="Syntax Error on line 5", stdout="")
        node = ValidationNode()
        result = node.exec(DUMMY_ARTIFACTS)
        assert result == {"passed": False, "error_log": "Syntax Error on line 5"}

    def test_post_success(self):
        node = ValidationNode()
        shared = {}
        result = node.post(shared, None, exec_res={"passed": True})
        assert result == "success"
        assert "validation_result" in shared

    def test_post_failure(self):
        node = ValidationNode()
        shared = {}
        exec_res = {"passed": False, "error_log": "error"}
        result = node.post(shared, None, exec_res)
        assert result == "failure"
        assert shared["validation_result"] == exec_res
        assert shared["error_log"] == "error"


# --- Test CritiqueAgentNode ---
class TestCritiqueAgentNode:
    @patch("nodes.call_llm", return_value="No issues found.")
    def test_exec_no_issues(self, mock_call_llm, mocker):
        mocker.patch("nodes.status")
        mocker.patch("nodes.print_step")
        node = CritiqueAgentNode()
        result = node.exec(DUMMY_ARTIFACTS)
        assert result is None

    @patch("nodes.call_llm", return_value="This is a major problem.")
    def test_exec_issues_found(self, mock_call_llm, mocker):
        mocker.patch("nodes.status")
        mocker.patch("nodes.print_step")
        mocker.patch("nodes.print_critique")
        node = CritiqueAgentNode()
        result = node.exec(DUMMY_ARTIFACTS)
        assert result == "This is a major problem."


# --- Test DebugAndRefineNode ---
class TestDebugAndRefineNode:
    def test_prep_prioritizes_error_log(self):
        node = DebugAndRefineNode()
        shared = {
            "target_spec_content": "spec", "generated_artifacts": DUMMY_ARTIFACTS,
            "error_log": "compiler error", "critique_feedback": "critique feedback"
        }
        result = node.prep(shared)
        assert result["feedback"] == "compiler error"

    @patch("nodes.call_llm")
    def test_exec_success(self, mock_call_llm, mocker):
        mocker.patch("nodes.status")
        mocker.patch("nodes.print_step")
        node = DebugAndRefineNode()
        new_code = "module refined_rtl; endmodule"
        yaml_response = f"```yaml\ngenerate_rtl: |\n  {new_code}\n```"
        mock_call_llm.return_value = yaml_response
        inputs = {"spec": "spec", "artifacts": DUMMY_ARTIFACTS, "feedback": "error"}
        result = node.exec(inputs)
        assert result["generate_rtl"].strip() == new_code.strip()

    def test_post_max_attempts(self):
        node = DebugAndRefineNode()
        shared = {"debug_attempt_count": 1}
        result = node.post(shared, None, {})
        assert result == "max_attempts_reached"
        assert shared["debug_attempt_count"] == 2


# --- Test HumanApprovalNode ---
class TestHumanApprovalNode:
    @patch("nodes.prompt_for_confirmation", return_value=True)
    def test_exec_approves(self, mock_prompt, mocker):
        mocker.patch("nodes.print_code")
        mocker.patch("nodes.print_step")
        node = HumanApprovalNode()
        node.flow_control = MagicMock(stop_flow=False)
        node.exec(DUMMY_ARTIFACTS)
        mock_prompt.assert_called_once()
        assert node.flow_control.stop_flow is False

    @patch("nodes.prompt_for_confirmation", return_value=False)
    def test_exec_rejects(self, mock_prompt, mocker):
        mocker.patch("nodes.print_code")
        mocker.patch("nodes.print_step")
        node = HumanApprovalNode()
        node.flow_control = MagicMock(stop_flow=False)
        node.exec(DUMMY_ARTIFACTS)
        mock_prompt.assert_called_once()
        assert node.flow_control.stop_flow is True


# --- Test FileParserAndWriterNode ---
class TestFileParserAndWriterNode:
    @patch("nodes.os.makedirs")
    def test_prep(self, mock_makedirs):
        node = FileParserAndWriterNode()
        shared = {"target_spec_name": "my_design.md", "generated_artifacts": DUMMY_ARTIFACTS}
        result = node.prep(shared)
        mock_makedirs.assert_called_with("output/my_design", exist_ok=True)
        assert len(result) == 2
        assert result[0]["path"] == "output/my_design/my_design.v"
        assert result[0]["content"] == DUMMY_RTL_CODE

    @patch("builtins.open", new_callable=mock_open)
    def test_exec(self, mock_file, mocker):
        mocker.patch("nodes.print_step")
        node = FileParserAndWriterNode()
        files_to_write = [{"path": "output/a.v", "content": "rtl"}]
        result = node.exec(files_to_write)
        mock_file.assert_called_once_with("output/a.v", 'w', encoding='utf-8')
        mock_file().write.assert_called_once_with("rtl")
        assert result == ["output/a.v"]


# --- Test SimulationScriptGeneratorNode ---
class TestSimulationScriptGeneratorNode:
    @patch("builtins.open", new_callable=mock_open)
    @patch("nodes.os.chmod")
    def test_exec_success(self, mock_chmod, mock_file):
        node = SimulationScriptGeneratorNode()
        file_paths = ["output/design/my_design.v", "output/design/my_design_tb.v"]
        node.exec(file_paths)
        script_path = "output/design/run_sim.sh"
        mock_file.assert_called_once_with(script_path, 'w', encoding='utf-8')
        handle = mock_file()
        expected_content = "#!/bin/bash\niverilog -o sim_output.vvp my_design.v my_design_tb.v\nvvp sim_output.vvp\n"
        handle.write.assert_called_once_with(expected_content)
        mock_chmod.assert_called_once_with(script_path, 0o755)

    def test_exec_no_files_written(self):
        node = SimulationScriptGeneratorNode()
        result = node.exec([])
        assert "No files were written" in result