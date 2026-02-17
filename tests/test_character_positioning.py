"""Tests for character positioning, overlap prevention, and dialogue box clearance.

These tests validate locations.json and sprite_manager.py to ensure:
1. All character positions are on-screen and within ground zone
2. No character position can overlap with the dialogue text box
3. Positions within the same location are spaced apart (no stacking)
4. The default fallback position follows the same safety rules
5. Every location has at least 2 character positions
6. All rules apply dynamically to ANY location in locations.json (future-proof)
"""

import json
import os
from unittest.mock import patch

import pytest

from src.video_assembler.sprite_manager import get_character_position, load_sprite

# --- Constants matching production code ---
FRAME_WIDTH = 1080
FRAME_HEIGHT = 1920
TEXT_BOX_Y = 1680  # from scene_builder.py
TEXT_BOX_HEIGHT = 200  # from text_renderer/renderer.py

# --- Safety rules ---
# Max sprite dimensions (from assets/characters/ analysis)
MAX_SPRITE_WIDTH = 192
MAX_SPRITE_HEIGHT = 288

# Character feet must not go below this y to avoid text box overlap.
# TEXT_BOX_Y (1680) minus a safety margin of 200px.
MAX_POSITION_Y = 1480

# Characters must be at least half a sprite width from frame edges.
MIN_POSITION_X = MAX_SPRITE_WIDTH // 2  # 96
MAX_POSITION_X = FRAME_WIDTH - MAX_SPRITE_WIDTH // 2  # 984

# Minimum horizontal distance between positions to prevent stacking.
MIN_POSITION_SPACING = 200

# Minimum number of character positions per location.
MIN_POSITIONS_PER_LOCATION = 2


# --- Fixtures ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


@pytest.fixture
def locations():
    """Load all locations from locations.json."""
    with open(os.path.join(DATA_DIR, "locations.json"), "r") as f:
        return json.load(f)["locations"]


@pytest.fixture
def all_positions(locations):
    """Extract all (location_id, position_name, x, y) tuples."""
    result = []
    for loc_id, loc_data in locations.items():
        for pos_name, pos_data in loc_data.get("character_positions", {}).items():
            result.append((loc_id, pos_name, pos_data["x"], pos_data["y"]))
    return result


# ---------------------------------------------------------------------------
# 1. Every location has enough positions
# ---------------------------------------------------------------------------

class TestLocationPositionCount:
    """Every location must have at least MIN_POSITIONS_PER_LOCATION positions."""

    def test_all_locations_have_minimum_positions(self, locations):
        for loc_id, loc_data in locations.items():
            positions = loc_data.get("character_positions", {})
            assert len(positions) >= MIN_POSITIONS_PER_LOCATION, (
                f"{loc_id} has only {len(positions)} position(s), "
                f"needs at least {MIN_POSITIONS_PER_LOCATION}"
            )


# ---------------------------------------------------------------------------
# 2. All positions are within frame bounds
# ---------------------------------------------------------------------------

