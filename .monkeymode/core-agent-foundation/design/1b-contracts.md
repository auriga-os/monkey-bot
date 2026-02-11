# Design: Emonk Core Agent Foundation - Phase 1B: Detailed Contracts

**Feature**: Core Agent Foundation  
**Date**: 2026-02-11  
**Status**: Phase 1B - API Contracts & Integration Points  
**Version**: 1.0

---

## API Contracts

### Base URL & Versioning
- **Base URL**: `https://{CLOUD_RUN_URL}`
- **Versioning**: None for Phase 1 (single version, no breaking changes expected)
- **Future**: Add `/v1/` prefix when v2 is needed

### Authentication & Authorization
- **External (Google Chat)**: User email allowlist (`ALLOWED_USERS` env var)
- **Internal**: No auth between modules (in-process calls)
- **Validation**: Check sender email against allowlist before processing

### Common Error Response Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "trace_id": "uuid",
    "timestamp": "ISO8601"
  }
}
```

### Common Errors
| Status | Code | When |
|--------|------|------|
| 401 | UNAUTHORIZED | User email not in ALLOWED_USERS |
| 500 | INTERNAL_ERROR | Unexpected server error |
| 503 | SERVICE_UNAVAILABLE | LLM or GCS unavailable |

---

## Public Endpoints

### POST /webhook
**Purpose**: Receive messages from Google Chat

**Request** (Google Chat format):
```json
{
  "message": {
    "sender": {"email": "user@example.com"},
    "text": "Remember that I prefer Python",
    "space": {"name": "spaces/xxx"},
    "thread": {"name": "spaces/xxx/threads/yyy"}
  }
}
```

**Response (200 OK)** (Google Chat Cards V2):
```json
{
  "text": "✅ I'll remember that. Stored: code_language_preference = Python"
}
```

**Endpoint-Specific Errors**:
| Status | Code | When |
|--------|------|------|
| 401 | UNAUTHORIZED | sender.email not in ALLOWED_USERS |
| 422 | INVALID_REQUEST | Missing required fields |

**Processing Flow**:
1. Validate request format
2. Check user email against allowlist
3. Filter PII (hash email to user_id, strip Google Chat metadata)
4. Pass clean message to Agent Core
5. Format response for Google Chat
6. Return response

---

### GET /health
**Purpose**: Health check for Cloud Run

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "timestamp": "ISO8601",
  "version": "1.0.0",
  "checks": {
    "llm": "ok",
    "gcs": "ok",
    "skills": "ok"
  }
}
```

**Response (503 Service Unavailable)**:
```json
{
  "status": "unhealthy",
  "timestamp": "ISO8601",
  "checks": {
    "llm": "error",
    "gcs": "ok",
    "skills": "ok"
  }
}
```

---

## Internal Module APIs

### Gateway → Agent Core
**Method**: `process_message(user_id: str, content: str, trace_id: str) -> str`

**Input**:
- `user_id`: Hashed user identifier (not email)
- `content`: Message text (PII already filtered)
- `trace_id`: Request trace ID

**Output**: Response text to send to Google Chat

**Errors**: Raises `AgentError` on failure

---

### Agent Core → LLM Client
**Method**: `chat(messages: List[Message], model: str, stream: bool) -> str`

**Input**:
- `messages`: Conversation history (last 10 messages)
- `model`: "gemini-2.0-flash" or "gemini-2.0-pro"
- `stream`: Enable streaming for responses > 200 tokens

**Output**: LLM response text

**Errors**: Raises `LLMError` on API failure, timeout, or rate limit

---

### Agent Core → Skills Engine
**Method**: `execute_skill(skill_name: str, args: Dict) -> SkillResult`

**Input**:
- `skill_name`: Skill identifier from SKILL.md
- `args`: Skill arguments from LLM tool call

**Output**: `SkillResult(success: bool, output: str, error: str | None)`

**Errors**: Raises `SkillError` if skill not found or execution fails

---

### Skills Engine → Terminal Executor
**Method**: `execute(command: str, args: List[str], timeout: int) -> ExecutionResult`

**Input**:
- `command`: Command name (must be in ALLOWED_COMMANDS)
- `args`: Command arguments (paths must be in ALLOWED_PATHS)
- `timeout`: Timeout in seconds (default 30)

**Output**: `ExecutionResult(stdout: str, stderr: str, exit_code: int)`

**Errors**: Raises `SecurityError` if command/path not allowed, `TimeoutError` if exceeds timeout

---

