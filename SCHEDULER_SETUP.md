# Cloud Scheduler Setup Guide

This guide explains how to migrate from in-process cron scheduling to Cloud Scheduler-triggered execution on Cloud Run.

## Architecture

```
┌─────────────────┐
│  Cloud Scheduler│
│  (every minute) │
└────────┬────────┘
         │ OIDC Token
         │ POST /cron/tick
         ▼
┌─────────────────────┐
│   Cloud Run Service │
│  ┌───────────────┐  │
│  │ /cron/tick    │  │
│  │ endpoint      │  │
│  └───────┬───────┘  │
│          │          │
│  ┌───────▼───────┐  │
│  │  Scheduler    │  │
│  │  run_tick()   │  │
│  └───────┬───────┘  │
│          │          │
│  ┌───────▼───────┐  │
│  │  Firestore    │  │
│  │  Job Storage  │  │
│  └───────────────┘  │
└─────────────────────┘
```

## Components

### 1. Cloud Scheduler
- Triggers HTTP POST to `/cron/tick` endpoint at configured cadence (default: every minute)
- Uses OIDC authentication with dedicated service account
- Retries on failure with exponential backoff

### 2. Cloud Run Service
- Receives authenticated requests from Cloud Scheduler
- Validates OIDC token via Cloud Run IAM
- Executes single scheduler tick and returns metrics

### 3. Scheduler Storage
- **Development**: JSON files (local or GCS)
- **Production**: Firestore with distributed locking
- Prevents duplicate execution across multiple Cloud Run instances

## Authentication Flow

1. Cloud Scheduler sends POST request with OIDC token
2. Cloud Run validates token:
   - Audience matches service URL
   - Issuer is `https://accounts.google.com`
   - Service account has `roles/run.invoker`
3. Request reaches `/cron/tick` endpoint
4. Scheduler executes jobs with distributed locking

## Setup Steps

### Prerequisites

- gcloud CLI installed and authenticated
- Cloud Run service deployed
- Firestore database created (for production)

### 1. Enable Required APIs

```bash
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable firestore.googleapis.com
```

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Scheduler storage backend
SCHEDULER_STORAGE=firestore  # or "json" for dev

# Scheduler cadence (cron format)
SCHEDULER_CADENCE="* * * * *"  # Every minute

# Timezone for scheduler
SCHEDULER_TIMEZONE="America/New_York"
```

### 3. Run Setup Script

The provided script automates IAM and Cloud Scheduler setup:

```bash
./setup-scheduler.sh
```

This script:
1. Creates service account for Cloud Scheduler
2. Grants `roles/run.invoker` permission
3. Creates Cloud Scheduler job with OIDC auth
4. Configures schedule and timezone

### 4. Verify Setup

Test the scheduler manually:

```bash
gcloud scheduler jobs run emonk-agent-tick --location us-central1
```

Check Cloud Run logs:

```bash
gcloud run logs read emonk-agent --region us-central1 --limit 50
```

Look for log entries:
- `"Running scheduler tick"`
- `"Scheduler tick completed"`
- Metrics: `jobs_checked`, `jobs_executed`, etc.

## Configuration Options

### Schedule Cadence

Set `SCHEDULER_CADENCE` environment variable in `.env`:

```bash
# Every minute (default)
SCHEDULER_CADENCE="* * * * *"

# Every 5 minutes
SCHEDULER_CADENCE="*/5 * * * *"

# Every hour at minute 0
SCHEDULER_CADENCE="0 * * * *"

# Weekdays at 9 AM
SCHEDULER_CADENCE="0 9 * * 1-5"
```

See [Cloud Scheduler schedule format](https://cloud.google.com/scheduler/docs/configuring/cron-job-schedules).

### Storage Backend

Configure via `SCHEDULER_STORAGE` environment variable:

- `json`: JSON file storage (dev/local only)
- `firestore`: Firestore with distributed locking (production)

### Fallback to Legacy Mode (Dev Only)

To use in-process continuous scheduling (not recommended for Cloud Run):

```python
# In main.py or startup code
import asyncio
await agent_core.start_scheduler()
```

This starts the legacy polling loop. **Do not use in production** - Cloud Run instances may restart, causing missed jobs.

## Monitoring

### Cloud Scheduler Metrics

View in Cloud Console → Cloud Scheduler:
- Success rate
- Execution count
- Latency
- Error messages

### Cloud Run Logs

Filter for scheduler-related logs:

```bash
gcloud run logs read emonk-agent \
  --region us-central1 \
  --filter="jsonPayload.message:scheduler"
