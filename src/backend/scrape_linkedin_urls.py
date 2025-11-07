"""
Scrape LinkedIn URLs from company homepages to complete the seed file.
This is a lightweight scraper that only fetches homepages to extract social links.
"""
import json
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


class LinkedInScraper:
    """Lightweight scraper to extract LinkedIn URLs from company websites."""
    
    def __init__(self, use_selenium: bool = False):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        self.use_selenium = use_selenium
        self.driver = None
        if use_selenium:
            self._init_selenium()
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver."""
        try:
            print("Initializing Selenium...")
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
            print("✅ Selenium initialized\n")
        except Exception as e:
            print(f"⚠️  Could not initialize Selenium: {e}")
            self.use_selenium = False
    
    def extract_linkedin_url(self, html: str) -> Optional[str]:
        """Extract LinkedIn company URL from HTML."""
        soup = BeautifulSoup(html, 'lxml')
        
        # Find all links
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '')
            
            # Look for LinkedIn company page
            if 'linkedin.com/company/' in href:
                # Clean up the URL (remove query params and tracking)
                clean_url = href.split('?')[0].split('#')[0]
                # Remove trailing slash
                clean_url = clean_url.rstrip('/')
                return clean_url
        
        return None
    
    def fetch_homepage(self, url: str) -> Optional[str]:
        """Fetch homepage HTML."""
        try:
            response = self.session.get(url, timeout=15, allow_redirects=True)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"      ❌ Error fetching: {e}")
            return None
    
    def scrape_linkedin(self, company_name: str, website: str) -> Optional[str]:
        """Scrape LinkedIn URL from company website."""
        if not website:
            return None
        
        print(f"  {company_name:30s}", end=" ")
        
        # Fetch homepage
        html = self.fetch_homepage(website)
        if not html:
            print("→ Could not fetch")
            return None
        
        # Extract LinkedIn URL
        linkedin_url = self.extract_linkedin_url(html)
        
        if linkedin_url:
            print(f"→ ✅ {linkedin_url}")
        else:
            print("→ ⚠️  No LinkedIn found")
        
        return linkedin_url
    
    def cleanup(self):
        """Clean up Selenium driver."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


def main():
    """Main function to scrape LinkedIn URLs and update seed file."""
    print("="*70)
    print("Scraping LinkedIn URLs from Company Websites")
    print("="*70 + "\n")
    
    # Load seed file
    seed_path = Path(__file__).parent.parent / "data" / "forbes_ai50_seed.json"
    
    with open(seed_path) as f:
        companies = json.load(f)
    
    print(f"📋 Loaded {len(companies)} companies\n")
    
    scraper = LinkedInScraper(use_selenium=False)
    
    updated_count = 0
    found_count = 0
    
    try:
        for idx, company in enumerate(companies, 1):
            company_name = company.get('company_name', '')
            website = company.get('website', '')
            
            print(f"[{idx}/{len(companies)}]", end=" ")
            
            if not website:
                print(f"  {company_name:30s} → ⚠️  No website")
                continue
            
            # Scrape LinkedIn URL
            linkedin_url = scraper.scrape_linkedin(company_name, website)
            
            if linkedin_url:
                company['linkedin'] = linkedin_url
                found_count += 1
            else:
                company['linkedin'] = None
            
            updated_count += 1
            time.sleep(1)  # Rate limiting
        
        # Save updated seed file
        with open(seed_path, 'w') as f:
            json.dump(companies, f, indent=2)
        
        print("\n" + "="*70)
        print(f"✅ Successfully updated {updated_count} companies")
        print(f"✅ Found LinkedIn URLs for {found_count}/{len(companies)} companies")
        print(f"✅ Saved to {seed_path}")
        print("="*70)
        
        print(f"\n📊 Summary:")
        print(f"  Companies with LinkedIn: {found_count}/{len(companies)}")
        print(f"  Companies without LinkedIn: {len(companies) - found_count}/{len(companies)}")
        
        if found_count < len(companies):
            print(f"\n💡 Note: Some companies don't have LinkedIn links on their homepage.")
            print(f"   These will be left as null in the seed file.")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print("Saving partial results...")
        with open(seed_path, 'w') as f:
            json.dump(companies, f, indent=2)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.cleanup()


if __name__ == "__main__":
    main()
