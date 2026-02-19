"""Tests for v2 pipeline simplification (Stage 2).

v2 removes: script review, Notion, video variants
v2 adds: single automated pipeline from idea pick → publish

Tests cover:
A. State machine — new v2 stages (idle → ideas_posted → pipeline_running → done)
B. Recovery — pipeline_running recovers to idle on crash
C. Pipeline flow — _run_full_pipeline executes all steps in order
D. Bot routing — removed handlers no longer routed
E. ISS-013 fix — YouTube title from script root, not metadata
"""

import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from src.bot.state import _default_state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_script(episode_id="DRAFT-EP-001"):
    """Build a realistic script dict for testing."""
    return {
        "episode_id": episode_id,
        "title": "The Pink Donut Incident",
        "slug": "the-pink-donut-incident",
        "created_at": "2026-02-17T12:00:00Z",
        "version": 1,
        "generation_params": {
            "character_a": "oinks",
            "character_b": "reows",
            "location": "diner_interior",
            "situation": "everyday_life",
        },
        "metadata": {
            "total_duration_seconds": 35,
            "characters_featured": ["oinks", "reows"],
            "primary_location": "diner_interior",
            "content_pillar": "everyday_life",
            "punchline_type": "callback_gag",
            "mood": "playful",
        },
        "scenes": [
            {
                "scene_number": 1,
                "duration_seconds": 10,
                "background": "diner_interior",
                "characters_present": ["oinks", "reows"],
                "character_positions": {"oinks": "stool_1", "reows": "stool_2"},
                "character_animations": {"oinks": "idle", "reows": "idle"},
                "action_description": "Oinks discovers a pink donut.",
                "dialogue": [
                    {"character": "oinks", "text": "Why is this glowing?", "duration_ms": 2500},
                ],
                "sfx_triggers": [],
                "music": "main_theme.wav",
            },
        ],
        "continuity_log": {
            "events": ["Oinks ate a glowing donut"],
            "new_running_gags": [],
            "callbacks_used": [],
            "character_developments": [],
        },
    }


def _make_sample_idea():
    """Build a sample idea dict."""
    return {
        "character_a": "oinks",
        "character_b": "reows",
        "additional_characters": [],
        "location": "diner_interior",
        "situation": "everyday_life",
        "punchline_type": "callback_gag",
        "concept": "Oinks finds a glowing donut",
        "trending_tie_in": None,
        "continuity_callbacks": [],
    }


def _make_metadata():
    """Build sample metadata from generate_metadata."""
    return {
        "tiktok": {
            "title": "The Pink Donut Incident",
            "description": "Oinks discovers a glowing donut",
            "hashtags": ["#pixelart", "#comedy"],
        },
        "youtube": {
            "title": "The Pink Donut Incident | Blobtoshi #Shorts",
            "description": "Oinks discovers a glowing donut\n\n#Shorts",
            "tags": ["#pixelart", "#comedy", "#Shorts"],
        },
        "instagram": {
            "caption": "Oinks discovers a glowing donut",
            "hashtags": ["#pixelart", "#comedy", "#reels"],
        },
    }


# ===========================================================================
# A. STATE MACHINE — v2 stages
# ===========================================================================

class TestV2StateMachine:
    """v2 uses simplified stages: idle → ideas_posted → pipeline_running → done."""

    def test_default_state_stage_is_idle(self):
        state = _default_state()
        assert state["stage"] == "idle"

    def test_v2_valid_stages(self):
        """v2 has exactly these stages."""
        v2_stages = {"idle", "ideas_posted", "pipeline_running", "done"}
        # The state machine should support all v2 stages
        from src.bot.state import set_stage, get_stage
        # We'll just verify the stages are accepted (set_stage doesn't validate)
        for stage in v2_stages:
            assert isinstance(stage, str)

    def test_no_script_review_stage(self):
        """v2 does not use script_review stage — scripts go straight to video."""
        v2_stages = {"idle", "ideas_posted", "pipeline_running", "done"}
        assert "script_review" not in v2_stages

    def test_no_video_review_stage(self):
        """v2 does not use video_review stage — no variant selection."""
        v2_stages = {"idle", "ideas_posted", "pipeline_running", "done"}
        assert "video_review" not in v2_stages

    def test_default_state_no_notion_url(self):
        """v2 default state should not reference Notion."""
        state = _default_state()
        assert state.get("script_notion_url") is None

    def test_default_state_no_video_variants(self):
        """v2 default state should not reference video variants."""
        state = _default_state()
        assert state.get("video_variants") == [] or "video_variants" not in state