class TestPositionsWithinFrame:
    """All position coordinates must be within the frame with sprite margin."""

    def test_x_not_too_far_left(self, all_positions):
        for loc_id, pos_name, x, y in all_positions:
            assert x >= MIN_POSITION_X, (
                f"{loc_id}/{pos_name}: x={x} is too far left "
                f"(min={MIN_POSITION_X})"
            )

    def test_x_not_too_far_right(self, all_positions):
        for loc_id, pos_name, x, y in all_positions:
            assert x <= MAX_POSITION_X, (
                f"{loc_id}/{pos_name}: x={x} is too far right "
                f"(max={MAX_POSITION_X})"
            )

    def test_y_within_location_ground_zone(self, locations):
        """Characters must be within the ground_zone defined for each location.
        Every location MUST define a ground_zone with min_y and max_y.
        This prevents characters from floating in the sky or ceiling."""
        for loc_id, loc_data in locations.items():
            ground_zone = loc_data.get("ground_zone")
            assert ground_zone is not None, (
                f"{loc_id}: missing 'ground_zone' — every location must define "
                f"the y-range where the ground is (e.g., {{'min_y': 1050, 'max_y': 1480}})"
            )
            gz_min = ground_zone["min_y"]
            gz_max = ground_zone["max_y"]
            assert gz_max <= MAX_POSITION_Y, (
                f"{loc_id}: ground_zone max_y={gz_max} exceeds "
                f"MAX_POSITION_Y={MAX_POSITION_Y} (would overlap text box)"
            )
            for pos_name, pos_data in loc_data.get("character_positions", {}).items():
                y = pos_data["y"]
                assert gz_min <= y <= gz_max, (
                    f"{loc_id}/{pos_name}: y={y} is outside ground zone "
                    f"[{gz_min}, {gz_max}] — character would float or sink"
                )

    def test_y_not_below_max(self, all_positions):
        """Characters must stay above the text box safe zone."""
        for loc_id, pos_name, x, y in all_positions:
            assert y <= MAX_POSITION_Y, (
                f"{loc_id}/{pos_name}: y={y} exceeds max={MAX_POSITION_Y}, "
                f"would overlap with dialogue text box at y={TEXT_BOX_Y}"
            )


# ---------------------------------------------------------------------------
# 3. No overlap with dialogue text box
# ---------------------------------------------------------------------------

class TestDialogueBoxClearance:
    """Character sprites must never overlap the dialogue text box area."""

    def test_character_bottom_clears_text_box(self, all_positions):
        """The bottom of a character (feet at y) plus margin must be
        above the text box (y=1680)."""
        margin = 100  # At least 100px gap between character feet and text box
        for loc_id, pos_name, x, y in all_positions:
            assert y + margin <= TEXT_BOX_Y, (
                f"{loc_id}/{pos_name}: character feet at y={y} + "
                f"{margin}px margin = {y + margin} overlaps text box at "
                f"y={TEXT_BOX_Y}"
            )


# ---------------------------------------------------------------------------
# 4. No character stacking (positions spaced apart)
# ---------------------------------------------------------------------------

class TestNoCharacterStacking:
    """Positions within the same location must be spaced far enough apart
    that two character sprites won't visually overlap.

    Sprites occupy: x ± (width/2), y - height to y.
    Two sprites overlap when BOTH x-ranges AND y-ranges intersect.
    So to NOT overlap, either x_dist >= sprite_width OR y_dist >= sprite_height.
    """

    def test_no_visual_overlap(self, locations):
        """No two positions in the same location should cause sprite overlap."""
        for loc_id, loc_data in locations.items():
            positions = loc_data.get("character_positions", {})
            pos_list = list(positions.items())

            for i in range(len(pos_list)):
                for j in range(i + 1, len(pos_list)):
                    name_a, data_a = pos_list[i]
                    name_b, data_b = pos_list[j]

                    x_dist = abs(data_a["x"] - data_b["x"])
                    y_dist = abs(data_a["y"] - data_b["y"])

                    # Sprites don't overlap if separated on EITHER axis.
                    # Add 20px padding for visual clarity.
                    x_clear = x_dist >= MAX_SPRITE_WIDTH + 20  # 212px
                    y_clear = y_dist >= MAX_SPRITE_HEIGHT + 20  # 308px

                    assert x_clear or y_clear, (
                        f"{loc_id}: '{name_a}' ({data_a['x']},{data_a['y']}) and "
                        f"'{name_b}' ({data_b['x']},{data_b['y']}) would cause "
                        f"sprite overlap — x_dist={x_dist} (need >= {MAX_SPRITE_WIDTH + 20}) "
                        f"or y_dist={y_dist} (need >= {MAX_SPRITE_HEIGHT + 20})"
                    )


# ---------------------------------------------------------------------------
# 5. Default fallback position is safe
# ---------------------------------------------------------------------------

