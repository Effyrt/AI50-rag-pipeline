summary: AI50-rag-pipeline
id: AI50-rag-pipeline
categories: data-engineering

# Project ORBIT: Codelabs Tutorial

## Overview

Build an automated PE dashboard factory with **dual-pipeline architecture**: Structured Pipeline (5-pass extraction) and RAG Pipeline (vector retrieval) for generating Forbes AI 50 investor dashboards on GCP.

---

## Step 1: Environment Setup

```bash
# Clone repository
git clone https://github.com/Effyrt/AI50-rag-pipeline.git
cd AI50-rag-pipeline

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add OPENAI_API_KEY and GCP settings
```

**✅ Checkpoint:** Virtual environment activated with all dependencies installed.

---

## Step 2: Understanding Dual-Pipeline Architecture

### System Overview

Project ORBIT uses **two parallel pipelines** for dashboard generation:

```
                    Forbes AI 50 Companies
                            ↓
                 Playwright Web Scraper
                            ↓
                    GCS (raw-data/)
                            ↓
              ┌─────────────┴─────────────┐
              ↓                           ↓
    STRUCTURED PIPELINE            RAG PIPELINE
    (5-Pass Extraction)         (Vector Indexing)
              ↓                           ↓
    GCS (structured-data/)      GCS (vector-index/)
              ↓                           ↓
    Payload Assembly             Vector Retrieval
              ↓                           ↓
              └─────────────┬─────────────┘
                            ↓
                    Dashboard Generation
                    (FastAPI + Streamlit)
```

### Pipeline Comparison

| Feature | Structured Pipeline | RAG Pipeline |
|---------|-------------------|--------------|
| **Method** | 5-pass targeted extraction | Vector similarity search |
| **Data Format** | Pydantic-validated JSON | Embedded text chunks |
| **Output** | Consistent, structured | Context-rich, flexible |
| **Best For** | Production reports | Exploratory analysis |

---

## Step 3: Data Ingestion - Web Scraping

**Purpose:** Collect raw data from company websites as the foundation for both pipelines.

**What's Happening:**
- Playwright scrapes: homepage, about, products, careers, blog
- Footer link detection for comprehensive coverage
- Raw HTML/text stored in `data/raw/` (or GCS in production)

**✅ Checkpoint:** Raw HTML files collected for Forbes AI 50 companies.

---

## Step 4: Structured Pipeline

**Purpose:**
Extract precise, validated, and schema-aligned data using five sequential extraction passes powered by Pydantic models.

**Key Concepts:**

Each pass focuses on a specific data dimension (e.g., Company Info, Funding, Product, Metrics, Market).

Pydantic ensures type validation and schema consistency, preventing malformed outputs.

Ideal for structured or semi-structured documents such as profiles, articles, and reports.

---

## Step 5: RAG Pipeline - Vector Indexing

**Purpose:** Build vector index for semantic search and context retrieval.

**What's Happening:**

1. **Document Chunking**
   - Raw HTML → cleaned text
   - Split into 800-character chunks with 200-character overlap
     (`RecursiveCharacterTextSplitter`, see `rag_pipeline.py`)
   - Preserves context across chunks

2. **Embedding Generation**
   - `sentence-transformers/all-MiniLM-L6-v2`, run locally
   - Each chunk → 384-dimensional vector
   - No API key and no per-token cost for embeddings

3. **Chroma Indexing**
   - Persistent Chroma collection under `data/vector_db/`
   - Enables fast nearest-neighbour retrieval
   - Chunk count depends on how many pages were scraped; check with
     `RAGPipeline().get_stats()` rather than assuming a figure

4. **Metadata Storage**
   - Company name, URL, chunk ID
   - Enables filtering and attribution

**✅ Checkpoint:** Vector index built and stored in `data/vector_db/`.

---

## Step 6: Run Both Pipelines Locally

### Start Backend & Frontend

### Test Structured Pipeline

1. Open http://localhost:8501
2. Select company: "OpenAI"
3. Choose: **"Structured Pipeline"**
4. Click "Generate Dashboard"

