"""
Enrichment scraper to find company websites and LinkedIn URLs.
Takes company names from Forbes scrape and finds their official URLs.
"""
import json
import time
import re
import uuid
from pathlib import Path
from typing import Optional, Dict
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


class CompanyEnricher:
    """Enriches company data with websites and LinkedIn URLs."""
    
    def __init__(self, use_selenium: bool = True):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
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
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
            print("✅ Selenium WebDriver initialized\n")
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize Selenium: {e}")
            self.use_selenium = False
            self.driver = None
    
    def construct_website_url(self, company_name: str) -> Optional[str]:
        """
        Construct likely website URL from company name.
        Try common patterns first before searching.
        """
        # Clean company name
        name = company_name.lower()
        name = re.sub(r'\s+(ai|labs|inc|corp|llc)$', '', name)
        name = name.replace(' ', '')
        name = name.replace('.', '')
        
        # Common domain patterns
        patterns = [
            f"{name}.com",
            f"{name}.ai",
            f"{name}.io",
            f"www.{name}.com",
        ]
        
        # Special cases
        special_cases = {
            'openai': 'openai.com',
            'anthropic': 'anthropic.com',
            'huggingface': 'huggingface.co',
            'cohere': 'cohere.com',
            'midjourney': 'midjourney.com',
            'mistralai': 'mistral.ai',
            'perplexityai': 'perplexity.ai',
            'runwayml': 'runwayml.com',
            'elevenlabs': 'elevenlabs.io',
            'databricks': 'databricks.com',
            'scaleai': 'scale.com',
            'glean': 'glean.com',
            'notion': 'notion.so',
            'deepl': 'deepl.com',
            'abridge': 'abridge.com',
            'anysphere': 'cursor.sh',
            'baseten': 'baseten.co',
            'captions': 'captions.ai',
            'clay': 'clay.com',
            'coactiveai': 'coactive.ai',
            'crusoe': 'crusoeenergy.com',
            'decagon': 'decagon.ai',
            'figureai': 'figure.ai',
            'fireworksai': 'fireworks.ai',
            'harvey': 'harvey.ai',
            'hebbia': 'hebbia.ai',
            'lambda': 'lambdalabs.com',
            'langchain': 'langchain.com',
            'luminance': 'luminance.com',
            'mercor': 'mercor.com',
            'openevidence': 'openevidence.com',
            'photoroom': 'photoroom.com',
            'pika': 'pika.art',
            'sakanaai': 'sakana.ai',
            'sambanova': 'sambanova.ai',
            'sierra': 'sierra.ai',
            'skildai': 'skild.ai',
            'snorkelai': 'snorkel.ai',
            'speak': 'speak.com',
            'stackblitz': 'stackblitz.com',
            'suno': 'suno.ai',
            'synthesia': 'synthesia.io',
            'thinkingmachinelabs': 'thinkingmachinelabs.com',
            'togetherai': 'together.ai',
            'vannevarlabs': 'vannevarlabs.com',
            'vastdata': 'vastdata.com',
            'windsurf': 'codeium.com/windsurf',
            'worldlabs': 'worldlabs.ai',
            'writer': 'writer.com',
            'xai': 'x.ai',
        }
        
        # Check special cases first
        clean_name = company_name.lower().replace(' ', '').replace('.', '')
        if clean_name in special_cases:
            return f"https://{special_cases[clean_name]}"
        
        # Try common patterns
        for pattern in patterns:
            url = f"https://{pattern}"
            try:
                response = self.session.head(url, timeout=5, allow_redirects=True)
                if response.status_code < 400:
                    return response.url
            except:
                continue
        
        return None
    
    def construct_linkedin_url(self, company_name: str) -> Optional[str]:
        """Construct likely LinkedIn URL from company name."""
        # Clean company name for LinkedIn slug
        name = company_name.lower()
        name = re.sub(r'\s+', '-', name)
        name = re.sub(r'[^\w-]', '', name)
        
        # Common LinkedIn patterns
        patterns = [
            f"https://www.linkedin.com/company/{name}",
            f"https://www.linkedin.com/company/{name}-ai",
            f"https://www.linkedin.com/company/{name}ai",
        ]
        
        # Try to verify LinkedIn URL
        for url in patterns:
            try:
                response = self.session.head(url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    return url
            except:
                continue
        
        # Return most likely pattern even if can't verify
        return f"https://www.linkedin.com/company/{name}"
    
    def search_google_for_website(self, company_name: str) -> Optional[str]:
        """Search Google for company official website."""
        if not self.driver:
            return None
        
        try:
            query = f"{company_name} official website"
            search_url = f"https://www.google.com/search?q={quote_plus(query)}"
            
            self.driver.get(search_url)
            time.sleep(2)
            
            # Look for search results
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            links = soup.find_all('a', href=True)
            
            # Filter for likely official websites
            for link in links[:20]:
                href = link.get('href', '')
                if '/url?q=' in href:
                    url = href.split('/url?q=')[1].split('&')[0]
                    if url.startswith('http') and 'google.com' not in url and 'forbes.com' not in url:
                        return url
            
            return None
        except Exception as e:
            print(f"    Error searching Google: {e}")
            return None
    
    def enrich_company(self, company: Dict) -> Dict:
        """Enrich a single company with website and LinkedIn."""
        company_name = company.get('company_name', '')
        
        print(f"  Enriching: {company_name}")
        
        # Try to construct website URL
        website = self.construct_website_url(company_name)
        
        # If construction failed, try Google search
        if not website and self.driver:
            print(f"    Searching Google for website...")
            website = self.search_google_for_website(company_name)
        
        # Construct LinkedIn URL
        linkedin = self.construct_linkedin_url(company_name)
        
        # Add enriched data
        enriched = company.copy()
        enriched['company_id'] = str(uuid.uuid4())
        enriched['website'] = website
        enriched['linkedin'] = linkedin
        
        # Map description to categories
        desc = company.get('description', '').lower()
        categories = []
        
        category_keywords = {
            'Healthcare AI': ['doctor', 'medical', 'health', 'clinical'],
            'Large Language Models': ['model developer', 'llm', 'language model'],
            'AI Coding': ['coding', 'development', 'developer'],
            'Video AI': ['video', 'image editing'],
            'Sales AI': ['go-to-market', 'sales'],
            'Computer Vision': ['vision', 'image'],
            'Translation': ['translation', 'language'],
            'Voice AI': ['voice', 'speech', 'audio'],
            'Robotics': ['robot', 'humanoid'],
            'Data Analytics': ['analytics', 'data storage'],
            'Enterprise Search': ['search engine', 'enterprise'],
            'Legal AI': ['legal', 'contract'],
            'Finance AI': ['finance', 'fintech'],
            'Customer Service AI': ['customer service', 'support'],
            'Music AI': ['music', 'sound'],
            'AI Infrastructure': ['infrastructure', 'cloud', 'chipmaker'],
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in desc for kw in keywords):
                categories.append(category)
        
        if not categories:
            categories = ['Artificial Intelligence']
        
        enriched['categories'] = categories[:3]  # Max 3 categories
        enriched['related_companies'] = []
        
        print(f"    Website: {website or 'Not found'}")
        print(f"    LinkedIn: {linkedin}")
        
        time.sleep(1)  # Rate limiting
        
        return enriched
    
    def cleanup(self):
        """Clean up Selenium driver."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


def main():
    """Main enrichment function."""
    print("="*60)
    print("Company Data Enrichment - Finding Websites & LinkedIn URLs")
    print("="*60 + "\n")
    
    # Load parsed Forbes data
    input_path = Path(__file__).parent.parent / "data" / "forbes_parsed_detailed.json"
    output_path = Path(__file__).parent.parent / "data" / "forbes_ai50_seed.json"
    
    with open(input_path) as f:
        companies = json.load(f)
    
    print(f"📋 Loaded {len(companies)} companies from Forbes scrape\n")
    
    enricher = CompanyEnricher(use_selenium=True)
    enriched_companies = []
    
    try:
        for idx, company in enumerate(companies, 1):
            print(f"[{idx}/{len(companies)}]")
            enriched = enricher.enrich_company(company)
            enriched_companies.append(enriched)
            print()
        
        # Save enriched data
        with open(output_path, 'w') as f:
            json.dump(enriched_companies, f, indent=2)
        
        print("="*60)
        print(f"✅ Successfully enriched {len(enriched_companies)} companies")
        print(f"✅ Saved to {output_path}")
        print("="*60)
        
        # Print summary
        websites_found = sum(1 for c in enriched_companies if c.get('website'))
        print(f"\n📊 Summary:")
        print(f"  Companies with websites: {websites_found}/{len(enriched_companies)}")
        print(f"  Companies with LinkedIn: {len(enriched_companies)}/{len(enriched_companies)}")
        print(f"  Companies with HQ info: {sum(1 for c in enriched_companies if c.get('hq_city'))}/{len(enriched_companies)}")
        print(f"  Companies with founded year: {sum(1 for c in enriched_companies if c.get('founded_year'))}/{len(enriched_companies)}")
        
        print("\n📝 Next step:")
        print("  Run: python src/scraper.py")
        print("  This will scrape full page content from all 50 company websites (Lab 1)")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        enricher.cleanup()


if __name__ == "__main__":
    main()




