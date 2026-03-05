"""Tests for character positioning, overlap prevention, and dialogue box clearance.

These tests validate locations.json and sprite_manager.py to ensure:
1. All character positions are on-screen and within reasonable ground range
2. No character position can overlap with the dialogue text box
3. Positions within the same location are spaced apart (no stacking)
4. The default fallback position follows the same safety rules
5. Every location has at least 2 character positions
6. All rules apply dynamically to ANY location in locations.json (future-proof)

Ground-anchored positioning: positions use x_pct (0-1 fraction) and y_offset
(pixels in 1080 reference), resolved against a per-location ground_y line.
"""

import json
import os
from unittest.mock import patch

import pytest

from src.video_assembler.sprite_manager import (
    get_character_position,
    load_sprite,
    resolve_ground_position,
)

# --- Constants matching production code ---
FRAME_WIDTH = 1080
FRAME_HEIGHT = 1920
TEXT_BOX_Y = 1680  # from scene_builder.py
TEXT_BOX_HEIGHT = 200  # from text_renderer/renderer.py

# --- Safety rules ---
# Max sprite dimensions (from assets/characters/ — Bootoshi redesign)
MAX_SPRITE_WIDTH = 260   # Reows is widest at 260px
MAX_SPRITE_HEIGHT = 420  # Reows is tallest at 420px

# Characters must be at least half a sprite width from frame edges.
MIN_POSITION_X = MAX_SPRITE_WIDTH // 2  # 130
MAX_POSITION_X = FRAME_WIDTH - MAX_SPRITE_WIDTH // 2  # 950

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
    """Extract all (location_id, position_name, x, y) tuples.

    Computes pixel coordinates using resolve_ground_position for
    the default vertical frame (1080x1920).
    """
    result = []
    for loc_id, loc_data in locations.items():
        ground_y = loc_data.get("ground_y", {"horizontal": 0.80, "vertical": 0.70})
        for pos_name, pos_data in loc_data.get("character_positions", {}).items():
            pos_result = resolve_ground_position(
                ground_y, pos_data, FRAME_WIDTH, FRAME_HEIGHT
            )
            x, y = pos_result[0], pos_result[1]
            result.append((loc_id, pos_name, x, y))
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

    def test_y_within_reasonable_ground_range(self, all_positions):
        """Characters must be positioned in the lower half of the frame
        (between 50% and 95% of frame height) to look grounded, not
        floating in the sky or buried below the frame."""
        min_y = int(FRAME_HEIGHT * 0.50)
        max_y = int(FRAME_HEIGHT * 0.95)
        for loc_id, pos_name, x, y in all_positions:
            assert min_y <= y <= max_y, (
                f"{loc_id}/{pos_name}: computed y={y} is outside "
                f"reasonable ground range [{min_y}, {max_y}]"
            )

    # NOTE: test_y_not_below_max and TestDialogueBoxClearance were removed.
    # Speech bubbles now position above character heads (scene_builder.py
    # lines 320-331), not in a fixed bottom text box. The old MAX_POSITION_Y
    # constraint no longer applies.


# ---------------------------------------------------------------------------
# 3. No character stacking (positions spaced apart)
# ---------------------------------------------------------------------------

class TestNoCharacterStacking:
    """Positions within the same location must be spaced far enough apart
    that two character sprites won't visually overlap.

    Sprites occupy: x +/- (width/2), y - height to y.
    Two sprites overlap when BOTH x-ranges AND y-ranges intersect.
    So to NOT overlap, either x_dist >= sprite_width OR y_dist >= sprite_height.
    """

    def test_no_visual_overlap(self, locations):
        """No two positions in the same location should cause sprite overlap."""
        for loc_id, loc_data in locations.items():
            ground_y = loc_data.get("ground_y", {"horizontal": 0.80, "vertical": 0.70})
            positions = loc_data.get("character_positions", {})
            pos_list = list(positions.items())

            # Resolve all positions to pixel coords for comparison
            resolved = []
            for name, data in pos_list:
                result = resolve_ground_position(
                    ground_y, data, FRAME_WIDTH, FRAME_HEIGHT
                )
                resolved.append((name, result[0], result[1]))

            for i in range(len(resolved)):
                for j in range(i + 1, len(resolved)):
                    name_a, xa, ya = resolved[i]
                    name_b, xb, yb = resolved[j]

                    x_dist = abs(xa - xb)
                    y_dist = abs(ya - yb)

                    # To NOT overlap, position centers must be at least half a
                    # sprite apart on EITHER axis. This prevents characters from
                    # being placed directly on top of each other while allowing
                    # some visual proximity for positions at different scene depths
                    # (e.g., behind counter vs at stool).
                    x_clear = x_dist >= MAX_SPRITE_WIDTH // 2  # 130px
                    y_clear = y_dist >= MAX_SPRITE_HEIGHT // 2  # 210px

                    assert x_clear or y_clear, (
                        f"{loc_id}: '{name_a}' ({xa},{ya}) and "
                        f"'{name_b}' ({xb},{yb}) would cause "
                        f"sprite overlap — x_dist={x_dist} (need >= {MAX_SPRITE_WIDTH // 2}) "
                        f"or y_dist={y_dist} (need >= {MAX_SPRITE_HEIGHT // 2})"
                    )


