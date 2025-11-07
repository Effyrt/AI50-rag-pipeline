"""
ORBIT - Dual Pipeline Comparison Dashboard
RAG vs Structured with Evaluation + Fallback indicators
"""
import streamlit as st
import requests
import time
from datetime import datetime

st.set_page_config(
    page_title="ORBIT Dual Pipeline",
    page_icon="🚀",
    layout="wide"
)

# CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(120deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .score-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        padding: 25px;
        text-align: center;
    }
    .fallback-badge {
        background: #f59e0b;
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

API_BASE = "http://localhost:8000"


@st.cache_data(ttl=3600)
def get_companies():
    """Get Forbes AI 50"""
    try:
        response = requests.get(f"{API_BASE}/api/companies/list", timeout=30)
        return response.json() if response.status_code == 200 else []
    except:
        return []


def run_dual_pipeline(company):
    """Run both pipelines and compare"""
    with st.status("🔄 Running Dual Pipeline Analysis...", expanded=True) as status:
        st.write("🕷️ Step 1/5: Scraping company website...")
        time.sleep(0.5)
        
        st.write("📊 Step 2/5: Running RAG pipeline...")
        time.sleep(0.5)
        
        st.write("🤖 Step 3/5: Running Structured extraction...")
        time.sleep(0.5)
        
        st.write("📊 Step 4/5: Generating Structured dashboard...")
        time.sleep(0.5)
        
        st.write("🔍 Step 5/5: Evaluating both pipelines...")
        
        try:
            response = requests.post(
                f"{API_BASE}/api/dual-pipeline/compare",
                json={
                    "company_id": company['company_id'],
                    "company_name": company['company_name'],
                    "website": company['website']
                },
                timeout=180
            )
            
            if response.status_code == 200:
                status.update(label="✅ Analysis Complete!", state="complete")
                return response.json()
            else:
                status.update(label="❌ Analysis Failed", state="error")
                st.error(f"Error: {response.text}")
                return None
        
        except Exception as e:
            status.update(label="❌ Analysis Failed", state="error")
            st.error(f"Exception: {e}")
            return None


def main():
    # Header
    st.markdown('<h1 class="main-header">�� ORBIT Dual Pipeline</h1>', unsafe_allow_html=True)
    st.caption("RAG vs Structured Comparison • Forbes AI 50")
    
    st.divider()
    
    # Sidebar
    with st.sidebar:
        st.header("System Status")
        try:
            health = requests.get(f"{API_BASE}/health", timeout=5).json()
            st.success("✅ Backend Online")
            st.caption(f"Mode: {health.get('mode', 'unknown')}")
        except:
            st.error("❌ Backend Offline")
            return
        
        st.divider()
        st.subheader("Evaluation Rubric")
        st.markdown("""
**Total: 10 points**
- Factual Correctness (0-3)
- Schema Adherence (0-2)
- Provenance Use (0-2)
- Hallucination Control (0-2)
- Readability (0-1)
        """)
    
    # Company selector
    companies = get_companies()
    
    if not companies:
        st.error("No companies loaded")
        return
    
    st.subheader("Select Company for Dual Pipeline Analysis")
    
    selected = st.selectbox(
        "Choose from Forbes AI 50",
        options=companies,
        format_func=lambda x: f"#{x['rank']:02d} — {x['company_name']}",
        key="company_selector"
    )
    
    if selected:
        st.divider()
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"### {selected['company_name']}")
            st.caption(f"🔗 {selected['website']}")
        
        with col2:
            analyze_button = st.button(
                "🔄 Run Comparison",
                type="primary",
                use_container_width=True
            )
        
        if analyze_button:
            st.info("⚠️ **Dual Pipeline Analysis** • This will take 15-30 seconds")
            
            result = run_dual_pipeline(selected)
            
            if result:
                # Show fallback badge if used
                if result.get('is_fallback'):
                    st.warning('⚠️ **Fallback Data Used** - Website blocks automated scraping. Using publicly available information.')
                
                st.success(f"✅ Analysis completed in {result['processing_time_seconds']:.1f}s")
                
                # Scores comparison
                st.subheader("📊 Evaluation Scores")
                
                col1, col2, col3 = st.columns(3)
                
                rag_score = result['rag_pipeline']['scores']['total_score']
                struct_score = result['structured_pipeline']['scores']['total_score']
                winner = result['evaluation'].get('winner', 'unknown')
                
                with col1:
                    st.markdown(
                        f'<div class="score-card"><h3>RAG Pipeline</h3>'
                        f'<p style="font-size:3rem;margin:0;">{rag_score}/10</p></div>',
                        unsafe_allow_html=True
                    )
                
                with col2:
                    st.markdown(
                        f'<div class="score-card"><h3>Structured Pipeline</h3>'
                        f'<p style="font-size:3rem;margin:0;">{struct_score}/10</p></div>',
                        unsafe_allow_html=True
                    )
                
                with col3:
                    st.markdown(
                        f'<div class="score-card"><h3>Winner</h3>'
                        f'<p style="font-size:1.5rem;margin:10px 0;text-transform:uppercase;">{winner}</p></div>',
                        unsafe_allow_html=True
                    )
                
                # Detailed scores
                st.divider()
                st.subheader("📋 Detailed Breakdown")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### RAG Pipeline")
                    rag_scores = result['rag_pipeline']['scores']
                    st.metric("Factual Correctness", f"{rag_scores['factual_correctness']}/3")
                    st.metric("Schema Adherence", f"{rag_scores['schema_adherence']}/2")
                    st.metric("Provenance Use", f"{rag_scores['provenance_use']}/2")
                    st.metric("Hallucination Control", f"{rag_scores['hallucination_control']}/2")
                    st.metric("Readability", f"{rag_scores['readability']}/1")
                    st.caption(f"**Notes:** {rag_scores['notes']}")
                
                with col2:
                    st.markdown("#### Structured Pipeline")
                    struct_scores = result['structured_pipeline']['scores']
                    st.metric("Factual Correctness", f"{struct_scores['factual_correctness']}/3")
                    st.metric("Schema Adherence", f"{struct_scores['schema_adherence']}/2")
                    st.metric("Provenance Use", f"{struct_scores['provenance_use']}/2")
                    st.metric("Hallucination Control", f"{struct_scores['hallucination_control']}/2")
                    st.metric("Readability", f"{struct_scores['readability']}/1")
                    st.caption(f"**Notes:** {struct_scores['notes']}")
                
                # Reasoning
                st.divider()
                st.subheader("💡 Evaluation Reasoning")
                st.markdown(result['evaluation'].get('reasoning', 'No reasoning provided'))
                
                # Show data source info
                if result.get('is_fallback'):
                    st.info(f"📄 **Data Source:** Fallback data (website blocked)")
                else:
                    st.success(f"📄 **Data Source:** Live scraped from {len(result['pages_scraped'])} pages")
                
                # Dashboards
                st.divider()
                
                tab1, tab2, tab3 = st.tabs(["📊 RAG Dashboard", "📊 Structured Dashboard", "🔍 Raw Data"])
                
                with tab1:
                    st.markdown(result['rag_pipeline']['dashboard'])
                
                with tab2:
                    st.markdown(result['structured_pipeline']['dashboard'])
                
                with tab3:
                    st.json(result['structured_pipeline']['extracted_data'])


if __name__ == "__main__":
    main()
