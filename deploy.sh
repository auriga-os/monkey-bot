#!/bin/bash
# deploy.sh - Deploy auriga-marketing-bot to GCP Cloud Run

set -e  # Exit on error

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-auriga-prod}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="auriga-marketing-bot"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying ${SERVICE_NAME} to GCP Cloud Run${NC}"
echo ""

# Pre-deployment checklist
echo -e "${YELLOW}📋 Pre-deployment Checklist${NC}"
echo "1. Have you set all required secrets in GCP Secret Manager?"
echo "2. Have you tested all features locally?"
echo "3. Have you committed all changes to git?"
echo ""
read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Deployment cancelled${NC}"
    exit 1
fi

# Step 1: Build Docker image
echo -e "${GREEN}📦 Building Docker image...${NC}"
docker build -t ${IMAGE_NAME}:latest .

# Step 2: Push to Container Registry
echo -e "${GREEN}⬆️  Pushing image to GCR...${NC}"
docker push ${IMAGE_NAME}:latest

# Step 3: Deploy to Cloud Run
echo -e "${GREEN}🚢 Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --platform managed \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --concurrency 1 \
    --max-instances 1 \
    --min-instances 0 \
    --set-env-vars "ENVIRONMENT=production" \
    --set-secrets "GOOGLE_CHAT_WEBHOOK=google-chat-webhook:latest" \
    --set-secrets "X_API_KEY=x-api-key:latest" \
    --set-secrets "X_API_SECRET=x-api-secret:latest" \
    --set-secrets "X_ACCESS_TOKEN=x-access-token:latest" \
    --set-secrets "X_ACCESS_TOKEN_SECRET=x-access-token-secret:latest" \
    --set-secrets "INSTAGRAM_USER_ID=instagram-user-id:latest" \
    --set-secrets "INSTAGRAM_ACCESS_TOKEN=instagram-access-token:latest" \
    --set-secrets "TIKTOK_ACCESS_TOKEN=tiktok-access-token:latest" \
    --set-secrets "LINKEDIN_ACCESS_TOKEN=linkedin-access-token:latest" \
    --set-secrets "LINKEDIN_PERSON_URN=linkedin-person-urn:latest" \
    --set-secrets "REDDIT_ACCESS_TOKEN=reddit-access-token:latest" \
    --set-secrets "PERPLEXITY_API_KEY=perplexity-api-key:latest" \
    --set-secrets "FIRECRAWL_API_KEY=firecrawl-api-key:latest" \
    --set-secrets "VERTEX_AI_PROJECT_ID=vertex-ai-project-id:latest" \
    --set-secrets "ALLOWED_USERS=allowed-users:latest"

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --format 'value(status.url)')

echo ""
echo -e "${GREEN}✅ Deployment successful!${NC}"
echo ""
echo -e "Service URL: ${GREEN}${SERVICE_URL}${NC}"
echo -e "Health check: ${GREEN}${SERVICE_URL}/health${NC}"
echo ""
echo -e "${YELLOW}📝 Post-deployment steps:${NC}"
echo "1. Test health endpoint: curl ${SERVICE_URL}/health"
echo "2. Send test message in Google Chat"
echo "3. Monitor logs: gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}' --limit 50 --format json"
echo ""
