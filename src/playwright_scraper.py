"""
Enhanced web scraper using Playwright for better JavaScript handling
"""
import json
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup


class PlaywrightScraper:
    """Web scraper using Playwright for JavaScript-heavy websites"""
    
    def __init__(self, headless: bool = True, timeout: int = 20000):
        """
        Initialize Playwright scraper
        
        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout in milliseconds (reduced from 30s to 20s for faster failures)
        """
        self.headless = headless
        self.timeout = timeout
        self.playwright = None
        self.browser = None
        self.context = None
        
    def __enter__(self):
        """Context manager entry"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',  # Faster startup
                '--disable-plugins',  # Faster startup
                '--disable-background-networking',  # Faster page loads
                '--disable-background-timer-throttling',  # Faster execution
                '--disable-renderer-backgrounding',  # Faster execution
            ]
        )
        self.context = self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def fetch_page(self, url: str, page_type: str) -> Optional[Tuple[str, str, str]]:
        """
        Fetch a page using Playwright
        
        Args:
            url: URL to fetch
            page_type: Type of page (for logging)
            
        Returns:
            Tuple of (html, text, final_url) or None if failed
        """
        page = None
        try:
            page = self.context.new_page()
            
            # Navigate to URL - use 'domcontentloaded' for faster loading (still gets all content)
            response = page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
            
            if not response or response.status >= 400:
                return None
            
            # Wait for main content to be ready (smart wait instead of fixed time)
            try:
                # Try to wait for main content elements (faster than fixed wait)
                page.wait_for_selector('main, article, [role="main"], .content, .main-content, body', timeout=3000)
            except:
                pass  # Continue if selectors not found (page might use different structure)
            
            # Reduced wait time for dynamic content (1s instead of 2s)
            page.wait_for_timeout(1000)
            
            # Get content
            html = page.content()
            
            # Extract visible text
            text = page.inner_text('body')
            
            final_url = page.url
            
            # Check if redirected to external domain
            if self._is_redirect_to_external(url, final_url):
                return None
            
            return (html, text, final_url)
            
        except PlaywrightTimeout:
            print(f"      ⏱️  Timeout loading {page_type}: {url}")
            return None
        except Exception as e:
            print(f"      ❌ Error fetching {page_type}: {e}")
            return None
        finally:
            if page:
                page.close()
    
    def _is_redirect_to_external(self, original_url: str, final_url: str) -> bool:
        """Check if URL redirected to an external site (allow same-site subdomains)."""
        original_domain = urlparse(original_url).netloc.replace('www.', '')
        final_domain = urlparse(final_url).netloc.replace('www.', '')
        if not original_domain or not final_domain:
            return False
        # Allow subdomains: blog.company.com should be treated as internal to company.com
        return not (
            final_domain == original_domain or
            final_domain.endswith('.' + original_domain) or
            original_domain.endswith('.' + final_domain)
        )
    
    def _extract_text_from_html(self, html: str) -> str:
        """Extract clean text from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        
        # Clean up
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def scrape_company(
        self,
        company_id: str,
        company_name: str,
        website: str,
        output_dir: Path,
        forbes_data: List[Dict]
    ) -> Dict:
        """
        Scrape all pages for a company
        
        Args:
            company_id: Unique company identifier
            company_name: Company name
            website: Company website URL
            output_dir: Directory to save results
            forbes_data: Forbes AI 50 data for reference
            
        Returns:
            Dictionary with scraping results
        """
        company_dir = output_dir / company_id
        company_dir.mkdir(parents=True, exist_ok=True)
        
        # Enhanced page patterns (10 page types!)
        pages_to_fetch = [
            ('homepage', [website]),
            ('about', ['/about', '/about-us', '/company', '/who-we-are']),
            ('product', ['/product', '/products', '/platform', '/solutions']),
            ('careers', ['/careers', '/jobs', '/join-us']),
            ('blog', ['/blog', '/news', '/insights', '/resources']),
            ('pricing', ['/pricing', '/plans', '/buy', '/purchase']),
            ('customers', ['/customers', '/case-studies', '/testimonials']),
            ('partners', ['/partners', '/integrations', '/ecosystem']),
            ('press', ['/press', '/newsroom', '/media']),
            ('team', ['/team', '/leadership', '/founders'])
        ]
        
        results = {
            'company_id': company_id,
            'company_name': company_name,
            'website': website,
            'pages_scraped': 0,
            'success': {},
            'errors': []
        }
        
        print(f"  📥 Scraping {company_name} with Playwright...")
        
        footer_links: Dict[str, List[str]] = {}

        for page_type, patterns in pages_to_fetch:
            success = False
            
            # Try each URL pattern
            for pattern in patterns:
                if pattern == website:
                    url = website
                else:
                    url = urljoin(website, pattern)
                
                print(f"    Trying {page_type}: {url}")
                
                result = self.fetch_page(url, page_type)
                
                if result:
                    html, text, final_url = result
                    
                    # After successfully fetching homepage, analyze footer for navigation links
                    if page_type == 'homepage' and not footer_links:
                        footer_links = self._extract_footer_links(html, website)
                        if footer_links:
                            print("    🔍 Footer links detected: " + ", ".join(f"{k}:{len(v)}" for k, v in footer_links.items()))
                            # PRIORITIZE footer links by putting them FIRST in the patterns list
                            for target_type, urls in footer_links.items():
                                for idx, (pt, pt_patterns) in enumerate(pages_to_fetch):
                                    if pt == target_type:
                                        # Put footer URLs FIRST, then default patterns
                                        enriched = list(dict.fromkeys(urls + pt_patterns))
                                        pages_to_fetch[idx] = (pt, enriched)
                                        print(f"    ✅ Prioritized {len(urls)} footer URLs for {target_type}")
                                        break

                    # Validate we got good content
                    if len(text) > 500:  # Reasonable content length
                        # Save HTML
                        html_file = company_dir / f"{page_type}.html"
                        with open(html_file, 'w', encoding='utf-8') as f:
                            f.write(html)
                        
                        # Save text
                        text_file = company_dir / f"{page_type}.txt"
                        with open(text_file, 'w', encoding='utf-8') as f:
                            f.write(text)
                        
                        results['pages_scraped'] += 1
                        results['success'][page_type] = final_url
                        
                        success = True
                        break
                 
            if not success:
                results['errors'].append(page_type)
                print(f"    ⚠️  Failed to fetch {page_type}")
 
        metadata = {
            'company_id': company_id,
            'timestamp': datetime.utcnow().isoformat(),
            'pages_scraped': results['pages_scraped'],
            'success': results['success'],
            'errors': results['errors'],
            'website': website,
            'forbes_reference': next((c for c in forbes_data if c['company_id'] == company_id), None)
        }
 
        metadata_file = company_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
 
        print(f"  ✅ Scraped {results['pages_scraped']} pages")
 
        return results
 
 
    def _extract_footer_links(self, html: str, base_url: str) -> Dict[str, List[str]]:
        """Inspect footer to find relevant navigation links."""
        soup = BeautifulSoup(html, 'html.parser')

        footer = soup.find('footer')
        if not footer:
            footer_candidates = soup.find_all(attrs={'class': re.compile(r'footer', re.I)})
            footer = footer_candidates[0] if footer_candidates else None
        if not footer:
            return {}

        link_map: Dict[str, List[str]] = {
            'careers': [],
            'blog': [],
            'press': [],
            'customers': [],
            'partners': [],
            'pricing': [],
            'team': [],
            'about': [],
            'product': []
        }

        keyword_map = {
            'careers': ['career', 'jobs', 'join', 'hiring', 'work with'],
            'blog': ['blog', 'insights', 'news', 'stories', 'resources'],
            'press': ['press', 'media', 'newsroom'],
            'customers': ['customers', 'case study', 'case studies', 'stories', 'clients'],
            'partners': ['partner', 'ecosystem', 'integration', 'alliance'],
            'pricing': ['pricing', 'plans', 'pricing plans', 'buy'],
            'team': ['team', 'leadership', 'founder', 'people'],
            'about': ['about', 'company', 'mission', 'who we are'],
            'product': ['product', 'platform', 'solution']
        }

        links = footer.find_all('a', href=True)
        for link in links:
            href = link['href'].strip()
            text = (link.get_text(strip=True) or '').lower()
            aria = (link.get('aria-label') or '').lower()
            context_text = f"{text} {aria}"

            if not href or href.startswith('#'):
                continue

            absolute_url = urljoin(base_url, href)

            matched = False
            for page_type, keywords in keyword_map.items():
                if any(keyword in context_text for keyword in keywords):
                    link_map[page_type].append(absolute_url)
                    matched = True
            if not matched and 'linkedin.com' in absolute_url.lower():
                link_map.setdefault('linkedin', []).append(absolute_url)

        cleaned = {k: list(dict.fromkeys(v)) for k, v in link_map.items() if v}
        return cleaned


def scrape_company_with_playwright(company_id: str, company_name: str, website: str) -> Dict:
    """
    Helper function to scrape a single company
    
    Args:
        company_id: Company ID
        company_name: Company name
        website: Company website
        
    Returns:
        Scraping results dictionary
    """
    output_dir = Path("data/raw")
    
    # Load Forbes seed data
    seed_file = Path("data/forbes_ai50_seed.json")
    with open(seed_file) as f:
        forbes_data = json.load(f)
    
    with PlaywrightScraper(headless=True) as scraper:
        return scraper.scrape_company(company_id, company_name, website, output_dir, forbes_data)

