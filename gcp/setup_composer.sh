#!/bin/bash

# Setup Cloud Composer (Managed Airflow) environment

set -e

PROJECT_ID="gen-lang-client-0653324487"
REGION="us-central1"
COMPOSER_ENV="ai50-composer"

echo "=================================================="
echo "Setting up Cloud Composer Environment"
echo "=================================================="

# Create Composer environment (this takes ~20-30 minutes)
echo "Creating Cloud Composer environment..."
echo "⏳ This will take 20-30 minutes..."

# NOTE: --python-version and --web-server-machine-type are Cloud Composer *1* flags and
# are rejected by a Composer 2 image version. They were previously masked by
# `|| echo "already exists"`, so a failed create looked like a successful one. Composer 2
# derives the Python version from --image-version, and web server sizing uses
# --web-server-cpu / --web-server-memory / --web-server-storage.
if gcloud composer environments describe $COMPOSER_ENV \
     --location=$REGION --project=$PROJECT_ID >/dev/null 2>&1; then
  echo "Composer environment $COMPOSER_ENV already exists, skipping create"
else
  gcloud composer environments create $COMPOSER_ENV \
    --location=$REGION \
    --image-version=composer-2.9.0-airflow-2.9.3 \
    --project=$PROJECT_ID \
    --environment-size=small \
    --scheduler-cpu=2 \
    --scheduler-memory=4 \
    --scheduler-storage=5 \
    --scheduler-count=1 \
    --web-server-cpu=1 \
    --web-server-memory=2 \
    --web-server-storage=1 \
    || { echo "FATAL: failed to create Composer environment" >&2; exit 1; }
fi

echo ""
echo "Installing Python packages..."
gcloud composer environments update $COMPOSER_ENV \
  --location=$REGION \
  --update-pypi-packages-from-file=requirements.txt \
  --project=$PROJECT_ID

echo ""
echo "Setting Airflow variables..."
gcloud composer environments run $COMPOSER_ENV \
  --location=$REGION \
  variables set -- gcp_project_id $PROJECT_ID \
  --project=$PROJECT_ID

echo ""
echo "Deploying Airflow DAGs..."
BUCKET=$(gcloud composer environments describe $COMPOSER_ENV \
  --location=$REGION \
  --project=$PROJECT_ID \
  --format="get(config.dagGcsPrefix)")

gsutil -m cp airflow/dags/*.py $BUCKET/

echo ""
echo "=================================================="
echo "✅ Cloud Composer Setup Complete!"
echo "=================================================="
echo ""
echo "Airflow UI:"
gcloud composer environments describe $COMPOSER_ENV \
  --location=$REGION \
  --project=$PROJECT_ID \
  --format="get(config.airflowUri)"
echo ""
echo "DAGs deployed:"
echo "  • ai50_daily_refresh - Manual scrape + extract pipeline for all 50 companies"
echo ""
echo "=================================================="

