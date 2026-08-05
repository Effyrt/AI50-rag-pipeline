# Airflow Usage Guide - AI50 Pipeline

## Quick Access

**Cloud Composer**: obtain the current UI URL from the environment rather than a
hard-coded link, which goes stale as soon as the environment is recreated:

```bash
gcloud composer environments describe ai50-composer \
  --location=us-central1 \
  --format="get(config.airflowUri)"
```

**Local Airflow** (no Composer environment required):

```bash
docker compose -f docker/docker-compose.airflow.yml up -d
# UI: http://localhost:8080  (admin / admin)
```

---

## Execution model

All heavy work runs in **Cloud Run Jobs**, not in the Airflow worker. Airflow only
coordinates and verifies. This matters: the DAGs previously ran Playwright and
sentence-transformers in-process, which both risked exhausting the worker and depended
on `src/backend` modules that are never uploaded to the Composer DAGs bucket.

Only `airflow/dags/` is uploaded to Composer, so a DAG that imports from `src/backend`
will fail at parse time. `tests/test_dags.py` enforces this.

---

## The DAGs

### `ai50_full_ingest_dag` — initial full load (Lab 2)
- **Schedule**: `@once`
- **Tasks**: `load_company_list` → `scrape_company_pages` → `store_raw_to_cloud`
  → `build_rag_index` → `generate_report`
- Scrapes 10 page types per company (homepage, about, product, careers, blog, pricing,
  customers, partners, press, team) into the GCS raw-data bucket, then builds the vector
  index. `store_raw_to_cloud` verifies per company and logs anything missing.

### `ai50_daily_refresh_dag` — daily delta refresh (Lab 3)
- **Schedule**: `0 3 * * *` (03:00 UTC daily)
- **Tasks**: `load_company_list` → `refresh_key_pages` → `extract_structured`
  → `update_vector_db` → `log_completion`
- Re-scrapes only the pages that change often (About, Careers, Blog) into a dated
  per-run subfolder, so the full-load run is never overwritten. `log_completion`
  records per-company success or failure.
- To stop it running daily in a deployed environment, **pause the DAG in the UI** — do
  not edit the schedule, which is a graded requirement.

### `ai50_structured_dag` — manual scrape + extract
- **Schedule**: `None` (manual trigger only)
- Convenience DAG for running scraping and extraction on demand.

```
Trigger DAG → Cloud Run scraper → Raw data in GCS → Cloud Run extractor → Structured JSON in GCS
```

**Typical runtime**: ~35-45 minutes end-to-end, depending on site speed and OpenAI latency.

---

## Verifying the DAGs parse

The check that matters before any deployment:

```bash
docker compose -f docker/docker-compose.airflow.yml exec airflow \
  airflow dags list-import-errors     # must be empty
```

---

## How to Run a DAG Manually

1. **Open the Airflow UI**
   - Composer: use the `airflowUri` from the command at the top of this guide
   - Local: http://localhost:8080

2. **Enable the DAG (if disabled)**
   - Find `ai50_daily_refresh_dag` in the DAG list
   - Click the toggle switch on the left so it turns **ON**

3. **Trigger the DAG**
   - Click the **▶️ (play)** button in the "Actions" column
   - Choose "Trigger DAG"
   - Click "Trigger" in the popup (no config changes needed)

4. **Monitor the run**
   - Click on the DAG name to open the details page
   - Graph view shows the task chain for the DAG you triggered
     (see "The DAGs" above for the task names)
   - Colors:
     - 🟡 Yellow = running
     - ✅ Green = success
     - ❌ Red = failed

5. **Check logs (optional)**
   - Click on a task box → click "Log" to stream real-time logs
   - Useful for monitoring scraping progress (per-company logs are echoed)

6. **Confirm completion**
   - Both tasks should turn green when done
   - Total runtime: ~35-45 minutes

7. **Repeat daily as needed**
   - Since the DAG is manual, just trigger it each day when you want fresh data

---

## Where the Data Goes

### Scraped Raw Data (HTML + Text)
```
Bucket: gs://gen-lang-client-0653324487-raw-data/
└── {company_id}/
    ├── metadata.json
    ├── homepage.html / homepage.txt
    ├── about.html / about.txt
    ├── product.html / product.txt
    ├── careers.html / careers.txt
    ├── blog.html / blog.txt
    ├── pricing.html / pricing.txt
    ├── customers.html / customers.txt
    ├── partners.html / partners.txt
    ├── press.html / press.txt
    └── team.html / team.txt
```

### Structured Data (LLM Output)
```
Bucket: gs://gen-lang-client-0653324487-structured-data/
└── {company_id}.json
```

Each JSON includes:
- `company_record`: Legal name, HQ, funding, BI fields (value prop, competitors, etc.)
  (the key is `company_record`, matching the `Payload` model in `src/backend/models.py`)
- `events`: Funding rounds, partnerships, launches
- `products`: Name, summary, pricing model, tier details when available
- `leadership`: Founders and executives with roles
- `snapshots`: Employee counts, job openings, office locations, hiring focus
- `visibility`: GitHub metrics and other visibility signals

---

## Command-Line Shortcuts (Optional)

List outputs:
```bash
gsutil ls gs://gen-lang-client-0653324487-raw-data/
gsutil ls gs://gen-lang-client-0653324487-structured-data/
```

Download one company's data:
```bash
gsutil cp -r gs://gen-lang-client-0653324487-raw-data/6bd457d9-54f4-40e1-9d65-7b43d30c1644/ ./databricks_raw/
gsutil cp gs://gen-lang-client-0653324487-structured-data/6bd457d9-54f4-40e1-9d65-7b43d30c1644.json ./databricks.json
```

Pretty-print JSON:
```bash
gsutil cat gs://gen-lang-client-0653324487-structured-data/6bd457d9-54f4-40e1-9d65-7b43d30c1644.json | jq .
```

---

## Monitoring & Troubleshooting

- **Scraper logs** show per-company status (✅ success, ❌ failures)
- **Extractor logs** show download counts and upload confirmations
- If a task fails:
  1. Click the red task
  2. Open the log to see the error
  3. Fix the issue (e.g., rerun if temporary network glitch)
  4. Click "Clear" on the failed task and re-trigger the DAG

Typical issues:
- Website temporarily unavailable → retry later
- OpenAI rate limit → wait a few minutes and re-trigger
- GCS permissions (if buckets were altered) → ensure service account still has access

---

## Recap

- **Two required DAGs**: `ai50_full_ingest_dag` (@once) and `ai50_daily_refresh_dag` (0 3 * * *)
- **`ai50_structured_dag`** is available for ad-hoc manual runs
- **Heavy work runs in Cloud Run Jobs**, never in the Airflow worker
- **Output** is written to the GCS raw-data and structured-data buckets

That’s it! 🚀

