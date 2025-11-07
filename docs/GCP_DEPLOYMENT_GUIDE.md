# GCP Deployment Guide - AI50 Pipeline

## Prerequisites

1. **GCP Project**: `gen-lang-client-0653324487`
2. **gcloud CLI**: Installed and authenticated
3. **OpenAI API Key**: Ready to upload to Secret Manager
4. **Python Dependencies**: Listed in `requirements.txt`

## Deployment Steps

### Step 1: Initial Setup (One-time)

```bash
# 1. Authenticate with GCP
gcloud auth login
gcloud config set project gen-lang-client-0653324487

# 2. Make deployment scripts executable
chmod +x gcp/*.sh

# 3. Set up GCP infrastructure (buckets, secrets)
./gcp/setup_gcp.sh
```

**What this does:**
- Creates 3 GCS buckets:
  - `gen-lang-client-0653324487-raw-data` (scraped HTML/text)
  - `gen-lang-client-0653324487-structured-data` (extracted JSON)
  - `gen-lang-client-0653324487-dashboards` (generated dashboards)
- Creates Secret Manager secret for OpenAI API key
- Enables required GCP APIs

**Estimated Time**: 5 minutes

---

### Step 2: Upload Seed Data

```bash
# Upload Forbes seed data to GCS
gsutil cp data/forbes_ai50_seed.json gs://gen-lang-client-0653324487-raw-data/
```

---

### Step 3: Build and Deploy Containers

```bash
# Build and deploy Docker images to Cloud Run
./gcp/build_and_deploy.sh
```

**What this does:**
- Builds scraper Docker image (Playwright-based)
- Builds extractor Docker image (5-pass with instructor/pydantic)
- Pushes images to Google Container Registry
- Creates Cloud Run Jobs:
  - `ai50-scraper` (2GB RAM, 2 CPUs, 1-hour timeout)
  - `ai50-extractor` (4GB RAM, 2 CPUs, 30-min timeout)

**Estimated Time**: 10-15 minutes

---

### Step 4: Set up Cloud Composer (Airflow)

```bash
# Create and configure Airflow environment
./gcp/setup_composer.sh
```

**What this does:**
- Creates Cloud Composer environment (`ai50-composer`)
- Installs Python dependencies (instructor, pydantic, playwright, etc.)
- Sets up Airflow variables
- Uploads one DAG:
  - `ai50_daily_refresh` – Manually triggered DAG that runs scraping **and** extraction for all 50 companies in sequence

**Estimated Time**: 25-30 minutes (Composer creation is slow)

---

### Step 5: Test the Pipeline

#### Option A: Test Individual Jobs

```bash
# Test scraper for one company
gcloud run jobs execute ai50-scraper \
  --region=us-central1 \
  --env-vars="COMPANY_ID=6bd457d9-54f4-40e1-9d65-7b43d30c1644,GCP_PROJECT_ID=gen-lang-client-0653324487"

# Test extractor for one company
gcloud run jobs execute ai50-extractor \
  --region=us-central1 \
  --env-vars="COMPANY_ID=6bd457d9-54f4-40e1-9d65-7b43d30c1644,GCP_PROJECT_ID=gen-lang-client-0653324487"
```

#### Option B: Test Airflow DAG

1. Go to Airflow UI (get URL from setup_composer.sh output)
2. Enable `ai50_daily_refresh`
3. Trigger manually (runs scraper first, then extractor)
4. Monitor the two-task workflow until both turn green

---

## Architecture Overview

```
┌───────────────────────────────────────────────────────────────┐
│                     AIRFLOW (Cloud Composer)                   │
│                                                               │
│                ┌─────────────────────────────┐                │
│                │ ai50_daily_refresh (manual) │                │
│                │ scrape → extract → done     │                │
│                └─────────────────────────────┘                │
│                              │                                │
└──────────────────────────────┼────────────────────────────────┘
                               │
                               ▼
                  ┌────────────────────────┐
                  │ Cloud Run Job: Scraper │
                  └────────────────────────┘
                               │
                               ▼
                  ┌──────────────────────────┐
                  │ Cloud Run Job: Extractor │
                  └──────────────────────────┘
                               │
                        ┌─────────────┐
                        │ GCS Buckets │
                        │             │
                        │ raw-data/   │
                        │ structured/ │
                        │ dashboards/ │
                        └─────────────┘
```

---

## Pipeline Flow

### 1. Initial Scraping (Manual Trigger)
```
Airflow DAG → Trigger 50 Cloud Run Jobs → Scrape websites → Save to raw-data bucket
```

