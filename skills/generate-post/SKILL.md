---
name: generate-post
description: Create social media content for any platform (Instagram, TikTok, X, LinkedIn, Reddit). Automatically validates character limits and brand voice. Use when user wants to create, write, draft, or generate a post.
metadata:
  emonk:
    requires:
      bins: []
      files: ["./data/memory/BRAND_VOICE.md"]
---

# Generate Social Media Post

Creates platform-specific social media content optimized for engagement.

## When to Use This Skill

Invoke this skill when the user:
- Wants to create a new social media post
- Says "write a post about [topic]"
- Requests "draft Instagram caption for [topic]"
- Says "generate content for X about [topic]"

## Parameters

- `topic` (required): What the post is about
- `platform` (required): Target platform ("instagram", "tiktok", "x", "linkedin", "reddit")
- `tone` (optional): Desired tone ("professional", "casual", "humorous")
- `include_hashtags` (optional): Whether to add hashtags (default: true)

## Success Criteria

A good post has:
- ✅ Appropriate length for platform
- ✅ Engaging hook in first line
- ✅ Clear call-to-action
- ✅ Platform-appropriate hashtags
- ✅ No forbidden brand voice phrases

## Platform Limits

| Platform | Character Limit | Hashtags |
|----------|----------------|----------|
| Instagram | 2200 | 3-5 |
| TikTok | 2200 | 3-5 |
| X | 280 | 1-2 |
| LinkedIn | 3000 | 3-5 |
| Reddit | 40000 | 0 (use flair) |

## Example Usage

```bash
python3 skills/generate-post/generate_post.py \
  --topic "AI agent evaluation" \
  --platform instagram \
  --tone professional
```
