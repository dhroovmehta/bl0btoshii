"""Copy cleaned sprites from blobtoshi_sprites/ to the project assets/ directory.

Handles the naming difference: blobtoshi_sprites/backgrounds/diner.png → assets/backgrounds/diner_interior.png

Usage:
    python scripts/copy_to_assets.py
"""

import os
import shutil

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
SPRITES_DIR = os.path.join(PROJECT_ROOT, "blobtoshi_sprites")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

CHARACTER_FOLDERS = ["pens", "chubs", "meows", "oinks", "quacks", "reows"]

# Background name mapping (source → destination)
BG_NAME_MAP = {
    "diner.png": "diner_interior.png",
    "beach.png": "beach.png",
    "forest.png": "forest.png",
    "town_square.png": "town_square.png",
    "chubs_office.png": "chubs_office.png",
    "reows_place.png": "reows_place.png",
}


def main():
    sprites_dir = os.path.abspath(SPRITES_DIR)
    assets_dir = os.path.abspath(ASSETS_DIR)

    print(f"Source: {sprites_dir}")
    print(f"Destination: {assets_dir}")
    print("=" * 60)

    copied = 0

    # Copy character sprites
    for folder in CHARACTER_FOLDERS:
        src_folder = os.path.join(sprites_dir, folder)
        dst_folder = os.path.join(assets_dir, "characters", folder)
        os.makedirs(dst_folder, exist_ok=True)

        if not os.path.exists(src_folder):
            print(f"  SKIP: {folder}/ not found")
            continue

        for filename in sorted(os.listdir(src_folder)):
            if not filename.endswith(".png"):
                continue
            src = os.path.join(src_folder, filename)
            dst = os.path.join(dst_folder, filename)
            shutil.copy2(src, dst)
            copied += 1
            print(f"  characters/{folder}/{filename}")

    # Copy portraits
    src_portraits = os.path.join(sprites_dir, "portraits")
    dst_portraits = os.path.join(assets_dir, "ui", "portraits")
    os.makedirs(dst_portraits, exist_ok=True)

    if os.path.exists(src_portraits):
        for filename in sorted(os.listdir(src_portraits)):
            if not filename.endswith(".png"):
                continue
            src = os.path.join(src_portraits, filename)
            dst = os.path.join(dst_portraits, filename)
            shutil.copy2(src, dst)
            copied += 1
            print(f"  ui/portraits/{filename}")

    # Copy backgrounds (with renaming)
    src_bg = os.path.join(sprites_dir, "backgrounds")
    dst_bg = os.path.join(assets_dir, "backgrounds")
    os.makedirs(dst_bg, exist_ok=True)

    if os.path.exists(src_bg):
        for src_name, dst_name in sorted(BG_NAME_MAP.items()):
            src = os.path.join(src_bg, src_name)
            dst = os.path.join(dst_bg, dst_name)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                copied += 1
                label = f"  backgrounds/{dst_name}"
                if src_name != dst_name:
                    label += f" (from {src_name})"
                print(label)
            else:
                print(f"  MISSING: backgrounds/{src_name}")

    print("=" * 60)
    print(f"Copied {copied} files to assets/")


if __name__ == "__main__":
    main()
