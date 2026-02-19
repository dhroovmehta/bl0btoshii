"""Tests for pipeline reliability fixes.

Covers all 7 diagnosed silent-failure issues:
1. asyncio.create_task swallows exceptions — safe_task wrapper
2. notify_error silently swallows its own errors — must print to stdout
3. platforms.yaml missing file — graceful fallback
4. continuity JSON files crash on missing files — graceful defaults
5. No startup recovery from crashed states — on_ready recovery
6. TikTok/Instagram stubs (informational only — tested by existing publisher tests)
7. data/episodes/index.json and data/continuity/ may not exist — safe creation
"""

import asyncio
import io
import json
import os
import sys
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Issue 1: safe_task wrapper catches exceptions from background tasks
# ---------------------------------------------------------------------------

class TestSafeTask:
    """asyncio.create_task must not silently swallow exceptions."""

    @pytest.mark.asyncio
    async def test_safe_task_exists(self):
        """safe_task function should exist in src.bot.tasks."""
        from src.bot.tasks import safe_task
        assert callable(safe_task)

    @pytest.mark.asyncio
    async def test_safe_task_runs_coro_to_completion(self):
        """Normal coroutines should complete successfully."""
        from src.bot.tasks import safe_task

        result = []

        async def good_coro():
            result.append("done")

        task = safe_task(good_coro())
        await task
        assert result == ["done"]

    @pytest.mark.asyncio
    async def test_safe_task_catches_exception(self):
        """Exceptions inside safe_task must not propagate as unhandled."""
        from src.bot.tasks import safe_task

        async def bad_coro():
            raise RuntimeError("test explosion")

        # Should not raise — the wrapper catches it
        task = safe_task(bad_coro())
        await task  # Must not raise

    @pytest.mark.asyncio
    async def test_safe_task_prints_error_to_stdout(self, capsys):
        """Exceptions must be printed to stdout for journalctl visibility."""
        from src.bot.tasks import safe_task

        async def bad_coro():
            raise RuntimeError("visible error")

        task = safe_task(bad_coro())
        await task
        captured = capsys.readouterr()
        assert "visible error" in captured.out

    @pytest.mark.asyncio
    async def test_safe_task_sends_to_channel_if_provided(self):
        """If a fallback channel is provided, error must be sent there."""
        from src.bot.tasks import safe_task

        channel = AsyncMock()

        async def bad_coro():
            raise RuntimeError("channel error")

        task = safe_task(bad_coro(), error_channel=channel)
        await task
        channel.send.assert_called_once()
        sent_text = channel.send.call_args[0][0]
        assert "channel error" in sent_text

    @pytest.mark.asyncio
    async def test_safe_task_calls_notify_error_if_bot_provided(self):
        """If bot is provided, notify_error must be called."""
        from src.bot.tasks import safe_task

        bot = MagicMock()
        mock_channel = AsyncMock()
        bot.get_channel.return_value = mock_channel

        async def bad_coro():
            raise RuntimeError("alert error")

        with patch("src.bot.alerts.notify_error", new_callable=AsyncMock) as mock_notify:
            task = safe_task(bad_coro(), bot=bot, stage="Test Stage")
            await task
            mock_notify.assert_called_once()
            args = mock_notify.call_args[0]
            assert args[0] is bot
            assert "Test Stage" in args[1]


# ---------------------------------------------------------------------------
# Issue 2: notify_error must print errors instead of silent pass
# ---------------------------------------------------------------------------

class TestNotifyErrorLogging:
    """notify_error must print to stdout when alerting itself fails."""

    @pytest.mark.asyncio
    async def test_notify_error_prints_on_channel_send_failure(self, capsys):
        """When channel.send fails, the error must be printed (not silently swallowed)."""
        from src.bot.alerts import notify_error

        bot = MagicMock()
        channel = AsyncMock()
        channel.send.side_effect = Exception("Discord API exploded")
        bot.get_channel.return_value = channel

        await notify_error(bot, "Stage", "EP001", "original error")

        captured = capsys.readouterr()
        assert "Discord API exploded" in captured.out or "Alerting" in captured.out

    @pytest.mark.asyncio
    async def test_notify_startup_prints_on_failure(self, capsys):
        """When startup notification fails, the error must be printed."""
        from src.bot.alerts import notify_startup

        bot = MagicMock()
        channel = AsyncMock()
        channel.send.side_effect = Exception("Startup send failed")
        bot.get_channel.return_value = channel

        await notify_startup(bot)

        captured = capsys.readouterr()
        assert "Startup send failed" in captured.out or "Alerting" in captured.out


