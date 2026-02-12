"""Tests for search-web skill."""

import pytest
from pathlib import Path
import sys

# Add skills directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "search-web"))

from search_web import search_web, SearchResponse, SearchResult


class TestSearchWeb:
    """Tests for web search skill."""

    def test_search_basic(self):
        """Test: Basic search returns results."""
        result = search_web("AI agents")

        assert isinstance(result, SearchResponse)
        assert result.query == "AI agents"
        assert result.count > 0
        assert len(result.results) == result.count
        assert all(isinstance(r, SearchResult) for r in result.results)

    def test_search_with_limit(self):
        """Test: Limit parameter is respected."""
        result = search_web("machine learning", limit=5)

        assert result.count <= 5
        assert len(result.results) <= 5

    def test_search_with_recency(self):
        """Test: Recency filter is accepted."""
        result = search_web("tech news", limit=10, recency="week")

        assert result.query == "tech news"
        assert result.count > 0
        # Mock results should have published_date when recency is set
        assert any(r.published_date is not None for r in result.results)

    def test_search_empty_query(self):
        """Test: Empty query raises ValueError."""
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            search_web("")

    def test_search_whitespace_only_query(self):
        """Test: Whitespace-only query raises ValueError."""
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            search_web("   \n\t  ")

    def test_search_limit_too_low(self):
        """Test: Limit < 1 raises ValueError."""
        with pytest.raises(ValueError, match="Limit must be at least 1"):
            search_web("test", limit=0)

    def test_search_limit_clamped_at_20(self):
        """Test: Limit > 20 is clamped to 20."""
        result = search_web("test", limit=100)

        # Should be clamped to max 20
        assert result.count <= 20

    def test_search_invalid_recency(self):
        """Test: Invalid recency filter raises ValueError."""
        with pytest.raises(ValueError, match="Invalid recency filter"):
            search_web("test", recency="hour")  # type: ignore

    def test_search_recency_day(self):
        """Test: Recency 'day' filter accepted."""
        result = search_web("test", recency="day")
        assert result.count > 0

    def test_search_recency_week(self):
        """Test: Recency 'week' filter accepted."""
        result = search_web("test", recency="week")
        assert result.count > 0

    def test_search_recency_month(self):
        """Test: Recency 'month' filter accepted."""
        result = search_web("test", recency="month")
        assert result.count > 0

    def test_search_recency_year(self):
        """Test: Recency 'year' filter accepted."""
        result = search_web("test", recency="year")
        assert result.count > 0

    def test_search_result_structure(self):
        """Test: Search results have correct structure."""
        result = search_web("test query", limit=1)

        assert len(result.results) >= 1
        first_result = result.results[0]
        
        assert hasattr(first_result, "title")
        assert hasattr(first_result, "snippet")
        assert hasattr(first_result, "url")
        assert hasattr(first_result, "published_date")
        
        assert isinstance(first_result.title, str)
        assert isinstance(first_result.snippet, str)
        assert isinstance(first_result.url, str)
        assert first_result.url.startswith("http")

    def test_search_response_matches_count(self):
        """Test: Response count matches number of results."""
        result = search_web("test", limit=7)

        assert result.count == len(result.results)
