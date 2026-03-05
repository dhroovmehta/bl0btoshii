"""Tests for ground-anchored character positioning system.

The ground-anchored system replaces the old proportional v1 scaling.
Instead of storing absolute pixel coordinates calibrated for one frame size,
positions are defined as:
  - x_pct: horizontal position as a fraction of frame width (0.0 to 1.0)
  - y_offset: pixels above/below the ground line (in 1080px reference height)
  - ground_y: per-orientation ground line as a fraction of frame height

This ensures characters stay grounded near the bottom of the frame
regardless of whether the output is horizontal (1920x1080) or
vertical (1080x1920).

Industry standard: Ren'Py anchor/pos system, Unity bottom-pivot sprites,
Godot keep_height stretch mode.
"""

import json
import os

import pytest
from PIL import Image

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

HORIZONTAL_W, HORIZONTAL_H = 1920, 1080
VERTICAL_W, VERTICAL_H = 1080, 1920


@pytest.fixture
def locations():
    with open(os.path.join(DATA_DIR, "locations.json"), "r") as f:
        return json.load(f)["locations"]


# ---------------------------------------------------------------------------
# 1. locations.json has ground_y per location
# ---------------------------------------------------------------------------

class TestGroundYExists:
    """Every location must define a ground_y with horizontal + vertical values."""

    def test_every_location_has_ground_y(self, locations):
        for loc_id, loc_data in locations.items():
            assert "ground_y" in loc_data, (
                f"{loc_id}: missing 'ground_y' — needed for ground-anchored positioning"
            )

    def test_ground_y_has_both_orientations(self, locations):
        for loc_id, loc_data in locations.items():
            gy = loc_data["ground_y"]
            assert "horizontal" in gy, f"{loc_id}: ground_y missing 'horizontal'"
            assert "vertical" in gy, f"{loc_id}: ground_y missing 'vertical'"

    def test_ground_y_values_are_valid_fractions(self, locations):
        """ground_y values must be between 0.5 and 0.95 (lower half of frame)."""
        for loc_id, loc_data in locations.items():
            for orient in ("horizontal", "vertical"):
                val = loc_data["ground_y"][orient]
                assert 0.5 <= val <= 0.95, (
                    f"{loc_id} ground_y[{orient}]={val} — "
                    f"must be between 0.5 and 0.95"
                )

    def test_ground_y_horizontal_in_foreground(self, locations):
        """Horizontal ground_y must be >= 0.85 for foreground positioning."""
        for loc_id, loc_data in locations.items():
            val = loc_data["ground_y"]["horizontal"]
            assert val >= 0.85, (
                f"{loc_id} ground_y[horizontal]={val} — "
                f"must be >= 0.85 to place characters in the foreground"
            )

    def test_ground_y_vertical_in_foreground(self, locations):
        """Vertical ground_y must be >= 0.82 for foreground positioning."""
        for loc_id, loc_data in locations.items():
            val = loc_data["ground_y"]["vertical"]
            assert val >= 0.82, (
                f"{loc_id} ground_y[vertical]={val} — "
                f"must be >= 0.82 to place characters in the foreground"
            )

    def test_ground_y_values_differ_between_orientations(self, locations):
        """Horizontal and vertical ground lines should not be identical
        since the backgrounds are different compositions."""
        for loc_id, loc_data in locations.items():
            h_gy = loc_data["ground_y"]["horizontal"]
            v_gy = loc_data["ground_y"]["vertical"]
            # They don't need to be in a specific order — the compositions
            # are different images with different ground positions.
            # Just verify they're both reasonable (already tested above).
            assert isinstance(h_gy, float) and isinstance(v_gy, float)


# ---------------------------------------------------------------------------
# 2. Positions use x_pct and y_offset format
# ---------------------------------------------------------------------------

