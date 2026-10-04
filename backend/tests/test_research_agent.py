import pytest
import httpx
from unittest.mock import patch, MagicMock

from app.tools.research.fetcher import WebFetcher, SecurityException
from app.tools.research.provider import DuckDuckGoProvider
from app.tools.research.tools import (
    ResearchSearchTool, ResearchFetchSourceTool, ResearchExtractEvidenceTool
)

@pytest.mark.asyncio
async def test_duckduckgo_provider_mocked():
    provider = DuckDuckGoProvider()
    provider.ddgs = MagicMock()
    provider.ddgs.text.return_value = [
        {"title": "Test", "href": "http://test.com", "body": "Snippet"}
    ]
    
    results = await provider.search("query", 1)
    assert len(results) == 1
    assert results[0]["title"] == "Test"
    assert results[0]["url"] == "http://test.com"
    assert results[0]["snippet"] == "Snippet"

def test_web_fetcher_security():
    fetcher = WebFetcher()
    
    assert fetcher._is_safe_url("https://google.com") == True
    assert fetcher._is_safe_url("http://google.com") == True
    
    # SSRF / Local blocks
    assert fetcher._is_safe_url("http://localhost:8000") == False
    assert fetcher._is_safe_url("http://127.0.0.1/admin") == False
    assert fetcher._is_safe_url("file:///etc/passwd") == False
    assert fetcher._is_safe_url("javascript:alert(1)") == False
    assert fetcher._is_safe_url("ftp://server") == False

@pytest.mark.asyncio
async def test_fetch_source_tool_mocked(monkeypatch):
    tool = ResearchFetchSourceTool()
    
    async def mock_fetch(url):
        if url == "http://bad.local":
            raise SecurityException("Blocked")
        return {"url": url, "title": "Mock Title", "text": "Mock content body."}
        
    monkeypatch.setattr(tool.fetcher, "fetch_and_extract", mock_fetch)
    
    res = await tool.execute(url="https://good.com")
    assert res.success == True
    assert res.output["title"] == "Mock Title"
    
    res = await tool.execute(url="http://bad.local")
    assert res.success == False
    assert "Blocked" in res.error

@pytest.mark.asyncio
async def test_evidence_extraction():
    tool = ResearchExtractEvidenceTool()
    text = "This is a paragraph about apples.\nHere is another about bananas.\nApples are red."
    
    res = await tool.execute(source_text=text, topic="apples")
    assert res.success == True
    assert len(res.output["evidence"]) == 2
    assert "apples" in res.output["evidence"][0].lower()
