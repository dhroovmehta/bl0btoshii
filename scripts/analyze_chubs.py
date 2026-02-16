"""Analyze why chubs/idle.png fails while other chubs images work."""

import os
import numpy as np
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "blobtoshi_sprites_BACKUP")


def analyze_image(path, label):
    img = Image.open(path)
    arr = np.array(img)[:, :, :3].astype(float)
    h, w = arr.shape[:2]

    sat = np.max(arr, axis=2) - np.min(arr, axis=2)
    bright = np.mean(arr, axis=2)

    # Corner analysis
    corners = np.concatenate([
        arr[0:20, 0:20].reshape(-1, 3),
        arr[0:20, w - 20:w].reshape(-1, 3),
        arr[h - 20:h, 0:20].reshape(-1, 3),
        arr[h - 20:h, w - 20:w].reshape(-1, 3),
    ])
    bg_bright = np.mean(corners, axis=1)
    bg_bright_min = max(bg_bright.min() - 25, 0)
    bg_bright_max = bg_bright.max() + 25

    # Background mask
    bg_mask = (sat < 25) & (bright >= bg_bright_min) & (bright <= bg_bright_max)

    print(f"\n{'='*60}")
    print(f"{label}: {w}x{h}")
    print(f"  Corner brightness: min={bg_bright.min():.1f}, max={bg_bright.max():.1f}, mean={bg_bright.mean():.1f}")
    print(f"  Adaptive range: [{bg_bright_min:.1f}, {bg_bright_max:.1f}]")
    print(f"  bg_mask coverage: {np.sum(bg_mask)/(h*w)*100:.1f}%")

    # Show brightness histogram of grey pixels (sat < 25)
    grey_mask = sat < 25
    grey_bright = bright[grey_mask]
    print(f"  Grey pixels (sat<25): {np.sum(grey_mask)/(h*w)*100:.1f}%")
    if len(grey_bright) > 0:
        hist, edges = np.histogram(grey_bright, bins=20, range=(0, 255))
        print(f"  Grey brightness histogram:")
        for i in range(len(hist)):
            if hist[i] > 0:
                bar = '#' * min(hist[i] // 100, 50)
                print(f"    [{edges[i]:6.1f}-{edges[i+1]:6.1f}]: {hist[i]:6d} {bar}")

    # Check unique grey values near checkerboard range
    in_range = grey_bright[(grey_bright >= bg_bright_min) & (grey_bright <= bg_bright_max)]
    print(f"  Grey pixels in bg range: {len(in_range)} ({len(in_range)/(h*w)*100:.1f}%)")

    # Analyze checkerboard pattern - check if grey pixels alternate
    # Sample a 20x20 patch from the corner
    corner_patch = bright[0:20, 0:20]
    corner_sat = sat[0:20, 0:20]
    if corner_sat.mean() < 15:  # Likely checkerboard
        # Check alternation: difference between adjacent pixels
        h_diff = np.abs(np.diff(corner_patch, axis=1))
        v_diff = np.abs(np.diff(corner_patch, axis=0))
        print(f"  Corner patch h-diff mean: {h_diff.mean():.1f}, v-diff mean: {v_diff.mean():.1f}")
        unique_vals = np.unique(corner_patch.astype(int))
        print(f"  Corner unique brightness values: {unique_vals[:10]}...")

    # Analyze center of image (where character should be)
    ch, cw = h // 2, w // 2
    center_patch = bright[ch-30:ch+30, cw-30:cw+30]
    center_sat_patch = sat[ch-30:ch+30, cw-30:cw+30]
    center_bg = bg_mask[ch-30:ch+30, cw-30:cw+30]
    print(f"  Center 60x60 patch:")
    print(f"    Mean brightness: {center_patch.mean():.1f}")
    print(f"    Mean saturation: {center_sat_patch.mean():.1f}")
    print(f"    bg_mask coverage: {np.sum(center_bg)/(60*60)*100:.1f}%")


images = [
    ("chubs/idle.png", "CHUBS IDLE (BROKEN)"),
    ("chubs/talking.png", "CHUBS TALKING (WORKS)"),
    ("pens/idle.png", "PENS IDLE (WORKS)"),
]

for fname, label in images:
    path = os.path.join(os.path.abspath(BACKUP_DIR), fname)
    if os.path.exists(path):
        analyze_image(path, label)
    else:
        print(f"NOT FOUND: {path}")