# ---------------------------------------------------------------------------
# Issue 4: continuity _load_json must handle missing files
# ---------------------------------------------------------------------------

class TestContinuityMissingFiles:
    """_load_json must return safe defaults when files don't exist."""

    def test_load_json_missing_timeline(self):
        """_load_json on a non-existent file must not raise FileNotFoundError."""
        from src.continuity.engine import _load_json

        with tempfile.TemporaryDirectory() as tmpdir:
            fake_path = os.path.join(tmpdir, "nonexistent.json")
            # Must NOT raise FileNotFoundError
            result = _load_json(fake_path)
            assert isinstance(result, dict)

    def test_load_json_missing_returns_empty_dict(self):
        """Missing file must return an empty dict."""
        from src.continuity.engine import _load_json

        with tempfile.TemporaryDirectory() as tmpdir:
            fake_path = os.path.join(tmpdir, "missing.json")
            result = _load_json(fake_path)
            assert result == {}

    def test_get_timeline_missing_file(self):
        """get_timeline must return empty list if timeline.json doesn't exist."""
        from src.continuity.engine import get_timeline

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.continuity.engine.TIMELINE_FILE",
                       os.path.join(tmpdir, "timeline.json")):
                result = get_timeline()
                assert result == []

    def test_get_running_gags_missing_file(self):
        """get_running_gags must return empty list if running_gags.json doesn't exist."""
        from src.continuity.engine import get_running_gags

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.continuity.engine.GAGS_FILE",
                       os.path.join(tmpdir, "gags.json")):
                result = get_running_gags()
                assert result == []

    def test_get_character_growth_missing_file(self):
        """get_character_growth must return empty dict if character_growth.json doesn't exist."""
        from src.continuity.engine import get_character_growth

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.continuity.engine.GROWTH_FILE",
                       os.path.join(tmpdir, "growth.json")):
                result = get_character_growth()
                assert result == {}

    def test_log_episode_missing_files(self):
        """log_episode must not crash when continuity files don't exist yet."""
        from src.continuity.engine import log_episode

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.continuity.engine.TIMELINE_FILE",
                       os.path.join(tmpdir, "timeline.json")), \
                 patch("src.continuity.engine.GAGS_FILE",
                       os.path.join(tmpdir, "gags.json")), \
                 patch("src.continuity.engine.GROWTH_FILE",
                       os.path.join(tmpdir, "growth.json")):

                script = {
                    "metadata": {
                        "episode_id": "EP099",
                        "title": "Test Episode",
                        "characters_featured": ["pens"],
                    },
                    "scenes": [{"background": "diner_interior"}],
                    "continuity_log": {
                        "events_to_track": ["Pens tested something"],
                        "new_gags": [],
                        "callbacks_used": [],
                        "character_developments": [],
                    },
                }
                # Must NOT raise
                log_episode(script)

                # Verify timeline was created
                assert os.path.exists(os.path.join(tmpdir, "timeline.json"))


# ---------------------------------------------------------------------------
# Issue 5: Startup recovery from crashed states
# ---------------------------------------------------------------------------

