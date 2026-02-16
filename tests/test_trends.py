"""Tests for trends/seasonal module.

Tests cover:
- get_seasonal_theme: date matching (single day, range, no match)
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.trends.seasonal import get_seasonal_theme


MOCK_THEMES = [
    {
        "theme": "Valentine's Day",
        "date_range": "02-14",
        "story_angles": ["Love stories", "Gift giving"],
    },
    {
        "theme": "Holiday Season",
        "date_range": "12-20:12-31",
        "story_angles": ["Gift exchange", "Holiday party"],
    },
    {
        "theme": "Summer Vibes",
        "date_range": "06-01:08-31",
        "story_angles": ["Beach day", "Ice cream"],
    },
]


class TestGetSeasonalTheme:
    """Test seasonal theme date matching."""

    @patch("src.trends.seasonal._load_seasonal_themes", return_value=MOCK_THEMES)
    def test_single_day_match(self, mock_themes):
        date = datetime(2026, 2, 14)
        result = get_seasonal_theme(date)
        assert result is not None
        assert result["theme"] == "Valentine's Day"
        assert "Love stories" in result["story_angles"]

    @patch("src.trends.seasonal._load_seasonal_themes", return_value=MOCK_THEMES)
    def test_range_start(self, mock_themes):
        date = datetime(2026, 12, 20)
        result = get_seasonal_theme(date)
        assert result is not None
        assert result["theme"] == "Holiday Season"

    @patch("src.trends.seasonal._load_seasonal_themes", return_value=MOCK_THEMES)
    def test_range_end(self, mock_themes):
        date = datetime(2026, 12, 31)
        result = get_seasonal_theme(date)
        assert result is not None
        assert result["theme"] == "Holiday Season"

    @patch("src.trends.seasonal._load_seasonal_themes", return_value=MOCK_THEMES)
    def test_range_middle(self, mock_themes):
        date = datetime(2026, 7, 15)
        result = get_seasonal_theme(date)
        assert result is not None
        assert result["theme"] == "Summer Vibes"

    @patch("src.trends.seasonal._load_seasonal_themes", return_value=MOCK_THEMES)
    def test_no_match(self, mock_themes):
        date = datetime(2026, 3, 15)
        result = get_seasonal_theme(date)
        assert result is None

    @patch("src.trends.seasonal._load_seasonal_themes", return_value=MOCK_THEMES)
    def test_day_before_single(self, mock_themes):
        date = datetime(2026, 2, 13)
        result = get_seasonal_theme(date)
        assert result is None

    @patch("src.trends.seasonal._load_seasonal_themes", return_value=MOCK_THEMES)
    def test_day_after_single(self, mock_themes):
        date = datetime(2026, 2, 15)
        result = get_seasonal_theme(date)
        assert result is None

    @patch("src.trends.seasonal._load_seasonal_themes", return_value=[])
    def test_empty_themes(self, mock_themes):
        result = get_seasonal_theme(datetime(2026, 2, 14))
        assert result is None

    @patch("src.trends.seasonal._load_seasonal_themes", return_value=MOCK_THEMES)
    def test_returns_story_angles(self, mock_themes):
        result = get_seasonal_theme(datetime(2026, 7, 1))
        assert "story_angles" in result
        assert isinstance(result["story_angles"], list)
        assert len(result["story_angles"]) > 0
