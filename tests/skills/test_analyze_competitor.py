"""Tests for analyze-competitor skill."""

import pytest
from pathlib import Path
import sys
from datetime import datetime

# Add skills directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "analyze-competitor"))

from analyze_competitor import (
    analyze_competitor,
    AnalysisResponse,
    CompetitorAnalysis
)


class TestAnalyzeCompetitor:
    """Tests for competitor analysis skill."""

    def test_analyze_success(self):
        """Test: Analyzing valid URL returns results."""
        result = analyze_competitor("https://competitor-blog.com")

        assert isinstance(result, AnalysisResponse)
        assert result.url == "https://competitor-blog.com"
        assert isinstance(result.analysis, CompetitorAnalysis)
        assert result.scraped_at
        
        # Check timestamp format (ISO 8601)
        datetime.fromisoformat(result.scraped_at.rstrip("Z"))

    def test_analyze_with_sections(self):
        """Test: Analyzing with specific sections works."""
        result = analyze_competitor(
            "https://example.com/blog",
            sections=["blog", "about"]
        )

        assert result.url == "https://example.com/blog"
        assert result.analysis

    def test_analyze_empty_url(self):
        """Test: Empty URL raises ValueError."""
        with pytest.raises(ValueError, match="Competitor URL cannot be empty"):
            analyze_competitor("")

    def test_analyze_whitespace_url(self):
        """Test: Whitespace-only URL raises ValueError."""
        with pytest.raises(ValueError, match="Competitor URL cannot be empty"):
            analyze_competitor("   \n\t  ")

    def test_analyze_invalid_url_protocol(self):
        """Test: URL without http/https raises ValueError."""
        with pytest.raises(ValueError, match="must start with http"):
            analyze_competitor("competitor-blog.com")

    def test_analyze_http_url(self):
        """Test: HTTP URL is accepted."""
        result = analyze_competitor("http://competitor-blog.com")
        assert result.url == "http://competitor-blog.com"

    def test_analyze_https_url(self):
        """Test: HTTPS URL is accepted."""
        result = analyze_competitor("https://competitor-blog.com")
        assert result.url == "https://competitor-blog.com"

    def test_analysis_structure(self):
        """Test: Analysis has correct structure."""
        result = analyze_competitor("https://example.com")
        analysis = result.analysis

        assert hasattr(analysis, "main_topics")
        assert hasattr(analysis, "content_style")
        assert hasattr(analysis, "posting_frequency")
        assert hasattr(analysis, "unique_angles")
        assert hasattr(analysis, "opportunities")

        assert isinstance(analysis.main_topics, list)
        assert isinstance(analysis.content_style, str)
        assert isinstance(analysis.posting_frequency, str)
        assert isinstance(analysis.unique_angles, list)
        assert isinstance(analysis.opportunities, list)

    def test_main_topics_not_empty(self):
        """Test: Main topics list is populated."""
        result = analyze_competitor("https://example.com")
        
        assert len(result.analysis.main_topics) > 0
        assert all(isinstance(topic, str) for topic in result.analysis.main_topics)

    def test_content_style_not_empty(self):
        """Test: Content style is provided."""
        result = analyze_competitor("https://example.com")
        
        assert result.analysis.content_style
        assert len(result.analysis.content_style) > 0

    def test_unique_angles_not_empty(self):
        """Test: Unique angles are identified."""
        result = analyze_competitor("https://example.com")
        
        assert len(result.analysis.unique_angles) > 0
        assert all(isinstance(angle, str) for angle in result.analysis.unique_angles)

    def test_opportunities_not_empty(self):
        """Test: Opportunities are identified."""
        result = analyze_competitor("https://example.com")
        
        assert len(result.analysis.opportunities) > 0
        assert all(isinstance(opp, str) for opp in result.analysis.opportunities)

    def test_timestamp_recent(self):
        """Test: Timestamp is recent (within last minute)."""
        result = analyze_competitor("https://example.com")
        
        scraped_time = datetime.fromisoformat(result.scraped_at.rstrip("Z"))
        now = datetime.utcnow()
        
        # Should be within 1 minute
        time_diff = (now - scraped_time).total_seconds()
        assert time_diff < 60
