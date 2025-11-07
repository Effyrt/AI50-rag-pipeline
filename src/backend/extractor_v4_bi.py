"""
Self-contained 5-pass extraction with Business Intelligence + Employee Data.
Pass 1: Company + Events
Pass 2: Products + Leadership  
Pass 3: GitHub Metrics (placeholder - not implemented yet)
Pass 4: Business Intelligence
Pass 5: Employee Count + Job Openings
"""
import os
import json
import uuid
from pydantic import BaseModel
from typing import Optional, List, Dict
from pathlib import Path
from datetime import date, datetime
from dotenv import load_dotenv

import instructor
from openai import OpenAI
from .models import Company, Event, Product, Leadership, Snapshot, Visibility, Provenance
from .employee_extractor import EmployeeDataExtractor
from .text_preprocessor import TextPreprocessor
from .github_api import get_github_visibility

# Load environment variables
load_dotenv()


# Data models for multi-pass extraction
class Pass1Data(BaseModel):
    """Pass 1: Company basics + Events"""
    company: Company
    events: List[Event] = []


class Pass2Data(BaseModel):
    """Pass 2: Products + Leadership"""
    products: List[Product] = []
    leadership: List[Leadership] = []


# Business Intelligence model
class BusinessIntelligence(BaseModel):
    """Business intelligence fields extracted from website content"""
    # Marketing & Positioning
    value_proposition: Optional[str] = None
    product_description: Optional[str] = None
    target_customer_segments: List[str] = []
    key_competitors: List[str] = []
    competitive_differentiation: Optional[str] = None
    
    # Business Model
    industry_primary: Optional[str] = None
    industry_tags: List[str] = []
    revenue_model: Optional[str] = None
    revenue_streams: List[str] = []
    primary_customer_type: Optional[str] = None
    
    # Go-to-Market
    sales_motion: Optional[str] = None
    gtm_channels: List[str] = []
    
    # Pricing
    pricing_model: Optional[str] = None
    pricing_disclosed: bool = False
    free_tier_available: bool = False
    free_tier_limitations: Optional[str] = None
    
    # Partnerships & Markets
    technology_partnerships: List[str] = []
    geographic_markets: List[str] = []
    
    # Funding Stage (inferred)
    company_stage: Optional[str] = None


# Extracted data container
class ExtractedData:
    """Container for all extracted data"""
    def __init__(self):
        self.company: Optional[Company] = None
        self.events: List[Event] = []
        self.products: List[Product] = []
        self.leadership: List[Leadership] = []
        self.snapshots: List[Snapshot] = []
        self.visibility: List[Visibility] = []


class EnhancedExtractor:
    """Self-contained 5-pass extractor with Business Intelligence + Employee Data"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize extractor with OpenAI client
        
        Args:
            model: OpenAI model to use (default: gpt-4o-mini)
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = instructor.patch(OpenAI(api_key=api_key))
        self.model = model
        self.preprocessor = TextPreprocessor()
        self.employee_extractor = EmployeeDataExtractor()
        
        print(f"✅ Initialized EnhancedExtractor with model: {model}")
    
    def load_scraped_data(self, company_dir: Path, forbes_seed: dict = None) -> Dict[str, Dict]:
        """
        Load scraped data from company directory
        
        Args:
            company_dir: Directory containing scraped files
            forbes_seed: Forbes seed data (list of company dicts)
            
        Returns:
            Dictionary with page_type -> {text, source_url, crawled_at}
        """
        scraped_data = {}
        
        # Load metadata if available
        metadata_file = company_dir / "metadata.json"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
        
        # Find company_id from directory name or metadata
        company_id = company_dir.name
        
        # Find Forbes data for this company
        forbes_info = None
        if forbes_seed:
            if isinstance(forbes_seed, list):
                forbes_info = next((c for c in forbes_seed if c.get('company_id') == company_id), None)
            elif isinstance(forbes_seed, dict) and forbes_seed.get('company_id') == company_id:
                forbes_info = forbes_seed
        
        # Load text files for each page type
        page_types = ['homepage', 'about', 'product', 'careers', 'blog', 
                     'pricing', 'customers', 'partners', 'press', 'team']
        
        for page_type in page_types:
            text_file = company_dir / f"{page_type}.txt"
            if text_file.exists():
                text = text_file.read_text(encoding='utf-8')
                
                # Find source URL from metadata
                source_url = ""
                crawled_at = datetime.utcnow().isoformat() + 'Z'
                
                if metadata:
                    pages_scraped = metadata.get('pages_scraped', [])
                    if isinstance(pages_scraped, list):
                        for page in pages_scraped:
                            if isinstance(page, dict) and page.get('page_type') == page_type:
                                source_url = page.get('source_url', '')
                                crawled_at = page.get('crawled_at', crawled_at)
                                break
                
                scraped_data[page_type] = {
                    'text': text,
                    'source_url': source_url,
                    'crawled_at': crawled_at
                }
        
        # Add Forbes data as "official source"
        if forbes_info:
            forbes_text = f"""