```

Key log events:
- `"Running scheduler tick"` - Tick started
- `"Scheduler tick completed"` - Tick finished with metrics
- `"Job {id} already claimed"` - Duplicate prevention working
- `"Claimed job {id}"` - Job claimed for execution
- `"Job {id} completed successfully"` - Job execution succeeded

### Firestore Console

Monitor job state in Firestore:
1. Open Cloud Console → Firestore
2. Navigate to `scheduler_jobs` collection
3. Check job documents for:
   - `status`: pending/running/completed/failed
   - `lease_until`: Active lease timestamp
   - `attempts`: Retry count

## Troubleshooting

### Scheduler Not Triggering

**Symptom**: No logs from `/cron/tick` endpoint

**Solutions**:
1. Verify scheduler job exists:
   ```bash
   gcloud scheduler jobs describe emonk-agent-tick --location us-central1
   ```

2. Check IAM permissions:
   ```bash
   gcloud run services get-iam-policy emonk-agent --region us-central1
   ```
   Should show service account with `roles/run.invoker`.

3. Test manually:
   ```bash
   gcloud scheduler jobs run emonk-agent-tick --location us-central1
   ```

### Jobs Not Executing

**Symptom**: Tick runs but `jobs_executed: 0`

**Solutions**:
1. Check job status in Firestore (should be `pending`)
2. Verify `schedule_at` is in the past
3. Check for active leases (`lease_until` in future)
4. Verify job handlers are registered:
   ```python
   from src.job_handlers import register_marketing_handlers
   register_marketing_handlers(agent_core.scheduler)
   ```

### Duplicate Execution

**Symptom**: Same job runs multiple times

**Solutions**:
1. Ensure using Firestore storage (`SCHEDULER_STORAGE=firestore`)
2. Check for lease claim failures in logs
3. Verify Firestore transactions are working
4. Check handler idempotency (handlers should be safe to retry)

### Permission Denied

**Symptom**: 403 errors in Cloud Scheduler

**Solutions**:
1. Re-run setup script: `./setup-scheduler.sh`
2. Verify service account email matches:
   ```bash
   gcloud scheduler jobs describe emonk-agent-tick --location us-central1
   ```
3. Check Cloud Run service URL matches OIDC audience

## Migration from In-Process Loop

### Step 1: Deploy Code with Both Paths

Deploy the updated code with both `/cron/tick` and legacy `start()` available.

### Step 2: Set Up Cloud Scheduler

Run `./setup-scheduler.sh` to create scheduler job.

### Step 3: Shadow Mode (Optional)

Enable Cloud Scheduler but keep legacy loop running. Monitor logs to verify both execute the same jobs.

### Step 4: Switch Storage to Firestore

Update `.env`:
```bash
SCHEDULER_STORAGE=firestore
```

Redeploy service.

### Step 5: Disable Legacy Loop

Remove any `agent_core.start_scheduler()` calls from startup code.

### Step 6: Monitor and Verify

- Check Cloud Scheduler success rate
- Verify jobs execute on schedule
- Monitor for duplicate execution
- Check Firestore for proper lease management

## Cost Estimate

Low-volume usage (single team):

- **Cloud Scheduler**: $0.10 per job/month (first 3 jobs free)
  - 1 job = ~$0.10/month or **free** if ≤3 jobs
  
- **Cloud Run**: Within free tier for cron ticks
  - ~43,200 invocations/month (every minute)
  - <100ms execution time typically
  - Minimal memory/CPU
  
- **Firestore**: ~$1-2/month
  - Document reads/writes for job state
  - Small dataset size
  
**Total**: ~$0-3/month for low-volume usage

## Security Best Practices

1. **Use OIDC tokens**: Never use API keys or secrets for authentication
2. **Principle of least privilege**: Service account only has `run.invoker` role
3. **Validate audience**: Cloud Run automatically validates OIDC audience
4. **Monitor IAM changes**: Alert on permission modifications
5. **Rotate service accounts**: If compromised, create new service account

## Advanced: Custom OIDC Validation

For additional security, add custom OIDC token validation in `/cron/tick` endpoint:

```python
from google.oauth2 import id_token
from google.auth.transport import requests

def validate_oidc_token(token: str, expected_audience: str) -> bool:
    try:
        # Verify token
        claims = id_token.verify_oauth2_token(
            token, 
            requests.Request(),
            expected_audience
        )
        
        # Verify service account
        email = claims.get("email")
        if not email or not email.endswith("@{project}.iam.gserviceaccount.com"):
            return False
            
        return True
    except Exception:
        return False
```

However, Cloud Run's built-in OIDC validation is sufficient for most use cases.
