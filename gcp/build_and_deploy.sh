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

# ==================================================================================
# Cloud Run SERVICES: FastAPI backend + Streamlit frontend (Lab 10)
#
# Deployed with --min-instances=0 so both scale to zero when idle. Cloud Run's
# always-free allowance (2M requests, 180k vCPU-s and 360k GiB-s per month) covers a
# demo app comfortably, so these two public URLs cost effectively nothing.
#
# Order matters: the API is deployed first so its URL can be injected into the UI as
# API_BASE.
# ==================================================================================

echo ""
echo "Building service images..."

gcloud builds submit \
  --config=gcp/cloudbuild.api.yaml \
  --project=$PROJECT_ID \
  . || { echo "FATAL: API image build failed" >&2; exit 1; }

gcloud builds submit \
  --config=gcp/cloudbuild.ui.yaml \
  --project=$PROJECT_ID \
  . || { echo "FATAL: UI image build failed" >&2; exit 1; }

echo ""
echo "Deploying Cloud Run services..."

# --allow-unauthenticated makes the dashboards publicly reachable, which is required
# for a demo link. Note this exposes the API too; if that is not wanted, drop the flag
# and use `gcloud run services proxy` for the demo instead.
gcloud run deploy ai50-api \
  --image=gcr.io/$PROJECT_ID/ai50-api:latest \
  --region=$REGION \
  --project=$PROJECT_ID \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=3 \
  --memory=2Gi \
  --cpu=1 \
  --timeout=300 \
  --port=8000 \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCS_BUCKET_NAME=${PROJECT_ID}-structured-data,RAG_LLM_MODEL=gpt-4o-mini" \
  --set-secrets=OPENAI_API_KEY=openai-api-key:latest \
  || { echo "FATAL: failed to deploy ai50-api" >&2; exit 1; }

API_URL=$(gcloud run services describe ai50-api \
  --region=$REGION --project=$PROJECT_ID --format="get(status.url)")

if [ -z "$API_URL" ]; then
  echo "FATAL: could not resolve the ai50-api URL" >&2
  exit 1
fi
echo "  → API deployed at $API_URL"

# --session-affinity keeps a browser pinned to one instance, which Streamlit's
# WebSocket connection needs to stay stable across Cloud Run instances.
gcloud run deploy ai50-ui \
  --image=gcr.io/$PROJECT_ID/ai50-ui:latest \
  --region=$REGION \
  --project=$PROJECT_ID \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=3 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300 \
  --port=8501 \
  --session-affinity \
  --set-env-vars="API_BASE=${API_URL}" \
  || { echo "FATAL: failed to deploy ai50-ui" >&2; exit 1; }

UI_URL=$(gcloud run services describe ai50-ui \
  --region=$REGION --project=$PROJECT_ID --format="get(status.url)")
echo "  → UI deployed at $UI_URL"

echo ""
echo "Verifying the API responds..."
if curl -fsS --max-time 60 "${API_URL}/" >/dev/null; then
  echo "  ✓ ${API_URL}/ is healthy"
  echo "  data source: $(curl -fsS "${API_URL}/" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("data_source","unknown"))' 2>/dev/null || echo unknown)"
else
  echo "  ✗ ${API_URL}/ did not respond; check: gcloud run services logs read ai50-api --region=$REGION"
fi

echo ""
echo "=================================================="
echo "✅ Build and Deploy Complete!"
echo "=================================================="
echo ""
echo "Cloud Run jobs (batch pipeline):"
echo "  🌐 ai50-scraper"
echo "  📊 ai50-extractor"
echo ""
echo "Cloud Run services (Lab 10 — scale to zero, within the free tier):"
echo "  🔌 ai50-api  $API_URL"
echo "  📈 ai50-ui   $UI_URL"
echo ""
echo "Record both URLs in README.md."
echo ""
echo "Next steps:"
echo "  • Schedule the pipeline:  ./gcp/setup_scheduler.sh   (Cloud Scheduler, 3 free jobs)"
echo "  • Or managed Airflow:     ./gcp/setup_composer.sh    (no free tier — see docs/ROADMAP.md)"
echo "=================================================="

