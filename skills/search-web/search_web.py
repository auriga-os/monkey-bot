#!/usr/bin/env python3
"""
Search the web for current information using Perplexity AI.

This skill wraps the Perplexity MCP server to provide web search capabilities.
"""

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass
from typing import List, Literal, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result."""
    title: str
    snippet: str
    url: str
    published_date: Optional[str] = None


@dataclass
class SearchResponse:
    """Response from web search."""
    query: str
    results: List[SearchResult]
    count: int


def search_web(
    query: str,
    limit: int = 10,
    recency: Optional[Literal["day", "week", "month", "year"]] = None
) -> SearchResponse:
    """
    Search the web using Perplexity AI.

    For MVP, this is a PLACEHOLDER that returns mock data.
    In production, this will call the Perplexity MCP server.

    Args:
        query: Search query string
        limit: Maximum number of results (default 10, max 20)
        recency: Optional time filter ("day", "week", "month", "year")

    Returns:
        SearchResponse with query, results, and count

    Raises:
        ValueError: If query is empty or limit is invalid
        RuntimeError: If MCP server call fails

    Notes:
        - MVP: Returns mock data for testing
        - Production: Call Perplexity MCP server
        - API key: Load from environment (PERPLEXITY_API_KEY)

    Example:
        >>> result = search_web("AI agents 2026", limit=5, recency="week")
        >>> print(result.count)
        5
        >>> print(result.results[0].title)
        'Latest AI Agent Developments'
    """
    # Validate query
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    # Validate and clamp limit
    if limit < 1:
        raise ValueError("Limit must be at least 1")
    limit = min(limit, 20)  # Max 20 results

    # Validate recency filter
    valid_recency = ["day", "week", "month", "year", None]
    if recency not in valid_recency:
        raise ValueError(
            f"Invalid recency filter: {recency}. "
            f"Must be one of: day, week, month, year"
        )

    # PLACEHOLDER: Mock Perplexity MCP response
    # TODO: Replace with real Perplexity MCP call
    """
    Production implementation:

    import os
    from mcp_client import MCPClient

    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY not found in environment")

    mcp_client = MCPClient()
    results = mcp_client.call_tool(
        server="perplexity",
        tool="search",
        arguments={
            "query": query,
            "limit": limit,
            "recency": recency
        }
    )

    search_results = [
        SearchResult(
            title=r["title"],
            snippet=r["snippet"],
            url=r["url"],
            published_date=r.get("published_date")
        )
        for r in results
    ]

    return SearchResponse(
        query=query,
        results=search_results,
        count=len(search_results)
    )
    """

    logger.info(
        "[PLACEHOLDER] Would search web via Perplexity",
        extra={
            "query": query,
            "limit": limit,
            "recency": recency
        },
    )

    # Mock search results for MVP testing
    mock_results = [
        SearchResult(
            title=f"Article {i+1}: {query}",
            snippet=f"This article discusses {query} in detail, covering recent developments and trends.",
            url=f"https://example.com/article-{i+1}",
            published_date="2026-02-10" if recency else None
        )
        for i in range(min(limit, 10))  # Return up to limit results
    ]

    return SearchResponse(
        query=query,
        results=mock_results,
        count=len(mock_results)
    )


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Search the web using Perplexity AI")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max results (default 10, max 20)"
    )
    parser.add_argument(
        "--recency",
        choices=["day", "week", "month", "year"],
        help="Time filter (day, week, month, year)"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    try:
        response = search_web(
            query=args.query,
            limit=args.limit,
            recency=args.recency
        )

        if args.json:
            # Convert to dict and serialize
            output = {
                "query": response.query,
                "results": [asdict(r) for r in response.results],
                "count": response.count
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"\n🔍 Search Results for: {response.query}")
            print(f"Found {response.count} results\n")
            
            for i, result in enumerate(response.results, 1):
                print(f"{i}. {result.title}")
                print(f"   {result.snippet}")
                print(f"   {result.url}")
                if result.published_date:
                    print(f"   Published: {result.published_date}")
                print()

        sys.exit(0)

    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        sys.exit(1)
    except RuntimeError as e:
        logger.error(f"Search failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
