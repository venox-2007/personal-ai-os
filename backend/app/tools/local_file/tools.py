import os
import glob
from pathlib import Path
from typing import Dict, Any, List
import stat
import time

from app.tools.base import BaseTool, ToolResult, PermissionLevel
from app.tools.local_file.sandbox import sandbox, SecurityException
from app.core.logging import logger

class FileSearchTool(BaseTool):
    name: str = "file_search"
    description: str = "Search for files within allowed directories matching a pattern."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "The directory path to search in (must be within allowed roots)."
            },
            "pattern": {
                "type": "string",
                "description": "A glob pattern to search for, e.g., '*.md' or '**/*.py'."
            }
        },
        "required": ["directory", "pattern"]
    }
        
    async def execute(self, **arguments) -> ToolResult:
        directory = arguments.get("directory")
        pattern = arguments.get("pattern")
        
        if not directory or not pattern:
            return ToolResult(success=False, error="Missing required arguments: directory and pattern.")
            
        try:
            safe_dir = sandbox.get_safe_path(directory)
            if not safe_dir.is_dir():
                return ToolResult(success=False, error=f"Path is not a directory: {directory}")
                
            # Perform search safely
            search_path = str(safe_dir / pattern)
            # Use glob to find files, but we must check each returned path against sandbox
            # because pattern could potentially be like '../../something' (though glob might not resolve it that way).
            matched_files = glob.glob(search_path, recursive=True)
            
            results = []
            for m in matched_files:
                try:
                    m_path = Path(m)
                    if m_path.is_file() and sandbox.is_path_allowed(m_path):
                        results.append(str(m_path))
                except Exception:
                    continue
                    
            # Limit results to avoid massive responses
            max_results = 100
            if len(results) > max_results:
                results = results[:max_results]
                limited = True
            else:
                limited = False
                
            data_dict = {
                "matched_count": len(results),
                "limited": limited,
                "files": results
            }
            return ToolResult(success=True, output=data_dict)
            
        except SecurityException as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error in file_search: {e}")
            return ToolResult(success=False, error=f"An error occurred: {str(e)}")

class FileMetadataTool(BaseTool):
    name: str = "file_metadata"
    description: str = "Get metadata (size, permissions, modification time) for a specific file."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The absolute or relative path to the file."
            }
        },
        "required": ["file_path"]
    }
        
    async def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        if not file_path:
            return ToolResult(success=False, error="Missing required argument: file_path.")
            
        try:
            safe_path = sandbox.get_safe_path(file_path)
            if not safe_path.exists():
                return ToolResult(success=False, error=f"File does not exist: {file_path}")
                
            stats = safe_path.stat()
            metadata = {
                "path": str(safe_path),
                "size_bytes": stats.st_size,
                "is_dir": safe_path.is_dir(),
                "is_file": safe_path.is_file(),
                "created_at": time.ctime(stats.st_ctime),
                "modified_at": time.ctime(stats.st_mtime),
            }
            return ToolResult(success=True, output=metadata)
            
        except SecurityException as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error in file_metadata: {e}")
            return ToolResult(success=False, error=f"An error occurred: {str(e)}")

class FileReadTool(BaseTool):
    name: str = "file_read"
    description: str = "Read the text content of a file. For large files, use start_line and end_line."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The path to the file."
            },
            "start_line": {
                "type": "integer",
                "description": "Optional starting line number (1-indexed)."
            },
            "end_line": {
                "type": "integer",
                "description": "Optional ending line number (inclusive)."
            }
        },
        "required": ["file_path"]
    }
        
    async def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        start_line = kwargs.get("start_line", 1)
        end_line = kwargs.get("end_line", None)
        
        if not file_path:
            return ToolResult(success=False, error="Missing required argument: file_path.")
            
        try:
            safe_path = sandbox.get_safe_path(file_path)
            if not safe_path.is_file():
                return ToolResult(success=False, error=f"Path is not a file or does not exist: {file_path}")
                
            # Basic text reading. Future: pdf/docx support.
            try:
                with open(safe_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                return ToolResult(success=False, error="File appears to be binary or not utf-8 encoded.")
                
            total_lines = len(lines)
            
            # Apply 1-indexed slicing
            start_idx = max(0, start_line - 1)
            end_idx = total_lines if end_line is None else min(total_lines, end_line)
            
            content = "".join(lines[start_idx:end_idx])
            
            # Limit total characters to avoid context overflow
            max_chars = 15000
            truncated = False
            if len(content) > max_chars:
                content = content[:max_chars] + "\n...[CONTENT TRUNCATED]..."
                truncated = True
                
            return ToolResult(success=True, output={
                "path": str(safe_path),
                "total_lines": total_lines,
                "lines_returned": f"{start_idx + 1} to {end_idx}",
                "truncated_by_length": truncated,
                "content": content
            })
            
        except SecurityException as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error in file_read: {e}")
            return ToolResult(success=False, error=f"An error occurred: {str(e)}")

class FileSummarizeTool(BaseTool):
    name: str = "file_summarize"
    description: str = "Summarize the content of a file using the orchestrator LLM."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The path to the file to summarize."
            },
            "prompt": {
                "type": "string",
                "description": "Optional specific question or instruction for the summary."
            }
        },
        "required": ["file_path"]
    }
        
    async def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        prompt = kwargs.get("prompt", "Please provide a concise summary of this file.")
        
        # `context` must be passed via kwargs when called by the agent loop
        context = kwargs.get("context", None)
        
        if not file_path:
            return ToolResult(success=False, error="Missing required argument: file_path.")
            
        if not context or not hasattr(context, "llm_provider"):
            return ToolResult(success=False, error="LLM provider not available in context for summarization.")
            
        try:
            safe_path = sandbox.get_safe_path(file_path)
            if not safe_path.is_file():
                return ToolResult(success=False, error=f"Path is not a file or does not exist: {file_path}")
                
            try:
                with open(safe_path, 'r', encoding='utf-8') as f:
                    content = f.read(15000) # Read up to 15k chars for summary
            except UnicodeDecodeError:
                return ToolResult(success=False, error="File appears to be binary or not utf-8 encoded.")
                
            messages = [
                {"role": "system", "content": "You are a helpful assistant that summarizes file contents."},
                {"role": "user", "content": f"{prompt}\n\nFile Content ({safe_path.name}):\n```\n{content}\n```"}
            ]
            
            response = await context.llm_provider.chat(
                messages=messages,
                temperature=0.3
            )
            
            return ToolResult(success=True, output={
                "path": str(safe_path),
                "summary": response.content
            })
            
        except SecurityException as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error in file_summarize: {e}")
            return ToolResult(success=False, error=f"An error occurred: {str(e)}")
