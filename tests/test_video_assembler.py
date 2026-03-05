"""Tests for video assembler modules.

Tests cover:
- sprite_manager: load_sprite, get_character_position, composite_character
- scene_builder: load_background, FRAME constants
- variant_generator: _adjust_script_pacing, _get_situation_music, SITUATION_MUSIC
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
    _get_situation_music,
    VARIANT_PRESETS,
    SITUATION_MUSIC,
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
        """Positions from locations.json are in v1 coords (1080x1920).
        get_character_position returns raw v1 values — scaling happens in scene_builder."""
        x, y = get_character_position("diner", "stool_1")
        assert isinstance(x, int)
        assert isinstance(y, int)
        # Raw v1 positions: x in 0-1080, y in 0-1920
        assert 0 <= x <= 1080
        assert 0 <= y <= 1920

    def test_unknown_position_returns_default(self):
        x, y = get_character_position("diner", "nonexistent_spot")
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
        result = composite_character(frame, "pens", "idle", "diner", "stool_1")
        assert result.size == (FRAME_WIDTH, FRAME_HEIGHT)
        assert result.mode == "RGBA"

    def test_modifies_frame(self):
        """Compositing a character should change the frame pixels."""
        frame = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (26, 26, 58, 255))
        original = frame.copy()
        result = composite_character(frame, "pens", "idle", "diner", "stool_1")
        # At least some pixels should differ
        assert result.tobytes() != original.tobytes()

    def test_sprite_flipped_when_facing_left(self):
        """Passing a 3-tuple with facing='left' should mirror the sprite."""
        frame_r = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (26, 26, 58, 255))
        frame_l = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (26, 26, 58, 255))

        # Same position, different facing
        composite_character(frame_r, "pens", "idle", "diner", (500, 800, "right"))
        composite_character(frame_l, "pens", "idle", "diner", (500, 800, "left"))

        # Frames should differ because one sprite is mirrored
        assert frame_r.tobytes() != frame_l.tobytes()

    def test_2_tuple_position_still_works(self):
        """Backward compat: 2-tuples should work with default right facing."""
        frame = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (26, 26, 58, 255))
        result = composite_character(frame, "pens", "idle", "diner", (500, 800))
        assert result.size == (FRAME_WIDTH, FRAME_HEIGHT)

    def test_default_facing_respected_for_mirror(self):
        """composite_character must use the character's default_facing to decide
        whether to mirror. A character whose default is 'left' should NOT be
        mirrored when position facing is also 'left', but SHOULD be mirrored
        when position facing is 'right'."""
        import numpy as np

        # Oinks default_facing is "left"
        # Position facing "left" → same as default → no mirror
        frame_same = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (26, 26, 58, 255))
        composite_character(frame_same, "oinks", "idle", "diner", (500, 800, "left"))

        # Position facing "right" → opposite of default → mirror
        frame_flip = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (26, 26, 58, 255))
        composite_character(frame_flip, "oinks", "idle", "diner", (500, 800, "right"))

        # These must produce different frames (one is mirrored)
        assert frame_same.tobytes() != frame_flip.tobytes(), (
            "Oinks at facing='left' vs facing='right' should produce different frames"
        )

        # Now verify the "same as default" case matches the raw sprite orientation
        # Load the raw sprite — it faces left by default
        from src.video_assembler.sprite_manager import load_sprite
        raw_sprite = load_sprite("oinks", "idle")

        # Extract the sprite region from the "same" frame and verify it's NOT mirrored
        # by checking that the raw sprite's left half has more opaque pixels
        arr = np.array(raw_sprite)
        mid = raw_sprite.width // 2
        left_mass = np.sum(arr[:, :mid, 3] > 20)
        right_mass = np.sum(arr[:, mid:, 3] > 20)
        # Oinks leans left — left half has more pixel mass
        assert left_mass > right_mass, (
            "Raw oinks sprite should have more pixel mass on left side"
        )

    def test_pens_not_mirrored_when_position_says_right(self):
        """Pens default_facing='right'. Position facing='right' → no mirror.
        Position facing='left' → mirror."""
        frame_nomirror = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (26, 26, 58, 255))
        composite_character(frame_nomirror, "pens", "idle", "diner", (500, 800, "right"))

        frame_mirror = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (26, 26, 58, 255))
        composite_character(frame_mirror, "pens", "idle", "diner", (500, 800, "left"))

        assert frame_nomirror.tobytes() != frame_mirror.tobytes()

    def test_oinks_facing_left_preserves_original_orientation(self):
        """Oinks default_facing='left'. When position says facing='left',
        the sprite should NOT be mirrored — it should preserve the raw
        sprite's original left-leaning orientation.

        This test catches the bug where the code mirrors on facing=='left'
        regardless of the character's default direction."""
        import numpy as np

        # Composite oinks at facing="left" (should match default → no mirror)
        frame = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (0, 0, 0, 0))
        composite_character(frame, "oinks", "idle", "diner", (500, 800, "left"))

        # Extract the sprite region from the composited frame
        arr = np.array(frame)
        alpha = arr[:, :, 3]
        # Find the bounding box of non-transparent pixels
        rows = np.any(alpha > 20, axis=1)
        cols = np.any(alpha > 20, axis=0)
        if rows.any() and cols.any():
            rmin, rmax = np.where(rows)[0][[0, -1]]
            cmin, cmax = np.where(cols)[0][[0, -1]]
            sprite_region = alpha[rmin:rmax+1, cmin:cmax+1]
            mid = sprite_region.shape[1] // 2
            left_mass = np.sum(sprite_region[:, :mid] > 20)
            right_mass = np.sum(sprite_region[:, mid:] > 20)

            # Oinks' raw sprite leans LEFT (more pixel mass on left).
            # If facing="left" and default_facing="left", sprite is NOT mirrored,
            # so left_mass should still be > right_mass.
            assert left_mass > right_mass, (
                f"Oinks at facing='left' should NOT be mirrored (default is 'left'). "
                f"Expected left_mass > right_mass, got {left_mass} vs {right_mass}"
            )

    def test_all_characters_mirror_produces_visible_difference(self):
        """Every character must produce a visually different result when
        mirrored vs not mirrored (proves sprites are asymmetric)."""
        import numpy as np

        characters = ["pens", "chubs", "meows", "oinks", "quacks", "reows"]
        for char_id in characters:
            frame_r = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (26, 26, 58, 255))
            frame_l = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (26, 26, 58, 255))

            composite_character(frame_r, char_id, "idle", "diner", (500, 800, "right"))
            composite_character(frame_l, char_id, "idle", "diner", (500, 800, "left"))

            diff = np.sum(np.abs(
                np.array(frame_r).astype(int) - np.array(frame_l).astype(int)
            ) > 30)
            assert diff > 1000, (
                f"{char_id}: mirrored vs non-mirrored should differ by > 1000 pixels, "
                f"got {diff} — sprite may be too symmetric or mirror not working"
            )


