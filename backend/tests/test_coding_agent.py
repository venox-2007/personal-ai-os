import pytest
import os
from pathlib import Path
import tempfile
import git
from unittest.mock import patch, MagicMock

from app.core.config import settings
from app.tools.coding.sandbox import CodeSandbox, SecurityException
from app.tools.coding.tools import (
    CodeListRepositoryTool, CodeSearchTool, CodeReadFileTool,
    CodeGitStatusTool, CodeGitLogTool, CodeGitShowTool,
    CodeRepoMetadataTool
)

@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        repo = git.Repo.init(p)
        
        # Add files
        (p / "main.py").write_text("print('Hello World')\n", encoding="utf-8")
        (p / ".env").write_text("SECRET=123", encoding="utf-8")
        
        repo.index.add(["main.py"])
        repo.index.commit("Initial commit")
        
        (p / "README.md").write_text("# Test Repo\n", encoding="utf-8")
        
        # Save old config
        old_roots = settings.CODING_AGENT_ALLOWED_ROOTS
        settings.CODING_AGENT_ALLOWED_ROOTS = str(p)
        
        yield p, repo
        
        repo.close()
        settings.CODING_AGENT_ALLOWED_ROOTS = old_roots

@pytest.mark.asyncio
async def test_coding_sandbox(temp_repo, monkeypatch):
    p, _ = temp_repo
    
    test_sandbox = CodeSandbox()
    import app.tools.coding.tools as tools_module
    monkeypatch.setattr(tools_module, "sandbox", test_sandbox)
    
    # Allowed
    assert test_sandbox.is_path_allowed(p / "main.py") == True
    
    # Blocked secret
    assert test_sandbox.is_path_allowed(p / ".env") == False
    
    # Escape
    assert test_sandbox.is_path_allowed(p / "..") == False

@pytest.mark.asyncio
async def test_code_list_repo(temp_repo, monkeypatch):
    p, _ = temp_repo
    test_sandbox = CodeSandbox()
    import app.tools.coding.tools as tools_module
    monkeypatch.setattr(tools_module, "sandbox", test_sandbox)
    
    tool = CodeListRepositoryTool()
    res = await tool.execute(repo_path=str(p))
    assert res.success == True
    assert "main.py" in res.output["files"]
    assert "README.md" in res.output["files"]
    assert ".git" not in res.output["files"] # excluded

@pytest.mark.asyncio
async def test_code_search(temp_repo, monkeypatch):
    p, _ = temp_repo
    test_sandbox = CodeSandbox()
    import app.tools.coding.tools as tools_module
    monkeypatch.setattr(tools_module, "sandbox", test_sandbox)
    
    tool = CodeSearchTool()
    res = await tool.execute(repo_path=str(p), pattern="Hello")
    assert res.success == True
    assert len(res.output["matches"]) == 1
    assert res.output["matches"][0]["file"] == "main.py"

@pytest.mark.asyncio
async def test_code_read_file(temp_repo, monkeypatch):
    p, _ = temp_repo
    test_sandbox = CodeSandbox()
    import app.tools.coding.tools as tools_module
    monkeypatch.setattr(tools_module, "sandbox", test_sandbox)
    
    tool = CodeReadFileTool()
    res = await tool.execute(file_path=str(p / "main.py"))
    assert res.success == True
    assert "print('Hello World')" in res.output["content"]
    
    res = await tool.execute(file_path=str(p / ".env"))
    assert res.success == False # blocked by sandbox

@pytest.mark.asyncio
async def test_git_tools(temp_repo, monkeypatch):
    p, repo = temp_repo
    test_sandbox = CodeSandbox()
    import app.tools.coding.tools as tools_module
    monkeypatch.setattr(tools_module, "sandbox", test_sandbox)
    
    status_tool = CodeGitStatusTool()
    res = await status_tool.execute(repo_path=str(p))
    assert res.success == True
    assert "Untracked files" in res.output["status"]
    
    log_tool = CodeGitLogTool()
    res = await log_tool.execute(repo_path=str(p))
    assert res.success == True
    assert len(res.output["commits"]) == 1
    assert res.output["commits"][0]["message"] == "Initial commit"
    
    meta_tool = CodeRepoMetadataTool()
    res = await meta_tool.execute(repo_path=str(p))
    assert res.success == True
    assert res.output["active_branch"] == "master" or res.output["active_branch"] == "main"
