# GCP Deployment Guide

This directory contains scripts and configuration for deploying the RAG pipeline to Google Cloud Platform.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         GCP PROJECT                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐         ┌──────────────────┐             │
│  │  Cloud Storage  │         │  Secret Manager  │             │
│  │  (GCS Bucket)   │         │                  │             │
│  ├─────────────────┤         │ - openai-api-key │             │
│  │ • raw/          │         └──────────────────┘             │
│  │ • structured/   │                                           │
│  │ • vector_index/ │                                           │
│  │ • payloads/     │                                           │
│  └─────────────────┘                                           │
│         │                                                       │
│         │                                                       │
│  ┌──────▼──────────────────────────────────────┐              │
│  │        Cloud Run Job: rag-index-builder     │              │
│  ├─────────────────────────────────────────────┤              │
│  │  1. Download raw data from GCS              │              │
│  │  2. Chunk text (1000 chars, 200 overlap)    │              │
│  │  3. Generate embeddings (OpenAI)            │              │
│  │  4. Build FAISS index                       │              │
│  │  5. Upload index back to GCS                │              │
│  │                                              │              │
│  │  Resources: 2 vCPU, 4GB RAM                 │              │
│  │  Timeout: 30 minutes                        │              │
│  └──────────────────────────────────────────────┘              │
│                                                                 │
│  ┌─────────────────────────────────────────────┐              │
│  │  Future: Cloud Composer (Airflow)           │              │
│  │  - Full ingest DAG (Labs 2)                 │              │
│  │  - Daily refresh DAG (Labs 3)               │              │
│  └─────────────────────────────────────────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **GCP Account** with billing enabled
2. **gcloud CLI** installed: https://cloud.google.com/sdk/docs/install
3. **Project ID**: Create a new GCP project or use existing
4. **OpenAI API Key**: For embeddings

## Quick Start

### 1. Configure Project

Edit `deploy_rag_job.sh` and set your project ID:

```bash
PROJECT_ID="your-gcp-project-id"  # Change this!
REGION="us-central1"              # Or your preferred region
```

### 2. Authenticate with GCP

```bash
gcloud auth login
gcloud config set project your-gcp-project-id
```

### 3. Deploy

```bash
cd gcp
chmod +x deploy_rag_job.sh
./deploy_rag_job.sh
```

The script will guide you through **7 checkpoints**:
- ✅ Checkpoint 1: Verify GCP setup
- ✅ Checkpoint 2: Create GCS bucket
- ✅ Checkpoint 3: Upload raw data
- ✅ Checkpoint 4: Store API key in Secret Manager
- ✅ Checkpoint 5: Build Docker image
- ✅ Checkpoint 6: Create Cloud Run Job
- ✅ Checkpoint 7: Execute job

### 4. Monitor Execution

```bash
# View job status
gcloud run jobs describe rag-index-builder --region=us-central1

# Stream logs
gcloud run jobs executions list --job=rag-index-builder --region=us-central1
```

### 5. Download Results

```bash
# Download the built index
gsutil -m cp -r gs://ai50-pipeline-data/vector_index data/

# Verify files
ls -lh data/vector_index/
# Should see: faiss.index, chunks.pkl, metadata.pkl
```

## Cost Estimate

| Service | Usage | Cost |
|---------|-------|------|
| Cloud Storage | ~1GB storage | $0.02/month |
| Cloud Run | 1 execution (5-10 min) | $0.01 |
| OpenAI Embeddings | ~200K tokens | $0.004 |
| Secret Manager | 1 secret | Free |
| **Total** | | **~$0.03** per build |

## Manual Execution

If you want to run the job manually later:

```bash
# Execute job
gcloud run jobs execute rag-index-builder --region=us-central1 --wait

# Get execution details
EXECUTION_NAME=$(gcloud run jobs executions list \
    --job=rag-index-builder \
    --region=us-central1 \
    --limit=1 \
    --format="value(name)")

# View logs
gcloud logging read "resource.type=cloud_run_job \
    AND resource.labels.job_name=rag-index-builder \
    AND resource.labels.execution_name=$EXECUTION_NAME" \
    --limit=100 \
    --format=json
```

## Integration with Airflow (Labs 2 & 3)

Once Cloud Composer is set up, integrate this job into your DAGs:

```python
from airflow.providers.google.cloud.operators.cloud_run import CloudRunExecuteJobOperator

build_rag_index = CloudRunExecuteJobOperator(
    task_id='build_rag_index',
    project_id='your-project-id',
    region='us-central1',
    job_name='rag-index-builder',
    dag=dag,
)
```

## Troubleshooting

### Job fails with "Out of memory"
```bash
# Increase memory allocation
gcloud run jobs update rag-index-builder \
    --region=us-central1 \
    --memory=8Gi \
    --cpu=4
```

### Can't access Secret Manager
```bash
# Grant Cloud Run service account access
gcloud secrets add-iam-policy-binding openai-api-key \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Upload/Download too slow
```bash
# Use parallel transfers
gsutil -m cp -r data/raw gs://ai50-pipeline-data/raw/
```

## Clean Up

```bash
# Delete Cloud Run job
gcloud run jobs delete rag-index-builder --region=us-central1 --quiet

# Delete GCS bucket (WARNING: deletes all data!)
gsutil -m rm -r gs://ai50-pipeline-data

# Delete secret
gcloud secrets delete openai-api-key --quiet
```

## Next Steps

1. ✅ **Lab 7**: RAG index build (this deployment)
2. 🔄 **Lab 2**: Create Airflow DAG for full ingestion
3. 🔄 **Lab 3**: Create Airflow DAG for daily refresh
4. 🔄 **Lab 8**: Deploy FastAPI + Streamlit on Cloud Run



