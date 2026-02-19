"""Tests for Stage 6: YouTube dual-publish.

Changes:
1. publish_to_youtube gains `is_short` parameter
   - is_short=True: keeps #Shorts in description (YouTube Shorts upload)
   - is_short=False: strips #Shorts from title and description (regular YouTube upload)
2. Pipeline Step 7 publishes horizontal as regular YouTube + vertical as YouTube Short

Test groups:
1. Short classification — #Shorts tag handling in publish_to_youtube
2. Pipeline dual-publish — Step 7 calls publish_to_youtube twice correctly
"""

import asyncio
import os
import tempfile
from unittest.mock import patch, AsyncMock, MagicMock, call

import pytest


# ---------------------------------------------------------------------------
# Short classification — is_short parameter controls #Shorts tag
# ---------------------------------------------------------------------------

class TestYouTubeShortClassification:
    """publish_to_youtube must handle #Shorts tag based on is_short parameter."""

    @patch("src.publisher.platforms._is_platform_enabled", return_value=True)
    @patch("src.publisher.platforms._youtube_get_access_token", return_value=("fake_token", None))
    @patch("src.publisher.platforms.requests.post")
    @patch("src.publisher.platforms.requests.put")
    def test_is_short_true_keeps_shorts_in_description(self, mock_put, mock_post, mock_token, mock_enabled):
        """When is_short=True, #Shorts should be in the description."""
        from src.publisher.platforms import publish_to_youtube

        # Mock successful upload flow
        mock_post.return_value = MagicMock(
            status_code=200,
            headers={"Location": "https://upload.example.com"},
        )
        mock_put.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "abc123"},
        )

        metadata = {
            "title": "Test Episode | Blobtoshi",
            "description": "A fun episode about donuts.",
            "tags": ["#pixelart"],
        }

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            result = asyncio.get_event_loop().run_until_complete(
                publish_to_youtube(tmp.name, metadata, is_short=True)
            )

        # Verify #Shorts is in the description sent to YouTube API
        api_call_kwargs = mock_post.call_args
        video_metadata = api_call_kwargs.kwargs.get("json") or api_call_kwargs[1].get("json")
        description = video_metadata["snippet"]["description"]
        assert "#Shorts" in description

    @patch("src.publisher.platforms._is_platform_enabled", return_value=True)
    @patch("src.publisher.platforms._youtube_get_access_token", return_value=("fake_token", None))
    @patch("src.publisher.platforms.requests.post")
    @patch("src.publisher.platforms.requests.put")
    def test_is_short_false_strips_shorts_from_description(self, mock_put, mock_post, mock_token, mock_enabled):
        """When is_short=False, #Shorts must NOT be in the description."""
        from src.publisher.platforms import publish_to_youtube

        mock_post.return_value = MagicMock(
            status_code=200,
            headers={"Location": "https://upload.example.com"},
        )
        mock_put.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "abc123"},
        )

        # Description already contains #Shorts from metadata generator
        metadata = {
            "title": "Test Episode | Blobtoshi #Shorts",
            "description": "A fun episode.\n\n#Shorts #Blobtoshi",
            "tags": ["#Shorts", "#pixelart"],
        }

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            result = asyncio.get_event_loop().run_until_complete(
                publish_to_youtube(tmp.name, metadata, is_short=False)
            )

        api_call_kwargs = mock_post.call_args
        video_metadata = api_call_kwargs.kwargs.get("json") or api_call_kwargs[1].get("json")
        description = video_metadata["snippet"]["description"]
        assert "#Shorts" not in description

    @patch("src.publisher.platforms._is_platform_enabled", return_value=True)
    @patch("src.publisher.platforms._youtube_get_access_token", return_value=("fake_token", None))
    @patch("src.publisher.platforms.requests.post")
    @patch("src.publisher.platforms.requests.put")
    def test_is_short_false_strips_shorts_from_title(self, mock_put, mock_post, mock_token, mock_enabled):
        """When is_short=False, #Shorts must NOT be in the title."""
        from src.publisher.platforms import publish_to_youtube

        mock_post.return_value = MagicMock(
            status_code=200,
            headers={"Location": "https://upload.example.com"},
        )
        mock_put.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "abc123"},
        )

        metadata = {
            "title": "Test Episode | Blobtoshi #Shorts",
            "description": "A fun episode.",
            "tags": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            result = asyncio.get_event_loop().run_until_complete(
                publish_to_youtube(tmp.name, metadata, is_short=False)
            )

        api_call_kwargs = mock_post.call_args
        video_metadata = api_call_kwargs.kwargs.get("json") or api_call_kwargs[1].get("json")
        title = video_metadata["snippet"]["title"]
        assert "#Shorts" not in title

    @patch("src.publisher.platforms._is_platform_enabled", return_value=True)
    @patch("src.publisher.platforms._youtube_get_access_token", return_value=("fake_token", None))
    @patch("src.publisher.platforms.requests.post")
    @patch("src.publisher.platforms.requests.put")
    def test_is_short_default_is_false(self, mock_put, mock_post, mock_token, mock_enabled):
        """Default value of is_short should be False (regular YouTube video)."""
        from src.publisher.platforms import publish_to_youtube

        mock_post.return_value = MagicMock(
            status_code=200,
            headers={"Location": "https://upload.example.com"},
        )
        mock_put.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "abc123"},
        )

        # Description with #Shorts from metadata generator
        metadata = {
            "title": "Test Episode",
            "description": "Episode content.\n\n#Shorts #Blobtoshi",
            "tags": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            # Call WITHOUT is_short — default should strip #Shorts
            result = asyncio.get_event_loop().run_until_complete(
                publish_to_youtube(tmp.name, metadata)
            )

        api_call_kwargs = mock_post.call_args
        video_metadata = api_call_kwargs.kwargs.get("json") or api_call_kwargs[1].get("json")
        description = video_metadata["snippet"]["description"]
        # Default is_short=False means #Shorts should be stripped
        assert "#Shorts" not in description

    @patch("src.publisher.platforms._is_platform_enabled", return_value=True)
    @patch("src.publisher.platforms._youtube_get_access_token", return_value=("fake_token", None))
    @patch("src.publisher.platforms.requests.post")
    @patch("src.publisher.platforms.requests.put")
    def test_is_short_false_preserves_other_hashtags(self, mock_put, mock_post, mock_token, mock_enabled):
        """When stripping #Shorts, other hashtags must be preserved."""
        from src.publisher.platforms import publish_to_youtube

        mock_post.return_value = MagicMock(
            status_code=200,
            headers={"Location": "https://upload.example.com"},
        )
        mock_put.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "abc123"},
        )

        metadata = {
            "title": "Test Episode",
            "description": "Fun episode.\n\n#Shorts #Blobtoshi #pixelart",
            "tags": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            result = asyncio.get_event_loop().run_until_complete(
                publish_to_youtube(tmp.name, metadata, is_short=False)
            )

        api_call_kwargs = mock_post.call_args
        video_metadata = api_call_kwargs.kwargs.get("json") or api_call_kwargs[1].get("json")
        description = video_metadata["snippet"]["description"]
        assert "#Blobtoshi" in description
        assert "#pixelart" in description
        assert "#Shorts" not in description

    @patch("src.publisher.platforms._is_platform_enabled", return_value=True)
    @patch("src.publisher.platforms._youtube_get_access_token", return_value=("fake_token", None))
    @patch("src.publisher.platforms.requests.post")
    @patch("src.publisher.platforms.requests.put")
    def test_is_short_true_returns_success(self, mock_put, mock_post, mock_token, mock_enabled):
        """Upload should succeed when is_short=True."""
        from src.publisher.platforms import publish_to_youtube

        mock_post.return_value = MagicMock(
            status_code=200,
            headers={"Location": "https://upload.example.com"},
        )
        mock_put.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "short123"},
        )

        metadata = {"title": "Short Video", "description": "Test", "tags": []}

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            result = asyncio.get_event_loop().run_until_complete(
                publish_to_youtube(tmp.name, metadata, is_short=True)
            )

        assert result["success"] is True
        assert "youtu.be/short123" in result["post_url"]