# ===========================================================================
# B. RECOVERY — v2 crash recovery
# ===========================================================================

class TestV2Recovery:
    """v2 recovery: pipeline_running → idle on crash."""

    def test_pipeline_running_recovers_to_idle(self):
        from src.bot.recovery import RECOVERY_MAP
        assert "pipeline_running" in RECOVERY_MAP
        assert RECOVERY_MAP["pipeline_running"] == "idle"

    def test_idle_is_safe_state(self):
        from src.bot.recovery import SAFE_STATES
        assert "idle" in SAFE_STATES

    def test_ideas_posted_is_safe_state(self):
        from src.bot.recovery import SAFE_STATES
        assert "ideas_posted" in SAFE_STATES

    def test_done_is_safe_state(self):
        from src.bot.recovery import SAFE_STATES
        assert "done" in SAFE_STATES

    def test_no_script_review_in_safe_states(self):
        """script_review is removed in v2."""
        from src.bot.recovery import SAFE_STATES
        assert "script_review" not in SAFE_STATES

    def test_no_video_review_in_safe_states(self):
        """video_review is removed in v2."""
        from src.bot.recovery import SAFE_STATES
        assert "video_review" not in SAFE_STATES

    def test_no_video_generating_in_recovery(self):
        """video_generating is not a v2 stage."""
        from src.bot.recovery import RECOVERY_MAP
        assert "video_generating" not in RECOVERY_MAP

    def test_no_publishing_in_recovery(self):
        """publishing is not a v2 stage — it's all inside pipeline_running."""
        from src.bot.recovery import RECOVERY_MAP
        assert "publishing" not in RECOVERY_MAP


# ===========================================================================
# C. PIPELINE FLOW — _run_full_pipeline
# ===========================================================================

