"""Sprite manager — loads, scales, and positions character sprites."""

import json
import os
from PIL import Image, ImageOps

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

# Sprites are pre-sized to ~192x288 display size by resize_for_pipeline.py
SPRITE_SCALE = 1

# Warning collection — caller can check for silent fallbacks after rendering
_warnings = []


def get_warnings():
    """Return list of warnings collected during rendering."""
    return list(_warnings)


def clear_warnings():
    """Clear the warning list. Call before starting a new render."""
    _warnings.clear()


def _load_locations():
    with open(os.path.join(DATA_DIR, "locations.json"), "r") as f:
        return json.load(f)["locations"]


def _load_characters():
    with open(os.path.join(DATA_DIR, "characters.json"), "r") as f:
        return json.load(f)["characters"]


def get_default_facing(character_id):
    """Get the default facing direction of a character's source sprite.

    Returns "left" or "right" based on characters.json default_facing field.
    Falls back to "right" if not specified.
    """
    characters = _load_characters()
    char_data = characters.get(character_id, {})
    return char_data.get("default_facing", "right")


def load_sprite(character_id, state="idle"):
    """Load a character sprite and scale it up with nearest-neighbor.

    Args:
        character_id: e.g., "pens"
        state: sprite state e.g., "idle", "talking"

    Returns:
        PIL Image (RGBA) scaled to video size.
    """
    sprite_path = os.path.join(
        ASSETS_DIR, "characters", character_id, f"{state}.png"
    )
    if not os.path.exists(sprite_path):
        # Fall back to idle
        sprite_path = os.path.join(
            ASSETS_DIR, "characters", character_id, "idle.png"
        )
    if not os.path.exists(sprite_path):
        # Character is completely missing — warn loudly, return placeholder so pipeline doesn't crash
        msg = f"[WARNING] Missing character sprite: {character_id}/idle.png — using transparent placeholder"
        print(msg)
        _warnings.append(msg)
        return Image.new("RGBA", (192, 288), (0, 0, 0, 0))

    sprite = Image.open(sprite_path).convert("RGBA")
    scaled = sprite.resize(
        (sprite.width * SPRITE_SCALE, sprite.height * SPRITE_SCALE),
        Image.NEAREST
    )
    return scaled


def _location_fallback(loc, ground_y=None, frame_width=1080, frame_height=1920):
    """Pick the first defined position for a location as the fallback.

    Uses ground-anchored math to compute pixel coordinates.
    Falls back to ground line center if the location has no positions.
    """
    if ground_y is None:
        ground_y = loc.get("ground_y", {"horizontal": 0.80, "vertical": 0.70})
    positions = loc.get("character_positions", {})
    if positions:
        first = next(iter(positions.values()))
        return resolve_ground_position(ground_y, first, frame_width, frame_height)
    # No positions defined — center of frame at ground line
    orientation = "vertical" if frame_height > frame_width else "horizontal"
    gy = ground_y.get(orientation, 0.75)
    return frame_width // 2, int(frame_height * gy), "right"


def get_character_position(location_id, position_name,
                           frame_width=1080, frame_height=1920):
    """Get the pixel coordinates for a character position in a location.

    Uses ground-anchored positioning: resolves x_pct and y_offset relative
    to the location's ground_y for the given frame dimensions.

    Args:
        location_id: e.g., "diner"
        position_name: e.g., "stool_1"
        frame_width: Target frame width (default 1080 for backward compat).
        frame_height: Target frame height (default 1920 for backward compat).

    Returns:
        (x, y) pixel tuple.
    """
    locations = _load_locations()
    loc = locations.get(location_id, {})
    ground_y = loc.get("ground_y", {"horizontal": 0.80, "vertical": 0.70})
    positions = loc.get("character_positions", {})
    pos = positions.get(position_name)
    if pos:
        x, y, _facing = resolve_ground_position(ground_y, pos, frame_width, frame_height)
        return x, y

    # Invalid position name — fall back to first valid position for this location
    if position_name and positions:
        print(f"[Sprite Manager] Warning: position '{position_name}' not found in {location_id}, using fallback")
    x, y, _facing = _location_fallback(loc, ground_y, frame_width, frame_height)
    return x, y


# Reference frame height for y_offset scaling — offsets are authored at 1080px
Y_OFFSET_REF_HEIGHT = 1080

MIN_OVERLAP_DISTANCE = 192  # sprite width — characters closer than this overlap


