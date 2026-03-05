"""Tests for audio mixer module.

Tests cover:
- generate_blip_events: disabled (speech bubbles don't use blips)
- Volume constants
"""

import pytest

from src.audio_mixer.mixer import (
    generate_blip_events,
    MUSIC_VOLUME_DB,
    SFX_VOLUME_DB,
    BLIP_VOLUME_DB,
)


# ---------------------------------------------------------------------------
# Volume constants
# ---------------------------------------------------------------------------

class TestVolumeConstants:
    """Test default volume level constants (v2: quieter for atmospheric audio)."""

    def test_music_volume(self):
        assert MUSIC_VOLUME_DB == -20.0

    def test_sfx_volume(self):
        assert SFX_VOLUME_DB == -8.0

    def test_blip_volume(self):
        assert BLIP_VOLUME_DB == -14.0


# ---------------------------------------------------------------------------
# generate_blip_events — disabled (D-025: speech bubbles)
# ---------------------------------------------------------------------------

class TestGenerateBlipEvents:
    """Text blips are disabled — speech bubbles don't use them."""

    def test_returns_empty_list(self):
        """Blip generation is disabled — always returns empty list."""
        script = {
            "scenes": [
                {
                    "duration_seconds": 10,
                    "dialogue": [
                        {"character": "pens", "text": "Hello world!"},
                    ],
                }
            ]
        }
        result = generate_blip_events(script)
        assert result == []

    def test_empty_script_returns_empty(self):
        result = generate_blip_events({"scenes": []})
        assert result == []

    def test_returns_list_type(self):
        result = generate_blip_events({"scenes": []})
        assert isinstance(result, list)