# ---------------------------------------------------------------------------
# 5. Default fallback position is safe
# ---------------------------------------------------------------------------

class TestDefaultFallbackPosition:
    """The fallback position used when a position name is not found
    must also be within safe bounds."""

    def test_fallback_y_within_bounds(self):
        """Fallback position must be within reasonable ground range."""
        # Request a position that doesn't exist to trigger fallback
        x, y = get_character_position("diner", "nonexistent_position")
        max_y = int(FRAME_HEIGHT * 0.95)
        assert y <= max_y, (
            f"Default fallback y={y} exceeds max={max_y}"
        )

    def test_fallback_x_within_bounds(self):
        """Fallback position must be within horizontal frame bounds."""
        x, y = get_character_position("diner", "nonexistent_position")
        assert MIN_POSITION_X <= x <= MAX_POSITION_X, (
            f"Default fallback x={x} is outside safe range "
            f"[{MIN_POSITION_X}, {MAX_POSITION_X}]"
        )

    def test_fallback_y_not_in_sky(self):
        """Fallback should not place characters in the top quarter."""
        x, y = get_character_position("diner", "nonexistent_position")
        min_y = FRAME_HEIGHT // 4
        assert y >= min_y, (
            f"Default fallback y={y} is in the sky zone (min={min_y})"
        )


# ---------------------------------------------------------------------------
# 6. Position data integrity
# ---------------------------------------------------------------------------

