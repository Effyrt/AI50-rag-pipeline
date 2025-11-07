
"""
Selenium scraper that ACTUALLY works.
"""
import logging
from typing import Dict, Any
from datetime import datetime
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SeleniumScraper:
    """Selenium scraper that handles JavaScript-heavy sites."""
    
    def __init__(self, headless: bool = True):
        """Initialize Chrome WebDriver."""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)")
        
        # Disable images for speed
        prefs = {"profile.managed_default_content_settings.images": 2}
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            logger.info("✅ Selenium WebDriver initialized")
        except Exception as e:
            logger.error(f"Failed to init Selenium: {e}")
            raise
    
    def scrape(self, url: str, wait_seconds: int = 3) -> Dict[str, Any]:
        """
        Scrape URL with JavaScript rendering.
        
        Args:
            url: URL to scrape
            wait_seconds: Seconds to wait for JS to load
            
        Returns:
            Dictionary with clean text
        """
        try:
            logger.info(f"Selenium scraping: {url}")
            
            # Load page
            self.driver.get(url)
            
            # Wait for JavaScript to load
            time.sleep(wait_seconds)
            
            # Get rendered HTML
            html = self.driver.page_source
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove junk
            for tag in soup(["script", "style", "noscript", "meta", "link", "svg"]):
                tag.decompose()
            
            # Get clean text
            text = soup.get_text(separator="\n")
            
            # Clean whitespace
            lines = [line.strip() for line in text.splitlines()]
            text = "\n".join(line for line in lines if line and len(line) > 2)
            
            logger.info(f"✅ Selenium extracted {len(text)} chars from {url}")
            
            return {
                "url": url,
                "html": html,
                "text": text,
                "scraper": "selenium",
                "content_length": len(text)
            }
        
        except Exception as e:
            logger.error(f"Selenium scraping failed: {e}")
            return {
                "url": url,
                "error": str(e),
                "scraper": "selenium_failed"
            }
    
    def close(self):
        """Close driver."""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium driver closed")
            except Exception as e:
                logger.warning(f"Error closing Selenium: {e}")
