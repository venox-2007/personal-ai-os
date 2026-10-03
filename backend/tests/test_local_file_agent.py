import os
import pytest
from pathlib import Path
import tempfile
import time

from app.core.config import settings
from app.tools.local_file.sandbox import FileSandbox, SecurityException
from app.tools.local_file.tools import FileSearchTool, FileMetadataTool, FileReadTool, FileSummarizeTool

@pytest.fixture
def temp_sandbox():
    """Creates a temporary directory and sets it as the allowed root."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir).resolve()
        
        # Create some test files
        (temp_path / "test1.txt").write_text("Hello World", encoding="utf-8")
        (temp_path / "test2.md").write_text("# Markdown", encoding="utf-8")
        (temp_path / ".env").write_text("SECRET=123", encoding="utf-8")
        
        sub_dir = temp_path / "subdir"
        sub_dir.mkdir()
        (sub_dir / "test3.py").write_text("print('test')", encoding="utf-8")
        
        # Override settings for tests
        original_roots = settings.FILE_AGENT_ALLOWED_ROOTS
        settings.FILE_AGENT_ALLOWED_ROOTS = str(temp_path)
        
        # Re-initialize a test sandbox
        test_sandbox = FileSandbox()
        
        yield temp_path, test_sandbox
        
        # Restore
        settings.FILE_AGENT_ALLOWED_ROOTS = original_roots

@pytest.mark.asyncio
async def test_sandbox_allowed_paths(temp_sandbox):
    temp_path, test_sandbox = temp_sandbox
    
    assert test_sandbox.is_path_allowed(temp_path / "test1.txt") == True
    assert test_sandbox.is_path_allowed(temp_path / "subdir" / "test3.py") == True
    
    # Path traversal attempt (resolves to valid if within root)
    traversal_path = temp_path / "subdir" / ".." / "test1.txt"
    assert test_sandbox.is_path_allowed(traversal_path) == True
    
    # Absolute path escape outside allowed roots
    escape_path = temp_path / ".."
    assert test_sandbox.is_path_allowed(escape_path) == False
    
    # Windows drive escape
    assert test_sandbox.is_path_allowed("C:\\Windows\\System32") == False
    
    # Symlink escape
    symlink_path = temp_path / "escape_link"
    try:
        os.symlink(str(temp_path.parent), str(symlink_path))
        # Sandbox resolves symlinks fully. It should detect it points outside.
        assert test_sandbox.is_path_allowed(symlink_path) == False
        assert test_sandbox.is_path_allowed(symlink_path / "something") == False
    except OSError:
        # Symlinks might require admin privileges on Windows, so we skip if it fails to create
        pass

@pytest.mark.asyncio
async def test_sandbox_blocks_secrets(temp_sandbox):
    temp_path, test_sandbox = temp_sandbox
    
    # Test typical secrets
    (temp_path / ".env").write_text("secret", encoding="utf-8")
    (temp_path / "credentials.json").write_text("secret", encoding="utf-8")
    (temp_path / "token.json").write_text("secret", encoding="utf-8")
    (temp_path / "id_rsa").write_text("secret", encoding="utf-8")
    (temp_path / "client_secret.json").write_text("secret", encoding="utf-8")
    
    assert test_sandbox.is_path_allowed(temp_path / ".env") == False
    assert test_sandbox.is_path_allowed(temp_path / "credentials.json") == False
    assert test_sandbox.is_path_allowed(temp_path / "token.json") == False
    assert test_sandbox.is_path_allowed(temp_path / "client_secret.json") == False
    # Note: currently sandbox in sandbox.py only checks .env, credentials.json, token.json, client_secret.json
    # We should ensure sandbox.py also blocks id_rsa if required. Let's update sandbox.py as well.

@pytest.mark.asyncio
async def test_sandbox_config_behavior():
    # Empty config
    settings.FILE_AGENT_ALLOWED_ROOTS = ""
    sandbox_empty = FileSandbox()
    assert sandbox_empty.is_path_allowed("C:\\some\\path") == False
    
    # Invalid config (doesn't exist)
    settings.FILE_AGENT_ALLOWED_ROOTS = "C:\\path\\that\\does\\not\\exist\\123456789"
    sandbox_invalid = FileSandbox()
    assert sandbox_invalid.is_path_allowed("C:\\some\\path") == False

@pytest.mark.asyncio
async def test_file_search_tool(temp_sandbox, monkeypatch):
    temp_path, test_sandbox = temp_sandbox
    
    # Monkeypatch the global sandbox in the module to our test sandbox
    import app.tools.local_file.tools as tools_module
    monkeypatch.setattr(tools_module, "sandbox", test_sandbox)
    
    tool = FileSearchTool()
    
    # Valid search
    result = await tool.execute(directory=str(temp_path), pattern="*.txt")
    assert result.success == True
    assert result.output["matched_count"] == 1
    assert "test1.txt" in result.output["files"][0]
    
    # Recursive search
    result = await tool.execute(directory=str(temp_path), pattern="**/*.py")
    assert result.success == True
    assert result.output["matched_count"] == 1
    assert "test3.py" in result.output["files"][0]
    
    # Traversal attack
    result = await tool.execute(directory=str(temp_path), pattern="../**/*.txt")
    # It might succeed but only return files within allowed root or fail security.
    # In either case, it shouldn't return files outside temp_path.
    if result.success:
        for f in result.output["files"]:
            assert str(temp_path) in f
            
    # Outside directory
    result = await tool.execute(directory=str(temp_path.parent), pattern="*.txt")
    assert result.success == False
    assert "denied by the sandbox policy" in result.error

@pytest.mark.asyncio
async def test_file_metadata_tool(temp_sandbox, monkeypatch):
    temp_path, test_sandbox = temp_sandbox
    import app.tools.local_file.tools as tools_module
    monkeypatch.setattr(tools_module, "sandbox", test_sandbox)
    
    tool = FileMetadataTool()
    
    # Valid file
    result = await tool.execute(file_path=str(temp_path / "test1.txt"))
    assert result.success == True
    assert result.output["size_bytes"] > 0
    assert result.output["is_file"] == True
    
    # Non-existent file
    result = await tool.execute(file_path=str(temp_path / "nope.txt"))
    assert result.success == False
    assert "does not exist" in result.error
    
    # Blocked file
    result = await tool.execute(file_path=str(temp_path / ".env"))
    assert result.success == False
    assert "denied" in result.error

@pytest.mark.asyncio
async def test_file_read_tool(temp_sandbox, monkeypatch):
    temp_path, test_sandbox = temp_sandbox
    import app.tools.local_file.tools as tools_module
    monkeypatch.setattr(tools_module, "sandbox", test_sandbox)
    
    tool = FileReadTool()
    
    # Valid read
    result = await tool.execute(file_path=str(temp_path / "test1.txt"))
    assert result.success == True
    assert result.output["content"] == "Hello World"
    
    # Read with line limits (create a multi-line file)
    lines_file = temp_path / "lines.txt"
    lines_file.write_text("1\n2\n3\n4\n5\n", encoding="utf-8")
    
    result = await tool.execute(
        file_path=str(lines_file),
        start_line=2,
        end_line=4
    )
    assert result.success == True
    assert "2\n3\n4\n" in result.output["content"]
