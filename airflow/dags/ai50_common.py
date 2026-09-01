"""Shared configuration and helpers for the AI50 DAGs.

This module deliberately defines NO DAG object.

A DAG file must never import another DAG file: Airflow's DagBag collects every DAG
found in a module's globals, so importing a module that builds a DAG at import time
registers that DAG twice and Airflow rejects the second one with
AirflowDagDuplicatedIdException. Shared code therefore lives here, and both DAGs
import from this module instead of from each other.

`.airflowignore` excludes this file from DAG parsing. It remains importable, because
Airflow puts the DAGs folder on sys.path.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "gen-lang-client-0653324487")
GCP_REGION = os.getenv("GCP_REGION", "us-central1")

SCRAPER_JOB_NAME = "ai50-scraper"
EXTRACTOR_JOB_NAME = "ai50-extractor"
RAG_INDEX_JOB_NAME = "ai50-rag-index-builder"

RAW_BUCKET = f"{GCP_PROJECT_ID}-raw-data"
SEED_OBJECT = "forbes_ai50_seed.json"


def company_slug(name: str) -> str:
    """Filesystem/GCS-safe company identifier, matching the scraper's convention."""
    return name.lower().replace(" ", "_").replace(".", "").replace("&", "and")


def read_seed() -> list[dict]:
    """Read the Forbes AI 50 seed list.

    Prefers GCS (production), falling back to a file in the repo (local Airflow).
    Deliberately imports nothing from src/backend, which is not shipped to Composer.
    """
    try:
        from airflow.providers.google.cloud.hooks.gcs import GCSHook

        hook = GCSHook()
        if hook.exists(bucket_name=RAW_BUCKET, object_name=SEED_OBJECT):
            return json.loads(hook.download(bucket_name=RAW_BUCKET, object_name=SEED_OBJECT))
    except Exception as exc:  # noqa: BLE001 - local runs legitimately have no GCS
        print(f"GCS seed unavailable ({exc}); falling back to a local file")

    for candidate in (
        Path(__file__).resolve().parent / SEED_OBJECT,
        Path(__file__).resolve().parents[2] / "data" / SEED_OBJECT,
        Path("data") / SEED_OBJECT,
    ):
        if candidate.exists():
            print(f"Loaded seed from {candidate}")
            return json.loads(candidate.read_text())

    raise FileNotFoundError(
        f"Could not find {SEED_OBJECT} in gs://{RAW_BUCKET}/ or on local disk"
    )


def load_company_list(**context) -> int:
    """Publish the company list for downstream verification.

    Shared by both DAGs: each pushes the same two XCom keys.
    """
    companies = read_seed()
    names = [c.get("company_name", "") for c in companies if c.get("company_name")]

    print(f"Loaded {len(names)} companies from the seed list")
    context["ti"].xcom_push(key="company_names", value=names)
    context["ti"].xcom_push(key="company_count", value=len(names))
    return len(names)
