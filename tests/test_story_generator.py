"""Tests for story generator modules.

Tests cover:
- validator: REQUIRED_TOP_KEYS, REQUIRED_SCENE_KEYS, validate_script
- slot_machine: _weighted_choice
"""

import json
import os
from unittest.mock import patch, mock_open

import pytest

from src.story_generator.validator import (
    validate_script,
    REQUIRED_TOP_KEYS,
    REQUIRED_SCENE_KEYS,
    VALID_SFX,
    VALID_MUSIC,
)
from src.story_generator.slot_machine import _weighted_choice


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestValidatorConstants:
    """Test validator constant definitions."""

    def test_required_top_keys(self):
        assert "episode_id" in REQUIRED_TOP_KEYS
        assert "scenes" in REQUIRED_TOP_KEYS
        assert "metadata" in REQUIRED_TOP_KEYS
        assert "continuity_log" in REQUIRED_TOP_KEYS
        assert len(REQUIRED_TOP_KEYS) == 10

    def test_required_scene_keys(self):
        assert "scene_number" in REQUIRED_SCENE_KEYS
        assert "background" in REQUIRED_SCENE_KEYS
        assert "dialogue" in REQUIRED_SCENE_KEYS
        assert "characters_present" in REQUIRED_SCENE_KEYS
        assert len(REQUIRED_SCENE_KEYS) == 6

    def test_valid_sfx_not_empty(self):
        assert len(VALID_SFX) > 0
        assert "text_blip_mid" in VALID_SFX

    def test_valid_music_not_empty(self):
        assert len(VALID_MUSIC) > 0


# ---------------------------------------------------------------------------
# validate_script
# ---------------------------------------------------------------------------

# Fixtures for mocking characters.json and locations.json
MOCK_CHARACTERS = {
    "characters": {
        "pens": {"nickname": "Pens"},
        "chubs": {"nickname": "Chubs"},
        "oinks": {"nickname": "Oinks"},
        "meows": {"nickname": "Meows"},
        "quacks": {"nickname": "Quacks"},
        "reows": {"nickname": "Reows"},
    }
}
MOCK_LOCATIONS = {
    "locations": {
        "diner_interior": {"name": "Oinks' Diner"},
        "town_square": {"name": "Town Square"},
        "beach": {"name": "Beach"},
    }
}


def _make_valid_script():
    """Build a minimal valid script for testing."""
    return {
        "episode_id": "EP001",
        "title": "Test Episode",
        "slug": "test-episode",
        "created_at": "2026-01-01T00:00:00Z",
        "version": 1,
        "generation_params": {"situation": "everyday_life"},
        "duration_target_seconds": 35,
        "scenes": [
            {
                "scene_number": 1,
                "duration_seconds": 10,
                "background": "diner_interior",
                "characters_present": ["pens", "chubs"],
                "action_description": "Pens walks in",
                "dialogue": [
                    {"character": "pens", "text": "Hey there."},
                    {"character": "chubs", "text": "Oh hey Pens, what's up?"},
                ],
            },
            {
                "scene_number": 2,
                "duration_seconds": 12,
                "background": "diner_interior",
                "characters_present": ["pens", "chubs"],
                "action_description": "They sit down",
                "dialogue": [
                    {"character": "pens", "text": "Not much."},
                    {"character": "chubs", "text": "Cool cool cool."},
                ],
            },
        ],
        "end_card": {"text": "Subscribe!", "duration_seconds": 3},
        "continuity_log": {
            "events": ["Pens and Chubs had coffee at the diner"],
        },
        "metadata": {
            "episode_id": "EP001",
            "title": "Test Episode",
            "characters_featured": ["pens", "chubs"],
        },
    }


def _mock_open_files(filename, *args, **kwargs):
    """Side effect for open() that returns mock data files."""
    if "characters.json" in str(filename):
        return mock_open(read_data=json.dumps(MOCK_CHARACTERS))()
    if "locations.json" in str(filename):
        return mock_open(read_data=json.dumps(MOCK_LOCATIONS))()
    return open(filename, *args, **kwargs)


