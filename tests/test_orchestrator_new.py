"""Tests for NEW orchestrator features (Phase 9 enhancements).

Tests cover:
1. run_with_retry: Generic retry utility with configurable backoff
2. Asset check integration: check_asset_availability called before video generation
3. Video quality check integration: check_video_quality called after generation
4. Episode logging integration: log_episode_to_index called on completion
5. Auto-publish step: publish_to_all called with retry after metadata
"""

import asyncio
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock, call

import pytest

from src.pipeline.orchestrator import run_with_retry


# ---------------------------------------------------------------------------
# run_with_retry
# ---------------------------------------------------------------------------

class TestRunWithRetry:
    """Test the retry utility function."""

    def test_succeeds_on_first_try(self):
        """Should return result immediately when function succeeds."""
        func = MagicMock(return_value="success")
        result = run_with_retry(func, max_retries=3, backoff_seconds=[1, 2, 3])
        assert result == "success"
        assert func.call_count == 1

    def test_retries_on_failure(self):
        """Should retry when function raises an exception."""
        func = MagicMock(side_effect=[ValueError("fail"), "success"])
        result = run_with_retry(func, max_retries=3, backoff_seconds=[0, 0, 0])
        assert result == "success"
        assert func.call_count == 2

    def test_respects_max_retries(self):
        """Should give up after max_retries attempts."""
        func = MagicMock(side_effect=ValueError("always fails"))
        with pytest.raises(ValueError, match="always fails"):
            run_with_retry(func, max_retries=3, backoff_seconds=[0, 0, 0])
        assert func.call_count == 3

    def test_passes_args_to_function(self):
        """Should forward args and kwargs to the target function."""
        func = MagicMock(return_value="ok")
        run_with_retry(func, max_retries=1, backoff_seconds=[], args=("a", "b"), kwargs={"key": "val"})
        func.assert_called_once_with("a", "b", key="val")

    def test_returns_none_on_all_failures_if_no_raise(self):
        """When raise_on_failure=False, should return None instead of raising."""
        func = MagicMock(side_effect=ValueError("fail"))
        result = run_with_retry(func, max_retries=2, backoff_seconds=[0, 0], raise_on_failure=False)
        assert result is None
        assert func.call_count == 2

    def test_collects_errors(self):
        """Should track all errors from failed attempts."""
        errors = []
        func = MagicMock(side_effect=[ValueError("err1"), TypeError("err2"), "success"])
        result = run_with_retry(func, max_retries=3, backoff_seconds=[0, 0, 0], error_log=errors)
        assert result == "success"
        assert len(errors) == 2
        assert "err1" in str(errors[0])
        assert "err2" in str(errors[1])


# ---------------------------------------------------------------------------
# Asset check integration (before video generation)
# ---------------------------------------------------------------------------

