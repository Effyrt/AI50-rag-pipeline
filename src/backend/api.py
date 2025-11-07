"""
FastAPI application for PE Dashboard
Provides RAG and Structured pipeline endpoints with GCS integration
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, List
import json
import os
from pathlib import Path
from datetime import datetime

# GCS imports
from google.cloud import storage
from google.oauth2 import service_account

# Import pipelines
from .rag_pipeline import RAGPipeline
from .structured_pipeline import load_payload

# Initialize FastAPI
app = FastAPI(
    title="PE Dashboard API",
    description="Forbes AI 50 Private Equity Dashboard System",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize GCS client
gcs_client = None
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ai50-dashboard-data")

def get_gcs_client():
    """Get or create GCS client"""
    global gcs_client
    if gcs_client is None:
        try:
            # Try to use service account if available
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if credentials_path:
                credentials = service_account.Credentials.from_service_account_file(credentials_path)
                gcs_client = storage.Client(credentials=credentials)
            else:
                # Use default credentials
                gcs_client = storage.Client()
        except Exception as e:
            print(f"Warning: GCS client initialization failed: {e}")
            gcs_client = None
    return gcs_client

# Initialize RAG pipeline (singleton)
rag_pipeline = None

# Cache for structured data file existence checks
_structured_files_cache = None

def get_structured_files_cache():
    """Get cached set of available structured data files"""
    global _structured_files_cache
    if _structured_files_cache is None:
        _structured_files_cache = set()
        try:
            structured_dir = Path("data/structured")
            if structured_dir.exists():
                # Get all .json files and extract company IDs from filenames
                for file_path in structured_dir.glob("*.json"):
                    company_id = file_path.stem  # Remove .json extension
                    _structured_files_cache.add(company_id)
        except Exception as e:
            print(f"Error building structured files cache: {e}")
    return _structured_files_cache

def get_rag_pipeline():
    """Get or create RAG pipeline instance"""
    global rag_pipeline
    if rag_pipeline is None:
        rag_pipeline = RAGPipeline()
    return rag_pipeline


# ============================================================
# Request/Response Models
# ============================================================

class DashboardRequest(BaseModel):
    company_name: str
    top_k: int = 20

class DashboardResponse(BaseModel):
    company_name: str
    pipeline: str
    dashboard: str
    generated_at: str
    retrieved_chunks: Optional[int] = None

class CompanyInfo(BaseModel):
    company_id: str
    company_name: str
    founded_year: Optional[int] = None
    headquarters: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    last_updated: Optional[str] = None
    structured_available: bool = False
    rag_available: bool = False

class CompaniesResponse(BaseModel):
    companies: List[CompanyInfo]
    total_count: int
    last_updated: str

class ComparisonResponse(BaseModel):
    company_name: str
    structured_dashboard: Optional[str] = None
    rag_dashboard: Optional[str] = None
    comparison_available: bool = False
    generated_at: str


# ============================================================
# Helper Functions
# ============================================================

def load_from_gcs(blob_path: str) -> Optional[str]:
    """Load content from GCS blob"""
    try:
        client = get_gcs_client()
        if not client:
            return None

        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(blob_path)

        if blob.exists():
            return blob.download_as_text()
        return None
    except Exception as e:
        print(f"Error loading from GCS {blob_path}: {e}")
        return None


def structured_data_exists(company_id: str) -> bool:
    """Check if structured data exists (prioritize local files for performance)"""
    # Check local file first (much faster)
    try:
        local_path = Path(f"data/structured/{company_id}.json")
        if local_path.exists():
            return True
    except Exception:
        pass

    # Only check GCS if local file doesn't exist
    try:
        client = get_gcs_client()
        if client:
            bucket = client.bucket(BUCKET_NAME)
            blob = bucket.blob(f"structured/payloads/{company_id}.json")
            if blob.exists():
                return True
    except Exception:
        pass

    return False


def load_structured_data(company_id: str) -> Optional[str]:
    """Load structured data from GCS or local fallback"""
    # Try GCS first
    gcs_data = load_from_gcs(f"structured/payloads/{company_id}.json")
    if gcs_data:
        return gcs_data

    # Fallback to local file
    try:
        local_path = Path(f"data/structured/{company_id}.json")
        if local_path.exists():
            with open(local_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"Error loading local structured data for {company_id}: {e}")

    return None


def load_rag_data(company_name: str) -> Optional[str]:
    """Load RAG data from GCS or local fallback"""
    # Try GCS first
    gcs_data = load_from_gcs(f"rag/dashboards/{company_name.lower().replace(' ', '_').replace('.', '').replace('&', 'and')}.md")
    if gcs_data:
        return gcs_data

    # Fallback to local file
    try:
        # Convert company name to filename format (lowercase, replace spaces with underscores, etc.)
        filename = company_name.lower().replace(' ', '_').replace('.', '').replace('&', 'and')
        local_path = Path(f"data/rag/{filename}_dashboard.md")
        if local_path.exists():
            with open(local_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"Error loading local RAG data for {company_name}: {e}")

    return None


def rag_data_exists(company_name: str) -> bool:
    """Check if RAG data exists (GCS or local)"""
    # Try GCS first
    try:
        client = get_gcs_client()
        if client:
            bucket = client.bucket(BUCKET_NAME)
            filename = company_name.lower().replace(' ', '_').replace('.', '').replace('&', 'and')
            blob = bucket.blob(f"rag/dashboards/{filename}.md")
            if blob.exists():
                return True
    except Exception:
        pass

    # Check local file
    try:
        filename = company_name.lower().replace(' ', '_').replace('.', '').replace('&', 'and')
        local_path = Path(f"data/rag/{filename}_dashboard.md")
        return local_path.exists()
    except Exception:
        return False


def get_companies_from_seed() -> List[Dict]:
    """Load companies from seed file"""
    try:
        seed_path = Path("data/forbes_ai50_seed.json")
        if seed_path.exists():
            with open(seed_path, 'r') as f:
                data = json.load(f)
                # The file is a direct array of company objects
                if isinstance(data, list):
                    return data
                else:
                    # Fallback in case structure changes
                    return data.get('companies', [])
        return []
    except Exception as e:
        print(f"Error loading seed file: {e}")
        return []

# ============================================================
# Health Check & Info Endpoints
# ============================================================

@app.get("/")
def read_root():
    """API health check and information"""
    return {
        "message": "PE Dashboard API is running",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "companies": "/companies - Get all companies list",
            "structured_dashboard": "/dashboard/structured - Generate structured dashboard",
            "rag_dashboard": "/dashboard/rag - Generate RAG dashboard",
            "comparison": "/companies/{company_name}/comparison - Compare both dashboards"
        }
    }


@app.get("/companies", response_model=CompaniesResponse)
def get_companies():
    """Get list of all companies with metadata"""
    companies_data = get_companies_from_seed()
    companies = []

    for company in companies_data:
        company_id = company.get('company_id', '')  # Use actual UUID from seed file

        # Check if structured data exists (GCS or local fallback)
        structured_available = structured_data_exists(company_id)

        # Check if RAG data exists (GCS or local fallback)
        rag_available = rag_data_exists(company.get('company_name', ''))

        company_info = CompanyInfo(
            company_id=company_id,
            company_name=company.get('company_name', ''),
            founded_year=company.get('founded_year'),
            headquarters=f"{company.get('hq_city', '')}, {company.get('hq_country', '')}".strip(', '),
            industry=company.get('categories', [None])[0] if company.get('categories') else None,
            website=company.get('website', ''),
            structured_available=structured_available,
            rag_available=rag_available
        )
        companies.append(company_info)

    return CompaniesResponse(
        companies=companies,
        total_count=len(companies),
        last_updated=datetime.now().isoformat()
    )


# ============================================================
# RAG Pipeline Endpoints (YOUR WORK!)
# ============================================================

@app.post("/dashboard/rag", response_model=DashboardResponse)
def generate_rag_dashboard(request: DashboardRequest):
    """
    Generate PE dashboard using RAG pipeline (UNSTRUCTURED)
    
    Args:
        request: DashboardRequest with company_name and top_k
    
    Returns:
        Generated dashboard in markdown format
    """
    try:
        rag = get_rag_pipeline()
        
        # Generate dashboard
        dashboard = rag.generate_dashboard(
            company_name=request.company_name,
            top_k=request.top_k
        )
        
        return DashboardResponse(
            company_name=request.company_name,
            pipeline="RAG (Unstructured)",
            dashboard=dashboard,
            generated_at=datetime.now().isoformat(),
            retrieved_chunks=request.top_k
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Dashboard generation error: {str(e)}"
        )


# ============================================================
# Structured Pipeline Endpoints
# ============================================================

@app.post("/dashboard/structured", response_model=DashboardResponse)
def generate_structured_dashboard(request: DashboardRequest):
    """
    Generate PE dashboard using structured pipeline

    Args:
        request: DashboardRequest with company_name

    Returns:
        Generated dashboard in markdown format
    """
    try:
        # Create company ID for GCS lookup
        company_id = request.company_name.lower().replace(' ', '_').replace('.', '').replace('&', 'and')

        # Try to load structured payload from GCS
        gcs_path = f"structured/payloads/{company_id}.json"
        payload_json = load_from_gcs(gcs_path)

        if not payload_json:
            raise HTTPException(
                status_code=404,
                detail=f"Structured data not found for {request.company_name}"
            )

        # Parse the payload
        payload = json.loads(payload_json)

        # Generate dashboard from structured data
        dashboard = generate_structured_dashboard_from_payload(payload)

        return DashboardResponse(
            company_name=request.company_name,
            pipeline="Structured",
            dashboard=dashboard,
            generated_at=datetime.now().isoformat()
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid structured data format for {request.company_name}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating structured dashboard: {str(e)}"
        )

def generate_structured_dashboard_from_payload(payload: Dict) -> str:
    """Generate dashboard markdown from structured payload aligned to required sections."""
    company = payload.get('company', {}) or {}
    events = payload.get('events', []) or []
    snapshots = payload.get('snapshots', []) or []
    snapshot = snapshots[0] if snapshots else {}
    visibility_top = payload.get('visibility', {}) if isinstance(payload.get('visibility'), dict) else {}
    visibility_company = company.get('visibility', {}) if isinstance(company.get('visibility'), dict) else {}
    visibility = {**visibility_top, **visibility_company}

    def fmt_currency(value):
        try:
            return f"${value:,.0f}"
        except Exception:
            return "Not disclosed"

    # 1) Company Overview
    overview = []
    overview.append(f"- **Legal Name / Brand**: {company.get('legal_name', 'Not disclosed')} / {company.get('brand_name', 'Not disclosed')}")
    hq = ", ".join(list(filter(None, [company.get('hq_city'), company.get('hq_state'), company.get('hq_country')])))
    overview.append(f"- **Headquarters**: {hq or 'Not disclosed'}")
    overview.append(f"- **Founded**: {company.get('founded_year', 'Not disclosed')}")
    overview.append(f"- **Categories**: {', '.join(company.get('categories', [])) or 'Not disclosed'}")
    positioning = company.get('competitive_differentiation') or (", ".join(company.get('related_companies', [])) if company.get('related_companies') else None)
    overview.append(f"- **Related Companies / Positioning**: {positioning or 'Not disclosed'}")

    # 2) Business Model and GTM
    bmodel = []
    bmodel.append(f"- **Who they sell to**: {', '.join(company.get('target_customer_segments', [])) or 'Not disclosed'}")
    pricing_tiers = company.get('pricing_tiers_public', [])
    bmodel.append(f"- **Pricing Model / Tiers**: {company.get('pricing_model', 'Not disclosed')}{' | ' + ', '.join(pricing_tiers) if pricing_tiers else ''}")
    integrations = []
    if company.get('technology_partnerships'):
        integrations.append(f"Partners: {', '.join(company.get('technology_partnerships', []))}")
    # Named customers from products[].reference_customers
    named_customers = []
    for p in payload.get('products', []) or []:
        for c in p.get('reference_customers', []) or []:
            named_customers.append(c)
    if named_customers:
        integrations.append(f"Customers: {', '.join(named_customers)}")
    bmodel.append(f"- **Integration Partners / Named Customers**: {(' | '.join(integrations)) if integrations else 'Not disclosed'}")
    bmodel.append(f"- **Go-to-Market Motion**: {company.get('sales_motion', 'Not disclosed')}")

    # 3) Funding & Investor Profile
    funding = []
    funding.append(f"- **Total Raised**: {fmt_currency(company.get('total_raised_usd')) if company.get('total_raised_usd') else 'Not disclosed'}")
    funding.append(f"- **Latest Round**: {company.get('last_round_name', 'Not disclosed')}")
    # Funding events
    funding_events = [e for e in events if e.get('event_type') == 'funding']
    if funding_events:
        for e in funding_events:
            line = []
            rn = e.get('round_name') or 'Not disclosed'
            line.append(f"round_name: {rn}")
            line.append(f"amount_usd: {fmt_currency(e.get('amount_usd')) if e.get('amount_usd') else 'Not disclosed'}")
            investors = ", ".join(e.get('investors', []) or [])
            line.append(f"investors: {investors or 'Not disclosed'}")
            # Valuation only if explicitly present
            val = e.get('valuation_usd')
            line.append(f"valuation_usd: {fmt_currency(val) if val else 'Not disclosed'}")
            occurred = e.get('occurred_on') or e.get('event_date') or 'Not disclosed'
            line.append(f"occurred_on: {occurred}")
            funding.append(f"- " + "; ".join(line))
    else:
        funding.append(f"- No funding events disclosed")

    # 4) Growth Momentum
    growth = []
    if snapshot:
        growth.append(f"- **Headcount**: {snapshot.get('headcount_total', 'Not disclosed')}")
        growth.append(f"- **Headcount Growth %**: {snapshot.get('headcount_growth_pct', 'Not disclosed')}")
        eng = snapshot.get('engineering_openings')
        sales = snapshot.get('sales_openings')
        hiring_focus = []
        if eng is not None:
            hiring_focus.append(f"engineering_openings: {eng}")
        if sales is not None:
            hiring_focus.append(f"sales_openings: {sales}")
        growth.append(f"- **Hiring Focus**: {', '.join(hiring_focus) if hiring_focus else 'Not disclosed'}")
        geo = snapshot.get('geo_presence') or company.get('geographic_markets', [])
        growth.append(f"- **Geo Presence**: {', '.join(geo) if geo else 'Not disclosed'}")
    else:
        growth.append(f"- **Headcount**: Not disclosed")
        growth.append(f"- **Headcount Growth %**: Not disclosed")
        growth.append(f"- **Hiring Focus**: Not disclosed")
        growth.append(f"- **Geo Presence**: {', '.join(company.get('geographic_markets', [])) or 'Not disclosed'}")
    # Recent traction events
    recent_traction = []
    for e in events:
        if e.get('event_type') in ('partnership', 'product_release', 'leadership_change'):
            occurred = e.get('occurred_on') or e.get('event_date')
            title = e.get('title') or e.get('description')
            if occurred or title:
                recent_traction.append(f"{occurred or ''} - {title or ''}".strip(" -"))
    growth.append(f"- **Recent Events**: {('; '.join(recent_traction)) if recent_traction else 'Not disclosed'}")

    # 5) Visibility & Market Sentiment
    vis = []
    vis.append(f"- **News Mentions (30d)**: {visibility.get('news_mentions_30d', 'Not disclosed')}")
    vis.append(f"- **Avg Sentiment**: {visibility.get('avg_sentiment', 'Not disclosed')}")
    vis.append(f"- **GitHub Stars**: {visibility.get('github_stars', 'Not disclosed')}")
    vis.append(f"- **Glassdoor Rating**: {visibility.get('glassdoor_rating', 'Not disclosed')}")
    vis.append(f"- **Attention Trend**: {visibility.get('attention_trend', 'Not disclosed')}")

    # 6) Risks and Challenges (only use provided fields if any appear in events or company flags)
    risks_lines = []
    # Look for event tags/flags that indicate layoffs, leadership churn, regulatory/security incidents, pricing pressure
    for e in events:
        et = (e.get('event_type') or '').lower()
        if et in ('layoff', 'leadership_change', 'regulatory_incident', 'security_incident', 'pricing_change'):
            occurred = e.get('occurred_on') or e.get('event_date') or ''
            title = e.get('title') or e.get('description') or et
            risks_lines.append(f"- {occurred} {title}".strip())
    risks = "\n".join(risks_lines) if risks_lines else "Not disclosed"

    # 7) Outlook (calm perspective from available structured data only)
    outlook = []
    cats = ", ".join(company.get('categories', []) or [])
    target = ", ".join(company.get('target_customer_segments', []) or [])
    outlook.append(f"{company.get('legal_name', 'The company')} operates in {cats or 'its category'} serving {target or 'its target customers'}.")
    outlook.append("Based on available structured fields, the company appears to have a clear product focus and defined buyer profile.")

    # 8) Disclosure Gaps
    gaps = []
    if not company.get('total_raised_usd'):
        gaps.append("- Total raised not disclosed")
    if not company.get('last_disclosed_valuation_usd'):
        gaps.append("- Valuation not disclosed")
    if not visibility.get('glassdoor_rating'):
        gaps.append("- Glassdoor rating unavailable or behind login")
    if not company.get('pricing_tiers_public'):
        gaps.append("- Pricing tiers not publicly detailed")
    if not named_customers:
        gaps.append("- Named customers not publicly listed")

    # Compose dashboard
    dashboard = []
    dashboard.append(f"# {company.get('legal_name', 'Company')} Dashboard")
    dashboard.append(f"*Generated: {datetime.now().isoformat()}*")
    dashboard.append(f"*Pipeline: Structured*")
    dashboard.append("")
    dashboard.append("## Company Overview")
    dashboard.extend(overview)
    dashboard.append("")
    dashboard.append("## Business Model and GTM")
    dashboard.extend(bmodel)
    dashboard.append("")
    dashboard.append("## Funding & Investor Profile")
    dashboard.extend(funding)
    dashboard.append("")
    dashboard.append("## Growth Momentum")
    dashboard.extend(growth)
    dashboard.append("")
    dashboard.append("## Visibility & Market Sentiment")
    dashboard.extend(vis)
    dashboard.append("")
    dashboard.append("## Risks and Challenges")
    dashboard.append(risks)
    dashboard.append("")
    dashboard.append("## Outlook")
    dashboard.append(" ".join(outlook))
    dashboard.append("")
    dashboard.append("## Disclosure Gaps")
    dashboard.extend(gaps or ["- None noted"])

    return "\n".join(dashboard)

@app.get("/companies/{company_name}/comparison", response_model=ComparisonResponse)
def get_company_comparison(company_name: str):
    """Get comparison of both structured and RAG dashboards for a company"""
    try:
        # Find company by name to get the correct UUID company_id
        companies_data = get_companies_from_seed()
        company_data = next((c for c in companies_data if c.get('company_name') == company_name), None)
        if not company_data:
            raise HTTPException(status_code=404, detail=f"Company {company_name} not found")

        company_id = company_data.get('company_id', '')

        # Load structured dashboard
        structured_dashboard = None
        try:
            structured_payload = load_structured_data(company_id)
            if structured_payload:
                payload = json.loads(structured_payload)
                structured_dashboard = generate_structured_dashboard_from_payload(payload)
        except Exception as e:
            print(f"Error loading structured data: {e}")

        # Load RAG dashboard
        rag_dashboard = None
        try:
            rag_dashboard = load_rag_data(company_name)
        except Exception as e:
            print(f"Error loading RAG data: {e}")

        comparison_available = structured_dashboard is not None and rag_dashboard is not None

        return ComparisonResponse(
            company_name=company_name,
            structured_dashboard=structured_dashboard,
            rag_dashboard=rag_dashboard,
            comparison_available=comparison_available,
            generated_at=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating comparison: {str(e)}"
        )


# ============================================================
# Utility Endpoints
# ============================================================

@app.get("/test")
def test_endpoint():
    """Simple test endpoint to verify API is working"""
    return {
        "status": "success",
        "message": "API is working correctly!",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("Starting PE Dashboard API Server")
    print("="*60)
    print("\nRAG Pipeline: Ready ✓")
    print("\nAPI Documentation: http://localhost:8000/docs")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)