"""Process source background images for the Mootoshi video pipeline.

Takes raw Gemini-generated backgrounds from a source directory, removes
the bottom-right watermark logo, crops dark edge artifacts, resizes to
pipeline dimensions, and saves to the assets/backgrounds/ directory.

Handles both horizontal (1920x1080) and vertical (1080x1920) formats.

Usage:
    python scripts/process_background.py [--source DIR] [--output DIR]
"""

import argparse
import os
import sys
import tempfile

import numpy as np
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

# Ensure the project root is importable from both pytest and direct invocation
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Reuse the watermark removal logic from the existing script
from scripts.remove_watermarks import clean_background

# Source filename prefix → pipeline location ID
NAME_MAP = {
    "diner": "diner",
    "farmers_market": "farmers_market",
    "reows": "reows_place",
    "town_square": "town_square",
}

HORIZONTAL_SIZE = (1920, 1080)
VERTICAL_SIZE = (1080, 1920)

DEFAULT_SOURCE = os.path.join(
    os.path.expanduser("~"), "Downloads", "bl0btoshii_v2", "backgrounds_2"
)
DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(__file__), "..", "assets", "backgrounds"
)


# Rows with average brightness below this are considered "dark edge" artifacts
DARK_EDGE_THRESHOLD = 30


def crop_dark_edges(img, threshold=DARK_EDGE_THRESHOLD):
    """Crop near-black rows from the top and bottom of an image.

    Nano Banana Pro sometimes generates horizontal backgrounds with a
    strip of nearly-black pixels at the bottom edge. This function
    detects those rows and crops them off so the resize step doesn't
    bake the black void into the final output.

    Only removes edges where contiguous dark rows start at the very
    top or bottom — never touches the interior of the image.

    Args:
        img: PIL Image (RGB).
        threshold: Rows with mean brightness <= this are considered dark.

    Returns:
        PIL Image (RGB), cropped. Returns the original if no dark edges found.
    """
    arr = np.array(img)
    row_brightness = arr.mean(axis=(1, 2))
    h = arr.shape[0]

    # Scan from bottom up to find last content row
    bottom_crop = h
    for y in range(h - 1, -1, -1):
        if row_brightness[y] > threshold:
            bottom_crop = y + 1
            break

    # Scan from top down to find first content row
    top_crop = 0
    for y in range(h):
        if row_brightness[y] > threshold:
            top_crop = y
            break

    rows_removed = (h - bottom_crop) + top_crop
    if rows_removed == 0:
        return img

    cropped = img.crop((0, top_crop, img.width, bottom_crop))
    print(f"    [crop_dark_edges] Removed {rows_removed} dark rows "
          f"(top={top_crop}, bottom={h - bottom_crop})")
    return cropped


def build_output_filename(pipeline_name, orientation):
    """Build the output filename for a processed background.

    Args:
        pipeline_name: The location ID used in the pipeline (e.g., "reows_place").
        orientation: "horizontal" or "vertical".

    Returns:
        Filename string (e.g., "reows_place.png" or "reows_place_vertical.png").
    """
    if orientation == "vertical":
        return f"{pipeline_name}_vertical.png"
    return f"{pipeline_name}.png"


def process_single_background(source_path, output_path, target_size):
    """Crop dark edges and resize a single background image.

    Source images are expected to be watermark-free (cleaned externally).
    Processing steps: crop dark edge artifacts, then LANCZOS resize.

    Args:
        source_path: Path to the source PNG.
        output_path: Path to save the processed PNG.
        target_size: (width, height) tuple for the output.
    """
    img = Image.open(source_path).convert("RGB")

    # Crop dark edge artifacts (Nano Banana Pro sometimes adds near-black rows)
    img = crop_dark_edges(img)

    # Resize to pipeline dimensions with LANCZOS for smooth downscaling
    resized = img.resize(target_size, Image.LANCZOS)
    resized.save(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Process background images for the Mootoshi pipeline."
    )
    parser.add_argument(
        "--source", default=DEFAULT_SOURCE,
        help="Directory containing source background PNGs."
    )
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT,
        help="Directory to save processed backgrounds."
    )
    args = parser.parse_args()

    source_dir = os.path.abspath(args.source)
    output_dir = os.path.abspath(args.output)

    if not os.path.exists(source_dir):
        print(f"ERROR: Source directory not found: {source_dir}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(f"Source: {source_dir}")
    print(f"Output: {output_dir}")
    print("=" * 60)

    processed = 0
    for source_prefix, pipeline_name in NAME_MAP.items():
        for orientation in ("horizontal", "vertical"):
            source_filename = f"{source_prefix}_{orientation}.png"
            source_path = os.path.join(source_dir, source_filename)

            if not os.path.exists(source_path):
                print(f"  SKIP: {source_filename} not found")
                continue

            target_size = HORIZONTAL_SIZE if orientation == "horizontal" else VERTICAL_SIZE
            out_filename = build_output_filename(pipeline_name, orientation)
            out_path = os.path.join(output_dir, out_filename)

            process_single_background(source_path, out_path, target_size)

            result = Image.open(out_path)
            print(f"  {source_filename} -> {out_filename} ({result.size[0]}x{result.size[1]})")
            processed += 1

    print("=" * 60)
    print(f"Done. {processed} backgrounds processed.")


if __name__ == "__main__":
    main()