**Expected Output:**
```markdown
# OpenAI - Investor Dashboard

## Company Overview
OpenAI | Founded: 2015 | HQ: San Francisco, CA
Leading AI research organization...

## Business Model
Revenue: $1.6B (2023)
Model: API subscriptions + Enterprise licensing

## Funding Analysis
Total Raised: $11.3B
Latest: Series D ($10B, Jan 2024)
Valuation: $86B

[8 sections total...]
```

### Test RAG Pipeline

1. Same company: "OpenAI"
2. Choose: **"RAG Pipeline"**
3. Click "Generate Dashboard"

**Expected Output:**
```markdown
# OpenAI - Investor Dashboard

## Company Overview
Based on comprehensive analysis of OpenAI's public materials...
[More narrative, context-rich content]

## Business Model
The company operates through multiple revenue streams...
[Synthesized from various sources]

[8 sections total...]
```

**✅ Checkpoint:** Both pipelines generate complete dashboards locally.

---

## Step 8: GCP Infrastructure Setup

**Creates:**
- `raw-data/` bucket for scraped HTML
- `structured-data/` bucket for Pydantic JSONs
- vector index persisted by the RAG index-builder job
- `payloads/` bucket for combined data

**✅ Checkpoint:** 4 GCS buckets created for dual-pipeline data.

---

## Step 9: Deploy Pipeline Jobs to Cloud Run

**Deploys 3 Cloud Run Jobs:**

1. **`ai50-scraper`**
   - Scrapes company websites
   - Outputs to `raw-data/`

2. **`ai50-extractor`**
   - Runs 5-pass structured extraction
   - Outputs to `structured-data/`

3. **`ai50-rag-index-builder`**
   - Builds the Chroma vector index
   - Outputs to `vector-index/`


**✅ Checkpoint:** All three pipeline jobs execute successfully.

---

## Step 10: Set Up Airflow Orchestration

```bash
cd gcp
chmod +x setup_composer.sh
./setup_composer.sh

# Get Airflow UI URL (after ~20-30 min setup)
gcloud composer environments describe ai50-composer \
  --location us-central1 \
  --format="get(config.airflowUri)"
```

### DAG Workflow

The `ai50_daily_refresh` DAG orchestrates both pipelines:

```
┌─────────────┐
│   Scraper   │  → GCS raw-data/
└──────┬──────┘
       ↓
   ┌───┴───┐
   ↓       ↓
┌────────┐ ┌──────────┐
│Extractor│ │RAG Index │
│(5-pass) │ │Builder   │
└────┬───┘ └────┬─────┘
     ↓          ↓
     GCS       GCS
structured/  vector-index/
```

**✅ Checkpoint:** `ai50_daily_refresh` DAG runs successfully with all tasks green.

---

## Step 11: Deploy Dashboard Services

**API Endpoints:**
- `/generate/structured` - Uses 5-pass extracted data
- `/generate/rag` - Uses vector retrieval

**✅ Checkpoint:** Both services accessible via HTTPS URLs.

---

## Step 12: Pipeline Evaluation & Comparison

### Side-by-Side Comparison

Generate dashboards for the same company using both pipelines:

#### Structured Pipeline Output

```markdown
## Funding Analysis
Total Raised: $11.3B
Latest Round: Series D ($10B, January 2024)
Valuation: $86B
Lead Investors: Microsoft, Sequoia Capital

## Growth Metrics
- 100M+ weekly ChatGPT users (Q4 2023)
- 2M+ developers using API (verified)
- 92% enterprise retention rate (reported)
```

#### RAG Pipeline Output

```markdown
## Funding Analysis
OpenAI has raised significant capital from top-tier investors.
The company's latest funding round valued it at approximately 
$86 billion, with Microsoft as a major strategic investor...

## Growth Metrics
The platform has experienced explosive user growth, with ChatGPT
becoming one of the fastest-growing consumer applications...
```

### Why Structured Pipeline Performs Better

#### 1. **Precision Through 5-Pass Extraction**
- Each pass targets specific data types
- Pass 3 (GitHub) only extracts tech metrics → no confusion with financial data
- Pass 4 (BI) focuses on strategy → cleaner competitive analysis

