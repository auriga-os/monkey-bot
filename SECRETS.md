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

### Vertex AI & Auth
```bash
echo -n "your-project-id" | gcloud secrets create vertex-ai-project-id --data-file=-
echo -n "user1@example.com,user2@example.com" | gcloud secrets create allowed-users --data-file=-
```

## Grant Access to Cloud Run

```bash
# For each secret, grant access to Cloud Run service account
gcloud secrets add-iam-policy-binding SECRET_NAME \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## Verify Secrets

```bash
# List all secrets
gcloud secrets list

# View a secret value
gcloud secrets versions access latest --secret="google-chat-webhook"
```
