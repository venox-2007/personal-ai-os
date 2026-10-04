from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging
import asyncio
from urllib.parse import urlparse, urlunparse

from app.core.config import settings

logger = logging.getLogger(__name__)

class BaseSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        pass

def normalize_url(url: str) -> str:
    """Normalize URL by lowering scheme/host, stripping fragment, and trailing slash."""
    try:
        parsed = urlparse(url)
        # Scheme and netloc to lowercase
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path
        if path.endswith('/'):
            path = path[:-1]
        if not path:
            path = '/'
            
        # Reconstruct without fragment and params for simple deduplication
        # (Be careful with query strings, but many tracking params are in query. We will keep query but sort it? 
        # Actually, just strip fragment and normalize scheme/host/path).
        normalized = urlunparse((scheme, netloc, path, parsed.params, parsed.query, ""))
        return normalized
    except Exception:
        return url

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
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, 
                lambda: list(self.ddgs.text(query, max_results=max_results * 2)) # Fetch extra for deduplication
            )
            
            normalized_results = []
            seen_urls = set()
            
            for r in results:
                raw_url = r.get("href", "")
                if not raw_url:
                    continue
                    
                norm_url = normalize_url(raw_url)
                if norm_url in seen_urls:
                    continue
                    
                seen_urls.add(norm_url)
                
                normalized_results.append({
                    "title": r.get("title", "").strip(),
                    "url": raw_url,
                    "snippet": r.get("body", "").strip(),
                })
                
                if len(normalized_results) >= max_results:
                    break
                    
            return normalized_results
            
        except Exception as e:
            logger.error(f"DDG Search failed: {e}")
            return []