### Agent Core → Memory Manager
**Methods**:
- `read_conversation_history(user_id: str, limit: int) -> List[Message]`
- `write_conversation(user_id: str, role: str, content: str, trace_id: str)`
- `read_fact(user_id: str, key: str) -> str | None`
- `write_fact(user_id: str, key: str, value: str)`

**GCS Sync**: Async background sync after each write (non-blocking)

---

### Cron Manager
**Methods**:
- `add_job(id: str, schedule: Dict, payload: Dict, name: str, enabled: bool)`
- `remove_job(id: str)`
- `list_jobs() -> List[CronJob]`

**Storage**: `gs://emonk-memory/cron-jobs.json` (loaded on startup)

---

## Integration Points

### External Service Dependencies

| Service | Purpose | Timeout | Retry | Failure Handling |
|---------|---------|---------|-------|------------------|
| Vertex AI | LLM inference | 60s | 3x exponential backoff | Return error to user, log trace_id |
| GCS | Memory persistence | 10s | 3x exponential backoff | Log error, continue with local cache |
| Google Chat API | Send responses | 10s | 3x exponential backoff | Log error, user sees no response |

### Vertex AI Integration
**API**: Gemini API via `google-cloud-aiplatform`
**Endpoints Used**:
- `POST /v1/projects/{project}/locations/{location}/publishers/google/models/{model}:generateContent`

**Request**:
```json
{
  "contents": [{"role": "user", "parts": [{"text": "message"}]}],
  "generation_config": {"max_output_tokens": 2048, "temperature": 0.7}
}
```

**Failure Scenarios**:
- Rate limit (429): Exponential backoff, then fail with error message
- Timeout (60s): Fail with timeout error
- Model unavailable (503): Fail with service unavailable error

---

### Google Cloud Storage Integration
**Bucket**: `gs://emonk-memory/`
**Operations**:
- `upload_blob(path, content)` - Sync memory files (async)
- `download_blob(path)` - Load memory on startup
- `list_blobs(prefix)` - List files in directory

**Failure Scenarios**:
- Upload fails: Log error, continue (local cache is primary)
- Download fails on startup: Use empty memory (fresh start)
- Bucket not found: Log error, disable GCS sync

---

### Google Chat API Integration
**API**: Google Chat API via `google-api-python-client`
**Method**: Send response to same space/thread as incoming message

**Request**:
```json
{
  "text": "Response text",
  "thread": {"name": "spaces/xxx/threads/yyy"}
}
```

**Failure Scenarios**:
- Send fails: Log error, user sees no response (acceptable for MVP)
- Invalid space/thread: Log error, skip response

---

## Testing Strategy

### Unit Testing (pytest)

**Coverage Target**: 80% overall, 100% for security-critical paths

#### Gateway Module Tests
- **test_filter_pii**: Mock webhook payload → verify email hashed, metadata stripped
- **test_allowlist_valid_user**: Mock ALLOWED_USERS → verify authorized user passes
- **test_allowlist_invalid_user**: Mock ALLOWED_USERS → verify unauthorized user rejected (401)
- **test_format_google_chat_response**: Mock response text → verify Cards V2 format

**Mocks**: Agent Core, ALLOWED_USERS env var

---

#### Agent Core Tests
- **test_route_message_to_skill**: Mock LLM response (skill tool call) → verify skill executed
- **test_conversation_context**: Mock memory (10 messages) → verify correct context sent to LLM
- **test_llm_error_handling**: Mock LLM failure → verify error returned gracefully
- **test_trace_id_propagation**: Verify trace_id passed through entire flow

**Mocks**: LLM Client, Skills Engine, Memory Manager

---

#### Skills Engine Tests
- **test_discover_skills**: Mock ./skills/ directory → verify all skills loaded
- **test_execute_skill**: Mock Terminal Executor → verify skill execution
- **test_skill_not_found**: Request unknown skill → verify error returned
- **test_skill_conflict**: Two skills same name → verify first loaded, warning logged

**Mocks**: Terminal Executor, filesystem

---

#### Memory Manager Tests
- **test_read_conversation_history**: Mock GCS (10 messages) → verify last 10 returned
- **test_write_conversation**: Mock GCS upload → verify message written + synced
- **test_read_fact**: Mock facts.json → verify fact retrieved
- **test_write_fact**: Mock facts.json → verify fact written + synced
- **test_gcs_sync_failure**: Mock GCS failure → verify continues with local cache

**Mocks**: GCS client, local filesystem

---

