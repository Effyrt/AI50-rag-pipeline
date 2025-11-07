"""AI50 manual pipeline DAG.

Hybrid DAG that runs the scraper in Cloud Run Jobs (for web scraping)
and the extractor in Cloud Functions (for API calls to OpenAI).
Each component processes all Forbes AI 50 companies.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.google.cloud.operators.cloud_run import (
    CloudRunExecuteJobOperator,
)
from airflow.providers.google.cloud.operators.functions import (
    CloudFunctionInvokeFunctionOperator,
)

GCP_PROJECT_ID = "gen-lang-client-0653324487"
GCP_REGION = "us-central1"
SCRAPER_JOB_NAME = "ai50-scraper"
EXTRACTOR_JOB_NAME = "ai50-extractor"

DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="ai50_structured_dag",
    default_args=DEFAULT_ARGS,
    description="Manually trigger to run scraping + extraction for all 50 companies",
    start_date=datetime(2025, 11, 7),
    schedule_interval=None,
    catchup=False,
    tags=["ai50", "manual", "scrape", "extract"],
) as dag:

    scrape_all = CloudRunExecuteJobOperator(
        task_id="scrape_all_companies",
        project_id=GCP_PROJECT_ID,
        region=GCP_REGION,
        job_name=SCRAPER_JOB_NAME,
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

    extract_all = CloudRunExecuteJobOperator(
        task_id="extract_all_companies",
        project_id=GCP_PROJECT_ID,
        region=GCP_REGION,
        job_name=EXTRACTOR_JOB_NAME,
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

    scrape_all >> extract_all
