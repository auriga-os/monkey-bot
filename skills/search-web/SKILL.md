---
name: search-web
description: Search the web for current information, articles, and trends using Perplexity AI. Use when researching topics, finding recent news, or gathering data for content creation.
metadata:
  emonk:
    requires:
      bins: []
      files: []
---

# Search Web

Search the web for real-time information using Perplexity AI.

## When to Use This Skill

Invoke this skill when the user:
- Says "search for articles about [topic]"
- Requests "what's trending in [topic]?"
- Says "find recent news about [topic]"
- Requests "research [topic] for me"
- Wants to find information for content creation

## Parameters

- `query` (required): Search query string
- `limit` (optional): Maximum number of results to return (default: 10, max: 20)
- `recency` (optional): Filter by time period ("day", "week", "month", "year")

## Success Criteria

A good search result has:
- ✅ Relevant articles and sources
- ✅ Up-to-date information (if recency filter applied)
- ✅ Varied sources for balanced perspective
- ✅ Clear titles and snippets
- ✅ Source URLs for citation

## Recency Options

| Recency | Description |
|---------|-------------|
| day | Past 24 hours |
| week | Past 7 days |
| month | Past 30 days |
| year | Past 365 days |
| (none) | All time |

## Example Usage

```bash
python3 skills/search-web/search_web.py \
  --query "AI agents 2026" \
  --limit 10 \
  --recency week
```

## Output Format

```json
{
  "query": "AI agents 2026",
  "results": [
    {
      "title": "Article title",
      "snippet": "Brief description...",
      "url": "https://example.com/article",
      "published_date": "2026-02-01"
    }
  ],
  "count": 10
}
```
