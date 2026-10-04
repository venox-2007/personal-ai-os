import os
import json
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List

import git

from app.tools.base import BaseTool, ToolResult, PermissionLevel
from app.core.config import settings
from app.tools.coding.sandbox import sandbox, SecurityException
from app.tools.coding.tools import is_text_file

logger = logging.getLogger(__name__)

class CodeProposeEditTool(BaseTool):
    name: str = "code_propose_edit"
    description: str = "Propose an edit to a file. Does NOT modify the file. Returns a proposal that the user can review before you call code_apply_edit."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_1_LOW_IMPACT
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "expected_old_content": {"type": "string", "description": "The exact block of code to replace. Must match exactly."},
            "new_content": {"type": "string", "description": "The new content to insert."},
            "reason": {"type": "string"}
        },
        "required": ["file_path", "expected_old_content", "new_content", "reason"]
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        old_content = kwargs.get("expected_old_content")
        new_content = kwargs.get("new_content")
        reason = kwargs.get("reason")
        
        try:
            safe_path = sandbox.get_safe_path(file_path)
            if not safe_path.is_file():
                return ToolResult(success=False, error="File does not exist.")
            if not is_text_file(safe_path):
                return ToolResult(success=False, error="File appears to be binary.")
                
            with open(safe_path, 'r', encoding='utf-8') as f:
                current_text = f.read()
                
            if old_content not in current_text:
                return ToolResult(success=False, error="expected_old_content not found in the file. Ensure exact match.")
                
            return ToolResult(success=True, output={
                "status": "proposal_ready",
                "file_path": file_path,
                "reason": reason,
                "note": "Call code_apply_edit to actually modify the file. This requires user approval."
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class CodeApplyEditTool(BaseTool):
    name: str = "code_apply_edit"
    description: str = "Apply an atomic edit to a file. Replaces expected_old_content with new_content."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "expected_old_content": {"type": "string"},
            "new_content": {"type": "string"}
        },
        "required": ["file_path", "expected_old_content", "new_content"]
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        old_content = kwargs.get("expected_old_content")
        new_content = kwargs.get("new_content")
        
        try:
            safe_path = sandbox.get_safe_path(file_path)
            if not safe_path.is_file():
                return ToolResult(success=False, error="File does not exist.")
                
            with open(safe_path, 'r', encoding='utf-8') as f:
                current_text = f.read()
                
            if old_content not in current_text:
                return ToolResult(success=False, error="expected_old_content not found in the file. The file may have changed.")
                
            # Perform replacement
            updated_text = current_text.replace(old_content, new_content, 1)
            
            with open(safe_path, 'w', encoding='utf-8') as f:
                f.write(updated_text)
                
            return ToolResult(success=True, output={"status": "edited", "file_path": file_path})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CodeGitDiffTool(BaseTool):
    name: str = "code_git_diff"
    description: str = "View the current workspace diff (uncommitted changes)."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "repo_path": {"type": "string"}
        },
        "required": ["repo_path"]
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        repo = None
        try:
            safe_path = sandbox.get_safe_path(kwargs.get("repo_path"))
            repo = git.Repo(safe_path)
            diff_text = repo.git.diff()
            if len(diff_text) > 15000:
                diff_text = diff_text[:15000] + "\n...[TRUNCATED]"
            return ToolResult(success=True, output={"diff": diff_text})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            if repo:
                repo.close()


class CodeCreateBranchTool(BaseTool):
    name: str = "code_create_branch"
    description: str = "Create and checkout a new git branch."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "repo_path": {"type": "string"},
            "branch_name": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"}
        },
        "required": ["repo_path", "branch_name"]
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        repo = None
        try:
            safe_path = sandbox.get_safe_path(kwargs.get("repo_path"))
            branch_name = kwargs.get("branch_name")
            
            if not branch_name or not branch_name.replace("-", "").replace("_", "").isalnum():
                return ToolResult(success=False, error="Invalid branch name format.")
                
            repo = git.Repo(safe_path)
            
            # Check if branch exists
            if branch_name in [h.name for h in repo.heads]:
                return ToolResult(success=False, error=f"Branch {branch_name} already exists.")
                
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()
            
            return ToolResult(success=True, output={"status": "branch_created", "branch": branch_name})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            if repo:
                repo.close()


