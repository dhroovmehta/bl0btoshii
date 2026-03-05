"""Generate positioning test images for all locations and orientations.

Composites two characters (pens + oinks) at primary positions with facing,
draws position markers and facing labels, saves to output/positioning_test/.

Usage:
    python scripts/generate_positioning_test.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image, ImageDraw, ImageFont
from src.video_assembler.sprite_manager import (
    load_sprite,
    resolve_scene_positions,
    get_default_facing,
)
from src.video_assembler.scene_builder import load_background_layers
from src.video_assembler.render_config import HORIZONTAL, VERTICAL

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "positioning_test")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
FONT_PATH = os.path.join(ASSETS_DIR, "ui", "fonts", "PressStart2P-Regular.ttf")

LOCATIONS = ["diner", "farmers_market", "town_square", "reows_place"]
# First two characters assigned get the primary conversation pair positions
TEST_CHARACTERS = ["pens", "oinks"]


def _load_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def _draw_marker(draw, x, y, color, label, font):
    """Draw a crosshair marker at (x, y) with a label."""
    arm = 12
    draw.line([(x - arm, y), (x + arm, y)], fill=color, width=2)
    draw.line([(x, y - arm), (x, y + arm)], fill=color, width=2)
    draw.text((x + arm + 4, y - 8), label, fill=color, font=font)


def generate_test_image(location_id, config):
    """Generate a positioning test image for one location + orientation.

    Args:
        location_id: e.g., "diner"
        config: RenderConfig (HORIZONTAL or VERTICAL)

    Returns:
        Path to saved PNG.
    """
    fw, fh = config.width, config.height

    # Load background
    layers = load_background_layers(location_id, target_width=fw, target_height=fh)
    base = Image.new("RGBA", (fw, fh), (0, 0, 0, 255))
    for layer in layers:
        base = Image.alpha_composite(base, layer)

    # Resolve positions for our two test characters
    char_positions = {}  # empty — let resolve_scene_positions auto-assign
    resolved = resolve_scene_positions(
        location_id, TEST_CHARACTERS, char_positions,
        frame_width=fw, frame_height=fh,
    )

    # Composite characters with facing
    from PIL import ImageOps
    for char_id in TEST_CHARACTERS:
        sprite = load_sprite(char_id, "idle")
        pos = resolved.get(char_id, (fw // 2, int(fh * 0.8), "right"))
        x, y = pos[0], pos[1]
        facing = pos[2] if len(pos) > 2 else "right"

        # Mirror when desired facing differs from sprite's natural orientation
        default_facing = get_default_facing(char_id)
        if facing != default_facing:
            sprite = ImageOps.mirror(sprite)

        paste_x = x - sprite.width // 2
        paste_y = y - sprite.height
        paste_x = max(0, min(paste_x, fw - sprite.width))
        paste_y = max(0, min(paste_y, fh - sprite.height))

        base.paste(sprite, (paste_x, paste_y), sprite)

    # Clean output — no debug overlays
    orientation = config.label

    # Save
    out = base.convert("RGB")
    filename = f"{location_id}_{orientation}.png"
    path = os.path.join(OUTPUT_DIR, filename)
    out.save(path)
    return path


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Generating positioning test images...")
    print(f"Output: {os.path.abspath(OUTPUT_DIR)}\n")

    for loc in LOCATIONS:
        for config in [HORIZONTAL, VERTICAL]:
            path = generate_test_image(loc, config)
            print(f"  {os.path.basename(path)}")

    print(f"\nDone — {len(LOCATIONS) * 2} images saved.")


if __name__ == "__main__":
    main()