class TestDefaultFallbackPosition:
    """The fallback position used when a position name is not found
    must also be within safe bounds."""

    def test_fallback_y_within_bounds(self):
        """Fallback position must not overlap text box."""
        # Request a position that doesn't exist to trigger fallback
        x, y = get_character_position("diner_interior", "nonexistent_position")
        assert y <= MAX_POSITION_Y, (
            f"Default fallback y={y} exceeds max={MAX_POSITION_Y}, "
            f"would overlap dialogue text box"
        )

    def test_fallback_x_within_bounds(self):
        """Fallback position must be within horizontal frame bounds."""
        x, y = get_character_position("diner_interior", "nonexistent_position")
        assert MIN_POSITION_X <= x <= MAX_POSITION_X, (
            f"Default fallback x={x} is outside safe range "
            f"[{MIN_POSITION_X}, {MAX_POSITION_X}]"
        )

    def test_fallback_y_not_in_sky(self):
        """Fallback should not place characters in the top quarter."""
        x, y = get_character_position("diner_interior", "nonexistent_position")
        min_y = FRAME_HEIGHT // 4
        assert y >= min_y, (
            f"Default fallback y={y} is in the sky zone (min={min_y})"
        )


# ---------------------------------------------------------------------------
# 6. Position data integrity
# ---------------------------------------------------------------------------

class TestPositionDataIntegrity:
    """Validate the structure and types of position data."""

    def test_all_positions_have_x_and_y(self, locations):
        """Every position must have numeric x and y keys."""
        for loc_id, loc_data in locations.items():
            for pos_name, pos_data in loc_data.get("character_positions", {}).items():
                assert "x" in pos_data, f"{loc_id}/{pos_name}: missing 'x'"
                assert "y" in pos_data, f"{loc_id}/{pos_name}: missing 'y'"
                assert isinstance(pos_data["x"], (int, float)), (
                    f"{loc_id}/{pos_name}: x must be a number"
                )
                assert isinstance(pos_data["y"], (int, float)), (
                    f"{loc_id}/{pos_name}: y must be a number"
                )

    def test_all_locations_have_background_file(self, locations):
        """Every location must reference a background file."""
        for loc_id, loc_data in locations.items():
            assert "background_file" in loc_data, (
                f"{loc_id}: missing 'background_file'"
            )

    def test_all_background_files_exist(self, locations):
        """Every referenced background file must exist on disk."""
        assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
        for loc_id, loc_data in locations.items():
            bg_file = loc_data.get("background_file", "")
            bg_path = os.path.join(assets_dir, "backgrounds", bg_file)
            assert os.path.exists(bg_path), (
                f"{loc_id}: background file '{bg_file}' not found at {bg_path}"
            )

    def test_position_coordinates_are_integers(self, all_positions):
        """Positions should use integer coordinates (pixel values)."""
        for loc_id, pos_name, x, y in all_positions:
            assert isinstance(x, int), (
                f"{loc_id}/{pos_name}: x={x} should be int, got {type(x)}"
            )
            assert isinstance(y, int), (
                f"{loc_id}/{pos_name}: y={y} should be int, got {type(y)}"
            )


# ---------------------------------------------------------------------------
# 7. get_character_position resolves correctly
# ---------------------------------------------------------------------------

