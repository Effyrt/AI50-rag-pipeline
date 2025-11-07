"""
Selenium-based scraper for JavaScript-heavy websites.
"""
import logging
import time
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from .base import BaseScraper
from ..config.settings import settings
from ..core.exceptions import ScrapingError

logger = logging.getLogger(__name__)


class SeleniumScraper(BaseScraper):
    """
    Selenium-based scraper for JavaScript-rendered content.
    
    Falls back to regular HTTP scraper if Selenium is not available.
    """
    
    def __init__(self, headless: bool = True, **kwargs):
        super().__init__(**kwargs)
        
        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium not available, falling back to HTTP scraper")
            self.driver = None
            return
        
        if not settings.enable_selenium:
            logger.info("Selenium disabled in settings")
            self.driver = None
            return
        
        try:
            # Configure Chrome options
            chrome_options = Options()
            
            if headless:
                chrome_options.add_argument("--headless=new")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument(f"user-agent={settings.scraper_user_agent}")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Initialize driver
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
            
            logger.info("Selenium WebDriver initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {e}")
            self.driver = None
    
    def scrape(self, url: str, wait_for_selector: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape URL with Selenium.
        
        Args:
            url: URL to scrape
            wait_for_selector: Optional CSS selector to wait for
            
        Returns:
            Dictionary with scraped data
        """
        if self.driver is None:
            # Fallback to HTTP scraper
            logger.info("Using HTTP fallback for Selenium scraper")
            return self._http_fallback(url)
        
        try:
            logger.info(f"Scraping with Selenium: {url}")
            
            # Load page
            self.driver.get(url)
            
            # Wait for specific element if provided
            if wait_for_selector:
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
                    )
                    logger.info(f"Successfully waited for selector: {wait_for_selector}")
                except TimeoutException:
                    logger.warning(f"Timeout waiting for selector: {wait_for_selector}")
            else:
                # Generic wait for page to load
                time.sleep(2)
            
            # Get page source
            html = self.driver.page_source
            
            # Parse with BeautifulSoup
            soup = self.parse_html(html)
            text = self.extract_text(soup, clean=True)
            
            # Take screenshot (optional)
            screenshot_path = None
            if settings.enable_selenium:
                screenshot_path = self._take_screenshot(url)
            
            return {
                "url": url,
                "html": html,
                "text": text,
                "screenshot": screenshot_path,
                "scraper": "selenium"
            }
        
        except WebDriverException as e:
            logger.error(f"Selenium error for {url}: {e}")
            raise ScrapingError(
                f"Selenium scraping failed: {e}",
                error_code="SELENIUM_ERROR",
                details={"url": url, "error": str(e)}
            )
    
    def _http_fallback(self, url: str) -> Dict[str, Any]:
        """Fallback to regular HTTP scraper."""
        response = self.fetch_url(url)
        soup = self.parse_html(response.text)
        text = self.extract_text(soup, clean=True)
        
        return {
            "url": url,
            "html": response.text,
            "text": text,
            "scraper": "http_fallback"
        }
    
    def _take_screenshot(self, url: str) -> Optional[str]:
        """
        Take screenshot of current page.
        
        Args:
            url: Page URL (for filename)
            
        Returns:
            Path to screenshot file, or None if failed
        """
        try:
            # Create screenshots directory
            screenshot_dir = settings.data_dir / "screenshots"
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename from URL
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace(".", "_")
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{domain}_{timestamp}.png"
            
            filepath = screenshot_dir / filename
            
            self.driver.save_screenshot(str(filepath))
            logger.info(f"Screenshot saved: {filepath}")
            
            return str(filepath)
        
        except Exception as e:
            logger.warning(f"Failed to take screenshot: {e}")
            return None
    
    def close(self):
        """Close Selenium driver and HTTP client."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium WebDriver closed")
            except Exception as e:
                logger.warning(f"Error closing Selenium driver: {e}")
        
        super().close()