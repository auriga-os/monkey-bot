# Deployment Guide: Monkey-Bot Framework

This guide walks you through deploying a monkey-bot agent to Google Cloud Run.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Clone and Configure](#clone-and-configure)
3. [Set Up Google Cloud](#set-up-google-cloud)
4. [Configure Secret Manager](#configure-secret-manager)
5. [Deploy to Cloud Run](#deploy-to-cloud-run)
6. [Verify Deployment](#verify-deployment)
7. [Configure Google Chat](#configure-google-chat)
8. [Set Up Cloud Scheduler (Optional)](#set-up-cloud-scheduler-optional)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have:

- **Google Cloud Platform account** with billing enabled
- **gcloud CLI** installed and authenticated
  - Install: https://cloud.google.com/sdk/docs/install
  - Authenticate: `gcloud auth login`
- **Python 3.12+** installed locally (for development/testing)
- **Docker** installed (for local testing, optional)

---

## Clone and Configure

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/monkey-bot.git
cd monkey-bot
```

### 2. Create Configuration File

```bash
cp .env.example .env
```

### 3. Configure Environment Variables

Edit `.env` and fill in your values:

```bash
# Required: Your GCP project ID
VERTEX_AI_PROJECT_ID=your-gcp-project-id

# Required: Service account credentials (see "Set Up Google Cloud" section)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Required: Allowed users (comma-separated emails)
ALLOWED_USERS=user@example.com,admin@example.com

# Optional: Customize model (default: gemini-2.5-flash)
MODEL_PROVIDER=google_vertexai
MODEL_NAME=gemini-2.5-flash
```

See `.env.example` for all available configuration options.

---

## Set Up Google Cloud

### 1. Create or Select GCP Project

```bash
# List existing projects
gcloud projects list

# Create new project (if needed)
gcloud projects create your-project-id --name="My Monkey-Bot"

# Set as active project
gcloud config set project your-project-id
```

### 2. Enable Required APIs

```bash
# Enable required Google Cloud APIs
gcloud services enable \
    aiplatform.googleapis.com \
    run.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com \
    cloudscheduler.googleapis.com \
    firestore.googleapis.com
```

**This may take 2-3 minutes to complete.**

### 3. Create Service Account

```bash
# Set your project ID
PROJECT_ID=your-gcp-project-id

# Create service account
gcloud iam service-accounts create monkey-bot-sa \
    --display-name="Monkey-Bot Service Account" \
    --project=${PROJECT_ID}

# Get service account email
SERVICE_ACCOUNT_EMAIL="monkey-bot-sa@${PROJECT_ID}.iam.gserviceaccount.com"
```

### 4. Grant IAM Roles

```bash
# Grant Secret Manager access (for loading secrets)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

# Grant Vertex AI access (for calling Gemini models)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/aiplatform.user"

# Grant Cloud Run invoker (for running the service)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/run.invoker"

# Grant Firestore access (if using Firestore scheduler storage)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/datastore.user"
```

### 5. Download Service Account Key (for local development)

```bash
# Download key file
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=${SERVICE_ACCOUNT_EMAIL}

# Update .env file with path
echo "GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json" >> .env
```

**⚠️ Security Note:** Keep `service-account-key.json` secure! Add it to `.gitignore` and never commit it to version control.

---

## Configure Secret Manager

For production deployments, store sensitive values in Google Secret Manager instead of environment variables.

### 1. Create Secrets

```bash
# Create secret for Vertex AI project ID
echo -n "your-gcp-project-id" | gcloud secrets create vertex-ai-project-id \
    --data-file=- \
    --replication-policy="automatic"

# Create secret for allowed users
echo -n "user@example.com,admin@example.com" | gcloud secrets create allowed-users \
    --data-file=- \
    --replication-policy="automatic"
```

### 2. Verify Secrets

```bash
# List all secrets
gcloud secrets list

# View secret value (for testing)
gcloud secrets versions access latest --secret="vertex-ai-project-id"
```

### 3. Grant Service Account Access

The service account already has `secretmanager.secretAccessor` role from Step 3.4, so it can read these secrets.

---

## Deploy to Cloud Run

### Option A: Using Automated Deploy Script (Recommended)

The framework includes an automated deployment script that handles all the steps above.

```bash
# Edit configuration in deploy.sh
vim deploy.sh

# Update these variables:
# - PROJECT_ID=your-gcp-project-id
# - REGION=us-central1
# - SERVICE_NAME=monkey-bot

# Run deployment
./deploy.sh
```

The script will:
1. ✅ Check/create service account
2. ✅ Grant required IAM roles
3. ✅ Build Docker image with Cloud Build
4. ✅ Deploy to Cloud Run with secrets
5. ✅ Print service URL

### Option B: Manual Deployment

#### 1. Build and Deploy with gcloud

```bash
PROJECT_ID=your-gcp-project-id
REGION=us-central1
SERVICE_NAME=monkey-bot
SERVICE_ACCOUNT_EMAIL="monkey-bot-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Deploy to Cloud Run
gcloud run deploy ${SERVICE_NAME} \
    --source . \
    --platform managed \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --service-account ${SERVICE_ACCOUNT_EMAIL} \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --concurrency 1 \
    --max-instances 10 \
    --min-instances 0 \
    --set-env-vars "ENVIRONMENT=production,SCHEDULER_STORAGE=json" \
    --set-secrets "VERTEX_AI_PROJECT_ID=vertex-ai-project-id:latest,ALLOWED_USERS=allowed-users:latest"
```

**This will:**
- Build the Docker image using Cloud Build
- Deploy to Cloud Run in your specified region
- Mount secrets from Secret Manager
- Make the service publicly accessible (for Google Chat webhooks)

#### 2. Get Service URL

```bash
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --format='value(status.url)')

echo "Service URL: ${SERVICE_URL}"
```

Save this URL - you'll need it for Google Chat configuration.

---

## Verify Deployment

### 1. Check Health Endpoint

```bash
# Test health check
curl ${SERVICE_URL}/health

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2026-02-16T20:00:00Z",
#   "version": "1.0.0",
#   "checks": {
#     "agent_core": "ok",
#     "llm": "ok"
#   }
# }
```

### 2. Check Cloud Run Logs

```bash
# View recent logs
gcloud run services logs read ${SERVICE_NAME} \
    --region ${REGION} \
    --limit 50

# Follow logs in real-time
gcloud run services logs tail ${SERVICE_NAME} \
    --region ${REGION}
```

### 3. Test Webhook Endpoint (Optional)

If you want to test the Google Chat webhook locally:

```bash
# Send test message
curl -X POST ${SERVICE_URL}/webhook \
    -H "Content-Type: application/json" \
    -d '{
      "message": {
        "sender": {"email": "user@example.com"},
        "text": "Hello bot"
      }
    }'
```

---

## Configure Google Chat

### 1. Create Google Chat Space

1. Open Google Chat: https://chat.google.com
2. Create a new space or select an existing one
3. Click the space name → **Apps & integrations**

### 2. Create Webhook

1. Click **+ Add webhooks**
2. Name: "Monkey-Bot"
3. Avatar URL (optional): Add a custom bot avatar
4. Click **Save**

**Important:** Copy the webhook URL - you'll need it for posting messages from scheduled jobs.

### 3. Configure HTTP Endpoint (for interactive bot)

If you want a fully interactive bot (responds to messages):

1. Go to: https://console.cloud.google.com/apis/api/chat.googleapis.com
2. Click **Enable**
3. Go to **Configuration** tab
4. Set **HTTP Endpoint URL**: `${SERVICE_URL}/webhook`
5. Set **Connection settings**: HTTP endpoint
6. Click **Save**

### 4. Add Bot to Space

1. Go to your Google Chat space
2. Click **+** → **Add apps**
3. Search for your bot name
4. Click **Add**

### 5. Test the Bot

Send a message in the chat space:

```
@Monkey-Bot Hello! Can you help me?
```

The bot should respond within 2-5 seconds.

---

## Set Up Cloud Scheduler (Optional)

If your bot needs to run scheduled jobs (reports, reminders, etc.), set up Cloud Scheduler.

### 1. Create Scheduler Job

```bash
PROJECT_ID=your-gcp-project-id
REGION=us-central1
SERVICE_URL=https://monkey-bot-xxx-uc.a.run.app

# Create Cloud Scheduler job
gcloud scheduler jobs create http monkey-bot-tick \
    --location ${REGION} \
    --schedule "*/5 * * * *" \
    --uri "${SERVICE_URL}/cron/tick" \
    --http-method POST \
    --oidc-service-account-email "monkey-bot-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --time-zone "America/New_York"
```

**Schedule Options:**
- `*/5 * * * *` - Every 5 minutes
- `0 * * * *` - Every hour
- `0 9 * * 1-5` - Weekdays at 9 AM
- `0 0 * * 0` - Sundays at midnight

See: https://crontab.guru/ for cron pattern reference

### 2. Test the Scheduler

```bash
# Trigger job manually
gcloud scheduler jobs run monkey-bot-tick --location ${REGION}

# Check logs
gcloud run services logs read ${SERVICE_NAME} --limit 20 | grep "Scheduler tick"
```

### 3. Verify Job Execution

Check the logs for:
```
INFO: Running scheduler tick
INFO: Scheduler tick completed: 5 checked, 2 due, 2 executed, 2 succeeded
```

---

## Troubleshooting

### Common Issues

#### ❌ "Failed to load secrets"

**Symptoms:**
```
ERROR: Failed to load required secrets: vertex-ai-project-id
RuntimeError: Failed to load secrets. See docs/deployment.md
```

**Causes:**
- Secrets don't exist in Secret Manager
- Service account lacks `secretmanager.secretAccessor` role
- Wrong project ID in `GCP_PROJECT_ID` env var

**Solutions:**

1. Verify secrets exist:
```bash
gcloud secrets list
```

2. Check service account has correct role:
```bash
gcloud projects get-iam-policy ${PROJECT_ID} \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:monkey-bot-sa@${PROJECT_ID}.iam.gserviceaccount.com"
```

3. Grant role if missing:
```bash
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:monkey-bot-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

---

#### ❌ "Can't compare offset-naive and offset-aware datetimes"

**Symptoms:**
```
ERROR: TypeError: can't compare offset-naive and offset-aware datetimes
```

**Cause:** Timezone bugs in scheduler (fixed in monkey-bot v1.5.0+)

**Solutions:**

1. Update monkey-bot to latest version:
```bash
pip install --upgrade git+https://github.com/your-org/monkey-bot.git
```

2. If you've pinned an older version, remove the pin and upgrade

---

#### ❌ "Health check failed" (503 Service Unavailable)

**Symptoms:**
- `curl ${SERVICE_URL}/health` returns 503
- Cloud Run shows "Revision failed to start"

**Causes:**
- Application failed to start
- Missing required environment variables
- Import errors in Python code

**Solutions:**

1. Check Cloud Run logs for errors:
```bash
gcloud run services logs read ${SERVICE_NAME} --limit 50
```

2. Look for Python errors like `ModuleNotFoundError`, `ImportError`, or `KeyError`

3. Verify all required env vars are set:
```bash
gcloud run services describe ${SERVICE_NAME} --region ${REGION}
```

4. Test locally with same configuration:
```bash
export ENVIRONMENT=development
python -m src.gateway.main
```

---

#### ❌ "403 Forbidden" from Google Chat

**Symptoms:**
- Google Chat shows "403 Forbidden" when you message the bot
- Or "The app didn't respond"

**Causes:**
- Service not publicly accessible
- Missing Cloud Run invoker permissions

**Solutions:**

1. Allow unauthenticated invocations (required for Google Chat):
```bash
gcloud run services add-iam-policy-binding ${SERVICE_NAME} \
    --region ${REGION} \
    --member="allUsers" \
    --role="roles/run.invoker"
```

2. Verify the service is accessible:
```bash
curl -I ${SERVICE_URL}/health
# Should return: HTTP/2 200
```

---

#### ❌ Scheduled jobs not executing

**Symptoms:**
- Cloud Scheduler shows "Success" but jobs don't run
- No "Scheduler tick" logs appear

**Causes:**
- Cloud Scheduler not configured correctly
- `/cron/tick` endpoint not accessible
- Scheduler storage (Firestore) not initialized

**Solutions:**

1. Test `/cron/tick` endpoint manually:
```bash
curl -X POST ${SERVICE_URL}/cron/tick
```

2. Check Cloud Scheduler logs:
```bash
gcloud scheduler jobs describe monkey-bot-tick --location ${REGION}
```

3. Verify OIDC service account is correct:
```bash
# Should match your service account email
gcloud scheduler jobs describe monkey-bot-tick --location ${REGION} \
    --format="value(httpTarget.oidcToken.serviceAccountEmail)"
```

4. If using Firestore storage, ensure Firestore is enabled:
```bash
gcloud firestore databases create --location=${REGION}
```

---

### Getting Help

If you're still stuck after trying the troubleshooting steps:

1. **Check logs** for detailed error messages:
```bash
gcloud run services logs read ${SERVICE_NAME} --limit 100
```

2. **Review health endpoint** for component status:
```bash
curl ${SERVICE_URL}/health | jq
```

3. **Verify configuration** matches `.env.example`:
```bash
gcloud run services describe ${SERVICE_NAME} --region ${REGION}
```

4. **Test locally** with same configuration:
```bash
export ENVIRONMENT=development
python -m src.gateway.main
```

5. **Check GitHub Issues**: https://github.com/your-org/monkey-bot/issues

6. **Ask in community**: [Your support channel]

---

## Next Steps

Now that your bot is deployed:

- **Configure skills**: Add custom skills to `./skills/` directory
- **Create scheduled jobs**: Use `schedule_task` tool in your agent
- **Monitor performance**: Set up Cloud Monitoring dashboards
- **Set up alerting**: Configure error alerts in Cloud Monitoring
- **Add integrations**: Connect to external APIs and services

**Useful Links:**
- [Creating Skills](../examples/skills/diagnostics/README.md)
- [Configuration Reference](../.env.example)
- [Architecture Overview](../README.md)
- [API Documentation](./api.md)

---

## Summary Checklist

Before going to production, ensure:

- [ ] GCP project created with billing enabled
- [ ] All required APIs enabled
- [ ] Service account created with correct IAM roles
- [ ] Secrets stored in Secret Manager (not `.env`)
- [ ] Cloud Run service deployed successfully
- [ ] Health check returns 200 OK
- [ ] Google Chat webhook configured
- [ ] Bot responds to messages in Google Chat
- [ ] Cloud Scheduler configured (if using scheduled jobs)
- [ ] Logs show no errors
- [ ] Monitoring and alerting configured

**You're ready for production! 🚀**