class TestGetCharacterPosition:
    """Verify sprite_manager.get_character_position returns correct coords."""

    def test_known_position_returns_correct_values(self, locations):
        """get_character_position should return the exact x,y from JSON."""
        for loc_id, loc_data in locations.items():
            for pos_name, pos_data in loc_data.get("character_positions", {}).items():
                x, y = get_character_position(loc_id, pos_name)
                assert x == pos_data["x"], (
                    f"{loc_id}/{pos_name}: expected x={pos_data['x']}, got {x}"
                )
                assert y == pos_data["y"], (
                    f"{loc_id}/{pos_name}: expected y={pos_data['y']}, got {y}"
                )

    def test_unknown_location_returns_fallback(self):
        """Unknown location should return the fallback position."""
        x, y = get_character_position("nonexistent_location", "some_pos")
        assert isinstance(x, int)
        assert isinstance(y, int)
        assert y <= MAX_POSITION_Y

    def test_unknown_position_returns_fallback(self):
        """Unknown position name should return the fallback."""
        x, y = get_character_position("diner_interior", "nonexistent_pos")
        assert isinstance(x, int)
        assert isinstance(y, int)
        assert y <= MAX_POSITION_Y

    def test_fallback_uses_location_ground_zone(self):
        """Fallback for invalid position should land in the location's ground zone,
        not a hardcoded global default that may be above the ground."""
        with open(os.path.join(DATA_DIR, "locations.json"), "r") as f:
            locations = json.load(f)["locations"]

        for loc_id, loc_data in locations.items():
            gz = loc_data["ground_zone"]
            x, y = get_character_position(loc_id, "nonexistent_pos")
            assert gz["min_y"] <= y <= gz["max_y"], (
                f"{loc_id}: fallback y={y} is outside ground zone "
                f"[{gz['min_y']}, {gz['max_y']}]"
            )


# ---------------------------------------------------------------------------
# 8. LLM prompt includes valid position names
# ---------------------------------------------------------------------------

class TestPromptIncludesPositions:
    """The LLM prompt must list valid position names per location
    so the LLM doesn't hallucinate non-existent position names."""

    def test_prompt_contains_position_names(self):
        """build_story_prompt must include the location's position names."""
        from src.story_generator.prompts import build_story_prompt

        idea = {
            "character_a": "oinks",
            "character_b": "chubs",
            "additional_characters": [],
            "location": "town_square",
            "situation": "everyday_life",
            "punchline_type": "deadpan",
            "trending_tie_in": None,
            "seasonal_theme": None,
            "continuity_callbacks": [],
        }
        prompt = build_story_prompt(idea, "EP999")

        # The prompt must contain the actual position names from town_square
        assert "bench_left" in prompt, (
            "Prompt must include valid position name 'bench_left' for town_square"
        )
        assert "fountain_center" in prompt, (
            "Prompt must include valid position name 'fountain_center' for town_square"
        )
        assert "bench_right" in prompt, (
            "Prompt must include valid position name 'bench_right' for town_square"
        )


# ---------------------------------------------------------------------------
# 9. Validator catches invalid position names
# ---------------------------------------------------------------------------

