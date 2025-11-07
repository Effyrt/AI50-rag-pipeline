"""
Multi-page company website scraper with Selenium support.
"""
import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse

from .base import BaseScraper
from .selenium_scraper_fixed import SeleniumScraper
from ..config.settings import settings
from ..core.exceptions import ScrapingError
from ..core.telemetry import track_time

logger = logging.getLogger(__name__)


class CompanyScraper(BaseScraper):
    """
    Scraper for individual company websites with Selenium fallback.
    
    Scrapes multiple pages:
    - Homepage
    - About page
    - Product/Platform page
    - Careers page
    - Blog/News page
    """
    
    # Common URL patterns for company pages
    PAGE_PATTERNS = {
        "about": ["about", "about-us", "company", "who-we-are"],
        "product": ["product", "products", "platform", "solutions", "technology"],
        "careers": ["careers", "jobs", "join", "join-us", "work-with-us"],
        "blog": ["blog", "news", "newsroom", "press", "media"],
    }
    
    def __init__(self, use_selenium: bool = True, **kwargs):
        """
        Initialize company scraper.
        
        Args:
            use_selenium: Whether to use Selenium for JS-heavy sites
            **kwargs: Additional arguments for BaseScraper
        """
        super().__init__(**kwargs)
        self.use_selenium = use_selenium
        
        if use_selenium:
            try:
                self.selenium = SeleniumScraper(headless=True)
                logger.info("✓ Selenium enabled for JS-heavy sites")
            except Exception as e:
                logger.warning(f"Selenium not available: {e}")
                self.selenium = None
        else:
            self.selenium = None
    
    @track_time("company_scrape")
    def scrape(self, company_id: str, company_name: str, website: str) -> Dict[str, Any]:
        """
        Scrape all relevant pages for a company.
        
        Args:
            company_id: Unique company identifier
            company_name: Company name
            website: Company website URL
            
        Returns:
            Dictionary with scraped data for all pages
        """
        logger.info(f"Scraping {company_name} ({website})")
        
        result = {
            "company_id": company_id,
            "company_name": company_name,
            "website": website,
            "scraped_at": datetime.utcnow().isoformat() + "Z",
            "pages": {}
        }
        
        try:
            # Normalize website URL
            if not website.startswith(("http://", "https://")):
                website = f"https://{website}"
            
            # Scrape homepage
            logger.info(f"Scraping homepage: {website}")
            homepage_data = self._scrape_page(website, "homepage")
            result["pages"]["homepage"] = homepage_data
            
            # Discover and scrape other pages
            discovered_urls = self._discover_urls(website, homepage_data.get("soup"))
            
            for page_type in ["about", "product", "careers", "blog"]:
                url = discovered_urls.get(page_type)
                
                if url:
                    logger.info(f"Scraping {page_type} page: {url}")
                    page_data = self._scrape_page(url, page_type)
                    result["pages"][page_type] = page_data
                else:
                    logger.warning(f"No {page_type} page found for {company_name}")
                    result["pages"][page_type] = None
            
            # Save raw HTML and clean text
            self._save_scraped_data(company_id, result)
            
            logger.info(f"Successfully scraped {len(result['pages'])} pages for {company_name}")
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to scrape {company_name}: {e}", exc_info=True)
            raise ScrapingError(
                f"Company scraping failed for {company_name}: {e}",
                error_code="COMPANY_SCRAPE_FAILED",
                details={"company_id": company_id, "website": website, "error": str(e)}
            )
    
    def _scrape_page(self, url: str, page_type: str) -> Dict[str, Any]:
        """
        Scrape a single page using best available method.
        
        Tries Selenium first (handles JavaScript), then falls back to HTTP.
        
        Args:
            url: Page URL
            page_type: Type of page
            
        Returns:
            Dictionary with page data
        """
        # Strategy 1: Try Selenium first if available (handles JS)
        if self.selenium:
            try:
                logger.info(f"Using Selenium for {page_type}")
                result = self.selenium.scrape(url, wait_seconds=3)
                
                if "error" not in result and len(result.get("text", "")) > 500:
                    logger.info(f"✓ Selenium extracted {len(result['text'])} chars")
                    
                    # Parse for URL discovery
                    soup = self.parse_html(result["html"])
                    
                    return {
                        "url": url,
                        "page_type": page_type,
                        "html": result["html"],
                        "text": result["text"],
                        "metadata": {},
                        "status_code": 200,
                        "content_length": len(result["text"]),
                        "scraped_at": datetime.utcnow().isoformat() + "Z",
                        "scraper": "selenium",
                        "soup": soup  # For URL discovery
                    }
                else:
                    logger.warning(f"Selenium got insufficient content, trying HTTP fallback")
            
            except Exception as e:
                logger.warning(f"Selenium failed for {page_type}: {e}, trying HTTP fallback")
        
        # Strategy 2: Fallback to HTTP
        try:
            logger.info(f"Using HTTP for {page_type}")
            response = self.fetch_url(url)
            soup = self.parse_html(response.text)
            text = self.extract_text(soup, clean=True)
            
            # Extract metadata
            metadata = self._extract_page_metadata(soup, url)
            
            return {
                "url": url,
                "page_type": page_type,
                "html": response.text,
                "text": text,
                "metadata": metadata,
                "status_code": response.status_code,
                "content_length": len(response.text),
                "scraped_at": datetime.utcnow().isoformat() + "Z",
                "scraper": "http",
                "soup": soup
            }
        
        except Exception as e:
            logger.error(f"Failed to scrape {page_type} page {url}: {e}")
            return {
                "url": url,
                "page_type": page_type,
                "error": str(e),
                "scraped_at": datetime.utcnow().isoformat() + "Z"
            }
    
    def _discover_urls(self, base_url: str, soup) -> Dict[str, str]:
        """
        Discover URLs for different page types.
        
        Args:
            base_url: Base website URL
            soup: BeautifulSoup object of homepage
            
        Returns:
            Dictionary mapping page types to URLs
        """
        if not soup:
            return {}
        
        discovered = {}
        
        # Find all links
        links = soup.find_all("a", href=True)
        
        for page_type, patterns in self.PAGE_PATTERNS.items():
            for link in links:
                href = link["href"].lower()
                
                # Check if link matches any pattern
                if any(pattern in href for pattern in patterns):
                    # Convert relative URL to absolute
                    full_url = urljoin(base_url, link["href"])
                    
                    # Ensure it's same domain
                    if self._same_domain(base_url, full_url):
                        discovered[page_type] = full_url
                        break
        
        return discovered
    
    def _extract_page_metadata(self, soup, url: str) -> Dict[str, Any]:
        """Extract metadata from page."""
        metadata = {"source_url": url}
        
        # Extract title
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)
        
        # Extract meta description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag:
            metadata["description"] = desc_tag.get("content", "")
        
        # Extract Open Graph data
        og_tags = soup.find_all("meta", attrs={"property": lambda x: x and x.startswith("og:")})
        og_data = {}
        for tag in og_tags:
            prop = tag.get("property", "").replace("og:", "")
            content = tag.get("content", "")
            if prop and content:
                og_data[prop] = content
        
        if og_data:
            metadata["open_graph"] = og_data
        
        return metadata
    
    @staticmethod
    def _same_domain(url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain."""
        domain1 = urlparse(url1).netloc
        domain2 = urlparse(url2).netloc
        return domain1 == domain2
    
    def _save_scraped_data(self, company_id: str, data: Dict[str, Any]):
        """
        Save scraped data to disk with proper encoding.
        
        Args:
            company_id: Company identifier
            data: Scraped data dictionary
        """
        # Create company directory
        company_dir = settings.raw_data_dir / company_id
        company_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped subdirectory
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        run_dir = company_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Save metadata
        metadata = {
            "company_id": data["company_id"],
            "company_name": data["company_name"],
            "website": data["website"],
            "scraped_at": data["scraped_at"],
            "pages_scraped": list(data["pages"].keys())
        }
        
        with open(run_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        # Save each page
        for page_type, page_data in data["pages"].items():
            if page_data is None or "error" in page_data:
                continue
            
            page_dir = run_dir / page_type
            page_dir.mkdir(exist_ok=True)
            
            # Save raw HTML
            with open(page_dir / "raw.html", "w", encoding="utf-8") as f:
                f.write(page_data["html"])
            
            # Save clean text - FORCE UTF-8
            with open(page_dir / "clean.txt", "w", encoding="utf-8") as f:
                f.write(page_data["text"])
            
            # Save page metadata
            page_meta = {
                "url": page_data["url"],
                "page_type": page_data["page_type"],
                "status_code": page_data.get("status_code", 200),
                "content_length": page_data["content_length"],
                "scraped_at": page_data["scraped_at"],
                "scraper_used": page_data.get("scraper", "unknown"),
                "metadata": page_data.get("metadata", {})
            }
            
            with open(page_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(page_meta, f, indent=2)
        
        logger.info(f"Saved scraped data to {run_dir}")
    
    def close(self):
        """Close both HTTP client and Selenium driver."""
        super().close()
        if self.selenium:
            self.selenium.close()