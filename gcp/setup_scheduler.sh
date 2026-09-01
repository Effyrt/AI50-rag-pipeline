#!/bin/bash

# Schedule the AI50 pipeline with Cloud Scheduler instead of Cloud Composer.
#
# Cloud Composer has no free tier and bills per environment rather than per DAG run.
# The deployed pipeline is two sequential Cloud Run Job invocations, which Cloud
# Scheduler can drive directly - and Cloud Scheduler gives 3 jobs free per month,
# permanently.
#
# The Airflow DAGs in airflow/dags/ remain the graded Lab 2/3 artifact and are still
# the right tool for local development and for demonstrating the orchestration. This
# script is the cheap way to actually run the pipeline on a schedule in production.
#
# Cadence note: the scraper consumes roughly 30,000 vCPU-seconds per full 50-company
# run, against a 180,000 vCPU-second monthly always-free allowance - about 6 runs per
# month. Weekly fits inside the free tier; daily does not.

set -e

PROJECT_ID="gen-lang-client-0653324487"
REGION="us-central1"
SCHEDULER_SA="ai50-scheduler"

# Weekly, Mondays at 03:00 UTC. Change to "0 3 * * *" for daily, but see the cadence
# note above: daily is roughly 5x the free vCPU allowance.
SCHEDULE="${SCHEDULE:-0 3 * * 1}"

echo "=================================================="
echo "Setting up Cloud Scheduler for the AI50 pipeline"
echo "=================================================="
echo "Project:  $PROJECT_ID"
echo "Region:   $REGION"
echo "Schedule: $SCHEDULE"
echo ""

gcloud services enable cloudscheduler.googleapis.com --project="$PROJECT_ID"

# ── Service account allowed to invoke Cloud Run Jobs ──────────────────────────────
SA_EMAIL="${SCHEDULER_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "Service account $SA_EMAIL already exists"
else
  echo "Creating service account $SA_EMAIL..."
  gcloud iam service-accounts create "$SCHEDULER_SA" \
    --display-name="AI50 Cloud Scheduler invoker" \
    --project="$PROJECT_ID" \
    || { echo "FATAL: failed to create service account" >&2; exit 1; }
fi

echo "Granting run.invoker..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.invoker" \
  --condition=None \
  >/dev/null \
  || { echo "FATAL: failed to grant run.invoker" >&2; exit 1; }

# ── Scheduler job per Cloud Run Job ───────────────────────────────────────────────
# Cloud Scheduler has no native "run Cloud Run Job" target, so it calls the Cloud Run
# Admin API v2 :run endpoint with an OAuth token.
schedule_run_job() {
  local name="$1" job="$2" schedule="$3"
  local uri="https://${REGION}-run.googleapis.com/v2/projects/${PROJECT_ID}/locations/${REGION}/jobs/${job}:run"

  if gcloud scheduler jobs describe "$name" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "  → updating scheduler job $name"
    gcloud scheduler jobs update http "$name" \
      --location="$REGION" --project="$PROJECT_ID" \
      --schedule="$schedule" --time-zone="Etc/UTC" \
      --uri="$uri" --http-method=POST \
      --oauth-service-account-email="$SA_EMAIL" \
      || { echo "FATAL: failed to update scheduler job $name" >&2; exit 1; }
  else
    echo "  → creating scheduler job $name"
    gcloud scheduler jobs create http "$name" \
      --location="$REGION" --project="$PROJECT_ID" \
      --schedule="$schedule" --time-zone="Etc/UTC" \
      --uri="$uri" --http-method=POST \
      --oauth-service-account-email="$SA_EMAIL" \
      || { echo "FATAL: failed to create scheduler job $name" >&2; exit 1; }
  fi
}

# The scraper runs on the given schedule; the extractor runs 2 hours later, allowing
# the 50-company scrape to finish. This is a deliberate simplification over Airflow's
# real task dependency - if strict sequencing matters, use the DAGs.
EXTRACTOR_SCHEDULE=$(python3 - "$SCHEDULE" <<'PY'
import sys

minute, hour, dom, month, dow = sys.argv[1].split()
shifted = int(hour) + 2
if shifted > 23 and (dom != "*" or dow != "*"):
    # Shifting past midnight would move the run into the next day, but the day-of-month
    # and day-of-week fields would still name the original day - scheduling the
    # extractor a whole period after the scrape. Refuse rather than get it subtly wrong.
    sys.exit(
        f"Scrape hour {hour} + 2h crosses midnight with a day constraint "
        f"(dom={dom}, dow={dow}). Set SCHEDULE to an hour <= 21, or create the "
        f"extractor scheduler job manually."
    )
print(" ".join([minute, str(shifted % 24), dom, month, dow]))
PY
) || { echo "FATAL: could not derive the extractor schedule" >&2; exit 1; }

schedule_run_job ai50-scrape-weekly     ai50-scraper   "$SCHEDULE"
schedule_run_job ai50-extract-weekly    ai50-extractor "$EXTRACTOR_SCHEDULE"

echo ""
echo "=================================================="
echo "✅ Cloud Scheduler configured"
echo "=================================================="
echo ""
echo "  ai50-scrape-weekly    $SCHEDULE            → ai50-scraper"
echo "  ai50-extract-weekly   $EXTRACTOR_SCHEDULE  → ai50-extractor"
echo ""
echo "Trigger one now to test:"
echo "  gcloud scheduler jobs run ai50-scrape-weekly --location=$REGION"
echo ""
echo "Inspect:"
echo "  gcloud scheduler jobs list --location=$REGION"
echo "  gcloud run jobs executions list --region=$REGION --limit=5"
echo "=================================================="