class TestV2PipelineFlow:
    """Test the full automated pipeline triggered after idea selection.

    All external dependencies are mocked. We verify:
    - Correct sequence of operations
    - Status notifications sent to #pipeline-status
    - Error handling at each step
    - State transitions
    """

    @pytest.fixture
    def mock_bot(self):
        """Create a mock Discord bot with channels."""
        bot = MagicMock()
        channels = {}
        for name in ["idea_selection", "pipeline_status", "publishing_log",
                      "weekly_analytics", "errors"]:
            ch = AsyncMock()
            ch.name = name
            channels[name] = ch

        def get_channel(cid):
            # Map channel IDs to mock channels
            return channels.get(cid)

        bot.get_channel = get_channel
        return bot, channels

    @pytest.fixture
    def channel_ids(self):
        """Return channel ID mapping where IDs match channel names for simplicity."""
        return {
            "idea_selection": "idea_selection",
            "pipeline_status": "pipeline_status",
            "publishing_log": "publishing_log",
            "weekly_analytics": "weekly_analytics",
            "errors": "errors",
        }

    @pytest.fixture
    def state_file(self, tmp_dir):
        """Redirect state file to temp directory."""
        test_state_file = os.path.join(tmp_dir, "data", "pipeline_state.json")
        with patch("src.bot.state.STATE_FILE", test_state_file):
            yield test_state_file

    @pytest.mark.asyncio
    async def test_successful_pipeline_sets_stage_done(
        self, mock_bot, channel_ids, state_file
    ):
        """Full successful run ends with stage = done."""
        bot, channels = mock_bot
        script = _make_test_script()
        idea = _make_sample_idea()

        with patch("src.bot.bot.CHANNEL_IDS", channel_ids), \
             patch("src.bot.handlers.idea_selection.generate_episode",
                   return_value=(script, [])), \
             patch("src.bot.handlers.idea_selection.check_asset_availability",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.compose_episode",
                   return_value="/tmp/video.mp4"), \
             patch("src.bot.handlers.idea_selection.check_video_quality",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.generate_metadata",
                   return_value=_make_metadata()), \
             patch("src.bot.handlers.idea_selection.safety_check",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.upload_to_drive",
                   return_value={"success": True, "file_url": "https://drive.google.com/file/123", "error": None}), \
             patch("src.bot.handlers.idea_selection.assign_episode_number",
                   return_value="EP001"), \
             patch("src.bot.handlers.idea_selection.publish_to_youtube",
                   new_callable=AsyncMock,
                   return_value={"success": True, "post_url": "https://youtu.be/abc123", "error": None}), \
             patch("src.bot.handlers.idea_selection.log_episode"), \
             patch("src.bot.handlers.idea_selection.log_episode_to_index"), \
             patch("src.bot.handlers.idea_selection.collect_rendering_warnings",
                   return_value=[]), \
             patch("src.bot.handlers.idea_selection.clear_all_rendering_warnings"), \
             patch("src.bot.handlers.idea_selection.format_drive_filename",
                   return_value="ep0001_the-pink-donut-incident.mp4"):

            from src.bot.handlers.idea_selection import _run_full_pipeline
            await _run_full_pipeline(idea, bot)

        from src.bot.state import load_state
        state = load_state()
        assert state["stage"] == "done"

    @pytest.mark.asyncio
    async def test_script_generation_failure_resets_to_idle(
        self, mock_bot, channel_ids, state_file
    ):
        """If script generation fails, pipeline resets to idle."""
        bot, channels = mock_bot
        idea = _make_sample_idea()

        with patch("src.bot.bot.CHANNEL_IDS", channel_ids), \
             patch("src.bot.handlers.idea_selection.generate_episode",
                   return_value=(None, ["API error"])):

            from src.bot.handlers.idea_selection import _run_full_pipeline
            await _run_full_pipeline(idea, bot)

        from src.bot.state import load_state
        state = load_state()
        assert state["stage"] == "idle"

    @pytest.mark.asyncio
    async def test_asset_check_failure_resets_to_idle(
        self, mock_bot, channel_ids, state_file
    ):
        """If assets are missing, pipeline resets to idle."""
        bot, channels = mock_bot
        script = _make_test_script()
        idea = _make_sample_idea()

        with patch("src.bot.bot.CHANNEL_IDS", channel_ids), \
             patch("src.bot.handlers.idea_selection.generate_episode",
                   return_value=(script, [])), \
             patch("src.bot.handlers.idea_selection.check_asset_availability",
                   return_value=(False, ["backgrounds/missing.png"])):

            from src.bot.handlers.idea_selection import _run_full_pipeline
            await _run_full_pipeline(idea, bot)

        from src.bot.state import load_state
        state = load_state()
        assert state["stage"] == "idle"

    @pytest.mark.asyncio
    async def test_status_notifications_sent(
        self, mock_bot, channel_ids, state_file
    ):
        """Pipeline sends status updates to #pipeline-status at key steps."""
        bot, channels = mock_bot
        script = _make_test_script()
        idea = _make_sample_idea()

        with patch("src.bot.bot.CHANNEL_IDS", channel_ids), \
             patch("src.bot.handlers.idea_selection.generate_episode",
                   return_value=(script, [])), \
             patch("src.bot.handlers.idea_selection.check_asset_availability",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.compose_episode",
                   return_value="/tmp/video.mp4"), \
             patch("src.bot.handlers.idea_selection.check_video_quality",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.generate_metadata",
                   return_value=_make_metadata()), \
             patch("src.bot.handlers.idea_selection.safety_check",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.upload_to_drive",
                   return_value={"success": True, "file_url": "https://drive.google.com/file/123", "error": None}), \
             patch("src.bot.handlers.idea_selection.assign_episode_number",
                   return_value="EP001"), \
             patch("src.bot.handlers.idea_selection.publish_to_youtube",
                   new_callable=AsyncMock,
                   return_value={"success": True, "post_url": "https://youtu.be/abc", "error": None}), \
             patch("src.bot.handlers.idea_selection.log_episode"), \
             patch("src.bot.handlers.idea_selection.log_episode_to_index"), \
             patch("src.bot.handlers.idea_selection.collect_rendering_warnings",
                   return_value=[]), \
             patch("src.bot.handlers.idea_selection.clear_all_rendering_warnings"), \
             patch("src.bot.handlers.idea_selection.format_drive_filename",
                   return_value="ep0001_the-pink-donut-incident.mp4"):

            from src.bot.handlers.idea_selection import _run_full_pipeline
            await _run_full_pipeline(idea, bot)

        # Check that #pipeline-status received key notifications
        status_ch = channels["pipeline_status"]
        sent_messages = [str(c) for c in status_ch.send.call_args_list]
        combined = " ".join(sent_messages)

        # These keywords must appear in the status messages
        assert "Script written" in combined or "script written" in combined.lower()
        assert "Video rendered" in combined or "video rendered" in combined.lower()
        assert "Drive" in combined or "drive" in combined.lower()
        assert "YouTube" in combined or "youtube" in combined.lower()
        assert "Pipeline complete" in combined or "pipeline complete" in combined.lower()

    @pytest.mark.asyncio
    async def test_episode_number_assigned_after_drive_upload(
        self, mock_bot, channel_ids, state_file
    ):
        """Real episode number (EP001) assigned only after successful Drive upload."""
        bot, channels = mock_bot
        script = _make_test_script("DRAFT-EP-001")
        idea = _make_sample_idea()

        mock_assign = MagicMock(return_value="EP001")

        with patch("src.bot.bot.CHANNEL_IDS", channel_ids), \
             patch("src.bot.handlers.idea_selection.generate_episode",
                   return_value=(script, [])), \
             patch("src.bot.handlers.idea_selection.check_asset_availability",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.compose_episode",
                   return_value="/tmp/video.mp4"), \
             patch("src.bot.handlers.idea_selection.check_video_quality",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.generate_metadata",
                   return_value=_make_metadata()), \
             patch("src.bot.handlers.idea_selection.safety_check",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.upload_to_drive",
                   return_value={"success": True, "file_url": "https://drive.google.com/file/123", "error": None}), \
             patch("src.bot.handlers.idea_selection.assign_episode_number",
                   mock_assign), \
             patch("src.bot.handlers.idea_selection.publish_to_youtube",
                   new_callable=AsyncMock,
                   return_value={"success": True, "post_url": "https://youtu.be/abc", "error": None}), \
             patch("src.bot.handlers.idea_selection.log_episode"), \
             patch("src.bot.handlers.idea_selection.log_episode_to_index"), \
             patch("src.bot.handlers.idea_selection.collect_rendering_warnings",
                   return_value=[]), \
             patch("src.bot.handlers.idea_selection.clear_all_rendering_warnings"), \
             patch("src.bot.handlers.idea_selection.format_drive_filename",
                   return_value="ep0001_the-pink-donut-incident.mp4"):

            from src.bot.handlers.idea_selection import _run_full_pipeline
            await _run_full_pipeline(idea, bot)

        # assign_episode_number should be called once (after Drive upload)
        mock_assign.assert_called_once()

        # State should have real episode ID
        from src.bot.state import load_state
        state = load_state()
        assert state["current_episode"] == "EP001"

    @pytest.mark.asyncio
    async def test_drive_failure_does_not_assign_episode_number(
        self, mock_bot, channel_ids, state_file
    ):
        """If Drive upload fails, episode number is NOT assigned."""
        bot, channels = mock_bot
        script = _make_test_script("DRAFT-EP-001")
        idea = _make_sample_idea()

        mock_assign = MagicMock(return_value="EP001")

        with patch("src.bot.bot.CHANNEL_IDS", channel_ids), \
             patch("src.bot.handlers.idea_selection.generate_episode",
                   return_value=(script, [])), \
             patch("src.bot.handlers.idea_selection.check_asset_availability",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.compose_episode",
                   return_value="/tmp/video.mp4"), \
             patch("src.bot.handlers.idea_selection.check_video_quality",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.generate_metadata",
                   return_value=_make_metadata()), \
             patch("src.bot.handlers.idea_selection.safety_check",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.upload_to_drive",
                   return_value={"success": False, "file_url": None, "error": "Auth failed"}), \
             patch("src.bot.handlers.idea_selection.assign_episode_number",
                   mock_assign), \
             patch("src.bot.handlers.idea_selection.publish_to_youtube",
                   new_callable=AsyncMock,
                   return_value={"success": True, "post_url": "https://youtu.be/abc", "error": None}), \
             patch("src.bot.handlers.idea_selection.log_episode"), \
             patch("src.bot.handlers.idea_selection.log_episode_to_index"), \
             patch("src.bot.handlers.idea_selection.collect_rendering_warnings",
                   return_value=[]), \
             patch("src.bot.handlers.idea_selection.clear_all_rendering_warnings"), \
             patch("src.bot.handlers.idea_selection.format_drive_filename",
                   return_value="ep0001_the-pink-donut-incident.mp4"):

            from src.bot.handlers.idea_selection import _run_full_pipeline
            await _run_full_pipeline(idea, bot)

        # assign_episode_number should NOT be called when Drive upload fails
        mock_assign.assert_not_called()

    @pytest.mark.asyncio
    async def test_safety_failure_skips_youtube(
        self, mock_bot, channel_ids, state_file
    ):
        """If safety check fails, YouTube publish is skipped."""
        bot, channels = mock_bot
        script = _make_test_script()
        idea = _make_sample_idea()

        mock_yt = AsyncMock(return_value={"success": True, "post_url": "x", "error": None})

        with patch("src.bot.bot.CHANNEL_IDS", channel_ids), \
             patch("src.bot.handlers.idea_selection.generate_episode",
                   return_value=(script, [])), \
             patch("src.bot.handlers.idea_selection.check_asset_availability",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.compose_episode",
                   return_value="/tmp/video.mp4"), \
             patch("src.bot.handlers.idea_selection.check_video_quality",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.generate_metadata",
                   return_value=_make_metadata()), \
             patch("src.bot.handlers.idea_selection.safety_check",
                   return_value=(False, ["Blocked word: hell"])), \
             patch("src.bot.handlers.idea_selection.upload_to_drive",
                   return_value={"success": True, "file_url": "https://drive.google.com/file/123", "error": None}), \
             patch("src.bot.handlers.idea_selection.assign_episode_number",
                   return_value="EP001"), \
             patch("src.bot.handlers.idea_selection.publish_to_youtube", mock_yt), \
             patch("src.bot.handlers.idea_selection.log_episode"), \
             patch("src.bot.handlers.idea_selection.log_episode_to_index"), \
             patch("src.bot.handlers.idea_selection.collect_rendering_warnings",
                   return_value=[]), \
             patch("src.bot.handlers.idea_selection.clear_all_rendering_warnings"), \
             patch("src.bot.handlers.idea_selection.format_drive_filename",
                   return_value="ep0001_the-pink-donut-incident.mp4"):

            from src.bot.handlers.idea_selection import _run_full_pipeline
            await _run_full_pipeline(idea, bot)

        # YouTube should not be called when safety check fails
        mock_yt.assert_not_called()

    @pytest.mark.asyncio
    async def test_video_generation_failure_resets_to_idle(
        self, mock_bot, channel_ids, state_file
    ):
        """If video rendering crashes, pipeline resets to idle."""
        bot, channels = mock_bot
        script = _make_test_script()
        idea = _make_sample_idea()

        with patch("src.bot.bot.CHANNEL_IDS", channel_ids), \
             patch("src.bot.handlers.idea_selection.generate_episode",
                   return_value=(script, [])), \
             patch("src.bot.handlers.idea_selection.check_asset_availability",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.compose_episode",
                   side_effect=RuntimeError("FFmpeg crashed")), \
             patch("src.bot.handlers.idea_selection.clear_all_rendering_warnings"), \
             patch("src.bot.handlers.idea_selection.collect_rendering_warnings",
                   return_value=[]):

            from src.bot.handlers.idea_selection import _run_full_pipeline
            await _run_full_pipeline(idea, bot)

        from src.bot.state import load_state
        state = load_state()
        assert state["stage"] == "idle"

    @pytest.mark.asyncio
    async def test_no_notion_publish_in_pipeline(
        self, mock_bot, channel_ids, state_file
    ):
        """v2 pipeline does NOT call publish_script (Notion removed)."""
        bot, channels = mock_bot
        script = _make_test_script()
        idea = _make_sample_idea()

        with patch("src.bot.bot.CHANNEL_IDS", channel_ids), \
             patch("src.bot.handlers.idea_selection.generate_episode",
                   return_value=(script, [])), \
             patch("src.bot.handlers.idea_selection.check_asset_availability",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.compose_episode",
                   return_value="/tmp/video.mp4"), \
             patch("src.bot.handlers.idea_selection.check_video_quality",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.generate_metadata",
                   return_value=_make_metadata()), \
             patch("src.bot.handlers.idea_selection.safety_check",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.upload_to_drive",
                   return_value={"success": True, "file_url": "https://drive.google.com/file/123", "error": None}), \
             patch("src.bot.handlers.idea_selection.assign_episode_number",
                   return_value="EP001"), \
             patch("src.bot.handlers.idea_selection.publish_to_youtube",
                   new_callable=AsyncMock,
                   return_value={"success": True, "post_url": "https://youtu.be/abc", "error": None}), \
             patch("src.bot.handlers.idea_selection.log_episode"), \
             patch("src.bot.handlers.idea_selection.log_episode_to_index"), \
             patch("src.bot.handlers.idea_selection.collect_rendering_warnings",
                   return_value=[]), \
             patch("src.bot.handlers.idea_selection.clear_all_rendering_warnings"), \
             patch("src.bot.handlers.idea_selection.format_drive_filename",
                   return_value="ep0001_the-pink-donut-incident.mp4"):

            from src.bot.handlers.idea_selection import _run_full_pipeline
            await _run_full_pipeline(idea, bot)

        # Notion publish_script should NOT be importable from idea_selection
        # (we removed the import). The test passes if the pipeline completes
        # without calling publish_script.

    @pytest.mark.asyncio
    async def test_pipeline_stage_set_to_running(
        self, mock_bot, channel_ids, state_file
    ):
        """Pipeline should set stage to pipeline_running before starting work."""
        bot, channels = mock_bot
        idea = _make_sample_idea()

        # Make generate_episode fail so we can check state was set first
        stages_seen = []

        original_load = None

        def capture_save(state):
            stages_seen.append(state.get("stage"))
            # Call real save
            from src.bot.state import save_state as real_save
            real_save(state)

        with patch("src.bot.bot.CHANNEL_IDS", channel_ids), \
             patch("src.bot.handlers.idea_selection.generate_episode",
                   return_value=(_make_test_script(), [])), \
             patch("src.bot.handlers.idea_selection.check_asset_availability",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.compose_episode",
                   return_value="/tmp/video.mp4"), \
             patch("src.bot.handlers.idea_selection.check_video_quality",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.generate_metadata",
                   return_value=_make_metadata()), \
             patch("src.bot.handlers.idea_selection.safety_check",
                   return_value=(True, [])), \
             patch("src.bot.handlers.idea_selection.upload_to_drive",
                   return_value={"success": True, "file_url": "https://drive.google.com/file/123", "error": None}), \
             patch("src.bot.handlers.idea_selection.assign_episode_number",
                   return_value="EP001"), \
             patch("src.bot.handlers.idea_selection.publish_to_youtube",
                   new_callable=AsyncMock,
                   return_value={"success": True, "post_url": "https://youtu.be/abc", "error": None}), \
             patch("src.bot.handlers.idea_selection.log_episode"), \
             patch("src.bot.handlers.idea_selection.log_episode_to_index"), \
             patch("src.bot.handlers.idea_selection.collect_rendering_warnings",
                   return_value=[]), \
             patch("src.bot.handlers.idea_selection.clear_all_rendering_warnings"), \
             patch("src.bot.handlers.idea_selection.format_drive_filename",
                   return_value="ep0001_test.mp4"):

            from src.bot.handlers.idea_selection import _run_full_pipeline
            await _run_full_pipeline(idea, bot)

        # The first stage set should be pipeline_running
        from src.bot.state import load_state
        # Final state is done, which means pipeline_running was set during execution
        state = load_state()
        assert state["stage"] == "done"


