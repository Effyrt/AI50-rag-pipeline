"""
Forbes AI 50 list scraper with JavaScript rendering support.
"""
import logging
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from bs4 import BeautifulSoup

from .base import BaseScraper
from ..core.exceptions import ScrapingError, ParsingError
from ..core.telemetry import track_time

logger = logging.getLogger(__name__)


class ForbesAI50Scraper(BaseScraper):
    """
    Scraper for Forbes AI 50 list.
    
    Extracts company names, websites, and basic info from the list page.
    """
    
    FORBES_AI50_URL = "https://www.forbes.com/lists/ai50/"
    
    @track_time("forbes_ai50_scrape")
    def scrape(self, url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Scrape the Forbes AI 50 list.
        
        Args:
            url: Optional custom URL (defaults to Forbes AI 50 page)
            
        Returns:
            List of company dictionaries
        """
        url = url or self.FORBES_AI50_URL
        
        logger.info(f"Scraping Forbes AI 50 from {url}")
        
        try:
            response = self.fetch_url(url)
            soup = self.parse_html(response.text)
            
            # Try multiple strategies to find companies
            companies = self._extract_from_json_ld(soup)
            
            if not companies:
                companies = self._extract_from_list_items(soup)
            
            if not companies:
                companies = self._extract_from_table(soup)
            
            if not companies:
                raise ParsingError(
                    "Could not extract companies using any strategy",
                    error_code="NO_COMPANIES_FOUND"
                )
            
            logger.info(f"Successfully extracted {len(companies)} companies")
            
            # Enrich with metadata
            for i, company in enumerate(companies, 1):
                company["rank"] = i
                company["list_year"] = 2025
                company["scraped_at"] = datetime.utcnow().isoformat() + "Z"
            
            return companies
        
        except Exception as e:
            logger.error(f"Failed to scrape Forbes AI 50: {e}", exc_info=True)
            raise ScrapingError(
                f"Forbes AI 50 scraping failed: {e}",
                error_code="FORBES_SCRAPE_FAILED",
                details={"url": url, "error": str(e)}
            )
    
    def _extract_from_json_ld(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract companies from JSON-LD structured data.
        
        Forbes often embeds data in <script type="application/ld+json"> tags.
        """
        companies = []
        
        try:
            # Find all JSON-LD scripts
            scripts = soup.find_all("script", type="application/ld+json")
            
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Look for ItemList or similar structures
                    if isinstance(data, dict):
                        if data.get("@type") == "ItemList":
                            items = data.get("itemListElement", [])
                            
                            for item in items:
                                company = self._parse_list_item(item)
                                if company:
                                    companies.append(company)
                
                except json.JSONDecodeError:
                    continue
            
            logger.info(f"Extracted {len(companies)} companies from JSON-LD")
            return companies
        
        except Exception as e:
            logger.warning(f"JSON-LD extraction failed: {e}")
            return []
    
    def _extract_from_list_items(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract companies from HTML list structure.
        
        Looks for common patterns like <li> or <div class="company-card">.
        """
        companies = []
        
        try:
            # Try multiple selectors
            selectors = [
                "div.fbs-list-item",
                "div.company-item",
                "li.list-item",
                "article.company-card",
                "div[data-company]"
            ]
            
            for selector in selectors:
                items = soup.select(selector)
                
                if items:
                    logger.info(f"Found {len(items)} items with selector: {selector}")
                    
                    for item in items:
                        company = self._parse_html_item(item)
                        if company:
                            companies.append(company)
                    
                    if companies:
                        break
            
            logger.info(f"Extracted {len(companies)} companies from list items")
            return companies
        
        except Exception as e:
            logger.warning(f"List item extraction failed: {e}")
            return []
    
    def _extract_from_table(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract companies from HTML table.
        
        Fallback method for table-based layouts.
        """
        companies = []
        
        try:
            table = soup.find("table")
            
            if not table:
                return []
            
            rows = table.find_all("tr")[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_all(["td", "th"])
                
                if len(cells) >= 2:
                    company_name = cells[1].get_text(strip=True)
                    
                    # Try to find website link
                    link = cells[1].find("a")
                    website = link.get("href") if link else None
                    
                    if company_name:
                        companies.append({
                            "company_name": company_name,
                            "website": website,
                            "description": None
                        })
            
            logger.info(f"Extracted {len(companies)} companies from table")
            return companies
        
        except Exception as e:
            logger.warning(f"Table extraction failed: {e}")
            return []
    
    def _parse_list_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a JSON-LD list item into company dict."""
        try:
            company = {}
            
            # Extract name
            if "item" in item:
                item_data = item["item"]
                company["company_name"] = item_data.get("name")
                company["website"] = item_data.get("url")
                company["description"] = item_data.get("description")
            else:
                company["company_name"] = item.get("name")
                company["website"] = item.get("url")
                company["description"] = item.get("description")
            
            # Validate required fields
            if not company.get("company_name"):
                return None
            
            return company
        
        except Exception as e:
            logger.warning(f"Failed to parse list item: {e}")
            return None
    
    def _parse_html_item(self, item) -> Optional[Dict[str, Any]]:
        """Parse an HTML element into company dict."""
        try:
            company = {}
            
            # Try to find company name
            name_elem = (
                item.find("h2") or
                item.find("h3") or
                item.find(class_=re.compile(r"company.*name", re.I)) or
                item.find(class_=re.compile(r"title", re.I))
            )
            
            if name_elem:
                company["company_name"] = name_elem.get_text(strip=True)
            else:
                # Fallback: use data attribute
                company["company_name"] = item.get("data-company")
            
            # Try to find website
            link = item.find("a", href=True)
            if link:
                href = link["href"]
                # Filter out Forbes internal links
                if not href.startswith("/") and "forbes.com" not in href:
                    company["website"] = href
            
            # Try to find description
            desc_elem = (
                item.find(class_=re.compile(r"description", re.I)) or
                item.find("p")
            )
            
            if desc_elem:
                company["description"] = desc_elem.get_text(strip=True)
            
            # Validate
            if not company.get("company_name"):
                return None
            
            return company
        
        except Exception as e:
            logger.warning(f"Failed to parse HTML item: {e}")
            return None
    
    def save_to_json(self, companies: List[Dict[str, Any]], output_path: str):
        """
        Save companies list to JSON file.
        
        Args:
            companies: List of company dictionaries
            output_path: Path to save JSON file
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(companies, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(companies)} companies to {output_path}")
        
        except Exception as e:
            raise ScrapingError(
                f"Failed to save companies to JSON: {e}",
                error_code="JSON_SAVE_FAILED",
                details={"path": output_path, "error": str(e)}
            )