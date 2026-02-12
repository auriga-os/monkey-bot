"""Tests for identify-trends skill."""

import pytest
from pathlib import Path
import sys

# Add skills directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "identify-trends"))

from identify_trends import (
    identify_trends,
    TrendsResponse,
    TrendAnalysis,
    TrendingTopic
)


class TestIdentifyTrends:
    """Tests for trend identification skill."""

    def test_identify_trends_success(self):
        """Test: Identifying trends returns results."""
        result = identify_trends("AI agents")

        assert isinstance(result, TrendsResponse)
        assert result.topic == "AI agents"
        assert result.time_range == "week"  # default
        assert isinstance(result.trends, TrendAnalysis)
        assert result.source_count > 0

    def test_identify_trends_with_time_range(self):
        """Test: Time range parameter is respected."""
        result = identify_trends("machine learning", time_range="day")

        assert result.topic == "machine learning"
        assert result.time_range == "day"

    def test_identify_trends_empty_topic(self):
        """Test: Empty topic raises ValueError."""
        with pytest.raises(ValueError, match="Topic cannot be empty"):
            identify_trends("")

    def test_identify_trends_whitespace_topic(self):
        """Test: Whitespace-only topic raises ValueError."""
        with pytest.raises(ValueError, match="Topic cannot be empty"):
            identify_trends("   \n\t  ")

    def test_identify_trends_invalid_time_range(self):
        """Test: Invalid time_range raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time_range"):
            identify_trends("test", time_range="hour")  # type: ignore

    def test_identify_trends_day_range(self):
        """Test: Time range 'day' accepted."""
        result = identify_trends("test", time_range="day")
        assert result.time_range == "day"

    def test_identify_trends_week_range(self):
        """Test: Time range 'week' accepted."""
        result = identify_trends("test", time_range="week")
        assert result.time_range == "week"

    def test_identify_trends_month_range(self):
        """Test: Time range 'month' accepted."""
        result = identify_trends("test", time_range="month")
        assert result.time_range == "month"

    def test_trending_topics_structure(self):
        """Test: Trending topics have correct structure."""
        result = identify_trends("test")

        assert len(result.trends.trending_topics) > 0
        
        for topic in result.trends.trending_topics:
            assert isinstance(topic, TrendingTopic)
            assert hasattr(topic, "topic")
            assert hasattr(topic, "explanation")
            assert isinstance(topic.topic, str)
            assert isinstance(topic.explanation, str)
            assert len(topic.topic) > 0
            assert len(topic.explanation) > 0

    def test_trending_topics_count(self):
        """Test: Returns top 5 trending topics."""
        result = identify_trends("test")

        # Should have 5 trending topics (as per spec)
        assert len(result.trends.trending_topics) == 5

    def test_emerging_themes_not_empty(self):
        """Test: Emerging themes are identified."""
        result = identify_trends("test")

        assert len(result.trends.emerging_themes) > 0
        assert all(isinstance(theme, str) for theme in result.trends.emerging_themes)
        assert all(len(theme) > 0 for theme in result.trends.emerging_themes)

    def test_popular_keywords_not_empty(self):
        """Test: Popular keywords are identified."""
        result = identify_trends("test")

        assert len(result.trends.popular_keywords) > 0
        assert all(isinstance(kw, str) for kw in result.trends.popular_keywords)

    def test_content_opportunities_not_empty(self):
        """Test: Content opportunities are identified."""
        result = identify_trends("test")

        assert len(result.trends.content_opportunities) > 0
        assert all(isinstance(opp, str) for opp in result.trends.content_opportunities)
        assert all(len(opp) > 0 for opp in result.trends.content_opportunities)

    def test_analysis_structure_complete(self):
        """Test: Analysis has all required fields."""
        result = identify_trends("test")
        analysis = result.trends

        assert hasattr(analysis, "trending_topics")
        assert hasattr(analysis, "emerging_themes")
        assert hasattr(analysis, "popular_keywords")
        assert hasattr(analysis, "content_opportunities")

    def test_source_count_positive(self):
        """Test: Source count is positive."""
        result = identify_trends("test")

        assert result.source_count > 0
