import os
import re
from pathlib import Path
from typing import Dict, Any, List

import git
from github import Github, GithubException

from app.tools.base import BaseTool, ToolResult, PermissionLevel
from app.core.config import settings
from app.core.logging import logger
from app.tools.coding.sandbox import sandbox

# Generated/Ignored directories
EXCLUDED_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist", ".idea", ".vscode"}
# Binary/non-text extensions
EXCLUDED_EXTS = {".exe", ".dll", ".so", ".dylib", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".tar", ".gz", ".mp3", ".mp4"}

def is_text_file(filepath: Path) -> bool:
    if filepath.suffix.lower() in EXCLUDED_EXTS:
        return False
    try:
        with open(filepath, 'tr') as check_file:
            check_file.read(1024)
            return True
    except UnicodeDecodeError:
        return False
    except Exception:
        return False

class CodeListRepositoryTool(BaseTool):
    name: str = "code_list_repository"
    description: str = "List the file structure of a local repository up to a certain depth."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "repo_path": {"type": "string"},
            "max_depth": {"type": "integer", "description": "Max depth to traverse (default 3)"}
        },
        "required": ["repo_path"]
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        repo_path = kwargs.get("repo_path")
        max_depth = kwargs.get("max_depth", 3)
        
        try:
            safe_path = sandbox.get_safe_path(repo_path)
            if not safe_path.is_dir():
                return ToolResult(success=False, error="Path is not a directory.")
                
            structure = []
            
            for root, dirs, files in os.walk(safe_path):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
                
                # Calculate depth
                current_depth = len(Path(root).relative_to(safe_path).parts)
                if current_depth > max_depth:
                    dirs[:] = [] # Don't traverse deeper
                    continue
                    
                rel_root = Path(root).relative_to(safe_path)
                prefix = str(rel_root) if str(rel_root) != "." else ""
                
                for f in files:
                    if prefix:
                        structure.append(f"{prefix}/{f}")
                    else:
                        structure.append(f)
            
            return ToolResult(success=True, output={"files": structure[:1000], "total_shown": min(len(structure), 1000)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class CodeSearchTool(BaseTool):
    name: str = "code_search"
    description: str = "Search for a text pattern in the source files of a local repository."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "repo_path": {"type": "string"},
            "pattern": {"type": "string"}
        },
        "required": ["repo_path", "pattern"]
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        repo_path = kwargs.get("repo_path")
        pattern = kwargs.get("pattern")
        
        try:
            safe_path = sandbox.get_safe_path(repo_path)
            regex = re.compile(pattern, re.IGNORECASE)
            
            results = []
            max_results = settings.CODING_AGENT_MAX_SEARCH_RESULTS
            
            for root, dirs, files in os.walk(safe_path):
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
                
                for f in files:
                    filepath = Path(root) / f
                    if not is_text_file(filepath):
                        continue
                        
                    try:
                        with open(filepath, 'r', encoding='utf-8') as file_obj:
                            lines = file_obj.readlines()
                            for i, line in enumerate(lines):
                                if regex.search(line):
                                    rel_path = str(filepath.relative_to(safe_path))
                                    results.append({
                                        "file": rel_path,
                                        "line_number": i + 1,
                                        "content": line.strip()
                                    })
                                    if len(results) >= max_results:
                                        break
                    except Exception:
                        pass
                if len(results) >= max_results:
                    break
                    
            return ToolResult(success=True, output={"matches": results, "pattern": pattern})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class CodeReadFileTool(BaseTool):
    name: str = "code_read_file"
    description: str = "Read the contents of a specific source file."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"}
        },
        "required": ["file_path"]
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        
        try:
            safe_path = sandbox.get_safe_path(file_path)
            
            if not safe_path.is_file():
                return ToolResult(success=False, error="File does not exist.")
                
            if not is_text_file(safe_path):
                return ToolResult(success=False, error="File appears to be binary.")
                
            stats = safe_path.stat()
            max_bytes = settings.CODING_AGENT_MAX_FILE_SIZE_KB * 1024
            if stats.st_size > max_bytes:
                return ToolResult(success=False, error=f"File exceeds max size of {settings.CODING_AGENT_MAX_FILE_SIZE_KB}KB.")
                
            with open(safe_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            return ToolResult(success=True, output={"content": content, "size_bytes": stats.st_size})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class CodeGitStatusTool(BaseTool):
    name: str = "code_git_status"
    description: str = "Get the git status of a local repository."
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
            status = repo.git.status()
            return ToolResult(success=True, output={"status": status})
        except git.InvalidGitRepositoryError:
            return ToolResult(success=False, error="Not a valid git repository.")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            if repo:
                repo.close()

class CodeGitLogTool(BaseTool):
    name: str = "code_git_log"
    description: str = "Get recent git commits."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "repo_path": {"type": "string"},
            "max_commits": {"type": "integer"}
        },
        "required": ["repo_path"]
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        repo = None
        try:
            safe_path = sandbox.get_safe_path(kwargs.get("repo_path"))
            max_commits = kwargs.get("max_commits", 10)
            repo = git.Repo(safe_path)
            commits = list(repo.iter_commits(max_count=max_commits))
            
            res = []
            for c in commits:
                res.append({
                    "sha": c.hexsha,
                    "author": str(c.author),
                    "message": c.message.strip(),
                    "date": c.committed_datetime.isoformat()
                })
            return ToolResult(success=True, output={"commits": res})
        except git.InvalidGitRepositoryError:
            return ToolResult(success=False, error="Not a valid git repository.")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            if repo:
                repo.close()

