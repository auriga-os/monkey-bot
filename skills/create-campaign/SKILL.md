---
name: create-campaign
description: Create a multi-week social media campaign with a content calendar, strategy, and post ideas. Use when planning comprehensive marketing campaigns across multiple platforms.
---

# create-campaign

Plan and structure social media campaigns.

## When to invoke

User says:
- "create a 4-week campaign about [topic]"
- "plan a campaign for [product launch]"
- "I need a content calendar for [topic]"
- "generate a marketing campaign about [theme]"

## Parameters

- `topic` (str, required): Campaign theme/topic
- `duration_weeks` (int, required): Campaign length in weeks
- `platforms` (list[str], required): Target platforms (instagram, x, tiktok, linkedin, reddit)
