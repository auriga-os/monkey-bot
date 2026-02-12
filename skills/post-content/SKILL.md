---
name: post-content
description: Publish approved content to social media platforms (X/Twitter). Requires content to be pre-approved. Returns live post URL. Use when user wants to post, publish, or go live.
metadata:
  emonk:
    requires:
      bins: ["python3"]
      files: ["./data/memory/approvals/"]
---

# Post Content to Social Media

Publishes content to X (Twitter) using platform API.

## When to Use This Skill

Invoke when user:
- Says "post this to X"
- Says "publish to Twitter"
- Says "go live on X"
- Has already approved content

## Parameters

- `content` (required): Post content (text)
- `platform` (required): Target platform ("x" only for MVP)
- `media_urls` (optional): List of image/video URLs
- `approval_id` (optional): Reference to approval record

## Pre-Posting Validation

Before posting, verify:
1. Content was approved (approval_id must exist)
2. X API key exists in environment
3. Content meets platform requirements (≤280 chars)

## Example Usage

```bash
python3 skills/post-content/post_content.py \
  --content "Check out this post! #AI" \
  --platform x \
  --approval-id abc-123-def
```