class TestAssetCheckIntegration:
    """Test that asset checks block video generation when assets are missing."""

    @pytest.mark.asyncio
    async def test_asset_check_blocks_on_missing(self):
        """When assets are missing, video generation should NOT proceed."""
        from src.bot.handlers.script_review import _generate_and_post_videos

        state = {
            "stage": "video_generating",
            "current_episode": "EP099",
            "current_script": {
                "scenes": [
                    {
                        "background": "nonexistent_bg",
                        "characters_present": ["fakeanimal"],
                        "character_positions": {"fakeanimal": "center"},
                        "character_animations": {"fakeanimal": "idle"},
                        "dialogue": [],
                        "sfx_triggers": [],
                    }
                ],
                "metadata": {"title": "Test"},
            },
        }

        mock_bot = MagicMock()
        mock_channel = AsyncMock()

        with patch("src.bot.handlers.script_review.load_state", return_value=state), \
             patch("src.bot.handlers.script_review.save_state"), \
             patch("src.pipeline.orchestrator.check_asset_availability") as mock_check:
            mock_check.return_value = (False, ["backgrounds/nonexistent_bg.png"])
            await _generate_and_post_videos(mock_bot, mock_channel)

            # Should have notified about missing assets
            mock_channel.send.assert_called()
            sent_text = mock_channel.send.call_args_list[0][0][0]
            assert "asset" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_asset_check_failure_sends_to_errors_channel(self):
        """Asset check failure must also notify #errors channel."""
        from src.bot.handlers.script_review import _generate_and_post_videos

        state = {
            "stage": "video_generating",
            "current_episode": "EP099",
            "current_script": {
                "scenes": [
                    {
                        "background": "nonexistent_bg",
                        "characters_present": ["fakeanimal"],
                        "character_positions": {"fakeanimal": "center"},
                        "character_animations": {"fakeanimal": "idle"},
                        "dialogue": [],
                        "sfx_triggers": [],
                    }
                ],
                "metadata": {"title": "Test"},
            },
        }

        mock_bot = MagicMock()
        mock_channel = AsyncMock()

        with patch("src.bot.handlers.script_review.load_state", return_value=state), \
             patch("src.bot.handlers.script_review.save_state"), \
             patch("src.pipeline.orchestrator.check_asset_availability") as mock_check, \
             patch("src.bot.alerts.notify_error") as mock_notify:
            mock_check.return_value = (False, ["backgrounds/nonexistent_bg.png"])
            await _generate_and_post_videos(mock_bot, mock_channel)

            # Must call notify_error for #errors channel
            mock_notify.assert_called_once()
            call_args = mock_notify.call_args
            assert call_args[0][0] == mock_bot  # bot
            assert "Asset" in call_args[0][1]   # stage
            assert "EP099" in call_args[0][2]   # episode_id

    @pytest.mark.asyncio
    async def test_asset_check_allows_when_present(self):
        """When all assets exist, video generation should proceed."""
        from src.bot.handlers.script_review import _generate_and_post_videos

        state = {
            "stage": "video_generating",
            "current_episode": "EP099",
            "current_script": {
                "scenes": [
                    {
                        "background": "diner_interior",
                        "characters_present": ["pens"],
                        "character_positions": {"pens": "stool_1"},
                        "character_animations": {"pens": "idle"},
                        "dialogue": [],
                        "sfx_triggers": [],
                    }
                ],
                "metadata": {"title": "Test"},
            },
        }

        mock_bot = MagicMock()
        mock_channel = AsyncMock()

        with patch("src.bot.handlers.script_review.load_state", return_value=state), \
             patch("src.bot.handlers.script_review.save_state"), \
             patch("src.pipeline.orchestrator.check_asset_availability", return_value=(True, [])), \
             patch("src.video_assembler.variant_generator.generate_variants") as mock_gen, \
             patch("src.pipeline.orchestrator.check_video_quality", return_value=(True, [])):
            mock_gen.return_value = [
                {"name": "v1", "description": "Standard", "video_path": "/tmp/v1.mp4", "duration_seconds": 35, "preset": "standard"},
            ]

            mock_preview_channel = AsyncMock()
            mock_bot.get_channel.return_value = mock_preview_channel

            with patch("src.bot.bot.CHANNEL_IDS", {"video_preview": 123}):
                await _generate_and_post_videos(mock_bot, mock_channel)

            # generate_variants should have been called
            mock_gen.assert_called_once()


# ---------------------------------------------------------------------------
# Video quality check integration (after generation)
# ---------------------------------------------------------------------------

class TestVideoQualityIntegration:
    """Test that video quality checks run after generation."""

    @pytest.mark.asyncio
    async def test_quality_check_warns_on_issues(self):
        """When quality check fails, should warn but not block (user picks)."""
        from src.bot.handlers.script_review import _generate_and_post_videos

        state = {
            "stage": "video_generating",
            "current_episode": "EP099",
            "current_script": {
                "scenes": [
                    {
                        "background": "diner_interior",
                        "characters_present": ["pens"],
                        "character_positions": {"pens": "stool_1"},
                        "character_animations": {"pens": "idle"},
                        "dialogue": [],
                        "sfx_triggers": [],
                    }
                ],
                "metadata": {"title": "Test"},
            },
        }

        mock_bot = MagicMock()
        mock_channel = AsyncMock()
        mock_preview = AsyncMock()
        mock_bot.get_channel.return_value = mock_preview

        # Patch os.path.exists to return True for the video path so quality check runs
        original_exists = os.path.exists

        def mock_exists(path):
            if path == "/tmp/v1.mp4":
                return True
            return original_exists(path)

        with patch("src.bot.handlers.script_review.load_state", return_value=state), \
             patch("src.bot.handlers.script_review.save_state"), \
             patch("src.pipeline.orchestrator.check_asset_availability", return_value=(True, [])), \
             patch("src.video_assembler.variant_generator.generate_variants") as mock_gen, \
             patch("src.pipeline.orchestrator.check_video_quality") as mock_quality, \
             patch("os.path.exists", side_effect=mock_exists), \
             patch("src.bot.bot.CHANNEL_IDS", {"video_preview": 123}):

            mock_gen.return_value = [
                {"name": "v1", "description": "Standard", "video_path": "/tmp/v1.mp4", "duration_seconds": 35, "preset": "standard"},
            ]
            mock_quality.return_value = (False, ["Resolution: 720x1280 (expected 1080x1920)"])

            await _generate_and_post_videos(mock_bot, mock_channel)

            # Quality check should have been called
            mock_quality.assert_called_once_with("/tmp/v1.mp4")

            # Should warn about quality issues in the preview message
            all_sent = " ".join(str(c) for c in mock_preview.send.call_args_list)
            assert "quality" in all_sent.lower() or "warning" in all_sent.lower()


