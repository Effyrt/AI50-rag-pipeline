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

# API base URL. Docker Compose sets this to http://api:8000.
API_BASE = os.environ.get("API_BASE", "http://localhost:8000")


def api_healthy() -> tuple[bool, str]:
    """Check whether the backend is actually reachable.

    The sidebar previously displayed "API Connected" unconditionally, which meant a
    down backend still looked healthy.
    """
    try:
        r = requests.get(f"{API_BASE}/", timeout=5)
        r.raise_for_status()
        return True, r.json().get("data_source", "unknown")
    except Exception as e:
        return False, str(e)

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
    _healthy, _detail = api_healthy()
    if _healthy:
        st.success("✅ API connected")
        st.caption(f"Data source: {_detail}")
    else:
        st.error("❌ API unreachable")
        st.caption(f"{API_BASE} — {_detail}")

@st.cache_data(ttl=300)
def load_companies():
    """Load the company list from the API.

    Returns None on failure so the caller can surface a visible error. This must
    not fall back to invented data: a fabricated list is indistinguishable from a
    real one in the UI.
    """
    try:
        response = requests.get(f"{API_BASE}/companies", timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.session_state["companies_error"] = str(e)
        return None

def load_companies_from_seed():
    """Load the company list directly from the seed file.

    Only used as an explicitly-labelled degraded mode when the API is unreachable;
    availability flags are reported as False because they cannot be verified here.
    """
    try:
        seed_path = Path("data/forbes_ai50_seed.json")
        if not seed_path.exists():
            return None
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
        return None

companies_data = load_companies()
if not companies_data:
    st.error(
        f"❌ Could not reach the API at {API_BASE}/companies — "
        f"{st.session_state.get('companies_error', 'unknown error')}"
    )
    companies_data = load_companies_from_seed()
    if companies_data:
        st.warning(
            "⚠️ Showing the company list from the local seed file (degraded mode). "
            "Dashboard availability is unknown and no dashboards can be generated "
            "until the API is reachable."
        )
    else:
        st.info("Start the backend with: `uvicorn src.backend.api:app --reload`")
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

# Dropdown covers all companies returned by the API. It was previously restricted to a
# curated set of five, which is why the assignment requirement "we should be able to try
# it for any of the 50 companies" was not met.
company_options = [f"{c['company_name']} ({c.get('headquarters', 'N/A')})" for c in companies]
selected_option = st.selectbox("Select a company to view dashboards:", options=[""] + company_options, index=0)

if not selected_option or selected_option == "":
    st.info("👆 Select a company from the dropdown above to view dashboards")
    st.stop()

selected_company = selected_option.split(" (")[0]

@st.cache_data(ttl=60)
def load_comparison(company_name):
    """Fetch both dashboards for a company from the API.

    Always calls the API. Previously a curated set of five companies short-circuited
    to hard-coded markdown before any request was made, so the UI displayed example
    dashboards rather than real pipeline output.
    """
    try:
        response = requests.get(
            f"{API_BASE}/companies/{company_name}/comparison", timeout=120
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.session_state["comparison_error"] = str(e)
        return None

st.header(f"📊 {selected_company}")
st.markdown("---")
with st.spinner(f"Loading dashboards for {selected_company}..."):
    comparison_data = load_comparison(selected_company)
if not comparison_data:
    st.error(
        f"❌ Could not load dashboards for {selected_company} — "
        f"{st.session_state.get('comparison_error', 'unknown error')}"
    )
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

