# Phase 3: Cloud Run Deployment + Reusable Framework

**Goal:** Production-ready deployment to GCP with reusable library for future agents

**Value Delivered:** Marketing agent running in production on Cloud Run. Framework extracted into reusable library, ready for jr software engineer agent or other use cases.

**Prerequisites:** Phase 1 and 2 must be complete (marketing agent working locally)

**Status:** Ready for monkeymode execution after Phase 2

---

## Strategic Context

This phase transforms the monolithic marketing agent into:
1. **Reusable Framework Library** - Core components extracted into `emonk-framework` package
2. **Production Deployment** - Marketing agent deployed to Cloud Run (serverless)
3. **Agent Templates** - Ready-to-use templates for new agent types

**Key Architectural Shift:**
- **From:** Local daemon with local cron
- **To:** Stateless Cloud Run with Cloud Scheduler

This enables:
- Zero-cost when idle (scale to zero)
- Auto-scaling for traffic spikes
- No server management
- Global availability

---

## Components to Build

### 1. Framework Library (`emonk-framework/`)

#### Directory Structure

```
emonk-framework/
├── emonk/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent.py        # Base agent class
│   │   ├── llm_client.py   # LLM abstraction
│   │   ├── memory.py       # Memory interface
│   │   └── skills.py       # Skill loader/executor
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── google_chat.py  # Google Chat integration
│   │   ├── telegram.py     # Telegram (future)
│   │   └── slack.py        # Slack (future)
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── gcs.py          # GCS storage adapter
│   │   ├── local.py        # Local storage adapter
│   │   └── sql.py          # SQL storage (future)
│   ├── deployment/
│   │   ├── __init__.py
│   │   ├── cloud_run.py    # Cloud Run helpers
│   │   ├── scheduler.py    # Cloud Scheduler integration
│   │   └── secrets.py      # Secret Manager integration
│   └── utils/
│       ├── __init__.py
│       ├── logging.py      # Structured logging
│       └── tracing.py      # Trace IDs
├── setup.py
├── pyproject.toml
├── README.md
└── LICENSE
```

#### Key Abstractions

**1. Base Agent Class**

```python
# emonk/core/agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class Agent(ABC):
    """Base class for all Emonk agents"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config["agent"]["name"]
        self.type = config["agent"]["type"]
        self.llm = self._init_llm()
        self.memory = self._init_memory()
        self.skills = self._init_skills()
    
    @classmethod
    def load_config(cls, path: str) -> Dict[str, Any]:
        """Load agent configuration from YAML"""
        import yaml
        with open(path) as f:
            return yaml.safe_load(f)
    
    @abstractmethod
    async def process_message(self, message: str, context: Dict) -> str:
        """Process incoming message - override in subclass"""
        pass
    
    def _init_llm(self):
        """Initialize LLM client"""
        from emonk.core.llm_client import LLMClient
        return LLMClient(self.config["agent"]["llm"])
    
    def _init_memory(self):
        """Initialize memory storage"""
        backend = self.config["agent"]["memory"]["backend"]
        if backend == "gcs":
            from emonk.storage.gcs import GCSStorage
            return GCSStorage(self.config["agent"]["memory"]["bucket"])
        else:
            from emonk.storage.local import LocalStorage
            return LocalStorage()
    
    def _init_skills(self):
        """Initialize skills"""
        from emonk.core.skills import SkillLoader
        return SkillLoader(self.config["agent"]["skills_dir"])
```

**2. Storage Adapters**

```python
# emonk/storage/gcs.py
from google.cloud import storage
import os

class GCSStorage:
    """GCS-backed storage for memory"""
    
    def __init__(self, bucket_name: str):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
    
    async def read(self, path: str) -> str:
        """Read file from GCS"""
        blob = self.bucket.blob(path)
        return blob.download_as_text()
    
    async def write(self, path: str, content: str):
        """Write file to GCS"""
        blob = self.bucket.blob(path)
        blob.upload_from_string(content)
    
    async def list(self, prefix: str) -> list[str]:
        """List files with prefix"""
        blobs = self.bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs]
```

