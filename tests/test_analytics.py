"""Tests for analytics modules.

Tests cover:
- collector: _scores_to_weights (pure function)
- report_generator: format_discord_summary, _generate_recommendations (pure functions)
"""

import pytest

from src.analytics.collector import _scores_to_weights
from src.analytics.report_generator import format_discord_summary, _generate_recommendations


# ---------------------------------------------------------------------------
# _scores_to_weights
# ---------------------------------------------------------------------------

class TestScoresToWeights:
    """Test performance score → weight conversion."""

    def test_empty_scores_returns_existing(self):
        existing = {"pens": 1.0, "chubs": 1.2}
        result = _scores_to_weights({}, existing)
        assert result == existing

    def test_single_element_stays_near_1(self):
        scores = {"pens": [100]}
        result = _scores_to_weights(scores, {"pens": 1.0})
        # Single element → normalized to 1.0, blended 70% old + 30% new
        # 1.0 * 0.7 + 1.0 * 0.3 = 1.0
        assert 0.95 <= result["pens"] <= 1.05

    def test_high_performer_gets_higher_weight(self):
        scores = {"a": [200], "b": [50]}
        result = _scores_to_weights(scores, {"a": 1.0, "b": 1.0})
        assert result["a"] > result["b"]

    def test_weight_floor_at_0_5(self):
        scores = {"a": [1000], "b": [1]}
        result = _scores_to_weights(scores, {"a": 1.0, "b": 0.5})
        assert result["b"] >= 0.5

    def test_weight_ceiling_at_2_0(self):
        scores = {"a": [10000], "b": [1]}
        result = _scores_to_weights(scores, {"a": 2.0, "b": 1.0})
        assert result["a"] <= 2.0

    def test_blends_with_existing(self):
        """New weights should be 70% old + 30% new signal."""
        scores = {"pens": [100]}
        existing = {"pens": 1.5}
        result = _scores_to_weights(scores, existing)
        # normalized = 100 / 100 = 1.0
        # blended = 1.5 * 0.7 + 1.0 * 0.3 = 1.35
        assert abs(result["pens"] - 1.35) < 0.01

    def test_multiple_scores_averaged(self):
        scores = {"a": [100, 200, 300]}  # avg = 200
        result = _scores_to_weights(scores, {"a": 1.0})
        assert isinstance(result["a"], float)

    def test_preserves_unscored_elements(self):
        scores = {"a": [100]}
        existing = {"a": 1.0, "b": 1.2}
        result = _scores_to_weights(scores, existing)
        # b is not in scores, should be preserved
        assert result["b"] == 1.2

    def test_zero_scores_returns_existing(self):
        """If all scores are 0, overall_mean is 0 → returns existing."""
        scores = {"a": [0], "b": [0]}
        existing = {"a": 1.0, "b": 1.0}
        result = _scores_to_weights(scores, existing)
        assert result == existing


# ---------------------------------------------------------------------------
# _generate_recommendations
# ---------------------------------------------------------------------------

class TestGenerateRecommendations:
    """Test recommendation generation."""

    def test_no_episodes(self):
        summary = {"total_episodes": 0, "total_views": 0, "platform_breakdown": {}}
        result = _generate_recommendations(summary, {})
        assert len(result) == 1
        assert "no episodes" in result[0].lower()

    def test_no_views(self):
        summary = {"total_episodes": 5, "total_views": 0, "platform_breakdown": {}}
        result = _generate_recommendations(summary, {})
        assert any("no view data" in r.lower() for r in result)

    def test_underperforming_characters(self):
        summary = {
            "total_episodes": 5,
            "total_views": 100,
            "platform_breakdown": {
                "tiktok": {"views": 50},
                "youtube": {"views": 30},
                "instagram": {"views": 20},
            },
        }
        weights = {"character_weights": {"pens": 0.6, "chubs": 1.5}}
        result = _generate_recommendations(summary, weights)
        assert any("underperforming" in r.lower() for r in result)

    def test_platform_imbalance(self):
        summary = {
            "total_episodes": 5,
            "total_views": 100,
            "platform_breakdown": {
                "tiktok": {"views": 100},
                "youtube": {"views": 50},
                "instagram": {"views": 0},
            },
        }
        weights = {"character_weights": {}}
        result = _generate_recommendations(summary, weights)
        assert any("instagram" in r.lower() for r in result)

    def test_healthy_metrics(self):
        summary = {
            "total_episodes": 5,
            "total_views": 100,
            "platform_breakdown": {
                "tiktok": {"views": 40},
                "youtube": {"views": 30},
                "instagram": {"views": 30},
            },
        }
        weights = {"character_weights": {"pens": 1.0, "chubs": 1.1}}
        result = _generate_recommendations(summary, weights)
        assert any("healthy" in r.lower() for r in result)


