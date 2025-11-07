
"""
Base scraper using urllib (Python built-in, most reliable).
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from bs4 import BeautifulSoup

from ..config.settings import settings
from ..core.exceptions import ScrapingError
from ..core.telemetry import telemetry
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base scraper using urllib - most reliable for encoding."""
    
    def __init__(self, rate_limiter: Optional[RateLimiter] = None, timeout: int = 30, max_retries: int = 3):
        self.rate_limiter = rate_limiter or RateLimiter(default_rate=settings.scraper_rate_limit)
        self.timeout = timeout
        self.max_retries = max_retries
    
    def fetch_url(self, url: str, method: str = "GET", **kwargs):
        """Fetch URL using urllib."""
        domain = self._extract_domain(url)
        self.rate_limiter.acquire(domain)
        
        with telemetry.track_duration("http_request", {"domain": domain}):
            try:
                logger.info(f"Fetching {method} {url}")
                
                # Create request with headers
                req = Request(url, headers={
                    "User-Agent": settings.scraper_user_agent,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate",
                })
                
                # Fetch with timeout
                with urlopen(req, timeout=self.timeout) as response:
                    # Read and decode properly
                    content = response.read()
                    
                    # Decode with UTF-8
                    text = content.decode('utf-8', errors='replace')
                    
                    # Create response object (mimics httpx/requests)
                    class SimpleResponse:
                        def __init__(self, text, status, headers):
                            self.text = text
                            self.status_code = status
                            self.headers = headers
                            self.encoding = 'utf-8'
                        
                        def raise_for_status(self):
                            if self.status_code >= 400:
                                raise Exception(f"HTTP {self.status_code}")
                    
                    resp = SimpleResponse(text, response.status, dict(response.headers))
                    
                    logger.info(f"✓ Fetched {len(text)} chars")
                    
                    return resp
            
            except (HTTPError, URLError) as e:
                raise ScrapingError(f"Request failed: {e}")
            except Exception as e:
                raise ScrapingError(f"Unexpected error: {e}")
    
    def parse_html(self, html: str, parser: str = "html.parser") -> BeautifulSoup:
        """Parse HTML."""
        return BeautifulSoup(html, parser)
    
    def extract_text(self, soup: BeautifulSoup, clean: bool = True) -> str:
        """Extract clean text."""
        # Remove unwanted tags
        for tag in soup(["script", "style", "noscript", "meta"]):
            tag.decompose()
        
        # Get text
        text = soup.get_text(separator="\n")
        
        # Clean encoding
        text = text.encode('utf-8', errors='ignore').decode('utf-8')
        
        if clean:
            lines = [line.strip() for line in text.splitlines()]
            text = "\n".join(line for line in lines if line)
        
        return text
    
    def save_metadata(self, url: str, content_length: int, status_code: int = 200) -> Dict[str, Any]:
        return {
            "source_url": url,
            "crawled_at": datetime.utcnow().isoformat() + "Z",
            "content_length_bytes": content_length,
            "status_code": status_code
        }
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc or parsed.path
    
    @abstractmethod
    def scrape(self, url: str) -> Dict[str, Any]:
        pass
    
    def close(self):
        pass  # urllib doesn't need cleanup
