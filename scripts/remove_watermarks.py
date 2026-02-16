"""Remove Gemini watermarks and convert fake checkerboard to real transparency.

Processes all sprite, portrait, and background images in blobtoshi_sprites/.

For sprites and portraits:
  - Converts baked-in grey checkerboard to actual alpha transparency
  - This automatically removes the Gemini sparkle watermark (it sits on the checkerboard)
  - Aggressive corner cleanup catches any watermark remnants

For backgrounds:
  - Crops the bottom-right corner and fills with nearby pixels to remove watermark

Usage:
    python scripts/remove_watermarks.py
"""

import os
import sys
import numpy as np
from PIL import Image, ImageFile
from scipy import ndimage

ImageFile.LOAD_TRUNCATED_IMAGES = True

SPRITES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "blobtoshi_sprites"
)


def _find_background(bg_mask, h, w, use_edge_barriers=False, bright=None):
    """Find border-connected background regions using dilation + connected components.

    If use_edge_barriers=True, dilation respects strong edges (character outlines)
    to prevent grey character bodies from being connected to the background.
    """
    struct = np.ones((7, 7))

    if use_edge_barriers and bright is not None:
        # Detect strong edges to use as dilation barriers
        edge_x = ndimage.sobel(bright, axis=0)
        edge_y = ndimage.sobel(bright, axis=1)
        edge_mag = np.sqrt(edge_x**2 + edge_y**2)
        edge_barriers = edge_mag > 60

        bg_dilated = bg_mask.copy()
        for _ in range(3):
            bg_dilated = ndimage.binary_dilation(bg_dilated, structure=struct, iterations=1)
            bg_dilated &= ~edge_barriers
    else:
        bg_dilated = ndimage.binary_dilation(bg_mask, structure=struct, iterations=3)

    labeled, _ = ndimage.label(bg_dilated)
    border_labels = set()
    border_labels.update(labeled[0, :].tolist())
    border_labels.update(labeled[h - 1, :].tolist())
    border_labels.update(labeled[:, 0].tolist())
    border_labels.update(labeled[:, w - 1].tolist())
    border_labels.discard(0)

    border_regions = np.isin(labeled, list(border_labels))
    return border_regions & bg_mask