# ---------------------------------------------------------------------------
# Pipeline dual-publish — Step 7 publishes both formats
# ---------------------------------------------------------------------------

class TestDualYouTubePublish:
    """Pipeline Step 7 must publish horizontal as regular + vertical as Short."""

    @pytest.fixture
    def mock_pipeline_deps(self):
        """Set up all the mocks needed to run _run_full_pipeline through Step 7."""
        patches = {
            "generate_episode": patch(
                "src.bot.handlers.idea_selection.generate_episode",
                return_value=({"episode_id": "DRAFT-EP-001", "title": "Test", "metadata": {"mood": "playful", "characters_featured": ["pens"]}, "scenes": [{"duration_seconds": 10, "dialogue": []}]}, []),
            ),
            "check_asset_availability": patch(
                "src.bot.handlers.idea_selection.check_asset_availability",
                return_value=(True, []),
            ),
            "compose_episode": patch(
                "src.bot.handlers.idea_selection.compose_episode",
                side_effect=lambda script, music, name, config: f"/tmp/video_{config.label}.mp4",
            ),
            "clear_all_rendering_warnings": patch(
                "src.bot.handlers.idea_selection.clear_all_rendering_warnings",
            ),
            "collect_rendering_warnings": patch(
                "src.bot.handlers.idea_selection.collect_rendering_warnings",
                return_value=[],
            ),
            "check_video_quality": patch(
                "src.bot.handlers.idea_selection.check_video_quality",
                return_value=(True, []),
            ),
            "generate_metadata": patch(
                "src.bot.handlers.idea_selection.generate_metadata",
                return_value={
                    "tiktok": {"title": "T"},
                    "youtube": {"title": "Test | Blobtoshi #Shorts", "description": "Ep.\n\n#Shorts #Blobtoshi", "tags": []},
                    "instagram": {"caption": "I"},
                },
            ),
            "safety_check": patch(
                "src.bot.handlers.idea_selection.safety_check",
                return_value=(True, []),
            ),
            "upload_to_drive": patch(
                "src.bot.handlers.idea_selection.upload_to_drive",
                return_value={"success": True, "file_url": "https://drive.example.com/file"},
            ),
            "format_drive_filename": patch(
                "src.bot.handlers.idea_selection.format_drive_filename",
                return_value="ep0001_test.mp4",
            ),
            "assign_episode_number": patch(
                "src.bot.handlers.idea_selection.assign_episode_number",
                return_value="EP001",
            ),
            "publish_to_youtube": patch(
                "src.bot.handlers.idea_selection.publish_to_youtube",
                new_callable=AsyncMock,
                return_value={"success": True, "post_url": "https://youtu.be/abc123", "error": None},
            ),
            "log_episode": patch(
                "src.bot.handlers.idea_selection.log_episode",
            ),
            "log_episode_to_index": patch(
                "src.bot.handlers.idea_selection.log_episode_to_index",
            ),
            "load_state": patch(
                "src.bot.handlers.idea_selection.load_state",
                return_value={"stage": "pipeline_running"},
            ),
            "save_state": patch(
                "src.bot.handlers.idea_selection.save_state",
            ),
            "os_path_exists": patch(
                "os.path.exists",
                return_value=True,
            ),
        }
        return patches

    def test_pipeline_calls_youtube_twice(self, mock_pipeline_deps):
        """Step 7 should call publish_to_youtube exactly twice."""
        from src.bot.handlers.idea_selection import _run_full_pipeline

        mocks = {}
        for name, p in mock_pipeline_deps.items():
            mocks[name] = p.start()

        try:
            # Set up bot mock
            bot = MagicMock()
            status_channel = AsyncMock()
            bot.get_channel.return_value = status_channel

            # Mock CHANNEL_IDS
            with patch("src.bot.handlers.idea_selection.CHANNEL_IDS",
                       {"pipeline_status": 1, "idea_selection": 2},
                       create=True), \
                 patch("src.bot.bot.CHANNEL_IDS",
                       {"pipeline_status": 1, "idea_selection": 2},
                       create=True):
                idea = {"character_a": "pens", "character_b": "chubs"}

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(_run_full_pipeline(idea, bot))
                finally:
                    loop.close()

                # publish_to_youtube should be called exactly twice
                assert mocks["publish_to_youtube"].call_count == 2
        finally:
            for p in mock_pipeline_deps.values():
                p.stop()

    def test_horizontal_published_as_regular_video(self, mock_pipeline_deps):
        """Horizontal video must be published with is_short=False."""
        from src.bot.handlers.idea_selection import _run_full_pipeline

        mocks = {}
        for name, p in mock_pipeline_deps.items():
            mocks[name] = p.start()

        try:
            bot = MagicMock()
            status_channel = AsyncMock()
            bot.get_channel.return_value = status_channel

            with patch("src.bot.handlers.idea_selection.CHANNEL_IDS",
                       {"pipeline_status": 1, "idea_selection": 2},
                       create=True), \
                 patch("src.bot.bot.CHANNEL_IDS",
                       {"pipeline_status": 1, "idea_selection": 2},
                       create=True):
                idea = {"character_a": "pens", "character_b": "chubs"}

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(_run_full_pipeline(idea, bot))
                finally:
                    loop.close()

                # First call should be horizontal (regular video, is_short=False)
                calls = mocks["publish_to_youtube"].call_args_list
                first_call = calls[0]
                # Check video path contains "horizontal"
                video_path_arg = first_call.args[0] if first_call.args else first_call.kwargs.get("video_path")
                assert "horizontal" in video_path_arg
                # Check is_short=False
                is_short_arg = first_call.kwargs.get("is_short", first_call.args[2] if len(first_call.args) > 2 else None)
                assert is_short_arg is False
        finally:
            for p in mock_pipeline_deps.values():
                p.stop()

    def test_vertical_published_as_short(self, mock_pipeline_deps):
        """Vertical video must be published with is_short=True."""
        from src.bot.handlers.idea_selection import _run_full_pipeline

        mocks = {}
        for name, p in mock_pipeline_deps.items():
            mocks[name] = p.start()

        try:
            bot = MagicMock()
            status_channel = AsyncMock()
            bot.get_channel.return_value = status_channel

            with patch("src.bot.handlers.idea_selection.CHANNEL_IDS",
                       {"pipeline_status": 1, "idea_selection": 2},
                       create=True), \
                 patch("src.bot.bot.CHANNEL_IDS",
                       {"pipeline_status": 1, "idea_selection": 2},
                       create=True):
                idea = {"character_a": "pens", "character_b": "chubs"}

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(_run_full_pipeline(idea, bot))
                finally:
                    loop.close()

                # Second call should be vertical (Short, is_short=True)
                calls = mocks["publish_to_youtube"].call_args_list
                second_call = calls[1]
                video_path_arg = second_call.args[0] if second_call.args else second_call.kwargs.get("video_path")
                assert "vertical" in video_path_arg
                is_short_arg = second_call.kwargs.get("is_short", second_call.args[2] if len(second_call.args) > 2 else None)
                assert is_short_arg is True
        finally:
            for p in mock_pipeline_deps.values():
                p.stop()

    def test_both_successes_reported_to_status(self, mock_pipeline_deps):
        """Both successful YouTube uploads should send status messages."""
        from src.bot.handlers.idea_selection import _run_full_pipeline

        mocks = {}
        for name, p in mock_pipeline_deps.items():
            mocks[name] = p.start()

        try:
            bot = MagicMock()
            status_channel = AsyncMock()
            bot.get_channel.return_value = status_channel

            with patch("src.bot.handlers.idea_selection.CHANNEL_IDS",
                       {"pipeline_status": 1, "idea_selection": 2},
                       create=True), \
                 patch("src.bot.bot.CHANNEL_IDS",
                       {"pipeline_status": 1, "idea_selection": 2},
                       create=True):
                idea = {"character_a": "pens", "character_b": "chubs"}

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(_run_full_pipeline(idea, bot))
                finally:
                    loop.close()

                # Check status messages contain both YouTube publish confirmations
                all_messages = [str(c) for c in status_channel.send.call_args_list]
                combined = " ".join(all_messages)
                assert "YouTube" in combined
                # Should mention both formats
                assert "horizontal" in combined.lower() or "regular" in combined.lower() or "Shorts" in combined
        finally:
            for p in mock_pipeline_deps.values():
                p.stop()

    def test_safety_failure_skips_both_uploads(self, mock_pipeline_deps):
        """If safety check fails, BOTH YouTube uploads should be skipped."""
        from src.bot.handlers.idea_selection import _run_full_pipeline

        mocks = {}
        for name, p in mock_pipeline_deps.items():
            mocks[name] = p.start()

        # Override safety_check to return unsafe
        mocks["safety_check"].return_value = (False, ["Blocked word: kill"])

        try:
            bot = MagicMock()
            status_channel = AsyncMock()
            bot.get_channel.return_value = status_channel

            with patch("src.bot.handlers.idea_selection.CHANNEL_IDS",
                       {"pipeline_status": 1, "idea_selection": 2},
                       create=True), \
                 patch("src.bot.bot.CHANNEL_IDS",
                       {"pipeline_status": 1, "idea_selection": 2},
                       create=True):
                idea = {"character_a": "pens", "character_b": "chubs"}

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(_run_full_pipeline(idea, bot))
                finally:
                    loop.close()

                # publish_to_youtube should NOT be called at all
                assert mocks["publish_to_youtube"].call_count == 0
        finally:
            for p in mock_pipeline_deps.values():
                p.stop()