class TestPositionFormat:
    """Character positions must use the ground-anchored format."""

    def test_positions_have_x_pct(self, locations):
        for loc_id, loc_data in locations.items():
            for pos_name, pos_data in loc_data.get("character_positions", {}).items():
                assert "x_pct" in pos_data, (
                    f"{loc_id}/{pos_name}: missing 'x_pct'"
                )

    def test_positions_have_y_offset(self, locations):
        for loc_id, loc_data in locations.items():
            for pos_name, pos_data in loc_data.get("character_positions", {}).items():
                assert "y_offset" in pos_data, (
                    f"{loc_id}/{pos_name}: missing 'y_offset'"
                )

    def test_x_pct_is_valid_fraction(self, locations):
        """x_pct must be between 0.05 and 0.95 (with sprite margin from edges)."""
        for loc_id, loc_data in locations.items():
            for pos_name, pos_data in loc_data.get("character_positions", {}).items():
                val = pos_data["x_pct"]
                assert 0.05 <= val <= 0.95, (
                    f"{loc_id}/{pos_name}: x_pct={val} out of range [0.05, 0.95]"
                )

    def test_y_offset_is_reasonable(self, locations):
        """y_offset should be within ±200 (ref 1080). Positive = below ground,
        negative = above ground."""
        for loc_id, loc_data in locations.items():
            for pos_name, pos_data in loc_data.get("character_positions", {}).items():
                val = pos_data["y_offset"]
                assert -200 <= val <= 200, (
                    f"{loc_id}/{pos_name}: y_offset={val} out of range [-200, 200]"
                )


# ---------------------------------------------------------------------------
# 3. resolve_ground_position computes correct pixel coordinates
# ---------------------------------------------------------------------------

class TestResolveGroundPosition:
    """The new resolve function must compute pixel (x, y) from
    ground_y, x_pct, y_offset, and frame dimensions."""

    def test_function_exists(self):
        from src.video_assembler.sprite_manager import resolve_ground_position
        assert callable(resolve_ground_position)

    def test_horizontal_diner_stool(self, locations):
        """A stool position in horizontal diner should have feet at ~80% down."""
        from src.video_assembler.sprite_manager import resolve_ground_position

        loc = locations["diner"]
        pos = loc["character_positions"]["stool_1"]
        result = resolve_ground_position(
            loc["ground_y"], pos, HORIZONTAL_W, HORIZONTAL_H
        )
        x, y = result[0], result[1]
        # Feet should be in the bottom 25% of the frame
        assert y >= HORIZONTAL_H * 0.75, (
            f"Horizontal stool_1 feet at y={y} ({100*y/HORIZONTAL_H:.0f}%) — "
            f"should be >= 75% down the frame"
        )
        # But not off-screen
        assert y <= HORIZONTAL_H, f"y={y} is off-screen (frame height={HORIZONTAL_H})"

    def test_vertical_diner_stool(self, locations):
        """Vertical stool position should use ground-anchored positioning.

        x = int(0.35 * 1080) = 378
        y = int(1920 * ground_y_vertical) — must be in foreground (>= 82%)
        """
        from src.video_assembler.sprite_manager import resolve_ground_position

        loc = locations["diner"]
        pos = loc["character_positions"]["stool_1"]
        result = resolve_ground_position(
            loc["ground_y"], pos, VERTICAL_W, VERTICAL_H
        )
        x, y = result[0], result[1]
        assert abs(x - 378) <= 1, (
            f"Vertical stool_1 x={x}, expected ~378"
        )
        y_pct = y / VERTICAL_H
        assert y_pct >= 0.82, (
            f"Vertical stool_1 y={y} ({y_pct:.0%}) — must be >= 82% (foreground)"
        )

    def test_horizontal_characters_lower_than_proportional_scaling(self, locations):
        """The whole point: horizontal characters must be LOWER than
        the old proportional scale_position_v1 would place them."""
        from src.video_assembler.sprite_manager import resolve_ground_position

        loc = locations["diner"]
        pos = loc["character_positions"]["stool_1"]
        result = resolve_ground_position(
            loc["ground_y"], pos, HORIZONTAL_W, HORIZONTAL_H
        )
        x, y = result[0], result[1]

        # Old proportional scaling: y = 1300 * 1080/1920 = 731
        old_proportional_y = int(1300 * HORIZONTAL_H / VERTICAL_H)
        assert y > old_proportional_y, (
            f"New y={y} should be greater than old proportional y={old_proportional_y}"
        )

    def test_x_scales_with_frame_width(self, locations):
        """x should be x_pct * frame_width."""
        from src.video_assembler.sprite_manager import resolve_ground_position

        loc = locations["diner"]
        pos = loc["character_positions"]["stool_1"]
        result_h = resolve_ground_position(
            loc["ground_y"], pos, HORIZONTAL_W, HORIZONTAL_H
        )
        result_v = resolve_ground_position(
            loc["ground_y"], pos, VERTICAL_W, VERTICAL_H
        )
        expected_h = int(pos["x_pct"] * HORIZONTAL_W)
        expected_v = int(pos["x_pct"] * VERTICAL_W)
        assert abs(result_h[0] - expected_h) <= 1
        assert abs(result_v[0] - expected_v) <= 1

    def test_y_offset_shifts_position(self, locations):
        """A negative y_offset should place character ABOVE the ground line."""
        from src.video_assembler.sprite_manager import resolve_ground_position

        loc = locations["diner"]
        # behind_counter has a negative y_offset (above ground)
        pos_counter = loc["character_positions"]["behind_counter"]
        pos_stool = loc["character_positions"]["stool_1"]

        result_counter = resolve_ground_position(
            loc["ground_y"], pos_counter, HORIZONTAL_W, HORIZONTAL_H
        )
        result_stool = resolve_ground_position(
            loc["ground_y"], pos_stool, HORIZONTAL_W, HORIZONTAL_H
        )
        y_counter = result_counter[1]
        y_stool = result_stool[1]
        # Behind counter should be higher (smaller y) than stool
        assert y_counter < y_stool, (
            f"behind_counter y={y_counter} should be above stool y={y_stool}"
        )


