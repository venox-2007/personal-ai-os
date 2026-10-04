import pytest
import httpx
import socket
from unittest.mock import patch, MagicMock, AsyncMock

from app.tools.research.fetcher import WebFetcher, SecurityException
from app.tools.research.provider import DuckDuckGoProvider, normalize_url
from app.tools.research.tools import (
    ResearchSearchTool, ResearchFetchSourceTool, ResearchExtractEvidenceTool
)

def test_normalize_url():
    assert normalize_url("HTTPS://Example.COM/Path/?track=1#frag") == "https://example.com/Path?track=1"
    assert normalize_url("http://example.com/") == "http://example.com/"
    assert normalize_url("http://example.com") == "http://example.com/"

@pytest.mark.asyncio
async def test_duckduckgo_provider_deduplication():
    provider = DuckDuckGoProvider()
    provider.ddgs = MagicMock()
    provider.ddgs.text.return_value = [
        {"title": "Test 1", "href": "http://test.com/a", "body": "Snippet"},
        {"title": "Test 2", "href": "HTTP://TEST.com/a/", "body": "Snippet duplicate"},
        {"title": "Test 3", "href": "http://test.com/b", "body": "Snippet"}
    ]
    
    results = await provider.search("query", 5)
    # The second one should be deduplicated
    assert len(results) == 2
    assert results[0]["url"] == "http://test.com/a"
    assert results[1]["url"] == "http://test.com/b"

def test_web_fetcher_security_validation():
    fetcher = WebFetcher()
    
    # Mock socket.getaddrinfo to simulate IP resolutions
    def mock_getaddrinfo(host, port, *args, **kwargs):
        if host == "good.com":
            return [(2, 1, 6, '', ('93.184.216.34', port))]
        elif host == "local.dev":
            return [(2, 1, 6, '', ('127.0.0.1', port))]
        elif host == "internal.corp":
            return [(2, 1, 6, '', ('10.0.0.5', port))]
        elif host == "linklocal":
            return [(2, 1, 6, '', ('169.254.169.254', port))]
        elif host == "ipv6local":
            return [(10, 1, 6, '', ('fe80::1', port))]
        else:
            raise socket.gaierror("Name or service not known")

    with patch("socket.getaddrinfo", side_effect=mock_getaddrinfo):
        # Good URL
        fetcher._validate_url_security("https://good.com")
        
        # Blocked schemas
        with pytest.raises(SecurityException):
            fetcher._validate_url_security("file:///etc/passwd")
        with pytest.raises(SecurityException):
            fetcher._validate_url_security("javascript:alert(1)")
            
        # Hardcoded loopback
        with pytest.raises(SecurityException):
            fetcher._validate_url_security("http://localhost/admin")
            
        # Private IPs and localhost through mock DNS
        with pytest.raises(SecurityException):
            fetcher._validate_url_security("http://local.dev")
        with pytest.raises(SecurityException):
            fetcher._validate_url_security("http://internal.corp")
        with pytest.raises(SecurityException):
            fetcher._validate_url_security("http://linklocal")
        with pytest.raises(SecurityException):
            fetcher._validate_url_security("http://ipv6local")

@pytest.mark.asyncio
async def test_evidence_extraction():
    tool = ResearchExtractEvidenceTool()
    
    # Text with 10 paragraphs about apples
    text = "\n".join([f"This is paragraph {i} about apples. It has enough words." for i in range(100)])
    
    res = await tool.execute(source_text=text, source_url="http://test.com", topic="apples")
    assert res.success == True
    assert "evidence" in res.output
    
    # Ensure it's bounded by RESEARCH_MAX_EVIDENCE_CHARS (default 5000 in config)
    total_len = sum(len(e) for e in res.output["evidence"])
    assert total_len <= 5100
    
    # No match
    res_no = await tool.execute(source_text=text, source_url="http://test.com", topic="bananas")
    assert res_no.success == True
    assert res_no.output["evidence"] == "Insufficient evidence found for this topic."

@pytest.mark.asyncio
async def test_research_search_tool_handles_zero_results():
    tool = ResearchSearchTool()
    tool.provider.search = AsyncMock(return_value=[])
    
    res = await tool.execute(query="impossible query that finds nothing")
    assert res.success == True
    assert res.output["results"] == []
    assert "Zero results" in res.output["message"]
