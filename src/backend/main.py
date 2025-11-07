"""
ORBIT - Dual Pipeline PE Intelligence
RAG vs Structured with Evaluation
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
    version="7.0.0",
    description="RAG vs Structured comparison with evaluation"
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


class EvaluationScore(BaseModel):
    factual_correctness: int = Field(..., ge=0, le=3, description="0-3 points")
    schema_adherence: int = Field(..., ge=0, le=2, description="0-2 points")
    provenance_use: int = Field(..., ge=0, le=2, description="0-2 points")
    hallucination_control: int = Field(..., ge=0, le=2, description="0-2 points")
    readability: int = Field(..., ge=0, le=1, description="0-1 points")
    total_score: int = Field(..., ge=0, le=10)
    notes: str


# ============================================================================
# Scraping (Shared)
# ============================================================================

async def scrape_page_live(url: str) -> Dict:
    """Scrape a single page"""
    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0'}
        ) as client:
            response = await client.get(url)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for tag in soup(['script', 'style', 'nav', 'footer', 'iframe']):
            tag.decompose()
        
        text = soup.get_text(separator='\n', strip=True)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        clean_text = '\n'.join(lines)
        
        return {
            'url': url,
            'content': clean_text[:15000],
            'success': True
        }
    
    except Exception as e:
        return {
            'url': url,
            'error': str(e),
            'success': False
        }


async def scrape_company_realtime(company_name: str, website: str) -> Dict:
    """Scrape company pages"""
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
    
    pages = {}
    for (url, page_type), result in zip(urls, results):
        if result.get('success') and len(result.get('content', '')) > 100:
            if page_type not in pages:
                pages[page_type] = result['content']
    
    all_text = '\n\n'.join([f"=== {ptype.upper()} ===\n{content}" 
                            for ptype, content in pages.items()])
    
    logger.info(f"  ✓ Scraped {len(pages)} pages")
    
    return {
        'company_name': company_name,
        'website': website,
        'pages_found': list(pages.keys()),
        'combined_text': all_text,
        'raw_pages': pages
    }


# ============================================================================
# RAG Pipeline
# ============================================================================

def generate_rag_dashboard(scraped_data: Dict) -> str:
    """
    RAG Pipeline: Raw text → Vector search → LLM → Dashboard
    (Simplified: directly use raw text as context)
    """
    logger.info(f"📊 RAG PIPELINE: {scraped_data['company_name']}")
    
    # Simulate RAG: use raw text as retrieval context
    context = scraped_data['combined_text'][:15000]
    
    prompt = f"""You are generating an investor PE dashboard using RAG (Retrieval-Augmented Generation).

Company: {scraped_data['company_name']}

Retrieved Context from Vector Database:
{context}

Generate a professional PE dashboard with these EXACT sections:

## Company Overview
## Business Model and GTM
## Funding & Investor Profile
## Growth Momentum
## Visibility & Market Sentiment
## Risks and Challenges
## Outlook
## Disclosure Gaps

RULES:
- Use ONLY information from the retrieved context
- Say "Not disclosed" for missing data
- Be factual, no speculation
- Include disclosure gaps section"""
    
    result = call_gemini_with_retry(prompt)
    logger.info(f"  ✓ RAG dashboard generated")
    return result


# ============================================================================
# Structured Pipeline
# ============================================================================

def extract_structured_data(scraped_data: Dict) -> Dict:
    """Extract structured Pydantic-style data"""
    logger.info(f"🤖 STRUCTURED EXTRACTION: {scraped_data['company_name']}")
    
    prompt = f"""Extract structured investor data in JSON format.

Company: {scraped_data['company_name']}
Content:
{scraped_data['combined_text'][:20000]}

Return ONLY valid JSON:
{{
  "company_record": {{
    "legal_name": "string",
    "hq_city": "string",
    "hq_country": "string",
    "founded_year": 2020,
    "categories": ["cat1"],
    "description": "2-3 sentences",
    "total_raised_usd": 50000000.0,
    "last_round_name": "Series B",
    "last_disclosed_valuation_usd": null
  }},
  "products": [
    {{
      "name": "Product",
      "description": "Description",
      "pricing_model": "enterprise",
      "target_customers": "Who"
    }}
  ],
  "leadership": [
    {{
      "name": "Name",
      "role": "CEO",
      "previous_affiliation": "ex-Company"
    }}
  ],
  "key_metrics": {{
    "hiring_momentum": "Growing",
    "engineering_openings": 10,
    "recent_news": "News"
  }}
}}

Use null for missing data. Don't invent."""
    
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
    
    prompt = f"""Generate an investor PE dashboard using STRUCTURED data.

Company: {company_name}

Structured Payload:
{json.dumps(extracted_data, indent=2)}

Generate dashboard with these EXACT sections:

## Company Overview
## Business Model and GTM
## Funding & Investor Profile
## Growth Momentum
## Visibility & Market Sentiment
## Risks and Challenges
## Outlook
## Disclosure Gaps

RULES:
- Use ONLY the structured data provided
- Say "Not disclosed" for null values
- Be precise and factual
- Include disclosure gaps"""
    
    result = call_gemini_with_retry(prompt)
    logger.info(f"  ✓ Structured dashboard generated")
    return result


