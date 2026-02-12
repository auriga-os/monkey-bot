# Cloud Scheduler Migration Rollout Guide

This guide provides a staged rollout plan for migrating from in-process cron to Cloud Scheduler with comprehensive testing and rollback procedures.

## Overview

The migration follows a 6-stage approach with verification at each step:

1. **Stage 0**: Pre-deployment validation
2. **Stage 1**: Deploy code with dual paths (no traffic switch)
3. **Stage 2**: Enable Cloud Scheduler in QA/staging
4. **Stage 3**: Shadow mode (dual execution for comparison)
5. **Stage 4**: Production cutover with Firestore
6. **Stage 5**: Cleanup legacy code paths

## Stage 0: Pre-Deployment Validation

### Prerequisites Checklist

- [ ] Cloud Run service is deployed and healthy
- [ ] Environment variables are configured (see `.env.example`)
- [ ] Firestore database is created (if using Firestore storage)
- [ ] Cloud Scheduler API is enabled
- [ ] Required IAM permissions are granted
- [ ] Code review completed
- [ ] Unit tests pass
- [ ] Integration tests pass

### Environment Setup

1. **QA Environment**:
   ```bash
   export ENVIRONMENT=qa
   export SCHEDULER_STORAGE=json  # Start with JSON for QA
   export SCHEDULER_CADENCE="*/5 * * * *"  # Every 5 minutes
   ```

2. **Production Environment**:
   ```bash
   export ENVIRONMENT=production
   export SCHEDULER_STORAGE=firestore  # Firestore for production
   export SCHEDULER_CADENCE="* * * * *"  # Every minute
   ```

### Run Pre-Deployment Tests

```bash
# Run unit tests
python -m pytest tests/unit/test_scheduler.py -v

# Run integration tests
python -m pytest tests/integration/test_cron_tick.py -v

# Lint and type check
python -m pylint src/core/scheduler/
python -m mypy src/core/scheduler/
```

## Stage 1: Deploy Code (Dual Paths Available)

### Deploy to QA

```bash
cd monkey-bot
./deploy.sh
```

### Verify Deployment

1. **Check service health**:
   ```bash
   SERVICE_URL=$(gcloud run services describe emonk-agent \
     --region us-central1 --format 'value(status.url)')
   curl "$SERVICE_URL/health"
   ```

2. **Verify endpoints exist**:
   ```bash
   # Test /cron/tick endpoint (should return 401 without auth)
   curl -X POST "$SERVICE_URL/cron/tick"
   
   # Test /webhook endpoint (should return 401 without allowed user)
   curl -X POST "$SERVICE_URL/webhook" -H "Content-Type: application/json" \
     -d '{"message":{"sender":{"email":"test@example.com"},"text":"test"}}'
   ```

3. **Check logs for startup**:
   ```bash
   gcloud run logs read emonk-agent --region us-central1 --limit 20
   ```
   
   Should see:
   - ✅ Scheduler storage initialized (JSON or Firestore)
   - ✅ Agent Core created
   - No errors during startup

### Rollback Plan

If deployment fails:
```bash
# Rollback to previous revision
gcloud run services update-traffic emonk-agent \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region us-central1
```

## Stage 2: Enable Cloud Scheduler (QA)

### Create Scheduler Job

```bash
cd monkey-bot
./setup-scheduler.sh
```

### Manual Test

Trigger scheduler manually:

```bash
gcloud scheduler jobs run emonk-agent-tick --location us-central1
```

### Verify Execution

1. **Check Cloud Scheduler logs**:
   ```bash
   gcloud scheduler jobs describe emonk-agent-tick --location us-central1
   ```
   
   Look for:
   - `state: ENABLED`
   - Recent execution in `lastAttemptTime`
   - `httpTarget.oidcToken` configured

2. **Check Cloud Run logs**:
   ```bash
   gcloud run logs read emonk-agent --region us-central1 \
     --filter="jsonPayload.message:scheduler" --limit 50
   ```
   
   Should see:
   - "Running scheduler tick"
   - "Scheduler tick completed"
   - Metrics: `jobs_checked`, `jobs_executed`, etc.

