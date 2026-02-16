"""Tests for video assembler modules.

Tests cover:
- sprite_manager: load_sprite, get_character_position, composite_character
- scene_builder: load_background, FRAME constants
- variant_generator: _adjust_script_pacing, _get_location_music
"""

import copy
import os
from unittest.mock import patch

import pytest
from PIL import Image

from src.video_assembler.sprite_manager import (
    load_sprite,
    get_character_position,
    composite_character,
    SPRITE_SCALE,
)
from src.video_assembler.scene_builder import (
    load_background,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    FRAME_RATE,
)
from src.video_assembler.variant_generator import (
    _adjust_script_pacing,
    _get_location_music,
    VARIANT_PRESETS,
    LOCATION_MUSIC,
)


# ---------------------------------------------------------------------------
# sprite_manager
# ---------------------------------------------------------------------------

class TestLoadSprite:
    """Test sprite loading."""

    def test_loads_existing_sprite(self):
        sprite = load_sprite("pens", "idle")
        assert sprite.mode == "RGBA"
        assert sprite.width > 0
        assert sprite.height > 0

    def test_falls_back_to_idle(self):
        """Should fall back to idle.png when requested state doesn't exist."""
        sprite = load_sprite("pens", "nonexistent_state")
        idle = load_sprite("pens", "idle")
        assert sprite.size == idle.size

    def test_placeholder_for_missing_character(self):
        """Should return transparent placeholder for unknown characters."""
        sprite = load_sprite("doesnotexist", "idle")
        assert sprite.mode == "RGBA"
        assert sprite.size == (192, 288)

    def test_sprite_scale_is_1(self):
        """Sprites are pre-sized, so SPRITE_SCALE should be 1."""
        assert SPRITE_SCALE == 1

    def test_all_characters_have_idle(self):
        chars = ["pens", "chubs", "meows", "oinks", "quacks", "reows"]
        for char in chars:
            sprite = load_sprite(char, "idle")
            assert sprite.width > 0, f"{char}/idle.png failed to load"

    def test_all_characters_have_talking(self):
        chars = ["pens", "chubs", "meows", "oinks", "quacks", "reows"]
        for char in chars:
            sprite = load_sprite(char, "talking")
            assert sprite.width > 0, f"{char}/talking.png failed to load"


class TestGetCharacterPosition:
    """Test character position lookup."""

    def test_known_position(self):
        x, y = get_character_position("diner_interior", "stool_1")
        assert isinstance(x, int)
        assert isinstance(y, int)
        assert 0 <= x <= FRAME_WIDTH
        assert 0 <= y <= FRAME_HEIGHT

    def test_unknown_position_returns_default(self):
        x, y = get_character_position("diner_interior", "nonexistent_spot")
        assert isinstance(x, int)
        assert isinstance(y, int)

    def test_unknown_location_returns_default(self):
        x, y = get_character_position("nonexistent_location", "center")
        assert isinstance(x, int)
        assert isinstance(y, int)


class TestCompositeCharacter:
    """Test character compositing onto frames."""

    def test_returns_frame(self):
        frame = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (26, 26, 58, 255))
        result = composite_character(frame, "pens", "idle", "diner_interior", "stool_1")
        assert result.size == (FRAME_WIDTH, FRAME_HEIGHT)
        assert result.mode == "RGBA"

    def test_modifies_frame(self):
        """Compositing a character should change the frame pixels."""
        frame = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (26, 26, 58, 255))
        original = frame.copy()
        result = composite_character(frame, "pens", "idle", "diner_interior", "stool_1")
        # At least some pixels should differ
        assert result.tobytes() != original.tobytes()


# ---------------------------------------------------------------------------
# scene_builder
# ---------------------------------------------------------------------------

