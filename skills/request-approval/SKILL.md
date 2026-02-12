---
name: request-approval
description: Send content to Google Chat for user approval before posting. Returns approved/rejected status with optional feedback. Use when user wants to review content before it goes live.
metadata:
  emonk:
    requires:
      bins: ["python3"]
      files: ["./data/memory/approvals/"]
---

# Request Approval for Content

Sends content to Google Chat with interactive Approve/Reject/Modify buttons.

## When to Use This Skill

Invoke when user:
- Says "send this for approval"
- Wants to "review before posting"
- Says "let me see it first"
- Says "get my approval"

## Parameters

- `content` (required): The content to approve
- `content_type` (required): Type ("social_post", "campaign", "image")
- `platform` (optional): Platform if social post
- `timeout_seconds` (optional): Approval timeout (default: 3600 = 1 hour)

## Example Usage

```bash
python3 skills/request-approval/request_approval.py \
  --content "Check out this post..." \
  --content-type social_post \
  --platform instagram
```