class CodeCommitTool(BaseTool):
    name: str = "code_commit"
    description: str = "Commit specific files to the repository."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "repo_path": {"type": "string"},
            "files_to_commit": {
                "type": "array",
                "items": {"type": "string"}
            },
            "commit_message": {"type": "string"}
        },
        "required": ["repo_path", "files_to_commit", "commit_message"]
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        repo = None
        try:
            safe_path = sandbox.get_safe_path(kwargs.get("repo_path"))
            files_to_commit = kwargs.get("files_to_commit", [])
            message = kwargs.get("commit_message")
            
            if not files_to_commit or not message:
                return ToolResult(success=False, error="Files and commit message required.")
                
            repo = git.Repo(safe_path)
            
            added_files = []
            for f in files_to_commit:
                # Sanity check file
                f_path = (safe_path / f).resolve()
                if not str(f_path).startswith(str(safe_path)):
                    continue # prevent escape
                if f_path.exists():
                    repo.index.add([f])
                    added_files.append(f)
                    
            if not added_files:
                return ToolResult(success=False, error="No valid files to commit.")
                
            commit = repo.index.commit(message)
            
            return ToolResult(success=True, output={
                "status": "committed",
                "sha": commit.hexsha,
                "message": message,
                "files_committed": added_files
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            if repo:
                repo.close()


class CodeRunTestsTool(BaseTool):
    name: str = "code_run_tests"
    description: str = "Run a registered test command from the sandbox."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "test_command_id": {"type": "string", "description": "ID of the configured test command (e.g. backend_tests, frontend_build)."}
        },
        "required": ["test_command_id"]
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        cmd_id = kwargs.get("test_command_id")
        
        try:
            config_str = settings.CODING_AGENT_TEST_COMMANDS
            if not config_str:
                return ToolResult(success=False, error="No test commands configured in CODING_AGENT_TEST_COMMANDS.")
                
            try:
                allowed_cmds = json.loads(config_str)
            except json.JSONDecodeError:
                return ToolResult(success=False, error="CODING_AGENT_TEST_COMMANDS is not valid JSON.")
                
            if cmd_id not in allowed_cmds:
                return ToolResult(success=False, error=f"Command ID '{cmd_id}' is not in the allowlist. Available: {list(allowed_cmds.keys())}")
                
            cmd_config = allowed_cmds[cmd_id]
            executable = cmd_config.get("executable")
            args = cmd_config.get("args", [])
            cwd_relative = cmd_config.get("cwd", ".")
            
            # The agent executes tests from the first allowed root if available, otherwise blocks.
            # In a real system, the tool might take repo_path, but for safety, we tie it to the first root.
            if not sandbox.allowed_roots:
                return ToolResult(success=False, error="No CODING_AGENT_ALLOWED_ROOTS configured.")
                
            base_dir = sandbox.allowed_roots[0]
            target_cwd = (base_dir / cwd_relative).resolve()
            
            if not str(target_cwd).startswith(str(base_dir)):
                return ToolResult(success=False, error="Target working directory escapes allowed root.")
                
            # Execute with asyncio.subprocess
            full_command = [executable] + args
            
            # Use shell=False for safety, relying on resolving executable manually if needed.
            # However, on Windows, npx, npm, pytest might be .cmd or .exe
            # We trust the allowlist entirely. We do NOT use shell=True.
            # To fix 'executable not found' on windows for 'npm', we might need to resolve it.
            # For this MVP phase, we just pass it to subprocess.
            
            # In a strict environment, we'd ensure executable is absolute path.
            
            process = await asyncio.create_subprocess_exec(
                *full_command,
                cwd=str(target_cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(success=False, error="Test command timed out after 30 seconds.")
                
            return ToolResult(success=True, output={
                "command_id": cmd_id,
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='ignore')[:5000],
                "stderr": stderr.decode('utf-8', errors='ignore')[:5000]
            })
            
        except FileNotFoundError:
            return ToolResult(success=False, error="Executable not found in path.")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