class TestLoadBackground:
    """Test background loading."""

    def test_loads_existing_background(self):
        bg = load_background("diner_interior")
        assert bg.size == (FRAME_WIDTH, FRAME_HEIGHT)

    def test_returns_placeholder_for_missing(self):
        bg = load_background("nonexistent_background")
        assert bg.size == (FRAME_WIDTH, FRAME_HEIGHT)
        assert bg.mode == "RGB"

    def test_frame_constants(self):
        assert FRAME_WIDTH == 1080
        assert FRAME_HEIGHT == 1920
        assert FRAME_RATE == 30


# ---------------------------------------------------------------------------
# variant_generator
# ---------------------------------------------------------------------------

class TestAdjustScriptPacing:
    """Test script pacing adjustment (pure function)."""

    @pytest.fixture
    def base_script(self):
        return {
            "scenes": [
                {
                    "duration_seconds": 10,
                    "dialogue": [
                        {"text": "hello", "duration_ms": 2000},
                        {"text": "world", "duration_ms": 3000},
                    ],
                },
                {
                    "duration_seconds": 12,
                    "dialogue": [
                        {"text": "goodbye", "duration_ms": 2500},
                    ],
                },
            ],
        }

    def test_standard_pacing_preserves_duration(self, base_script):
        result = _adjust_script_pacing(base_script, 1.0, 0)
        assert result["scenes"][0]["duration_seconds"] == 10
        assert result["scenes"][1]["duration_seconds"] == 12

    def test_faster_pacing_reduces_duration(self, base_script):
        result = _adjust_script_pacing(base_script, 0.85, 0)
        assert result["scenes"][0]["duration_seconds"] < 10

    def test_slower_pacing_increases_duration(self, base_script):
        result = _adjust_script_pacing(base_script, 1.15, 0)
        assert result["scenes"][0]["duration_seconds"] > 10

    def test_punchline_hold_adds_to_last_scene(self, base_script):
        result = _adjust_script_pacing(base_script, 1.0, 3)
        # Last scene should be original + punchline hold
        assert result["scenes"][-1]["duration_seconds"] == 12 + 3

    def test_does_not_mutate_original(self, base_script):
        original_duration = base_script["scenes"][0]["duration_seconds"]
        _adjust_script_pacing(base_script, 0.5, 5)
        assert base_script["scenes"][0]["duration_seconds"] == original_duration

    def test_minimum_duration_floor(self, base_script):
        """Duration should not go below 4 seconds."""
        result = _adjust_script_pacing(base_script, 0.1, 0)
        for scene in result["scenes"][:-1]:  # Exclude last (has punchline hold)
            assert scene["duration_seconds"] >= 4

    def test_dialogue_timing_scales(self, base_script):
        result = _adjust_script_pacing(base_script, 0.85, 0)
        assert result["scenes"][0]["dialogue"][0]["duration_ms"] < 2000

    def test_dialogue_minimum_floor(self, base_script):
        """Dialogue duration should not go below 1000ms."""
        result = _adjust_script_pacing(base_script, 0.1, 0)
        for scene in result["scenes"]:
            for line in scene["dialogue"]:
                assert line["duration_ms"] >= 1000

    def test_empty_scenes(self):
        result = _adjust_script_pacing({"scenes": []}, 1.0, 3)
        assert result["scenes"] == []


class TestGetLocationMusic:
    """Test location-based music lookup (pure function)."""

    def test_known_location(self):
        script = {"scenes": [{"background": "diner_interior"}]}
        assert _get_location_music(script) == "default_theme.wav"

    def test_town_square(self):
        script = {"scenes": [{"background": "town_square"}]}
        assert _get_location_music(script) == "town_theme.wav"

    def test_unknown_location_returns_default(self):
        script = {"scenes": [{"background": "unknown_place"}]}
        assert _get_location_music(script) == "default_theme.wav"

    def test_empty_scenes_returns_default(self):
        assert _get_location_music({"scenes": []}) == "default_theme.wav"

    def test_variant_presets_exist(self):
        assert len(VARIANT_PRESETS) >= 3
        for preset in VARIANT_PRESETS:
            assert "name" in preset
            assert "pacing_multiplier" in preset
            assert "punchline_hold_seconds" in preset