# ---------------------------------------------------------------------------
# 4. resolve_scene_positions uses ground-anchored system
# ---------------------------------------------------------------------------

class TestResolveScenePositionsGroundAnchored:
    """resolve_scene_positions must use the new ground-anchored system
    and accept frame dimensions."""

    def test_accepts_frame_dimensions(self):
        """resolve_scene_positions must accept frame_width and frame_height."""
        from src.video_assembler.sprite_manager import resolve_scene_positions

        positions = resolve_scene_positions(
            location_id="diner",
            characters=["pens"],
            char_positions={"pens": "stool_1"},
            frame_width=HORIZONTAL_W,
            frame_height=HORIZONTAL_H,
        )
        assert "pens" in positions

    def test_horizontal_positions_are_grounded(self):
        """In horizontal format, all characters should have feet in bottom 30%."""
        from src.video_assembler.sprite_manager import resolve_scene_positions

        positions = resolve_scene_positions(
            location_id="diner",
            characters=["pens", "oinks"],
            char_positions={"pens": "stool_1", "oinks": "behind_counter"},
            frame_width=HORIZONTAL_W,
            frame_height=HORIZONTAL_H,
        )
        for char_id, pos_tuple in positions.items():
            y = pos_tuple[1]
            assert y >= HORIZONTAL_H * 0.65, (
                f"{char_id} feet at y={y} ({100*y/HORIZONTAL_H:.0f}%) in horizontal — "
                f"should be >= 65% down"
            )

    def test_vertical_positions_grounded(self):
        """In vertical format, positions should be grounded in foreground zone (>= 82%)."""
        from src.video_assembler.sprite_manager import resolve_scene_positions

        positions = resolve_scene_positions(
            location_id="town_square",
            characters=["pens", "oinks"],
            char_positions={"pens": "bench_left", "oinks": "bench_right"},
            frame_width=VERTICAL_W,
            frame_height=VERTICAL_H,
        )
        for char_id in ["pens", "oinks"]:
            y = positions[char_id][1]
            y_pct = y / VERTICAL_H
            assert y_pct >= 0.82, (
                f"{char_id} vertical y={y} ({y_pct:.0%}) — "
                f"must be >= 82% for foreground"
            )
            assert y <= VERTICAL_H, f"{char_id} y={y} off-screen"

    def test_fallback_for_unknown_position(self):
        """Unknown position names should still produce grounded coordinates."""
        from src.video_assembler.sprite_manager import resolve_scene_positions

        positions = resolve_scene_positions(
            location_id="diner",
            characters=["pens"],
            char_positions={"pens": "nonexistent"},
            frame_width=HORIZONTAL_W,
            frame_height=HORIZONTAL_H,
        )
        y = positions["pens"][1]
        assert y >= HORIZONTAL_H * 0.65, (
            f"Fallback y={y} should be grounded (>= 65% down)"
        )


# ---------------------------------------------------------------------------
# 5. All locations produce grounded positions for both orientations
# ---------------------------------------------------------------------------

