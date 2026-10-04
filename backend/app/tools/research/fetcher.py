import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import ipaddress
import socket
import logging
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)

class SecurityException(Exception):
    pass

class WebFetcher:
    def __init__(self):
        self.max_size = settings.RESEARCH_MAX_SOURCE_SIZE_MB * 1024 * 1024
        self.max_redirects = settings.RESEARCH_MAX_REDIRECTS
        self.timeout = settings.RESEARCH_REQUEST_TIMEOUT_SECONDS
        self.max_extracted_chars = settings.RESEARCH_MAX_EXTRACTED_CHARS
        
    def _validate_url_security(self, url: str) -> None:
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ["http", "https"]:
                raise SecurityException(f"Unsupported scheme: {parsed.scheme}")
                
            hostname = parsed.hostname
            if not hostname:
                raise SecurityException("No hostname in URL")
                
            if hostname in ["localhost", "127.0.0.1", "::1"]:
                raise SecurityException("Localhost explicitly blocked")
                
            try:
                # getaddrinfo resolves both IPv4 and IPv6
                addrs = socket.getaddrinfo(hostname, None)
                for addr in addrs:
                    ip = addr[4][0]
                    ip_obj = ipaddress.ip_address(ip)
                    if (ip_obj.is_private or ip_obj.is_loopback or 
                        ip_obj.is_link_local or ip_obj.is_multicast or 
                        ip_obj.is_reserved or ip_obj.is_unspecified):
                        raise SecurityException(f"URL resolves to restricted IP range: {ip}")
            except socket.gaierror:
                raise SecurityException(f"Failed to resolve hostname: {hostname}")
                
        except ValueError as e:
            raise SecurityException(f"Malformed URL: {url}")

    async def fetch_and_extract(self, url: str) -> dict:
        headers = {"User-Agent": settings.RESEARCH_USER_AGENT}
        
        current_url = url
        redirects = 0
        
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
            while redirects <= self.max_redirects:
                try:
                    self._validate_url_security(current_url)
                except SecurityException as e:
                    return {"url": current_url, "error": str(e)}

                try:
                    async with client.stream("GET", current_url, headers=headers) as response:
                        if 300 <= response.status_code < 400:
                            location = response.headers.get("Location")
                            if not location:
                                return {"url": current_url, "error": "Redirect without Location header"}
                            current_url = urljoin(current_url, location)
                            redirects += 1
                            continue

                        response.raise_for_status()
                        
                        content_type = response.headers.get("content-type", "").lower()
                        if not ("text/html" in content_type or "text/plain" in content_type or "application/xhtml+xml" in content_type):
                            return {"url": current_url, "error": f"Unsupported content type: {content_type}"}
                            
                        content_length = int(response.headers.get("content-length", 0))
                        if content_length > self.max_size:
                            return {"url": current_url, "error": f"File too large: {content_length} bytes"}
                            
                        chunks = []
                        bytes_read = 0
                        async for chunk in response.aiter_bytes():
                            bytes_read += len(chunk)
                            if bytes_read > self.max_size:
                                return {"url": current_url, "error": "Content exceeded maximum size during download"}
                            chunks.append(chunk)
                            
                        html_content = b"".join(chunks).decode("utf-8", errors="ignore")
                        
                        soup = BeautifulSoup(html_content, "html.parser")
                        
                        # Remove noise
                        for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]):
                            element.decompose()
                            
                        title = soup.title.string if soup.title else ""
                        
                        # Better extraction
                        main_content = soup.find("main") or soup.find("article") or soup.body or soup
                        text = main_content.get_text(separator="\n", strip=True)
                        
                        lines = (line.strip() for line in text.splitlines())
                        chunks_text = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = "\n".join(chunk for chunk in chunks_text if chunk)
                        
                        return {
                            "url": str(response.url),
                            "title": title.strip() if title else "",
                            "text": text[:self.max_extracted_chars]
                        }
                        
                except httpx.HTTPError as e:
                    return {"url": current_url, "error": f"HTTP error: {str(e)}"}
                except Exception as e:
                    return {"url": current_url, "error": f"Error: {str(e)}"}
            
            return {"url": current_url, "error": f"Exceeded maximum redirects ({self.max_redirects})"}