class TestValidatorCatchesBadPositions:
    """The script validator must reject scripts with position names
    that don't exist in locations.json."""

    def test_invalid_position_name_flagged(self):
        """A script using 'center_left' for town_square should fail validation."""
        from src.story_generator.validator import validate_script

        script = {
            "episode_id": "EP999",
            "title": "Test",
            "slug": "test",
            "created_at": "2026-01-01T00:00:00Z",
            "version": 1,
            "generation_params": {
                "character_a": "oinks",
                "character_b": "chubs",
                "location": "town_square",
                "situation": "everyday_life",
                "punchline_type": "deadpan",
                "trending_tie_in": None,
                "seasonal_theme": None,
                "continuity_callbacks": [],
            },
            "duration_target_seconds": 35,
            "scenes": [
                {
                    "scene_number": 1,
                    "duration_seconds": 10,
                    "background": "town_square",
                    "characters_present": ["oinks", "chubs"],
                    "character_positions": {
                        "oinks": "center_left",
                        "chubs": "center_right",
                    },
                    "action_description": "Test",
                    "dialogue": [
                        {"character": "oinks", "text": "Hello", "duration_ms": 2000}
                    ],
                }
            ],
            "end_card": {"duration_seconds": 3, "text": "Follow!"},
            "continuity_log": {"events": ["test"], "new_running_gags": [], "character_developments": []},
            "metadata": {
                "total_duration_seconds": 13,
                "characters_featured": ["oinks", "chubs"],
                "primary_location": "town_square",
                "content_pillar": "everyday_life",
                "punchline_type": "deadpan",
            },
        }

        is_valid, errors = validate_script(script)
        position_errors = [e for e in errors if "position" in e.lower()]
        assert len(position_errors) >= 1, (
            f"Validator should flag invalid position names 'center_left'/'center_right' "
            f"for town_square. Got errors: {errors}"
        )

    def test_valid_position_name_passes(self):
        """A script using real position names should not get position errors."""
        from src.story_generator.validator import validate_script

        script = {
            "episode_id": "EP999",
            "title": "Test",
            "slug": "test",
            "created_at": "2026-01-01T00:00:00Z",
            "version": 1,
            "generation_params": {
                "character_a": "oinks",
                "character_b": "chubs",
                "location": "town_square",
                "situation": "everyday_life",
                "punchline_type": "deadpan",
                "trending_tie_in": None,
                "seasonal_theme": None,
                "continuity_callbacks": [],
            },
            "duration_target_seconds": 35,
            "scenes": [
                {
                    "scene_number": 1,
                    "duration_seconds": 10,
                    "background": "town_square",
                    "characters_present": ["oinks", "chubs"],
                    "character_positions": {
                        "oinks": "bench_left",
                        "chubs": "bench_right",
                    },
                    "action_description": "Test",
                    "dialogue": [
                        {"character": "oinks", "text": "Hello", "duration_ms": 2000}
                    ],
                }
            ],
            "end_card": {"duration_seconds": 3, "text": "Follow!"},
            "continuity_log": {"events": ["test"], "new_running_gags": [], "character_developments": []},
            "metadata": {
                "total_duration_seconds": 13,
                "characters_featured": ["oinks", "chubs"],
                "primary_location": "town_square",
                "content_pillar": "everyday_life",
                "punchline_type": "deadpan",
            },
        }

        is_valid, errors = validate_script(script)
        position_errors = [e for e in errors if "position" in e.lower()]
        assert len(position_errors) == 0, (
            f"Valid position names should not trigger errors. Got: {position_errors}"
        )


# ---------------------------------------------------------------------------
# 10. Anti-overlap at render time
# ---------------------------------------------------------------------------

class TestRenderTimeAntiOverlap:
    """When two characters resolve to the same or nearby positions,
    the renderer must nudge them apart."""

    def test_two_chars_same_fallback_get_separated(self):
        """Two characters both hitting fallback should NOT get identical coordinates."""
        from src.video_assembler.sprite_manager import resolve_scene_positions

        positions = resolve_scene_positions(
            location_id="town_square",
            characters=["oinks", "chubs"],
            char_positions={"oinks": "nonexistent", "chubs": "nonexistent"},
        )
        oinks_pos = positions["oinks"]
        chubs_pos = positions["chubs"]

        x_dist = abs(oinks_pos[0] - chubs_pos[0])
        y_dist = abs(oinks_pos[1] - chubs_pos[1])

        x_clear = x_dist >= MAX_SPRITE_WIDTH
        y_clear = y_dist >= MAX_SPRITE_HEIGHT

        assert x_clear or y_clear, (
            f"Two characters at fallback should be separated: "
            f"oinks={oinks_pos}, chubs={chubs_pos}, "
            f"x_dist={x_dist}, y_dist={y_dist}"
        )

    def test_valid_positions_preserved(self):
        """Characters with valid distinct positions should keep their exact coordinates."""
        from src.video_assembler.sprite_manager import resolve_scene_positions

        positions = resolve_scene_positions(
            location_id="town_square",
            characters=["oinks", "chubs"],
            char_positions={"oinks": "bench_left", "chubs": "bench_right"},
        )

        assert positions["oinks"] == (150, 1350)
        assert positions["chubs"] == (900, 1350)