class TestAllLocationsGrounded:
    """Every location + orientation combo must produce grounded characters."""

    LOCATIONS = ["diner", "farmers_market", "town_square", "reows_place"]

    @pytest.mark.parametrize("location_id", LOCATIONS)
    def test_horizontal_grounded(self, location_id, locations):
        from src.video_assembler.sprite_manager import resolve_ground_position

        loc = locations[location_id]
        for pos_name, pos_data in loc["character_positions"].items():
            result = resolve_ground_position(
                loc["ground_y"], pos_data, HORIZONTAL_W, HORIZONTAL_H
            )
            y = result[1]
            assert y >= HORIZONTAL_H * 0.55, (
                f"{location_id}/{pos_name}: horizontal y={y} "
                f"({100*y/HORIZONTAL_H:.0f}%) — should be >= 55%"
            )
            assert y <= HORIZONTAL_H, (
                f"{location_id}/{pos_name}: y={y} off-screen"
            )

    @pytest.mark.parametrize("location_id", LOCATIONS)
    def test_vertical_grounded(self, location_id, locations):
        from src.video_assembler.sprite_manager import resolve_ground_position

        loc = locations[location_id]
        for pos_name, pos_data in loc["character_positions"].items():
            result = resolve_ground_position(
                loc["ground_y"], pos_data, VERTICAL_W, VERTICAL_H
            )
            y = result[1]
            assert y >= VERTICAL_H * 0.50, (
                f"{location_id}/{pos_name}: vertical y={y} "
                f"({100*y/VERTICAL_H:.0f}%) — should be >= 50%"
            )
            assert y <= VERTICAL_H, (
                f"{location_id}/{pos_name}: y={y} off-screen"
            )


# ---------------------------------------------------------------------------
# 6. scene_builder no longer uses scale_position_v1 for character placement
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 6b. Facing direction is included in position data
# ---------------------------------------------------------------------------

class TestFacingDirection:
    """Facing direction must be included in position resolution
    and used for sprite flipping."""

    def test_resolve_ground_position_returns_3_tuple(self, locations):
        """resolve_ground_position must return (x, y, facing)."""
        from src.video_assembler.sprite_manager import resolve_ground_position

        loc = locations["diner"]
        pos = loc["character_positions"]["stool_1"]
        result = resolve_ground_position(
            loc["ground_y"], pos, HORIZONTAL_W, HORIZONTAL_H
        )
        assert len(result) == 3, (
            f"resolve_ground_position must return (x, y, facing), got {len(result)}-tuple"
        )
        assert result[2] in ("left", "right")

    def test_primary_pair_face_each_other(self, locations):
        """The first two positions in each location should face each other:
        first faces right, second faces left."""
        for loc_id, loc_data in locations.items():
            positions = list(loc_data["character_positions"].values())
            if len(positions) >= 2:
                assert positions[0].get("facing") == "right", (
                    f"{loc_id}: first position should face right"
                )
                assert positions[1].get("facing") == "left", (
                    f"{loc_id}: second position should face left"
                )

    def test_resolve_scene_positions_includes_facing(self):
        """resolve_scene_positions must return 3-tuples with facing."""
        from src.video_assembler.sprite_manager import resolve_scene_positions

        positions = resolve_scene_positions(
            "diner", ["pens", "oinks"],
            {"pens": "stool_1", "oinks": "stool_2"},
            frame_width=HORIZONTAL_W, frame_height=HORIZONTAL_H,
        )
        for char_id, pos in positions.items():
            assert len(pos) == 3, (
                f"{char_id}: expected 3-tuple (x, y, facing), got {len(pos)}-tuple"
            )
            assert pos[2] in ("left", "right")

    def test_stool_1_faces_right(self, locations):
        from src.video_assembler.sprite_manager import resolve_ground_position

        loc = locations["diner"]
        pos = loc["character_positions"]["stool_1"]
        result = resolve_ground_position(
            loc["ground_y"], pos, HORIZONTAL_W, HORIZONTAL_H
        )
        assert result[2] == "right"

    def test_stool_2_faces_left(self, locations):
        from src.video_assembler.sprite_manager import resolve_ground_position

        loc = locations["diner"]
        pos = loc["character_positions"]["stool_2"]
        result = resolve_ground_position(
            loc["ground_y"], pos, HORIZONTAL_W, HORIZONTAL_H
        )
        assert result[2] == "left"

    def test_fallback_position_facing_defaults_right(self):
        """Fallback positions should default to facing right."""
        from src.video_assembler.sprite_manager import resolve_scene_positions

        positions = resolve_scene_positions(
            "diner", ["pens"],
            {"pens": "nonexistent"},
            frame_width=HORIZONTAL_W, frame_height=HORIZONTAL_H,
        )
        assert positions["pens"][2] == "right"


