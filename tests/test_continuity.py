"""Tests for continuity engine module.

Tests cover:
- _extract_tags: stop word filtering, punctuation stripping, deduplication
- find_callback_opportunities: scoring logic (character overlap, location, tags, gags)
"""

import json
from unittest.mock import patch

import pytest

from src.continuity.engine import _extract_tags, find_callback_opportunities


# ---------------------------------------------------------------------------
# _extract_tags
# ---------------------------------------------------------------------------

class TestExtractTags:
    """Test keyword tag extraction."""

    def test_basic_extraction(self):
        tags = _extract_tags("Pens discovered a hidden cave")
        assert "pens" in tags
        assert "discovered" in tags
        assert "hidden" in tags
        assert "cave" in tags

    def test_stop_words_removed(self):
        tags = _extract_tags("the cat is on the mat")
        assert "the" not in tags
        assert "is" not in tags
        assert "on" not in tags

    def test_punctuation_stripped(self):
        tags = _extract_tags("amazing! great, wonderful.")
        assert "amazing" in tags
        assert "great" in tags
        assert "wonderful" in tags

    def test_deduplicates(self):
        tags = _extract_tags("fish fish fish fish fish")
        assert tags.count("fish") == 1

    def test_max_8_tags(self):
        text = " ".join([f"word{i}" for i in range(20)])
        tags = _extract_tags(text)
        assert len(tags) <= 8

    def test_empty_text(self):
        tags = _extract_tags("")
        assert tags == []

    def test_short_words_filtered(self):
        """Words with 2 or fewer characters should be filtered."""
        tags = _extract_tags("I am ok so we go")
        # All are stop words or <= 2 chars
        assert len(tags) == 0

    def test_lowercase(self):
        tags = _extract_tags("PENS Found Something")
        assert all(t == t.lower() for t in tags)


# ---------------------------------------------------------------------------
# find_callback_opportunities
# ---------------------------------------------------------------------------

MOCK_TIMELINE = {
    "events": [
        {
            "episode_id": "EP001",
            "event": "Pens burned the pancakes",
            "characters_involved": ["pens", "oinks"],
            "location": "diner_interior",
            "tags": ["pancakes", "cooking", "disaster"],
            "callback_potential": "high",
        },
        {
            "episode_id": "EP002",
            "event": "Chubs got lost in the forest",
            "characters_involved": ["chubs"],
            "location": "forest_path",
            "tags": ["lost", "adventure"],
            "callback_potential": "medium",
        },
    ]
}

MOCK_GAGS = {
    "running_gags": [
        {
            "id": "pens_pancakes",
            "origin_episode": "EP001",
            "description": "pens always burns pancakes",
            "last_referenced": "EP001",
            "times_referenced": 1,
            "status": "active",
            "escalation_ideas": ["Pens tries a cooking class"],
        },
        {
            "id": "inactive_gag",
            "origin_episode": "EP001",
            "description": "something inactive",
            "status": "retired",
            "times_referenced": 10,
        },
    ]
}

MOCK_GROWTH = {
    "character_growth": {
        "pens": {
            "developments": [
                {"episode_id": "EP001", "development": "Learned to flip pancakes"},
            ]
        }
    }
}


def _mock_load_json(path):
    """Return mock data based on file path."""
    if "timeline" in str(path):
        return MOCK_TIMELINE
    if "running_gags" in str(path):
        return MOCK_GAGS
    if "character_growth" in str(path):
        return MOCK_GROWTH
    return {}


class TestFindCallbackOpportunities:
    """Test callback opportunity scoring."""

    @patch("src.continuity.engine._load_json", side_effect=_mock_load_json)
    def test_returns_list(self, mock_json):
        result = find_callback_opportunities(["pens"], "cooking", "diner_interior")
        assert isinstance(result, list)

    @patch("src.continuity.engine._load_json", side_effect=_mock_load_json)
    def test_character_overlap_scores(self, mock_json):
        """Episodes with matching characters should score higher."""
        result = find_callback_opportunities(["pens"], "random_situation", "beach")
        pens_callbacks = [cb for cb in result if cb["source_episode"] == "EP001"]
        assert len(pens_callbacks) > 0

    @patch("src.continuity.engine._load_json", side_effect=_mock_load_json)
    def test_location_match_boosts_score(self, mock_json):
        result = find_callback_opportunities(["pens"], "cooking", "diner_interior")
        ep001 = [cb for cb in result if cb["source_episode"] == "EP001" and "pancakes" in cb.get("reference", "")]
        assert len(ep001) > 0
        # Should have location boost
        assert ep001[0]["relevance_score"] > 0.3

    @patch("src.continuity.engine._load_json", side_effect=_mock_load_json)
    def test_inactive_gags_excluded(self, mock_json):
        result = find_callback_opportunities(["pens"], "cooking", "diner_interior")
        refs = [cb["reference"] for cb in result]
        assert "something inactive" not in refs

    @patch("src.continuity.engine._load_json", side_effect=_mock_load_json)
    def test_active_gag_included(self, mock_json):
        result = find_callback_opportunities(["pens"], "cooking", "diner_interior")
        gag_refs = [cb for cb in result if "pancakes" in cb.get("reference", "").lower()]
        assert len(gag_refs) > 0

    @patch("src.continuity.engine._load_json", side_effect=_mock_load_json)
    def test_max_5_results(self, mock_json):
        result = find_callback_opportunities(["pens", "oinks", "chubs"], "cooking", "diner_interior")
        assert len(result) <= 5

    @patch("src.continuity.engine._load_json", side_effect=_mock_load_json)
    def test_sorted_by_relevance(self, mock_json):
        result = find_callback_opportunities(["pens"], "cooking", "diner_interior")
        if len(result) >= 2:
            assert result[0]["relevance_score"] >= result[1]["relevance_score"]

    @patch("src.continuity.engine._load_json", side_effect=_mock_load_json)
    def test_character_growth_included(self, mock_json):
        result = find_callback_opportunities(["pens"], "cooking", "diner_interior")
        growth_refs = [cb for cb in result if "pancakes" in cb.get("reference", "").lower()]
        assert len(growth_refs) > 0

    @patch("src.continuity.engine._load_json", side_effect=_mock_load_json)
    def test_score_capped_at_1(self, mock_json):
        result = find_callback_opportunities(["pens", "oinks"], "cooking disaster", "diner_interior")
        for cb in result:
            assert cb["relevance_score"] <= 1.0

    @patch("src.continuity.engine._load_json", side_effect=_mock_load_json)
    def test_no_match_returns_empty_or_low(self, mock_json):
        result = find_callback_opportunities(["meows"], "space_travel", "moon_base")
        # No matches expected (meows not in any events, location/tags don't match)
        # Growth entries for meows don't exist either
        assert len(result) == 0 or all(cb["relevance_score"] <= 0.3 for cb in result)