def clean_sprite(input_path, output_path):
    """Remove fake checkerboard background and watermark from a sprite/portrait image.

    Uses a two-pass approach:
    1. First try standard dilation (works for most images)
    2. If the character gets erased (center is mostly transparent), retry with
       edge-aware dilation that respects character outlines

    Steps:
    1. Auto-detect background color from image corners
    2. Create mask of low-saturation grey pixels (the fake checkerboard)
    3. Dilate mask to bridge alternating checkerboard squares
    4. Keep only border-connected regions (avoids removing grey pixels inside character)
    5. If character was erased, retry with edge-aware dilation
    6. Set background pixels to transparent (alpha=0)
    7. Aggressive cleanup of bottom-right corner for watermark remnants
    """
    img = Image.open(input_path)
    arr = np.array(img)[:, :, :3].astype(float)
    h, w = arr.shape[:2]

    # Auto-detect background brightness range from 4 corners
    corners = np.concatenate([
        arr[0:20, 0:20].reshape(-1, 3),
        arr[0:20, w - 20:w].reshape(-1, 3),
        arr[h - 20:h, 0:20].reshape(-1, 3),
        arr[h - 20:h, w - 20:w].reshape(-1, 3),
    ])
    bg_bright = np.mean(corners, axis=1)
    bg_bright_min = max(bg_bright.min() - 25, 0)
    bg_bright_max = bg_bright.max() + 25

    # Detect grey background pixels
    sat = np.max(arr, axis=2) - np.min(arr, axis=2)
    bright = np.mean(arr, axis=2)
    bg_mask = (sat < 25) & (bright >= bg_bright_min) & (bright <= bg_bright_max)

    # Pass 1: Standard dilation (no edge barriers) — works for most images
    final_bg = _find_background(bg_mask, h, w, use_edge_barriers=False)

    # Check if the character was erased: if the center region is almost entirely
    # flagged as background, the character was likely wiped out (grey body problem)
    center_slice = final_bg[h // 4:3 * h // 4, w // 4:3 * w // 4]
    center_bg_pct = np.sum(center_slice) / center_slice.size * 100

    if center_bg_pct > 95:
        # Character likely erased — retry with edge-aware dilation
        final_bg = _find_background(bg_mask, h, w, use_edge_barriers=True, bright=bright)

    # Apply transparency
    original = np.array(img)
    if original.shape[2] == 3:
        alpha = np.full((h, w), 255, dtype=np.uint8)
        original = np.concatenate([original, alpha[:, :, np.newaxis]], axis=2)
    original[final_bg, 3] = 0

    # Aggressive corner cleanup for watermark remnants
    wm_h = max(int(h * 0.06), 80)
    wm_w = max(int(w * 0.06), 80)
    corner_sat = sat[h - wm_h:h, w - wm_w:w]
    corner_rgb = arr[h - wm_h:h, w - wm_w:w]

    # Detect watermark pixels in corner:
    # 1. Low saturation grey (sparkle body and checkerboard)
    # 2. Bright red pixels (sparkle border, RGB ~255/38/0)
    is_grey = corner_sat < 40
    is_red = (
        (corner_rgb[:, :, 0] > 200) &
        (corner_rgb[:, :, 1] < 80) &
        (corner_rgb[:, :, 2] < 80)
    )
    corner_watermark = is_grey | is_red
    original[h - wm_h:h, w - wm_w:w][corner_watermark] = [0, 0, 0, 0]

    result = Image.fromarray(original, "RGBA")
    result.save(output_path)

    # Return stats
    total_transparent = np.sum(original[:, :, 3] == 0)
    corner_alpha = original[h - 80:h, w - 80:w, 3]
    wm_removed_pct = np.sum(corner_alpha == 0) / corner_alpha.size * 100
    return total_transparent / (h * w) * 100, wm_removed_pct


def clean_background(input_path, output_path):
    """Remove watermark from a background image by patching the corner.

    Since backgrounds have no transparency, we can't just clear pixels.
    Instead, we copy adjacent content over the watermark area from directly
    above. Uses a generous patch size to fully cover the Gemini sparkle.
    """
    img = Image.open(input_path)
    arr = np.array(img)
    h, w = arr.shape[:2]

    # Generous patch size to fully cover the Gemini sparkle watermark
    patch_h = max(int(h * 0.10), 120)
    patch_w = max(int(w * 0.10), 120)

    # Copy the strip from directly above the watermark area
    source_strip = arr[h - 2 * patch_h:h - patch_h, w - patch_w:w].copy()
    arr[h - patch_h:h, w - patch_w:w] = source_strip

    result = Image.fromarray(arr)
    result.save(output_path)
    return True


def main():
    sprites_dir = os.path.abspath(SPRITES_DIR)

    if not os.path.exists(sprites_dir):
        print(f"ERROR: Directory not found: {sprites_dir}")
        sys.exit(1)

    print(f"Processing images in: {sprites_dir}")
    print("=" * 60)

    character_folders = ["pens", "chubs", "meows", "oinks", "quacks", "reows"]
    ok_count = 0
    issue_count = 0
    total = 0

    # Process character sprites
    for folder in character_folders:
        folder_path = os.path.join(sprites_dir, folder)
        if not os.path.exists(folder_path):
            print(f"  SKIP: {folder}/ not found")
            continue

        for filename in sorted(os.listdir(folder_path)):
            if not filename.endswith(".png"):
                continue
            total += 1
            input_path = os.path.join(folder_path, filename)
            bg_pct, wm_pct = clean_sprite(input_path, input_path)
            status = "OK" if wm_pct > 80 else "CHECK"
            if wm_pct > 80:
                ok_count += 1
            else:
                issue_count += 1
            print(f"  {folder}/{filename}: bg={bg_pct:.0f}% removed, watermark={wm_pct:.0f}% cleared [{status}]")

    # Process portraits
    portraits_dir = os.path.join(sprites_dir, "portraits")
    if os.path.exists(portraits_dir):
        for filename in sorted(os.listdir(portraits_dir)):
            if not filename.endswith(".png"):
                continue
            total += 1
            input_path = os.path.join(portraits_dir, filename)
            bg_pct, wm_pct = clean_sprite(input_path, input_path)
            status = "OK" if wm_pct > 80 else "CHECK"
            if wm_pct > 80:
                ok_count += 1
            else:
                issue_count += 1
            print(f"  portraits/{filename}: bg={bg_pct:.0f}% removed, watermark={wm_pct:.0f}% cleared [{status}]")

    # Process backgrounds
    bg_dir = os.path.join(sprites_dir, "backgrounds")
    if os.path.exists(bg_dir):
        for filename in sorted(os.listdir(bg_dir)):
            if not filename.endswith(".png"):
                continue
            total += 1
            input_path = os.path.join(bg_dir, filename)
            clean_background(input_path, input_path)
            ok_count += 1
            print(f"  backgrounds/{filename}: corner patched [OK]")

    print("=" * 60)
    print(f"Done. {ok_count} OK, {issue_count} need review, {total} total processed.")

    if issue_count > 0:
        print(f"\nNote: {issue_count} image(s) may have watermark remnants where")
        print("the watermark overlapped character art. These will be invisible")
        print("after downscaling for the video pipeline.")


if __name__ == "__main__":
    main()