class CodeGitShowTool(BaseTool):
    name: str = "code_git_show"
    description: str = "Show a specific git commit's diff."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "repo_path": {"type": "string"},
            "commit_sha": {"type": "string"}
        },
        "required": ["repo_path", "commit_sha"]
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        repo = None
        try:
            safe_path = sandbox.get_safe_path(kwargs.get("repo_path"))
            repo = git.Repo(safe_path)
            show = repo.git.show(kwargs.get("commit_sha"))
            # Limit size of output to prevent blowing up LLM context
            if len(show) > 10000:
                show = show[:10000] + "\n...[TRUNCATED]"
            return ToolResult(success=True, output={"show": show})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            if repo:
                repo.close()

class CodeRepoMetadataTool(BaseTool):
    name: str = "code_repo_metadata"
    description: str = "Get basic metadata about a local repository (branch, package files, etc)."
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
            meta = {"path": str(safe_path)}
            try:
                repo = git.Repo(safe_path)
                meta["active_branch"] = repo.active_branch.name
                meta["is_dirty"] = repo.is_dirty()
            except:
                meta["git"] = "Not a valid git repository or detached HEAD."
                
            config_files = []
            for f in ["package.json", "requirements.txt", "pyproject.toml", "Cargo.toml", "pom.xml", "go.mod"]:
                if (safe_path / f).exists():
                    config_files.append(f)
            meta["detected_configs"] = config_files
            
            return ToolResult(success=True, output=meta)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
        finally:
            if repo:
                repo.close()

class GithubRepoInfoTool(BaseTool):
    name: str = "github_repo_info"
    description: str = "Get read-only GitHub repository metadata (requires token to avoid rate limits)."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "repo_name": {"type": "string", "description": "e.g., octocat/Hello-World"}
        },
        "required": ["repo_name"]
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        repo_name = kwargs.get("repo_name")
        token = settings.GITHUB_ACCESS_TOKEN
        
        try:
            g = Github(token) if token else Github()
            repo = g.get_repo(repo_name)
            data = {
                "name": repo.full_name,
                "description": repo.description,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count,
                "language": repo.language,
                "default_branch": repo.default_branch,
                "html_url": repo.html_url
            }
            return ToolResult(success=True, output=data)
        except GithubException as e:
            return ToolResult(success=False, error=f"GitHub API Error: {e.data}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