**3. Cloud Run Adapter**

```python
# emonk/deployment/cloud_run.py
from fastapi import FastAPI, Request
from emonk.core.agent import Agent

class CloudRunAdapter:
    """Adapt agent for Cloud Run deployment"""
    
    def __init__(self, agent: Agent, integrations: list):
        self.agent = agent
        self.integrations = integrations
        self.app = self._create_app()
    
    def _create_app(self) -> FastAPI:
        """Create FastAPI app with routes"""
        app = FastAPI()
        
        # Google Chat webhook
        @app.post("/webhook")
        async def webhook(request: Request):
            data = await request.json()
            response = await self.agent.process_message(
                data["message"]["text"],
                {"user": data["user"]}
            )
            return {"text": response}
        
        # Health check
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        # Job execution (from Cloud Scheduler)
        @app.post("/jobs/execute")
        async def execute_job(request: Request):
            data = await request.json()
            job_id = data["job_id"]
            result = await self.agent.execute_job(job_id)
            return {"success": True, "result": result}
        
        return app
    
    def run(self):
        """Run the app"""
        import uvicorn
        port = int(os.environ.get("PORT", 8080))
        uvicorn.run(self.app, host="0.0.0.0", port=port)
```

#### Agent Configuration System

**agent.yaml Template:**

```yaml
agent:
  name: marketing-agent
  type: marketing
  llm:
    model: gemini-2.0-flash
    fallback: gemini-2.0-pro
    project_id: ${VERTEX_AI_PROJECT_ID}
    location: us-central1
  memory:
    backend: gcs  # or 'local' for development
    bucket: emonk-marketing-memory
  integrations:
    - google_chat
  skills_dir: ./skills/
  system_prompt: |
    You are a marketing campaign automation assistant.
    Focus on creating engaging, brand-aligned content.
    Always validate against BRAND_VOICE.md before posting.
```

**Configuration Loading:**

```python
# emonk/core/config.py
import os
import yaml
from string import Template

def load_config(path: str) -> dict:
    """Load config with environment variable substitution"""
    with open(path) as f:
        content = f.read()
    
    # Substitute environment variables
    template = Template(content)
    expanded = template.safe_substitute(os.environ)
    
    return yaml.safe_load(expanded)
```

---

### 2. Cloud Run Deployment

#### A. Stateless Architecture Adaptation

**Replace Local Cron Daemon**

**Before (Phase 1-2):**
```python
# src/cron/scheduler.py (local daemon)
class CronScheduler:
    def __init__(self):
        self.jobs = load_jobs()
        self.scheduler = BackgroundScheduler()
    
    def start(self):
        for job in self.jobs:
            self.scheduler.add_job(...)
        self.scheduler.start()
```

**After (Phase 3):**
```python
# src/cron/cloud_scheduler.py (Cloud Scheduler client)
from google.cloud import scheduler_v1

class CloudSchedulerClient:
    """Manage jobs in Cloud Scheduler"""
    
    def __init__(self, project_id: str, location: str):
        self.client = scheduler_v1.CloudSchedulerClient()
        self.project_id = project_id
        self.location = location
    
    def create_job(self, name: str, schedule: str, 
                   target_url: str, job_data: dict):
        """Create Cloud Scheduler job"""
        parent = f"projects/{self.project_id}/locations/{self.location}"
        
        job = scheduler_v1.Job(
            name=f"{parent}/jobs/{name}",
            schedule=schedule,
            time_zone="America/New_York",
            http_target=scheduler_v1.HttpTarget(
                uri=f"{target_url}/jobs/execute",
                http_method=scheduler_v1.HttpMethod.POST,
                headers={
                    "Content-Type": "application/json"
                },
                body=json.dumps(job_data).encode()
            )
        )
        
        return self.client.create_job(parent=parent, job=job)
    
    def list_jobs(self) -> list:
        """List all jobs"""
        parent = f"projects/{self.project_id}/locations/{self.location}"
        return list(self.client.list_jobs(parent=parent))
    
    def delete_job(self, name: str):
        """Delete job"""
        self.client.delete_job(name=name)
```

