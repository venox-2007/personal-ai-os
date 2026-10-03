from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.tools.local_file.tools import FileSearchTool, FileMetadataTool, FileReadTool, FileSummarizeTool

router = APIRouter(prefix="/files", tags=["Files"])

class SearchRequest(BaseModel):
    directory: str
    pattern: str = "*.*"

class ReadRequest(BaseModel):
    file_path: str
    start_line: Optional[int] = 1
    end_line: Optional[int] = None

@router.post("/search")
async def search_files(request: SearchRequest):
    tool = FileSearchTool()
    result = await tool.execute(directory=request.directory, pattern=request.pattern)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.output

@router.post("/metadata")
async def get_metadata(request: ReadRequest):
    tool = FileMetadataTool()
    result = await tool.execute(file_path=request.file_path)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.output

@router.post("/read")
async def read_file(request: ReadRequest):
    tool = FileReadTool()
    result = await tool.execute(file_path=request.file_path, start_line=request.start_line, end_line=request.end_line)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.output