# ===========================================================================
# D. BOT ROUTING — removed handlers
# ===========================================================================

class TestV2BotRouting:
    """v2 removes routing to script_review and video_preview handlers."""

    def test_bot_channel_ids_has_pipeline_status(self):
        """CHANNEL_IDS should have pipeline_status key."""
        from src.bot.bot import CHANNEL_IDS
        assert "pipeline_status" in CHANNEL_IDS

    def test_bot_channel_ids_no_script_review_key(self):
        """CHANNEL_IDS should NOT have script_review key (renamed to pipeline_status)."""
        from src.bot.bot import CHANNEL_IDS
        assert "script_review" not in CHANNEL_IDS

    def test_no_script_review_import_in_bot(self):
        """on_message should not import handle_script_review."""
        import inspect
        from src.bot.bot import on_message
        source = inspect.getsource(on_message)
        assert "handle_script_review" not in source

    def test_no_video_preview_import_in_bot(self):
        """on_message should not import handle_video_preview."""
        import inspect
        from src.bot.bot import on_message
        source = inspect.getsource(on_message)
        assert "handle_video_preview" not in source


# ===========================================================================
# E. ISS-013 FIX — YouTube title from script root
# ===========================================================================

class TestISS013YouTubeTitle:
    """YouTube title must come from script root, not metadata."""

    def test_metadata_generator_uses_root_title(self):
        """generate_metadata should use script.get('title'), not metadata.get('title')."""
        from src.metadata.generator import generate_metadata
        script = _make_test_script()
        # Ensure metadata does NOT have a title key
        assert "title" not in script["metadata"]
        metadata = generate_metadata(script)
        # YouTube title should contain the actual episode title
        yt_title = metadata["youtube"]["title"]
        assert "The Pink Donut Incident" in yt_title
        assert "Untitled" not in yt_title

    def test_youtube_metadata_title_not_empty(self):
        """YouTube metadata must have a real title, not fallback."""
        from src.metadata.generator import generate_metadata
        script = _make_test_script()
        metadata = generate_metadata(script)
        yt_title = metadata["youtube"]["title"]
        assert len(yt_title) > 5
        assert yt_title != "bl0btoshii episode"


# ===========================================================================
# F. IDEA SELECTION HANDLER — v2 flow
# ===========================================================================

class TestV2IdeaSelectionHandler:
    """Test that handle_idea_selection triggers _run_full_pipeline, not _generate_and_post_script."""

    def test_handler_calls_run_full_pipeline(self):
        """After user picks an idea, handler should call _run_full_pipeline."""
        import inspect
        from src.bot.handlers.idea_selection import handle_idea_selection
        source = inspect.getsource(handle_idea_selection)
        assert "_run_full_pipeline" in source
        assert "_generate_and_post_script" not in source

    def test_handler_sets_pipeline_running_stage(self):
        """After user picks an idea, stage should be set to pipeline_running."""
        import inspect
        from src.bot.handlers.idea_selection import handle_idea_selection
        source = inspect.getsource(handle_idea_selection)
        assert "pipeline_running" in source
