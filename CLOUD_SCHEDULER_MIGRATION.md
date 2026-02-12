# Cloud Scheduler Migration - Quick Start

This document provides a quick reference for the Cloud Scheduler migration from in-process cron to event-driven scheduling.

## What Changed

### Before (In-Process Cron)
- Scheduler ran as background asyncio loop inside Cloud Run
- Used `while True` polling every 10 seconds
- Jobs stored in local JSON files
- Single instance required (no scaling)
- Vulnerable to instance restarts

### After (Cloud Scheduler)
- Cloud Scheduler triggers HTTP endpoint every minute (configurable)
- Scheduler executes single tick on demand
- Jobs stored in Firestore with distributed locking
- Multi-instance safe with proper concurrency control
- Resilient to restarts and failures

## Quick Start

### 1. Update Environment Variables

Add to `.env`:

```bash
# Use Firestore for production
SCHEDULER_STORAGE=firestore

# Optional: Add cron secret for additional security
CRON_SECRET=$(openssl rand -hex 32)

# Configure schedule (default: every minute)
SCHEDULER_CADENCE="* * * * *"
SCHEDULER_TIMEZONE="America/New_York"
```

### 2. Deploy Updated Service

```bash
./deploy.sh
```

### 3. Set Up Cloud Scheduler

```bash
./setup-scheduler.sh
```

This creates:
- Service account for scheduler
- IAM binding for `roles/run.invoker`
- Cloud Scheduler job with OIDC auth

### 4. Test Manually

```bash
# Trigger scheduler once
gcloud scheduler jobs run emonk-agent-tick --location us-central1

# Check logs
gcloud run logs read emonk-agent --region us-central1 --limit 20
```

Look for:
- "Running scheduler tick"
- "Scheduler tick completed"
- Metrics showing jobs executed

## Architecture

```
Cloud Scheduler (every minute)
    │
    │ POST /cron/tick with OIDC token
    ▼
Cloud Run Service
    │
    ├─ /webhook → Google Chat (real-time, unchanged)
    │
    └─ /cron/tick → Scheduler tick
        │
        ├─ Load jobs from Firestore
        ├─ Claim jobs with distributed lock
        ├─ Execute due jobs
        └─ Release locks
```

## Key Features

### Real-Time Chat Preserved
- `/webhook` endpoint unchanged
- Synchronous responses to Google Chat
- No impact on user experience

### Distributed Locking
- Firestore transactions for atomic job claiming
- 5-minute lease duration
- Automatic lease expiration
- Prevents duplicate execution

### Idempotency
- Safe to retry failed jobs
- Deterministic execution keys
- Job handlers must be idempotent

### Observability
- Structured logging with trace IDs
- Metrics per tick (jobs checked, executed, succeeded, failed)
- Cloud Scheduler success rate monitoring

## Configuration

### Storage Backend

- **Development**: `SCHEDULER_STORAGE=json` (local files)
- **Production**: `SCHEDULER_STORAGE=firestore` (distributed)

### Authentication

Two methods supported:

1. **Cloud Scheduler Header** (automatic):
   ```
   X-Cloudscheduler: true
   ```

2. **Bearer Token** (optional extra security):
   ```
   Authorization: Bearer <CRON_SECRET>
   ```

### Schedule Cadence

Configure via `SCHEDULER_CADENCE` (cron format):

```bash
# Every minute (default)
SCHEDULER_CADENCE="* * * * *"

# Every 5 minutes
SCHEDULER_CADENCE="*/5 * * * *"

# Every hour
SCHEDULER_CADENCE="0 * * * *"

# Weekdays at 9 AM
SCHEDULER_CADENCE="0 9 * * 1-5"
```

## Testing

### Unit Tests

```bash
python -m pytest tests/unit/test_scheduler.py -v
python -m pytest tests/unit/test_scheduler_storage.py -v
```

### Integration Tests

```bash
python -m pytest tests/integration/test_cron_tick.py -v
```

### Manual Test in QA