**Job Execution Flow (Serverless):**

```
1. Cloud Scheduler (9:00 AM daily)
     ↓
2. POST https://marketing-agent-xyz.run.app/jobs/execute
     Headers: Authorization: Bearer {service-account-token}
     Body: {"job_id": "competitor-prices-001"}
     ↓
3. Cloud Run spins up container (cold start or reuse)
     ↓
4. Agent loads job definition from GCS
     ↓
5. Executes job (e.g., fetch competitor prices)
     ↓
6. Sends results to Google Chat
     ↓
7. Updates job status in GCS
     ↓
8. Cloud Run container shuts down (or kept warm)
```

**Migration Script:**

```python
# scripts/migrate_cron_to_cloud_scheduler.py
"""Migrate local cron jobs to Cloud Scheduler"""

import json
from emonk.deployment.scheduler import CloudSchedulerClient

def migrate():
    # Load local cron jobs
    with open("./data/memory/cron_jobs.json") as f:
        local_jobs = json.load(f)
    
    # Initialize Cloud Scheduler client
    scheduler = CloudSchedulerClient(
        project_id=os.environ["GCP_PROJECT_ID"],
        location="us-central1"
    )
    
    # Create each job in Cloud Scheduler
    agent_url = os.environ["AGENT_URL"]
    
    for job in local_jobs["jobs"]:
        scheduler.create_job(
            name=job["id"],
            schedule=job["schedule"],
            target_url=agent_url,
            job_data={"job_id": job["id"], "task": job["task"]}
        )
        print(f"✓ Migrated {job['id']}")

if __name__ == "__main__":
    migrate()
```

#### B. GCP Services Integration

**1. Cloud Storage (Memory Persistence)**

**Bucket Structure:**
```
gs://emonk-marketing-memory/
├── SYSTEM_PROMPT.md
├── BRAND_VOICE.md
├── CONVERSATION_HISTORY/
│   └── 2026-02/
│       └── 2026-02-11.md
├── campaigns/
│   └── ai-eval-campaign-001/
│       ├── plan.json
│       └── posts.json
├── cron_jobs/
│   └── jobs.json
└── secrets/
    └── tokens.enc.json
```

**GCS Sync Implementation:**

```python
# emonk/storage/gcs.py (enhanced)
class GCSStorage:
    def __init__(self, bucket_name: str, cache_dir: str = "./cache"):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    async def read(self, path: str) -> str:
        """Read with local cache"""
        cache_path = os.path.join(self.cache_dir, path)
        
        # Check cache first
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                return f.read()
        
        # Fetch from GCS
        blob = self.bucket.blob(path)
        content = blob.download_as_text()
        
        # Update cache
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w") as f:
            f.write(content)
        
        return content
    
    async def write(self, path: str, content: str):
        """Write to GCS and cache"""
        # Update cache immediately
        cache_path = os.path.join(self.cache_dir, path)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w") as f:
            f.write(content)
        
        # Upload to GCS (async, non-blocking)
        blob = self.bucket.blob(path)
        blob.upload_from_string(content)
```

**2. Secret Manager (Token Storage)**

**Secret Names Convention:**
- `{agent-name}-{service}-token`
- Examples: `marketing-agent-x-api-token`, `marketing-agent-linkedin-token`

**Implementation:**

```python
# emonk/deployment/secrets.py
from google.cloud import secretmanager

class SecretManagerClient:
    """Manage secrets in Secret Manager"""
    
    def __init__(self, project_id: str):
        self.client = secretmanager.SecretManagerServiceClient()
        self.project_id = project_id
    
    def create_secret(self, name: str, value: str):
        """Create or update secret"""
        parent = f"projects/{self.project_id}"
        secret_id = name
        
        # Create secret
        try:
            secret = self.client.create_secret(
                parent=parent,
                secret_id=secret_id,
                secret={"replication": {"automatic": {}}}
            )
        except Exception:
            # Secret already exists
            secret = self.client.get_secret(
                name=f"{parent}/secrets/{secret_id}"
            )
        
        # Add version with value
        parent = secret.name
        payload = value.encode("UTF-8")
        self.client.add_secret_version(
            parent=parent,
            payload={"data": payload}
        )
    
    def get_secret(self, name: str) -> str:
        """Get secret value"""
        name = f"projects/{self.project_id}/secrets/{name}/versions/latest"
        response = self.client.access_secret_version(name=name)
        return response.payload.data.decode("UTF-8")
    
    def list_secrets(self) -> list:
        """List all secrets"""
        parent = f"projects/{self.project_id}"
        return list(self.client.list_secrets(parent=parent))
```

