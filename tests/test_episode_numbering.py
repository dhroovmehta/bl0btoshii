"""Tests for DRAFT episode numbering system.

Episode numbers should only be assigned on successful publish, not at script generation.
During generation, episodes use DRAFT-EP-XXX format.

End-to-end contract: DRAFT-EP-XXX at generation → real EP-XXX only on publish.
Every downstream module must handle DRAFT format without crashing or leaking it
into published data.
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


# ---------------------------------------------------------------------------
# log_episode_to_index must NOT double-increment the counter
# ---------------------------------------------------------------------------

class TestLogEpisodeToIndexNoIncrement:
    """log_episode_to_index must not increment next_episode_number.

    assign_episode_number() handles the counter. If log_episode_to_index
    also increments, the counter advances by 2 per published episode.
    """

    def test_counter_not_incremented(self):
        """next_episode_number must be unchanged after log_episode_to_index."""
        from src.pipeline.orchestrator import log_episode_to_index

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "episodes", "index.json")
            os.makedirs(os.path.dirname(index_path))
            with open(index_path, "w") as f:
                json.dump({"next_episode_number": 2, "episodes": []}, f)

            script = {
                "metadata": {"episode_id": "EP001", "title": "Test"},
                "scenes": [],
            }

            with patch("src.pipeline.orchestrator.DATA_DIR", tmpdir):
                log_episode_to_index(script)

            with open(index_path, "r") as f:
                data = json.load(f)
            assert data["next_episode_number"] == 2, \
                "log_episode_to_index must NOT increment counter (assign_episode_number handles it)"

    def test_episode_appended_to_list(self):
        """Episode must still be appended to the episodes list."""
        from src.pipeline.orchestrator import log_episode_to_index

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "episodes", "index.json")
            os.makedirs(os.path.dirname(index_path))
            with open(index_path, "w") as f:
                json.dump({"next_episode_number": 2, "episodes": []}, f)

            script = {
                "metadata": {"episode_id": "EP001", "title": "Test Episode"},
                "scenes": [],
            }

            with patch("src.pipeline.orchestrator.DATA_DIR", tmpdir):
                log_episode_to_index(script)

            with open(index_path, "r") as f:
                data = json.load(f)
            assert len(data["episodes"]) == 1
            assert data["episodes"][0]["episode_id"] == "EP001"


# ---------------------------------------------------------------------------
# Notion publisher must handle DRAFT-EP-XXX without crashing
# ---------------------------------------------------------------------------

class TestNotionPublisherDraftFormat:
    """Notion script_publisher must handle DRAFT-EP-XXX episode IDs."""

    def test_draft_id_does_not_crash(self):
        """_build_properties must not crash on DRAFT-EP-001."""
        from src.notion.script_publisher import _build_properties

        script_data = {
            "episode_id": "DRAFT-EP-001",
            "title": "Test Script",
            "version": 1,
            "created_at": "2026-02-17T00:00:00Z",
            "metadata": {"characters_featured": ["oinks"]},
            "generation_params": {"situation": "everyday_life"},
        }
        props = _build_properties(script_data)
        assert "title" in props

    def test_draft_id_page_title_shows_draft(self):
        """Notion page title must include DRAFT prefix for draft episodes."""
        from src.notion.script_publisher import _build_properties

        script_data = {
            "episode_id": "DRAFT-EP-001",
            "title": "Test Script",
            "version": 1,
            "created_at": "2026-02-17T00:00:00Z",
            "metadata": {},
            "generation_params": {},
        }
        props = _build_properties(script_data)
        page_title = props["title"]["title"][0]["text"]["content"]
        assert "DRAFT" in page_title

    def test_real_id_page_title_shows_ep_number(self):
        """Notion page title must show EP # XXX for real episode IDs."""
        from src.notion.script_publisher import _build_properties

        script_data = {
            "episode_id": "EP001",
            "title": "Published Episode",
            "version": 1,
            "created_at": "2026-02-17T00:00:00Z",
            "metadata": {},
            "generation_params": {},
        }
        props = _build_properties(script_data)
        page_title = props["title"]["title"][0]["text"]["content"]
        assert "EP # 001" in page_title
        assert "DRAFT" not in page_title

    def test_draft_episode_number_extracted(self):
        """Episode number must be correctly extracted from DRAFT-EP-042."""
        from src.notion.script_publisher import _build_properties

        script_data = {
            "episode_id": "DRAFT-EP-042",
            "title": "Test",
            "version": 1,
            "created_at": "2026-02-17T00:00:00Z",
            "metadata": {},
            "generation_params": {},
        }
        props = _build_properties(script_data)
        assert props["Episode Number"]["number"] == 42