```bash
# Schedule test job
# (Add to your agent code or via API)

# Trigger tick
gcloud scheduler jobs run emonk-agent-tick --location us-central1

# Verify execution
gcloud run logs read emonk-agent --region us-central1 | grep "Job.*completed"
```

## Monitoring

### Key Metrics

1. **Scheduler Success Rate**
   - Target: >99%
   - Cloud Scheduler console shows execution history

2. **Job Execution Count**
   - Check `jobs_executed` in logs
   - Should match scheduled jobs per interval

3. **Duplicate Executions**
   - Target: 0%
   - Check for "already claimed" messages

4. **Tick Latency**
   - Target: <2s p99
   - Check Cloud Run request latency

### Logs Query

```bash
# View recent ticks
gcloud run logs read emonk-agent --region us-central1 \
  --filter="jsonPayload.message:scheduler" --limit 50

# Check for errors
gcloud run logs read emonk-agent --region us-central1 \
  --filter="severity>=ERROR" --limit 20

# Find specific job
gcloud run logs read emonk-agent --region us-central1 \
  --filter="jsonPayload.job_id:YOUR_JOB_ID"
```

## Troubleshooting

### Scheduler Not Triggering

**Check**: Is scheduler job enabled?
```bash
gcloud scheduler jobs describe emonk-agent-tick --location us-central1
```

**Fix**: Enable if paused
```bash
gcloud scheduler jobs resume emonk-agent-tick --location us-central1
```

### Jobs Not Executing

**Check**: Are jobs pending with past `schedule_at`?
- Open Firestore console
- Look at `scheduler_jobs` collection
- Check `status=pending` and `schedule_at<now`

**Fix**: Check for stuck leases
- Look for `lease_until` in future
- Manually delete lease fields if stuck

### Duplicate Execution

**Check**: Is Firestore storage configured?
```bash
# Should show SCHEDULER_STORAGE=firestore
gcloud run services describe emonk-agent --region us-central1 \
  --format="value(spec.template.spec.containers[0].env)"
```

**Fix**: Ensure Firestore is enabled
```bash
export SCHEDULER_STORAGE=firestore
./deploy.sh
```

### Permission Denied (403)

**Check**: IAM binding
```bash
gcloud run services get-iam-policy emonk-agent --region us-central1
```

**Fix**: Re-run setup
```bash
./setup-scheduler.sh
```

## Rollback Procedure

If you need to rollback:

### Quick Rollback (Pause Scheduler)

```bash
# Pause Cloud Scheduler
gcloud scheduler jobs pause emonk-agent-tick --location us-central1
```

This stops scheduled execution but preserves configuration.

### Full Rollback (Emergency)

```bash
# 1. Pause scheduler
gcloud scheduler jobs pause emonk-agent-tick --location us-central1

# 2. Switch to JSON storage (or previous storage)
export SCHEDULER_STORAGE=json

# 3. Deploy
./deploy.sh

# 4. Verify service health
curl "$(gcloud run services describe emonk-agent --region us-central1 \
  --format='value(status.url)')/health"
```

## Documentation

- **Setup Guide**: `SCHEDULER_SETUP.md` - Complete setup instructions and IAM configuration
- **Rollout Guide**: `ROLLOUT_GUIDE.md` - Staged deployment plan with testing procedures
- **Migration Plan**: See Cursor plans directory for detailed technical plan

## Support

For issues or questions:

1. Check logs first: `gcloud run logs read emonk-agent --region us-central1`
2. Review troubleshooting section above
3. Consult SCHEDULER_SETUP.md for detailed guidance
4. Check Firestore console for job state

## Cost Estimate

Low-volume usage (single team):

- Cloud Scheduler: $0-0.10/month (first 3 jobs free)
- Cloud Run: Within free tier for cron ticks
- Firestore: ~$1-2/month

**Total**: ~$1-3/month

## Next Steps

After migration:

1. Monitor for 24 hours
2. Verify all scheduled jobs execute correctly
3. Check for any duplicate executions
4. Review and tune `SCHEDULER_CADENCE` if needed
5. Set up monitoring alerts
6. Update team documentation
