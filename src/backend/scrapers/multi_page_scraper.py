"""
Enterprise Multi-Page Scraper
Scrapes homepage, about, careers, blog, product pages
"""
import asyncio
import logging
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import json

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class MultiPageScraper:
    """
    Scrapes multiple pages for a company
    Stores raw HTML + clean text with metadata
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or (PROJECT_ROOT / "data" / "raw")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def scrape_page(self, url: str, page_type: str) -> Optional[Dict]:
        """Scrape a single page"""
        try:
            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
            ) as client:
                response = await client.get(url)
            
            if response.status_code != 200:
                logger.warning(f"Non-200 status for {url}: {response.status_code}")
                return None
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove noise
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            # Extract clean text
            text = soup.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            clean_text = '\n'.join(lines)
            
            return {
                'url': url,
                'page_type': page_type,
                'status_code': response.status_code,
                'raw_html': response.text,
                'clean_text': clean_text,
                'crawled_at': datetime.utcnow().isoformat(),
                'content_length': len(clean_text)
            }
        
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return {
                'url': url,
                'page_type': page_type,
                'error': str(e),
                'crawled_at': datetime.utcnow().isoformat()
            }
    
    async def scrape_company(
        self,
        company_id: str,
        company_name: str,
        website: str,
        run_id: str = "initial"
    ) -> Dict:
        """
        Scrape all pages for a company
        
        Pages:
        - homepage
        - /about
        - /product or /platform
        - /careers  
        - /blog or /news
        """
        logger.info(f"Scraping {company_name} ({company_id})")
        
        # Normalize base URL
        if not website.startswith('http'):
            website = f"https://{website}"
        
        base_url = website.rstrip('/')
        
        # Define pages to scrape
        pages_to_scrape = [
            {'url': base_url, 'type': 'homepage'},
            {'url': f"{base_url}/about", 'type': 'about'},
            {'url': f"{base_url}/about-us", 'type': 'about'},
            {'url': f"{base_url}/company", 'type': 'about'},
            {'url': f"{base_url}/product", 'type': 'product'},
            {'url': f"{base_url}/products", 'type': 'product'},
            {'url': f"{base_url}/platform", 'type': 'product'},
            {'url': f"{base_url}/solutions", 'type': 'product'},
            {'url': f"{base_url}/careers", 'type': 'careers'},
            {'url': f"{base_url}/jobs", 'type': 'careers'},
            {'url': f"{base_url}/blog", 'type': 'blog'},
            {'url': f"{base_url}/news", 'type': 'blog'},
            {'url': f"{base_url}/press", 'type': 'blog'},
        ]
        
        # Scrape all pages concurrently
        tasks = [self.scrape_page(page['url'], page['type']) for page in pages_to_scrape]
        results = await asyncio.gather(*tasks)
        
        # Filter successful scrapes
        successful = [r for r in results if r and 'error' not in r and r.get('content_length', 0) > 100]
        
        # Deduplicate by page_type (keep first successful)
        unique_pages = {}
        for page in successful:
            ptype = page['page_type']
            if ptype not in unique_pages:
                unique_pages[ptype] = page
        
        logger.info(f"Successfully scraped {len(unique_pages)} unique pages for {company_name}")
        
        # Save to disk
        company_dir = self.output_dir / company_id / run_id
        company_dir.mkdir(parents=True, exist_ok=True)
        
        # Save each page
        for page_type, page_data in unique_pages.items():
            # Save raw HTML
            html_file = company_dir / f"{page_type}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(page_data['raw_html'])
            
            # Save clean text
            text_file = company_dir / f"{page_type}.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(page_data['clean_text'])
        
        # Save metadata
        metadata = {
            'company_id': company_id,
            'company_name': company_name,
            'website': website,
            'run_id': run_id,
            'crawled_at': datetime.utcnow().isoformat(),
            'pages_scraped': list(unique_pages.keys()),
            'total_content_length': sum(p['content_length'] for p in unique_pages.values())
        }
        
        metadata_file = company_dir / 'metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Saved {company_name} to {company_dir}")
        
        return metadata


async def scrape_all_50_companies():
    """Scrape all 50 Forbes AI companies"""
    
    # Load Forbes 50 list
    forbes_file = PROJECT_ROOT / "data" / "forbes_ai50_seed.json"
    with open(forbes_file) as f:
        companies = json.load(f)
    
    scraper = MultiPageScraper()
    
    results = []
    for i, company in enumerate(companies, 1):
        logger.info(f"\n[{i}/50] Processing {company['company_name']}...")
        
        try:
            result = await scraper.scrape_company(
                company_id=company['company_id'],
                company_name=company['company_name'],
                website=company['website'],
                run_id='initial'
            )
            results.append(result)
            
            # Rate limiting
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Failed to scrape {company['company_name']}: {e}")
            results.append({
                'company_id': company['company_id'],
                'error': str(e)
            })
    
    # Summary
    successful = [r for r in results if 'error' not in r]
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ Successfully scraped: {len(successful)}/50")
    logger.info(f"❌ Failed: {50 - len(successful)}/50")
    
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(scrape_all_50_companies())