# ---------------------------------------------------------------------------
# Episode logging integration (on completion)
# ---------------------------------------------------------------------------

class TestEpisodeLoggingIntegration:
    """Test that episode logging happens when pipeline completes."""

    @pytest.mark.asyncio
    async def test_episode_logged_on_completion(self):
        """log_episode_to_index should be called when pipeline reaches done."""
        from src.bot.handlers.video_preview import _generate_metadata_and_schedule

        state = {
            "stage": "publishing",
            "current_episode": "EP099",
            "current_script": {
                "episode_id": "EP099",
                "title": "Test Episode",
                "scenes": [],
                "metadata": {
                    "episode_id": "EP099",
                    "title": "Test Episode",
                    "characters_featured": ["pens"],
                    "situation_type": "everyday_life",
                    "punchline_type": "deadpan",
                    "location": "diner_interior",
                    "created_at": "2026-02-15T00:00:00Z",
                },
            },
            "video_variants": [{"video_path": "/tmp/v1.mp4"}],
            "selected_video_index": 0,
        }

        mock_bot = MagicMock()
        mock_channel = AsyncMock()
        mock_pub_channel = AsyncMock()
        mock_bot.get_channel.return_value = mock_pub_channel

        with patch("src.bot.handlers.video_preview.load_state", return_value=state), \
             patch("src.bot.handlers.video_preview.save_state"), \
             patch("src.metadata.generator.generate_metadata") as mock_meta, \
             patch("src.metadata.generator.safety_check", return_value=(True, [])), \
             patch("src.publisher.scheduler.get_next_posting_slots") as mock_slots, \
             patch("src.publisher.scheduler.format_schedule_message", return_value="Schedule"), \
             patch("src.continuity.engine.log_episode") as mock_log_cont, \
             patch("src.pipeline.orchestrator.log_episode_to_index") as mock_log_index, \
             patch("src.publisher.platforms.publish_to_all") as mock_publish, \
             patch("src.bot.bot.CHANNEL_IDS", {"publishing_log": 456}):

            mock_meta.return_value = {
                "tiktok": {"title": "Test", "description": "Test", "hashtags": []},
                "youtube": {"title": "Test", "description": "Test", "tags": []},
                "instagram": {"caption": "Test", "hashtags": []},
            }
            from datetime import datetime
            mock_slots.return_value = {
                "tiktok": datetime(2026, 2, 16, 10, 0),
                "youtube": datetime(2026, 2, 16, 10, 30),
                "instagram": datetime(2026, 2, 16, 11, 0),
            }
            mock_publish.return_value = {
                "tiktok": {"success": False, "error": "Not configured"},
                "youtube": {"success": False, "error": "Not configured"},
                "instagram": {"success": False, "error": "Not configured"},
            }

            await _generate_metadata_and_schedule(mock_bot, mock_channel)

            # log_episode_to_index should have been called with the script
            mock_log_index.assert_called_once()


# ---------------------------------------------------------------------------
# Auto-publish step
# ---------------------------------------------------------------------------

