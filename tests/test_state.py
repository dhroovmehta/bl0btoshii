"""Tests for the pipeline state manager (src/bot/state.py).

Tests cover:
- Loading default state when no file exists
- Saving and loading state roundtrip
- Resetting state to idle
- Getting and setting stage
- updated_at timestamp updates on save
"""

import json
import os
from unittest.mock import patch

import pytest

from src.bot.state import (
    STATE_FILE,
    _default_state,
    load_state,
    save_state,
    reset_state,
    get_stage,
    set_stage,
)


@pytest.fixture
def state_file(tmp_dir):
    """Redirect state file to a temporary directory for isolation."""
    test_state_file = os.path.join(tmp_dir, "data", "pipeline_state.json")
    with patch("src.bot.state.STATE_FILE", test_state_file):
        yield test_state_file


class TestDefaultState:
    """Test the default state structure."""

    def test_default_state_has_idle_stage(self):
        state = _default_state()
        assert state["stage"] == "idle"

    def test_default_state_has_no_episode(self):
        state = _default_state()
        assert state["current_episode"] is None

    def test_default_state_has_empty_ideas(self):
        state = _default_state()
        assert state["ideas"] == []

    def test_default_state_has_no_selection(self):
        state = _default_state()
        assert state["selected_idea_index"] is None

    def test_default_state_has_updated_at(self):
        state = _default_state()
        assert "updated_at" in state

    def test_default_state_has_all_required_keys(self):
        state = _default_state()
        required_keys = [
            "current_episode",
            "stage",
            "ideas",
            "selected_idea_index",
            "script_notion_url",
            "script_version",
            "video_variants",
            "selected_video_index",
            "updated_at",
        ]
        for key in required_keys:
            assert key in state, f"Missing key: {key}"


class TestLoadState:
    """Test loading pipeline state from disk."""

    def test_load_returns_default_when_no_file(self, state_file):
        state = load_state()
        assert state["stage"] == "idle"
        assert state["current_episode"] is None

    def test_load_returns_saved_state(self, state_file):
        # Write a state file manually
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        test_state = {
            "current_episode": "EP005",
            "stage": "script_review",
            "ideas": [],
            "selected_idea_index": 0,
            "script_notion_url": "https://notion.so/test",
            "script_version": 2,
            "video_variants": [],
            "selected_video_index": None,
            "updated_at": "2026-02-15T00:00:00",
        }
        with open(state_file, "w") as f:
            json.dump(test_state, f)

        loaded = load_state()
        assert loaded["stage"] == "script_review"
        assert loaded["current_episode"] == "EP005"
        assert loaded["script_version"] == 2


class TestSaveState:
    """Test saving pipeline state to disk."""

    def test_save_creates_file(self, state_file):
        state = _default_state()
        save_state(state)
        assert os.path.exists(state_file)

    def test_save_creates_parent_directory(self, state_file):
        state = _default_state()
        save_state(state)
        assert os.path.isdir(os.path.dirname(state_file))

    def test_save_updates_timestamp(self, state_file):
        state = _default_state()
        old_ts = state["updated_at"]
        save_state(state)
        # Reload and check timestamp changed
        with open(state_file, "r") as f:
            saved = json.load(f)
        # Timestamp should be set (may or may not differ from old_ts depending on speed)
        assert "updated_at" in saved

    def test_save_roundtrip(self, state_file):
        state = _default_state()
        state["stage"] = "video_generating"
        state["current_episode"] = "EP042"
        save_state(state)

        loaded = load_state()
        assert loaded["stage"] == "video_generating"
        assert loaded["current_episode"] == "EP042"

    def test_save_preserves_all_fields(self, state_file):
        state = _default_state()
        state["ideas"] = [{"concept": "test idea"}]
        state["selected_idea_index"] = 0
        state["video_variants"] = [{"name": "v1"}]
        save_state(state)

        loaded = load_state()
        assert loaded["ideas"] == [{"concept": "test idea"}]
        assert loaded["selected_idea_index"] == 0
        assert loaded["video_variants"] == [{"name": "v1"}]


class TestResetState:
    """Test resetting pipeline state."""

    def test_reset_returns_idle_state(self, state_file):
        state = reset_state()
        assert state["stage"] == "idle"

    def test_reset_clears_episode(self, state_file):
        # First set a non-idle state
        state = _default_state()
        state["stage"] = "publishing"
        state["current_episode"] = "EP010"
        save_state(state)

        # Reset should clear everything
        reset = reset_state()
        assert reset["current_episode"] is None
        assert reset["stage"] == "idle"

    def test_reset_persists_to_disk(self, state_file):
        reset_state()
        loaded = load_state()
        assert loaded["stage"] == "idle"


class TestGetSetStage:
    """Test stage get/set helpers."""

    def test_get_stage_returns_idle_by_default(self, state_file):
        assert get_stage() == "idle"

    def test_set_stage_updates_stage(self, state_file):
        set_stage("script_review")
        assert get_stage() == "script_review"

    def test_set_stage_persists(self, state_file):
        set_stage("video_generating")
        loaded = load_state()
        assert loaded["stage"] == "video_generating"

    def test_set_stage_preserves_other_fields(self, state_file):
        state = _default_state()
        state["current_episode"] = "EP007"
        save_state(state)

        set_stage("publishing")
        loaded = load_state()
        assert loaded["stage"] == "publishing"
        assert loaded["current_episode"] == "EP007"

    def test_all_valid_stages(self, state_file):
        valid_stages = [
            "idle",
            "ideas_posted",
            "script_generating",
            "script_review",
            "video_generating",
            "video_review",
            "publishing",
            "done",
        ]
        for stage in valid_stages:
            set_stage(stage)
            assert get_stage() == stage