3. **Verify metrics**:
   Look for structured log with:
   ```json
   {
     "message": "Scheduler tick completed",
     "jobs_checked": 5,
     "jobs_due": 2,
     "jobs_executed": 2,
     "jobs_succeeded": 2,
     "jobs_failed": 0
   }
   ```

### Acceptance Criteria

- [ ] Scheduler job triggers every configured interval
- [ ] `/cron/tick` endpoint returns 200 with metrics
- [ ] No authentication errors (401s)
- [ ] Jobs execute successfully
- [ ] Cloud Run logs show tick execution
- [ ] No errors or warnings in logs

### Rollback Plan

Disable scheduler temporarily:

```bash
gcloud scheduler jobs pause emonk-agent-tick --location us-central1
```

## Stage 3: Shadow Mode (Dual Execution)

**Purpose**: Run both Cloud Scheduler and legacy loop side-by-side to validate behavior.

### Enable Shadow Mode

Add environment variable:
```bash
export SCHEDULER_SHADOW_MODE=true
```

This enables both:
- Cloud Scheduler → `/cron/tick`
- Legacy `start_scheduler()` loop (if called)

### Deploy Shadow Mode Build

```bash
./deploy.sh
```

### Monitor for Discrepancies

Run monitoring script:

```bash
# Create monitoring script
cat > monitor-shadow.sh << 'EOF'
#!/bin/bash
while true; do
  echo "=== $(date) ==="
  
  # Check scheduler ticks
  gcloud run logs read emonk-agent --region us-central1 \
    --filter="jsonPayload.message:scheduler tick" \
    --limit 5 --format=json | \
    jq '.[] | {time: .timestamp, message: .jsonPayload.message, metrics: .jsonPayload}'
  
  echo ""
  sleep 60
done
EOF

chmod +x monitor-shadow.sh
./monitor-shadow.sh
```

### Compare Execution

Over 1-hour period, verify:

- [ ] Both paths execute the same jobs
- [ ] No duplicate side effects (posts, API calls)
- [ ] Execution timing is comparable
- [ ] Error rates are similar

### Acceptance Criteria

- [ ] Shadow mode runs for ≥1 hour without issues
- [ ] Duplicate detection works (no double-posting)
- [ ] Cloud Scheduler path matches legacy behavior
- [ ] No performance degradation

### Rollback Plan

Disable Cloud Scheduler, keep legacy:

```bash
gcloud scheduler jobs pause emonk-agent-tick --location us-central1
export SCHEDULER_SHADOW_MODE=false
./deploy.sh
```

## Stage 4: Production Cutover (Firestore)

### Pre-Cutover Checklist

- [ ] Shadow mode validated successfully
- [ ] Firestore database created
- [ ] IAM permissions configured
- [ ] Monitoring alerts configured
- [ ] Incident response plan documented

### Switch to Firestore

Update environment:
```bash
export SCHEDULER_STORAGE=firestore
export VERTEX_AI_PROJECT_ID=your-project-id
```

### Deploy Production Build

```bash
./deploy.sh
```

### Disable Legacy Loop

Remove any startup code calling:
```python
await agent_core.start_scheduler()
```

Redeploy:
```bash
./deploy.sh
```

### Monitor Cutover

1. **Watch logs in real-time**:
   ```bash
   gcloud run logs tail emonk-agent --region us-central1
   ```

2. **Check Firestore operations**:
   - Open Cloud Console → Firestore
   - Navigate to `scheduler_jobs` collection
   - Verify documents are created/updated
   - Check `lease_until` fields for locking

3. **Monitor metrics** (first hour):
   - Jobs execute on schedule
   - No duplicate executions
   - Lease claim/release working
   - No errors in Firestore operations

### Failure Injection Tests

Run controlled failure scenarios:

1. **Duplicate Scheduler Trigger**:
   ```bash
   # Trigger scheduler twice rapidly
   gcloud scheduler jobs run emonk-agent-tick --location us-central1 &
   gcloud scheduler jobs run emonk-agent-tick --location us-central1 &
   ```
   
   **Expected**: Second execution skips jobs (lease already claimed)

