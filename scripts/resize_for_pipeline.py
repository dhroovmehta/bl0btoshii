"""Resize all assets for the video pipeline.

Sprites: crop transparent edges → fit within 192x288 (nearest-neighbor)
Portraits: resize to 48x48 (nearest-neighbor)
Backgrounds: resize to 1080x1920 (nearest-neighbor)

Usage:
    python scripts/resize_for_pipeline.py
"""

import os
import numpy as np
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

# Target dimensions matching the pipeline's expected sprite display size
SPRITE_MAX_W = 192
SPRITE_MAX_H = 288
PORTRAIT_SIZE = 48
BG_WIDTH = 1080
BG_HEIGHT = 1920

CHARACTER_FOLDERS = ["pens", "chubs", "meows", "oinks", "quacks", "reows"]


def crop_to_content(img):
    """Crop an RGBA image to the bounding box of non-transparent pixels."""
    arr = np.array(img)
    if arr.shape[2] < 4:
        return img  # No alpha channel, nothing to crop

    alpha = arr[:, :, 3]
    rows = np.any(alpha > 0, axis=1)
    cols = np.any(alpha > 0, axis=0)

    if not rows.any() or not cols.any():
        return img  # Fully transparent — return as-is

    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    return img.crop((cmin, rmin, cmax + 1, rmax + 1))


def fit_within(img, max_w, max_h):
    """Resize an image to fit within max_w x max_h, preserving aspect ratio."""
    w, h = img.size
    scale = min(max_w / w, max_h / h)
    if scale >= 1.0:
        # Already fits — still resize to ensure consistent pixel density
        scale = min(max_w / w, max_h / h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return img.resize((new_w, new_h), Image.NEAREST)


def process_sprites():
    """Crop and resize all character sprites."""
    print("Character sprites (crop + fit within {}x{}):".format(SPRITE_MAX_W, SPRITE_MAX_H))
    for folder in CHARACTER_FOLDERS:
        folder_path = os.path.join(ASSETS_DIR, "characters", folder)
        if not os.path.exists(folder_path):
            print(f"  SKIP: {folder}/ not found")
            continue

        for filename in sorted(os.listdir(folder_path)):
            if not filename.endswith(".png"):
                continue
            path = os.path.join(folder_path, filename)
            img = Image.open(path).convert("RGBA")
            orig_size = img.size

            cropped = crop_to_content(img)
            resized = fit_within(cropped, SPRITE_MAX_W, SPRITE_MAX_H)
            resized.save(path)

            print(f"  {folder}/{filename}: {orig_size[0]}x{orig_size[1]} → "
                  f"crop {cropped.size[0]}x{cropped.size[1]} → "
                  f"resize {resized.size[0]}x{resized.size[1]}")


def process_portraits():
    """Resize all portraits to PORTRAIT_SIZE x PORTRAIT_SIZE."""
    print(f"\nPortraits (resize to {PORTRAIT_SIZE}x{PORTRAIT_SIZE}):")
    portraits_dir = os.path.join(ASSETS_DIR, "ui", "portraits")
    if not os.path.exists(portraits_dir):
        print("  SKIP: ui/portraits/ not found")
        return

    for filename in sorted(os.listdir(portraits_dir)):
        if not filename.endswith(".png"):
            continue
        path = os.path.join(portraits_dir, filename)
        img = Image.open(path).convert("RGBA")
        orig_size = img.size

        # Crop to content first, then resize to square
        cropped = crop_to_content(img)
        resized = cropped.resize((PORTRAIT_SIZE, PORTRAIT_SIZE), Image.NEAREST)
        resized.save(path)

        print(f"  {filename}: {orig_size[0]}x{orig_size[1]} → "
              f"crop {cropped.size[0]}x{cropped.size[1]} → "
              f"{PORTRAIT_SIZE}x{PORTRAIT_SIZE}")


def process_backgrounds():
    """Resize all backgrounds to BG_WIDTH x BG_HEIGHT."""
    print(f"\nBackgrounds (resize to {BG_WIDTH}x{BG_HEIGHT}):")
    bg_dir = os.path.join(ASSETS_DIR, "backgrounds")
    if not os.path.exists(bg_dir):
        print("  SKIP: backgrounds/ not found")
        return

    for filename in sorted(os.listdir(bg_dir)):
        if not filename.endswith(".png"):
            continue
        path = os.path.join(bg_dir, filename)
        img = Image.open(path).convert("RGB")
        orig_size = img.size

        if img.size != (BG_WIDTH, BG_HEIGHT):
            img = img.resize((BG_WIDTH, BG_HEIGHT), Image.NEAREST)
            img.save(path)
            print(f"  {filename}: {orig_size[0]}x{orig_size[1]} → {BG_WIDTH}x{BG_HEIGHT}")
        else:
            print(f"  {filename}: already {BG_WIDTH}x{BG_HEIGHT}")


def main():
    print(f"Assets directory: {os.path.abspath(ASSETS_DIR)}")
    print("=" * 60)
    process_sprites()
    process_portraits()
    process_backgrounds()
    print("\n" + "=" * 60)
    print("Done. All assets resized for the video pipeline.")


if __name__ == "__main__":
    main()
