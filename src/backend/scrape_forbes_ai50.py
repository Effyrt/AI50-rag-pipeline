"""
Lab 0: Scraper to populate forbes_ai50_seed.json from Forbes AI 50 website.
This script scrapes the Forbes AI 50 list and extracts basic company information
(company_name, website, linkedin, hq_city, hq_country, founded_year, categories, related_companies).
"""
import json
import re
import time
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


class ForbesAI50Scraper:
    """Scraper for Forbes AI 50 list with Selenium support."""
    
    def __init__(self, base_url: str = "https://www.forbes.com/lists/ai50/", use_selenium: bool = True):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.companies = []
        
        # Selenium setup
        self.use_selenium = use_selenium
        self.driver = None
        if use_selenium:
            self._init_selenium()
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver."""
        try:
            print("Initializing Selenium WebDriver...")
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(60)  # Longer timeout for Forbes
            print("✅ Selenium WebDriver initialized")
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize Selenium: {e}")
            print(f"   Continuing with requests only...")
            self.use_selenium = False
            self.driver = None
    
    def fetch_page_with_selenium(self, url: str, save_html: bool = False) -> Optional[str]:
        """Fetch a page using Selenium (for JS-heavy sites)."""
        if not self.driver:
            return None
        
        try:
            print(f"  Fetching with Selenium: {url}")
            self.driver.get(url)
            
            # Wait for body to load
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                print("  ⚠️  Timeout waiting for page body")
            
            # Wait extra time for dynamic content (Forbes loads data via JS)
            print("  ⏳ Waiting for dynamic content to load...")
            time.sleep(8)
            
            # Scroll to load lazy content
            print("  📜 Scrolling to load lazy content...")
            for i in range(3):
                scroll_position = (i + 1) * (self.driver.execute_script("return document.body.scrollHeight") // 3)
                self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                time.sleep(2)
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            html = self.driver.page_source
            print(f"  ✅ Got {len(html)} bytes of HTML via Selenium")
            
            # Save HTML for debugging if requested
            if save_html:
                debug_path = Path(__file__).parent.parent / "data" / "forbes_debug.html"
                debug_path.write_text(html, encoding='utf-8')
                print(f"  💾 Saved HTML to {debug_path} for debugging")
            
            return html
        except Exception as e:
            print(f"  ❌ Selenium error: {e}")
            return None
    
    def fetch_page(self, url: str, retries: int = 3, use_selenium_fallback: bool = True) -> Optional[str]:
        """Fetch a page with retries, falling back to Selenium if needed."""
        # Try requests first (faster)
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                html = response.text
                
                # Check if we got actual content (not just a skeleton)
                if len(html) > 1000:
                    return html
                else:
                    print(f"  ⚠️  Requests got minimal content ({len(html)} bytes), may need JS rendering")
                    break
            except requests.RequestException as e:
                print(f"  Requests error (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    break
        
        # If requests failed or got minimal content, try Selenium
        if use_selenium_fallback and self.use_selenium:
            print(f"  🔄 Falling back to Selenium for {url}")
            # Save HTML for Forbes AI 50 list page only (for debugging)
            save_html = 'ai50' in url
            return self.fetch_page_with_selenium(url, save_html=save_html)
        
        return None
    
    def extract_companies_from_list(self, html: str) -> List[Dict]:
        """Extract company list from Forbes AI 50 main page."""
        soup = BeautifulSoup(html, 'lxml')
        companies = []
        seen_names = set()  # Avoid duplicates
        
        print("  Trying multiple extraction methods...")
        
        # Method 1: Look for structured data (JSON-LD)
        print("  Method 1: Checking JSON-LD structured data...")
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            if script.string:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'itemListElement' in data:
                        print(f"    Found itemListElement with {len(data['itemListElement'])} items")
                        for item in data['itemListElement']:
                            if 'name' in item:
                                name = item['name']
                                if name and name not in seen_names and len(name) < 100:
                                    seen_names.add(name)
                                    companies.append({
                                        'name': name,
                                        'forbes_url': item.get('url', '')
                                    })
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    continue
        
        if companies:
            print(f"  ✅ Method 1 found {len(companies)} companies")
            return companies
        
        # Method 2: Look for Forbes-specific selectors
        print("  Method 2: Checking Forbes-specific CSS selectors...")
        selectors = [
            '[data-type="list-item"]',
            '.fbs-list__item',
            '.listitem',
            '.ranked-list-item',
            'div[class*="list-item"]',
            'div[class*="company"]',
            'article[class*="company"]'
        ]
        
        for selector in selectors:
            items = soup.select(selector)
            if items:
                print(f"    Found {len(items)} items with selector: {selector}")
                for item in items:
                    # Try to find company name in various tags
                    name_elem = item.find(['h2', 'h3', 'h4', 'a', 'span'])
                    if name_elem:
                        text = name_elem.get_text(strip=True)
                        # Clean up rank if present (e.g., "1. OpenAI" -> "OpenAI")
                        text = re.sub(r'^\d+\.?\s*', '', text)
                        if text and text not in seen_names and 2 < len(text) < 100:
                            seen_names.add(text)
                            # Try to find link
                            link = item.find('a')
                            url = urljoin(self.base_url, link['href']) if link and link.get('href') else ''
                            companies.append({'name': text, 'forbes_url': url})
        
        if companies:
            print(f"  ✅ Method 2 found {len(companies)} companies")
            return companies
        
        # Method 3: Look for numbered list headings
        print("  Method 3: Checking for numbered headings...")
        # Filter words that indicate non-company text
        filter_words = ['under', 'over', 'top', 'college', 'universities', 'best', 
                       'subscribe', 'forbes', 'menu', 'sign in', 'follow', 'share']
        
        headings = soup.find_all(['h2', 'h3', 'h4', 'div', 'span'])
        for heading in headings:
            text = heading.get_text(strip=True)
            # Match patterns like "1. OpenAI" or "1 OpenAI"
            match = re.match(r'^(\d+)[\.\s]+(.+)$', text)
            if match:
                rank = int(match.group(1))
                name = match.group(2).strip()
                text_lower = name.lower()
                
                # Filter out obviously wrong matches
                is_valid = (
                    1 <= rank <= 50 and
                    name not in seen_names and
                    2 < len(name) < 100 and
                    not any(fw in text_lower for fw in filter_words) and
                    not text_lower.isdigit()
                )
                
                if is_valid:
                    seen_names.add(name)
                    link = heading.find('a') or heading.find_parent('a')
                    url = urljoin(self.base_url, link['href']) if link and link.get('href') else ''
                    companies.append({'name': name, 'forbes_url': url})
        
        if companies:
            print(f"  ✅ Method 3 found {len(companies)} companies")
            return companies
        
        # Method 4: Look for any links that might be companies
        print("  Method 4: Checking links...")
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            # Look for company-related URLs or reasonable company names
            if (('/companies/' in href or '/profile/' in href) and 
                text and text not in seen_names and 2 < len(text) < 100 and
                not any(skip in text.lower() for skip in ['forbes', 'subscribe', 'sign in', 'menu'])):
                seen_names.add(text)
                companies.append({
                    'name': text,
                    'forbes_url': urljoin(self.base_url, href)
                })
        
        if companies:
            print(f"  ✅ Method 4 found {len(companies)} companies")
        
        return companies
    
    def extract_company_details(self, company_name: str, forbes_url: str) -> Dict:
        """Extract detailed information from a company's Forbes profile page."""
        company_data = {
            'company_id': str(uuid.uuid4()),
            'company_name': company_name,
            'legal_name': None,  # Will be extracted from company website/about page
            'brand_name': company_name,  # Default to company_name, may be updated
            'website': None,
            'linkedin': None,
            'hq_city': None,
            'hq_country': None,
            'founded_year': None,
            'categories': [],  # Will extract from Forbes page and company website
            'related_companies': []  # Will extract from competitive positioning mentions
        }
        
        if not forbes_url:
            return company_data
        
        html = self.fetch_page(forbes_url)
        if not html:
            return company_data
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract website
        website_links = soup.find_all('a', href=re.compile(r'^https?://(?!www\.forbes\.com)', re.I))
        for link in website_links:
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            if 'website' in text or 'visit' in text or (href and not 'forbes.com' in href):
                company_data['website'] = href
                break
        
        # Look for structured data
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    # Extract website
                    if 'url' in data and not company_data['website']:
                        company_data['website'] = data['url']
                    
                    # Extract location
                    if 'address' in data:
                        address = data['address']
                        if isinstance(address, dict):
                            company_data['hq_city'] = address.get('addressLocality')
                            company_data['hq_country'] = address.get('addressCountry')
                    
                    # Extract founding year
                    if 'foundingDate' in data:
                        year_match = re.search(r'\d{4}', str(data['foundingDate']))
                        if year_match:
                            company_data['founded_year'] = int(year_match.group())
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        
        # Extract from text content
        text_content = soup.get_text()
        
        # Try to find HQ location
        if not company_data['hq_city']:
            location_patterns = [
                r'headquarters?[:\s]+([^,\n]+),\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
                r'based in ([^,\n]+),\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
                r'located in ([^,\n]+),\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
            ]
            for pattern in location_patterns:
                match = re.search(pattern, text_content, re.I)
                if match:
                    company_data['hq_city'] = match.group(1).strip()
                    company_data['hq_country'] = match.group(2).strip()
                    break
        
        # Try to find founded year
        if not company_data['founded_year']:
            founded_patterns = [
                r'founded[:\s]+(\d{4})',
                r'established[:\s]+(\d{4})',
                r'founded in (\d{4})'
            ]
            for pattern in founded_patterns:
                match = re.search(pattern, text_content, re.I)
                if match:
                    try:
                        year = int(match.group(1))
                        if 1900 <= year <= 2025:
                            company_data['founded_year'] = year
                            break
                    except ValueError:
                        continue
        
        # Extract LinkedIn (look for LinkedIn links)
        linkedin_links = soup.find_all('a', href=re.compile(r'linkedin\.com/company', re.I))
        if linkedin_links:
            company_data['linkedin'] = linkedin_links[0].get('href')
        
        # Extract categories from text (look for industry/sector mentions)
        category_keywords = [
            'artificial intelligence', 'machine learning', 'generative ai', 'llm', 'nlp',
            'computer vision', 'robotics', 'autonomous', 'data analytics', 'mlops',
            'enterprise ai', 'healthcare ai', 'fintech', 'saas', 'cybersecurity'
        ]
        found_categories = []
        text_lower = text_content.lower()
        for keyword in category_keywords:
            if keyword in text_lower:
                found_categories.append(keyword.title())
        company_data['categories'] = list(set(found_categories))[:5]  # Limit to 5
        
        time.sleep(1)  # Be respectful with rate limiting
        return company_data
    
    def scrape_all(self) -> List[Dict]:
        """Scrape all companies from Forbes AI 50 list."""
        print(f"\n{'='*60}")
        print(f"Fetching Forbes AI 50 list from {self.base_url}...")
        print(f"{'='*60}\n")
        
        # Force Selenium for Forbes AI 50 list (it's JavaScript-heavy)
        print("📌 Using Selenium to render JavaScript content...")
        html = self.fetch_page_with_selenium(self.base_url, save_html=True)
        
        if not html:
            print("❌ Failed to fetch Forbes AI 50 list page")
            return []
        
        print(f"\n{'='*60}")
        print("Extracting company list from HTML...")
        print(f"{'='*60}\n")
        
        company_list = self.extract_companies_from_list(html)
        
        if not company_list:
            print("\n⚠️  No companies found with standard methods.")
            print("Attempting fallback text extraction...")
            # Fallback: try to find all company names in the page text
            soup = BeautifulSoup(html, 'lxml')
            all_text = soup.get_text()
            # Pattern: "1. Company Name" or similar
            matches = re.findall(r'\n\s*\d+[\.\s]+([^\n]+)', all_text)
            if matches:
                # Clean and deduplicate
                seen = set()
                for match in matches[:50]:
                    name = match.strip()
                    # Filter out noise
                    if (name and name not in seen and 2 < len(name) < 100 and
                        not any(skip in name.lower() for skip in ['forbes', 'subscribe', 'sign in'])):
                        seen.add(name)
                        company_list.append({'name': name, 'forbes_url': ''})
                print(f"  Fallback found {len(company_list)} potential companies")
        
        if not company_list:
            print("\n❌ Could not extract any companies from Forbes AI 50 list")
            print("   The page structure may have changed significantly.")
            print("   You may need to manually populate the seed file.")
            return []
        
        print(f"\n✅ Found {len(company_list)} companies from Forbes AI 50 list\n")
        
        # Extract details for each company
        all_companies = []
        companies_to_process = company_list[:50]  # Limit to 50
        
        print(f"{'='*60}")
        print(f"Extracting details for {len(companies_to_process)} companies...")
        print(f"{'='*60}\n")
        
        for idx, company in enumerate(companies_to_process, 1):
            company_name = company.get('name', 'Unknown')
            forbes_url = company.get('forbes_url', '')
            
            print(f"[{idx}/{len(companies_to_process)}] Processing: {company_name}")
            
            details = self.extract_company_details(company_name, forbes_url)
            all_companies.append(details)
            
            # Show quick summary
            website = details.get('website', 'N/A')
            hq = f"{details.get('hq_city', '?')}, {details.get('hq_country', '?')}"
            print(f"  → Website: {website}")
            print(f"  → HQ: {hq}")
            print(f"  → Categories: {', '.join(details.get('categories', []))[:50]}...")
            
            time.sleep(2)  # Rate limiting
        
        return all_companies
    
    def cleanup(self):
        """Clean up Selenium driver."""
        if self.driver:
            try:
                print("\nCleaning up Selenium driver...")
                self.driver.quit()
                print("✅ Selenium driver closed")
            except Exception as e:
                print(f"⚠️  Error closing Selenium: {e}")