class TestValidateScript:
    """Test script validation."""

    @patch("builtins.open", side_effect=_mock_open_files)
    def test_valid_script_passes(self, mock_file):
        is_valid, errors = validate_script(_make_valid_script())
        assert is_valid is True
        assert errors == []

    @patch("builtins.open", side_effect=_mock_open_files)
    def test_missing_top_key(self, mock_file):
        script = _make_valid_script()
        del script["episode_id"]
        is_valid, errors = validate_script(script)
        assert is_valid is False
        assert any("episode_id" in e for e in errors)

    @patch("builtins.open", side_effect=_mock_open_files)
    def test_missing_scene_key(self, mock_file):
        script = _make_valid_script()
        del script["scenes"][0]["background"]
        is_valid, errors = validate_script(script)
        assert is_valid is False
        assert any("background" in e for e in errors)

    @patch("builtins.open", side_effect=_mock_open_files)
    def test_empty_scenes(self, mock_file):
        script = _make_valid_script()
        script["scenes"] = []
        is_valid, errors = validate_script(script)
        assert is_valid is False
        assert any("no scenes" in e.lower() for e in errors)

    @patch("builtins.open", side_effect=_mock_open_files)
    def test_invalid_duration(self, mock_file):
        script = _make_valid_script()
        script["scenes"][0]["duration_seconds"] = 0
        is_valid, errors = validate_script(script)
        assert is_valid is False
        assert any("duration" in e.lower() for e in errors)

    @patch("builtins.open", side_effect=_mock_open_files)
    def test_unknown_background(self, mock_file):
        script = _make_valid_script()
        script["scenes"][0]["background"] = "nonexistent_bg"
        is_valid, errors = validate_script(script)
        assert is_valid is False
        assert any("unknown background" in e.lower() for e in errors)

    @patch("builtins.open", side_effect=_mock_open_files)
    def test_unknown_character(self, mock_file):
        script = _make_valid_script()
        script["scenes"][0]["characters_present"] = ["pens", "unknownchar"]
        is_valid, errors = validate_script(script)
        assert is_valid is False
        assert any("unknown character" in e.lower() for e in errors)

    @patch("builtins.open", side_effect=_mock_open_files)
    def test_empty_dialogue_text(self, mock_file):
        script = _make_valid_script()
        script["scenes"][0]["dialogue"][0]["text"] = ""
        is_valid, errors = validate_script(script)
        assert is_valid is False
        assert any("empty dialogue" in e.lower() for e in errors)

    @patch("builtins.open", side_effect=_mock_open_files)
    def test_pens_word_limit(self, mock_file):
        script = _make_valid_script()
        script["scenes"][0]["dialogue"][0] = {
            "character": "pens",
            "text": "one two three four five six seven eight",
        }
        is_valid, errors = validate_script(script)
        assert is_valid is False
        assert any("pens" in e.lower() and "words" in e.lower() for e in errors)

    @patch("builtins.open", side_effect=_mock_open_files)
    def test_duration_too_short(self, mock_file):
        script = _make_valid_script()
        script["scenes"][0]["duration_seconds"] = 2
        script["scenes"][1]["duration_seconds"] = 2
        script["duration_target_seconds"] = 35
        is_valid, errors = validate_script(script)
        assert is_valid is False
        assert any("too short" in e.lower() for e in errors)

    @patch("builtins.open", side_effect=_mock_open_files)
    def test_empty_continuity_log(self, mock_file):
        script = _make_valid_script()
        script["continuity_log"] = {"events": []}
        is_valid, errors = validate_script(script)
        assert is_valid is False
        assert any("continuity" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# _weighted_choice
# ---------------------------------------------------------------------------

class TestWeightedChoice:
    """Test weighted random selection."""

    def test_returns_item_from_list(self):
        items = ["a", "b", "c"]
        weights = {"a": 1.0, "b": 1.0, "c": 1.0}
        result = _weighted_choice(items, weights)
        assert result in items

    def test_heavily_weighted_item_selected(self):
        """With extreme weights, the heavy item should win almost always."""
        items = ["a", "b"]
        weights = {"a": 1000.0, "b": 0.001}
        results = [_weighted_choice(items, weights) for _ in range(100)]
        assert results.count("a") > 90

    def test_zero_total_falls_back(self):
        """When all weights are 0, should fall back to random.choice."""
        items = ["a", "b", "c"]
        weights = {}  # no weights → all default to 0
        # total would be 0 from sum(weights.values()), should not crash
        result = _weighted_choice(items, weights)
        assert result in items

    def test_missing_weight_defaults_to_1(self):
        """Items missing from weights dict should get weight 1.0."""
        items = ["a", "b"]
        weights = {"a": 1.0}  # b missing
        result = _weighted_choice(items, weights)
        assert result in items

    def test_single_item(self):
        result = _weighted_choice(["only"], {"only": 1.0})
        assert result == "only"
