"""Scene builder — generates all frames for a single scene."""

import os
from PIL import Image
from src.video_assembler.sprite_manager import composite_character, load_sprite
from src.text_renderer.renderer import render_dialogue_frames

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
FRAME_WIDTH = 1080
FRAME_HEIGHT = 1920
FRAME_RATE = 30
TEXT_BOX_Y = 1680  # Position text box near bottom


def load_background(location_id):
    """Load and scale a background to 1080x1920."""
    bg_path = os.path.join(ASSETS_DIR, "backgrounds", f"{location_id}.png")
    if not os.path.exists(bg_path):
        return Image.new("RGB", (FRAME_WIDTH, FRAME_HEIGHT), (26, 26, 58))
    bg = Image.open(bg_path).convert("RGB")
    if bg.size != (FRAME_WIDTH, FRAME_HEIGHT):
        bg = bg.resize((FRAME_WIDTH, FRAME_HEIGHT), Image.NEAREST)
    return bg


def build_scene_frames(scene, output_dir, frame_offset=0):
    """Build all frames for a single scene.

    Args:
        scene: Scene dict from the script.
        output_dir: Directory to save frames.
        frame_offset: Starting frame number (for sequential numbering across scenes).

    Returns:
        (frame_paths, sfx_events, blip_events)
        - frame_paths: list of frame image paths
        - sfx_events: list of (timestamp_ms, sfx_file) for audio mixer
        - blip_events: list of (timestamp_ms, blip_file) for text blip sounds
    """
    os.makedirs(output_dir, exist_ok=True)

    background_id = scene.get("background", "diner_interior")
    duration_seconds = scene.get("duration_seconds", 8)
    characters_present = scene.get("characters_present", [])
    char_positions = scene.get("character_positions", {})
    char_animations = scene.get("character_animations", {})
    dialogue = scene.get("dialogue", [])
    sfx_triggers = scene.get("sfx_triggers", [])

    total_frames = duration_seconds * FRAME_RATE
    bg = load_background(background_id)

    frame_paths = []
    sfx_events = []
    blip_events = []

    # Pre-render dialogue text box frames
    dialogue_frame_sets = []
    for line in dialogue:
        char_id = line.get("character", "pens")
        text = line.get("text", "")
        line_dir = os.path.join(output_dir, f"textbox_{char_id}_{len(dialogue_frame_sets)}")
        text_frames = render_dialogue_frames(
            character_id=char_id,
            text=text,
            output_dir=line_dir,
            frame_rate=FRAME_RATE,
        )
        dialogue_frame_sets.append({
            "character": char_id,
            "frames": text_frames,
            "duration_ms": line.get("duration_ms", 2500),
        })

    # Calculate when each dialogue line starts
    dialogue_timeline = []
    # Spread dialogue evenly across scene duration, leaving some intro time
    intro_frames = FRAME_RATE  # 1 second intro before dialogue starts
    dialogue_start = intro_frames

    for dset in dialogue_frame_sets:
        line_frames = len(dset["frames"])
        dialogue_timeline.append({
            "start_frame": dialogue_start,
            "end_frame": dialogue_start + line_frames,
            "frames": dset["frames"],
            "character": dset["character"],
        })
        dialogue_start += line_frames

    # Collect SFX events
    scene_start_ms = (frame_offset / FRAME_RATE) * 1000
    for sfx in sfx_triggers:
        sfx_events.append((
            scene_start_ms + sfx.get("time_ms", 0),
            sfx.get("sfx", "")
        ))

    # Generate frames
    for frame_num in range(total_frames):
        # Start with background
        frame = bg.copy().convert("RGBA")

        # Composite characters
        for char_id in characters_present:
            position = char_positions.get(char_id, "center")
            animation = char_animations.get(char_id, "idle")

            # Check if this character is currently speaking — use talking state
            is_speaking = False
            for dt in dialogue_timeline:
                if dt["start_frame"] <= frame_num < dt["end_frame"] and dt["character"] == char_id:
                    is_speaking = True
                    break

            state = "talking" if is_speaking else animation
            frame = composite_character(frame, char_id, state, background_id, position)

        # Composite text box if dialogue is active
        for dt in dialogue_timeline:
            if dt["start_frame"] <= frame_num < dt["end_frame"]:
                text_frame_idx = frame_num - dt["start_frame"]
                if text_frame_idx < len(dt["frames"]):
                    text_box = Image.open(dt["frames"][text_frame_idx]).convert("RGBA")
                    # Center text box horizontally at bottom
                    tx = (FRAME_WIDTH - text_box.width) // 2
                    ty = TEXT_BOX_Y
                    frame.paste(text_box, (tx, ty), text_box)
                break  # Only show one dialogue at a time

        # Save frame as RGB (no alpha in final video)
        frame_rgb = frame.convert("RGB")
        global_frame_num = frame_offset + frame_num
        frame_path = os.path.join(output_dir, f"frame_{global_frame_num:05d}.png")
        frame_rgb.save(frame_path)
        frame_paths.append(frame_path)

    return frame_paths, sfx_events, blip_events
