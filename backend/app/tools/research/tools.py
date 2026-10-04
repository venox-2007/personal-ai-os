from typing import Dict, Any, List
from app.tools.base import BaseTool, ToolResult, PermissionLevel
from app.core.config import settings
from .provider import DuckDuckGoProvider
from .fetcher import WebFetcher, SecurityException

class ResearchSearchTool(BaseTool):
    name: str = "research_search"
    description: str = "Search the web for information."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "description": "Max results to return (default 5, max configured limit)"}
        },
        "required": ["query"]
    }
    
    def __init__(self):
        super().__init__()
        self.provider = DuckDuckGoProvider()
        
    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query")
        max_results = min(kwargs.get("max_results", 5), settings.RESEARCH_MAX_SEARCH_RESULTS)
        
        results = await self.provider.search(query, max_results)
        return ToolResult(success=True, output={"query": query, "results": results})

class ResearchFetchSourceTool(BaseTool):
    name: str = "research_fetch_source"
    description: str = "Fetch and extract text content from a URL."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "url": {"type": "string"}
        },
        "required": ["url"]
    }
    
    def __init__(self):
        super().__init__()
        self.fetcher = WebFetcher()
        
    async def execute(self, **kwargs) -> ToolResult:
        url = kwargs.get("url")
        try:
            result = await self.fetcher.fetch_and_extract(url)
            if "error" in result:
                return ToolResult(success=False, error=result["error"])
            return ToolResult(success=True, output=result)
        except SecurityException as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class ResearchExtractEvidenceTool(BaseTool):
    name: str = "research_extract_evidence"
    description: str = "Extract relevant evidence from fetched source text given a query."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "source_text": {"type": "string"},
            "topic": {"type": "string"}
        },
        "required": ["source_text", "topic"]
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        # In a real heavy system this might use embeddings/LLM. 
        # For Phase 6A, we'll do simple keyword windowing or just return a snippet.
        # To avoid overhead, we rely on the agent to pass source_text (which might be too large).
        # Actually, if we just truncate and return, the orchestrator's LLM does the synthesis.
        text = kwargs.get("source_text", "")
        topic = kwargs.get("topic", "").lower()
        
        # Simple extraction: find paragraphs mentioning topic words
        paragraphs = text.split("\n")
        evidence = []
        topic_words = set(topic.split())
        
        for p in paragraphs:
            p_lower = p.lower()
            if any(w in p_lower for w in topic_words if len(w) > 3):
                if len(evidence) < 5:
                    evidence.append(p.strip())
                    
        if not evidence:
            evidence = paragraphs[:5] # fallback to beginning
            
        return ToolResult(success=True, output={"evidence": evidence})