**Token Manager Migration:**

```python
# Migrate tokens from local storage to Secret Manager
# scripts/migrate_tokens_to_secret_manager.py

def migrate_tokens():
    # Load local tokens
    with open("./data/secrets/tokens.json") as f:
        tokens = json.load(f)
    
    # Initialize Secret Manager
    sm = SecretManagerClient(project_id=os.environ["GCP_PROJECT_ID"])
    agent_name = os.environ["AGENT_NAME"]
    
    # Create secret for each token
    for service, token_data in tokens["tokens"].items():
        secret_name = f"{agent_name}-{service}-token"
        sm.create_secret(secret_name, token_data["value"])
        print(f"✓ Migrated {service} token to Secret Manager")
```

**3. Cloud Scheduler (Cron Jobs)**

**Job Configuration:**

```yaml
# Example: Competitor prices daily job
name: competitor-prices-daily
schedule: "0 9 * * *"  # 9 AM daily
time_zone: America/New_York
http_target:
  uri: https://marketing-agent-xyz.run.app/jobs/execute
  http_method: POST
  headers:
    Content-Type: application/json
  body: |
    {
      "job_id": "competitor-prices-001",
      "task": "fetch_competitor_prices",
      "args": {
        "platforms": ["twitter", "linkedin"]
      }
    }
  oidc_token:
    service_account_email: marketing-agent-sa@project.iam.gserviceaccount.com
```

#### C. Cloud Run Configuration

**1. Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

# Create cache directory for GCS
RUN mkdir -p /app/cache

# Service account for GCP access (mounted at runtime)
ENV GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcp-credentials

# Cloud Run port
ENV PORT=8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run server
CMD ["python", "-m", "emonk.gateway.server"]
```

**2. cloud-run.yaml**

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: marketing-agent
  labels:
    app: emonk
    agent: marketing
spec:
  template:
    metadata:
      annotations:
        # Scaling configuration
        autoscaling.knative.dev/minScale: '0'  # Scale to zero when idle
        autoscaling.knative.dev/maxScale: '10'
        autoscaling.knative.dev/target: '80'  # Target 80% CPU utilization
        
        # Timeout
        run.googleapis.com/timeout: '300s'  # 5 minute timeout for long tasks
    spec:
      serviceAccountName: marketing-agent-sa@project.iam.gserviceaccount.com
      
      containers:
      - image: gcr.io/PROJECT_ID/marketing-agent:latest
        
        ports:
        - containerPort: 8080
        
        env:
        - name: AGENT_CONFIG
          value: /app/agent.yaml
        - name: GCS_MEMORY_BUCKET
          value: emonk-marketing-memory
        - name: GCP_PROJECT_ID
          value: PROJECT_ID
        - name: VERTEX_AI_LOCATION
          value: us-central1
        
        resources:
          limits:
            memory: 2Gi
            cpu: '2'
          requests:
            memory: 512Mi
            cpu: '1'
        
        # Liveness probe
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
```

**3. Deploy Script**

```bash
#!/bin/bash
# scripts/deploy.sh

set -euo pipefail

PROJECT_ID=${GCP_PROJECT_ID}
REGION=${GCP_REGION:-us-central1}
AGENT_NAME=${AGENT_NAME:-marketing-agent}

echo "🚀 Deploying ${AGENT_NAME} to Cloud Run..."

# Build Docker image
echo "Building Docker image..."
docker build -t gcr.io/${PROJECT_ID}/${AGENT_NAME}:latest .

# Push to Container Registry
echo "Pushing to Container Registry..."
docker push gcr.io/${PROJECT_ID}/${AGENT_NAME}:latest

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy ${AGENT_NAME} \
  --image gcr.io/${PROJECT_ID}/${AGENT_NAME}:latest \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --service-account ${AGENT_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 10

echo "✅ Deployment complete!"
gcloud run services describe ${AGENT_NAME} --region ${REGION} --format="value(status.url)"
```

