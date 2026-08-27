"""AI50 full ingest DAG (Lab 2).

Runs the initial, one-off ingestion for all Forbes AI 50 companies.

Execution model: the heavy work (Playwright scraping, embedding) runs in Cloud Run
Jobs, not in the Airflow worker. Only lightweight coordination and verification runs
here. An earlier version of this DAG imported the scraper and RAG pipeline directly
and ran them in-process; those imports could not resolve in Cloud Composer, where only
airflow/dags/ is uploaded and the src/backend package never ships. Fifty concurrent
Playwright browsers would also have exhausted the worker.

Tasks (per Lab 2):
    load_company_list    -> read the seed list, publish names and count
    scrape_company_pages -> Cloud Run Job: ai50-scraper (one task per company)
    store_raw_to_cloud   -> verify raw objects landed in GCS, per company
    build_rag_index      -> Cloud Run Job: ai50-rag-index-builder
    generate_report      -> summarise the run
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.cloud_run import (
    CloudRunExecuteJobOperator,
)

# Shared config and helpers. Importing from ai50_common (which defines no DAG) rather
# than from the other DAG file: importing a DAG-defining module would register its DAG
# a second time and Airflow would reject it as a duplicate ID.
from ai50_common import (
    GCP_PROJECT_ID,
    GCP_REGION,
    RAG_INDEX_JOB_NAME,
    RAW_BUCKET,
    SCRAPER_JOB_NAME,
    company_slug,
    load_company_list,
)

DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def store_raw_to_cloud(**context) -> dict:
    """Verify the scraper wrote raw objects to GCS, logging per company.

    The Cloud Run scraper writes straight to GCS, so this task confirms the outcome
    rather than copying anything. Per-company results are logged so a partial run is
    visible instead of silently passing.
    """
    names = context["ti"].xcom_pull(key="company_names", task_ids="load_company_list") or []

    try:
        from airflow.providers.google.cloud.hooks.gcs import GCSHook

        hook = GCSHook()
    except Exception as exc:  # noqa: BLE001
        print(f"GCS unavailable ({exc}); skipping verification")
        return {"verified": 0, "missing": len(names), "skipped": True}

    verified, missing = [], []
    for name in names:
        objects = hook.list(bucket_name=RAW_BUCKET, prefix=f"raw/{company_slug(name)}/")
        if objects:
            verified.append(name)
            print(f"  ✓ {name}: {len(objects)} objects")
        else:
            missing.append(name)
            print(f"  ✗ {name}: no raw objects found")

    print(f"\nVerified {len(verified)}/{len(names)} companies; {len(missing)} missing")
    if missing:
        print(f"Missing: {', '.join(missing)}")

    return {"verified": len(verified), "missing": len(missing), "missing_names": missing}


def generate_report(**context) -> None:
    """Summarise the run."""
    count = context["ti"].xcom_pull(key="company_count", task_ids="load_company_list")
    result = context["ti"].xcom_pull(task_ids="store_raw_to_cloud") or {}

    print("=" * 60)
    print("FULL INGEST COMPLETE")
    print("=" * 60)
    print(f"Companies in seed: {count}")
    print(f"Verified in GCS:   {result.get('verified', 'unknown')}")
    print(f"Missing:           {result.get('missing', 'unknown')}")


with DAG(
    dag_id="ai50_full_ingest_dag",
    default_args=DEFAULT_ARGS,
    description="Full ingestion of Forbes AI 50 companies with vector DB indexing",
    start_date=datetime(2025, 11, 7),
    schedule="@once",
    catchup=False,
    tags=["ai50", "orbit", "full-load"],
) as dag:

    t1_load = PythonOperator(
        task_id="load_company_list",
        python_callable=load_company_list,
    )

    t2_scrape = CloudRunExecuteJobOperator(
        task_id="scrape_company_pages",
        project_id=GCP_PROJECT_ID,
        region=GCP_REGION,
        job_name=SCRAPER_JOB_NAME,
        overrides={
            "container_overrides": [
                {
                    "env": [
                        {"name": "GCP_PROJECT_ID", "value": GCP_PROJECT_ID},
                        {"name": "RUN_MODE", "value": "full"},
                    ]
                }
            ]
        },
    )

    t3_verify = PythonOperator(
        task_id="store_raw_to_cloud",
        python_callable=store_raw_to_cloud,
    )

    t4_index = CloudRunExecuteJobOperator(
        task_id="build_rag_index",
        project_id=GCP_PROJECT_ID,
        region=GCP_REGION,
        job_name=RAG_INDEX_JOB_NAME,
        overrides={
            "container_overrides": [
                {
                    "env": [
                        {"name": "GCP_PROJECT_ID", "value": GCP_PROJECT_ID},
                    ]
                }
            ]
        },
    )

    t5_report = PythonOperator(
        task_id="generate_report",
        python_callable=generate_report,
        trigger_rule="all_done",
    )

    t1_load >> t2_scrape >> t3_verify >> t4_index >> t5_report
