from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)

class BaseSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        pass

class DuckDuckGoProvider(BaseSearchProvider):
    def __init__(self):
        try:
            from duckduckgo_search import DDGS
            self.ddgs = DDGS()
        except ImportError:
            self.ddgs = None
            logger.error("duckduckgo_search not installed.")

    async def search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        if not self.ddgs:
            return []
            
        try:
            # duckduckgo_search blocks on IO, so run in executor
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, 
                lambda: list(self.ddgs.text(query, max_results=max_results))
            )
            
            normalized = []
            for r in results:
                normalized.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
            return normalized
        except Exception as e:
            logger.error(f"DDG Search failed: {e}")
            return []