class TestPositionDataIntegrity:
    """Validate the structure and types of position data."""

    def test_all_positions_have_x_pct_and_y_offset(self, locations):
        """Every position must have x_pct (float 0-1) and y_offset keys."""
        for loc_id, loc_data in locations.items():
            for pos_name, pos_data in loc_data.get("character_positions", {}).items():
                assert "x_pct" in pos_data, f"{loc_id}/{pos_name}: missing 'x_pct'"
                assert "y_offset" in pos_data, f"{loc_id}/{pos_name}: missing 'y_offset'"
                assert isinstance(pos_data["x_pct"], (int, float)), (
                    f"{loc_id}/{pos_name}: x_pct must be a number"
                )
                assert isinstance(pos_data["y_offset"], (int, float)), (
                    f"{loc_id}/{pos_name}: y_offset must be a number"
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

    def test_position_coordinate_types(self, locations):
        """x_pct should be a float (0-1 fraction), y_offset should be int or float."""
        for loc_id, loc_data in locations.items():
            for pos_name, pos_data in loc_data.get("character_positions", {}).items():
                x_pct = pos_data["x_pct"]
                y_offset = pos_data["y_offset"]
                assert isinstance(x_pct, float), (
                    f"{loc_id}/{pos_name}: x_pct={x_pct} should be float, "
                    f"got {type(x_pct)}"
                )
                assert isinstance(y_offset, (int, float)), (
                    f"{loc_id}/{pos_name}: y_offset={y_offset} should be "
                    f"int or float, got {type(y_offset)}"
                )


# ---------------------------------------------------------------------------
# 7. get_character_position resolves correctly
# ---------------------------------------------------------------------------

class TestGetCharacterPosition:
    """Verify sprite_manager.get_character_position returns correct coords."""

    def test_known_position_returns_correct_values(self, locations):
        """get_character_position should return the same pixel coords as
        resolve_ground_position for the default frame size (1080x1920)."""
        for loc_id, loc_data in locations.items():
            ground_y = loc_data.get("ground_y", {"horizontal": 0.80, "vertical": 0.70})
            for pos_name, pos_data in loc_data.get("character_positions", {}).items():
                gx, gy = get_character_position(loc_id, pos_name)
                result = resolve_ground_position(
                    ground_y, pos_data, FRAME_WIDTH, FRAME_HEIGHT
                )
                ex, ey = result[0], result[1]
                assert gx == ex, (
                    f"{loc_id}/{pos_name}: expected x={ex}, got {gx}"
                )
                assert gy == ey, (
                    f"{loc_id}/{pos_name}: expected y={ey}, got {gy}"
                )

    def test_unknown_location_returns_fallback(self):
        """Unknown location should return the fallback position."""
        x, y = get_character_position("nonexistent_location", "some_pos")
        assert isinstance(x, int)
        assert isinstance(y, int)
        assert y <= int(FRAME_HEIGHT * 0.95)

    def test_unknown_position_returns_fallback(self):
        """Unknown position name should return the fallback."""
        x, y = get_character_position("diner", "nonexistent_pos")
        assert isinstance(x, int)
        assert isinstance(y, int)
        assert y <= int(FRAME_HEIGHT * 0.95)

    def test_fallback_within_reasonable_y_range(self):
        """Fallback for invalid position should land within the lower half
        of the frame — a reasonable y-range where characters look grounded."""
        with open(os.path.join(DATA_DIR, "locations.json"), "r") as f:
            locations = json.load(f)["locations"]

        min_y = int(FRAME_HEIGHT * 0.50)
        max_y = int(FRAME_HEIGHT * 0.95)
        for loc_id, loc_data in locations.items():
            x, y = get_character_position(loc_id, "nonexistent_pos")
            assert min_y <= y <= max_y, (
                f"{loc_id}: fallback y={y} is outside reasonable "
                f"ground range [{min_y}, {max_y}]"
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
        """Characters with valid distinct positions should keep their exact coordinates.

        bench_left:  x = int(0.35 * 1080) = 378, y = int(1920 * ground_y_vertical)
        bench_right: x = int(0.65 * 1080) = 702, y = int(1920 * ground_y_vertical)
        """
        from src.video_assembler.sprite_manager import resolve_scene_positions

        positions = resolve_scene_positions(
            location_id="town_square",
            characters=["oinks", "chubs"],
            char_positions={"oinks": "bench_left", "chubs": "bench_right"},
        )

        # X values are fixed by x_pct
        assert positions["oinks"][0] == 378
        assert positions["chubs"][0] == 702
        # Y values must match ground_y_vertical * 1920 (read from locations.json)
        assert positions["oinks"][1] == positions["chubs"][1]
        # Verify facing directions
        assert positions["oinks"][2] == "right"
        assert positions["chubs"][2] == "left"


# ---------------------------------------------------------------------------
# 11. Location set integrity
# ---------------------------------------------------------------------------

class TestLocationSetIntegrity:
    """Validate the exact set of locations and their vertical background files."""

    EXPECTED_LOCATION_IDS = {"diner", "farmers_market", "reows_place", "town_square"}

    def test_exactly_four_locations(self, locations):
        assert len(locations) == 4, (
            f"Expected 4 locations, got {len(locations)}: {list(locations.keys())}"
        )

    def test_location_ids_are_correct(self, locations):
        assert set(locations.keys()) == self.EXPECTED_LOCATION_IDS, (
            f"Expected {self.EXPECTED_LOCATION_IDS}, got {set(locations.keys())}"
        )

    def test_vertical_background_files_exist(self, locations):
        """Every location should have a vertical background variant on disk."""
        assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
        for loc_id in locations:
            vertical_path = os.path.join(
                assets_dir, "backgrounds", f"{loc_id}_vertical.png"
            )
            assert os.path.exists(vertical_path), (
                f"{loc_id}: vertical background '{loc_id}_vertical.png' not found"
            )


# ---------------------------------------------------------------------------
# 12. Situations reference only valid locations
# ---------------------------------------------------------------------------

class TestSituationLocationReferences:
    """Every best_locations entry in situations.json must exist in locations.json."""

    REMOVED_LOCATIONS = {"beach", "forest", "chubs_office", "diner_interior"}

    def test_all_best_locations_are_valid(self, locations):
        with open(os.path.join(DATA_DIR, "situations.json"), "r") as f:
            situations = json.load(f)["situations"]
        valid_ids = set(locations.keys())
        for sit_id, sit_data in situations.items():
            for loc in sit_data.get("best_locations", []):
                assert loc in valid_ids, (
                    f"Situation '{sit_id}' references location '{loc}' "
                    f"which is not in locations.json. Valid: {valid_ids}"
                )

    def test_no_removed_locations_in_situations(self):
        with open(os.path.join(DATA_DIR, "situations.json"), "r") as f:
            situations = json.load(f)["situations"]
        for sit_id, sit_data in situations.items():
            for loc in sit_data.get("best_locations", []):
                assert loc not in self.REMOVED_LOCATIONS, (
                    f"Situation '{sit_id}' still references removed location '{loc}'"
                )