def resolve_ground_position(ground_y, pos_data, frame_width, frame_height):
    """Compute pixel (x, y) from ground-anchored position data.

    Uses the industry-standard bottom-anchor approach: a per-orientation
    ground line (ground_y) plus a per-position y_offset, combined with
    x_pct for horizontal placement.

    Args:
        ground_y: Dict with "horizontal" and "vertical" ground line fractions.
        pos_data: Dict with "x_pct" (0-1 fraction) and "y_offset" (ref 1080px).
        frame_width: Target frame width in pixels.
        frame_height: Target frame height in pixels.

    Returns:
        (x, y) pixel tuple where y = character feet position.
    """
    # Pick orientation based on aspect ratio
    orientation = "vertical" if frame_height > frame_width else "horizontal"
    gy = ground_y[orientation]

    ground_pixel_y = frame_height * gy
    # Scale y_offset from 1080 reference to actual frame height
    scaled_offset = pos_data.get("y_offset", 0) * frame_height / Y_OFFSET_REF_HEIGHT

    x = int(pos_data["x_pct"] * frame_width)
    y = int(ground_pixel_y + scaled_offset)
    facing = pos_data.get("facing", "right")
    return x, y, facing


def resolve_scene_positions(location_id, characters, char_positions,
                            frame_width=1080, frame_height=1920):
    """Resolve all character positions for a scene, preventing overlap.

    Uses the ground-anchored positioning system: each position's x_pct
    and y_offset are converted to pixel coordinates relative to the
    location's ground_y for the current orientation.

    Args:
        location_id: e.g., "town_square"
        characters: list of character IDs present in the scene
        char_positions: dict mapping character_id → position_name from script
        frame_width: Target frame width (default 1080 for backward compat).
        frame_height: Target frame height (default 1920 for backward compat).

    Returns:
        Dict mapping character_id → (x, y) pixel tuples.
    """
    locations = _load_locations()
    loc = locations.get(location_id, {})
    available = loc.get("character_positions", {})
    ground_y = loc.get("ground_y", {"horizontal": 0.80, "vertical": 0.70})
    available_names = list(available.keys())
    available_list = list(available.values())

    resolved = {}
    used_indices = set()

    # First pass: resolve valid position names via ground-anchored math
    for char_id in characters:
        pos_name = char_positions.get(char_id, "")
        pos_data = available.get(pos_name)
        if pos_data:
            resolved[char_id] = resolve_ground_position(
                ground_y, pos_data, frame_width, frame_height
            )
            # Track which position index was used
            idx = available_names.index(pos_name)
            used_indices.add(idx)

    # Second pass: assign unresolved characters to unused positions
    unresolved = [c for c in characters if c not in resolved]
    unused = [i for i in range(len(available_list)) if i not in used_indices]

    for char_id in unresolved:
        if unused:
            idx = unused.pop(0)
            pos_data = available_list[idx]
            resolved[char_id] = resolve_ground_position(
                ground_y, pos_data, frame_width, frame_height
            )
            used_indices.add(idx)
        elif available_list:
            # All positions taken — pick the one furthest from already-placed chars
            best_idx = 0
            best_min_dist = -1
            for i, pos_data in enumerate(available_list):
                px, py, _pf = resolve_ground_position(
                    ground_y, pos_data, frame_width, frame_height
                )
                min_dist = min(
                    (abs(px - rv[0]) for rv in resolved.values()),
                    default=9999,
                )
                if min_dist > best_min_dist:
                    best_min_dist = min_dist
                    best_idx = i
            resolved[char_id] = resolve_ground_position(
                ground_y, available_list[best_idx], frame_width, frame_height
            )
        else:
            # No positions at all — use ground line center as fallback
            orientation = "vertical" if frame_height > frame_width else "horizontal"
            gy = ground_y.get(orientation, 0.75)
            resolved[char_id] = (frame_width // 2, int(frame_height * gy), "right")

    return resolved


def composite_character(frame, character_id, state, location_id, position_name):
    """Composite a character sprite onto a frame at the specified position.

    Args:
        frame: PIL Image (the current frame, 1080x1920)
        character_id: e.g., "pens"
        state: sprite state
        location_id: e.g., "diner"
        position_name: e.g., "stool_1" or an (x, y) tuple

    Returns:
        The frame with the character composited.
    """
    sprite = load_sprite(character_id, state)

    # Accept pre-resolved (x, y, facing) or (x, y) tuple, or look up by name
    if isinstance(position_name, tuple):
        if len(position_name) == 3:
            x, y, facing = position_name
        else:
            x, y = position_name
            facing = "right"
    else:
        x, y = get_character_position(location_id, position_name)
        facing = "right"

    # Mirror sprite when the desired facing differs from the sprite's
    # natural orientation. Each character's source sprite faces a specific
    # direction (default_facing in characters.json). We only flip when
    # the position wants the opposite direction.
    default_facing = get_default_facing(character_id)
    if facing != default_facing:
        sprite = ImageOps.mirror(sprite)

    # Center the sprite on the position point
    paste_x = x - sprite.width // 2
    paste_y = y - sprite.height

    # Clamp to frame bounds
    paste_x = max(0, min(paste_x, frame.width - sprite.width))
    paste_y = max(0, min(paste_y, frame.height - sprite.height))

    frame.paste(sprite, (paste_x, paste_y), sprite)
    return frame