# ============================================================================
# Evaluation
# ============================================================================

def evaluate_dashboards(rag_dashboard: str, structured_dashboard: str, scraped_data: Dict) -> Dict:
    """
    Evaluate both dashboards using the rubric
    
    Rubric (10 points total):
    - Factual correctness (0-3)
    - Schema adherence (0-2)
    - Provenance use (0-2)
    - Hallucination control (0-2)
    - Readability (0-1)
    """
    logger.info("🔍 EVALUATING both pipelines...")
    
    prompt = f"""Evaluate these two PE dashboards against each other.

SCRAPED SOURCE DATA (ground truth):
{scraped_data['combined_text'][:10000]}

RAG DASHBOARD:
{rag_dashboard}

STRUCTURED DASHBOARD:
{structured_dashboard}

Evaluate each dashboard using this rubric (0-10 points):

1. Factual Correctness (0-3): Are claims accurate vs source data?
2. Schema Adherence (0-2): Does it follow the 8-section format?
3. Provenance Use (0-2): Does it properly cite sources and say "Not disclosed"?
4. Hallucination Control (0-2): Does it avoid inventing data?
5. Readability (0-1): Is it clear and useful for investors?

Return ONLY JSON:
{{
  "rag_scores": {{
    "factual_correctness": 2,
    "schema_adherence": 2,
    "provenance_use": 1,
    "hallucination_control": 2,
    "readability": 1,
    "total_score": 8,
    "notes": "Strengths and weaknesses"
  }},
  "structured_scores": {{
    "factual_correctness": 3,
    "schema_adherence": 2,
    "provenance_use": 2,
    "hallucination_control": 2,
    "readability": 1,
    "total_score": 10,
    "notes": "Strengths and weaknesses"
  }},
  "winner": "structured",
  "reasoning": "Why one is better"
}}"""
    
    result_text = call_gemini_with_retry(prompt)
    
    import re
    text = result_text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    
    if json_match:
        evaluation = json.loads(json_match.group())
        logger.info(f"  ✓ Evaluation complete")
        return evaluation
    
    return {"error": "Evaluation failed"}


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
def root():
    return {
        "name": "ORBIT Dual Pipeline",
        "version": "7.0.0",
        "pipelines": ["RAG", "Structured"],
        "evaluation": "10-point rubric"
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
    """
    Run BOTH pipelines and compare them
    
    Flow:
    1. Scrape company (shared)
    2. RAG pipeline → dashboard
    3. Structured pipeline → extraction → dashboard
    4. Evaluate both
    5. Return comparison
    """
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 DUAL PIPELINE COMPARISON: {request.company_name}")
        logger.info(f"{'='*80}")
        
        # STEP 1: Scrape (shared by both)
        logger.info("  [1/5] 🕷️  Scraping website...")
        scraped = await scrape_company_realtime(request.company_name, request.website)
        
        if not scraped.get('combined_text'):
            raise HTTPException(500, "Scraping failed")
        
        # STEP 2: RAG Pipeline
        logger.info("  [2/5] 📊 Running RAG pipeline...")
        rag_dashboard = generate_rag_dashboard(scraped)
        
        # STEP 3: Structured Pipeline - Extract
        logger.info("  [3/5] 🤖 Running Structured pipeline (extraction)...")
        extracted_data = extract_structured_data(scraped)
        
        if 'error' in extracted_data:
            raise HTTPException(500, f"Extraction failed: {extracted_data['error']}")
        
        # STEP 4: Structured Pipeline - Dashboard
        logger.info("  [4/5] 📊 Running Structured pipeline (dashboard)...")
        structured_dashboard = generate_structured_dashboard(extracted_data, request.company_name)
        
        # STEP 5: Evaluate
        logger.info("  [5/5] 🔍 Evaluating both pipelines...")
        evaluation = evaluate_dashboards(rag_dashboard, structured_dashboard, scraped)
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(f"  ✅ COMPLETE in {elapsed:.1f}s")
        logger.info(f"     RAG Score: {evaluation.get('rag_scores', {}).get('total_score', 0)}/10")
        logger.info(f"     Structured Score: {evaluation.get('structured_scores', {}).get('total_score', 0)}/10")
        logger.info(f"     Winner: {evaluation.get('winner', 'unknown')}")
        logger.info(f"{'='*80}\n")
        
        return {
            "company_name": request.company_name,
            "pages_scraped": scraped.get('pages_found', []),
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
        logger.error(f"❌ Dual pipeline failed: {e}")
        raise HTTPException(500, str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