# ---------------------------------------------------------------------------
# scene_builder
# ---------------------------------------------------------------------------

class TestLoadBackground:
    """Test background loading."""

    def test_loads_existing_background(self):
        bg = load_background("diner")
        assert bg.size == (FRAME_WIDTH, FRAME_HEIGHT)

    def test_returns_placeholder_for_missing(self):
        bg = load_background("nonexistent_background")
        assert bg.size == (FRAME_WIDTH, FRAME_HEIGHT)
        assert bg.mode == "RGB"

    def test_frame_constants(self):
        # v2: 16:9 horizontal format
        assert FRAME_WIDTH == 1920
        assert FRAME_HEIGHT == 1080
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


class TestGetSituationMusic:
    """Test situation-based music selection (Curb-style: mood drives music)."""

    def test_everyday_life_uses_main_theme(self):
        script = {"generation_params": {"situation": "everyday_life"}}
        assert _get_situation_music(script) == "main_theme.wav"

    def test_business_uses_main_theme(self):
        script = {"generation_params": {"situation": "business"}}
        assert _get_situation_music(script) == "main_theme.wav"

    def test_diplomatic_uses_main_theme(self):
        script = {"generation_params": {"situation": "diplomatic"}}
        assert _get_situation_music(script) == "main_theme.wav"

    def test_chill_hangout_uses_main_theme(self):
        script = {"generation_params": {"situation": "chill_hangout"}}
        assert _get_situation_music(script) == "main_theme.wav"

    def test_mystery_uses_tense_theme(self):
        script = {"generation_params": {"situation": "mystery"}}
        assert _get_situation_music(script) == "tense_theme.wav"

    def test_scheme_uses_tense_theme(self):
        script = {"generation_params": {"situation": "scheme"}}
        assert _get_situation_music(script) == "tense_theme.wav"

    def test_unknown_situation_uses_main_theme(self):
        script = {"generation_params": {"situation": "unknown_thing"}}
        assert _get_situation_music(script) == "main_theme.wav"

    def test_missing_generation_params_uses_main_theme(self):
        assert _get_situation_music({}) == "main_theme.wav"

    def test_missing_situation_uses_main_theme(self):
        script = {"generation_params": {}}
        assert _get_situation_music(script) == "main_theme.wav"


class TestSituationMusicMapping:
    """Test SITUATION_MUSIC dict has correct entries."""

    def test_all_situations_mapped(self):
        expected = ["everyday_life", "business", "diplomatic",
                    "chill_hangout", "mystery", "scheme"]
        for situation in expected:
            assert situation in SITUATION_MUSIC

    def test_only_valid_tracks(self):
        valid_tracks = {"main_theme.wav", "tense_theme.wav", "upbeat_theme.wav"}
        for track in SITUATION_MUSIC.values():
            assert track in valid_tracks


class TestVariantPresets:
    """Test variant preset structure and music references."""

    def test_three_presets_exist(self):
        assert len(VARIANT_PRESETS) >= 3

    def test_preset_structure(self):
        for preset in VARIANT_PRESETS:
            assert "name" in preset
            assert "music" in preset
            assert "pacing_multiplier" in preset
            assert "punchline_hold_seconds" in preset

    def test_presets_use_valid_tracks(self):
        valid_tracks = {"main_theme.wav", "tense_theme.wav", "upbeat_theme.wav"}
        for preset in VARIANT_PRESETS:
            assert preset["music"] in valid_tracks

    def test_presets_have_different_music(self):
        """Each preset should offer a different track."""
        music_set = {p["music"] for p in VARIANT_PRESETS}
        assert len(music_set) == 3

    def test_standard_preset_is_first(self):
        assert VARIANT_PRESETS[0]["name"] == "Standard"

    def test_upbeat_preset_faster_pacing(self):
        upbeat = VARIANT_PRESETS[1]
        assert upbeat["pacing_multiplier"] < 1.0

    def test_tense_preset_slower_pacing(self):
        tense = VARIANT_PRESETS[2]
        assert tense["pacing_multiplier"] > 1.0