2. **Cloud Run Restart Mid-Execution**:
   ```bash
   # Deploy new revision while jobs are running
   ./deploy.sh
   ```
   
   **Expected**: 
   - Leases expire after 5 minutes
   - Jobs retry on next tick
   - No lost jobs

3. **Firestore Transient Error**:
   Simulate by temporarily blocking Firestore access:
   ```bash
   # Remove Firestore IAM permission temporarily
   gcloud projects remove-iam-policy-binding your-project-id \
     --member="serviceAccount:..." --role="roles/datastore.user"
   ```
   
   **Expected**: 
   - Graceful error handling
   - Jobs retry on next tick
   - Error logged but doesn't crash service

4. **Clock Skew / Overdue Jobs**:
   Schedule job 10 minutes in past:
   ```python
   await scheduler.schedule_job(
       job_type="test",
       schedule_at=datetime.utcnow() - timedelta(minutes=10),
       payload={}
   )
   ```
   
   **Expected**: Job executes on next tick (catch-up logic works)

### Acceptance Criteria

- [ ] Jobs execute reliably for ≥24 hours
- [ ] No duplicate executions detected
- [ ] Firestore locking prevents race conditions
- [ ] Failure scenarios handled gracefully
- [ ] Error rate <1% (excluding transient Firestore errors)
- [ ] Latency p99 <2 seconds for tick endpoint
- [ ] All scheduled jobs complete within cadence window

### Rollback Plan (Emergency)

**Immediate rollback** (if critical issues):

```bash
# 1. Pause Cloud Scheduler
gcloud scheduler jobs pause emonk-agent-tick --location us-central1

# 2. Switch back to JSON storage
export SCHEDULER_STORAGE=json

# 3. Re-enable legacy loop in code (temporary)
# Uncomment in main.py:
# await agent_core.start_scheduler()

# 4. Deploy emergency rollback
./deploy.sh

# 5. Verify service health
curl "$SERVICE_URL/health"
```

**Partial rollback** (if Firestore issues only):

```bash
# Switch to JSON storage, keep Cloud Scheduler
export SCHEDULER_STORAGE=json
./deploy.sh
```

## Stage 5: Cleanup Legacy Code

After 7 days of stable production operation:

### Remove Legacy Code

1. **Delete in-process loop support**:
   - Remove `start()` method from `CronScheduler`
   - Remove `_check_and_execute_jobs()` method
   - Remove `running` flag

2. **Update documentation**:
   - Mark old scheduler docs as deprecated
   - Update README with Cloud Scheduler instructions

3. **Remove JSON storage** (optional):
   - Keep for dev/testing or remove entirely
   - Update default to Firestore

### Deploy Cleanup

```bash
./deploy.sh
```

### Final Verification

- [ ] Service still healthy
- [ ] No references to removed code
- [ ] Documentation updated
- [ ] Team trained on new approach

## Monitoring and Alerts

### Key Metrics to Monitor

1. **Scheduler Success Rate**:
   - Target: >99%
   - Alert if <95% for 5 minutes

2. **Job Execution Rate**:
   - Target: Matches scheduled cadence
   - Alert if zero jobs execute for 5 minutes

3. **Duplicate Execution Rate**:
   - Target: 0%
   - Alert if >0% (indicates locking failure)

4. **Tick Latency**:
   - Target: p99 <2s
   - Alert if p99 >5s

5. **Firestore Error Rate**:
   - Target: <0.1%
   - Alert if >1% for 5 minutes

### Create Monitoring Dashboard

Use Cloud Monitoring to create dashboard with:

- Cloud Scheduler execution count
- Cloud Run request count for `/cron/tick`
- Average tick latency
- Job execution metrics (from logs)
- Error rate by type

### Set Up Alerts

```bash
# Create alert policy for scheduler failures
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Scheduler Tick Failures" \
  --condition-display-name="High error rate" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s
```

## Runbook for Common Issues

### Issue: Jobs Not Executing

**Symptoms**: `jobs_executed: 0` in tick metrics

