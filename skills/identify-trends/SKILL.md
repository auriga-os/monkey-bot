---
name: identify-trends
description: Identify trending topics, keywords, and content opportunities in a given subject area by aggregating multiple web searches and analyzing patterns.
metadata:
  emonk:
    requires:
      bins: []
      files: []
---

# Identify Trends

Find what's trending in a topic area by analyzing aggregated search results.

## When to Use This Skill

Invoke this skill when the user:
- Says "what's trending in [topic]?"
- Requests "identify trends in [topic]"
- Says "what should I write about for [topic]?"
- Requests "find trending topics in [industry]"
- Wants content ideas based on current trends

## Parameters

- `topic` (required): Topic area to research (e.g., "AI", "social media marketing")
- `time_range` (optional): How far back to search ("day", "week", "month") - default: "week"

## Success Criteria

A good trend analysis includes:
- ✅ Top 5 trending topics with explanations
- ✅ Emerging themes and patterns
- ✅ Popular keywords and hashtags
- ✅ Content opportunities (gaps to fill)
- ✅ Source count for confidence

## Time Range Options

| Time Range | Description |
|------------|-------------|
| day | Past 24 hours |
| week | Past 7 days (default) |
| month | Past 30 days |

## Example Usage

```bash
python3 skills/identify-trends/identify_trends.py \
  --topic "AI agents" \
  --time-range week
```

## Output Format

```json
{
  "topic": "AI agents",
  "time_range": "week",
  "trends": {
    "trending_topics": [
      {
        "topic": "Multi-agent systems",
        "explanation": "Growing interest in coordinating multiple AI agents"
      }
    ],
    "emerging_themes": ["Autonomous workflows", "Agent collaboration"],
    "popular_keywords": ["#aiagents", "#automation", "#llm"],
    "content_opportunities": ["Tutorial: Building your first agent"]
  },
  "source_count": 50
}
```

## Notes

- Makes multiple search-web calls (5+ searches)
- Consider caching results (trends don't change hourly)
- LLM prompt engineering is critical for quality
- Watch API costs due to multiple searches
