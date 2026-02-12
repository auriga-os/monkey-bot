#!/bin/bash
# =============================================================================
# Cloud Scheduler Setup Script
# =============================================================================
# This script sets up Cloud Scheduler to trigger the /cron/tick endpoint
# with proper IAM authentication (OIDC tokens).
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Cloud Run service deployed
#   - Appropriate IAM permissions
# =============================================================================

set -e  # Exit on error

# Load environment variables from .env
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Copy .env.example to .env and fill in your values"
    exit 1
fi

source .env

# Validate required env vars
REQUIRED_VARS=(
    "VERTEX_AI_PROJECT_ID"
    "CLOUD_RUN_REGION"
    "CLOUD_RUN_SERVICE_NAME"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: Missing required env var: $var"
        exit 1
    fi
done

PROJECT_ID="$VERTEX_AI_PROJECT_ID"
REGION="$CLOUD_RUN_REGION"
SERVICE_NAME="$CLOUD_RUN_SERVICE_NAME"
SCHEDULER_NAME="${SERVICE_NAME}-tick"
SCHEDULER_SERVICE_ACCOUNT="${SCHEDULER_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "🚀 Setting up Cloud Scheduler"
echo "================================"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo "Scheduler: $SCHEDULER_NAME"
echo "================================"
echo

# Step 1: Enable Cloud Scheduler API
echo "📦 Enabling Cloud Scheduler API..."
gcloud services enable cloudscheduler.googleapis.com \
    --project="$PROJECT_ID"

# Step 2: Create service account for Cloud Scheduler
echo "👤 Creating service account for Cloud Scheduler..."
gcloud iam service-accounts create "$SCHEDULER_NAME" \
    --display-name="Cloud Scheduler for $SERVICE_NAME" \
    --project="$PROJECT_ID" \
    2>/dev/null || echo "Service account already exists"

# Step 3: Grant run.invoker permission to service account
echo "🔐 Granting Cloud Run invoker permission..."
gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
    --member="serviceAccount:${SCHEDULER_SERVICE_ACCOUNT}" \
    --role="roles/run.invoker" \
    --region="$REGION" \
    --project="$PROJECT_ID"

# Step 4: Get Cloud Run service URL
echo "🔍 Getting Cloud Run service URL..."
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(status.url)")

CRON_ENDPOINT="${SERVICE_URL}/cron/tick"

echo "Service URL: $SERVICE_URL"
echo "Cron endpoint: $CRON_ENDPOINT"
echo

# Step 5: Create or update Cloud Scheduler job
SCHEDULE="${SCHEDULER_CADENCE:-* * * * *}"  # Default: every minute
TIMEZONE="${SCHEDULER_TIMEZONE:-America/New_York}"

echo "⏰ Creating Cloud Scheduler job..."
echo "Schedule: $SCHEDULE ($TIMEZONE)"

# Check if job already exists
if gcloud scheduler jobs describe "$SCHEDULER_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" &>/dev/null; then
    
    echo "Updating existing scheduler job..."
    gcloud scheduler jobs update http "$SCHEDULER_NAME" \
        --location="$REGION" \
        --project="$PROJECT_ID" \
        --schedule="$SCHEDULE" \
        --time-zone="$TIMEZONE" \
        --uri="$CRON_ENDPOINT" \
        --http-method="POST" \
        --oidc-service-account-email="$SCHEDULER_SERVICE_ACCOUNT" \
        --oidc-token-audience="$SERVICE_URL"
else
    echo "Creating new scheduler job..."
    gcloud scheduler jobs create http "$SCHEDULER_NAME" \
        --location="$REGION" \
        --project="$PROJECT_ID" \
        --schedule="$SCHEDULE" \
        --time-zone="$TIMEZONE" \
        --uri="$CRON_ENDPOINT" \
        --http-method="POST" \
        --oidc-service-account-email="$SCHEDULER_SERVICE_ACCOUNT" \
        --oidc-token-audience="$SERVICE_URL"
fi

echo
echo "✅ Cloud Scheduler setup complete!"
echo
echo "Scheduler job: $SCHEDULER_NAME"
echo "Schedule: $SCHEDULE ($TIMEZONE)"
echo "Target URL: $CRON_ENDPOINT"
echo "Service account: $SCHEDULER_SERVICE_ACCOUNT"
echo
echo "Next steps:"
echo "1. Test manually: gcloud scheduler jobs run $SCHEDULER_NAME --location $REGION"
echo "2. Check logs: gcloud run logs read $SERVICE_NAME --region $REGION --limit 50"
echo "3. Monitor execution in Cloud Scheduler console"
echo