# ---------------------------------------------------------------------------
# format_discord_summary
# ---------------------------------------------------------------------------

class TestFormatDiscordSummary:
    """Test Discord summary formatting."""

    def test_contains_report_header(self):
        report = {
            "report_date": "2026-01-01",
            "summary": {
                "total_episodes": 7,
                "total_views": 1000,
                "total_likes": 200,
                "total_comments": 50,
                "total_shares": 30,
            },
            "top_episodes": {"by_views": [], "by_engagement": []},
            "character_rankings": [],
            "recommendations": [],
        }
        result = format_discord_summary(report)
        assert "Weekly Analytics Report" in result
        assert "2026-01-01" in result

    def test_contains_stats(self):
        report = {
            "report_date": "2026-01-01",
            "summary": {
                "total_episodes": 7,
                "total_views": 1000,
                "total_likes": 200,
                "total_comments": 50,
                "total_shares": 30,
            },
            "top_episodes": {"by_views": [], "by_engagement": []},
            "character_rankings": [],
            "recommendations": [],
        }
        result = format_discord_summary(report)
        assert "1,000" in result  # formatted views
        assert "Episodes: 7" in result

    def test_contains_top_episodes(self):
        report = {
            "report_date": "2026-01-01",
            "summary": {
                "total_episodes": 3,
                "total_views": 500,
                "total_likes": 100,
                "total_comments": 20,
                "total_shares": 10,
            },
            "top_episodes": {
                "by_views": [{"episode_id": "EP001", "views": 300}],
                "by_engagement": [],
            },
            "character_rankings": [],
            "recommendations": [],
        }
        result = format_discord_summary(report)
        assert "EP001" in result
        assert "300" in result

    def test_contains_character_rankings(self):
        report = {
            "report_date": "2026-01-01",
            "summary": {
                "total_episodes": 3,
                "total_views": 500,
                "total_likes": 100,
                "total_comments": 20,
                "total_shares": 10,
            },
            "top_episodes": {"by_views": [], "by_engagement": []},
            "character_rankings": [
                {"name": "Pens", "weight": 1.2},
                {"name": "Chubs", "weight": 0.8},
            ],
            "recommendations": [],
        }
        result = format_discord_summary(report)
        assert "Pens" in result
        assert "Chubs" in result
        assert "[+]" in result  # Pens > 1.0
        assert "[-]" in result  # Chubs < 1.0

    def test_contains_recommendations(self):
        report = {
            "report_date": "2026-01-01",
            "summary": {
                "total_episodes": 3,
                "total_views": 500,
                "total_likes": 100,
                "total_comments": 20,
                "total_shares": 10,
            },
            "top_episodes": {"by_views": [], "by_engagement": []},
            "character_rankings": [],
            "recommendations": ["Try more Pens episodes"],
        }
        result = format_discord_summary(report)
        assert "Try more Pens episodes" in result

    def test_returns_string(self):
        report = {
            "report_date": "2026-01-01",
            "summary": {
                "total_episodes": 0,
                "total_views": 0,
                "total_likes": 0,
                "total_comments": 0,
                "total_shares": 0,
            },
            "top_episodes": {"by_views": [], "by_engagement": []},
            "character_rankings": [],
            "recommendations": [],
        }
        assert isinstance(format_discord_summary(report), str)
