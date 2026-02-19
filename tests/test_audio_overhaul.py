"""Tests for Stage 5: Audio overhaul.

Changes:
1. Volume reduction — music, SFX, and blips all quieter
2. Dialogue ducking — music volume drops further during dialogue
3. Ducking schedule generation — extract dialogue time ranges from script

Test groups:
1. Volume constants — new default levels
2. Ducking schedule — dialogue time range extraction
3. Ducked mix — music is quieter during dialogue sections
"""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest
from pydub import AudioSegment

from src.audio_mixer.mixer import (
    MUSIC_VOLUME_DB,
    SFX_VOLUME_DB,
    BLIP_VOLUME_DB,
)


# ---------------------------------------------------------------------------
# Volume constants — quieter defaults
# ---------------------------------------------------------------------------

class TestVolumeOverhaul:
    """All default volumes must be significantly quieter than v1."""

    def test_music_volume_quieter(self):
        """Music should be atmospheric background, not dominant."""
        assert MUSIC_VOLUME_DB <= -18.0

    def test_sfx_volume_quieter(self):
        """SFX should be noticeable but not jarring."""
        assert SFX_VOLUME_DB <= -6.0

    def test_blip_volume_quieter(self):
        """Text blips should be subtle, not distracting."""
        assert BLIP_VOLUME_DB <= -12.0


# ---------------------------------------------------------------------------
# Ducking schedule — extract dialogue time ranges from script
# ---------------------------------------------------------------------------

MOCK_CHAR_BLIPS = {
    "pens": "text_blip_low.wav",
    "chubs": "text_blip_warm.wav",
}


class TestDuckingSchedule:
    """Generate time ranges when dialogue is active for music ducking."""

    @patch("src.audio_mixer.mixer._load_character_blips", return_value=MOCK_CHAR_BLIPS)
    def test_returns_list_of_tuples(self, mock_blips):
        """Ducking schedule returns list of (start_ms, end_ms) tuples."""
        from src.audio_mixer.mixer import generate_ducking_schedule
        script = {
            "scenes": [{
                "duration_seconds": 10,
                "dialogue": [
                    {"character": "pens", "text": "Hello!"},
                ],
            }]
        }
        schedule = generate_ducking_schedule(script)
        assert isinstance(schedule, list)
        assert len(schedule) > 0
        for item in schedule:
            assert isinstance(item, tuple)
            assert len(item) == 2
            start, end = item
            assert end > start

    @patch("src.audio_mixer.mixer._load_character_blips", return_value=MOCK_CHAR_BLIPS)
    def test_empty_dialogue_no_ducking(self, mock_blips):
        """No dialogue = no ducking ranges."""
        from src.audio_mixer.mixer import generate_ducking_schedule
        script = {"scenes": [{"duration_seconds": 10, "dialogue": []}]}
        schedule = generate_ducking_schedule(script)
        assert schedule == []

    @patch("src.audio_mixer.mixer._load_character_blips", return_value=MOCK_CHAR_BLIPS)
    def test_second_scene_offset(self, mock_blips):
        """Ducking ranges in scene 2 are offset by scene 1's duration."""
        from src.audio_mixer.mixer import generate_ducking_schedule
        script = {
            "scenes": [
                {"duration_seconds": 5, "dialogue": []},
                {"duration_seconds": 10, "dialogue": [
                    {"character": "pens", "text": "Hello!"},
                ]},
            ]
        }
        schedule = generate_ducking_schedule(script)
        assert len(schedule) > 0
        # Scene 2 starts at 5000ms, dialogue starts 1s into scene = 6000ms
        assert schedule[0][0] >= 5000

    @patch("src.audio_mixer.mixer._load_character_blips", return_value=MOCK_CHAR_BLIPS)
    def test_multiple_dialogue_lines_multiple_ranges(self, mock_blips):
        """Each dialogue line produces its own ducking range."""
        from src.audio_mixer.mixer import generate_ducking_schedule
        script = {
            "scenes": [{
                "duration_seconds": 20,
                "dialogue": [
                    {"character": "pens", "text": "First line."},
                    {"character": "chubs", "text": "Second line."},
                ],
            }]
        }
        schedule = generate_ducking_schedule(script)
        assert len(schedule) == 2
        # Second range starts after first
        assert schedule[1][0] >= schedule[0][1]


# ---------------------------------------------------------------------------
# Ducking constant
# ---------------------------------------------------------------------------

class TestDuckingConstant:
    """Ducking amount must be defined as a constant."""

    def test_ducking_db_exists(self):
        from src.audio_mixer.mixer import DUCKING_DB
        assert isinstance(DUCKING_DB, float)

    def test_ducking_is_negative(self):
        """Ducking should reduce volume (negative dB)."""
        from src.audio_mixer.mixer import DUCKING_DB
        assert DUCKING_DB < 0

    def test_ducking_is_significant(self):
        """Ducking should be at least -4 dB to be noticeable."""
        from src.audio_mixer.mixer import DUCKING_DB
        assert DUCKING_DB <= -4.0


# ---------------------------------------------------------------------------
# Mix with ducking — music quieter during dialogue
# ---------------------------------------------------------------------------

class TestDuckedMix:
    """mix_episode_audio should apply ducking during dialogue segments."""

    def test_mix_still_produces_output(self):
        """Mixing with ducking must still produce a valid audio file."""
        from src.audio_mixer.mixer import mix_episode_audio

        script = {
            "scenes": [{
                "duration_seconds": 3,
                "dialogue": [
                    {"character": "pens", "text": "Test dialogue."},
                ],
            }]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple sine-wave music file
            music = AudioSegment.silent(duration=5000)
            music_path = os.path.join(tmpdir, "test_music.wav")
            music.export(music_path, format="wav")

            output_path = os.path.join(tmpdir, "mixed.wav")
            result = mix_episode_audio(
                script=script,
                music_path=music_path,
                total_duration_ms=3000,
                output_path=output_path,
            )
            assert os.path.exists(result)
            mixed = AudioSegment.from_file(result)
            assert len(mixed) >= 2900  # roughly 3 seconds

    def test_ducking_applied_flag(self):
        """mix_episode_audio should accept enable_ducking parameter."""
        from src.audio_mixer.mixer import mix_episode_audio

        script = {
            "scenes": [{
                "duration_seconds": 3,
                "dialogue": [
                    {"character": "pens", "text": "Test."},
                ],
            }]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            music = AudioSegment.silent(duration=5000)
            music_path = os.path.join(tmpdir, "test_music.wav")
            music.export(music_path, format="wav")

            output_path = os.path.join(tmpdir, "mixed.wav")
            # Should not raise with enable_ducking=True
            result = mix_episode_audio(
                script=script,
                music_path=music_path,
                total_duration_ms=3000,
                output_path=output_path,
                enable_ducking=True,
            )
            assert os.path.exists(result)
