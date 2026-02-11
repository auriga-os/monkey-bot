# Design: Emonk Core Agent Foundation - Phase 1C: Production Readiness

**Feature**: Core Agent Foundation  
**Date**: 2026-02-11  
**Status**: Phase 1C - Production Readiness (MVP)  
**Version**: 1.0

**Note**: Simplified for MVP (1 user, single instance). Add complexity when scaling.

---

## Security Design

### Authentication & Authorization
- **External**: Email allowlist (`ALLOWED_USERS` env var)
- **Internal**: No auth between modules (in-process)
- **Validation**: Check sender email against allowlist on every webhook request

### Input Validation
- **Webhook payload**: Validate Google Chat format (reject malformed requests)
- **User messages**: No sanitization needed (passed to LLM as-is per user requirement)
- **File paths**: Validated against `ALLOWED_PATHS` before execution
- **Commands**: Validated against `ALLOWED_COMMANDS` before execution

### Data Protection
- **PII filtering**: Email hashed to user_id, Google Chat metadata stripped before LLM
- **Secrets**: Stored in env vars (GCP Secret Manager for production)
- **Encryption in transit**: HTTPS enforced by Cloud Run
- **Encryption at rest**: GCS default encryption (Google-managed keys)

### Secrets Management
- **Development**: `.env` file (never committed)
- **Production**: GCP Secret Manager
- **Secrets to manage**:
  - `GOOGLE_APPLICATION_CREDENTIALS` (service account JSON)
  - `ALLOWED_USERS` (email allowlist)
  - `GCS_MEMORY_BUCKET` (bucket name)

**Rotation**: Service account keys rotated every 90 days (GCP best practice)

### Security Headers (Cloud Run default)
- TLS 1.3 enforced
- HTTPS only (HTTP redirects to HTTPS)

---

## Performance & Scalability

### Expected Load (MVP)
- **Users**: 1 user (startup team)
- **Requests**: ~100 messages/day (~1 req/10min)
- **Data**: < 1GB memory files

### Performance Targets
| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Response time | < 5s | > 10s |
| LLM latency | < 2s (Flash) | > 5s |
| Error rate | < 1% | > 5% |
| Availability | 99% | < 95% |

**Note**: Relaxed targets for MVP. Tighten when multi-user.

### Optimization Strategy

**LLM**:
- Use Flash by default (fast, cheap)
- Stream responses > 200 tokens (better UX)
- Context window: Last 10 messages (reduce tokens)

**Memory**:
- Local cache first (no GCS read on every request)
- Async GCS sync (non-blocking)
- Retention: 90 days conversation history

**Cron**:
- Single instance avoids duplicate execution
- Jobs loaded once on startup (no repeated GCS reads)

### Scalability Path (Future)
**When scaling to 10+ users**:
1. Increase Cloud Run instances (`--max-instances=5`)
2. Add GCS object versioning (handle concurrent writes)
3. Add Redis for conversation context (reduce GCS reads)
4. Add connection pooling for Vertex AI

**Current design supports this without refactor** ✓

---

## Deployment Strategy

### Rollout Approach
- **Phase 1**: Single Cloud Run instance (`--min-instances=1 --max-instances=1`)
- **Deployment**: Rolling update via `gcloud run deploy`
- **Rollback**: Cloud Run automatic revision rollback

### Deployment Pipeline (Simple)
```
Local Dev → Docker Build → Push to GCR → Deploy to Cloud Run → Health Check
```

**Steps**:
1. Build Docker image locally: `docker build -t emonk-agent .`
2. Tag: `docker tag emonk-agent gcr.io/{PROJECT_ID}/emonk-agent`
3. Push: `docker push gcr.io/{PROJECT_ID}/emonk-agent`
4. Deploy: `gcloud run deploy emonk-agent --image gcr.io/{PROJECT_ID}/emonk-agent ...`
5. Verify: `curl https://{SERVICE_URL}/health`

**Future**: Add GitHub Actions CI/CD

### Health Checks
**Liveness** (`GET /health`):
- Check LLM connectivity (Vertex AI)
- Check GCS connectivity
- Check skills loaded
- Return 200 if all healthy, 503 if any failing

**Readiness**: Same as liveness for MVP

**Startup**: Allow 30s for GCS sync + skill loading

### Rollback Plan

**Automatic Rollback**:
- Cloud Run keeps last 3 revisions
- If new revision fails health checks → automatic rollback to previous

**Manual Rollback**:
```bash
# List revisions
gcloud run revisions list --service emonk-agent

# Rollback to previous
gcloud run services update-traffic emonk-agent --to-revisions=emonk-agent-00001-abc=100
```

**Rollback Triggers**:
- Health check fails for 3 consecutive attempts
- Error rate > 50% for 5 minutes
- Manual decision (user reports issues)

**Rollback Time**: < 2 minutes (Cloud Run revision switch is instant)

### Post-Deployment Verification
- [ ] Health check returns 200
- [ ] Send test message via Google Chat → verify response
- [ ] Check Cloud Logging for errors
- [ ] Verify GCS sync working (check bucket for new files)

---

## Observability

### Logging

**Tool**: Cloud Logging (built-in with Cloud Run)

**Log Levels**:
- **INFO**: Request start/end, skill execution, memory operations
- **ERROR**: Failed LLM calls, GCS errors, skill errors, security violations

**Log Format** (structured JSON):
```json
{
  "timestamp": "2026-02-11T20:00:00Z",
  "severity": "INFO",
  "trace": "trace_abc123",
  "component": "agent_core",
  "message": "Executing skill: memory-remember",
  "user_id": "hashed_user_123",
  "skill": "memory-remember",
  "duration_ms": 45
}
```

