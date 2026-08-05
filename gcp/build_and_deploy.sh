#!/bin/bash

# Build and deploy Docker images to GCP

set -e

PROJECT_ID="gen-lang-client-0653324487"
REGION="us-central1"

echo "=================================================="
echo "Building and Deploying AI50 Pipeline to GCP"
echo "=================================================="

# Build and push scraper image
echo "Building scraper image..."
gcloud builds submit \
  --config=gcp/cloudbuild.scraper.yaml \
  --project=$PROJECT_ID \
  .

# Build and push extractor image
echo "Building extractor image..."
gcloud builds submit \
  --config=gcp/cloudbuild.extractor.yaml \
  --project=$PROJECT_ID \
  .

# Deploy Cloud Run jobs
echo "Deploying Cloud Run jobs..."

# Create the job if it does not exist, otherwise update it. Previously both a create
# and an update were issued unconditionally, with `|| echo "already exists"` on the
# create - which reported genuine failures (invalid flags, quota, permissions) as
# success. Every gcloud call below is fatal on error.
deploy_job() {
  local job_name="$1"; shift
  if gcloud run jobs describe "$job_name" --region="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "  → updating existing job $job_name"
    gcloud run jobs update "$job_name" --region="$REGION" --project="$PROJECT_ID" "$@" \
      || { echo "FATAL: failed to update job $job_name" >&2; exit 1; }
  else
    echo "  → creating job $job_name"
    gcloud run jobs create "$job_name" --region="$REGION" --project="$PROJECT_ID" "$@" \
      || { echo "FATAL: failed to create job $job_name" >&2; exit 1; }
  fi
}

# Scraper job. One task per company, 10 running concurrently.
deploy_job ai50-scraper \
  --image=gcr.io/$PROJECT_ID/ai50-scraper:latest \
  --memory=2Gi \
  --cpu=2 \
  --task-timeout=7200 \
  --parallelism=10 \
  --task-count=50 \
  --max-retries=1

# Extractor job.
# NOTE: `--task-timeout` is the correct flag for Cloud Run *Jobs*; the previous
# `--timeout` is a Cloud Run *services* flag and was silently rejected. This job runs
# as a single task covering all 50 companies x 5 extraction passes, so the timeout is
# set to 2h rather than the original 30m.
deploy_job ai50-extractor \
  --image=gcr.io/$PROJECT_ID/ai50-extractor:latest \
  --memory=4Gi \
  --cpu=2 \
  --task-timeout=7200 \
  --max-retries=2 \
  --set-secrets=OPENAI_API_KEY=openai-api-key:latest

echo ""
echo "=================================================="
echo "✅ Build and Deploy Complete!"
echo "=================================================="
echo ""
echo "Created Cloud Run jobs:"
echo "  🌐 ai50-scraper"
echo "  📊 ai50-extractor"
echo ""
echo "Next steps:"
echo "  1. Set up Cloud Composer environment"
echo "  2. Deploy Airflow DAGs"
echo ""
echo "Run: ./gcp/setup_composer.sh"
echo "=================================================="

