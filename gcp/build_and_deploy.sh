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

# Scraper job with parallelism and increased resources
gcloud run jobs create ai50-scraper \
  --image=gcr.io/$PROJECT_ID/ai50-scraper:latest \
  --region=$REGION \
  --memory=4Gi \
  --cpu=4 \
  --task-timeout=7200 \
  --parallelism=10 \
  --task-count=50 \
  --max-retries=1 \
  --project=$PROJECT_ID \
  || echo "Job ai50-scraper already exists, updating..."

gcloud run jobs update ai50-scraper \
  --image=gcr.io/$PROJECT_ID/ai50-scraper:latest \
  --region=$REGION \
  --memory=4Gi \
  --cpu=4 \
  --task-timeout=7200 \
  --parallelism=10 \
  --task-count=50 \
  --project=$PROJECT_ID

# Extractor job
gcloud run jobs create ai50-extractor \
  --image=gcr.io/$PROJECT_ID/ai50-extractor:latest \
  --region=$REGION \
  --memory=4Gi \
  --cpu=2 \
  --timeout=1800 \
  --max-retries=2 \
  --set-secrets=OPENAI_API_KEY=openai-api-key:latest \
  --project=$PROJECT_ID \
  || echo "Job ai50-extractor already exists, updating..."

gcloud run jobs update ai50-extractor \
  --image=gcr.io/$PROJECT_ID/ai50-extractor:latest \
  --region=$REGION \
  --set-secrets=OPENAI_API_KEY=openai-api-key:latest \
  --project=$PROJECT_ID

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

