# Code Spec: Sprint 4 - Production Polish & Deployment

**Author:** MonkeyMode Agent  
**Date:** 2026-02-12  
**Status:** Ready for Implementation  
**Sprint:** Sprint 4 - Polish & Production  
**Stories:** 4.1-4.2 (Deployment, metrics, reporting)

---

## Table of Contents

1. [Implementation Summary](#implementation-summary)
2. [Technical Context](#technical-context)
3. [Story 4.1: Deployment & Documentation](#story-41-deployment--documentation)
4. [Story 4.2: Engagement Metrics Collection](#story-42-engagement-metrics-collection)
5. [Final Verification](#final-verification)

---

## Implementation Summary

**Files to Create:** 12 files  
**Files to Modify:** 2 files  
**Tests to Add:** 3 test files  
**Estimated Complexity:** M (3-5 days solo developer)

### File Breakdown by Story

| Story | Description | Files Created | Files Modified | Tests |
|-------|-------------|---------------|----------------|-------|
| 4.1 | Deployment & docs | 6 | 1 | 0 |
| 4.2 | Metrics collection | 5 | 1 | 3 |
| **Total** | **2 stories** | **11** | **2** | **3** |

---

## Technical Context

### Deployment Target

**GCP Cloud Run:**
- Serverless container platform
- Automatically scales to zero when idle
- Perfect for low-volume bots (10-25 posts/week)
- Pay only for actual usage

### Key Production Concerns

1. **Secrets Management:** API keys must be in GCP Secret Manager, not .env
2. **Health Checks:** Cloud Run needs /health endpoint
3. **Graceful Shutdown:** Scheduler must stop cleanly
4. **Logging:** Structured JSON logs for Cloud Logging
5. **Monitoring:** Track post success rate, API errors, scheduler health

### Dependencies

**Story 4.1 depends on:**
- All features complete (Sprints 1-3)
- GCP project created and configured

**Story 4.2 depends on:**
- All platform posting working (Sprint 2)
- Posts being tracked somewhere (need post IDs)

---

## Story 4.1: Deployment & Documentation

**Priority:** High  
**Size:** M (1-2 days)  
**Dependencies:** All previous sprints complete

### Overview

Create automated deployment to GCP Cloud Run with proper documentation for future developers.

### Task 4.1.1: Create Deployment Script

**Files to Create:**
- `deploy.sh` (new - main deployment script)
- `.dockerignore` (new)
- `Dockerfile` (new)
- `cloudbuild.yaml` (new - GCP Cloud Build config)
- `README.md` (modify - add deployment instructions)
- `SECRETS.md` (new - secrets setup guide)

**Files to Modify:**
- `config/settings.py` - Add production config loading

**Pattern Reference:** Standard GCP Cloud Run deployment

### Implementation Details

**Dockerfile:**

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data/memory

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Run application
CMD ["python", "main.py"]
```

**.dockerignore:**

```
# .dockerignore
.git
.gitignore
.env
.venv
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.coverage
htmlcov/
.monkeymode/
tests/
docs/
*.md
!README.md
.DS_Store
```

**Deployment Script:**

```bash
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
    --set-secrets "INSTAGRAM_USER_ID=instagram-user-id:latest" \
    --set-secrets "INSTAGRAM_ACCESS_TOKEN=instagram-access-token:latest" \
    --set-secrets "TIKTOK_ACCESS_TOKEN=tiktok-access-token:latest" \
    --set-secrets "LINKEDIN_ACCESS_TOKEN=linkedin-access-token:latest" \
    --set-secrets "REDDIT_ACCESS_TOKEN=reddit-access-token:latest" \
    --set-secrets "PERPLEXITY_API_KEY=perplexity-api-key:latest" \
    --set-secrets "FIRECRAWL_API_KEY=firecrawl-api-key:latest"

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
```

**Cloud Build Config:**

```yaml
# cloudbuild.yaml - Automated builds on git push
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/auriga-marketing-bot:$COMMIT_SHA', '.']
  
  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/auriga-marketing-bot:$COMMIT_SHA']
  
  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'auriga-marketing-bot'
      - '--image'
      - 'gcr.io/$PROJECT_ID/auriga-marketing-bot:$COMMIT_SHA'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'

images:
  - 'gcr.io/$PROJECT_ID/auriga-marketing-bot:$COMMIT_SHA'
```

**Health Endpoint:**

```python
# Add to main.py or create core/health.py

from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {
        "status": "healthy",
        "service": "auriga-marketing-bot",
        "timestamp": datetime.utcnow().isoformat(),
        "scheduler": {
            "running": agent.scheduler.running,
            "pending_jobs": len(agent.scheduler.get_pending_jobs())
        }
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Auriga Marketing Bot",
        "status": "running",
        "version": "1.0.0"
    }
```

**Production Config:**

```python
# config/settings.py (modify)

import os
from google.cloud import secretmanager

def load_secrets():
    """Load secrets from GCP Secret Manager in production."""
    if os.getenv("ENVIRONMENT") == "production":
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GCP_PROJECT_ID", "auriga-prod")
        
        secrets = [
            "google-chat-webhook",
            "x-api-key",
            "x-api-secret",
            "instagram-user-id",
            "instagram-access-token",
            "tiktok-access-token",
            "linkedin-access-token",
            "reddit-access-token",
            "perplexity-api-key",
            "firecrawl-api-key"
        ]
        
        loaded_secrets = {}
        for secret_name in secrets:
            try:
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                loaded_secrets[secret_name.upper().replace("-", "_")] = response.payload.data.decode("UTF-8")
            except Exception as e:
                logger.error(f"Failed to load secret {secret_name}: {e}")
        
        return loaded_secrets
    else:
        # Development: Use .env file
        from dotenv import load_dotenv
        load_dotenv()
        return {}

# Load secrets on import
SECRETS = load_secrets()
```

**SECRETS.md Documentation:**

```markdown
# Secrets Setup Guide

## Required Secrets

Before deploying, set up these secrets in GCP Secret Manager:

### Google Chat
```bash
echo -n "your_webhook_url" | gcloud secrets create google-chat-webhook --data-file=-
```

### X/Twitter
```bash
echo -n "your_api_key" | gcloud secrets create x-api-key --data-file=-
echo -n "your_api_secret" | gcloud secrets create x-api-secret --data-file=-
echo -n "your_access_token" | gcloud secrets create x-access-token --data-file=-
echo -n "your_access_token_secret" | gcloud secrets create x-access-token-secret --data-file=-
```

### Instagram
```bash
echo -n "your_user_id" | gcloud secrets create instagram-user-id --data-file=-
echo -n "your_access_token" | gcloud secrets create instagram-access-token --data-file=-
```

### TikTok
```bash
echo -n "your_access_token" | gcloud secrets create tiktok-access-token --data-file=-
```

### LinkedIn
```bash
echo -n "your_access_token" | gcloud secrets create linkedin-access-token --data-file=-
echo -n "your_person_urn" | gcloud secrets create linkedin-person-urn --data-file=-
```

### Reddit
```bash
echo -n "your_access_token" | gcloud secrets create reddit-access-token --data-file=-
```

### MCP Servers
```bash
echo -n "your_perplexity_key" | gcloud secrets create perplexity-api-key --data-file=-
echo -n "your_firecrawl_key" | gcloud secrets create firecrawl-api-key --data-file=-
```

## Grant Access to Cloud Run

```bash
gcloud secrets add-iam-policy-binding SECRET_NAME \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## Verify Secrets

```bash
gcloud secrets list
gcloud secrets versions access latest --secret="google-chat-webhook"
```
```

**README.md Updates:**

```markdown
# Auriga Marketing Bot

## Deployment

### Prerequisites
- GCP project with billing enabled
- Docker installed
- gcloud CLI configured

### Setup Secrets

Follow [SECRETS.md](SECRETS.md) to configure all API keys in GCP Secret Manager.

### Deploy

```bash
chmod +x deploy.sh
./deploy.sh
```

### Verify Deployment

```bash
# Check service status
gcloud run services describe auriga-marketing-bot --region us-central1

# View logs
gcloud logging read 'resource.type=cloud_run_revision' --limit 50

# Test health
curl https://auriga-marketing-bot-XXXXX.run.app/health
```

### Rollback

```bash
gcloud run services update-traffic auriga-marketing-bot \
    --to-revisions=PREVIOUS_REVISION=100
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy .env.example to .env and fill in values
cp .env.example .env

# Run locally
python main.py
```
```

**Critical Notes:**
- Use `--concurrency 1` and `--max-instances 1` to avoid race conditions in scheduler
- `--min-instances 0` allows scaling to zero (cost savings)
- `--timeout 300` (5 minutes) for long-running scheduler operations
- All secrets via Secret Manager (never commit .env to git)
- Health check every 30 seconds ensures service stays alive

---

## Story 4.2: Engagement Metrics Collection

**Priority:** Medium  
**Size:** M (1-2 days)  
**Dependencies:** All platform posting working

### Overview

Collect engagement metrics (likes, comments, shares) from all platforms and generate weekly reports sent to Google Chat.

### Task 4.2.1: Create Metrics Collection Script

**Files to Create:**
- `scripts/collect_metrics.py` (new)
- `scripts/generate_report.py` (new)
- `data/metrics/.gitkeep` (new - ensure directory exists)
- `tests/scripts/test_metrics_collection.py` (new)

**Files to Modify:**
- `core/scheduler/cron.py` - Add scheduled job types for metrics

**Pattern Reference:** Simple scripts, not full skills (run via cron)

### Implementation Details

**Metrics Collection Script:**

```python
# scripts/collect_metrics.py
"""Collect engagement metrics from all social platforms."""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from config.settings import SECRETS


class MetricsCollector:
    """Collect engagement metrics from all platforms."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.metrics_dir = data_dir / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
    
    async def collect_all(self) -> dict:
        """Collect metrics from all platforms."""
        metrics = {
            "collected_at": datetime.utcnow().isoformat(),
            "platforms": {}
        }
        
        # Collect from each platform
        metrics["platforms"]["x"] = await self.collect_x_metrics()
        metrics["platforms"]["instagram"] = await self.collect_instagram_metrics()
        metrics["platforms"]["tiktok"] = await self.collect_tiktok_metrics()
        metrics["platforms"]["linkedin"] = await self.collect_linkedin_metrics()
        metrics["platforms"]["reddit"] = await self.collect_reddit_metrics()
        
        # Save to file
        filename = f"{datetime.utcnow().strftime('%Y-%m-%d')}.json"
        (self.metrics_dir / filename).write_text(json.dumps(metrics, indent=2))
        
        return metrics
    
    async def collect_x_metrics(self) -> dict:
        """Collect metrics from X/Twitter."""
        import httpx
        
        # Get recent posts from local storage
        posts = self._load_recent_posts("x")
        
        if not posts:
            return {"posts": [], "total_engagement": 0}
        
        # Fetch engagement for each post
        headers = {
            "Authorization": f"Bearer {SECRETS['X_ACCESS_TOKEN']}"
        }
        
        engagement_data = []
        total_engagement = 0
        
        async with httpx.AsyncClient() as client:
            for post in posts:
                try:
                    # GET tweet metrics
                    response = await client.get(
                        f"https://api.twitter.com/2/tweets/{post['post_id']}",
                        headers=headers,
                        params={
                            "tweet.fields": "public_metrics",
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        metrics = data["data"]["public_metrics"]
                        
                        engagement = {
                            "post_id": post["post_id"],
                            "posted_at": post["posted_at"],
                            "likes": metrics["like_count"],
                            "retweets": metrics["retweet_count"],
                            "replies": metrics["reply_count"],
                            "impressions": metrics.get("impression_count", 0)
                        }
                        
                        engagement["total"] = (
                            engagement["likes"] + 
                            engagement["retweets"] + 
                            engagement["replies"]
                        )
                        
                        engagement_data.append(engagement)
                        total_engagement += engagement["total"]
                
                except Exception as e:
                    print(f"Error fetching metrics for post {post['post_id']}: {e}")
        
        return {
            "posts": engagement_data,
            "total_engagement": total_engagement,
            "avg_engagement": total_engagement / len(posts) if posts else 0
        }
    
    async def collect_instagram_metrics(self) -> dict:
        """Collect metrics from Instagram."""
        import httpx
        
        posts = self._load_recent_posts("instagram")
        if not posts:
            return {"posts": [], "total_engagement": 0}
        
        # Instagram Graph API
        base_url = "https://graph.facebook.com/v18.0"
        access_token = SECRETS["INSTAGRAM_ACCESS_TOKEN"]
        
        engagement_data = []
        total_engagement = 0
        
        async with httpx.AsyncClient() as client:
            for post in posts:
                try:
                    response = await client.get(
                        f"{base_url}/{post['post_id']}",
                        params={
                            "fields": "like_count,comments_count,timestamp",
                            "access_token": access_token
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        engagement = {
                            "post_id": post["post_id"],
                            "posted_at": post["posted_at"],
                            "likes": data.get("like_count", 0),
                            "comments": data.get("comments_count", 0)
                        }
                        
                        engagement["total"] = engagement["likes"] + engagement["comments"]
                        engagement_data.append(engagement)
                        total_engagement += engagement["total"]
                
                except Exception as e:
                    print(f"Error fetching Instagram metrics: {e}")
        
        return {
            "posts": engagement_data,
            "total_engagement": total_engagement,
            "avg_engagement": total_engagement / len(posts) if posts else 0
        }
    
    async def collect_tiktok_metrics(self) -> dict:
        """Collect metrics from TikTok."""
        # Similar pattern to Instagram
        # TikTok API endpoint: https://open.tiktokapis.com/v2/video/list/
        # Fields: like_count, comment_count, share_count, view_count
        posts = self._load_recent_posts("tiktok")
        return {"posts": [], "total_engagement": 0}  # TODO: Implement
    
    async def collect_linkedin_metrics(self) -> dict:
        """Collect metrics from LinkedIn."""
        # LinkedIn UGC Post Statistics API
        posts = self._load_recent_posts("linkedin")
        return {"posts": [], "total_engagement": 0}  # TODO: Implement
    
    async def collect_reddit_metrics(self) -> dict:
        """Collect metrics from Reddit."""
        # Reddit API: /api/info.json?id=post_id
        posts = self._load_recent_posts("reddit")
        return {"posts": [], "total_engagement": 0}  # TODO: Implement
    
    def _load_recent_posts(self, platform: str, days: int = 7) -> list:
        """Load posts from last N days for a platform."""
        # Posts should be stored by post-content skill after successful posting
        posts_dir = self.data_dir / "posts" / platform
        
        if not posts_dir.exists():
            return []
        
        # Load all post files from last N days
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_posts = []
        
        for post_file in posts_dir.glob("*.json"):
            try:
                post_data = json.loads(post_file.read_text())
                posted_at = datetime.fromisoformat(post_data["posted_at"])
                
                if posted_at >= cutoff:
                    recent_posts.append(post_data)
            except Exception as e:
                print(f"Error loading post file {post_file}: {e}")
        
        return recent_posts


async def main():
    """Run metrics collection."""
    data_dir = Path("./data/memory")
    collector = MetricsCollector(data_dir)
    
    print("📊 Collecting engagement metrics...")
    metrics = await collector.collect_all()
    
    print(f"✅ Metrics collected and saved to {collector.metrics_dir}")
    print(f"Total platforms: {len(metrics['platforms'])}")
    
    for platform, data in metrics["platforms"].items():
        print(f"  - {platform}: {data.get('total_engagement', 0)} total engagement")


if __name__ == "__main__":
    asyncio.run(main())
```

**Weekly Report Generation:**

```python
# scripts/generate_report.py
"""Generate weekly engagement report and send to Google Chat."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import httpx


class WeeklyReportGenerator:
    """Generate and send weekly engagement reports."""
    
    def __init__(self, data_dir: Path, webhook_url: str):
        self.data_dir = data_dir
        self.metrics_dir = data_dir / "metrics"
        self.webhook_url = webhook_url
    
    async def generate_and_send(self):
        """Generate weekly report and send to Google Chat."""
        # Load this week's metrics
        this_week_metrics = self._load_week_metrics(weeks_ago=0)
        last_week_metrics = self._load_week_metrics(weeks_ago=1)
        
        # Calculate growth
        growth = self._calculate_growth(this_week_metrics, last_week_metrics)
        
        # Format report
        report = self._format_report(this_week_metrics, growth)
        
        # Send to Google Chat
        await self._send_to_google_chat(report)
        
        print("✅ Weekly report sent to Google Chat")
    
    def _load_week_metrics(self, weeks_ago: int = 0) -> dict:
        """Load aggregated metrics for a given week."""
        start_date = datetime.utcnow() - timedelta(weeks=weeks_ago+1)
        end_date = datetime.utcnow() - timedelta(weeks=weeks_ago)
        
        aggregated = {
            "platforms": {
                "x": {"total_engagement": 0, "posts": 0},
                "instagram": {"total_engagement": 0, "posts": 0},
                "tiktok": {"total_engagement": 0, "posts": 0},
                "linkedin": {"total_engagement": 0, "posts": 0},
                "reddit": {"total_engagement": 0, "posts": 0}
            }
        }
        
        # Load all metrics files in date range
        for metrics_file in self.metrics_dir.glob("*.json"):
            try:
                file_date = datetime.strptime(metrics_file.stem, "%Y-%m-%d")
                
                if start_date <= file_date <= end_date:
                    metrics = json.loads(metrics_file.read_text())
                    
                    for platform, data in metrics["platforms"].items():
                        aggregated["platforms"][platform]["total_engagement"] += data.get("total_engagement", 0)
                        aggregated["platforms"][platform]["posts"] += len(data.get("posts", []))
            
            except Exception as e:
                print(f"Error loading metrics file {metrics_file}: {e}")
        
        return aggregated
    
    def _calculate_growth(self, this_week: dict, last_week: dict) -> dict:
        """Calculate week-over-week growth."""
        growth = {}
        
        for platform in this_week["platforms"]:
            this_engagement = this_week["platforms"][platform]["total_engagement"]
            last_engagement = last_week["platforms"][platform]["total_engagement"]
            
            if last_engagement > 0:
                pct_change = ((this_engagement - last_engagement) / last_engagement) * 100
            else:
                pct_change = 0 if this_engagement == 0 else 100
            
            growth[platform] = {
                "absolute": this_engagement - last_engagement,
                "percent": round(pct_change, 1)
            }
        
        return growth
    
    def _format_report(self, this_week: dict, growth: dict) -> dict:
        """Format report as Google Chat card."""
        sections = []
        
        # Summary section
        total_engagement = sum(
            p["total_engagement"] 
            for p in this_week["platforms"].values()
        )
        total_posts = sum(
            p["posts"] 
            for p in this_week["platforms"].values()
        )
        
        sections.append({
            "header": "📊 Weekly Social Media Report",
            "widgets": [
                {
                    "keyValue": {
                        "topLabel": "Total Engagement",
                        "content": str(total_engagement),
                        "icon": "STAR"
                    }
                },
                {
                    "keyValue": {
                        "topLabel": "Total Posts",
                        "content": str(total_posts),
                        "icon": "DESCRIPTION"
                    }
                }
            ]
        })
        
        # Per-platform breakdown
        platform_widgets = []
        for platform, data in this_week["platforms"].items():
            if data["posts"] > 0:  # Only show active platforms
                growth_indicator = "🔺" if growth[platform]["percent"] > 0 else "🔻"
                
                platform_widgets.append({
                    "keyValue": {
                        "topLabel": platform.upper(),
                        "content": f"{data['total_engagement']} engagement ({data['posts']} posts)",
                        "bottomLabel": f"{growth_indicator} {growth[platform]['percent']}% vs last week"
                    }
                })
        
        sections.append({
            "header": "Platform Breakdown",
            "widgets": platform_widgets
        })
        
        return {
            "cards": [
                {
                    "sections": sections
                }
            ]
        }
    
    async def _send_to_google_chat(self, report: dict):
        """Send report to Google Chat webhook."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.webhook_url,
                json=report
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to send report: {response.text}")


async def main():
    """Generate and send weekly report."""
    from config.settings import SECRETS
    
    data_dir = Path("./data/memory")
    webhook_url = SECRETS["GOOGLE_CHAT_WEBHOOK"]
    
    generator = WeeklyReportGenerator(data_dir, webhook_url)
    
    print("📧 Generating weekly report...")
    await generator.generate_and_send()


if __name__ == "__main__":
    asyncio.run(main())
```

**Schedule Metrics Collection:**

```python
# Add to core/scheduler/cron.py

async def _execute_job(self, job: Dict):
    """Execute a single job."""
    job_type = job["job_type"]
    
    # ... existing code ...
    
    elif job_type == "collect_metrics":
        await self._execute_collect_metrics(job)
    
    elif job_type == "send_weekly_report":
        await self._execute_send_weekly_report(job)
    
    # ... rest of code ...

async def _execute_collect_metrics(self, job: Dict):
    """Execute metrics collection job."""
    from scripts.collect_metrics import MetricsCollector
    
    collector = MetricsCollector(self.agent_state.memory_dir)
    await collector.collect_all()

async def _execute_send_weekly_report(self, job: Dict):
    """Execute weekly report job."""
    from scripts.generate_report import WeeklyReportGenerator
    from config.settings import SECRETS
    
    generator = WeeklyReportGenerator(
        self.agent_state.memory_dir,
        SECRETS["GOOGLE_CHAT_WEBHOOK"]
    )
    await generator.generate_and_send()
```

**Schedule Jobs on Agent Start:**

```python
# Add to core/agent.py

async def start(self):
    """Start agent and schedule recurring jobs."""
    # ... existing start logic ...
    
    # Schedule daily metrics collection (every day at 11pm)
    await self._schedule_daily_metrics()
    
    # Schedule weekly report (every Monday at 9am)
    await self._schedule_weekly_report()

async def _schedule_daily_metrics(self):
    """Schedule daily metrics collection."""
    from datetime import time
    
    next_run = datetime.combine(
        datetime.utcnow().date() + timedelta(days=1),
        time(hour=23, minute=0)  # 11pm UTC
    )
    
    await self.scheduler.schedule_job(
        job_type="collect_metrics",
        schedule_at=next_run,
        payload={}
    )

async def _schedule_weekly_report(self):
    """Schedule weekly report every Monday."""
    from datetime import time
    
    today = datetime.utcnow()
    days_until_monday = (7 - today.weekday()) % 7  # 0 = Monday
    if days_until_monday == 0:
        days_until_monday = 7  # Next Monday, not today
    
    next_monday = datetime.combine(
        today.date() + timedelta(days=days_until_monday),
        time(hour=9, minute=0)  # 9am UTC
    )
    
    await self.scheduler.schedule_job(
        job_type="send_weekly_report",
        schedule_at=next_monday,
        payload={}
    )
```

**Test Cases:**

```python
# tests/scripts/test_metrics_collection.py

async def test_collect_x_metrics():
    """Collect metrics from X/Twitter."""
    collector = MetricsCollector(data_dir)
    
    # Create mock posts
    _create_mock_posts("x", count=5)
    
    metrics = await collector.collect_x_metrics()
    
    assert "posts" in metrics
    assert "total_engagement" in metrics
    assert len(metrics["posts"]) == 5


async def test_weekly_report_generation():
    """Generate weekly report."""
    generator = WeeklyReportGenerator(data_dir, "https://mock-webhook")
    
    # Create mock metrics for 2 weeks
    _create_mock_metrics(weeks=2)
    
    report = generator._format_report(
        this_week=mock_this_week,
        growth=mock_growth
    )
    
    assert "cards" in report
    assert len(report["cards"]) > 0


async def test_growth_calculation():
    """Calculate week-over-week growth."""
    generator = WeeklyReportGenerator(data_dir, "https://mock-webhook")
    
    this_week = {"platforms": {"x": {"total_engagement": 150, "posts": 5}}}
    last_week = {"platforms": {"x": {"total_engagement": 100, "posts": 5}}}
    
    growth = generator._calculate_growth(this_week, last_week)
    
    assert growth["x"]["absolute"] == 50
    assert growth["x"]["percent"] == 50.0
```

**Critical Notes:**
- Metrics collection runs **daily at 11pm** to capture full day's data
- Weekly report sent **Monday at 9am** with previous week's data
- Store post IDs when posting (need to modify post-content skill)
- Rate limits: Be careful not to hammer platform APIs for metrics
- Consider caching metrics to avoid re-fetching

---

## Task 4.2.2: Modify Post Content to Store Post IDs

**Files to Modify:**
- `skills/post-content/post_content.py` - Save post data after successful posting

**Implementation:**

```python
# In skills/post-content/post_content.py

async def post_content(agent_state: AgentState, ...):
    """Post content to platform."""
    
    # ... existing posting logic ...
    
    if result.success:
        # Store post data for metrics collection
        await _store_post_data(
            agent_state.memory_dir,
            platform=platform,
            post_id=result.post_id,
            post_url=result.post_url,
            content=post_data["content"],
            posted_at=datetime.utcnow().isoformat()
        )

async def _store_post_data(
    memory_dir: Path,
    platform: str,
    post_id: str,
    post_url: str,
    content: str,
    posted_at: str
):
    """Store post data for future metrics collection."""
    posts_dir = memory_dir / "posts" / platform
    posts_dir.mkdir(parents=True, exist_ok=True)
    
    post_data = {
        "post_id": post_id,
        "post_url": post_url,
        "content": content[:100],  # Truncate for storage
        "posted_at": posted_at,
        "platform": platform
    }
    
    # Save with timestamp in filename
    filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{post_id}.json"
    (posts_dir / filename).write_text(json.dumps(post_data, indent=2))
```

---

## Final Verification

**Deployment:**
- [ ] Dockerfile builds successfully
- [ ] deploy.sh runs without errors
- [ ] Service deploys to Cloud Run
- [ ] Health endpoint returns 200
- [ ] All secrets loaded from Secret Manager
- [ ] Service scales to zero when idle
- [ ] Logs appear in Cloud Logging

**Metrics:**
- [ ] Metrics collection script runs successfully
- [ ] Metrics saved to data/metrics/{date}.json
- [ ] Weekly report generates correctly
- [ ] Report sent to Google Chat
- [ ] All platforms' metrics collected
- [ ] Growth calculation accurate

**Documentation:**
- [ ] README has clear deployment instructions
- [ ] SECRETS.md documents all required secrets
- [ ] Pre-deployment checklist complete
- [ ] Post-deployment verification steps documented
- [ ] Rollback procedure documented

**Production Readiness:**
- [ ] Error handling in all scripts
- [ ] Graceful shutdown implemented
- [ ] Logs structured (JSON format)
- [ ] Health checks passing
- [ ] Secrets never in code
- [ ] .env never committed
- [ ] All API keys in Secret Manager

---

## Post-Implementation Notes

After completing Sprint 4, you'll have:
- ✅ Automated deployment to GCP Cloud Run
- ✅ Complete deployment documentation
- ✅ Engagement metrics collection
- ✅ Weekly reporting to Google Chat
- ✅ Production-ready configuration

**Congratulations!** 🎉

The Marketing Campaign Manager is complete and ready for production use. You now have a fully automated social media agent that can:

1. Generate content across 5 platforms
2. Request approval before posting
3. Post automatically at scheduled times
4. Plan and execute multi-week campaigns
5. Collect engagement metrics
6. Send weekly performance reports

## Next Steps (Post-MVP)

Future enhancements to consider:
- A/B testing for content variations
- AI-powered engagement prediction
- Automated response to comments
- Content performance analysis and recommendations
- Multi-language support
- Analytics dashboard
- Campaign templates library
