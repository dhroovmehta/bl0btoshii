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
    pos = positions.get(position_name, {"x": 450, "y": 1300})
    return pos["x"], pos["y"]


def composite_character(frame, character_id, state, location_id, position_name):
    """Composite a character sprite onto a frame at the specified position.

    Args:
        frame: PIL Image (the current frame, 1080x1920)
        character_id: e.g., "pens"
        state: sprite state
        location_id: e.g., "diner_interior"
        position_name: e.g., "stool_1"

    Returns:
        The frame with the character composited.
    """
    sprite = load_sprite(character_id, state)
    x, y = get_character_position(location_id, position_name)

    # Center the sprite on the position point
    paste_x = x - sprite.width // 2
    paste_y = y - sprite.height

    # Clamp to frame bounds
    paste_x = max(0, min(paste_x, frame.width - sprite.width))
    paste_y = max(0, min(paste_y, frame.height - sprite.height))

    frame.paste(sprite, (paste_x, paste_y), sprite)
    return frame