OFFICIAL SOURCE - Forbes AI 50:
Company: {forbes_info.get('company_name', '')}
Legal Name: {forbes_info.get('legal_name', forbes_info.get('company_name', ''))}
Description: {forbes_info.get('description', '')}
Funding: {forbes_info.get('funding', '')}
Founded: {forbes_info.get('founded_year', '')}
HQ: {forbes_info.get('hq_city', '')}, {forbes_info.get('hq_country', '')}
Categories: {', '.join(forbes_info.get('categories', []))}
Website: {forbes_info.get('website', '')}
LinkedIn: {forbes_info.get('linkedin', '')}
"""
            scraped_data['forbes'] = {
                'text': forbes_text,
                'source_url': forbes_info.get('forbes_url', ''),
                'crawled_at': datetime.utcnow().isoformat() + 'Z'
            }
        
        return scraped_data
    
    def build_extraction_context(self, scraped_data: Dict[str, Dict]) -> str:
        """
        Build context string from scraped data with smart filtering
        
        Args:
            scraped_data: Dictionary with page_type -> {text, source_url, crawled_at}
            
        Returns:
            Formatted context string
        """
        # Preprocess with smart filtering
        filtered_data = self.preprocessor.preprocess_scraped_data(scraped_data)
        
        context_parts = []
        
        # Prioritize Forbes data
        if 'forbes' in filtered_data:
            context_parts.append("=== OFFICIAL SOURCE: Forbes AI 50 ===\n")
            context_parts.append(filtered_data['forbes'])
            context_parts.append("\n")
        
        # Add other pages in priority order
        priority_order = ['homepage', 'about', 'product', 'blog', 'press', 
                         'careers', 'pricing', 'customers', 'partners', 'team']
        
        for page_type in priority_order:
            if page_type in filtered_data:
                context_parts.append(f"=== {page_type.upper()} PAGE ===\n")
                context_parts.append(filtered_data[page_type])
                context_parts.append("\n")
        
        return "\n".join(context_parts)
    
    def extract_structured_data(self, company_dir: Path, forbes_seed: dict = None) -> ExtractedData:
        """
        Extract structured data using 5-pass approach
        
        Args:
            company_dir: Directory containing scraped files
            forbes_seed: Forbes seed data
            
        Returns:
            ExtractedData object with all extracted information
        """
        extracted = ExtractedData()
        
        # Load scraped data
        scraped_data = self.load_scraped_data(company_dir, forbes_seed)
        
        if not scraped_data:
            print("   ⚠️  No scraped data found")
            return extracted
        
        # Find company_id
        company_id = company_dir.name
        
        # Find Forbes info for company_id
        forbes_info = None
        if forbes_seed:
            if isinstance(forbes_seed, list):
                forbes_info = next((c for c in forbes_seed if c.get('company_id') == company_id), None)
            elif isinstance(forbes_seed, dict) and forbes_seed.get('company_id') == company_id:
                forbes_info = forbes_seed
        
        # === PASS 1: Company Basics + Events ===
        print(f"   📋 Pass 1: Company + Events...")
        
        context = self.build_extraction_context(scraped_data)
        
        pass1_prompt = """Extract company basics and events from website content.

EXTRACT:
1. COMPANY: legal_name, brand_name, website, hq_city, hq_state, hq_country, founded_year, categories
2. EVENTS: funding rounds, product launches, partnerships, leadership changes, etc.

Use Forbes data as primary source for company basics. Extract events from blog/press pages.
Be concise. Use ONLY information from the content."""

        try:
            pass1_result = self.client.chat.completions.create(
                model=self.model,
                response_model=Pass1Data,
                messages=[
                    {"role": "system", "content": pass1_prompt},
                    {"role": "user", "content": context[:30000]}  # Limit context size
                ],
                max_tokens=6000,
                temperature=0.1,
                max_retries=1
            )
            
            extracted.company = pass1_result.company
            extracted.events = pass1_result.events
            
            # Ensure company_id matches
            extracted.company.company_id = company_id
            
            print(f"      ✅ Company: {extracted.company.legal_name}")
            print(f"      ✅ Events: {len(extracted.events)}")
            
        except Exception as e:
            print(f"      ⚠️  Pass 1 failed: {e}")
            # Create minimal company record
            if forbes_info:
                extracted.company = Company(
                    company_id=company_id,
                    legal_name=forbes_info.get('legal_name', forbes_info.get('company_name', 'Unknown')),
                    website=forbes_info.get('website'),
                    hq_city=forbes_info.get('hq_city'),
                    hq_country=forbes_info.get('hq_country'),
                    founded_year=forbes_info.get('founded_year'),
                    categories=forbes_info.get('categories', [])
                )
            else:
                extracted.company = Company(company_id=company_id, legal_name="Unknown")
        
        # === PASS 2: Products + Leadership ===
        print(f"   🏢 Pass 2: Products + Leadership...")
        
        try:
            pass2_prompt = """Extract products and leadership from website content.