---

### 3. Deployment Tooling

#### A. CLI Tool (`emonk-cli`)

**Installation:**

```bash
pip install emonk-cli
```

**Commands:**

```bash
# Initialize new agent project
emonk init --name "jr-engineer-agent" --type "software-engineer"

# Deploy to Cloud Run
emonk deploy --project my-gcp-project --region us-central1

# Manage secrets
emonk secrets set X_API_TOKEN --from-file ./token.txt
emonk secrets get X_API_TOKEN
emonk secrets list

# Manage cron jobs
emonk jobs create "daily-standup" --schedule "0 9 * * 1-5" --task "generate_standup"
emonk jobs list
emonk jobs delete "daily-standup"

# View logs
emonk logs tail --follow
emonk logs search "error" --last 1h

# Test agent locally
emonk dev --port 8080
```

**Implementation Sketch:**

```python
# emonk_cli/main.py
import click
from emonk.deployment import CloudSchedulerClient, SecretManagerClient

@click.group()
def cli():
    """Emonk CLI - Manage AI agents"""
    pass

@cli.command()
@click.option("--name", required=True)
@click.option("--type", default="general")
def init(name, type):
    """Initialize new agent project"""
    # Create directory structure from template
    # Copy agent.yaml template
    # Initialize git repo
    click.echo(f"✅ Created {name} agent project")

@cli.command()
@click.option("--project", required=True)
@click.option("--region", default="us-central1")
def deploy(project, region):
    """Deploy agent to Cloud Run"""
    # Build Docker image
    # Push to Container Registry
    # Deploy to Cloud Run
    click.echo("✅ Deployment complete!")

# ... more commands ...
```

#### B. Terraform/IaC

**Directory Structure:**

```
terraform/
├── main.tf
├── variables.tf
├── outputs.tf
└── modules/
    └── emonk-agent/
        ├── main.tf
        ├── variables.tf
        └── outputs.tf
```

**Main Configuration:**

```hcl
# terraform/main.tf
module "marketing_agent" {
  source = "./modules/emonk-agent"
  
  agent_name = "marketing-agent"
  project_id = var.gcp_project_id
  region     = "us-central1"
  
  # Storage
  memory_bucket = "emonk-marketing-memory"
  
  # Secrets
  secrets = [
    "x-api-token",
    "linkedin-token",
    "perplexity-token"
  ]
  
  # Cron Jobs
  cron_jobs = [
    {
      name     = "competitor-prices"
      schedule = "0 9 * * *"
      task     = "fetch-competitor-prices"
    },
    {
      name     = "weekly-report"
      schedule = "0 9 * * 1"
      task     = "generate-weekly-report"
    }
  ]
  
  # Cloud Run configuration
  memory_limit = "2Gi"
  cpu_limit    = "2"
  min_instances = 0
  max_instances = 10
}

output "agent_url" {
  value = module.marketing_agent.url
}
```

**Agent Module:**