#### 2. **Data Validation & Type Safety**
- **Structured:** Pydantic enforces types
  ```json
  {"funding_total": 11300000000}  // Always float
  {"founded_year": 2015}          // Always int
  ```
- **RAG:** Free-form text
  ```
  "raised $11.3B" or "11.3 billion" or "significant funding"
  ```

#### 3. **Explicit Handling of Missing Data**
- **Structured:** Shows "Unknown" when data unavailable
  ```json
  {"revenue_2023": "Unknown"}
  ```
- **RAG:** May hallucinate or omit
  ```
  "The company appears profitable..." (unverified)
  ```

#### 4. **Performance Metrics**

> **These figures must be measured, not assumed.** Earlier versions of this codelab
> quoted specific percentages that no artifact in the repository supported. Run the
> evaluation harness and record what it reports:
>
> ```bash
> python scripts/run_eval.py --companies anthropic,databricks,abridge,hebbia,xai \
>                            --scorer "<your name>"
> ```
>
> Each row below names the source that produces it. Fill the table in from
> `EVAL.md` and `data/eval/<company>/scores.json` once the run has completed.

| Metric | Structured Pipeline | RAG Pipeline | Where the number comes from |
|--------|--------------------|--------------|------------------------------|
| **Schema adherence** (0–2) | _to be measured_ | _to be measured_ | `evaluator.score_schema`, automated |
| **Provenance use** (0–2) | _to be measured_ | _to be measured_ | `evaluator.score_provenance`, automated |
| **Hallucination control** (0–2) | _to be measured_ | _to be measured_ | `evaluator.score_hallucination`, automated |
| **Factual correctness** (0–3) | _to be measured_ | _to be measured_ | human-scored, scorer recorded in `scores.json` |
| **Readability** (0–1) | _to be measured_ | _to be measured_ | human-scored, scorer recorded in `scores.json` |
| **Generation latency** | _to be measured_ | _to be measured_ | `latency_seconds` in `scores.json` |
| **Token usage** | _to be measured_ | _to be measured_ | `input_tokens` / `output_tokens` in `scores.json` |
| **Missing data handling** | explicit `"Not disclosed."` | explicit `"Not disclosed."` | both pipelines share the same prompt contract |

#### 5. **Consistency Across Companies**

**Structured Pipeline** - Guaranteed format:
```
All 50 dashboards have:
✓ Same 8 sections in same order
✓ Same metrics reported (revenue, valuation, etc.)
✓ Easy to compare company A vs company B
✓ Can export to standard templates
```

**RAG Pipeline** - Variable output:
```
❌ Section order varies by company
❌ Some metrics present in one dashboard, missing in another
❌ Narrative style differs per company
❌ Hard to standardize for reports
```

#### 6. **Production Use Cases**

**Use Structured Pipeline for:**
- ✅ Investor reports for stakeholders
- ✅ Automated daily/weekly briefings
- ✅ Due diligence packages
- ✅ Comparative analysis across multiple companies
- ✅ Feeding downstream systems (CRMs, databases)

**Use RAG Pipeline for:**
- 🔍 Exploratory research
- 🔍 Initial company discovery
- 🔍 Ad-hoc questions requiring context
- 🔍 Brainstorming and synthesis

**✅ Checkpoint:** Clear understanding of when to use each pipeline, and a completed
`EVAL.md` showing which one measured better on your data.

---

## Step 13: Monitoring and Maintenance

**Automated Schedule:**
- DAG runs daily
- Scraper → Extractor (Structured) → RAG Index Builder → Payloads
- Fresh dashboards available 

---

### Key Takeaway

The **Structured Pipeline** is expected to produce more consistent investor dashboards,
because of:
- its targeted 5-pass extraction architecture
- Pydantic validation and type safety
- a fixed field set, giving comparable output across companies
- explicit handling of missing data

Whether that expectation holds on your data is exactly what Lab 9 is for. Run the
evaluation, record the scores in `EVAL.md`, and state the result you actually measured —
including if it contradicts the hypothesis above.