**Diagnosis**:
```bash
# Check job status in Firestore
# Look for pending jobs with past schedule_at

# Check for active leases
# Look for lease_until in future
```

**Resolution**:
1. Check if jobs are stuck with active leases
2. Verify handlers are registered at startup
3. Check job `schedule_at` timestamps
4. Manually release stuck leases if needed

### Issue: Duplicate Execution

**Symptoms**: Same job runs twice, duplicate side effects

**Diagnosis**:
```bash
# Check logs for duplicate "Executing job {id}" messages
# Check Firestore for lease timestamps
```

**Resolution**:
1. Verify Firestore storage is configured (not JSON)
2. Check Firestore transaction errors
3. Verify handler idempotency
4. Add execution deduplication in handlers if needed

### Issue: Scheduler Not Triggering

**Symptoms**: No tick logs, scheduler appears stopped

**Diagnosis**:
```bash
# Check scheduler job status
gcloud scheduler jobs describe emonk-agent-tick --location us-central1

# Check for IAM errors
gcloud run logs read emonk-agent --region us-central1 \
  --filter="severity>=ERROR"
```

**Resolution**:
1. Verify scheduler job is enabled
2. Check IAM permissions for service account
3. Verify OIDC token configuration
4. Test manually with `gcloud scheduler jobs run`

### Issue: High Latency

**Symptoms**: Tick endpoint takes >5 seconds

**Diagnosis**:
```bash
# Check Cloud Run metrics for cold starts
# Check job count and complexity
# Check Firestore operation latency
```

**Resolution**:
1. Increase Cloud Run `--min-instances` to prevent cold starts
2. Optimize job execution (batch operations, async)
3. Check Firestore indexes
4. Consider job sharding if many jobs

## Post-Migration Validation

After 30 days of stable operation, conduct final review:

### Success Criteria

- [ ] Zero production incidents related to scheduler
- [ ] Scheduled jobs execute reliably (>99.9% success rate)
- [ ] No duplicate executions detected
- [ ] Firestore costs within budget (<$5/month)
- [ ] Cloud Scheduler costs minimal (free tier or <$1/month)
- [ ] Team comfortable with new system
- [ ] Documentation complete and accurate

### Lessons Learned

Document in retrospective:
- Issues encountered and resolutions
- Unexpected edge cases
- Performance improvements identified
- Recommendations for future migrations

## Support and Escalation

### Debug Commands

```bash
# View recent scheduler ticks
gcloud run logs read emonk-agent --region us-central1 \
  --filter="jsonPayload.message:scheduler" --limit 20

# Check specific job execution
gcloud run logs read emonk-agent --region us-central1 \
  --filter="jsonPayload.job_id:YOUR_JOB_ID"

# View Firestore operations
gcloud logging read "resource.type=cloud_firestore" --limit 50

# Test scheduler manually
gcloud scheduler jobs run emonk-agent-tick --location us-central1
```

### Escalation Path

1. **Level 1**: Check this runbook and SCHEDULER_SETUP.md
2. **Level 2**: Review logs and Firestore state
3. **Level 3**: Rollback using emergency procedure
4. **Level 4**: Contact GCP support for platform issues

## Appendix: Testing Checklist

### Pre-Deployment Tests

- [ ] Unit tests for `CronScheduler.run_tick()`
- [ ] Unit tests for Firestore storage backend
- [ ] Unit tests for job lease claim/release
- [ ] Integration test for `/cron/tick` endpoint
- [ ] Integration test for OIDC auth validation
- [ ] Integration test for duplicate execution prevention

### Post-Deployment Tests (QA)

- [ ] Manual scheduler trigger
- [ ] Job execution verification
- [ ] Lease claim/release verification
- [ ] Duplicate trigger test
- [ ] Restart mid-execution test
- [ ] Overdue job catch-up test
- [ ] Error handling test

### Post-Deployment Tests (Production)

- [ ] Monitor for 24 hours
- [ ] Review all metrics dashboards
- [ ] Check for any errors or warnings
- [ ] Verify job execution patterns
- [ ] Validate cost estimates

