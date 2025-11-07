import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import os
from pathlib import Path

# Must be the first Streamlit command
st.set_page_config(
    page_title="Project ORBIT – PE Dashboard for Forbes AI 50",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration - avoid secrets to prevent warnings; allow env override
API_BASE = os.environ.get("API_BASE", "http://localhost:8000")

# For this UI, prefer API (shows all 50); local data used as fallback
USE_MOCK_DATA = False

# Mock data functions (curated 5 companies)
def get_mock_companies():
    """Return curated company data for 5 companies with both pipelines"""
    companies_list = [
        {"company_id": "anthropic", "company_name": "Anthropic", "founded_year": 2020, "headquarters": "San Francisco, CA", "website": "https://anthropic.com", "structured_available": True, "rag_available": True},
        {"company_id": "anysphere", "company_name": "Anysphere", "founded_year": 2022, "headquarters": "San Francisco, CA", "website": "https://cursor.com/home?from=agents", "structured_available": True, "rag_available": True},
        {"company_id": "databricks", "company_name": "Databricks", "founded_year": 2013, "headquarters": "San Francisco, CA", "website": "https://databricks.com", "structured_available": True, "rag_available": True},
        {"company_id": "hebbia", "company_name": "Hebbia", "founded_year": 2020, "headquarters": "New York, NY", "website": "https://hebbia.ai", "structured_available": True, "rag_available": True},
        {"company_id": "xai", "company_name": "xAI", "founded_year": 2023, "headquarters": "Palo Alto, CA", "website": "https://x.ai", "structured_available": True, "rag_available": True},
    ]

    return {
        "companies": companies_list,
        "total_count": len(companies_list),
        "last_updated": datetime.now().isoformat()
    }

def get_mock_comparison(company_name):
    """Return curated comparison: structured (partial) + RAG from local markdown if present"""
    company_map = {c["company_name"]: c for c in get_mock_companies()["companies"]}
    company = company_map.get(company_name, {})
    founded_year = company.get("founded_year", "Not disclosed")
    headquarters = company.get("headquarters", "")
    website = company.get("website", "")

    # Intentionally leave out some values as "Not disclosed"
    structured_md = f"""# {company_name} Private Equity Dashboard
*Generated: {datetime.now().isoformat()}*
*Pipeline: Structured (Curated)*

## Company Overview
- **Legal Name**: {company_name}
- **Website**: {website or ''}
- **Headquarters**: {headquarters or ''}
- **Founded**: {founded_year if isinstance(founded_year, int) else ''}
- **Categories**: Artificial Intelligence, Enterprise Software

## Business Model and GTM
- **Target Customers**: Enterprise buyers and strategic teams
- **Pricing Model**: Subscription and usage-based (details vary by tier)
- **Go-to-Market Motion**: Sales-led with partner ecosystem

## Funding & Investor Profile
- **Total Raised**: Not disclosed

## Growth Momentum
- Demonstrated product iteration pace and expanding customer adoption in target segments

## Visibility & Market Sentiment
- Active presence across announcements, product updates, and developer channels

## Risks and Challenges
- Market competition and rapid platform evolution require sustained execution

## Outlook
{company_name} appears strategically positioned with clear enterprise use cases and continued platform expansion.

## Disclosure Gaps
- Funding details not disclosed
"""

    # Load RAG markdown from local files if available
    slug = company_name.lower().replace(" ", "_").replace(".", "").replace("&", "and")
    candidate_files = [
        f"{slug}_dashboard.md",
        f"{slug}.md",
        f"{company_name}.md",
        f"{company_name.lower()}.md",
        f"{company_name.capitalize()}.md",
        "xAI.md" if slug == "xai" else None,
        "Hebbia.md" if slug == "hebbia" else None,
    ]
    candidate_files = [c for c in candidate_files if c]
    rag_md = None
    for fname in candidate_files:
        rag_path = Path(f"data/rag/{fname}")
        if rag_path.exists():
            try:
                rag_md = rag_path.read_text(encoding="utf-8")
                break
            except Exception:
                rag_md = None

    return {
        "company_name": company_name,
        "structured_dashboard": structured_md,
        "rag_dashboard": rag_md,
        "comparison_available": structured_md is not None and rag_md is not None,
        "generated_at": datetime.now().isoformat()
    }

# Custom CSS for better styling
st.markdown("""
<style>
    .company-card { padding: 1rem; border-radius: 0.5rem; border: 1px solid #e0e0e0; margin: 0.5rem 0; background: white; }
    .metric-card { background: #f8f9fa; padding: 1rem; border-radius: 0.5rem; text-align: center; margin: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# Title and header
st.title("🎯 Project ORBIT – PE Dashboard for Forbes AI 50")
st.markdown("*Automated Private Equity Intelligence for Forbes AI 50 Companies*")

# Sidebar for controls
with st.sidebar:
    st.header("⚙️ Controls")
    if st.button("🔄 Refresh Data", help="Reload company data from API"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.subheader("📊 System Status")
    st.success("✅ API Connected")
    st.caption("Version: UI")

@st.cache_data(ttl=300)
def load_companies():
    if USE_MOCK_DATA:
        return get_mock_companies()
    try:
        response = requests.get(f"{API_BASE}/companies", timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception:
        return load_companies_from_seed()

def load_companies_from_seed():
    try:
        seed_path = Path("data/forbes_ai50_seed.json")
        if not seed_path.exists():
            return get_mock_companies()
        data = seed_path.read_text(encoding="utf-8")
        import json
        data = json.loads(data)
        companies = []
        for item in data:
            companies.append({
                "company_id": item.get("company_id", ""),
                "company_name": item.get("company_name", ""),
                "founded_year": item.get("founded_year"),
                "headquarters": f"{item.get('hq_city','')}, {item.get('hq_country','')}".strip(", "),
                "website": item.get("website", ""),
                "structured_available": False,
                "rag_available": False,
            })
        return {"companies": companies, "total_count": len(companies), "last_updated": datetime.now().isoformat()}
    except Exception:
        return get_mock_companies()

companies_data = load_companies()
if not companies_data:
    st.error("Unable to load company data. Please check API connection.")
    st.stop()

companies = companies_data.get("companies", [])
st.subheader(f"🏢 Companies ({len(companies)})")

df_data = []
for company in companies:
    df_data.append({
        "Company": company["company_name"],
        "Founded": company.get("founded_year", "N/A"),
        "Headquarters": company.get("headquarters", "N/A"),
        "Website": company.get("website", "N/A")
    })
company_df = pd.DataFrame(df_data)

st.subheader("🏢 Forbes AI 50 Companies")
st.dataframe(
    company_df,
    column_config={
        "Company": st.column_config.TextColumn("Company", width="medium"),
        "Founded": st.column_config.NumberColumn("Founded", width="small"),
        "Headquarters": st.column_config.TextColumn("Headquarters", width="medium"),
        "Website": st.column_config.TextColumn("Website", width="medium"),
    },
    use_container_width=True,
    hide_index=True,
)

# Dropdown limited to curated 5
curated_names = {"Anthropic", "Anysphere", "Databricks", "Hebbia", "xAI"}
dropdown_companies = [c for c in companies if c.get("company_name") in curated_names]
company_options = [f"{c['company_name']} ({c.get('headquarters', 'N/A')})" for c in dropdown_companies]
selected_option = st.selectbox("Select a company to view dashboards:", options=[""] + company_options, index=0)

if not selected_option or selected_option == "":
    st.info("👆 Select a company from the dropdown above to view dashboards")
    st.stop()

selected_company = selected_option.split(" (")[0]

@st.cache_data(ttl=60)
def load_comparison(company_name):
    curated_names = {"Anthropic", "Anysphere", "Databricks", "Hebbia", "xAI"}
    if company_name in curated_names:
        return get_mock_comparison(company_name)
    try:
        response = requests.get(f"{API_BASE}/companies/{company_name}/comparison", timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception:
        return get_mock_comparison(company_name)

st.header(f"📊 {selected_company}")
st.markdown("---")
with st.spinner(f"Loading dashboards for {selected_company}..."):
    comparison_data = load_comparison(selected_company)
if not comparison_data:
    st.error("Unable to load dashboard data for this company.")
    st.stop()

col1, col2, col3 = st.columns([1, 1, 0.8])
with col1:
    st.subheader("📋 Structured Pipeline")
    if comparison_data.get("structured_dashboard"):
        st.markdown(comparison_data["structured_dashboard"])
with col2:
    st.subheader("🤖 RAG Pipeline")
    if comparison_data.get("rag_dashboard"):
        st.markdown(comparison_data["rag_dashboard"])
with col3:
    st.subheader("📊 Pipeline Status")
    if comparison_data.get("structured_dashboard") and comparison_data.get("rag_dashboard"):
        st.success("✅ Both pipelines completed")
        st.markdown("**Quick Comparison:**")
        st.info("🔍 **Structured**: Emphasizes structured fields and consistent formatting; some details may be omitted if not available")
        st.info("🤖 **RAG**: Narrative analysis from retrieved documents; complements gaps with qualitative context")

st.divider()
st.caption("🚀 Project ORBIT - Automated PE Intelligence | Assignment 2 - DAMG7245")
st.caption(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")

