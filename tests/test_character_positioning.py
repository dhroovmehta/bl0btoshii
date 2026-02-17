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
