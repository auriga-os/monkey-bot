---
name: analyze-competitor
description: Analyze a competitor's website or blog to understand their content strategy, posting frequency, topics, and style. Use when researching competitors or finding content gaps.
metadata:
  emonk:
    requires:
      bins: []
      files: []
---

# Analyze Competitor

Scrape and analyze competitor content using Firecrawl.

## When to Use This Skill

Invoke this skill when the user:
- Says "analyze [competitor name]'s blog"
- Requests "what is [company] posting about?"
- Says "check out [url] and tell me their content strategy"
- Wants competitive intelligence for content planning
- Needs to identify content gaps or opportunities

## Parameters

- `competitor_url` (required): URL to analyze (blog, website, social profile)
- `sections` (optional): Specific sections to scrape (e.g., ["blog", "about"])

## Success Criteria

A good analysis includes:
- ✅ Main topics discussed
- ✅ Content tone and style
- ✅ Posting frequency estimate
- ✅ Unique angles or approaches
- ✅ Opportunities for differentiation

## Example Usage

```bash
python3 skills/analyze-competitor/analyze_competitor.py \
  --competitor-url "https://competitor-blog.com" \
  --sections blog about
```

## Output Format

```json
{
  "url": "https://competitor-blog.com",
  "analysis": {
    "main_topics": ["AI", "automation", "marketing"],
    "content_style": "professional, technical, with case studies",
    "posting_frequency": "2-3 times per week",
    "unique_angles": ["Focus on SMB use cases", "Heavy data-driven content"],
    "opportunities": ["More beginner-friendly content", "Video tutorials"]
  },
  "scraped_at": "2026-02-11T10:30:00Z"
}
```

## Notes

- Respects robots.txt and rate limits
- Some sites may block scrapers (handles 403/429 gracefully)
- Results are cached to reduce API calls
- Production: Requires Firecrawl API key
