"""Storyboard renderer — generates a visual grid of scene thumbnails from a script."""

import os
from PIL import Image, ImageDraw, ImageFont

from src.video_assembler.sprite_manager import load_sprite, get_character_position, resolve_scene_positions
from src.video_assembler.scene_builder import load_background

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
FONT_PATH = os.path.join(ASSETS_DIR, "ui", "fonts", "PressStart2P-Regular.ttf")

# Storyboard layout
THUMB_WIDTH = 360
THUMB_HEIGHT = 640
COLUMNS = 3
PADDING = 20
LABEL_HEIGHT = 60
BG_COLOR = (30, 30, 50)
LABEL_BG = (20, 20, 40)
TEXT_COLOR = (255, 255, 255)
DIALOGUE_COLOR = (200, 200, 255)


def render_storyboard(script, output_dir):
    """Generate a storyboard image grid from a script.

    Each cell shows:
    - Background plate (scaled down)
    - Character sprites in position
    - First line of dialogue overlaid
    - Scene number and duration label

    Args:
        script: Full episode script dict.
        output_dir: Directory to save the storyboard image.

    Returns:
        Path to the storyboard PNG.
    """
    os.makedirs(output_dir, exist_ok=True)

    scenes = script.get("scenes", [])
    if not scenes:
        return None

    # Load fonts
    try:
        label_font = ImageFont.truetype(FONT_PATH, 10)
        dialogue_font = ImageFont.truetype(FONT_PATH, 8)
    except OSError:
        label_font = ImageFont.load_default()
        dialogue_font = label_font

    # Calculate grid dimensions
    rows = (len(scenes) + COLUMNS - 1) // COLUMNS
    grid_width = COLUMNS * (THUMB_WIDTH + PADDING) + PADDING
    grid_height = rows * (THUMB_HEIGHT + LABEL_HEIGHT + PADDING) + PADDING + 80  # +80 for title

    # Create storyboard canvas
    storyboard = Image.new("RGB", (grid_width, grid_height), BG_COLOR)
    draw = ImageDraw.Draw(storyboard)

    # Draw title
    metadata = script.get("metadata", {})
    episode_id = metadata.get("episode_id", "?")
    title = metadata.get("title", "Untitled")
    title_text = f"{episode_id}: {title}"
    draw.text((PADDING, PADDING), title_text, fill=TEXT_COLOR, font=label_font)

    # Draw each scene thumbnail
    for i, scene in enumerate(scenes):
        col = i % COLUMNS
        row = i // COLUMNS

        x = PADDING + col * (THUMB_WIDTH + PADDING)
        y = 80 + row * (THUMB_HEIGHT + LABEL_HEIGHT + PADDING)

        # Generate thumbnail
        thumb = _render_scene_thumbnail(scene, label_font, dialogue_font)
        storyboard.paste(thumb, (x, y))

        # Draw label below thumbnail
        label_y = y + THUMB_HEIGHT
        draw.rectangle(
            [x, label_y, x + THUMB_WIDTH, label_y + LABEL_HEIGHT],
            fill=LABEL_BG,
        )

        scene_num = scene.get("scene_number", i + 1)
        duration = scene.get("duration_seconds", 0)
        desc = scene.get("description", "")[:40]
        label = f"Scene {scene_num} ({duration}s)"

        draw.text((x + 5, label_y + 5), label, fill=TEXT_COLOR, font=label_font)
        draw.text((x + 5, label_y + 25), desc, fill=DIALOGUE_COLOR, font=dialogue_font)

    # Save storyboard
    output_path = os.path.join(output_dir, "storyboard.png")
    storyboard.save(output_path)
    return output_path


def _render_scene_thumbnail(scene, label_font, dialogue_font):
    """Render a single scene as a thumbnail image.

    Args:
        scene: Scene dict from script.
        label_font: PIL font for labels.
        dialogue_font: PIL font for dialogue.

    Returns:
        PIL Image (THUMB_WIDTH x THUMB_HEIGHT).
    """
    bg_id = scene.get("background", "diner_interior")
    characters = scene.get("characters_present", [])
    positions = scene.get("character_positions", {})
    dialogue = scene.get("dialogue", [])

    # Load and scale background
    bg = load_background(bg_id)
    thumb = bg.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.NEAREST).convert("RGBA")

    # Resolve positions using the same anti-overlap logic as the video renderer
    resolved = resolve_scene_positions(bg_id, characters, positions)

    # Composite characters (scaled down proportionally)
    scale_factor = THUMB_WIDTH / 1080  # ~0.33x
    for char_id in characters:
        sprite = load_sprite(char_id, "idle")

        # Scale sprite for thumbnail
        s_w = max(1, int(sprite.width * scale_factor))
        s_h = max(1, int(sprite.height * scale_factor))
        small_sprite = sprite.resize((s_w, s_h), Image.NEAREST)

        # Get resolved position and scale it
        px, py = resolved.get(char_id, get_character_position(bg_id, positions.get(char_id, "")))
        tx = int(px * scale_factor) - s_w // 2
        ty = int(py * scale_factor) - s_h

        # Clamp
        tx = max(0, min(tx, THUMB_WIDTH - s_w))
        ty = max(0, min(ty, THUMB_HEIGHT - s_h))

        thumb.paste(small_sprite, (tx, ty), small_sprite)

    # Overlay first line of dialogue at bottom
    if dialogue:
        first_line = dialogue[0]
        char_name = first_line.get("character", "?").upper()
        text = first_line.get("text", "")[:30]

        draw = ImageDraw.Draw(thumb)
        # Semi-transparent box at bottom
        box_y = THUMB_HEIGHT - 50
        draw.rectangle(
            [0, box_y, THUMB_WIDTH, THUMB_HEIGHT],
            fill=(26, 26, 58, 200),
        )
        draw.text((5, box_y + 5), f"{char_name}:", fill=(150, 200, 255), font=dialogue_font)
        draw.text((5, box_y + 20), text, fill=TEXT_COLOR, font=dialogue_font)

    return thumb.convert("RGB")
