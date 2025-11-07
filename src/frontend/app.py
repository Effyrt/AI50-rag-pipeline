"""
ORBIT - Executive-Grade PE Intelligence Platform
Final version with aggressive HTML cleaning
"""
import streamlit as st
import requests
import pandas as pd
import json
import re
from datetime import datetime

st.set_page_config(
    page_title="ORBIT PE Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, system-ui, sans-serif;
        -webkit-font-smoothing: antialiased;
    }
    
    .main {
        background: linear-gradient(180deg, #0a0e1a 0%, #0f1419 50%, #0a0e1a 100%);
    }
    
    .block-container {
        padding: 2rem 4rem;
        max-width: 1800px;
    }
    
    .premium-header {
        background: linear-gradient(135deg, rgba(30, 64, 175, 0.8) 0%, rgba(59, 130, 246, 0.8) 50%, rgba(126, 87, 194, 0.8) 100%);
        backdrop-filter: blur(40px);
        padding: 4.5rem 4rem;
        border-radius: 28px;
        margin-bottom: 3.5rem;
        box-shadow: 0 25px 80px rgba(59, 130, 246, 0.25);
        position: relative;
        overflow: hidden;
    }
    
    .premium-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 5px;
        background: linear-gradient(90deg, #60a5fa 0%, #a78bfa 25%, #f472b6 50%, #a78bfa 75%, #60a5fa 100%);
        background-size: 200% 100%;
        animation: shimmer 3s linear infinite;
    }
    
    @keyframes shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    
    .premium-title {
        font-size: 4rem;
        font-weight: 900;
        margin: 0;
        letter-spacing: -0.04em;
        background: linear-gradient(135deg, #ffffff 0%, #e0f2fe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .premium-subtitle {
        font-size: 1.3rem;
        color: rgba(255, 255, 255, 0.9);
        margin-top: 1.25rem;
    }
    
    .section-title {
        font-size: 1.75rem;
        font-weight: 800;
        color: #f1f5f9;
        margin: 4rem 0 2.5rem 0;
        padding: 1.5rem 0 1.5rem 2.5rem;
        border-left: 6px solid;
        border-image: linear-gradient(180deg, #42a5f5 0%, #7e57c2 100%) 1;
        background: linear-gradient(90deg, rgba(66, 165, 245, 0.15) 0%, transparent 100%);
        border-radius: 0 16px 16px 0;
    }
    
    .comparison-container {
        background: linear-gradient(135deg, rgba(17, 24, 39, 0.8) 0%, rgba(30, 41, 59, 0.7) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(66, 165, 245, 0.15);
        border-radius: 24px;
        padding: 3rem;
        margin: 2.5rem 0;
    }
    
    .winner-badge {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 0.5rem 1.5rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 800;
        text-transform: uppercase;
        display: inline-block;
        box-shadow: 0 4px 16px rgba(16, 185, 129, 0.4);
    }
    
    .score-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(66, 165, 245, 0.2);
        border-radius: 16px;
        padding: 2rem;
        margin: 1rem 0;
    }
    
    .score-card.winner {
        border: 2px solid #10b981;
        background: rgba(16, 185, 129, 0.1);
    }
    
    .metric-card-premium {
        background: linear-gradient(135deg, rgba(30, 64, 175, 0.4) 0%, rgba(59, 130, 246, 0.3) 100%);
        backdrop-filter: blur(30px);
        border: 1px solid rgba(96, 165, 250, 0.3);
        padding: 2.5rem 2rem;
        border-radius: 20px;
        box-shadow: 0 15px 50px rgba(0, 0, 0, 0.5);
        text-align: center;
        transition: all 0.5s;
    }
    
    .metric-card-premium:hover {
        transform: translateY(-10px) scale(1.03);
        box-shadow: 0 30px 80px rgba(66, 165, 245, 0.35);
    }
    
    .metric-label-premium {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        color: #bfdbfe;
        font-weight: 700;
        margin-bottom: 1.25rem;
    }
    
    .metric-value-premium {
        font-size: 2.4rem;
        font-weight: 900;
        color: white;
        line-height: 1;
    }
    
    .data-container {
        background: linear-gradient(135deg, rgba(17, 24, 39, 0.8) 0%, rgba(30, 41, 59, 0.7) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(66, 165, 245, 0.15);
        border-radius: 24px;
        padding: 3rem;
        margin: 2.5rem 0;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
    }
    
    .dashboard-premium {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%);
        backdrop-filter: blur(30px);
        border: 1px solid rgba(96, 165, 250, 0.25);
        border-radius: 28px;
        padding: 4rem;
        margin: 3rem 0;
        box-shadow: 0 25px 80px rgba(0, 0, 0, 0.6);
        position: relative;
    }
    
    .dashboard-premium::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #42a5f5 0%, #7e57c2 50%, #ec4899 100%);
    }
    
    .dashboard-header-inside {
        background: linear-gradient(135deg, rgba(66, 165, 245, 0.18) 0%, rgba(126, 87, 194, 0.18) 100%);
        border: 1px solid rgba(96, 165, 250, 0.35);
        padding: 2rem 2.5rem;
        border-radius: 20px;
        margin-bottom: 3rem;
    }
    
    .dashboard-title-inside {
        font-size: 1.85rem;
        font-weight: 800;
        color: #bfdbfe;
        margin: 0;
    }
    
    .dashboard-subtitle-inside {
        font-size: 1.05rem;
        color: #94a3b8;
        margin: 0.75rem 0 0 0;
    }
    
    .dashboard-premium h2 {
        color: #93c5fd !important;
        font-weight: 800;
        font-size: 2rem;
        margin: 3rem 0 1.75rem 0;
        padding-bottom: 1.25rem;
        border-bottom: 2px solid rgba(66, 165, 245, 0.3);
    }
    
    .dashboard-premium h3 {
        color: #bfdbfe !important;
        font-weight: 700;
        font-size: 1.5rem;
        margin: 2.25rem 0 1.25rem 0;
    }
    
    .dashboard-premium p,
    .dashboard-premium li {
        color: #cbd5e1 !important;
        line-height: 2;
        font-size: 1.05rem;
    }
    
    .dashboard-premium ul {
        margin-left: 2.25rem;
        margin-top: 1.25rem;
    }
    
    .dashboard-premium strong {
        color: #f1f5f9 !important;
        font-weight: 700;
    }
    
    .event-card-full {
        background: rgba(30, 41, 59, 0.5);
        border-left: 4px solid #42a5f5;
        padding: 2rem;
        border-radius: 16px;
        margin: 1.75rem 0;
        transition: all 0.4s;
    }
    
    .event-card-full:hover {
        background: rgba(30, 41, 59, 0.7);
        transform: translateX(6px);
    }
    
    .event-badge-inside {
        background: linear-gradient(135deg, rgba(66, 165, 245, 0.25) 0%, rgba(96, 165, 250, 0.25) 100%);
        color: #bfdbfe;
        padding: 0.5rem 1.25rem;
        border-radius: 24px;
        font-size: 0.7rem;
        font-weight: 800;
        text-transform: uppercase;
        display: inline-block;
        border: 1px solid rgba(96, 165, 250, 0.4);
    }
    
    .event-badge-funding { background: linear-gradient(135deg, rgba(16, 185, 129, 0.25) 0%, rgba(5, 150, 105, 0.25) 100%); color: #6ee7b7; border-color: rgba(16, 185, 129, 0.5); }
    .event-badge-partnership { background: linear-gradient(135deg, rgba(139, 92, 246, 0.25) 0%, rgba(124, 58, 237, 0.25) 100%); color: #c4b5fd; border-color: rgba(139, 92, 246, 0.5); }
    .event-badge-product-release { background: linear-gradient(135deg, rgba(236, 72, 153, 0.25) 0%, rgba(219, 39, 119, 0.25) 100%); color: #f9a8d4; border-color: rgba(236, 72, 153, 0.5); }
    
    .event-title-inside {
        font-size: 1.2rem;
        font-weight: 700;
        color: #e3f2fd;
        margin: 0.75rem 0 0.5rem 0;
    }
    
    .event-date-inside {
        color: #90caf9;
        font-size: 0.9rem;
        font-weight: 600;
    }
    
    .event-description-inside {
        color: #cbd5e1;
        margin-top: 1rem;
        line-height: 1.7;
    }
    
    .product-card-full {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(51, 65, 85, 0.6) 100%);
        border: 1px solid rgba(96, 165, 250, 0.25);
        border-radius: 20px;
        padding: 3rem;
        margin: 2.5rem 0;
        box-shadow: 0 12px 48px rgba(0, 0, 0, 0.4);
    }
    
    .product-header-full {
        display: flex;
        align-items: center;
        margin-bottom: 1.5rem;
    }
    
    .product-number {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        color: white;
        min-width: 45px;
        height: 45px;
        border-radius: 14px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 1.3rem;
        margin-right: 1.25rem;
        box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
    }
    
    .product-name-full {
        font-size: 1.75rem;
        font-weight: 800;
        color: #bfdbfe;
    }
    
    .product-description-full {
        color: #cbd5e1;
        line-height: 1.8;
        font-size: 1.05rem;
        margin: 1.5rem 0;
    }
    
    .leader-card-full {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(66, 165, 245, 0.2);
        border-radius: 16px;
        padding: 2.5rem;
        margin: 1.75rem 0;
    }
    
    .leader-header-full {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
    }
    
    .leader-name-full {
        font-size: 1.5rem;
        font-weight: 800;
        color: #bfdbfe;
        margin-right: 1rem;
    }
    
    .founder-badge {
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 16px;
        font-size: 0.75rem;
        font-weight: 800;
        text-transform: uppercase;
    }
    
    .leader-role-full {
        color: #90caf9;
        font-size: 1.15rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    .leader-detail {
        color: #cbd5e1;
        margin: 0.5rem 0;
        line-height: 1.6;
    }
    
    .stMarkdown, p, li, td, th, span, div, label { color: #cbd5e1; }
    h1 { color: #f1f5f9 !important; font-size: 3.25rem !important; font-weight: 900 !important; }
    h2, h3, h4 { color: #e3f2fd !important; }
    
    .stDataFrame {
        background: rgba(17, 24, 39, 0.8);
        border-radius: 18px;
        border: 1px solid rgba(66, 165, 245, 0.2);
    }
    
    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.4);
        padding: 1.75rem;
        border-radius: 16px;
        border: 1px solid rgba(66, 165, 245, 0.25);
    }
    
    [data-testid="stMetricLabel"] { color: #90caf9 !important; font-weight: 700; }
    [data-testid="stMetricValue"] { color: #f1f5f9 !important; font-weight: 800; }
    
    .stButton > button {
        border-radius: 16px;
        font-weight: 800;
        padding: 1rem 3rem;
        background: linear-gradient(135deg, rgba(30, 64, 175, 0.6) 0%, rgba(59, 130, 246, 0.6) 100%);
        color: white;
        border: 1px solid rgba(66, 165, 245, 0.4);
        box-shadow: 0 8px 24px rgba(59, 130, 246, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 50px rgba(66, 165, 245, 0.5);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        background: rgba(17, 24, 39, 0.5);
        padding: 1rem 1.5rem;
        border-radius: 20px;
    }
    
    .stTabs [data-baseweb="tab"] {
        font-weight: 800;
        font-size: 1.2rem;
        padding: 1.5rem 3rem;
        border-radius: 16px;
        color: #90caf9;
        background: rgba(30, 41, 59, 0.3);
        border: 1px solid rgba(66, 165, 245, 0.2);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        color: white !important;
        box-shadow: 0 12px 36px rgba(66, 165, 245, 0.5);
    }
</style>
""", unsafe_allow_html=True)

API_BASE = "http://localhost:8000"

def aggressive_clean(text):
    """Nuclear HTML removal"""
    if not text or text in ['Not disclosed', 'None', None]:
        return 'N/A'
    text = str(text)
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'</[^>]*>', '', text)
    text = re.sub(r'&\w+;', '', text)
    text = text.replace('</div>', '').replace('<div>', '')
    text = ' '.join(text.split())
    return text.strip() or 'N/A'

@st.cache_data(ttl=600)
def get_companies_table():
    try:
        response = requests.get(f"{API_BASE}/api/companies/list", timeout=30)
        return pd.DataFrame(response.json()) if response.status_code == 200 else pd.DataFrame()
    except:
        return pd.DataFrame()

def analyze_company(company):
    try:
        response = requests.post(
            f"{API_BASE}/api/dual-pipeline/compare",
            json={"company_id": company['company_id'], "company_name": company['company_name'], "website": company['website']},
            timeout=180
        )
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def render_company_data(payload):
    st.markdown('<div class="section-title">🏢 Company Overview</div>', unsafe_allow_html=True)
    
    if 'company_record' in payload:
        company = payload['company_record']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f'<div class="metric-card-premium"><div class="metric-label-premium">Legal Entity</div><div class="metric-value-premium" style="font-size:1.4rem;">{company.get("legal_name") or "Not disclosed"}</div></div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'<div class="metric-card-premium"><div class="metric-label-premium">Founded</div><div class="metric-value-premium">{company.get("founded_year") or "Not disclosed"}</div></div>', unsafe_allow_html=True)
        
        with col3:
            city = company.get('hq_city') or 'Not disclosed'
            state = company.get('hq_state')
            country = company.get('hq_country') or ''
            if state:
                hq = f"{city}, {state}"
            else:
                hq = f"{city}, {country}" if country else city
            st.markdown(f'<div class="metric-card-premium"><div class="metric-label-premium">Headquarters</div><div class="metric-value-premium" style="font-size:1.25rem;">{hq}</div></div>', unsafe_allow_html=True)
        
        with col4:
            funding = company.get('total_raised_usd')
            funding_str = f"${funding/1e6:.1f}M" if funding else "Not disclosed"
            st.markdown(f'<div class="metric-card-premium"><div class="metric-label-premium">Capital Raised</div><div class="metric-value-premium" style="font-size:1.5rem;">{funding_str}</div></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="data-container">', unsafe_allow_html=True)
        st.markdown("### Description")
        st.write(company.get('description', 'Not available'))
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Categories")
            categories = company.get('categories') or []
            if categories:
                for cat in categories:
                    if cat and cat != 'None':
                        st.markdown(f"• {cat}")
            else:
                st.caption("Not disclosed")
        
        with col2:
            st.markdown("### Last Round")
            if company.get('last_round_name'):
                st.markdown(f"**{company.get('last_round_name')}**")
                if company.get('last_round_date'):
                    st.caption(f"{company.get('last_round_date')}")
            else:
                st.caption("Not disclosed")
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_events(events):
    st.markdown('<div class="section-title">📅 Events Timeline</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="data-container">', unsafe_allow_html=True)
    
    funding = [e for e in events if e.get('event_type') == 'funding']
    partnerships = [e for e in events if e.get('event_type') == 'partnership']
    products = [e for e in events if e.get('event_type') == 'product_release']
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Funding", len(funding))
    with col2:
        st.metric("🤝 Partnerships", len(partnerships))
    with col3:
        st.metric("🚀 Products", len(products))
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    sorted_events = sorted(events, key=lambda x: x.get('occurred_on') or '', reverse=True)[:12]
    
    for event in sorted_events:
        etype = event.get('event_type', 'announcement').replace('_', '-')
        event_label = event.get('event_type', 'announcement').replace('_', ' ').upper()
        title = event.get('title', 'Event')
        date = event.get('occurred_on') or 'Date N/A'
        desc = event.get('description', '')
        
        event_html = f'''
        <div class="event-card-full">
            <div class="event-header-inside">
                <span class="event-badge-inside event-badge-{etype}">{event_label}</span>
            </div>
            <div class="event-title-inside">{title}</div>
            <div class="event-date-inside">📅 {date}</div>
        '''
        
        if desc and desc != 'None':
            event_html += f'<div class="event-description-inside">{desc}</div>'
        
        if event.get('event_type') == 'funding':
            details = []
            if event.get('amount_usd'):
                details.append(f"💵 ${event['amount_usd']/1e6:.1f}M")
            investors = event.get('investors') or []
            valid = [i for i in investors if i and i != 'None']
            if valid:
                details.append(f"🏦 {', '.join(valid)}")
            if details:
                event_html += f'<div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(66, 165, 245, 0.2); color: #cbd5e1;">{" | ".join(details)}</div>'
        
        event_html += '</div>'
        st.markdown(event_html, unsafe_allow_html=True)

def render_products(products):
    st.markdown('<div class="section-title">🎯 Products</div>', unsafe_allow_html=True)
    
    for i, prod in enumerate(products, 1):
        name = prod.get('name', f'Product {i}')
        desc = prod.get('description', '')
        pricing = prod.get('pricing_model')
        tiers = prod.get('pricing_tiers_public') or []
        partners = prod.get('integration_partners') or []
        customers = prod.get('reference_customers') or []
        
        product_html = f'''
        <div class="product-card-full">
            <div class="product-header-full">
                <span class="product-number">{i}</span>
                <span class="product-name-full">{name if name != 'None' else f'Product {i}'}</span>
            </div>
        '''
        
        if desc and desc != 'None':
            product_html += f'<div class="product-description-full">{desc}</div>'
        
        details = []
        if pricing and pricing != 'None':
            details.append(f'💰 Pricing: {pricing.title()}')
        
        valid_tiers = [t for t in tiers if t and t != 'None']
        if valid_tiers:
            details.append(f'�� Tiers: {", ".join(valid_tiers)}')
        
        valid_partners = [p for p in partners if p and p != 'None']
        if valid_partners:
            details.append(f'🔗 Partners: {len(valid_partners)}')
        
        if details:
            product_html += f'<div style="margin: 1.5rem 0; display: flex; gap: 2rem; flex-wrap: wrap;">'
            for detail in details:
                product_html += f'<div style="background: rgba(59, 130, 246, 0.08); padding: 1rem 1.5rem; border-radius: 10px; border-left: 3px solid #42a5f5; color: #cbd5e1;"><strong>{detail}</strong></div>'
            product_html += '</div>'
        
        valid_customers = [c for c in customers if c and c != 'None']
        if valid_customers:
            product_html += f'<div style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid rgba(66, 165, 245, 0.2);"><strong style="color: #90caf9;">Notable Customers:</strong><br><span style="color: #cbd5e1; margin-top: 0.5rem; display: inline-block;">{", ".join(valid_customers)}</span></div>'
        
        product_html += '</div>'
        st.markdown(product_html, unsafe_allow_html=True)

def render_leadership(leaders):
    st.markdown('<div class="section-title">👔 Leadership</div>', unsafe_allow_html=True)
    
    leadership_html = '<div class="data-container">'
    
    for leader in leaders:
        name = aggressive_clean(leader.get('name'))
        role = aggressive_clean(leader.get('role'))
        is_founder = leader.get('is_founder', False)
        prev = aggressive_clean(leader.get('previous_affiliation'))
        edu = aggressive_clean(leader.get('education'))
        
        leadership_html += '<div class="leader-card-full">'
        leadership_html += '<div class="leader-header-full">'
        leadership_html += f'<span class="leader-name-full">{name}</span>'
        if is_founder:
            leadership_html += '<span class="founder-badge">FOUNDER</span>'
        leadership_html += '</div>'
        leadership_html += f'<div class="leader-role-full">{role}</div>'
        
        if prev not in ['Not disclosed', 'N/A', 'None']:
            leadership_html += f'<div class="leader-detail"><strong>Previously:</strong> {prev}</div>'
        
        if edu not in ['Not disclosed', 'N/A', 'None']:
            leadership_html += f'<div class="leader-detail"><strong>Education:</strong> {edu}</div>'
        
        leadership_html += '</div>'
    
    leadership_html += '</div>'
    st.markdown(leadership_html, unsafe_allow_html=True)

def render_comparison(evaluation):
    st.markdown('<div class="section-title">⚖️ Pipeline Comparison</div>', unsafe_allow_html=True)
    
    rag_scores = evaluation.get('rag_scores', {})
    structured_scores = evaluation.get('structured_scores', {})
    winner = evaluation.get('winner', 'structured')
    reasoning = evaluation.get('reasoning', 'Comparison analysis not available')
    
    html = '<div class="comparison-container">'
    html += f'<h3 style="color: #bfdbfe; margin-bottom: 2rem;">Winner: <span class="winner-badge">{"Structured" if winner == "structured" else "RAG"} Pipeline</span></h3>'
    
    html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin: 2rem 0;">'
    html += f'<div class="score-card {"winner" if winner == "structured" else ""}">'
    html += '<h4 style="color: #90caf9; margin: 0 0 1.5rem 0;">📋 Structured Pipeline</h4>'
    html += f'<div style="font-size: 3rem; font-weight: 900; color: {"#10b981" if winner == "structured" else "#60a5fa"}; margin: 1rem 0;">'
    html += f'{structured_scores.get("total_score", 0)}/10'
    html += '</div>'
    html += f'<div style="color: #94a3b8; font-size: 0.9rem; margin-top: 1rem;">{structured_scores.get("notes", "Schema-validated extraction")}</div>'
    html += '</div>'
    
    html += f'<div class="score-card {"winner" if winner == "rag" else ""}">'
    html += '<h4 style="color: #90caf9; margin: 0 0 1.5rem 0;">📄 RAG Pipeline</h4>'
    html += f'<div style="font-size: 3rem; font-weight: 900; color: {"#10b981" if winner == "rag" else "#60a5fa"}; margin: 1rem 0;">'
    html += f'{rag_scores.get("total_score", 0)}/10'
    html += '</div>'
    html += f'<div style="color: #94a3b8; font-size: 0.9rem; margin-top: 1rem;">{rag_scores.get("notes", "Semantic search retrieval")}</div>'
    html += '</div>'
    html += '</div>'
    
    html += '<div style="margin-top: 2rem; padding: 2rem; background: rgba(59, 130, 246, 0.1); border-left: 4px solid #42a5f5; border-radius: 12px;">'
    html += '<h4 style="color: #bfdbfe; margin: 0 0 1rem 0;">🔍 Analysis</h4>'
    html += f'<p style="color: #cbd5e1; line-height: 1.8; margin: 0;">{reasoning}</p>'
    html += '</div>'
    
    html += '<div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem; margin-top: 2rem;">'
    
    metrics = [
        ('Factual', 'factual_correctness', 3),
        ('Schema', 'schema_adherence', 2),
        ('Provenance', 'provenance_use', 2),
        ('Control', 'hallucination_control', 2),
        ('Readable', 'readability', 1)
    ]
    
    for label, key, max_val in metrics:
        html += '<div style="text-align: center; padding: 1rem; background: rgba(30, 41, 59, 0.5); border-radius: 12px;">'
        html += f'<div style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.5rem;">{label}</div>'
        html += f'<div style="color: #bfdbfe; font-weight: 700;">S: {structured_scores.get(key, 0)}/{max_val} | R: {rag_scores.get(key, 0)}/{max_val}</div>'
        html += '</div>'
    
    html += '</div>'
    html += '</div>'
    
    st.markdown(html, unsafe_allow_html=True)

def render_dashboard(dashboard_text, pipeline_name, description):
    dashboard_html = f'''
    <div class="dashboard-premium">
        <div class="dashboard-header-inside">
            <div class="dashboard-title-inside">{pipeline_name}</div>
            <div class="dashboard-subtitle-inside">{description}</div>
        </div>
        {dashboard_text}
    </div>
    '''
    st.markdown(dashboard_html, unsafe_allow_html=True)

def main():
    st.markdown(
        '<div class="premium-header">'
        '<div class="premium-title">📊 ORBIT Intelligence Platform</div>'
        '<div class="premium-subtitle">Private Equity Diligence System • Forbes AI 50</div>'
        '</div>',
        unsafe_allow_html=True
    )
    
    try:
        requests.get(f"{API_BASE}/health", timeout=5)
        st.success("✅ System Operational")
    except:
        st.error("⚠️ Backend Offline")
        return
    
    st.markdown("---")
    
    if 'analysis_result' not in st.session_state:
        st.markdown('<div class="section-title">📊 Forbes AI 50 Universe</div>', unsafe_allow_html=True)
        
        df = get_companies_table()
        if df.empty:
            return
        
        st.info("**Select any company for comprehensive PE analysis**")
        
        display_df = df[['rank', 'company_name', 'website']].copy()
        display_df.columns = ['Rank', 'Company', 'Website']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=520)
        
        st.markdown("---")
        
        col1, col2 = st.columns([4, 1])
        with col1:
            selected = st.selectbox("Company:", df.to_dict('records'), format_func=lambda x: f"#{x['rank']:02d} — {x['company_name']}")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Generate", type="primary", use_container_width=True):
                with st.spinner("Generating..."):
                    result = analyze_company(selected)
                    if result:
                        st.session_state.analysis_result = result
                        st.session_state.selected_company = selected
                        st.rerun()
    
    else:
        result = st.session_state.analysis_result
        company = st.session_state.selected_company
        
        if st.button("← Back"):
            del st.session_state.analysis_result
            del st.session_state.selected_company
            st.rerun()
        
        st.markdown("---")
        st.markdown(f"# {company['company_name']}")
        st.caption(f"Rank #{company['rank']} • {company['website']}")
        
        if result.get('is_fallback'):
            st.warning("⚠️ Fallback data used")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("⚡ Time", f"{result['processing_time_seconds']:.1f}s")
        with col2:
            st.metric("📄 Pages", len(result['pages_scraped']))
        with col3:
            st.metric("🔍 Source", "Fallback" if result.get('is_fallback') else "Live")
        
        st.markdown("---")
        
        render_company_data(result['complete_payload'])
        
        if result['complete_payload'].get('events'):
            render_events(result['complete_payload']['events'])
        
        if result['complete_payload'].get('products'):
            render_products(result['complete_payload']['products'])
        
        if result['complete_payload'].get('leadership'):
            render_leadership(result['complete_payload']['leadership'])
        
        vis = result['complete_payload'].get('visibility', [{}])[0]
        if any([vis.get(k) for k in ['news_mentions_30d', 'avg_sentiment', 'github_stars', 'glassdoor_rating']]):
            st.markdown('<div class="section-title">📈 Visibility</div>', unsafe_allow_html=True)
            st.markdown('<div class="data-container">', unsafe_allow_html=True)
            
            vis_data = []
            if vis.get('news_mentions_30d'):
                vis_data.append(("📰 News (30d)", vis['news_mentions_30d']))
            if vis.get('avg_sentiment') is not None:
                vis_data.append(("😊 Sentiment", f"{vis['avg_sentiment']:.2f}"))
            if vis.get('github_stars'):
                vis_data.append(("⭐ GitHub", f"{vis['github_stars']:,}"))
            if vis.get('glassdoor_rating'):
                vis_data.append(("💼 Glassdoor", f"{vis['glassdoor_rating']:.1f}/5"))
            
            cols = st.columns(len(vis_data))
            for idx, (label, value) in enumerate(vis_data):
                with cols[idx]:
                    st.metric(label, value)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown('<div class="section-title">📊 PE Dashboards</div>', unsafe_allow_html=True)
        st.info("**8-Section Format:** Overview → Business → Funding → Growth → Sentiment → Risks → Outlook → Gaps")
        
        tab1, tab2 = st.tabs(["📄 RAG Pipeline", "📋 Structured Pipeline"])
        
        with tab1:
            render_dashboard(result['rag_pipeline']['dashboard'], "RAG Pipeline Dashboard", "Unstructured text retrieval with semantic search")
        
        with tab2:
            render_dashboard(result['structured_pipeline']['dashboard'], "Structured Pipeline Dashboard", "Schema-validated Pydantic extraction")
        
        st.markdown("---")
        
        if result.get('evaluation'):
            render_comparison(result['evaluation'])

if __name__ == "__main__":
    main()
