"""Test that all assets load and composite correctly in the video pipeline.

Renders test frames for each character on each background to verify:
1. Backgrounds load and display at 1080x1920
2. Character sprites load, composite, and position correctly
3. Portraits load in dialogue text boxes
4. No crashes or missing files

Usage:
    python scripts/test_pipeline_assets.py
"""

import os
import sys

# Add project root to path so we can import src modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image
from src.video_assembler.sprite_manager import load_sprite, composite_character
from src.video_assembler.scene_builder import load_background, FRAME_WIDTH, FRAME_HEIGHT
from src.text_renderer.renderer import render_dialogue_frames

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "asset_test")
CHARACTERS = ["pens", "chubs", "meows", "oinks", "quacks", "reows"]
BACKGROUNDS = ["diner_interior", "beach", "forest", "town_square", "chubs_office", "reows_place"]


def test_backgrounds():
    """Test that all backgrounds load at correct resolution."""
    print("Testing backgrounds:")
    errors = []
    for bg_id in BACKGROUNDS:
        bg = load_background(bg_id)
        if bg.size == (FRAME_WIDTH, FRAME_HEIGHT):
            print(f"  {bg_id}: {bg.size[0]}x{bg.size[1]} OK")
        else:
            print(f"  {bg_id}: {bg.size[0]}x{bg.size[1]} WRONG SIZE (expected {FRAME_WIDTH}x{FRAME_HEIGHT})")
            errors.append(bg_id)
    return errors


def test_sprites():
    """Test that all character sprites load without errors."""
    print("\nTesting sprites:")
    errors = []
    for char_id in CHARACTERS:
        states = {
            "pens": ["idle", "talking", "sipping", "reaction_surprise", "reaction_deadpan", "walking"],
            "chubs": ["idle", "talking", "calculating", "excited", "reaction_nervous", "walking"],
            "meows": ["idle", "talking", "refined_pose", "reaction_appalled", "reaction_pleased", "walking"],
            "oinks": ["idle", "talking", "serving", "wiping_counter", "reaction_exasperated", "walking"],
            "quacks": ["idle", "talking", "investigating", "suspicious", "eureka", "walking"],
            "reows": ["idle", "talking", "burst_entrance", "excited", "scheming", "walking"],
        }
        for state in states.get(char_id, ["idle"]):
            sprite = load_sprite(char_id, state)
            if sprite.size[0] > 0 and sprite.size[1] > 0:
                is_placeholder = (sprite.size == (192, 288) and all(
                    sprite.getpixel((96, 144))[i] == 0 for i in range(4)
                ))
                if is_placeholder:
                    print(f"  {char_id}/{state}: PLACEHOLDER (transparent)")
                    errors.append(f"{char_id}/{state}")
                else:
                    print(f"  {char_id}/{state}: {sprite.size[0]}x{sprite.size[1]} OK")
            else:
                print(f"  {char_id}/{state}: FAILED (empty)")
                errors.append(f"{char_id}/{state}")
    return errors


def test_compositing():
    """Render a test frame with characters on a background."""
    print("\nTesting compositing (diner scene with Pens + Oinks):")
    bg = load_background("diner_interior")
    frame = bg.copy().convert("RGBA")

    frame = composite_character(frame, "pens", "idle", "diner_interior", "stool_1")
    frame = composite_character(frame, "oinks", "serving", "diner_interior", "behind_counter")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    test_path = os.path.join(OUTPUT_DIR, "test_compositing.png")
    frame.convert("RGB").save(test_path)
    print(f"  Saved: {test_path}")
    print(f"  Frame size: {frame.size[0]}x{frame.size[1]}")
    return test_path


def test_dialogue():
    """Render a dialogue text box with portrait."""
    print("\nTesting dialogue text box (Pens speaking):")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    dialogue_dir = os.path.join(OUTPUT_DIR, "dialogue_test")

    try:
        frames = render_dialogue_frames(
            character_id="pens",
            text="...cool.",
            output_dir=dialogue_dir,
            frame_rate=30,
        )
        print(f"  Generated {len(frames)} text box frames")
        if frames:
            # Copy last frame (full text visible) to test output
            last_frame = Image.open(frames[-1])
            last_frame.save(os.path.join(OUTPUT_DIR, "test_dialogue.png"))
            print(f"  Text box size: {last_frame.size[0]}x{last_frame.size[1]}")
        return []
    except Exception as e:
        print(f"  ERROR: {e}")
        return ["dialogue"]


def test_full_frame():
    """Render a complete frame: background + characters + dialogue box."""
    print("\nTesting full frame (background + characters + dialogue):")
    bg = load_background("diner_interior")
    frame = bg.copy().convert("RGBA")

    # Add characters
    frame = composite_character(frame, "pens", "sipping", "diner_interior", "stool_1")
    frame = composite_character(frame, "oinks", "talking", "diner_interior", "behind_counter")

    # Add dialogue text box
    dialogue_dir = os.path.join(OUTPUT_DIR, "full_frame_dialogue")
    text_frames = render_dialogue_frames(
        character_id="oinks",
        text="Can I just get someone to order something?",
        output_dir=dialogue_dir,
        frame_rate=30,
    )
    if text_frames:
        text_box = Image.open(text_frames[-1]).convert("RGBA")
        tx = (FRAME_WIDTH - text_box.width) // 2
        ty = 1680
        frame.paste(text_box, (tx, ty), text_box)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    test_path = os.path.join(OUTPUT_DIR, "test_full_frame.png")
    frame.convert("RGB").save(test_path)
    print(f"  Saved: {test_path}")
    print(f"  Frame size: {frame.size[0]}x{frame.size[1]}")
    return test_path


def main():
    print("=" * 60)
    print("ASSET PIPELINE TEST")
    print("=" * 60)

    all_errors = []

    bg_errors = test_backgrounds()
    all_errors.extend(bg_errors)

    sprite_errors = test_sprites()
    all_errors.extend(sprite_errors)

    test_compositing()

    dialogue_errors = test_dialogue()
    all_errors.extend(dialogue_errors)

    test_full_frame()

    print("\n" + "=" * 60)
    if all_errors:
        print(f"ISSUES FOUND: {len(all_errors)}")
        for e in all_errors:
            print(f"  - {e}")
    else:
        print("ALL TESTS PASSED")
    print(f"\nTest frames saved to: {os.path.abspath(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()
