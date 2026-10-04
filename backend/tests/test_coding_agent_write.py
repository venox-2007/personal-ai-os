import pytest
import os
import json
from pathlib import Path
import tempfile
import git
from unittest.mock import patch, MagicMock

from app.core.config import settings
from app.tools.coding.sandbox import CodeSandbox, SecurityException
from app.tools.coding.write_tools import (
    CodeProposeEditTool, CodeApplyEditTool, CodeGitDiffTool,
    CodeCreateBranchTool, CodeCommitTool, CodeRunTestsTool
)

@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        repo = git.Repo.init(p)
        
        # Add files
        (p / "main.py").write_text("print('Hello World')\n", encoding="utf-8")
        
        repo.index.add(["main.py"])
        repo.index.commit("Initial commit")
        
        old_roots = settings.CODING_AGENT_ALLOWED_ROOTS
        settings.CODING_AGENT_ALLOWED_ROOTS = str(p)
        
        yield p, repo
        
        repo.close()
        settings.CODING_AGENT_ALLOWED_ROOTS = old_roots

@pytest.mark.asyncio
async def test_code_edit_workflow(temp_repo, monkeypatch):
    p, repo = temp_repo
    test_sandbox = CodeSandbox()
    
    import app.tools.coding.write_tools as write_module
    monkeypatch.setattr(write_module, "sandbox", test_sandbox)
    
    # 1. Propose Edit
    propose_tool = CodeProposeEditTool()
    res = await propose_tool.execute(
        file_path=str(p / "main.py"),
        expected_old_content="print('Hello World')\n",
        new_content="print('Hello World Updated')\n",
        reason="Testing edit"
    )
    assert res.success == True
    assert res.output["status"] == "proposal_ready"
    
    # File not modified yet
    assert (p / "main.py").read_text(encoding="utf-8") == "print('Hello World')\n"
    
    # 2. Apply Edit
    apply_tool = CodeApplyEditTool()
    res = await apply_tool.execute(
        file_path=str(p / "main.py"),
        expected_old_content="print('Hello World')\n",
        new_content="print('Hello World Updated')\n"
    )
    assert res.success == True
    
    # File is modified
    assert (p / "main.py").read_text(encoding="utf-8") == "print('Hello World Updated')\n"
    
    # 3. Apply Edit with stale content (fails)
    res = await apply_tool.execute(
        file_path=str(p / "main.py"),
        expected_old_content="print('Hello World')\n",
        new_content="print('Stale Replace')\n"
    )
    assert res.success == False
    assert "expected_old_content not found" in res.error

@pytest.mark.asyncio
async def test_code_branch_and_commit(temp_repo, monkeypatch):
    p, repo = temp_repo
    test_sandbox = CodeSandbox()
    import app.tools.coding.write_tools as write_module
    monkeypatch.setattr(write_module, "sandbox", test_sandbox)
    
    # Create Branch
    branch_tool = CodeCreateBranchTool()
    res = await branch_tool.execute(repo_path=str(p), branch_name="feature-test")
    assert res.success == True
    assert repo.active_branch.name == "feature-test"
    
    # Modify file
    (p / "main.py").write_text("print('Hello World Updated')\n", encoding="utf-8")
    
    # Diff
    diff_tool = CodeGitDiffTool()
    res = await diff_tool.execute(repo_path=str(p))
    assert res.success == True
    assert "Hello World Updated" in res.output["diff"]
    
    # Commit
    commit_tool = CodeCommitTool()
    res = await commit_tool.execute(
        repo_path=str(p),
        files_to_commit=["main.py"],
        commit_message="Updated main.py"
    )
    assert res.success == True
    assert res.output["status"] == "committed"
    assert repo.head.commit.message == "Updated main.py"

@pytest.mark.asyncio
async def test_code_run_tests_invalid_command(temp_repo, monkeypatch):
    p, repo = temp_repo
    test_sandbox = CodeSandbox()
    import app.tools.coding.write_tools as write_module
    monkeypatch.setattr(write_module, "sandbox", test_sandbox)
    
    # Mock settings
    settings.CODING_AGENT_TEST_COMMANDS = '{"valid": {"executable": "echo", "args": ["hello"], "cwd": "."}}'
    
    tool = CodeRunTestsTool()
    res = await tool.execute(test_command_id="invalid")
    assert res.success == False
    assert "not in the allowlist" in res.error

@pytest.mark.asyncio
async def test_code_run_tests_injection_blocked(temp_repo, monkeypatch):
    p, repo = temp_repo
    test_sandbox = CodeSandbox()
    import app.tools.coding.write_tools as write_module
    monkeypatch.setattr(write_module, "sandbox", test_sandbox)
    
    # Mock settings
    settings.CODING_AGENT_TEST_COMMANDS = '{"valid": {"executable": "echo", "args": ["hello"], "cwd": "."}}'
    
    tool = CodeRunTestsTool()
    
    # Test arbitrary path execution injection by modifying test_command_id
    res = await tool.execute(test_command_id='valid; ls')
    assert res.success == False
    assert "not in the allowlist" in res.error
    
    res = await tool.execute(test_command_id='valid" && whoami')
    assert res.success == False
    assert "not in the allowlist" in res.error