EXTRACT:
1. PRODUCTS: name, description, pricing_model, pricing_tiers_public, ga_date
2. LEADERSHIP: name, role, is_founder, previous_affiliation, linkedin

MANDATORY: Extract at least 1 product and 1 leadership member if available.
Be concise. Use ONLY information from the content."""

            pass2_result = self.client.chat.completions.create(
                model=self.model,
                response_model=Pass2Data,
                messages=[
                    {"role": "system", "content": pass2_prompt},
                    {"role": "user", "content": context[:30000]}
                ],
                max_tokens=8000,
                temperature=0.1,
                max_retries=1
            )
            
            # Set company_id for all products and leadership
            for product in pass2_result.products:
                product.company_id = company_id
                if not product.product_id:
                    product.product_id = str(uuid.uuid4())
            
            for leader in pass2_result.leadership:
                leader.company_id = company_id
                if not leader.person_id:
                    leader.person_id = str(uuid.uuid4())
            
            extracted.products = pass2_result.products
            extracted.leadership = pass2_result.leadership
            
            print(f"      ✅ Products: {len(extracted.products)}")
            print(f"      ✅ Leadership: {len(extracted.leadership)}")
            
        except Exception as e:
            print(f"      ⚠️  Pass 2 failed: {e}")
        
        # === PASS 3: GitHub Metrics (placeholder) ===
        print(f"   🐙 Pass 3: GitHub Metrics...")
        try:
            github_data = get_github_visibility(scraped_data)
            if github_data:
                visibility = Visibility(
                    company_id=company_id,
                    as_of=date.today(),
                    github_stars=github_data.get('github_stars'),
                    github_forks=github_data.get('github_forks'),
                    github_contributors=github_data.get('github_contributors'),
                    github_url=github_data.get('github_url')
                )
                extracted.visibility.append(visibility)
                print(f"      ✅ GitHub: {github_data.get('github_stars', 0)} stars")
            else:
                print(f"      ℹ️  No GitHub data found")
        except Exception as e:
            print(f"      ⚠️  Pass 3 failed: {e}")
        
        # === PASS 4: Business Intelligence ===
        print(f"   🧠 Pass 4: Business Intelligence...")
        
        try:
            bi_prompt = """Extract business intelligence from website content.

EXTRACT:

1. POSITIONING & MARKETING:
   - Value proposition (1-2 sentences, what makes them unique)
   - Product description (concise summary of what they do)
   - Target customer segments (who they sell to)
   - Key competitors (if mentioned)
   - Competitive differentiation (how they're different)

2. BUSINESS MODEL:
   - Industry/sector (e.g., "AI-Powered Developer Tools")
   - Industry tags (keywords like "AI", "SaaS", "Developer Tools")
   - Revenue model (Subscription, Transactional, Freemium, etc.)
   - Revenue streams (sources of income)
   - Customer type (B2B SMB, B2B Enterprise, B2C, B2B2C)

3. GO-TO-MARKET:
   - Sales motion (Product-Led, Sales-Led, or Hybrid)
   - GTM channels (how they acquire customers)

4. PRICING:
   - Pricing model (Tiered, Usage-Based, Per-Seat, etc.)
   - Is pricing disclosed on website? (true/false)
   - Free tier available? (true/false)
   - Free tier limitations (if applicable)

5. PARTNERSHIPS & MARKETS:
   - Technology partnerships (AWS, Google Cloud, Microsoft, OpenAI, etc.)
   - Geographic markets (countries/regions they serve)

6. FUNDING STAGE (infer from content):
   - Company stage (Seed, Series A/B/C/D, etc.)

Be concise. Use ONLY information from the content. Mark as None if not available."""

            bi_data = self.client.chat.completions.create(
                model=self.model,
                response_model=BusinessIntelligence,
                messages=[
                    {"role": "system", "content": bi_prompt},
                    {"role": "user", "content": context[:30000]}
                ],
                max_tokens=4000,
                temperature=0.1,
                max_retries=1
            )
            
            # Merge BI data into company record
            if extracted.company:
                extracted.company.value_proposition = bi_data.value_proposition
                extracted.company.product_description = bi_data.product_description
                extracted.company.target_customer_segments = bi_data.target_customer_segments
                extracted.company.key_competitors = bi_data.key_competitors
                extracted.company.competitive_differentiation = bi_data.competitive_differentiation
                extracted.company.industry_primary = bi_data.industry_primary
                extracted.company.industry_tags = bi_data.industry_tags
                extracted.company.revenue_model = bi_data.revenue_model
                extracted.company.revenue_streams = bi_data.revenue_streams
                extracted.company.primary_customer_type = bi_data.primary_customer_type
                extracted.company.sales_motion = bi_data.sales_motion
                extracted.company.gtm_channels = bi_data.gtm_channels
                extracted.company.pricing_model = bi_data.pricing_model
                extracted.company.pricing_disclosed = bi_data.pricing_disclosed
                extracted.company.free_tier_available = bi_data.free_tier_available
                extracted.company.free_tier_limitations = bi_data.free_tier_limitations
                extracted.company.technology_partnerships = bi_data.technology_partnerships
                extracted.company.geographic_markets = bi_data.geographic_markets
                extracted.company.company_stage = bi_data.company_stage
            
            print(f"      ✅ Value prop: {bool(bi_data.value_proposition)}")
            print(f"      ✅ Industry: {bi_data.industry_primary or 'Not found'}")
            print(f"      ✅ Segments: {len(bi_data.target_customer_segments)}")
            print(f"      ✅ Competitors: {len(bi_data.key_competitors)}")
            print(f"      ✅ Partnerships: {len(bi_data.technology_partnerships)}")
            print(f"      ✅ Stage: {bi_data.company_stage or 'Not found'}")
            
        except Exception as e:
            print(f"      ⚠️  Pass 4 failed: {e}")
        
        # === PASS 5: Employee Count + Job Openings ===
        print(f"   👥 Pass 5: Employee & Hiring Data...")
        
        try:
            # Load page texts for employee extraction
            page_texts = {}
            for page_type in ['about', 'careers', 'homepage', 'team']:
                page_file = company_dir / f"{page_type}.txt"
                if page_file.exists():
                    page_texts[page_type] = page_file.read_text()
                else:
                    page_texts[page_type] = ''
            
            # Extract employee snapshot
            snapshot_data = self.employee_extractor.create_snapshot(
                company_id=company_id,
                about_text=page_texts.get('about', ''),
                careers_text=page_texts.get('careers', ''),
                homepage_text=page_texts.get('homepage', ''),
                team_text=page_texts.get('team', '')
            )
            
            if snapshot_data:
                # Add provenance
                provenance = []
                for page_type in ['about', 'careers', 'homepage', 'team']:
                    if page_texts.get(page_type):
                        # Find source URL from metadata
                        metadata_file = company_dir / "metadata.json"
                        if metadata_file.exists():
                            metadata = json.loads(metadata_file.read_text())
                            for page in metadata.get('pages_scraped', []):
                                if page.get('page_type') == page_type:
                                    provenance.append(Provenance(
                                        source_url=page.get('source_url', ''),
                                        crawled_at=page.get('crawled_at', datetime.utcnow().isoformat() + 'Z'),
                                        snippet=f"Extracted from {page_type} page"
                                    ))
                                    break
                
                snapshot_data['provenance'] = provenance
                
                # Create Snapshot object
                snapshot = Snapshot(**snapshot_data)
                extracted.snapshots.append(snapshot)
                
                # Log what we found
                print(f"      ✅ Employees: {snapshot.headcount_total or snapshot.headcount_estimate or 'Not found'}")
                print(f"      ✅ Job openings: {snapshot.job_openings_count or 'Not found'}")
                print(f"      ✅ Locations: {len(snapshot.office_locations)}")
                print(f"      ✅ Hiring focus: {', '.join(snapshot.hiring_focus) if snapshot.hiring_focus else 'Not found'}")
            else:
                print(f"      ℹ️  No employee/hiring data found")
                
        except Exception as e:
            print(f"      ⚠️  Pass 5 failed: {e}")
        
        return extracted
    
    def extract_company(self, company_dir: Path, output_dir: Path, forbes_seed: dict = None) -> Path:
        """
        Extract structured data and save to JSON file
        
        Args:
            company_dir: Directory containing scraped files
            output_dir: Directory to save output JSON
            forbes_seed: Forbes seed data
            
        Returns:
            Path to output JSON file
        """
        # Extract structured data
        extracted = self.extract_structured_data(company_dir, forbes_seed)
        
        if not extracted.company:
            raise ValueError(f"No company data extracted for {company_dir.name}")
        
        # Build output dictionary
        output_data = {
            "company": extracted.company.model_dump(),
            "events": [e.model_dump() for e in extracted.events],
            "products": [p.model_dump() for p in extracted.products],
            "leadership": [l.model_dump() for l in extracted.leadership],
            "snapshots": [s.model_dump() for s in extracted.snapshots],
            "visibility": [v.model_dump() for v in extracted.visibility]
        }
        
        # Save to JSON file
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{extracted.company.company_id}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        return output_file