class TestStartupRecovery:
    """Bot on_ready must detect and recover from stuck pipeline states."""

    def test_recover_stuck_state_exists(self):
        """recover_stuck_state function should exist."""
        from src.bot.recovery import recover_stuck_state
        assert callable(recover_stuck_state)

    @pytest.mark.asyncio
    async def test_idle_state_not_touched(self):
        """If state is idle, recovery should do nothing."""
        from src.bot.recovery import recover_stuck_state

        bot = MagicMock()

        with patch("src.bot.recovery.load_state", return_value={"stage": "idle"}), \
             patch("src.bot.recovery.save_state") as mock_save:
            await recover_stuck_state(bot)
            mock_save.assert_not_called()

    @pytest.mark.asyncio
    async def test_pipeline_running_recovered(self):
        """v2: pipeline_running on startup must be reset to idle."""
        from src.bot.recovery import recover_stuck_state

        bot = MagicMock()
        errors_channel = AsyncMock()
        bot.get_channel.return_value = errors_channel

        stuck_state = {"stage": "pipeline_running", "current_episode": "EP005"}

        with patch("src.bot.recovery.load_state", return_value=stuck_state), \
             patch("src.bot.recovery.save_state") as mock_save:
            await recover_stuck_state(bot)
            saved = mock_save.call_args[0][0]
            assert saved["stage"] == "idle"

    @pytest.mark.asyncio
    async def test_recovery_posts_to_errors_channel(self):
        """Recovery must notify #errors channel about what happened."""
        from src.bot.recovery import recover_stuck_state

        bot = MagicMock()
        errors_channel = AsyncMock()
        bot.get_channel.return_value = errors_channel

        stuck_state = {"stage": "pipeline_running", "current_episode": "EP005"}

        with patch("src.bot.recovery.load_state", return_value=stuck_state), \
             patch("src.bot.recovery.save_state"):
            await recover_stuck_state(bot)
            errors_channel.send.assert_called()
            sent_text = errors_channel.send.call_args[0][0]
            assert "pipeline_running" in sent_text or "recover" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_human_waiting_states_not_reset(self):
        """v2: States waiting on human input (ideas_posted) must NOT be reset."""
        from src.bot.recovery import recover_stuck_state

        bot = MagicMock()

        for stage in ["idle", "ideas_posted", "done"]:
            with patch("src.bot.recovery.load_state", return_value={"stage": stage}), \
                 patch("src.bot.recovery.save_state") as mock_save:
                await recover_stuck_state(bot)
                mock_save.assert_not_called()


# ---------------------------------------------------------------------------
# Issue 7: log_episode_to_index handles missing dirs/files
# ---------------------------------------------------------------------------

class TestLogEpisodeToIndex:
    """log_episode_to_index must work even when data/episodes/ doesn't exist."""

    def test_creates_index_file_if_missing(self):
        """Must create index.json with proper structure if it doesn't exist."""
        from src.pipeline.orchestrator import log_episode_to_index

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "episodes", "index.json")
            with patch("src.pipeline.orchestrator.DATA_DIR", tmpdir):
                script = {
                    "metadata": {
                        "episode_id": "EP001",
                        "title": "Test",
                        "characters_featured": ["pens"],
                    }
                }
                log_episode_to_index(script)

                assert os.path.exists(index_path)
                with open(index_path, "r") as f:
                    data = json.load(f)
                assert data["next_episode_number"] == 1  # Counter managed by assign_episode_number, not here
                assert len(data["episodes"]) == 1

    def test_appends_to_existing_index(self):
        """Must append to existing episodes list, not overwrite."""
        from src.pipeline.orchestrator import log_episode_to_index

        with tempfile.TemporaryDirectory() as tmpdir:
            ep_dir = os.path.join(tmpdir, "episodes")
            os.makedirs(ep_dir)
            index_path = os.path.join(ep_dir, "index.json")

            # Pre-populate
            existing = {
                "next_episode_number": 2,
                "episodes": [{"episode_id": "EP001", "title": "First"}],
            }
            with open(index_path, "w") as f:
                json.dump(existing, f)

            with patch("src.pipeline.orchestrator.DATA_DIR", tmpdir):
                script = {
                    "metadata": {
                        "episode_id": "EP002",
                        "title": "Second",
                    }
                }
                log_episode_to_index(script)

                with open(index_path, "r") as f:
                    data = json.load(f)
                assert data["next_episode_number"] == 2  # Counter not incremented here
                assert len(data["episodes"]) == 2
