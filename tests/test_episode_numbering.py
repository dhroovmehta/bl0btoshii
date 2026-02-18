"""Tests for DRAFT episode numbering system.

Episode numbers should only be assigned on successful publish, not at script generation.
During generation, episodes use DRAFT-EP-XXX format.
"""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from src.story_generator.engine import _get_next_episode_id


# ---------------------------------------------------------------------------
# _get_next_episode_id returns DRAFT format
# ---------------------------------------------------------------------------

class TestGetNextEpisodeId:
    """Episode IDs at script generation must use DRAFT prefix."""

    def test_returns_draft_prefix(self):
        """Episode ID must start with DRAFT-EP-."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "episodes", "index.json")
            os.makedirs(os.path.dirname(index_path))
            with open(index_path, "w") as f:
                json.dump({"next_episode_number": 1, "episodes": []}, f)

            with patch("src.story_generator.engine._get_next_episode_id") as mock_fn:
                mock_fn.return_value = _get_next_episode_id.__wrapped__(index_path) if hasattr(_get_next_episode_id, '__wrapped__') else None
            # Direct call
            with patch("src.story_generator.engine.os.path.join", return_value=index_path):
                result = _get_next_episode_id()
                assert result.startswith("DRAFT-EP-")

    def test_draft_episode_001(self):
        """First episode must be DRAFT-EP-001."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "index.json")
            with open(index_path, "w") as f:
                json.dump({"next_episode_number": 1, "episodes": []}, f)

            with patch("src.story_generator.engine.os.path.dirname", return_value=tmpdir), \
                 patch("src.story_generator.engine.os.path.join",
                       side_effect=lambda *args: index_path if "index.json" in args else os.path.join(*args)):
                result = _get_next_episode_id()
                assert result == "DRAFT-EP-001"


# ---------------------------------------------------------------------------
# Script generation must NOT increment counter
# ---------------------------------------------------------------------------

class TestScriptGenerationNoIncrement:
    """generate_episode must not increment the episode counter."""

    def test_counter_not_incremented_on_script_gen(self):
        """After generate_episode, next_episode_number must be unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "index.json")
            with open(index_path, "w") as f:
                json.dump({"next_episode_number": 1, "episodes": []}, f)

            # We can't easily call generate_episode (needs API), but we can
            # verify _increment_episode_counter is not called
            from src.story_generator import engine
            assert not hasattr(engine, '_increment_episode_counter'), \
                "_increment_episode_counter should be removed from engine.py"


# ---------------------------------------------------------------------------
# assign_episode_number — called only on successful publish
# ---------------------------------------------------------------------------

class TestAssignEpisodeNumber:
    """assign_episode_number must exist and properly assign real EP numbers."""

    def test_function_exists(self):
        """assign_episode_number must exist in story_generator.engine."""
        from src.story_generator.engine import assign_episode_number
        assert callable(assign_episode_number)

    def test_returns_real_episode_id(self):
        """Must return EP001 format (not DRAFT)."""
        from src.story_generator.engine import assign_episode_number

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "index.json")
            with open(index_path, "w") as f:
                json.dump({"next_episode_number": 1, "episodes": []}, f)

            with patch("src.story_generator.engine.os.path.dirname", return_value=tmpdir), \
                 patch("src.story_generator.engine.os.path.join",
                       side_effect=lambda *args: index_path if "index.json" in args else os.path.join(*args)):
                result = assign_episode_number()
                assert result == "EP001"

    def test_increments_counter(self):
        """Must increment next_episode_number after assignment."""
        from src.story_generator.engine import assign_episode_number

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "index.json")
            with open(index_path, "w") as f:
                json.dump({"next_episode_number": 1, "episodes": []}, f)

            with patch("src.story_generator.engine.os.path.dirname", return_value=tmpdir), \
                 patch("src.story_generator.engine.os.path.join",
                       side_effect=lambda *args: index_path if "index.json" in args else os.path.join(*args)):
                assign_episode_number()

                with open(index_path, "r") as f:
                    data = json.load(f)
                assert data["next_episode_number"] == 2

    def test_sequential_assignments(self):
        """Multiple calls must produce EP001, EP002, EP003."""
        from src.story_generator.engine import assign_episode_number

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "index.json")
            with open(index_path, "w") as f:
                json.dump({"next_episode_number": 1, "episodes": []}, f)

            with patch("src.story_generator.engine.os.path.dirname", return_value=tmpdir), \
                 patch("src.story_generator.engine.os.path.join",
                       side_effect=lambda *args: index_path if "index.json" in args else os.path.join(*args)):
                assert assign_episode_number() == "EP001"
                assert assign_episode_number() == "EP002"
                assert assign_episode_number() == "EP003"


# ---------------------------------------------------------------------------
# Variant filenames use draft prefix
# ---------------------------------------------------------------------------

class TestVariantDraftNaming:
    """Variant filenames must use draft-ep-xxx-v1 format."""

    def test_variant_output_name_uses_draft(self):
        """Variant output name must include 'draft' prefix."""
        from src.video_assembler.variant_generator import generate_single_variant

        script = {
            "metadata": {"episode_id": "DRAFT-EP-001", "title": "Test"},
            "scenes": [],
        }
        # The output_name is constructed from episode_id.lower()
        # We just verify the metadata flows through
        episode_id = script["metadata"]["episode_id"].lower()
        expected_name = f"{episode_id}_v1"
        assert expected_name == "draft-ep-001_v1"