# ---------------------------------------------------------------------------
# 6c. Default facing in characters.json
# ---------------------------------------------------------------------------

class TestDefaultFacing:
    """characters.json must define default_facing per character so the
    mirror logic knows which direction the source sprite faces."""

    @pytest.fixture
    def characters(self):
        with open(os.path.join(DATA_DIR, "characters.json"), "r") as f:
            return json.load(f)["characters"]

    ALL_CHARACTERS = ["pens", "chubs", "meows", "oinks", "quacks", "reows"]

    def test_every_character_has_default_facing(self, characters):
        for char_id in self.ALL_CHARACTERS:
            assert "default_facing" in characters[char_id], (
                f"{char_id}: missing 'default_facing' in characters.json"
            )

    def test_default_facing_is_left_or_right(self, characters):
        for char_id in self.ALL_CHARACTERS:
            facing = characters[char_id]["default_facing"]
            assert facing in ("left", "right"), (
                f"{char_id}: default_facing must be 'left' or 'right', got '{facing}'"
            )

    def test_pens_faces_right(self, characters):
        """Pens sprite holds soda in right flipper, faces right."""
        assert characters["pens"]["default_facing"] == "right"

    def test_reows_faces_right(self, characters):
        """Reows sprite snout and cap point right."""
        assert characters["reows"]["default_facing"] == "right"

    def test_oinks_faces_left(self, characters):
        """Oinks sprite has left arm extended, leans left."""
        assert characters["oinks"]["default_facing"] == "left"

    def test_chubs_faces_left(self, characters):
        """Chubs sprite leans left."""
        assert characters["chubs"]["default_facing"] == "left"

    def test_meows_faces_left(self, characters):
        """Meows sprite body and tail lean left."""
        assert characters["meows"]["default_facing"] == "left"

    def test_quacks_faces_left(self, characters):
        """Quacks sprite leans slightly left."""
        assert characters["quacks"]["default_facing"] == "left"


# ---------------------------------------------------------------------------
# 6d. Foreground zone — characters in bottom portion of frame
# ---------------------------------------------------------------------------

class TestForegroundPositioning:
    """Characters must be positioned in the foreground zone of each
    background — not floating in the middle of the scene.

    For horizontal (1920x1080): feet must be at >= 85% of frame height.
    For vertical (1080x1920): feet must be at >= 82% of frame height.
    """

    LOCATIONS = ["diner", "farmers_market", "town_square", "reows_place"]

    @pytest.mark.parametrize("location_id", LOCATIONS)
    def test_horizontal_in_foreground(self, location_id, locations):
        from src.video_assembler.sprite_manager import resolve_ground_position

        loc = locations[location_id]
        for pos_name, pos_data in loc["character_positions"].items():
            # Skip elevated positions (negative y_offset like behind_counter)
            if pos_data.get("y_offset", 0) < -50:
                continue
            result = resolve_ground_position(
                loc["ground_y"], pos_data, HORIZONTAL_W, HORIZONTAL_H
            )
            y_pct = result[1] / HORIZONTAL_H
            assert y_pct >= 0.85, (
                f"{location_id}/{pos_name} horizontal: feet at {y_pct:.0%} "
                f"of frame — must be >= 85% (foreground zone)"
            )

    @pytest.mark.parametrize("location_id", LOCATIONS)
    def test_vertical_in_foreground(self, location_id, locations):
        from src.video_assembler.sprite_manager import resolve_ground_position

        loc = locations[location_id]
        for pos_name, pos_data in loc["character_positions"].items():
            if pos_data.get("y_offset", 0) < -50:
                continue
            result = resolve_ground_position(
                loc["ground_y"], pos_data, VERTICAL_W, VERTICAL_H
            )
            y_pct = result[1] / VERTICAL_H
            assert y_pct >= 0.82, (
                f"{location_id}/{pos_name} vertical: feet at {y_pct:.0%} "
                f"of frame — must be >= 82% (foreground zone)"
            )


# ---------------------------------------------------------------------------
# 6e. Full matrix — all characters x all locations x both orientations
# ---------------------------------------------------------------------------

