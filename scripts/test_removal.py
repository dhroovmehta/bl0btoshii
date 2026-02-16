"""Test watermark removal on copies — DO NOT touch originals.

Reads from blobtoshi_sprites_BACKUP/, writes cleaned copies to blobtoshi_sprites_TEST_OUTPUT/.
Reports per-image stats: background removed %, watermark corner cleared %, and any issues.
"""

import os
import sys
import shutil
import numpy as np
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

# Add parent dir so we can import the removal functions
sys.path.insert(0, os.path.dirname(__file__))
from remove_watermarks import clean_sprite, clean_background

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "blobtoshi_sprites_BACKUP")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "blobtoshi_sprites_TEST_OUTPUT")

CHARACTER_FOLDERS = ["pens", "chubs", "meows", "oinks", "quacks", "reows"]


def test_removal():
    backup_dir = os.path.abspath(BACKUP_DIR)
    output_dir = os.path.abspath(OUTPUT_DIR)

    if not os.path.exists(backup_dir):
        print(f"ERROR: Backup directory not found: {backup_dir}")
        sys.exit(1)

    print(f"Source (backups): {backup_dir}")
    print(f"Output (test):    {output_dir}")
    print("=" * 70)

    results = []
    errors = []

    # Process character sprites
    for folder in CHARACTER_FOLDERS:
        src_folder = os.path.join(backup_dir, folder)
        dst_folder = os.path.join(output_dir, folder)
        os.makedirs(dst_folder, exist_ok=True)

        if not os.path.exists(src_folder):
            print(f"  SKIP: {folder}/ not found in backup")
            continue

        for filename in sorted(os.listdir(src_folder)):
            if not filename.endswith(".png"):
                continue
            src_path = os.path.join(src_folder, filename)
            dst_path = os.path.join(dst_folder, filename)
            label = f"{folder}/{filename}"
            try:
                bg_pct, wm_pct = clean_sprite(src_path, dst_path)
                status = "OK" if wm_pct > 80 else "CHECK"
                results.append((label, bg_pct, wm_pct, status))
                print(f"  {label}: bg_removed={bg_pct:.1f}%, wm_cleared={wm_pct:.1f}% [{status}]")
            except Exception as e:
                errors.append((label, str(e)))
                print(f"  {label}: ERROR — {e}")

    # Process portraits
    src_portraits = os.path.join(backup_dir, "portraits")
    dst_portraits = os.path.join(output_dir, "portraits")
    os.makedirs(dst_portraits, exist_ok=True)

    if os.path.exists(src_portraits):
        for filename in sorted(os.listdir(src_portraits)):
            if not filename.endswith(".png"):
                continue
            src_path = os.path.join(src_portraits, filename)
            dst_path = os.path.join(dst_portraits, filename)
            label = f"portraits/{filename}"
            try:
                bg_pct, wm_pct = clean_sprite(src_path, dst_path)
                status = "OK" if wm_pct > 80 else "CHECK"
                results.append((label, bg_pct, wm_pct, status))
                print(f"  {label}: bg_removed={bg_pct:.1f}%, wm_cleared={wm_pct:.1f}% [{status}]")
            except Exception as e:
                errors.append((label, str(e)))
                print(f"  {label}: ERROR — {e}")

    # Process backgrounds
    src_bg = os.path.join(backup_dir, "backgrounds")
    dst_bg = os.path.join(output_dir, "backgrounds")
    os.makedirs(dst_bg, exist_ok=True)

    if os.path.exists(src_bg):
        for filename in sorted(os.listdir(src_bg)):
            if not filename.endswith(".png"):
                continue
            src_path = os.path.join(src_bg, filename)
            dst_path = os.path.join(dst_bg, filename)
            label = f"backgrounds/{filename}"
            try:
                clean_background(src_path, dst_path)
                results.append((label, None, None, "PATCHED"))
                print(f"  {label}: corner patched [PATCHED]")
            except Exception as e:
                errors.append((label, str(e)))
                print(f"  {label}: ERROR — {e}")

    # Summary
    print()
    print("=" * 70)
    print("REMOVAL TEST SUMMARY")
    print("=" * 70)

    ok_count = sum(1 for r in results if r[3] in ("OK", "PATCHED"))
    check_count = sum(1 for r in results if r[3] == "CHECK")
    error_count = len(errors)
    total = len(results) + error_count

    print(f"Total processed: {total}")
    print(f"  OK/PATCHED:    {ok_count}")
    print(f"  CHECK:         {check_count}")
    print(f"  ERRORS:        {error_count}")
    print()

    if check_count > 0:
        print("Images needing review (watermark <80% cleared):")
        for label, bg_pct, wm_pct, status in results:
            if status == "CHECK":
                print(f"  - {label}: wm_cleared={wm_pct:.1f}%")
        print()

    if error_count > 0:
        print("Errors:")
        for label, err in errors:
            print(f"  - {label}: {err}")
        print()

    # Verify output files exist and have reasonable sizes
    print("Output file verification:")
    missing = 0
    tiny = 0
    for label, _, _, _ in results:
        out_path = os.path.join(output_dir, label)
        if not os.path.exists(out_path):
            print(f"  MISSING: {label}")
            missing += 1
        else:
            size = os.path.getsize(out_path)
            if size < 1000:
                print(f"  TINY ({size}B): {label}")
                tiny += 1

    if missing == 0 and tiny == 0:
        print(f"  All {len(results)} output files exist with valid sizes.")

    print()
    print(f"Test complete. Output files in: {output_dir}")


if __name__ == "__main__":
    test_removal()
