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

gcloud composer environments create $COMPOSER_ENV \
  --location=$REGION \
  --python-version=3.11 \
  --image-version=composer-2.9.0-airflow-2.9.3 \
  --project=$PROJECT_ID \
  --environment-size=small \
  --scheduler-cpu=2 \
  --scheduler-memory=4 \
  --scheduler-storage=5 \
  --scheduler-count=1 \
  --web-server-machine-type=composer-n1-webserver-2 \
  || echo "Composer environment already exists"

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

