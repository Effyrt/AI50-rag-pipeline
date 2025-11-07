"""
ORBIT - Dual Pipeline PE Intelligence
RAG vs Structured with Evaluation + Working Fallback System
"""
import logging
import asyncio
import time
from typing import List, Dict, Any
from pathlib import Path
import json
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import httpx
from bs4 import BeautifulSoup
import google.generativeai as genai

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Import fallback handler
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from scrapers.fallback_handler import get_fallback_content
    logger.info("✅ Fallback handler loaded")
except Exception as e:
    logger.warning(f"⚠️ Fallback handler not available: {e}")
    def get_fallback_content(company_id):
        return {'success': False, 'error': 'No fallback'}

# Load Gemini
try:
    with open(PROJECT_ROOT / '.env') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY='):
                genai.configure(api_key=line.split('=', 1)[1].strip())
                logger.info("✅ Gemini configured")
                break
except Exception as e:
    logger.error(f"❌ Gemini config failed: {e}")

app = FastAPI(
    title="ORBIT Dual Pipeline Intelligence",
    version="7.1.0",
    description="RAG vs Structured comparison with working fallback system"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Rate limiting
last_llm_call = 0
MIN_CALL_INTERVAL = 3.0


def rate_limit_wait():
    """Enforce rate limiting"""
    global last_llm_call
    current = time.time()
    elapsed = current - last_llm_call
    
    if elapsed < MIN_CALL_INTERVAL:
        sleep_time = MIN_CALL_INTERVAL - elapsed
        logger.info(f"⏱️  Rate limiting: waiting {sleep_time:.1f}s")
        time.sleep(sleep_time)
    
    last_llm_call = time.time()


def call_gemini_with_retry(prompt: str, max_retries: int = 3) -> str:
    """Call Gemini with exponential backoff"""
    rate_limit_wait()
    
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel("gemini-2.0-flash-exp")
            result = model.generate_content(prompt)
            return result.text
        
        except Exception as e:
            error_str = str(e)
            
            if "429" in error_str or "Resource exhausted" in error_str:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 5
                    logger.warning(f"⚠️  Rate limit, retrying in {wait_time}s... ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception("Rate limit exceeded after retries")
            
            raise


# ============================================================================
# Models
# ============================================================================

class CompanyListItem(BaseModel):
    company_id: str
    company_name: str
    website: str
    rank: int


class DualPipelineRequest(BaseModel):
    company_id: str
    company_name: str
    website: str


# ============================================================================
# Scraping with Fallback - FIXED LOGIC
# ============================================================================

async def scrape_page_live(url: str) -> Dict:
    """Scrape a single page"""
    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        ) as client:
            response = await client.get(url)
        
        if response.status_code == 403:
            return {'url': url, 'blocked': True, 'success': False}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for tag in soup(['script', 'style', 'nav', 'footer', 'iframe']):
            tag.decompose()
        
        text = soup.get_text(separator='\n', strip=True)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        clean_text = '\n'.join(lines)
        
        return {
            'url': url,
            'content': clean_text[:15000],
            'success': True,
            'blocked': False
        }
    
    except Exception as e:
        return {'url': url, 'error': str(e), 'success': False, 'blocked': False}


async def scrape_company_realtime(company_name: str, website: str, company_id: str = None) -> Dict:
    """Scrape company pages with fallback for blocked sites"""
    logger.info(f"🔴 SCRAPING: {company_name}")
    
    if not website.startswith('http'):
        website = f"https://{website}"
    
    base = website.rstrip('/')
    
    urls = [
        (base, 'homepage'),
        (f"{base}/about", 'about'),
        (f"{base}/about-us", 'about'),
        (f"{base}/product", 'product'),
        (f"{base}/products", 'product'),
        (f"{base}/careers", 'careers'),
        (f"{base}/blog", 'blog'),
        (f"{base}/news", 'news'),
    ]
    
    tasks = [scrape_page_live(url) for url, _ in urls]
    results = await asyncio.gather(*tasks)
    
    # Count blocks
    blocked_count = sum(1 for r in results if r.get('blocked'))
    
    # Collect successful pages
    pages = {}
    for (url, page_type), result in zip(urls, results):
        if result.get('success') and len(result.get('content', '')) > 100:
            if page_type not in pages:
                pages[page_type] = result['content']
    
    logger.info(f"  ✓ Scraped {len(pages)} pages (blocked: {blocked_count})")
    
    # ============================================================================
    # FALLBACK LOGIC - Fixed to actually trigger
    # ============================================================================
    if len(pages) == 0 and blocked_count >= 4:
        logger.warning(f"⚠️  Website blocking detected ({blocked_count} pages blocked)")
        logger.info(f"     Attempting fallback for {company_name}...")
        
        # Normalize company_id
        if not company_id:
            company_id = company_name.lower().replace(' ', '-').replace('.', '')
        
        fallback = get_fallback_content(company_id)
        
        if fallback.get('success'):
            logger.info(f"     ✅ Using fallback data for {company_name}")
            return {
                'company_name': company_name,
                'website': website,
                'pages_found': ['fallback'],
                'combined_text': fallback['content'],
                'is_fallback': True
            }
        
        # No fallback and no scraped pages - return empty but valid
        logger.warning(f"     ⚠️  No fallback available, returning minimal data")
        return {
            'company_name': company_name,
            'website': website,
            'pages_found': [],
            'combined_text': f"Company: {company_name}\nWebsite: {website}\n\nNote: Website blocks automated scraping. No fallback data available.",
            'is_fallback': False,
            'scraping_blocked': True
        }
    
    # Normal success case
    all_text = '\n\n'.join([f"=== {ptype.upper()} ===\n{content}" 
                            for ptype, content in pages.items()])
    
    return {
        'company_name': company_name,
        'website': website,
        'pages_found': list(pages.keys()),
        'combined_text': all_text,
        'is_fallback': False
    }


# ============================================================================
# RAG Pipeline
# ============================================================================

def generate_rag_dashboard(scraped_data: Dict) -> str:
    """RAG Pipeline"""
    logger.info(f"📊 RAG PIPELINE: {scraped_data['company_name']}")
    
    context = scraped_data['combined_text'][:15000]
    
    prompt = f"""Generate an investor PE dashboard using RAG.

Company: {scraped_data['company_name']}

Context:
{context}

Generate with EXACT sections:
## Company Overview
## Business Model and GTM
## Funding & Investor Profile
## Growth Momentum
## Visibility & Market Sentiment
## Risks and Challenges
## Outlook
## Disclosure Gaps

Use ONLY provided context. Say "Not disclosed" for missing data."""
    
    result = call_gemini_with_retry(prompt)
    logger.info(f"  ✓ RAG dashboard generated")
    return result


# ============================================================================
# Structured Pipeline
# ============================================================================

def extract_structured_data(scraped_data: Dict) -> Dict:
    """Extract structured data"""
    logger.info(f"🤖 STRUCTURED EXTRACTION: {scraped_data['company_name']}")
    
    prompt = f"""Extract structured investor data in JSON.

Company: {scraped_data['company_name']}
Content:
{scraped_data['combined_text'][:20000]}

Return ONLY valid JSON (no markdown):
{{
  "company_record": {{
    "legal_name": "string",
    "hq_city": "string",
    "hq_country": "string",
    "founded_year": 2020,
    "categories": ["cat1"],
    "description": "2-3 sentences",
    "total_raised_usd": 50000000.0
  }},
  "products": [{{"name": "Product", "description": "Description"}}],
  "leadership": [{{"name": "Name", "role": "CEO"}}]
}}

Use null for missing data."""
    
    result_text = call_gemini_with_retry(prompt)
    
    import re
    text = result_text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    
    if json_match:
        data = json.loads(json_match.group())
        logger.info(f"  ✓ Structured extraction complete")
        return data
    
    return {"error": "Extraction failed"}


def generate_structured_dashboard(extracted_data: Dict, company_name: str) -> str:
    """Generate dashboard from structured data"""
    logger.info(f"📊 STRUCTURED PIPELINE: {company_name}")
    
    prompt = f"""Generate PE dashboard using STRUCTURED data.

Company: {company_name}
Data:
{json.dumps(extracted_data, indent=2)}

Generate with EXACT sections:
## Company Overview
## Business Model and GTM
## Funding & Investor Profile
## Growth Momentum
## Visibility & Market Sentiment
## Risks and Challenges
## Outlook
## Disclosure Gaps

Use ONLY the structured data. Say "Not disclosed" for null values."""
    
    result = call_gemini_with_retry(prompt)
    logger.info(f"  ✓ Structured dashboard generated")
    return result


# ============================================================================
# Evaluation
# ============================================================================

def evaluate_dashboards(rag_dashboard: str, structured_dashboard: str, scraped_data: Dict) -> Dict:
    """Evaluate both dashboards"""
    logger.info("🔍 EVALUATING...")
    
    prompt = f"""Evaluate these PE dashboards.

SOURCE: {scraped_data['combined_text'][:10000]}

RAG: {rag_dashboard}

STRUCTURED: {structured_dashboard}

Return ONLY JSON:
{{
  "rag_scores": {{"factual_correctness": 2, "schema_adherence": 2, "provenance_use": 1, "hallucination_control": 2, "readability": 1, "total_score": 8, "notes": "..."}},
  "structured_scores": {{"factual_correctness": 3, "schema_adherence": 2, "provenance_use": 2, "hallucination_control": 2, "readability": 1, "total_score": 10, "notes": "..."}},
  "winner": "structured",
  "reasoning": "..."
}}"""
    
    result_text = call_gemini_with_retry(prompt)
    
    import re
    text = result_text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    
    if json_match:
        return json.loads(json_match.group())
    
    return {"error": "Evaluation failed"}


# ============================================================================
# API
# ============================================================================

@app.get("/")
def root():
    return {
        "name": "ORBIT Dual Pipeline",
        "version": "7.1.0",
        "features": ["Working fallback system", "10-point evaluation"]
    }


@app.get("/health")
def health():
    return {"status": "operational", "mode": "dual-pipeline"}


@app.get("/api/companies/list", response_model=List[CompanyListItem])
async def get_companies_list():
    """Get Forbes AI 50"""
    try:
        forbes_file = PROJECT_ROOT / "data" / "forbes_ai50_seed.json"
        with open(forbes_file) as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/dual-pipeline/compare")
async def dual_pipeline_comparison(request: DualPipelineRequest):
    """Run BOTH pipelines with fallback support"""
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 DUAL PIPELINE: {request.company_name}")
        logger.info(f"{'='*80}")
        
        # STEP 1: Scrape with fallback (never fails now)
        logger.info("  [1/5] 🕷️  Scraping...")
        scraped = await scrape_company_realtime(
            request.company_name,
            request.website,
            request.company_id
        )
        
        if scraped.get('is_fallback'):
            logger.info("     ℹ️  Using fallback data")
        elif scraped.get('scraping_blocked'):
            logger.info("     ⚠️  Scraping blocked, using minimal data")
        
        # STEP 2: RAG
        logger.info("  [2/5] 📊 RAG pipeline...")
        rag_dashboard = generate_rag_dashboard(scraped)
        
        # STEP 3: Extract
        logger.info("  [3/5] 🤖 Structured extraction...")
        extracted_data = extract_structured_data(scraped)
        
        # STEP 4: Structured
        logger.info("  [4/5] 📊 Structured dashboard...")
        structured_dashboard = generate_structured_dashboard(extracted_data, request.company_name)
        
        # STEP 5: Evaluate
        logger.info("  [5/5] 🔍 Evaluating...")
        evaluation = evaluate_dashboards(rag_dashboard, structured_dashboard, scraped)
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(f"  ✅ COMPLETE in {elapsed:.1f}s")
        logger.info(f"     RAG: {evaluation.get('rag_scores', {}).get('total_score', 0)}/10")
        logger.info(f"     Structured: {evaluation.get('structured_scores', {}).get('total_score', 0)}/10")
        logger.info(f"     Winner: {evaluation.get('winner', 'unknown')}")
        logger.info(f"{'='*80}\n")
        
        return {
            "company_name": request.company_name,
            "pages_scraped": scraped.get('pages_found', []),
            "is_fallback": scraped.get('is_fallback', False),
            "scraping_blocked": scraped.get('scraping_blocked', False),
            "rag_pipeline": {
                "dashboard": rag_dashboard,
                "scores": evaluation.get('rag_scores', {})
            },
            "structured_pipeline": {
                "extracted_data": extracted_data,
                "dashboard": structured_dashboard,
                "scores": evaluation.get('structured_scores', {})
            },
            "evaluation": evaluation,
            "processing_time_seconds": elapsed,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        raise HTTPException(500, str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