### 2. Extraction (Auto-triggered after scraping)
```
Airflow DAG → Trigger 50 Cloud Run Jobs → 5-pass extraction → Save to structured-data bucket
```

### 3. Daily Updates (Scheduled)
```
Airflow DAG (2 AM UTC daily) → Check for updates → Scrape + Extract → Update buckets
```

---

## Data Models

### 5-Pass Extraction Strategy

**Pass 1**: Company Basics + Events
- Legal name, website, HQ, founded year
- Funding events, partnerships, product launches

**Pass 2**: Products + Leadership
- Product names, descriptions, pricing models
- Founders, executives, roles

**Pass 3**: GitHub Metrics
- Stars, forks, contributors (when available)

**Pass 4**: Business Intelligence
- Value proposition, industry, competitors
- Revenue model, sales motion, GTM channels
- Tech partnerships, geographic markets

**Pass 5**: Employee & Hiring Data
- Job openings (16% coverage)
- Office locations (14% coverage)
- Hiring focus/departments

---

## Monitoring

### Cloud Run Jobs
```bash
# List job executions
gcloud run jobs executions list --job=ai50-scraper --region=us-central1

# View logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=ai50-scraper" --limit=50
```

### Airflow
- Access Airflow UI for DAG monitoring
- Check task logs for detailed execution info

### GCS Buckets
```bash
# Check raw data
gsutil ls gs://gen-lang-client-0653324487-raw-data/

# Check structured data
gsutil ls gs://gen-lang-client-0653324487-structured-data/

# Download a file
gsutil cp gs://gen-lang-client-0653324487-structured-data/6bd457d9-54f4-40e1-9d65-7b43d30c1644.json .
```

---

## Cost Estimation

### Daily Costs (50 companies)

**Cloud Run**:
- Scraper: 50 jobs × 60s × $0.00002400/vCPU-second = $0.07
- Extractor: 50 jobs × 20s × $0.00002400/vCPU-second = $0.02
- **Total**: ~$0.10/day

**Cloud Storage**:
- Raw data: ~500MB × $0.020/GB/month = $0.01/month
- Structured data: ~50MB × $0.020/GB/month = $0.001/month
- **Total**: ~$0.01/month

**Cloud Composer** (Airflow):
- Small environment: ~$150/month (fixed cost)

**OpenAI API**:
- Extraction: 50 companies × $0.05 = $2.50/day
- Daily updates: ~$0.50/day (incremental)

**Total Estimated Cost**: ~$150/month + $3/day = ~$240/month

---

## Troubleshooting

### Issue: Scraper fails
```bash
# Check logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=ai50-scraper" --limit=50

# Common fixes:
# 1. Playwright browser not installed
# 2. Website blocking (rate limiting)
# 3. Timeout (increase in Dockerfile)
```

### Issue: Extractor fails
```bash
# Check if OpenAI API key is set
gcloud secrets versions access latest --secret=openai-api-key

# Check logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=ai50-extractor" --limit=50

# Common fixes:
# 1. OpenAI API key not accessible
# 2. Token limit exceeded (adjust smart filtering)
# 3. Pydantic validation error (check models.py)
```

### Issue: Composer creation fails
```bash
# Check quota
gcloud compute project-info describe --project=gen-lang-client-0653324487

# Enable additional APIs if needed
gcloud services enable composer.googleapis.com
```

---

## Cleanup (if needed)

```bash
# Delete Cloud Run jobs
gcloud run jobs delete ai50-scraper --region=us-central1
gcloud run jobs delete ai50-extractor --region=us-central1

# Delete Composer environment
gcloud composer environments delete ai50-composer --location=us-central1

# Delete GCS buckets
gsutil -m rm -r gs://gen-lang-client-0653324487-raw-data
gsutil -m rm -r gs://gen-lang-client-0653324487-structured-data
gsutil -m rm -r gs://gen-lang-client-0653324487-dashboards

# Delete secret
gcloud secrets delete openai-api-key
```

---

## Next Steps After Deployment

1. ✅ Test pipeline with 1-2 companies
2. ✅ Run initial scraping for all 50 companies
3. ✅ Verify structured data quality
4. ✅ Set up daily update schedule
5. ⏭️ Build dashboard generator (if needed)
6. ⏭️ Deploy dashboard hosting

---

## Support

For issues or questions:
- Check GCP Console logs
- Review Airflow task logs
- Check this guide's troubleshooting section

