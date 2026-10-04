from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from app.tools.registry import tool_registry

router = APIRouter(prefix="/research", tags=["Research"])

class SearchRequest(BaseModel):
    query: str
    max_results: int = 5

class FetchRequest(BaseModel):
    url: str

class EvidenceRequest(BaseModel):
    source_text: str
    topic: str

@router.post("/search")
async def search_web(req: SearchRequest):
    tool = tool_registry.get("research_search")
    if not tool: raise HTTPException(status_code=500, detail="Tool not registered")
    result = await tool.execute(query=req.query, max_results=req.max_results)
    if not result.success: raise HTTPException(status_code=400, detail=result.error)
    return result.output

@router.post("/fetch")
async def fetch_source(req: FetchRequest):
    tool = tool_registry.get("research_fetch_source")
    result = await tool.execute(url=req.url)
    if not result.success: raise HTTPException(status_code=400, detail=result.error)
    return result.output

@router.post("/evidence")
async def extract_evidence(req: EvidenceRequest):
    tool = tool_registry.get("research_extract_evidence")
    result = await tool.execute(source_text=req.source_text, topic=req.topic)
    if not result.success: raise HTTPException(status_code=400, detail=result.error)
    return result.output
