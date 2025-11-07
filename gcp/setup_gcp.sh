#!/bin/bash

# GCP Setup Script for AI50 RAG Pipeline
# This script sets up all necessary GCP resources

set -e

# Configuration
PROJECT_ID="gen-lang-client-0653324487"
REGION="us-central1"
ZONE="us-central1-a"

# Bucket names
RAW_BUCKET="${PROJECT_ID}-raw-data"
STRUCTURED_BUCKET="${PROJECT_ID}-structured-data"
DASHBOARD_BUCKET="${PROJECT_ID}-dashboards"

# Service names
SCRAPER_SERVICE="ai50-scraper"
EXTRACTOR_SERVICE="ai50-extractor"
DASHBOARD_SERVICE="ai50-dashboard-generator"

# Composer (Airflow) environment
COMPOSER_ENV="ai50-composer"

echo "=================================================="
echo "Setting up GCP Infrastructure for AI50 Pipeline"
echo "=================================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Set project
echo "Setting GCP project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "Enabling required GCP APIs..."
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  storage.googleapis.com \
  composer.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com

# Create GCS buckets
echo "Creating GCS buckets..."

# Raw data bucket (for scraped HTML/text)
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION -b on gs://$RAW_BUCKET/ 2>/dev/null || echo "Bucket $RAW_BUCKET already exists"
gsutil lifecycle set - gs://$RAW_BUCKET/ <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF

# Structured data bucket (for extracted JSON)
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION -b on gs://$STRUCTURED_BUCKET/ 2>/dev/null || echo "Bucket $STRUCTURED_BUCKET already exists"

# Dashboard bucket (for generated dashboards)
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION -b on gs://$DASHBOARD_BUCKET/ 2>/dev/null || echo "Bucket $DASHBOARD_BUCKET already exists"
gsutil web set -m index.html -e 404.html gs://$DASHBOARD_BUCKET/
gsutil iam ch allUsers:objectViewer gs://$DASHBOARD_BUCKET/

# Create Secret Manager secret for OpenAI API key
echo "Setting up Secret Manager..."
if ! gcloud secrets describe openai-api-key --project=$PROJECT_ID > /dev/null 2>&1; then
  echo "Creating OpenAI API key secret..."
  echo "Please enter your OpenAI API key:"
  read -s OPENAI_KEY
  echo -n "$OPENAI_KEY" | gcloud secrets create openai-api-key \
    --data-file=- \
    --replication-policy="automatic" \
    --project=$PROJECT_ID
else
  echo "OpenAI API key secret already exists"
fi

# Grant Cloud Run access to secrets
echo "Granting access to secrets..."
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=$PROJECT_ID

echo ""
echo "=================================================="
echo "✅ GCP Infrastructure Setup Complete!"
echo "=================================================="
echo ""
echo "Created resources:"
echo "  📦 Raw data bucket: gs://$RAW_BUCKET"
echo "  📦 Structured data bucket: gs://$STRUCTURED_BUCKET"
echo "  📦 Dashboard bucket: gs://$DASHBOARD_BUCKET"
echo "  🔐 Secret: openai-api-key"
echo ""
echo "Next steps:"
echo "  1. Build and push Docker images"
echo "  2. Deploy Cloud Run jobs"
echo "  3. Set up Cloud Composer environment"
echo "  4. Deploy Airflow DAGs"
echo ""
echo "Run: ./gcp/build_and_deploy.sh"
echo "=================================================="