**What to Log**:
- Every webhook request (trace_id, user_id, duration)
- Skill executions (skill name, args, result)
- LLM calls (model, tokens, duration)
- GCS sync operations (success/failure)
- Security violations (blocked commands, unauthorized users)

**What NOT to Log**:
- User email (hash to user_id first)
- Google Chat space/thread IDs
- Large message content (> 1KB)

### Metrics (Simple)

**Tool**: Cloud Logging metrics (no Prometheus for MVP)

**Key Metrics**:
| Metric | Query | Alert |
|--------|-------|-------|
| Error rate | `severity=ERROR` count | > 10 errors/hour |
| Response time | `duration_ms` p99 | > 10000ms |
| LLM failures | `component=llm_client severity=ERROR` | > 5/hour |
| Security blocks | `component=terminal_executor severity=ERROR` | > 1/day |

**Dashboard**: Cloud Console → Logs Explorer (manual queries for MVP)

### Tracing

**Tool**: Cloud Trace (built-in, optional for MVP)

**Trace ID**: Generated per request, propagated through all modules

**Sample Rate**: 100% (low volume, no sampling needed)

**Trace Spans**: Gateway → Agent Core → LLM/Skills/Memory

**Future**: Add OpenTelemetry when multi-user

### Alerting (Simple)

**Tool**: Cloud Monitoring + Email

**Alerts**:
| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| Service Down | Health check fails 3x | Critical | Email |
| High Error Rate | > 10 errors/hour | Warning | Email |
| LLM Failures | > 5 LLM errors/hour | Warning | Email |

**Setup**:
1. Create Cloud Monitoring alert policy
2. Set notification channel (email)
3. Test alert delivery

**Future**: Add PagerDuty/Slack when 24/7 support needed

### Dashboards

**Dashboard 1: Service Health** (Cloud Console):
- Request count (last 24h)
- Error rate (%)
- Response time (p50, p99)
- Health check status

**Dashboard 2: LLM Usage** (Cloud Console):
- LLM requests/hour
- Token usage (input + output)
- Model distribution (Flash vs Pro)
- LLM errors

**Future**: Add Grafana when metrics grow complex

---

## Risk Assessment (MVP Focus)

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| LLM API rate limit exceeded | Low | High | Exponential backoff + retry, monitor token usage | Dev |
| GCS sync fails (extended outage) | Low | Medium | Continue with local cache, alert on failure | Dev |
| Skill executes malicious code | Medium | High | Security warning in README, developer responsibility | User |
| Cron job runs twice (multi-instance) | N/A | Medium | Single instance for MVP, add locking when scaling | Dev |
| Cloud Run instance crash | Low | Medium | Auto-restart by Cloud Run, 1-2 min downtime | Platform |
| User email leaked to LLM | Low | Critical | PII filter validated in unit tests, code review | Dev |

### Risk Monitoring
- Set up alerts for LLM failures, GCS sync failures
- Weekly review of error logs (first 2 weeks post-deployment)
- Update risk assessment after any incident

---

## Infrastructure Requirements

### GCP Resources Needed
- **Cloud Run service**: emonk-agent (1 instance, 1 CPU, 2GB RAM)
- **GCS bucket**: emonk-memory (standard storage, us-central1)
- **Service Account**: emonk-agent-sa (Vertex AI, GCS, Cloud Logging permissions)
- **Secret Manager**: Store ALLOWED_USERS, service account key

### Estimated Costs (MVP)
| Resource | Usage | Cost/Month |
|----------|-------|------------|
| Cloud Run | 1 instance, ~10 hours/day active | $5-10 |
| Vertex AI (Gemini Flash) | ~3000 requests/month, ~30K tokens | $1-3 |
| GCS | < 1GB storage, minimal ops | $0.50 |
| **Total** | | **~$10-15/month** |

**Note**: Costs scale linearly with usage. Monitor via GCP Billing dashboard.

---

## Deployment Checklist

### Pre-Deployment
- [ ] Environment variables configured in Cloud Run
- [ ] Service account has required permissions (Vertex AI, GCS)
- [ ] GCS bucket created (emonk-memory)
- [ ] Skills directory populated (file-ops, shell, memory)
- [ ] `ALLOWED_USERS` env var set
- [ ] Dockerfile tested locally
- [ ] Health check endpoint working

### Deployment
- [ ] Build Docker image
- [ ] Push to GCR
- [ ] Deploy to Cloud Run
- [ ] Verify health check (GET /health returns 200)
- [ ] Test webhook (send Google Chat message)
- [ ] Verify GCS sync (check bucket for files)
- [ ] Set up Cloud Monitoring alerts

### Post-Deployment
- [ ] Send test messages (remember fact, recall fact, list files)
- [ ] Verify conversation history persisted
- [ ] Check error logs (should be empty)
- [ ] Schedule cron job (test execution)
- [ ] Document any issues encountered

---

## Final Sign-Off

- [x] Security reviewed (email allowlist, PII filter, secrets management)
- [x] Performance targets achievable (< 5s response, < 2s LLM)
- [x] Deployment plan clear (Cloud Run, health checks, rollback)
- [x] Observability in place (Cloud Logging, basic metrics, alerting)
- [x] Risks identified and mitigated (LLM limits, GCS sync, skill security)
- [x] **Simplified for MVP** (no over-engineering, practical approach)

**Status**: Ready for Phase 2 (User Stories)

---

## Next Steps

Phase 1C complete! All 3 design phases done:
- **Phase 1A**: Architecture & Core Design ✓
- **Phase 1B**: API Contracts & Integration ✓
- **Phase 1C**: Production Readiness ✓

**Ready for Phase 2: User Stories** - Decompose into parallelizable implementation stories
