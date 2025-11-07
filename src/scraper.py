"""
Enhanced Web Scraper for Forbes AI 50 Companies
Automatically scrapes multiple pages per company
"""
import os
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse


class CompanyScraper:
    """
    Scrapes company web pages and saves to data/raw/<company>/
    """
    
    def __init__(self, base_data_dir: str = "data/raw"):
        self.base_data_dir = Path(base_data_dir)
        self.base_data_dir.mkdir(parents=True, exist_ok=True)
        
        # HTTP session with proper headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
    
    def scrape_company(
        self, 
        company_name: str, 
        base_url: str,
        run_id: Optional[str] = None
    ) -> Dict:
        """
        Scrape all relevant pages for a company
        
        Returns:
            Metadata dictionary with scraping results
        """
        print(f"\n{'='*60}")
        print(f"Scraping: {company_name}")
        print(f"Base URL: {base_url}")
        print(f"{'='*60}")
        
        # Create company folder
        company_folder = self.base_data_dir / self._sanitize_name(company_name)
        if run_id:
            company_folder = company_folder / run_id
        company_folder.mkdir(parents=True, exist_ok=True)
        
        # Define pages to scrape with multiple path variations
        pages_config = {
            'homepage': ['', '/', '/index', '/index.html'],
            'about': ['/about', '/about-us', '/company', '/who-we-are', '/our-company'],
            'product': ['/product', '/products', '/solutions', '/platform', '/technology'],
            'careers': ['/careers', '/jobs', '/join-us', '/work-with-us', '/opportunities'],
            'blog': ['/blog', '/news', '/newsroom', '/press', '/media', '/insights']
        }
        
        results = {
            'company_name': company_name,
            'base_url': base_url,
            'crawled_at': datetime.now().isoformat(),
            'run_id': run_id,
            'pages': {}
        }
        
        # Scrape each page type
        for page_type, path_variations in pages_config.items():
            success = False
            
            # Try each path variation until one works
            for path in path_variations:
                if success:
                    break
                    
                try:
                    url = urljoin(base_url, path)
                    print(f"  Trying {page_type}: {url}")
                    
                    html, text = self._fetch_page(url)
                    
                    if html and text and len(text) > 200:  # Minimum content check
                        # Save files
                        html_file = company_folder / f"{page_type}.html"
                        text_file = company_folder / f"{page_type}.txt"
                        
                        html_file.write_text(html, encoding='utf-8')
                        text_file.write_text(text, encoding='utf-8')
                        
                        results['pages'][page_type] = {
                            'url': url,
                            'status': 'success',
                            'text_length': len(text),
                            'html_file': str(html_file),
                            'text_file': str(text_file)
                        }
                        
                        print(f"    ✓ Success: {len(text)} characters")
                        success = True
                        
                        # Be polite - delay between requests
                        time.sleep(1)
                        
                except Exception as e:
                    print(f"    ✗ Failed: {str(e)}")
                    continue
            
            if not success:
                results['pages'][page_type] = {
                    'status': 'failed',
                    'attempted_urls': [urljoin(base_url, p) for p in path_variations],
                    'error': 'All path variations failed'
                }
                print(f"    ⚠ Could not find {page_type} page")
        
        # Save metadata
        metadata_file = company_folder / 'metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        # Summary
        success_count = sum(1 for p in results['pages'].values() if p['status'] == 'success')
        print(f"\n✓ Completed: {success_count}/{len(pages_config)} pages scraped")
        
        return results
    
    def _fetch_page(self, url: str, timeout: int = 10) -> tuple[Optional[str], Optional[str]]:
        """
        Fetch a page and extract clean text
        
        Returns:
            (raw_html, clean_text) tuple
        """
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Check if it's HTML
            content_type = response.headers.get('content-type', '')
            if 'text/html' not in content_type.lower():
                print(f"      Not HTML: {content_type}")
                return None, None
            
            html = response.text
            text = self._extract_text(html)
            
            return html, text
            
        except requests.exceptions.RequestException as e:
            return None, None
    
    def _extract_text(self, html: str) -> str:
        """Extract clean text from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'noscript']):
            element.decompose()
        
        # Get text
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        # Remove very short lines (likely navigation/menu items)
        lines = [line for line in lines if len(line) > 3]
        text = '\n'.join(lines)
        
        return text
    
    def _sanitize_name(self, name: str) -> str:
        """Convert company name to safe folder name"""
        return name.lower().replace(' ', '_').replace('/', '_').replace('\\', '_').replace('.', '_')
    
    def batch_scrape(self, companies: List[Dict]) -> List[Dict]:
        """
        Scrape multiple companies
        
        Args:
            companies: List of dicts with 'name' and 'url' keys
            
        Returns:
            List of scraping results
        """
        results = []
        
        for i, company in enumerate(companies, 1):
            print(f"\n[{i}/{len(companies)}]")
            
            try:
                result = self.scrape_company(
                    company_name=company['name'],
                    base_url=company['url']
                )
                results.append(result)
            except Exception as e:
                print(f"ERROR: Failed to scrape {company['name']}: {str(e)}")
                results.append({
                    'company_name': company['name'],
                    'base_url': company.get('url', 'unknown'),
                    'status': 'error',
                    'error': str(e)
                })
            
            # Delay between companies
            time.sleep(2)
        
        return results


# Test function
def test_scraper():
    """Test the scraper with a few companies"""
    
    scraper = CompanyScraper()
    
    # Test companies
    test_companies = [
        {'name': 'OpenAI', 'url': 'https://www.openai.com'},
        {'name': 'Anthropic', 'url': 'https://www.anthropic.com'}
    ]
    
    print("\n" + "="*60)
    print("TESTING ENHANCED SCRAPER")
    print("="*60)
    
    results = scraper.batch_scrape(test_companies)
    
    # Save summary
    summary_file = Path("data/scraping_summary.json")
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*60)
    print(f"✓ Scraping complete! Summary saved to {summary_file}")
    print("="*60)
    
    # Print summary
    for result in results:
        company = result['company_name']
        if 'pages' in result:
            success = sum(1 for p in result['pages'].values() if p.get('status') == 'success')
            total = len(result['pages'])
            print(f"  {company}: {success}/{total} pages")
        else:
            print(f"  {company}: ERROR")


if __name__ == "__main__":
    test_scraper()