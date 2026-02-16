"""Tests for metadata generator module.

Tests cover:
- _generate_title: truncation and passthrough
- _pick_hashtags: deduplication, count limits
- safety_check: blocked words, clickbait detection
"""

import pytest

from src.metadata.generator import _generate_title, _pick_hashtags, safety_check


# ---------------------------------------------------------------------------
# _generate_title
# ---------------------------------------------------------------------------

class TestGenerateTitle:
    """Test title generation."""

    def test_short_title_passes_through(self):
        assert _generate_title("Short Title", "Pens & Chubs") == "Short Title"

    def test_long_title_truncated(self):
        long_title = "A" * 100
        result = _generate_title(long_title, "Pens & Chubs", max_len=55)
        assert len(result) <= 55
        assert result.endswith("...")

    def test_exact_max_len_not_truncated(self):
        title = "A" * 55
        result = _generate_title(title, "Pens & Chubs", max_len=55)
        assert result == title

    def test_one_over_max_len_truncated(self):
        title = "A" * 56
        result = _generate_title(title, "Pens & Chubs", max_len=55)
        assert len(result) <= 55
        assert result.endswith("...")

    def test_custom_max_len(self):
        title = "A" * 30
        result = _generate_title(title, "Pens", max_len=20)
        assert len(result) <= 20


# ---------------------------------------------------------------------------
# _pick_hashtags
# ---------------------------------------------------------------------------

class TestPickHashtags:
    """Test hashtag selection."""

    def test_returns_requested_count(self):
        base = ["#a", "#b", "#c", "#d", "#e"]
        char = ["#pens"]
        result = _pick_hashtags(base, char, 3)
        assert len(result) == 3

    def test_deduplicates(self):
        base = ["#pixelart", "#comedy"]
        char = ["#pixelart"]  # duplicate
        result = _pick_hashtags(base, char, 10)
        assert len(result) == len(set(result))

    def test_returns_fewer_if_not_enough(self):
        base = ["#a", "#b"]
        char = ["#c"]
        result = _pick_hashtags(base, char, 100)
        assert len(result) <= 3  # only 3 unique tags

    def test_all_items_are_strings(self):
        result = _pick_hashtags(["#a", "#b"], ["#c"], 2)
        assert all(isinstance(t, str) for t in result)

    def test_empty_inputs(self):
        result = _pick_hashtags([], [], 5)
        assert result == []


# ---------------------------------------------------------------------------
# safety_check
# ---------------------------------------------------------------------------

class TestSafetyCheck:
    """Test content safety checking."""

    def test_clean_metadata_passes(self):
        metadata = {
            "tiktok": {"title": "Island Adventures", "description": "Fun times", "hashtags": ["#pixelart"]},
            "youtube": {"title": "Island Adventures", "description": "Fun times", "tags": ["#comedy"]},
            "instagram": {"caption": "Check this out!", "hashtags": ["#reels"]},
        }
        is_safe, issues = safety_check(metadata)
        assert is_safe is True
        assert issues == []

    def test_blocked_word_detected(self):
        metadata = {
            "tiktok": {"title": "A stupid mistake", "description": "test", "hashtags": []},
            "youtube": {"title": "test", "description": "test", "tags": []},
            "instagram": {"caption": "test", "hashtags": []},
        }
        is_safe, issues = safety_check(metadata)
        assert is_safe is False
        assert any("stupid" in i for i in issues)

    def test_blocked_word_in_description(self):
        metadata = {
            "tiktok": {"title": "ok", "description": "they hate each other", "hashtags": []},
            "youtube": {"title": "ok", "description": "ok", "tags": []},
            "instagram": {"caption": "ok", "hashtags": []},
        }
        is_safe, issues = safety_check(metadata)
        assert is_safe is False
        assert any("hate" in i for i in issues)

    def test_blocked_word_in_hashtags(self):
        metadata = {
            "tiktok": {"title": "ok", "description": "ok", "hashtags": ["#violence"]},
            "youtube": {"title": "ok", "description": "ok", "tags": []},
            "instagram": {"caption": "ok", "hashtags": []},
        }
        is_safe, issues = safety_check(metadata)
        assert is_safe is False

    def test_clickbait_detected(self):
        metadata = {
            "tiktok": {"title": "You won't believe what happened!", "description": "ok", "hashtags": []},
            "youtube": {"title": "ok", "description": "ok", "tags": []},
            "instagram": {"caption": "ok", "hashtags": []},
        }
        is_safe, issues = safety_check(metadata)
        assert is_safe is False
        assert any("clickbait" in i.lower() for i in issues)

    def test_word_boundary_no_false_positive(self):
        """'die' in 'diet' should NOT be flagged."""
        metadata = {
            "tiktok": {"title": "Diet tips", "description": "ok", "hashtags": []},
            "youtube": {"title": "ok", "description": "ok", "tags": []},
            "instagram": {"caption": "ok", "hashtags": []},
        }
        is_safe, issues = safety_check(metadata)
        assert is_safe is True

    def test_case_insensitive(self):
        metadata = {
            "tiktok": {"title": "SHOCKING news", "description": "ok", "hashtags": []},
            "youtube": {"title": "ok", "description": "ok", "tags": []},
            "instagram": {"caption": "ok", "hashtags": []},
        }
        is_safe, issues = safety_check(metadata)
        assert is_safe is False

    def test_multiple_issues_collected(self):
        metadata = {
            "tiktok": {"title": "You won't believe this stupid thing", "description": "ok", "hashtags": []},
            "youtube": {"title": "ok", "description": "ok", "tags": []},
            "instagram": {"caption": "ok", "hashtags": []},
        }
        _, issues = safety_check(metadata)
        assert len(issues) >= 2  # at least "stupid" + "you won't believe"
