from typing import Dict, Any, List
import logging
from app.tools.base import BaseTool, ToolResult, PermissionLevel
from app.core.config import settings
from .provider import DuckDuckGoProvider
from .fetcher import WebFetcher, SecurityException

logger = logging.getLogger(__name__)

class ResearchSearchTool(BaseTool):
    name: str = "research_search"
    description: str = "Search the web for information. Returns normalized URLs with snippets."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "description": "Max results to return"}
        },
        "required": ["query"]
    }
    
    def __init__(self):
        super().__init__()
        self.provider = DuckDuckGoProvider()
        
    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query")
        max_results = min(kwargs.get("max_results", 5), settings.RESEARCH_MAX_SEARCH_RESULTS)
        
        try:
            results = await self.provider.search(query, max_results)
            if not results:
                return ToolResult(success=True, output={"query": query, "results": [], "message": "Zero results found."})
            return ToolResult(success=True, output={"query": query, "results": results})
        except Exception as e:
            return ToolResult(success=False, error=f"Search provider unavailable or failed: {str(e)}")

class ResearchFetchSourceTool(BaseTool):
    name: str = "research_fetch_source"
    description: str = "Fetch and extract text content from a single URL safely."
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
            logger.warning(f"Security exception fetching {url}: {e}")
            return ToolResult(success=False, error=f"Security violation: {str(e)}")
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return ToolResult(success=False, error=f"Fetch failed: {str(e)}")

class ResearchExtractEvidenceTool(BaseTool):
    name: str = "research_extract_evidence"
    description: str = "Extract relevant evidence from fetched source text given a query."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "source_text": {"type": "string"},
            "source_url": {"type": "string", "description": "Identity of the source"},
            "topic": {"type": "string"}
        },
        "required": ["source_text", "source_url", "topic"]
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        text = kwargs.get("source_text", "")
        url = kwargs.get("source_url", "unknown")
        topic = kwargs.get("topic", "").lower()
        
        if not text:
            return ToolResult(success=False, error="Source text is empty.")
            
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        evidence = []
        topic_words = {w.lower() for w in topic.split() if len(w) > 3}
        current_chars = 0
        max_chars = settings.RESEARCH_MAX_EVIDENCE_CHARS
        
        for p in paragraphs:
            p_lower = p.lower()
            # If any topic word is in the paragraph
            if any(w in p_lower for w in topic_words):
                if current_chars + len(p) <= max_chars:
                    evidence.append(p)
                    current_chars += len(p)
                else:
                    # Truncate final paragraph if needed
                    remaining = max_chars - current_chars
                    if remaining > 50:
                        evidence.append(p[:remaining] + "...")
                        current_chars += remaining
                    break
                    
        if not evidence:
            return ToolResult(success=True, output={"source_url": url, "evidence": "Insufficient evidence found for this topic."})
            
        return ToolResult(success=True, output={"source_url": url, "evidence": evidence, "total_chars": current_chars})
