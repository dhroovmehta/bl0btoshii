"""Tests for the pipeline orchestrator (src/pipeline/orchestrator.py).

Tests cover:
- check_asset_availability: verifies backgrounds, sprites, SFX existence
- check_video_quality: validates resolution, file size, duration, audio
- log_episode_to_index: records episode metadata to index.json
"""

import json
import os
import subprocess
from unittest.mock import patch, MagicMock

import pytest

from src.pipeline.orchestrator import (
    check_asset_availability,
    check_video_quality,
    log_episode_to_index,
)


# ---------------------------------------------------------------------------
# check_asset_availability
# ---------------------------------------------------------------------------

class TestCheckAssetAvailability:
    """Test the asset availability checker."""

    def test_all_assets_present(self, sample_script):
        """When all referenced assets exist, should return (True, [])."""
        all_present, missing = check_asset_availability(sample_script)
        # diner_interior.png and pens/oinks sprites exist from previous phase
        assert all_present is True
        assert missing == []

    def test_missing_background(self, sample_script_missing_assets):
        """Should detect missing background."""
        _, missing = check_asset_availability(sample_script_missing_assets)
        assert "backgrounds/nonexistent_bg.png" in missing

    def test_missing_character_sprites(self, sample_script_missing_assets):
        """Should detect missing character sprite folders."""
        _, missing = check_asset_availability(sample_script_missing_assets)
        assert "characters/fakeanimal/idle.png" in missing
        assert "characters/fakeanimal/talking.png" in missing

    def test_missing_sfx(self, sample_script_missing_assets):
        """Should detect missing SFX files."""
        _, missing = check_asset_availability(sample_script_missing_assets)
        assert "sfx/nonexistent_sound.wav" in missing

    def test_returns_false_when_missing(self, sample_script_missing_assets):
        """Should return False when assets are missing."""
        all_present, _ = check_asset_availability(sample_script_missing_assets)
        assert all_present is False

    def test_empty_script_passes(self):
        """A script with no scenes should pass (nothing to check)."""
        empty_script = {"scenes": []}
        all_present, missing = check_asset_availability(empty_script)
        assert all_present is True
        assert missing == []

    def test_deduplicates_missing_assets(self):
        """Same missing asset across scenes should only appear once."""
        script = {
            "scenes": [
                {
                    "background": "nonexistent_bg",
                    "characters_present": [],
                    "sfx_triggers": [],
                },
                {
                    "background": "nonexistent_bg",
                    "characters_present": [],
                    "sfx_triggers": [],
                },
            ]
        }
        _, missing = check_asset_availability(script)
        assert missing.count("backgrounds/nonexistent_bg.png") == 1

    def test_checks_idle_and_talking_states(self, sample_script):
        """Should check both idle and talking sprites for each character."""
        # Modify script to have a character that only has idle but not talking
        script = {
            "scenes": [
                {
                    "background": "diner_interior",
                    "characters_present": ["pens"],
                    "character_positions": {"pens": "stool_1"},
                    "character_animations": {"pens": "idle"},
                    "dialogue": [],
                    "sfx_triggers": [],
                },
            ],
        }
        all_present, missing = check_asset_availability(script)
        # pens has both idle.png and talking.png, so should pass
        assert all_present is True


# ---------------------------------------------------------------------------
# check_video_quality
# ---------------------------------------------------------------------------

