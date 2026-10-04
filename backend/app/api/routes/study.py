from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from pydantic import BaseModel
from app.tools.registry import tool_registry

router = APIRouter(prefix="/study", tags=["Study"])

class IngestRequest(BaseModel):
    file_path: str

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

class AskRequest(BaseModel):
    question: str

class RemoveRequest(BaseModel):
    document_id: str

@router.post("/ingest")
async def ingest_document(req: IngestRequest):
    tool = tool_registry.get("study_ingest_document")
    if not tool:
        raise HTTPException(status_code=500, detail="Tool not found")
    result = await tool.execute(file_path=req.file_path)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.output

@router.post("/search")
async def search_documents(req: SearchRequest):
    tool = tool_registry.get("study_search")
    if not tool:
        raise HTTPException(status_code=500, detail="Tool not found")
    result = await tool.execute(query=req.query, top_k=req.top_k)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.output

@router.get("/list")
async def list_documents():
    tool = tool_registry.get("study_list_documents")
    if not tool:
        raise HTTPException(status_code=500, detail="Tool not found")
    result = await tool.execute()
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.output

@router.delete("/remove")
async def remove_document(req: RemoveRequest):
    tool = tool_registry.get("study_remove_document")
    if not tool:
        raise HTTPException(status_code=500, detail="Tool not found")
    result = await tool.execute(document_id=req.document_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.output

# study_ask requires context (llm_provider). For direct API call, it might fail unless we mock or provide it.
# We'll rely on the Orchestrator/Chat loop for Ask, or we can instantiate LLM provider here.
@router.post("/ask")
async def ask_question(req: AskRequest):
    from app.integrations.ollama_provider import OllamaProvider
    tool = tool_registry.get("study_ask")
    if not tool:
        raise HTTPException(status_code=500, detail="Tool not found")
        
    class MockContext:
        def __init__(self):
            self.llm_provider = OllamaProvider()
            
    result = await tool.execute(question=req.question, context=MockContext())
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.output