```hcl
# terraform/modules/emonk-agent/main.tf

# GCS Bucket for memory
resource "google_storage_bucket" "memory" {
  name     = var.memory_bucket
  location = var.region
  
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 365  # Delete old conversation logs after 1 year
      matches_prefix = ["CONVERSATION_HISTORY/"]
    }
  }
}

# Service Account
resource "google_service_account" "agent" {
  account_id   = "${var.agent_name}-sa"
  display_name = "${var.agent_name} Service Account"
}

# IAM bindings
resource "google_storage_bucket_iam_member" "agent_storage" {
  bucket = google_storage_bucket.memory.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.agent.email}"
}

resource "google_project_iam_member" "agent_vertex_ai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent.email}"
}

# Cloud Run Service
resource "google_cloud_run_service" "agent" {
  name     = var.agent_name
  location = var.region
  
  template {
    spec {
      service_account_name = google_service_account.agent.email
      
      containers {
        image = "gcr.io/${var.project_id}/${var.agent_name}:latest"
        
        resources {
          limits = {
            memory = var.memory_limit
            cpu    = var.cpu_limit
          }
        }
        
        env {
          name  = "GCS_MEMORY_BUCKET"
          value = google_storage_bucket.memory.name
        }
      }
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = var.min_instances
        "autoscaling.knative.dev/maxScale" = var.max_instances
      }
    }
  }
}

# Cloud Scheduler Jobs
resource "google_cloud_scheduler_job" "cron_jobs" {
  for_each = { for job in var.cron_jobs : job.name => job }
  
  name      = each.value.name
  schedule  = each.value.schedule
  time_zone = "America/New_York"
  
  http_target {
    uri         = "${google_cloud_run_service.agent.status[0].url}/jobs/execute"
    http_method = "POST"
    
    body = base64encode(jsonencode({
      job_id = each.value.name
      task   = each.value.task
    }))
    
    oidc_token {
      service_account_email = google_service_account.agent.email
    }
  }
}
```

---

### 4. Documentation & Templates

#### A. Framework Documentation

**docs/quickstart.md:**

```markdown
# Quick Start Guide

## Install Framework

```bash
pip install emonk-framework
```

## Create Agent

```bash
emonk init --name my-agent --type general
cd my-agent
```

## Configure Agent

Edit `agent.yaml`:

```yaml
agent:
  name: my-agent
  type: general
  llm:
    model: gemini-2.0-flash
  memory:
    backend: local
  skills_dir: ./skills/
```

## Add Custom Skill

Create `skills/my-skill/SKILL.md` and `skills/my-skill/my_skill.py`.

## Run Locally

```bash
emonk dev --port 8080
```

## Deploy to Cloud Run

```bash
emonk deploy --project my-gcp-project
```
```

#### B. Agent Templates

**1. Marketing Agent Template**

```bash
templates/marketing-agent/
├── agent.yaml
├── skills/
│   ├── research/
│   ├── campaign/
│   ├── content/
│   └── posting/
├── data/
│   └── memory/
│       └── BRAND_VOICE.md
└── README.md
```

**2. General Assistant Template**

```bash
templates/general-assistant/
├── agent.yaml
├── skills/
│   ├── file-ops/
│   ├── shell/
│   └── memory/
└── README.md
```

**3. Jr Software Engineer Template (Skeleton)**

```bash
templates/jr-engineer-agent/
├── agent.yaml
├── skills/
│   ├── code/       # TODO: Implement in Phase 4
│   ├── dev/        # TODO: Implement in Phase 4
│   ├── git/        # TODO: Implement in Phase 4
│   └── docs/       # TODO: Implement in Phase 4
└── README.md
```

---

## Migration Path (Phase 1-2 → Phase 3)

### Step 1: Extract Framework Library

```bash
# Create emonk-framework package
mkdir emonk-framework
cd emonk-framework

# Copy core components
cp -r ../src/core emonk/core
cp -r ../src/integrations emonk/integrations
# ... etc

# Add setup.py
cat > setup.py << EOF
from setuptools import setup, find_packages

setup(
    name="emonk-framework",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[...],
)
EOF

# Install locally for testing
pip install -e .
```

### Step 2: Refactor Agent to Use Framework

**Before:**
```python
# src/core/agent.py (monolithic)
from src.core.llm_client import LLMClient
from src.gateway.google_chat import GoogleChatGateway

agent = LLMClient(model="gemini-2.0-flash")
gateway = GoogleChatGateway(agent=agent)
```

**After:**
```python
# marketing_agent.py (uses framework)
from emonk import Agent, GoogleChatIntegration
from emonk.storage import GCSStorage
from emonk.deployment import CloudRunAdapter

config = Agent.load_config("agent.yaml")
agent = Agent(config=config, storage=GCSStorage("emonk-marketing-memory"))
integration = GoogleChatIntegration(agent=agent)
app = CloudRunAdapter(agent=agent, integrations=[integration])
app.run()
```

