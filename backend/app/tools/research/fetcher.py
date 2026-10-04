import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import ipaddress
import socket
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class SecurityException(Exception):
    pass

class WebFetcher:
    def __init__(self):
        self.max_size = settings.RESEARCH_MAX_SOURCE_SIZE_MB * 1024 * 1024
        
    def _is_safe_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ["http", "https"]:
                return False
                
            hostname = parsed.hostname
            if not hostname:
                return False
                
            # Block localhost and obvious private IPs
            if hostname in ["localhost", "127.0.0.1", "::1"]:
                return False
                
            # Try resolving to check IP
            try:
                ip = socket.gethostbyname(hostname)
                ip_obj = ipaddress.ip_address(ip)
                if ip_obj.is_private or ip_obj.is_loopback:
                    return False
            except Exception:
                pass # If it doesn't resolve easily, let httpx handle it or fail, but we did our best
                
            return True
        except Exception:
            return False

    async def fetch_and_extract(self, url: str) -> dict:
        if not self._is_safe_url(url):
            raise SecurityException(f"URL is not allowed: {url}")
            
        headers = {"User-Agent": settings.RESEARCH_USER_AGENT}
        
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, max_redirects=3) as client:
            try:
                # We use stream to check content length and type before downloading entirely
                async with client.stream("GET", url, headers=headers) as response:
                    response.raise_for_status()
                    
                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type and "text/plain" not in content_type:
                        return {"url": url, "error": f"Unsupported content type: {content_type}"}
                        
                    content_length = int(response.headers.get("content-length", 0))
                    if content_length > self.max_size:
                        return {"url": url, "error": f"File too large: {content_length} bytes"}
                        
                    # Read cautiously
                    chunks = []
                    bytes_read = 0
                    async for chunk in response.aiter_bytes():
                        bytes_read += len(chunk)
                        if bytes_read > self.max_size:
                            return {"url": url, "error": "Content exceeded maximum size during download."}
                        chunks.append(chunk)
                        
                    html_content = b"".join(chunks).decode("utf-8", errors="ignore")
                    
                    # Extract text
                    soup = BeautifulSoup(html_content, "html.parser")
                    
                    # Remove noise
                    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        element.decompose()
                        
                    title = soup.title.string if soup.title else ""
                    text = soup.get_text(separator="\n", strip=True)
                    
                    # Normalize text slightly
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = "\n".join(chunk for chunk in chunks if chunk)
                    
                    return {
                        "url": str(response.url), # the resolved URL
                        "title": title.strip(),
                        "text": text[:20000] # Cap text size
                    }
                    
            except httpx.HTTPError as e:
                return {"url": url, "error": f"HTTP error: {str(e)}"}
            except Exception as e:
                return {"url": url, "error": f"Error: {str(e)}"}