class TestAutoPublishIntegration:
    """Test that auto-publish is attempted after metadata generation."""

    @pytest.mark.asyncio
    async def test_publish_attempted_after_metadata(self):
        """publish_to_all should be called after metadata is generated."""
        from src.bot.handlers.video_preview import _generate_metadata_and_schedule

        state = {
            "stage": "publishing",
            "current_episode": "EP099",
            "current_script": {
                "episode_id": "EP099",
                "title": "Test Episode",
                "scenes": [],
                "metadata": {
                    "episode_id": "EP099",
                    "title": "Test Episode",
                    "characters_featured": ["pens"],
                    "situation_type": "everyday_life",
                    "punchline_type": "deadpan",
                    "location": "diner_interior",
                    "created_at": "2026-02-15T00:00:00Z",
                },
            },
            "video_variants": [{"video_path": "/tmp/v1.mp4"}],
            "selected_video_index": 0,
        }

        mock_bot = MagicMock()
        mock_channel = AsyncMock()
        mock_pub_channel = AsyncMock()
        mock_bot.get_channel.return_value = mock_pub_channel

        with patch("src.bot.handlers.video_preview.load_state", return_value=state), \
             patch("src.bot.handlers.video_preview.save_state"), \
             patch("src.metadata.generator.generate_metadata") as mock_meta, \
             patch("src.metadata.generator.safety_check", return_value=(True, [])), \
             patch("src.publisher.scheduler.get_next_posting_slots") as mock_slots, \
             patch("src.publisher.scheduler.format_schedule_message", return_value="Schedule"), \
             patch("src.continuity.engine.log_episode") as mock_log_cont, \
             patch("src.pipeline.orchestrator.log_episode_to_index"), \
             patch("src.publisher.platforms.publish_to_all") as mock_publish, \
             patch("src.bot.bot.CHANNEL_IDS", {"publishing_log": 456}):

            mock_meta.return_value = {
                "tiktok": {"title": "Test"},
                "youtube": {"title": "Test"},
                "instagram": {"caption": "Test"},
            }
            from datetime import datetime
            mock_slots.return_value = {
                "tiktok": datetime(2026, 2, 16, 10, 0),
                "youtube": datetime(2026, 2, 16, 10, 30),
                "instagram": datetime(2026, 2, 16, 11, 0),
            }
            mock_publish.return_value = {
                "tiktok": {"success": False, "error": "Not configured"},
                "youtube": {"success": False, "error": "Not configured"},
                "instagram": {"success": False, "error": "Not configured"},
            }

            await _generate_metadata_and_schedule(mock_bot, mock_channel)

            # publish_to_all should have been called
            mock_publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_failure_does_not_block_completion(self):
        """If publishing fails, pipeline should still complete (stage=done)."""
        from src.bot.handlers.video_preview import _generate_metadata_and_schedule

        state = {
            "stage": "publishing",
            "current_episode": "EP099",
            "current_script": {
                "episode_id": "EP099",
                "title": "Test Episode",
                "scenes": [],
                "metadata": {
                    "episode_id": "EP099",
                    "title": "Test Episode",
                    "characters_featured": ["pens"],
                    "situation_type": "everyday_life",
                    "punchline_type": "deadpan",
                    "location": "diner_interior",
                    "created_at": "2026-02-15T00:00:00Z",
                },
            },
            "video_variants": [{"video_path": "/tmp/v1.mp4"}],
            "selected_video_index": 0,
        }

        saved_states = []

        mock_bot = MagicMock()
        mock_channel = AsyncMock()
        mock_pub_channel = AsyncMock()
        mock_bot.get_channel.return_value = mock_pub_channel

        def capture_state(s):
            saved_states.append(s.copy())

        with patch("src.bot.handlers.video_preview.load_state", return_value=state), \
             patch("src.bot.handlers.video_preview.save_state", side_effect=capture_state), \
             patch("src.metadata.generator.generate_metadata") as mock_meta, \
             patch("src.metadata.generator.safety_check", return_value=(True, [])), \
             patch("src.publisher.scheduler.get_next_posting_slots") as mock_slots, \
             patch("src.publisher.scheduler.format_schedule_message", return_value="Schedule"), \
             patch("src.continuity.engine.log_episode") as mock_log_cont, \
             patch("src.pipeline.orchestrator.log_episode_to_index"), \
             patch("src.publisher.platforms.publish_to_all") as mock_publish, \
             patch("src.bot.bot.CHANNEL_IDS", {"publishing_log": 456}):

            mock_meta.return_value = {
                "tiktok": {"title": "Test"},
                "youtube": {"title": "Test"},
                "instagram": {"caption": "Test"},
            }
            from datetime import datetime
            mock_slots.return_value = {
                "tiktok": datetime(2026, 2, 16, 10, 0),
                "youtube": datetime(2026, 2, 16, 10, 30),
                "instagram": datetime(2026, 2, 16, 11, 0),
            }
            # Publishing fails
            mock_publish.return_value = {
                "tiktok": {"success": False, "error": "API not configured"},
                "youtube": {"success": False, "error": "API not configured"},
                "instagram": {"success": False, "error": "API not configured"},
            }

            await _generate_metadata_and_schedule(mock_bot, mock_channel)

            # Pipeline should still reach "done"
            assert any(s.get("stage") == "done" for s in saved_states)
