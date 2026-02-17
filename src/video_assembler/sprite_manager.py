"""Sprite manager — loads, scales, and positions character sprites."""

import json
import os
from PIL import Image

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

# Sprites are pre-sized to ~192x288 display size by resize_for_pipeline.py
SPRITE_SCALE = 1


def _load_locations():
    with open(os.path.join(DATA_DIR, "locations.json"), "r") as f:
        return json.load(f)["locations"]


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
        # Create a transparent placeholder
        return Image.new("RGBA", (192, 288), (0, 0, 0, 0))

    sprite = Image.open(sprite_path).convert("RGBA")
    scaled = sprite.resize(
        (sprite.width * SPRITE_SCALE, sprite.height * SPRITE_SCALE),
        Image.NEAREST
    )
    return scaled


def _location_fallback(loc):
    """Pick the first defined position for a location as the fallback.
    Falls back to (450, 1300) only if the location has no positions at all."""
    positions = loc.get("character_positions", {})
    if positions:
        first = next(iter(positions.values()))
        return first["x"], first["y"]
    return 450, 1300


def get_character_position(location_id, position_name):
    """Get the pixel coordinates for a character position in a location.

    Args:
        location_id: e.g., "diner_interior"
        position_name: e.g., "stool_1"

    Returns:
        (x, y) tuple for the 1080x1920 frame.
    """
    locations = _load_locations()
    loc = locations.get(location_id, {})
    positions = loc.get("character_positions", {})
    pos = positions.get(position_name)
    if pos:
        return pos["x"], pos["y"]

    # Invalid position name — fall back to first valid position for this location
    if position_name and positions:
        print(f"[Sprite Manager] Warning: position '{position_name}' not found in {location_id}, using fallback")
    return _location_fallback(loc)


MIN_OVERLAP_DISTANCE = 192  # sprite width — characters closer than this overlap


def resolve_scene_positions(location_id, characters, char_positions):
    """Resolve all character positions for a scene, preventing overlap.

    Looks up each character's position name in locations.json.
    If two characters end up at the same or overlapping coordinates,
    nudges them to different available positions in the location.

    Args:
        location_id: e.g., "town_square"
        characters: list of character IDs present in the scene
        char_positions: dict mapping character_id → position_name from script

    Returns:
        Dict mapping character_id → (x, y) tuples.
    """
    locations = _load_locations()
    loc = locations.get(location_id, {})
    available = loc.get("character_positions", {})
    available_list = list(available.values())

    resolved = {}
    used_indices = set()

    # First pass: resolve valid position names
    for char_id in characters:
        pos_name = char_positions.get(char_id, "")
        pos_data = available.get(pos_name)
        if pos_data:
            resolved[char_id] = (pos_data["x"], pos_data["y"])
            # Track which available position was used
            for i, ap in enumerate(available_list):
                if ap["x"] == pos_data["x"] and ap["y"] == pos_data["y"]:
                    used_indices.add(i)
                    break

    # Second pass: assign unresolved characters to unused positions
    unresolved = [c for c in characters if c not in resolved]
    unused = [i for i in range(len(available_list)) if i not in used_indices]

    for char_id in unresolved:
        if unused:
            idx = unused.pop(0)
            pos = available_list[idx]
            resolved[char_id] = (pos["x"], pos["y"])
            used_indices.add(idx)
        elif available_list:
            # All positions taken — pick the position furthest from already-placed chars
            best_idx = 0
            best_min_dist = -1
            for i, pos in enumerate(available_list):
                min_dist = min(
                    (abs(pos["x"] - rx) for rx, ry in resolved.values()),
                    default=9999,
                )
                if min_dist > best_min_dist:
                    best_min_dist = min_dist
                    best_idx = i
            pos = available_list[best_idx]
            resolved[char_id] = (pos["x"], pos["y"])
        else:
            resolved[char_id] = (450, 1300)

    return resolved


def composite_character(frame, character_id, state, location_id, position_name):
    """Composite a character sprite onto a frame at the specified position.

    Args:
        frame: PIL Image (the current frame, 1080x1920)
        character_id: e.g., "pens"
        state: sprite state
        location_id: e.g., "diner_interior"
        position_name: e.g., "stool_1" or an (x, y) tuple

    Returns:
        The frame with the character composited.
    """
    sprite = load_sprite(character_id, state)

    # Accept pre-resolved (x, y) tuple or look up by name
    if isinstance(position_name, tuple):
        x, y = position_name
    else:
        x, y = get_character_position(location_id, position_name)

    # Center the sprite on the position point
    paste_x = x - sprite.width // 2
    paste_y = y - sprite.height

    # Clamp to frame bounds
    paste_x = max(0, min(paste_x, frame.width - sprite.width))
    paste_y = max(0, min(paste_y, frame.height - sprite.height))

    frame.paste(sprite, (paste_x, paste_y), sprite)
    return frame
