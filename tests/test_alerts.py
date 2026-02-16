"""Tests for the centralized error alerting module."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.alerts import (
    ERRORS_CHANNEL_KEY,
    format_error_message,
    format_startup_message,
    notify_error,
    notify_startup,
)


# ---------------------------------------------------------------------------
# format_error_message
# ---------------------------------------------------------------------------


class TestFormatErrorMessage:
    """Tests for format_error_message()."""

    def test_includes_stage_name(self):
        msg = format_error_message("Script Generation", "EP002", "API timeout")
        assert "Script Generation" in msg

    def test_includes_episode_id(self):
        msg = format_error_message("Video Generation", "EP003", "FFmpeg crash")
        assert "EP003" in msg

    def test_includes_error_text(self):
        msg = format_error_message("Publishing", "EP001", "Token expired")
        assert "Token expired" in msg

    def test_includes_timestamp(self):
        msg = format_error_message("Script Generation", "EP002", "fail")
        today = datetime.utcnow().strftime("%Y-%m-%d")
        assert today in msg

    def test_none_episode_shows_na(self):
        msg = format_error_message("Daily Pipeline Trigger", None, "timeout")
        assert "N/A" in msg

    def test_stage_is_bold(self):
        msg = format_error_message("Script Generation", "EP002", "err")
        assert "**Script Generation**" in msg

    def test_long_error_message_not_truncated_under_limit(self):
        error = "x" * 500
        msg = format_error_message("Stage", "EP001", error)
        assert error in msg

    def test_very_long_error_message_truncated(self):
        error = "x" * 2000
        msg = format_error_message("Stage", "EP001", error)
        # Message should not exceed Discord's 2000 char limit
        assert len(msg) <= 2000


# ---------------------------------------------------------------------------
# format_startup_message
# ---------------------------------------------------------------------------


class TestFormatStartupMessage:
    """Tests for format_startup_message()."""

    def test_includes_online_text(self):
        msg = format_startup_message()
        lower = msg.lower()
        assert "online" in lower or "started" in lower or "running" in lower

    def test_includes_timestamp(self):
        msg = format_startup_message()
        today = datetime.utcnow().strftime("%Y-%m-%d")
        assert today in msg


# ---------------------------------------------------------------------------
# notify_error (async)
# ---------------------------------------------------------------------------


class TestNotifyError:
    """Tests for the async notify_error() function."""

    @pytest.fixture
    def mock_bot(self):
        bot = MagicMock()
        channel = AsyncMock()
        bot.get_channel.return_value = channel
        return bot, channel

    @pytest.mark.asyncio
    async def test_sends_message_to_errors_channel(self, mock_bot):
        bot, channel = mock_bot
        await notify_error(bot, "Script Generation", "EP002", "API timeout")
        channel.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_contains_stage(self, mock_bot):
        bot, channel = mock_bot
        await notify_error(bot, "Video Generation", "EP003", "crash")
        sent_text = channel.send.call_args[0][0]
        assert "Video Generation" in sent_text

    @pytest.mark.asyncio
    async def test_message_contains_error(self, mock_bot):
        bot, channel = mock_bot
        await notify_error(bot, "Publishing", "EP001", "Token expired")
        sent_text = channel.send.call_args[0][0]
        assert "Token expired" in sent_text

    @pytest.mark.asyncio
    async def test_message_contains_episode_id(self, mock_bot):
        bot, channel = mock_bot
        await notify_error(bot, "Stage", "EP005", "err")
        sent_text = channel.send.call_args[0][0]
        assert "EP005" in sent_text

    @pytest.mark.asyncio
    async def test_handles_missing_channel_gracefully(self):
        bot = MagicMock()
        bot.get_channel.return_value = None
        # Should not raise
        await notify_error(bot, "Stage", "EP001", "err")

    @pytest.mark.asyncio
    async def test_handles_channel_send_failure_gracefully(self, mock_bot):
        bot, channel = mock_bot
        channel.send.side_effect = Exception("Discord API down")
        # Should not raise — alerting itself should never crash the bot
        await notify_error(bot, "Stage", "EP001", "err")

    @pytest.mark.asyncio
    async def test_looks_up_correct_channel_key(self, mock_bot):
        bot, channel = mock_bot
        from src.bot.bot import CHANNEL_IDS

        with patch.dict(CHANNEL_IDS, {"errors": 1473064771040313449}):
            await notify_error(bot, "Stage", "EP001", "err")
            bot.get_channel.assert_called_with(1473064771040313449)


# ---------------------------------------------------------------------------
# notify_startup (async)
# ---------------------------------------------------------------------------


class TestNotifyStartup:
    """Tests for the async notify_startup() function."""

    @pytest.fixture
    def mock_bot(self):
        bot = MagicMock()
        channel = AsyncMock()
        bot.get_channel.return_value = channel
        return bot, channel

    @pytest.mark.asyncio
    async def test_sends_startup_message(self, mock_bot):
        bot, channel = mock_bot
        await notify_startup(bot)
        channel.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_message_content(self, mock_bot):
        bot, channel = mock_bot
        await notify_startup(bot)
        sent_text = channel.send.call_args[0][0]
        lower = sent_text.lower()
        assert "online" in lower or "started" in lower or "running" in lower

    @pytest.mark.asyncio
    async def test_handles_missing_channel_gracefully(self):
        bot = MagicMock()
        bot.get_channel.return_value = None
        # Should not raise
        await notify_startup(bot)

    @pytest.mark.asyncio
    async def test_handles_send_failure_gracefully(self, mock_bot):
        bot, channel = mock_bot
        channel.send.side_effect = Exception("Discord API down")
        # Should not raise
        await notify_startup(bot)


# ---------------------------------------------------------------------------
# ERRORS_CHANNEL_KEY constant
# ---------------------------------------------------------------------------


class TestErrorsChannelKey:
    """Tests for the ERRORS_CHANNEL_KEY constant."""

    def test_key_value(self):
        assert ERRORS_CHANNEL_KEY == "errors"