### Step 3: Migrate Storage to GCS

```bash
# Run migration script
python scripts/migrate_local_to_gcs.py \
  --bucket emonk-marketing-memory \
  --local-dir ./data/memory
```

### Step 4: Migrate Cron Jobs to Cloud Scheduler

```bash
# Run migration script
python scripts/migrate_cron_to_cloud_scheduler.py \
  --project my-gcp-project \
  --region us-central1 \
  --agent-url https://marketing-agent-xyz.run.app
```

### Step 5: Deploy to Cloud Run

```bash
# Build and deploy
./scripts/deploy.sh
```

---

## Success Criteria

- [ ] Marketing agent deployed and running on Cloud Run
- [ ] Memory persists via GCS (survives container restarts)
- [ ] Cron jobs work via Cloud Scheduler
- [ ] Secrets managed via Secret Manager (no hardcoded tokens)
- [ ] Framework library can create new agent in < 30 minutes
- [ ] Documentation complete and tested with new user
- [ ] Zero downtime during scaling (graceful shutdown)
- [ ] Costs < $50/month for typical usage
- [ ] Agent responds within 2 seconds (P95)

---

## Cost Estimation

**Monthly Costs (Typical Usage):**

| Service | Usage | Cost |
|---------|-------|------|
| Cloud Run | 100 requests/day, 2GB RAM, 2 CPU | ~$15 |
| Cloud Storage | 10 GB storage, 1000 operations/day | ~$0.50 |
| Cloud Scheduler | 5 jobs | ~$0.10 |
| Secret Manager | 10 secrets, 1000 accesses/day | ~$0.10 |
| Vertex AI | 1M tokens/day (Flash) | ~$20 |
| **Total** | | **~$36/month** |

**Scale to Zero Benefits:**
- No charges when agent is idle
- Pay only for actual usage
- Auto-scale for traffic spikes

---

## Testing Strategy

### Pre-Deployment Tests
- [ ] Framework library installs correctly
- [ ] Agent runs locally with framework
- [ ] GCS storage works (read/write/list)
- [ ] Secret Manager integration works
- [ ] Cloud Scheduler client works

### Deployment Tests
- [ ] Docker image builds successfully
- [ ] Image pushes to Container Registry
- [ ] Cloud Run deployment succeeds
- [ ] Health check endpoint responds
- [ ] Agent responds to Google Chat messages

### Post-Deployment Tests
- [ ] Memory persists across restarts
- [ ] Cron jobs execute on schedule
- [ ] Secrets load correctly
- [ ] Logs appear in Cloud Logging
- [ ] Metrics appear in Cloud Monitoring

---

## Monitoring & Observability

### Cloud Logging Filters

```bash
# View agent logs
resource.type="cloud_run_revision"
resource.labels.service_name="marketing-agent"

# View errors
resource.type="cloud_run_revision"
resource.labels.service_name="marketing-agent"
severity>="ERROR"

# View cron job executions
jsonPayload.job_id="competitor-prices-001"
```

### Cloud Monitoring Metrics

**Key Metrics:**
- Request count (requests/second)
- Request latency (P50, P95, P99)
- Error rate (errors/second)
- Container instance count
- Memory utilization
- CPU utilization

**Alerts:**
- Error rate > 5% for 5 minutes
- Request latency P95 > 2 seconds
- Container instance count > 8 (near max)

---

## References

- [OpenClaw Gateway](../ref/01_gateway_daemon.md) - Adapt for HTTP instead of WebSocket
- [OpenClaw Deployment](../preplanning/OpenClaw_Implementation_Guide.md) - Section on Docker
- GCP Documentation:
  - [Cloud Run](https://cloud.google.com/run/docs)
  - [Cloud Scheduler](https://cloud.google.com/scheduler/docs)
  - [Secret Manager](https://cloud.google.com/secret-manager/docs)
  - [Cloud Storage](https://cloud.google.com/storage/docs)

---

## Next Phase

After Phase 3 is complete and deployed:
- **Phase 4:** Add production hardening features and build jr software engineer agent
- Focus: Error recovery, session management, multi-model routing, observability
