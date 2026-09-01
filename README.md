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
    [Video Tutorial](https://drive.google.com/file/d/1l9eHigLPNOoIipDBt_OJbqbPLDQG29DQ/view?usp=sharing)
Codelab Document:
👉 [Open Google Codelab](https://codelabs-preview.appspot.com/?file_id=https://raw.githubusercontent.com/Effyrt/AI50-rag-pipeline/main/codelabs.md#0)

### Key Features

- **Dual Pipeline Architecture**: 
  - **Structured Pipeline**: Uses Pydantic + Instructor for precise data extraction
  - **RAG Pipeline**: Uses a Chroma vector database with local sentence-transformers embeddings for retrieval-augmented generation
  
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
uvicorn src.backend.api:app --reload

# In another terminal, start Streamlit frontend
streamlit run src/frontend/streamlit_app.py
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
   - GCS buckets: `raw-data`, `structured-data`, `dashboards` (payloads are stored
     under `structured-data/payloads/`; the vector index is built inside the RAG job)
   - Secret Manager for API keys
   - Service accounts with proper IAM roles

2. **Build and deploy Docker images and services:**
   ```bash
   ./gcp/build_and_deploy.sh
   ```
   This builds four images and deploys:
   - Cloud Run **Jobs** (batch): `ai50-scraper`, `ai50-extractor`
   - Cloud Run **Services** (Lab 10): `ai50-api` (FastAPI) and `ai50-ui` (Streamlit),
     both with `--min-instances=0` so they scale to zero when idle. The script prints
     both public URLs and wires the UI's `API_BASE` to the API automatically.

3. **Schedule the pipeline (free):**
   ```bash
   ./gcp/setup_scheduler.sh          # weekly, Mondays 03:00 UTC
   SCHEDULE="0 3 * * *" ./gcp/setup_scheduler.sh   # daily
   ```
   Cloud Scheduler drives the two Cloud Run Jobs directly and gives 3 jobs free per
   month, permanently. The Airflow DAGs remain the Lab 2/3 artifact and the tool for
   local development — see `docs/ROADMAP.md` for why Composer is not the default.

### Running costs

The deployed footprint fits inside GCP's always-free allowances at a weekly cadence:

| Resource | Free allowance / month | Usage (weekly) |
|---|---|---|
| Cloud Run vCPU | 180,000 vCPU-s | ~134,400 |
| Cloud Run memory | 360,000 GiB-s | ~149,000 |
| Cloud Run requests | 2,000,000 | hundreds |
| GCS storage | 5 GB | ~2.2 GB steady state |
| Cloud Scheduler | 3 jobs | 2 |

The scraper uses ~30,000 vCPU-s per full 50-company run, so the vCPU allowance permits
about **6 runs/month** — weekly fits, daily (30 runs) is roughly 5× over. Container
image storage slightly exceeds the 0.5 GB Artifact Registry allowance (~$0.15/month).

**Cloud Composer has no free tier** and bills per environment rather than per DAG run,
so it is not part of the default deployment path.
   This builds and deploys:
   - `ai50-scraper` Cloud Run Job
   - `ai50-extractor` Cloud Run Job
   - `ai50-rag-index-builder` Cloud Run Job (if RAG pipeline is deployed)

4. **Optional — managed Airflow via Cloud Composer:**
   ```bash
   ./gcp/setup_composer.sh
   ```
   Creates a Composer environment, uploads the DAGs, and configures service accounts.
   Only needed if you want a hosted Airflow UI; step 3 already schedules the pipeline
   for free.

### Running the Pipeline

1. **Locally, via Airflow:**
   ```bash
   docker compose -f docker/docker-compose.airflow.yml up -d
   # UI at http://localhost:8080 (admin / admin), then trigger ai50_full_ingest_dag
   ```

2. **On a schedule:** Cloud Scheduler triggers the Cloud Run Jobs (step 3 above).
   Check runs with `gcloud run jobs executions list --region=us-central1 --limit=5`.

3. **Via a hosted Airflow UI:** only if Composer was created in step 4 — trigger
   `ai50_daily_refresh_dag` and monitor it in the Airflow UI.

The `ai50_daily_refresh_dag` schedule is `0 3 * * *` (03:00 UTC), as Lab 3 requires. It
re-scrapes the pages that change often (About, Careers, Blog) into a dated per-run
folder, re-extracts, and refreshes the vector index.

### Documentation

- **GCP Deployment Guide**: See `docs/GCP_DEPLOYMENT_GUIDE.md`
- **Airflow Usage Guide**: See `docs/AIRFLOW_USAGE_GUIDE.md`
- **Remediation Roadmap**: See `docs/ROADMAP.md`
- **Remediation Roadmap**: See `docs/ROADMAP.md`

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
├── src/
│   ├── backend/                       # FastAPI app, pipelines, extractors
│   │   ├── api.py                     # FastAPI endpoints
│   │   ├── models.py                  # Pydantic data models
│   │   ├── rag_pipeline.py            # RAG pipeline (Chroma + local embeddings)
│   │   ├── structured_pipeline.py     # Payload loading
│   │   ├── evaluator.py               # Lab 9 rubric scoring
│   │   ├── extractor_v4_bi.py         # 5-pass structured extractor
│   │   ├── extractor_gcp.py           # GCP extractor entry point
│   │   ├── playwright_scraper.py      # Web scraper (Playwright)
│   │   ├── scraper_gcp.py             # GCP scraper entry point
│   │   ├── payload_assembler.py       # Lab 6 payload assembly
│   │   └── github_api.py              # GitHub visibility metrics
│   ├── frontend/
│   │   └── streamlit_app.py           # Streamlit UI
│   └── prompts/
│       └── dashboard_system.md        # 8-section dashboard prompt
├── airflow/dags/                      # Airflow DAGs (single source of truth)
│   ├── ai50_full_ingest_dag.py        # @once full load
│   ├── ai50_daily_refresh_dag.py      # 0 3 * * * daily refresh
│   └── ai50_structured_dag.py         # manual scrape + extract
├── scripts/
│   └── run_eval.py                    # Lab 9 evaluation runner
├── tests/                             # pytest suite (no credentials required)
├── gcp/                               # GCP deployment scripts
│   ├── setup_gcp.sh
│   ├── build_and_deploy.sh
│   └── setup_composer.sh
├── docker/
│   ├── docker-compose.airflow.yml     # local Airflow
│   └── Dockerfile
├── docs/
│   ├── ROADMAP.md                     # remediation roadmap
│   ├── GCP_DEPLOYMENT_GUIDE.md
│   └── AIRFLOW_USAGE_GUIDE.md
├── EVAL.md                            # Lab 9 RAG vs Structured comparison
└── data/                              # Seed only; generated data lives in GCS
    └── forbes_ai50_seed.json
```

## 🧪 Testing

### Automated test suite

Runs with **no** `OPENAI_API_KEY` and **no** GCP credentials — all external boundaries
are mocked, so it is safe to run anywhere and usable in CI.

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Covers: the seed list contract (all 50 companies), Pydantic model validation, every API
route, the Lab 9 rubric scoring, and DAG structure (including a guard against importing
`src/backend` from a DAG, which cannot resolve in Cloud Composer).

### Verify DAGs parse

```bash
docker compose -f docker/docker-compose.airflow.yml up -d
docker compose -f docker/docker-compose.airflow.yml exec airflow \
  airflow dags list-import-errors     # must be empty
```

### Evaluation harness (Lab 9)

```bash
# Exercise the scoring path with no API calls
python scripts/run_eval.py --companies ExampleCo --dry-run

# Real run — needs OPENAI_API_KEY and scraped data under data/raw/
python scripts/run_eval.py --companies anthropic,databricks,abridge,hebbia,xai \
                           --scorer "<your name>"
```

### Pipeline smoke tests

Each requires credentials and writes to GCS:

```bash
python -m src.backend.scraper_gcp      # scraping
python -m src.backend.extractor_gcp    # 5-pass extraction
python -m src.backend.rag_pipeline     # RAG indexing + generation
```

## 📝 Key Technologies

- **Web Scraping**: Playwright, BeautifulSoup4
- **LLM & Extraction**: OpenAI GPT-4o-mini (Instructor + Pydantic for structured extraction)
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim, runs locally, no API cost)
- **Vector DB**: Chroma (persistent, local)
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
- **Live Streamlit dashboard**: _paste the `ai50-ui` URL printed by `./gcp/build_and_deploy.sh`_
- **Live FastAPI backend**: _paste the `ai50-api` URL; interactive docs at `/docs`_

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
