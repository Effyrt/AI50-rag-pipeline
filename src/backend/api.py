"""
ORBIT Backend API - Debug Version
"""
import json
import re
from pathlib import Path
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="ORBIT API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
COMPANIES_DIR = DATA_DIR / "companies"

COMPANIES_DIR.mkdir(parents=True, exist_ok=True)

class CompanyListItem(BaseModel):
    company_id: str
    company_name: str
    website: str
    rank: int

class CompanyRequest(BaseModel):
    company_id: str
    company_name: str
    website: str

def clean_html_from_text(text: str) -> str:
    """Strip HTML tags from text"""
    if not text or text in ['Not disclosed', 'None', None]:
        return None
    cleaned = re.sub(r'<[^>]+>', '', str(text))
    cleaned = re.sub(r'&\w+;', '', cleaned)
    cleaned = ' '.join(cleaned.split())
    return cleaned.strip() if cleaned.strip() else None

def deep_clean_payload(obj):
    """Recursively clean HTML from all strings"""
    if isinstance(obj, dict):
        return {k: deep_clean_payload(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deep_clean_payload(item) for item in obj]
    elif isinstance(obj, str):
        cleaned = clean_html_from_text(obj)
        if cleaned != obj and obj:
            print(f"🧹 CLEANED: '{obj[:50]}...' → '{cleaned}'")
        return cleaned
    else:
        return obj

def generate_mock_data(company_name: str, company_id: str, website: str) -> Dict:
    """Generate placeholder data for development"""
    print(f"\n🔧 GENERATING MOCK DATA FOR: {company_name}")
    
    mock_data = {
        "company_name": company_name,
        "pages_scraped": ["homepage", "about", "team"],
        "is_fallback": True,
        "complete_payload": {
            "company_record": {
                "legal_name": f"{company_name}, Inc.",
                "brand_name": company_name,
                "website": website,
                "hq_city": "San Francisco",
                "hq_state": "CA",
                "hq_country": "United States",
                "founded_year": 2018,
                "categories": ["Artificial Intelligence", "Enterprise Software"],
                "description": f"{company_name} develops AI-powered solutions for enterprise customers. The company focuses on innovative approaches to solve complex business challenges through advanced machine learning and natural language processing technologies.",
                "total_raised_usd": 50000000,
                "last_round_name": "Series B",
                "last_round_date": "2024-03-15"
            },
            "events": [
                {
                    "occurred_on": "2024-03-15",
                    "event_type": "funding",
                    "title": f"{company_name} Closes $50M Series B",
                    "description": "Funding round led by Sequoia Capital to accelerate product development and market expansion.",
                    "round_name": "Series B",
                    "amount_usd": 50000000,
                    "investors": ["Sequoia Capital", "Andreessen Horowitz"]
                },
                {
                    "occurred_on": "2024-06-20",
                    "event_type": "partnership",
                    "title": "Strategic Partnership with Fortune 500 Enterprise",
                    "description": "New collaboration to integrate AI capabilities into enterprise workflows."
                }
            ],
            "products": [
                {
                    "name": f"{company_name} Platform",
                    "description": "Enterprise AI platform that streamlines business operations through intelligent automation and predictive analytics.",
                    "pricing_model": "enterprise",
                    "pricing_tiers_public": [],
                    "integration_partners": ["Salesforce", "Microsoft", "SAP"],
                    "reference_customers": ["Acme Corp", "Global Industries", "Tech Solutions Inc"]
                }
            ],
            "leadership": [
                {
                    "name": "Sarah Chen",
                    "role": "Chief Executive Officer",
                    "is_founder": True,
                    "previous_affiliation": "Google AI",
                    "education": "PhD Computer Science, Stanford"
                },
                {
                    "name": "Michael Rodriguez",
                    "role": "Chief Technology Officer",
                    "is_founder": True,
                    "previous_affiliation": "Meta AI Research",
                    "education": "MS Computer Science, MIT"
                },
                {
                    "name": "Jennifer Park",
                    "role": "Chief Operating Officer",
                    "is_founder": False,
                    "previous_affiliation": "McKinsey & Company",
                    "education": "MBA, Harvard Business School"
                }
            ],
            "snapshots": [
                {
                    "as_of": "2024-11-01",
                    "headcount_total": 150,
                    "headcount_growth_pct": None,
                    "engineering_openings": 12,
                    "sales_openings": 6,
                    "support_openings": 3,
                    "hiring_focus": "Engineering and Go-to-Market",
                    "geo_presence": ["United States", "United Kingdom"]
                }
            ],
            "visibility": [
                {
                    "as_of": "2024-11-07",
                    "news_mentions_30d": 18,
                    "avg_sentiment": 0.78,
                    "github_stars": 2500,
                    "glassdoor_rating": 4.1,
                    "linkedin_followers": 8400
                }
            ]
        },
        "rag_pipeline": {
            "dashboard": f"""## Company Overview

{company_name} operates in the enterprise AI space, developing solutions that help businesses automate complex workflows and make data-driven decisions. The company was founded in 2018 and is based in San Francisco, California.

## Business Model and GTM

The company uses an enterprise B2B model, selling directly to large organizations. Their platform integrates with major enterprise software like Salesforce, Microsoft, and SAP. Key customers include several Fortune 500 companies, though specific pricing details aren't publicly available.

## Funding & Investor Profile

{company_name} has raised $50 million in total funding. Their most recent round was a $50M Series B in March 2024, led by Sequoia Capital with participation from Andreessen Horowitz.

## Growth Momentum

The team has grown to approximately 150 employees. Current hiring focuses on engineering (12 open roles) and sales (6 open roles), indicating continued expansion. Recent partnership announcements suggest growing market traction.

## Visibility & Market Sentiment

Media coverage shows 18 mentions in the past 30 days with positive sentiment (0.78/1.0). The company maintains an active developer community with 2,500 GitHub stars and has a 4.1/5.0 Glassdoor rating from employees.

## Risks and Challenges

Key challenges include navigating a competitive enterprise AI market, scaling operations while maintaining product quality, and managing the complexity of enterprise sales cycles. The company must also stay ahead of rapidly evolving AI technologies.

## Outlook

{company_name} shows promising signs with recent funding, strategic partnerships, and active hiring. The leadership team brings strong experience from top tech companies. Continued focus on enterprise integration and customer success will be critical for sustained growth.

## Disclosure Gaps

- Detailed revenue and ARR figures not available
- Full investor cap table not disclosed
- Specific pricing tiers not public
- Customer contract values not disclosed
- International expansion plans unclear""",
            "scores": {
                "factual_correctness": 2,
                "schema_adherence": 2,
                "provenance_use": 1,
                "hallucination_control": 2,
                "readability": 1,
                "total_score": 8,
                "notes": "Strong narrative flow with good context, though some structured details could be more precise"
            }
        },
        "structured_pipeline": {
            "dashboard": f"""## Company Overview

**Legal Entity:** {company_name}, Inc.  
**Headquarters:** San Francisco, CA, United States  
**Founded:** 2018  
**Categories:** Artificial Intelligence, Enterprise Software

{company_name} develops AI-powered solutions for enterprise customers, focusing on innovative approaches to solve complex business challenges through advanced machine learning and natural language processing technologies.

**Total Capital Raised:** $50.0M  
**Last Round:** Series B (March 15, 2024)

## Business Model and GTM

**Target Market:** Enterprise B2B customers  
**Pricing Model:** Enterprise (contact sales)  
**Distribution:** Direct sales to large organizations

**Integration Partners:**  
Salesforce, Microsoft, SAP

**Notable Customers:**  
Acme Corp, Global Industries, Tech Solutions Inc

The company follows an enterprise sales motion with deep integrations into existing business software ecosystems.

## Funding & Investor Profile

**Total Raised:** $50.0M  
**Last Round:** Series B - March 15, 2024

**Series B Details:**  
- **Amount:** $50M  
- **Lead Investor:** Sequoia Capital  
- **Other Investors:** Andreessen Horowitz  
- **Use of Funds:** Product development and market expansion  
- **Valuation:** Not disclosed

## Growth Momentum

**Team Size:** ~150 employees  
**Hiring Activity:**  
- Engineering: 12 open positions  
- Sales: 6 open positions  
- Support: 3 open positions  
**Focus Area:** Engineering and Go-to-Market expansion

**Recent Milestones:**  
- Series B funding (Mar 2024)  
- Strategic partnership with Fortune 500 enterprise (Jun 2024)

**Geographic Presence:** United States, United Kingdom

## Visibility & Market Sentiment

**Media Coverage:** 18 mentions (last 30 days)  
**Sentiment Score:** 0.78/1.0 (Positive)  
**GitHub Stars:** 2,500  
**Glassdoor Rating:** 4.1/5.0  
**LinkedIn Followers:** 8,400

Public perception remains positive with steady media attention and strong employee satisfaction scores.

## Risks and Challenges

**Market Risks:**  
- Highly competitive enterprise AI landscape  
- Rapid technological change requiring continuous innovation  
- Long enterprise sales cycles

**Operational Risks:**  
- Scaling team and operations efficiently  
- Maintaining product quality during growth  
- Customer concentration in specific verticals

**Execution Risks:**  
- Delivering on enterprise customer expectations  
- Achieving product-market fit across diverse use cases

## Outlook

{company_name} demonstrates solid fundamentals with experienced leadership from Google AI and Meta AI Research. The recent Series B funding from top-tier investors provides runway for expansion. Active hiring in engineering and sales signals growth ambitions. Success will depend on execution in enterprise customer acquisition, product development velocity, and competitive differentiation in a crowded market.

## Disclosure Gaps

- Revenue and ARR figures not publicly available  
- Exact valuation not disclosed  
- Detailed pricing structure not published  
- Full cap table and ownership breakdown unclear  
- Customer contract values and retention metrics not disclosed  
- International expansion timeline not specified  
- Product roadmap details not public""",
            "scores": {
                "factual_correctness": 3,
                "schema_adherence": 2,
                "provenance_use": 2,
                "hallucination_control": 2,
                "readability": 1,
                "total_score": 10,
                "notes": "Structured pipeline delivers complete schema compliance with all required fields"
            }
        },
        "evaluation": {
            "rag_scores": {
                "factual_correctness": 2,
                "schema_adherence": 2,
                "provenance_use": 1,
                "hallucination_control": 2,
                "readability": 1,
                "total_score": 8,
                "notes": "RAG pipeline provides good narrative context but misses some structured precision"
            },
            "structured_scores": {
                "factual_correctness": 3,
                "schema_adherence": 2,
                "provenance_use": 2,
                "hallucination_control": 2,
                "readability": 1,
                "total_score": 10,
                "notes": "Structured pipeline delivers complete schema compliance with all required fields"
            },
            "winner": "structured",
            "reasoning": "The Structured pipeline achieved perfect 10/10 score versus RAG's 8/10 by maintaining complete schema adherence and capturing all required data fields. While the RAG approach created compelling narrative flow, it occasionally missed specific structured elements like exact funding amounts, hiring numbers, and sentiment scores. For PE diligence where precision and auditability matter most, the structured extraction approach provides more reliable and verifiable intelligence."
        },
        "processing_time_seconds": 0.1,
        "timestamp": "2024-11-07T12:00:00Z"
    }
    
    print(f"✅ Generated clean mock data")
    print(f"   Jennifer Park role: {mock_data['complete_payload']['leadership'][2]['role']}")
    
    return mock_data

@app.get("/")
def root():
    return {"status": "operational", "name": "ORBIT API", "mode": "development"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/companies/list", response_model=List[CompanyListItem])
def get_companies_list():
    """Get list of all Forbes AI 50 companies"""
    try:
        with open(DATA_DIR / "forbes_ai50_seed.json") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(500, f"Failed to load companies: {str(e)}")

@app.post("/api/dual-pipeline/compare")
def dual_pipeline_comparison(request: CompanyRequest):
    """Get dual pipeline comparison for a company"""
    try:
        company_file = COMPANIES_DIR / f"{request.company_id}.json"
        
        if company_file.exists():
            print(f"\n✅ Loading REAL data from file: {request.company_id}")
            with open(company_file) as f:
                company_data = json.load(f)
            
            print(f"   Cleaning data...")
            company_data = deep_clean_payload(company_data)
            
            return {
                "company_name": request.company_name,
                "pages_scraped": company_data.get("pages_scraped", []),
                "is_fallback": company_data.get("is_fallback", False),
                "complete_payload": company_data.get("complete_payload", {}),
                "rag_pipeline": company_data.get("rag_pipeline", {}),
                "structured_pipeline": company_data.get("structured_pipeline", {}),
                "evaluation": company_data.get("evaluation", {}),
                "processing_time_seconds": company_data.get("processing_time_seconds", 0),
                "timestamp": company_data.get("timestamp", "")
            }
        else:
            print(f"\n⚠️  File not found, generating MOCK data: {request.company_id}")
            mock_data = generate_mock_data(request.company_name, request.company_id, request.website)
            
            # Verify leadership is clean
            leaders = mock_data['complete_payload']['leadership']
            for leader in leaders:
                print(f"   Leader: {leader['name']} | Role: {leader['role']}")
            
            return mock_data
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return generate_mock_data(request.company_name, request.company_id, request.website)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