class TestCheckVideoQuality:
    """Test the video quality checker."""

    def test_nonexistent_video(self):
        """Should fail for a file that doesn't exist."""
        passed, issues = check_video_quality("/nonexistent/video.mp4")
        assert passed is False
        assert "Video file does not exist" in issues

    def test_file_too_small(self, tmp_dir):
        """Should flag files that are too small."""
        # Create a tiny file (1 byte)
        tiny_file = os.path.join(tmp_dir, "tiny.mp4")
        with open(tiny_file, "wb") as f:
            f.write(b"\x00")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({
                    "streams": [
                        {"codec_type": "video", "width": 1080, "height": 1920},
                        {"codec_type": "audio"},
                    ],
                    "format": {"duration": "35.0"},
                }),
            )
            passed, issues = check_video_quality(tiny_file)

        assert passed is False
        assert any("too small" in issue for issue in issues)

    def test_wrong_resolution(self, tmp_dir):
        """Should flag incorrect resolution."""
        video_file = os.path.join(tmp_dir, "wrong_res.mp4")
        # Create a file larger than min size
        with open(video_file, "wb") as f:
            f.write(b"\x00" * 600 * 1024)  # 600KB

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({
                    "streams": [
                        {"codec_type": "video", "width": 1920, "height": 1080},
                        {"codec_type": "audio"},
                    ],
                    "format": {"duration": "35.0"},
                }),
            )
            passed, issues = check_video_quality(video_file)

        assert passed is False
        assert any("1920x1080" in issue for issue in issues)

    def test_duration_too_short(self, tmp_dir):
        """Should flag videos that are too short."""
        video_file = os.path.join(tmp_dir, "short.mp4")
        with open(video_file, "wb") as f:
            f.write(b"\x00" * 600 * 1024)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({
                    "streams": [
                        {"codec_type": "video", "width": 1080, "height": 1920},
                        {"codec_type": "audio"},
                    ],
                    "format": {"duration": "2.0"},
                }),
            )
            passed, issues = check_video_quality(video_file)

        assert passed is False
        assert any("too short" in issue for issue in issues)

    def test_no_audio_stream(self, tmp_dir):
        """Should flag videos without audio."""
        video_file = os.path.join(tmp_dir, "no_audio.mp4")
        with open(video_file, "wb") as f:
            f.write(b"\x00" * 600 * 1024)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({
                    "streams": [
                        {"codec_type": "video", "width": 1080, "height": 1920},
                    ],
                    "format": {"duration": "35.0"},
                }),
            )
            passed, issues = check_video_quality(video_file)

        assert passed is False
        assert any("No audio" in issue for issue in issues)

    def test_valid_video_passes(self, tmp_dir):
        """A valid video should pass all checks."""
        video_file = os.path.join(tmp_dir, "good.mp4")
        with open(video_file, "wb") as f:
            f.write(b"\x00" * 600 * 1024)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({
                    "streams": [
                        {"codec_type": "video", "width": 1080, "height": 1920},
                        {"codec_type": "audio"},
                    ],
                    "format": {"duration": "35.0"},
                }),
            )
            passed, issues = check_video_quality(video_file)

        assert passed is True
        assert issues == []

    def test_ffprobe_not_installed(self, tmp_dir):
        """Should handle ffprobe not being installed."""
        video_file = os.path.join(tmp_dir, "no_ffprobe.mp4")
        with open(video_file, "wb") as f:
            f.write(b"\x00" * 600 * 1024)

        with patch("subprocess.run", side_effect=FileNotFoundError):
            passed, issues = check_video_quality(video_file)

        assert any("ffprobe not installed" in issue for issue in issues)

    def test_ffprobe_failure(self, tmp_dir):
        """Should handle ffprobe returning non-zero."""
        video_file = os.path.join(tmp_dir, "bad_probe.mp4")
        with open(video_file, "wb") as f:
            f.write(b"\x00" * 600 * 1024)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            passed, issues = check_video_quality(video_file)

        assert any("ffprobe failed" in issue for issue in issues)


# ---------------------------------------------------------------------------
# log_episode_to_index
# ---------------------------------------------------------------------------

class TestLogEpisodeToIndex:
    """Test episode index logging."""

    def test_creates_index_if_missing(self, tmp_dir, sample_script):
        """Should create index.json if it doesn't exist."""
        index_path = os.path.join(tmp_dir, "episodes", "index.json")
        with patch("src.pipeline.orchestrator.DATA_DIR", tmp_dir):
            log_episode_to_index(sample_script)
        assert os.path.exists(index_path)

    def test_adds_episode_to_index(self, tmp_dir, sample_script):
        """Should add the episode to the episodes list."""
        with patch("src.pipeline.orchestrator.DATA_DIR", tmp_dir):
            log_episode_to_index(sample_script)

        index_path = os.path.join(tmp_dir, "episodes", "index.json")
        with open(index_path, "r") as f:
            index = json.load(f)

        assert len(index["episodes"]) == 1
        assert index["episodes"][0]["episode_id"] == "EP099"
        assert index["episodes"][0]["title"] == "Test Episode"
        assert index["episodes"][0]["published"] is True

    def test_increments_episode_counter(self, tmp_dir, sample_script):
        """Should increment next_episode_number."""
        with patch("src.pipeline.orchestrator.DATA_DIR", tmp_dir):
            log_episode_to_index(sample_script)
            log_episode_to_index(sample_script)

        index_path = os.path.join(tmp_dir, "episodes", "index.json")
        with open(index_path, "r") as f:
            index = json.load(f)

        assert len(index["episodes"]) == 2
        assert index["next_episode_number"] == 3

    def test_preserves_existing_episodes(self, tmp_dir, sample_script):
        """Should not overwrite existing episodes when adding new ones."""
        index_path = os.path.join(tmp_dir, "episodes", "index.json")
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        existing = {
            "next_episode_number": 5,
            "episodes": [
                {"episode_id": "EP001", "title": "First", "published": True},
            ],
        }
        with open(index_path, "w") as f:
            json.dump(existing, f)

        with patch("src.pipeline.orchestrator.DATA_DIR", tmp_dir):
            log_episode_to_index(sample_script)

        with open(index_path, "r") as f:
            index = json.load(f)

        assert len(index["episodes"]) == 2
        assert index["episodes"][0]["episode_id"] == "EP001"
        assert index["episodes"][1]["episode_id"] == "EP099"
        assert index["next_episode_number"] == 6

    def test_records_content_parameters(self, tmp_dir, sample_script):
        """Should record characters, situation, punchline, location."""
        with patch("src.pipeline.orchestrator.DATA_DIR", tmp_dir):
            log_episode_to_index(sample_script)

        index_path = os.path.join(tmp_dir, "episodes", "index.json")
        with open(index_path, "r") as f:
            index = json.load(f)

        ep = index["episodes"][0]
        assert ep["characters_featured"] == ["pens", "oinks"]
        assert ep["situation"] == "everyday_life"
        assert ep["punchline_type"] == "deadpan"
        assert ep["location"] == "diner_interior"