def main():
    """Main function to scrape and save Forbes AI 50 seed data."""
    scraper = ForbesAI50Scraper(use_selenium=True)
    
    try:
        companies = scraper.scrape_all()
        
        if not companies:
            print("\n❌ No companies were scraped")
            print("   Check the output above for errors")
            print("   You may need to manually populate the seed file")
            return
        
        # Save to seed file (basic info only - will be used to scrape full payloads later)
        output_path = Path(__file__).parent.parent / "data" / "forbes_ai50_seed.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure all required seed fields are present
        seed_data = []
        for company in companies:
            seed_entry = {
                'company_id': company.get('company_id', str(uuid.uuid4())),
                'company_name': company.get('company_name', ''),
                'website': company.get('website', ''),
                'linkedin': company.get('linkedin', ''),
                'hq_city': company.get('hq_city'),
                'hq_country': company.get('hq_country'),
                'founded_year': company.get('founded_year'),
                'categories': company.get('categories', []),
                'related_companies': company.get('related_companies', [])
            }
            seed_data.append(seed_entry)
        
        with open(output_path, 'w') as f:
            json.dump(seed_data, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"✅ Successfully scraped {len(companies)} companies")
        print(f"✅ Saved to {output_path}")
        print(f"{'='*60}")
        
        # Print summary statistics
        print("\n📊 Summary Statistics:")
        print(f"  Total companies: {len(companies)}")
        print(f"  Companies with website: {sum(1 for c in companies if c.get('website'))}")
        print(f"  Companies with LinkedIn: {sum(1 for c in companies if c.get('linkedin'))}")
        print(f"  Companies with HQ info: {sum(1 for c in companies if c.get('hq_city'))}")
        print(f"  Companies with founded year: {sum(1 for c in companies if c.get('founded_year'))}")
        print(f"  Companies with categories: {sum(1 for c in companies if c.get('categories'))}")
        
        print("\n📝 Next step:")
        print("  Run: python src/scraper.py")
        print("  This will scrape full page content from company websites (Lab 1)")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.cleanup()


if __name__ == "__main__":
    main()

