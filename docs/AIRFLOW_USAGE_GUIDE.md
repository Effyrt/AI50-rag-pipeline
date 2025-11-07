# Airflow Usage Guide - AI50 Pipeline

## Quick Access

**Airflow UI**: https://7945412f28754a46b762144896412ac1-dot-us-central1.composer.googleusercontent.com

**Login**: Use your Google account (rayuduhemanth6@gmail.com)

---

## The Only DAG You Need

### `ai50_daily_refresh`
- **What it does**: Runs scraping **and** extraction for **all 50 companies** in one shot.
- **How it works**:
  1. Executes the `ai50-scraper` Cloud Run Job
     - Scrapes 10 page types per company (homepage, about, product, careers, blog, pricing, customers, partners, press, team)
     - Saves HTML and cleaned text files to GCS raw-data bucket
  2. Executes the `ai50-extractor` Cloud Run Job
     - Loads scraped data
     - Runs the 5-pass extraction (Company, Events, Products, Leadership, BI, Employees)
     - Saves structured JSON to GCS structured-data bucket
- **Schedule**: `schedule_interval=None` (manual trigger only)
- **Typical runtime**: ~35-45 minutes end-to-end (depends on site speed and OpenAI latency)

```
Trigger DAG → Cloud Run scraper → Raw data in GCS → Cloud Run extractor → Structured JSON in GCS
```

---

## How to Run the DAG Manually (Daily)

1. **Open the Airflow UI**
   - Go to https://7945412f28754a46b762144896412ac1-dot-us-central1.composer.googleusercontent.com
   - Sign in with your Google account

2. **Enable the DAG (if disabled)**
   - Find `ai50_daily_refresh` in the DAG list
   - Click the toggle switch on the left so it turns **ON**

3. **Trigger the DAG**
   - Click the **▶️ (play)** button in the "Actions" column
   - Choose "Trigger DAG"
   - Click "Trigger" in the popup (no config changes needed)

4. **Monitor the run**
   - Click on the DAG name to open the details page
   - Graph view will show two tasks:
     - `scrape_all_companies`
     - `extract_all_companies`
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
- `company`: Legal name, HQ, funding, BI fields (value prop, competitors, etc.)
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

- **You only need one DAG**: `ai50_daily_refresh`
- **Trigger manually whenever you want fresh data**
- **No schedule** (runs only when you click)
- **Output** stored automatically in the two GCS buckets

That’s it! 🚀

