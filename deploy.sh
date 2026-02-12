#!/bin/bash
# =============================================================================
# Cloud Run Deployment Script for Emonk
# =============================================================================
# Usage:
#   ./deploy.sh
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - .env file with GCP configuration
#   - Service account with Vertex AI + Cloud Run permissions
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
    "ALLOWED_USERS"
    "GCS_MEMORY_BUCKET"
    "GOOGLE_APPLICATION_CREDENTIALS"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: Missing required env var: $var"
        exit 1
    fi
done

echo "🚀 Deploying Emonk to Cloud Run"
echo "================================"
echo "Project: $VERTEX_AI_PROJECT_ID"
echo "Region: $CLOUD_RUN_REGION"
echo "Service: $CLOUD_RUN_SERVICE_NAME"
echo "Allowed users: $ALLOWED_USERS"
echo "GCS bucket: $GCS_MEMORY_BUCKET"
echo "================================"
echo

# Build and deploy to Cloud Run (Cloud Build will use Dockerfile)
gcloud run deploy "$CLOUD_RUN_SERVICE_NAME" \
    --source . \
    --platform managed \
    --region "$CLOUD_RUN_REGION" \
    --project "$VERTEX_AI_PROJECT_ID" \
    --allow-unauthenticated \
    --min-instances="${CLOUD_RUN_MIN_INSTANCES:-0}" \
    --max-instances="${CLOUD_RUN_MAX_INSTANCES:-10}" \
    --memory=1Gi \
    --cpu=1 \
    --timeout=60s \
    --set-env-vars="VERTEX_AI_PROJECT_ID=$VERTEX_AI_PROJECT_ID" \
    --set-env-vars="VERTEX_AI_LOCATION=${VERTEX_AI_LOCATION:-us-central1}" \
    --set-env-vars="ALLOWED_USERS=$ALLOWED_USERS" \
    --set-env-vars="GCS_ENABLED=true" \
    --set-env-vars="GCS_MEMORY_BUCKET=$GCS_MEMORY_BUCKET" \
    --set-env-vars="MEMORY_DIR=/app/data/memory" \
    --set-env-vars="SKILLS_DIR=/app/skills" \
    --set-env-vars="LOG_LEVEL=INFO" \
    --set-env-vars="SCHEDULER_STORAGE=${SCHEDULER_STORAGE:-json}" \
    --set-env-vars="CRON_SECRET=${CRON_SECRET:-}" \
    --service-account="$(gcloud iam service-accounts list --filter="displayName:Compute Engine default service account" --format="value(email)")"

echo
echo "✅ Deployment complete!"
echo
echo "Service URL:"
gcloud run services describe "$CLOUD_RUN_SERVICE_NAME" \
    --region "$CLOUD_RUN_REGION" \
    --project "$VERTEX_AI_PROJECT_ID" \
    --format="value(status.url)"
echo
echo "Test health check:"
SERVICE_URL=$(gcloud run services describe "$CLOUD_RUN_SERVICE_NAME" \
    --region "$CLOUD_RUN_REGION" \
    --project "$VERTEX_AI_PROJECT_ID" \
    --format="value(status.url)")
curl -s "$SERVICE_URL/health" | jq .
echo
echo "Next steps:"
echo "1. Configure Google Chat webhook to point to: $SERVICE_URL/webhook"
echo "2. Send a test message in Google Chat"
echo "3. Check logs: gcloud run logs read $CLOUD_RUN_SERVICE_NAME --region $CLOUD_RUN_REGION"
