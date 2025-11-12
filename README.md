---
summary: AI50 RAG Pipeline Codelab
id: ai50-rag-pipeline
---
# Project ORBIT — PE Dashboard Factory for Forbes AI 50

**Automated Private-Equity Intelligence System**

## 📋 Project Overview

Project ORBIT is an automated, reproducible, cloud-hosted system that generates investor dashboards for all 50 Forbes AI 50 companies. The system uses two parallel generation pipelines (RAG and Structured) to extract and analyze company data, then serves dashboards through FastAPI and Streamlit on Google Cloud Platform.

## 📘 Interactive Codelab  
View the full tutorial here:  
👉 [Open Google Codelab](https://codelabs-preview.appspot.com/?file_id=https://raw.githubusercontent.com/Effyrt/AI50-rag-pipeline/refs/heads/main/codelabs.md)

### Key Features

- **Dual Pipeline Architecture**: 
  - **Structured Pipeline**: Uses Pydantic + Instructor for precise data extraction
  - **RAG Pipeline**: Uses vector database (FAISS) for retrieval-augmented generation
  
- **Automated Data Ingestion**: 
  - Web scraping with Playwright (homepage, about, products, careers, blog, etc.)
  - Footer link detection for comprehensive page discovery
  - Daily automated refresh via Apache Airflow

- **5-Pass Structured Extraction**:
  - Pass 1: Company basics + Events (funding, partnerships, milestones)
  - Pass 2: Products + Leadership
  - Pass 3: GitHub visibility metrics
  - Pass 4: Business Intelligence (value prop, competitors, GTM)
  - Pass 5: Employee & Hiring data

- **Cloud-Native Deployment**:
  - Google Cloud Platform (GCP) infrastructure
  - Cloud Run Jobs for scalable execution
  - Cloud Composer (Airflow) for orchestration
  - Google Cloud Storage (GCS) for data persistence

- **Dashboard Generation**:
  - 8-section investor dashboards (Company Overview, Business Model, Funding, Growth, Visibility, Risks, Outlook, Disclosure Gaps)
  - FastAPI endpoints for both RAG and Structured pipelines
  - Streamlit UI for interactive dashboard viewing

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Google Cloud Platform                   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────┐       ┌──────────────────┐           │
│  │   Cloud Run      │       │   Cloud Run      │           │
│  │  (FastAPI)       │◄─────►│  (Streamlit)     │           │
│  │  Port: 8000      │       │  Port: 8501      │           │
│  └────────┬─────────┘       └────────┬─────────┘           │
│           │                         │                      │
│           │                         │                      │
│           ▼                         ▼                      │
│  ┌─────────────────────────────────────────────────┐       │
│  │        Google Cloud Storage (GCS)               │       │
│  │  ┌──────────┐  ┌──────────-┐  ┌──────────┐      │       │
│  │  │   raw/   │  │structured/│  │payloads/ │      │       │
│  │  │          │  │           │  │          │      │       │
│  │  └──────────┘  └──────────-┘  └──────────┘      │       │
│  │  ┌──────────┐                                   │       │
│  │  │vector_   │                                   │       │
│  │  │index/    │                                   │       │
│  │  └──────────┘                                   │       │
│  └─────────────────────────────────────────────────┘       │
│           ▲                                                │
│           │                                                │
│  ┌────────┴─────────-┐                                     │
│  │ Cloud Composer    │                                     │
│  │  (Airflow)        │                                     │
│  │                   │                                     │
│  │  - Scraper Job    │                                     │
│  │  - Extractor Job  │                                     │
│  │  - RAG Index Job  │                                     │
│  └───────────────────┘                                     │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Google Cloud Platform account with billing enabled
- `gcloud` CLI installed and configured
- OpenAI API key (for LLM extraction)

### Local Setup

```bash
# Clone repository
git clone https://github.com/Effyrt/AI50-rag-pipeline.git
cd AI50-rag-pipeline

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env  # Create .env file
# Add your OPENAI_API_KEY to .env
```

### Run Locally (Development)

```bash
# Start FastAPI backend
uvicorn src.api:app --reload

# In another terminal, start Streamlit frontend
streamlit run src/streamlit_app.py
```

- FastAPI: http://localhost:8000
- Streamlit: http://localhost:8501

### Docker (Local Testing)

```bash
cd docker
docker compose up --build
```

## ☁️ GCP Deployment

### Initial Setup

1. **Set up GCP infrastructure:**
   ```bash
   cd gcp
   ./setup_gcp.sh
   ```
   This creates:
   - GCS buckets (raw-data, structured-data, payloads, vector-index)
   - Secret Manager for API keys
   - Service accounts with proper IAM roles

2. **Build and deploy Docker images:**
   ```bash
   ./build_and_deploy.sh
   ```
   This builds and deploys:
   - `ai50-scraper` Cloud Run Job
   - `ai50-extractor` Cloud Run Job
   - `ai50-rag-index-builder` Cloud Run Job (if RAG pipeline is deployed)

3. **Set up Cloud Composer (Airflow):**
   ```bash
   ./setup_composer.sh
   ```
   This creates:
   - Cloud Composer environment
   - Uploads DAGs to Composer
   - Configures service accounts

### Running the Pipeline

1. **Manual trigger via Airflow UI:**
   - Access Airflow UI (link provided after Composer setup)
   - Trigger `ai50_daily_refresh` DAG
   - Monitor execution in Airflow UI

2. **Automatic daily refresh:**
   - DAG runs daily at 3 AM UTC
   - Scrapes updated pages
   - Extracts structured data
   - Updates dashboards

### Documentation

- **GCP Deployment Guide**: See `docs/GCP_DEPLOYMENT_GUIDE.md`
- **Airflow Usage Guide**: See `docs/AIRFLOW_USAGE_GUIDE.md`
- **RAG Pipeline Guide**: See `TEAMMATE_RAG_GUIDE.md`

## 📊 Data Flow

1. **Ingestion**: Airflow DAG → Scraper Job → Raw HTML/text → GCS `raw-data/`
2. **Structured Extraction**: Airflow DAG → Extractor Job → Structured JSON → GCS `structured-data/`
3. **RAG Index Building**: Airflow DAG → RAG Index Job → Vector Index → GCS `vector-index/`
4. **Payload Assembly**: Structured data → Combined payloads → GCS `payloads/`
5. **Dashboard Generation**: 
   - RAG: Vector retrieval → LLM → Dashboard markdown
   - Structured: Payload → LLM → Dashboard markdown
6. **Serving**: FastAPI + Streamlit → Display dashboards

## 📁 Project Structure

```
AI50-rag-pipeline/
├── src/                    # Source code
│   ├── playwright_scraper.py      # Web scraper (Playwright)
│   ├── scraper_gcp.py            # GCP scraper entry point
│   ├── extractor_v4_bi.py        # 5-pass structured extractor
│   ├── extractor_gcp.py          # GCP extractor entry point
│   ├── rag_pipeline.py            # RAG pipeline (teammate)
│   ├── models.py                  # Pydantic data models
│   ├── api.py                    # FastAPI endpoints
│   └── streamlit_app.py          # Streamlit UI
├── airflow/dags/           # Airflow DAGs
│   └── ai50_daily_refresh.py
├── gcp/                    # GCP deployment scripts
│   ├── setup_gcp.sh
│   ├── build_and_deploy.sh
│   └── setup_composer.sh
├── docker/                 # Docker configurations
├── docs/                   # Documentation
└── data/                   # Data files (seed only)
    └── forbes_ai50_seed.json
```

## 🧪 Testing

### Test Scraping
```bash
python -m src.scraper_gcp
```

### Test Extraction
```bash
python -m src.extractor_gcp
```

### Test RAG Pipeline
```bash
python -m src.rag_pipeline
```

## 📝 Key Technologies

- **Web Scraping**: Playwright, BeautifulSoup4
- **LLM & Extraction**: OpenAI GPT-4o-mini, Instructor, Pydantic
- **Vector DB**: FAISS
- **Orchestration**: Apache Airflow (Cloud Composer)
- **Cloud Platform**: Google Cloud Platform (Cloud Run, GCS, Cloud Composer)
- **API**: FastAPI
- **UI**: Streamlit
- **Containerization**: Docker

## 📚 Assignment Details

**Course**: DAMG7245 — Assignment 2  
**Project**: Case Study 2 — Project ORBIT (Part 1)  
**Institution**: Northeastern University

## 👥 Team Contributions

### Contribution Attestation

**WE ATTEST THAT WE HAVEN'T USED ANY OTHER STUDENTS' WORK IN OUR ASSIGNMENT AND ABIDE BY THE POLICIES LISTED IN THE STUDENT HANDBOOK**

| Team Member | Contribution | Percentage |
|------------ |--------------|------------|
| **Hemanth Rayudu** | Structured Pipeline, Airflow DAGs, GCP Deployment | 33.33% |
| **PeiYing Chen** | RAG Pipeline Implementation | 33.33% |
| **Om Shailesh Raut** | Frontend & Backend (FastAPI + Streamlit) | 33.33% |

## 🔗 Links

- **GitHub Repository**: https://github.com/Effyrt/AI50-rag-pipeline
- **Project Video Demo**: https://drive.google.com/file/d/188NkhlREF0QHgGaySn_ZsDOnG95bkoVa/view?usp=sharing
- **GCP Project**: gen-lang-client-0653324487

## 📄 License

See `LICENSE` file for details.

## 🙏 Acknowledgments

- Forbes AI 50 for the company list
- OpenAI for GPT-4o-mini API
- Google Cloud Platform for infrastructure
- Apache Airflow for orchestration

---

**Last Updated**: November 2025  
**Status**: Production Ready ✅
