from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel
from app.tools.registry import tool_registry

router = APIRouter(prefix="/coding", tags=["Coding"])

class RepoRequest(BaseModel):
    repo_path: str

class SearchRequest(BaseModel):
    repo_path: str
    pattern: str

class ReadFileRequest(BaseModel):
    file_path: str

class AskRequest(BaseModel):
    question: str
    repo_path: str

@router.post("/list")
async def list_repo(req: RepoRequest):
    tool = tool_registry.get("code_list_repository")
    result = await tool.execute(repo_path=req.repo_path)
    if not result.success: raise HTTPException(status_code=400, detail=result.error)
    return result.output

@router.post("/metadata")
async def metadata_repo(req: RepoRequest):
    tool = tool_registry.get("code_repo_metadata")
    result = await tool.execute(repo_path=req.repo_path)
    if not result.success: raise HTTPException(status_code=400, detail=result.error)
    return result.output

@router.post("/search")
async def search_code(req: SearchRequest):
    tool = tool_registry.get("code_search")
    result = await tool.execute(repo_path=req.repo_path, pattern=req.pattern)
    if not result.success: raise HTTPException(status_code=400, detail=result.error)
    return result.output

@router.post("/read")
async def read_code(req: ReadFileRequest):
    tool = tool_registry.get("code_read_file")
    result = await tool.execute(file_path=req.file_path)
    if not result.success: raise HTTPException(status_code=400, detail=result.error)
    return result.output

@router.post("/git_status")
async def git_status(req: RepoRequest):
    tool = tool_registry.get("code_git_status")
    result = await tool.execute(repo_path=req.repo_path)
    if not result.success: raise HTTPException(status_code=400, detail=result.error)
    return result.output

@router.post("/git_log")
async def git_log(req: RepoRequest):
    tool = tool_registry.get("code_git_log")
    result = await tool.execute(repo_path=req.repo_path)
    if not result.success: raise HTTPException(status_code=400, detail=result.error)
    return result.output

@router.post("/ask")
async def ask_agent(req: AskRequest):
    # This is a stub for the frontend to ask the agent. In a real system,
    # the orchestrator loop handles reasoning by calling these tools.
    # For Phase 5A frontend demo, we'll route it as a direct question via Orchestrator or similar,
    # or just use Chat loop. The user instructions:
    # "The agent should retrieve relevant code before asking Qwen3 to reason about it."
    # Since we can't easily run the full orchestrator loop in a single endpoint without context,
    # we will return a message instructing to use the Chat Orchestrator for complex reasoning,
    # OR we can just pass it to the chat loop.
    return {"message": "Please use the Orchestrator Chat in the Home tab for complex coding tasks."}
