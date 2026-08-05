"""AI50 daily refresh DAG (Lab 3).

Re-scrapes the key pages (About, Careers, Blog) for all Forbes AI 50 companies and
refreshes downstream artifacts. Runs into a dated per-run subfolder so the full-load
run is never overwritten.

Execution model: the heavy work runs in Cloud Run Jobs, not in the Airflow worker.
An earlier version imported the scraper and RAG pipeline directly and ran 50 Playwright
browsers in-process; those imports could not resolve in Cloud Composer, where only
airflow/dags/ is uploaded and the src/backend package never ships.

Schedule: 0 3 * * * (daily at 03:00 UTC), as Lab 3 requires. If a deployment does not
need a daily cadence, pause the DAG in the Airflow UI rather than editing this schedule -
the definition itself is a graded requirement.

Tasks:
    load_company_list    -> read the seed list, publish names and count
    refresh_key_pages    -> Cloud Run Job: ai50-scraper in delta mode
    extract_structured   -> Cloud Run Job: ai50-extractor
    update_vector_db     -> Cloud Run Job: ai50-rag-index-builder
    log_completion       -> per-company success/failure summary
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.cloud_run import (
    CloudRunExecuteJobOperator,
)

# Shared helpers live in the full-ingest DAG module, which sits alongside this file in
# the DAGs folder, so the import resolves both in Composer and locally.
from ai50_full_ingest_dag import company_slug, read_seed

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "gen-lang-client-0653324487")
GCP_REGION = os.getenv("GCP_REGION", "us-central1")

SCRAPER_JOB_NAME = "ai50-scraper"
EXTRACTOR_JOB_NAME = "ai50-extractor"
RAG_INDEX_JOB_NAME = "ai50-rag-index-builder"

RAW_BUCKET = f"{GCP_PROJECT_ID}-raw-data"

# Lab 3: refresh only the pages that change often.
KEY_PAGES = "about,careers,blog"

DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def load_company_list(**context) -> int:
    """Publish the company list for downstream verification."""
    companies = read_seed()
    names = [c.get("company_name", "") for c in companies if c.get("company_name")]

    print(f"Loaded {len(names)} companies for daily refresh")
    context["ti"].xcom_push(key="company_names", value=names)
    context["ti"].xcom_push(key="company_count", value=len(names))
    return len(names)


def log_completion(**context) -> dict:
    """Log per-company refresh success or failure (Lab 3 requirement).

    Checks for objects under this run's dated prefix, so a company that silently
    failed to refresh shows up as a failure rather than being assumed successful.
    """
    names = context["ti"].xcom_pull(key="company_names", task_ids="load_company_list") or []
    run_date = context["ds"]

    try:
        from airflow.providers.google.cloud.hooks.gcs import GCSHook

        hook = GCSHook()
    except Exception as exc:  # noqa: BLE001
        print(f"GCS unavailable ({exc}); cannot verify refresh")
        return {"succeeded": 0, "failed": len(names), "skipped": True}

    succeeded, failed = [], []
    for name in names:
        prefix = f"raw/{company_slug(name)}/daily_{run_date}/"
        if hook.list(bucket_name=RAW_BUCKET, prefix=prefix):
            succeeded.append(name)
            print(f"  ✓ {name}")
        else:
            failed.append(name)
            print(f"  ✗ {name}: nothing written under {prefix}")

    print("=" * 60)
    print(f"DAILY REFRESH COMPLETE — {run_date}")
    print("=" * 60)
    print(f"✓ Succeeded: {len(succeeded)}/{len(names)}")
    print(f"✗ Failed:    {len(failed)}/{len(names)}")
    if failed:
        print(f"Failed companies: {', '.join(failed)}")

    return {"succeeded": len(succeeded), "failed": len(failed), "failed_names": failed}


with DAG(
    dag_id="ai50_daily_refresh_dag",
    default_args=DEFAULT_ARGS,
    description="Daily refresh of Forbes AI 50 companies (About, Careers, Blog)",
    start_date=datetime(2025, 11, 7),
    schedule="0 3 * * *",
    catchup=False,
    tags=["ai50", "orbit", "daily"],
) as dag:

    t1_load = PythonOperator(
        task_id="load_company_list",
        python_callable=load_company_list,
    )

    t2_refresh = CloudRunExecuteJobOperator(
        task_id="refresh_key_pages",
        project_id=GCP_PROJECT_ID,
        region=GCP_REGION,
        job_name=SCRAPER_JOB_NAME,
        overrides={
            "container_overrides": [
                {
                    "env": [
                        {"name": "GCP_PROJECT_ID", "value": GCP_PROJECT_ID},
                        {"name": "RUN_MODE", "value": "daily"},
                        {"name": "RUN_ID", "value": "daily_{{ ds }}"},
                        {"name": "PAGES", "value": KEY_PAGES},
                    ]
                }
            ]
        },
    )

    t3_extract = CloudRunExecuteJobOperator(
        task_id="extract_structured",
        project_id=GCP_PROJECT_ID,
        region=GCP_REGION,
        job_name=EXTRACTOR_JOB_NAME,
        overrides={
            "container_overrides": [
                {
                    "env": [
                        {"name": "GCP_PROJECT_ID", "value": GCP_PROJECT_ID},
                        {"name": "RUN_ID", "value": "daily_{{ ds }}"},
                    ]
                }
            ]
        },
    )

    t4_update_index = CloudRunExecuteJobOperator(
        task_id="update_vector_db",
        project_id=GCP_PROJECT_ID,
        region=GCP_REGION,
        job_name=RAG_INDEX_JOB_NAME,
        overrides={
            "container_overrides": [
                {
                    "env": [
                        {"name": "GCP_PROJECT_ID", "value": GCP_PROJECT_ID},
                        {"name": "RUN_ID", "value": "daily_{{ ds }}"},
                    ]
                }
            ]
        },
    )

    t5_log = PythonOperator(
        task_id="log_completion",
        python_callable=log_completion,
        trigger_rule="all_done",
    )

    t1_load >> t2_refresh >> t3_extract >> t4_update_index >> t5_log