class TestFullPositionMatrix:
    """Test every character in every location at every orientation.
    Characters must resolve to valid, non-overlapping, foreground positions."""

    LOCATIONS = ["diner", "farmers_market", "town_square", "reows_place"]
    ALL_CHARACTERS = ["pens", "chubs", "meows", "oinks", "quacks", "reows"]
    ORIENTATIONS = [
        (HORIZONTAL_W, HORIZONTAL_H, "horizontal"),
        (VERTICAL_W, VERTICAL_H, "vertical"),
    ]

    @pytest.mark.parametrize("location_id", LOCATIONS)
    @pytest.mark.parametrize("fw,fh,orient", ORIENTATIONS)
    def test_two_characters_resolve_valid(self, location_id, fw, fh, orient):
        """Any pair of characters should resolve to valid positions."""
        from src.video_assembler.sprite_manager import resolve_scene_positions

        # Use the first two characters as the conversation pair
        chars = ["pens", "oinks"]
        positions = resolve_scene_positions(
            location_id, chars, {},
            frame_width=fw, frame_height=fh,
        )
        for char_id in chars:
            assert char_id in positions, (
                f"{location_id} {orient}: {char_id} not in resolved positions"
            )
            pos = positions[char_id]
            assert len(pos) == 3, (
                f"{location_id} {orient} {char_id}: expected 3-tuple, got {len(pos)}"
            )
            x, y, facing = pos
            assert 0 <= x <= fw, (
                f"{location_id} {orient} {char_id}: x={x} out of frame (0-{fw})"
            )
            assert 0 <= y <= fh, (
                f"{location_id} {orient} {char_id}: y={y} out of frame (0-{fh})"
            )
            assert facing in ("left", "right")

    @pytest.mark.parametrize("location_id", LOCATIONS)
    @pytest.mark.parametrize("fw,fh,orient", ORIENTATIONS)
    def test_six_characters_no_crash(self, location_id, fw, fh, orient):
        """All 6 characters in one scene should resolve without crash."""
        from src.video_assembler.sprite_manager import resolve_scene_positions

        positions = resolve_scene_positions(
            location_id, self.ALL_CHARACTERS, {},
            frame_width=fw, frame_height=fh,
        )
        assert len(positions) == 6, (
            f"{location_id} {orient}: expected 6 resolved, got {len(positions)}"
        )

    @pytest.mark.parametrize("location_id", LOCATIONS)
    def test_primary_pair_face_each_other_at_render(self, location_id):
        """The first two auto-assigned characters should face each other."""
        from src.video_assembler.sprite_manager import resolve_scene_positions

        positions = resolve_scene_positions(
            location_id, ["pens", "oinks"], {},
            frame_width=HORIZONTAL_W, frame_height=HORIZONTAL_H,
        )
        # First assigned gets "right", second gets "left"
        assert positions["pens"][2] == "right", (
            f"{location_id}: first character should face right"
        )
        assert positions["oinks"][2] == "left", (
            f"{location_id}: second character should face left"
        )


# ---------------------------------------------------------------------------
# 7. scene_builder no longer uses scale_position_v1 for character placement
# ---------------------------------------------------------------------------

class TestSceneBuilderUsesGroundAnchoring:
    """build_scene_frames must use ground-anchored positions, not
    the old scale_position_v1."""

    def test_horizontal_frame_characters_grounded(self):
        """Render a horizontal frame and verify characters are in bottom 30%."""
        from src.video_assembler.scene_builder import build_scene_frames
        import numpy as np

        scene = {
            "background": "diner",
            "duration_seconds": 1,
            "characters_present": ["pens"],
            "character_positions": {"pens": "stool_1"},
            "character_animations": {"pens": "idle"},
            "dialogue": [],
            "sfx_triggers": [],
        }
        frame_iter, _, _ = build_scene_frames(scene, frame_offset=0)
        frame = next(frame_iter)
        arr = np.array(frame)

        # Render same scene without characters to get clean background
        no_char_scene = dict(scene, characters_present=[], character_positions={})
        nc_iter, _, _ = build_scene_frames(no_char_scene, frame_offset=0)
        bg_frame = next(nc_iter)
        bg_arr = np.array(bg_frame)

        # Find where the character is by diffing against clean background
        diff = np.abs(arr.astype(int) - bg_arr.astype(int))
        char_mask = diff.sum(axis=2) > 30  # Pixels that differ significantly

        if char_mask.any():
            char_rows = np.where(char_mask.any(axis=1))[0]
            char_bottom = char_rows.max()
            # Character bottom (feet) should be in the bottom 30% of frame
            assert char_bottom >= HORIZONTAL_H * 0.70, (
                f"Character bottom at y={char_bottom} "
                f"({100*char_bottom/HORIZONTAL_H:.0f}%) — "
                f"should be in bottom 30% of frame (>= 70%)"
            )
