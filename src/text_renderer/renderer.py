"""NES-style text box renderer — generates frame-by-frame typewriter animation."""

import json
import os
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
FONT_PATH = os.path.join(ASSETS_DIR, "ui", "fonts", "PressStart2P-Regular.ttf")

# Text box visual spec from PRD
BOX_WIDTH = 900
BOX_HEIGHT = 200
BOX_BG_COLOR = (26, 26, 58, 216)  # #1A1A3A at ~85% opacity
BOX_BORDER_COLOR = (255, 255, 255, 255)
BOX_BORDER_WIDTH = 2
TEXT_COLOR = (255, 255, 255)
FONT_SIZE = 16
NAME_FONT_SIZE = 14
PORTRAIT_SIZE = 48
TEXT_PADDING = 12
NAME_PADDING_TOP = 12
TEXT_AREA_TOP = 38


def _load_character_data():
    with open(os.path.join(DATA_DIR, "characters.json"), "r") as f:
        return json.load(f)["characters"]


def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def render_dialogue_frames(
    character_id,
    text,
    output_dir,
    frame_rate=30,
    chars_per_second=12,
    include_portrait=True,
):
    """Render frame-by-frame typewriter animation for a dialogue line.

    Args:
        character_id: Character ID (e.g., "pens")
        text: The dialogue text
        output_dir: Directory to save frame images
        frame_rate: Video frame rate
        chars_per_second: Typewriter speed
        include_portrait: Whether to include character portrait

    Returns:
        List of frame image paths, plus the total number of frames.
    """
    os.makedirs(output_dir, exist_ok=True)

    chars_data = _load_character_data()
    char = chars_data.get(character_id, {})
    name = char.get("nickname", character_id.capitalize())
    name_color = _hex_to_rgb(char.get("name_color", "#FFFFFF"))

    # Load font
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        name_font = ImageFont.truetype(FONT_PATH, NAME_FONT_SIZE)
    except OSError:
        font = ImageFont.load_default()
        name_font = font

    # Load portrait if needed
    portrait = None
    if include_portrait:
        portrait_path = os.path.join(ASSETS_DIR, "ui", "portraits", f"{character_id}_portrait.png")
        if os.path.exists(portrait_path):
            portrait = Image.open(portrait_path).resize(
                (PORTRAIT_SIZE, PORTRAIT_SIZE), Image.NEAREST
            )

    # Calculate text area
    text_x_start = TEXT_PADDING
    if portrait:
        text_x_start = PORTRAIT_SIZE + TEXT_PADDING * 2
    text_area_width = BOX_WIDTH - text_x_start - TEXT_PADDING

    # Word wrap the text
    wrapped_lines = _word_wrap(text, font, text_area_width)

    # Calculate frames needed for typewriter effect
    # Use float division to avoid integer rounding bug (30//20=1 → 30cps instead of 20)
    total_chars = sum(len(line) for line in wrapped_lines)
    frames_per_char = frame_rate / chars_per_second  # float: e.g. 30/12 = 2.5
    typewriter_frames = int(total_chars * frames_per_char)
    # Hold the full text for 2 seconds after typewriter completes so viewer can read it
    hold_frames = frame_rate * 2
    total_frames = typewriter_frames + hold_frames

    frame_paths = []

    for frame_num in range(total_frames):
        # How many characters to show this frame
        if frame_num < typewriter_frames:
            chars_shown = min(total_chars, int(frame_num / frames_per_char) + 1)
        else:
            chars_shown = total_chars

        # Create the text box frame
        box = Image.new("RGBA", (BOX_WIDTH, BOX_HEIGHT), BOX_BG_COLOR)
        draw = ImageDraw.Draw(box)

        # Draw border
        draw.rectangle(
            [0, 0, BOX_WIDTH - 1, BOX_HEIGHT - 1],
            outline=BOX_BORDER_COLOR, width=BOX_BORDER_WIDTH
        )

        # Draw portrait
        if portrait:
            box.paste(portrait, (TEXT_PADDING, TEXT_PADDING), portrait)

        # Draw character name
        draw.text(
            (text_x_start, NAME_PADDING_TOP),
            name, fill=name_color, font=name_font
        )

        # Draw typewriter text
        chars_remaining = chars_shown
        y = TEXT_AREA_TOP
        for line in wrapped_lines:
            if chars_remaining <= 0:
                break
            visible = line[:chars_remaining]
            draw.text((text_x_start, y), visible, fill=TEXT_COLOR, font=font)
            chars_remaining -= len(line)
            y += FONT_SIZE + 6

        # Save frame
        frame_path = os.path.join(output_dir, f"frame_{frame_num:05d}.png")
        box.save(frame_path)
        frame_paths.append(frame_path)

    return frame_paths


def _word_wrap(text, font, max_width):
    """Wrap text to fit within max_width pixels."""
    words = text.split(" ")
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines
