"""Post-processing pipeline for character sprites with transparent backgrounds.

Background removal is done manually in Photopea before running this script.
This handles the remaining post-processing:
  1. Cleans up alpha artifacts (snap low-alpha to fully transparent)
  2. Crops to content (trim transparent padding)
  3. Resizes to pipeline-ready dimensions (nearest-neighbor for crisp pixels)
  4. Saves to the correct assets folder

Usage:
    python scripts/process_sprite.py <image_path> --character <name> --pose <pose>

Examples:
    python scripts/process_sprite.py ~/Downloads/quacks_idle.png --character quacks --pose idle
    python scripts/process_sprite.py ~/Downloads/pens_talking.png --character pens --pose talking

The processed sprite lands in assets/characters/<name>/<pose>.png ready for the pipeline.
"""

import argparse
import os
import sys
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

# Characters at the same height tier should end up at roughly the same pixel height.
# The pipeline composites sprites in a 1920x1080 frame, so these are display sizes.
#   Short tier  (Pens, Quacks, Oinks): fit within 240 x 320
#   Medium tier (Chubs, Meows):        fit within 240 x 370
#   Tall tier   (Reows):               fit within 260 x 420
HEIGHT_TIERS = {
    "pens":   (240, 320),
    "quacks": (240, 320),
    "oinks":  (240, 320),
    "chubs":  (240, 370),
    "meows":  (240, 370),
    "reows":  (260, 420),
}

VALID_CHARACTERS = list(HEIGHT_TIERS.keys())

# Alpha threshold: pixels with alpha below this become fully transparent.
ALPHA_THRESHOLD = 20


def clean_transparency(img):
    """Remove semi-transparent artifacts by thresholding the alpha channel.

    Pixels with alpha below ALPHA_THRESHOLD become fully transparent.
    """
    if img.mode != "RGBA":
        return img

    r, g, b, a = img.split()
    a = a.point(lambda val: 0 if val < ALPHA_THRESHOLD else val)
    return Image.merge("RGBA", (r, g, b, a))


def crop_to_content(img):
    """Crop an RGBA image to the bounding box of non-transparent pixels.

    Returns the original image unchanged if no opaque content is found.
    """
    if img.mode != "RGBA":
        return img

    w, h = img.size
    pixels = img.load()

    top, bottom, left, right = h, -1, w, -1

    for y in range(h):
        for x in range(w):
            if pixels[x, y][3] > ALPHA_THRESHOLD:
                if y < top:
                    top = y
                if y > bottom:
                    bottom = y
                if x < left:
                    left = x
                if x > right:
                    right = x

    # No opaque content found
    if bottom == -1:
        return img

    return img.crop((left, top, right + 1, bottom + 1))


def fit_within(img, max_w, max_h):
    """Resize to fit within max_w x max_h, preserving aspect ratio.

    Uses nearest-neighbor interpolation to keep pixel edges crisp.
    """
    w, h = img.size
    scale = min(max_w / w, max_h / h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return img.resize((new_w, new_h), Image.NEAREST)


def process_sprite(image_path, character, pose):
    """Full processing pipeline for a single sprite.

    Expects an image with transparent background (done in Photopea).
    Cleans alpha, crops padding, resizes, and saves.

    Returns:
        Path to the saved output file.
    """
    if character not in VALID_CHARACTERS:
        print(f"ERROR: Unknown character '{character}'. Valid: {', '.join(VALID_CHARACTERS)}")
        sys.exit(1)

    if not os.path.exists(image_path):
        print(f"ERROR: File not found: {image_path}")
        sys.exit(1)

    img = Image.open(image_path).convert("RGBA")
    original_size = img.size
    print(f"Input: {image_path} ({original_size[0]}x{original_size[1]})")

    # Step 1: Clean transparency artifacts
    img = clean_transparency(img)
    print(f"  [1/4] Cleaned transparency (threshold={ALPHA_THRESHOLD})")

    # Step 2: Crop to content
    img = crop_to_content(img)
    print(f"  [2/4] Cropped to content: {img.size[0]}x{img.size[1]}")

    # Step 3: Resize to pipeline dimensions
    max_w, max_h = HEIGHT_TIERS[character]
    img = fit_within(img, max_w, max_h)
    print(f"  [3/4] Resized to {img.size[0]}x{img.size[1]} (tier: {max_w}x{max_h})")

    # Step 4: Save to the correct assets folder
    output_dir = os.path.join(ASSETS_DIR, "characters", character)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{pose}.png")

    # Back up existing file if present
    if os.path.exists(output_path):
        backup_path = output_path.replace(".png", "_old.png")
        os.rename(output_path, backup_path)
        print(f"  Backed up existing sprite to {os.path.basename(backup_path)}")

    img.save(output_path, "PNG")
    print(f"\nSaved: {output_path}")
    print(f"  Character: {character}")
    print(f"  Pose: {pose}")
    print(f"  Final size: {img.size[0]}x{img.size[1]}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Process a sprite for the Mootoshi pipeline (background must already be removed).",
        epilog="Example: python scripts/process_sprite.py ~/Downloads/quacks_idle.png --character quacks --pose idle",
    )
    parser.add_argument("image_path", help="Path to the sprite with transparent background")
    parser.add_argument("--character", "-c", required=True, choices=VALID_CHARACTERS,
                        help="Character name")
    parser.add_argument("--pose", "-p", required=True,
                        help="Pose name (e.g., idle, talking)")
    args = parser.parse_args()

    process_sprite(args.image_path, args.character, args.pose)


if __name__ == "__main__":
    main()
