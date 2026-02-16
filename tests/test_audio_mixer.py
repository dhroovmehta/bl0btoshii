"""Tests for audio mixer module.

Tests cover:
- generate_blip_events: timestamp generation, character blip mapping, spacing
- Volume constants
"""

from unittest.mock import patch

import pytest

from src.audio_mixer.mixer import (
    generate_blip_events,
    MUSIC_VOLUME_DB,
    SFX_VOLUME_DB,
    BLIP_VOLUME_DB,
)


# Mock character blips so we don't need to read the real characters.json
MOCK_CHAR_BLIPS = {
    "pens": "text_blip_low.wav",
    "chubs": "text_blip_warm.wav",
    "oinks": "text_blip_bold.wav",
}


# ---------------------------------------------------------------------------
# Volume constants
# ---------------------------------------------------------------------------

class TestVolumeConstants:
    """Test default volume level constants."""

    def test_music_volume(self):
        assert MUSIC_VOLUME_DB == -12.0

    def test_sfx_volume(self):
        assert SFX_VOLUME_DB == -3.0

    def test_blip_volume(self):
        assert BLIP_VOLUME_DB == -6.0


# ---------------------------------------------------------------------------
# generate_blip_events
# ---------------------------------------------------------------------------

class TestGenerateBlipEvents:
    """Test text blip event generation."""

    @patch("src.audio_mixer.mixer._load_character_blips", return_value=MOCK_CHAR_BLIPS)
    def test_returns_list(self, mock_blips):
        script = {
            "scenes": [
                {
                    "duration_seconds": 10,
                    "dialogue": [
                        {"character": "pens", "text": "Hello!"},
                    ],
                }
            ]
        }
        result = generate_blip_events(script)
        assert isinstance(result, list)

    @patch("src.audio_mixer.mixer._load_character_blips", return_value=MOCK_CHAR_BLIPS)
    def test_blip_per_n_chars(self, mock_blips):
        """Should create a blip every 3 non-space characters."""
        script = {
            "scenes": [
                {
                    "duration_seconds": 10,
                    "dialogue": [
                        {"character": "pens", "text": "abcdefghi"},  # 9 chars, indices 0,3,6 → 3 blips
                    ],
                }
            ]
        }
        result = generate_blip_events(script)
        assert len(result) == 3

    @patch("src.audio_mixer.mixer._load_character_blips", return_value=MOCK_CHAR_BLIPS)
    def test_spaces_skipped(self, mock_blips):
        """Spaces should not generate blips."""
        script = {
            "scenes": [
                {
                    "duration_seconds": 10,
                    "dialogue": [
                        {"character": "pens", "text": "a b c"},
                    ],
                }
            ]
        }
        result = generate_blip_events(script)
        # Chars: a(0), ' '(1-skip), b(2), ' '(3-skip), c(4)
        # Non-space at index 0→blip, 2→no(not %3==0), 4→no
        # Actually index 0 % 3 == 0 → blip for 'a'
        # index 2 % 3 != 0 → no blip for 'b'
        # index 4 % 3 != 0 → no blip for 'c'
        # But spaces are skipped entirely (continue), not counted as blip candidates
        # Wait - the code iterates over enumerate(text), spaces hit continue
        # Index 0: 'a' → 0%3==0 → blip
        # Index 1: ' ' → skip
        # Index 2: 'b' → 2%3!=0 → no blip
        # Index 3: ' ' → skip
        # Index 4: 'c' → 4%3!=0 → no blip
        # So only 1 blip for 'a'
        assert len(result) == 1

    @patch("src.audio_mixer.mixer._load_character_blips", return_value=MOCK_CHAR_BLIPS)
    def test_uses_character_blip_file(self, mock_blips):
        script = {
            "scenes": [
                {
                    "duration_seconds": 10,
                    "dialogue": [
                        {"character": "pens", "text": "Hello world"},
                    ],
                }
            ]
        }
        result = generate_blip_events(script)
        for _, blip_file in result:
            assert blip_file == "text_blip_low.wav"

    @patch("src.audio_mixer.mixer._load_character_blips", return_value=MOCK_CHAR_BLIPS)
    def test_different_characters_different_blips(self, mock_blips):
        script = {
            "scenes": [
                {
                    "duration_seconds": 20,
                    "dialogue": [
                        {"character": "pens", "text": "abc"},
                        {"character": "chubs", "text": "def"},
                    ],
                }
            ]
        }
        result = generate_blip_events(script)
        blip_files = set(f for _, f in result)
        assert "text_blip_low.wav" in blip_files
        assert "text_blip_warm.wav" in blip_files

    @patch("src.audio_mixer.mixer._load_character_blips", return_value=MOCK_CHAR_BLIPS)
    def test_timestamps_increase(self, mock_blips):
        script = {
            "scenes": [
                {
                    "duration_seconds": 10,
                    "dialogue": [
                        {"character": "pens", "text": "abcdef"},
                    ],
                }
            ]
        }
        result = generate_blip_events(script)
        timestamps = [t for t, _ in result]
        assert timestamps == sorted(timestamps)

    @patch("src.audio_mixer.mixer._load_character_blips", return_value=MOCK_CHAR_BLIPS)
    def test_second_scene_offset(self, mock_blips):
        """Blips in scene 2 should be offset by scene 1's duration."""
        script = {
            "scenes": [
                {
                    "duration_seconds": 5,
                    "dialogue": [],
                },
                {
                    "duration_seconds": 10,
                    "dialogue": [
                        {"character": "pens", "text": "abc"},
                    ],
                },
            ]
        }
        result = generate_blip_events(script)
        # Scene 2 starts at 5000ms, dialogue starts 1000ms in → first blip at 6000ms
        assert len(result) > 0
        assert result[0][0] >= 5000 + 1000

    @patch("src.audio_mixer.mixer._load_character_blips", return_value=MOCK_CHAR_BLIPS)
    def test_empty_dialogue(self, mock_blips):
        script = {"scenes": [{"duration_seconds": 10, "dialogue": []}]}
        result = generate_blip_events(script)
        assert result == []

    @patch("src.audio_mixer.mixer._load_character_blips", return_value=MOCK_CHAR_BLIPS)
    def test_empty_scenes(self, mock_blips):
        result = generate_blip_events({"scenes": []})
        assert result == []

    @patch("src.audio_mixer.mixer._load_character_blips", return_value=MOCK_CHAR_BLIPS)
    def test_unknown_character_gets_default_blip(self, mock_blips):
        script = {
            "scenes": [
                {
                    "duration_seconds": 10,
                    "dialogue": [
                        {"character": "unknown_char", "text": "abc"},
                    ],
                }
            ]
        }
        result = generate_blip_events(script)
        # Unknown chars get "text_blip_mid.wav" from the .get() default
        assert len(result) > 0
        assert result[0][1] == "text_blip_mid.wav"

    @patch("src.audio_mixer.mixer._load_character_blips", return_value=MOCK_CHAR_BLIPS)
    def test_tuple_format(self, mock_blips):
        script = {
            "scenes": [
                {
                    "duration_seconds": 10,
                    "dialogue": [
                        {"character": "pens", "text": "abc"},
                    ],
                }
            ]
        }
        result = generate_blip_events(script)
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2
            assert isinstance(item[0], float)
            assert isinstance(item[1], str)