#### Terminal Executor Tests
- **test_allowed_command**: Execute "cat" → verify succeeds
- **test_blocked_command**: Execute "rm" → verify SecurityError raised
- **test_allowed_path**: Execute "cat ./data/memory/test.txt" → verify succeeds
- **test_blocked_path**: Execute "cat /etc/passwd" → verify SecurityError raised
- **test_timeout**: Mock slow command → verify TimeoutError after 30s
- **test_output_limit**: Mock large output → verify truncated to 1MB

**Mocks**: subprocess

---

#### LLM Client Tests
- **test_chat_success**: Mock Vertex AI response → verify parsed correctly
- **test_chat_timeout**: Mock slow Vertex AI → verify timeout after 60s
- **test_chat_rate_limit**: Mock 429 response → verify exponential backoff
- **test_streaming_enabled**: Mock large response → verify streaming used
- **test_token_tracking**: Mock response with token metadata → verify tokens logged

**Mocks**: Vertex AI API

---

#### Cron Manager Tests
- **test_add_job**: Add cron job → verify saved to GCS + timer scheduled
- **test_remove_job**: Remove job → verify deleted from GCS + timer cancelled
- **test_execute_job**: Mock job trigger → verify payload executed
- **test_load_jobs_on_startup**: Mock GCS with jobs → verify all jobs rescheduled
- **test_cron_schedule**: Mock cron "0 9 * * *" → verify next run calculated correctly
- **test_interval_schedule**: Mock interval every 1 hour → verify next run calculated

**Mocks**: GCS client, threading.Timer

---

### Integration Testing (pytest + Docker)

**Test Database**: Local filesystem (`./test-data/`)
**Cleanup**: Delete `./test-data/` after each test

#### End-to-End Flow Tests
- **test_e2e_remember_fact**: POST /webhook (remember Python) → verify fact saved to disk + GCS
- **test_e2e_recall_fact**: POST /webhook (what's my preference?) → verify fact retrieved from memory
- **test_e2e_list_files**: POST /webhook (list files) → verify Terminal Executor called + response formatted
- **test_e2e_unauthorized_user**: POST /webhook (invalid email) → verify 401 returned

**Mocks**: Vertex AI (mock LLM responses), GCS (use local filesystem)

---

#### Skills Integration Tests
- **test_skill_file_ops_read**: Execute file-ops skill (read) → verify file contents returned
- **test_skill_file_ops_write**: Execute file-ops skill (write) → verify file created
- **test_skill_memory_remember**: Execute memory skill (remember) → verify fact saved
- **test_skill_memory_recall**: Execute memory skill (recall) → verify fact retrieved

**Mocks**: None (use real filesystem in `./test-data/`)

---

#### Cron Integration Tests
- **test_cron_job_execution**: Add job with "at" schedule (1 second future) → wait → verify executed
- **test_cron_job_persistence**: Add job → restart app → verify job reloaded + rescheduled

**Mocks**: None (use real GCS or local filesystem mock)

---

### Contract Testing

#### Google Chat Webhook Contract
- **test_webhook_request_schema**: Validate incoming webhook matches Google Chat format
- **test_webhook_response_schema**: Validate outgoing response matches Cards V2 format

**Tool**: JSON Schema validation (jsonschema library)

---

#### Internal API Contracts
- **test_agent_process_message_contract**: Verify signature matches `(user_id, content, trace_id) -> str`
- **test_skill_execute_contract**: Verify signature matches `(skill_name, args) -> SkillResult`

**Tool**: Type checking (mypy) + runtime validation (Pydantic)

---

### End-to-End Testing (Manual + Automated)

#### Critical User Journeys
1. **Remember + Recall**:
   - User: "Remember that I prefer Python"
   - Agent: "✅ Stored: code_language_preference = Python"
   - User: "What's my preferred language?"
   - Agent: "You prefer Python for all code examples"

2. **File Operations**:
   - User: "List files in ./data/memory/"
   - Agent: Lists SYSTEM_PROMPT.md, CONVERSATION_HISTORY/, KNOWLEDGE_BASE/

3. **Error Handling**:
   - User: "Delete /etc/passwd"
   - Agent: "❌ Permission denied. I can only access ./data/memory/ and ./skills/"

**Test Environment**: Local dev environment or Cloud Run staging

---

## Backward Compatibility

**Phase 1 Approach**: No versioning (single version)
**Future Breaking Changes**:
- Add `/v1/` prefix to all endpoints
- Run v1 and v2 in parallel for 6 months
- Deprecation header: `X-API-Deprecated: true`

---

## Next Steps

Phase 1B complete! Next:
- **Phase 1C**: Security hardening, performance optimization, deployment strategy, observability
