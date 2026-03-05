"""Speech bubble renderer — generates frame-by-frame typewriter animation.

Renders dialogue as auto-sized speech bubbles with a triangular tail,
positioned above the speaking character. Matches Bootoshi.ai visual style:
dark bubble, white pixel-art text, Press Start 2P font.
"""

import json
import os
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
FONT_PATH = os.path.join(ASSETS_DIR, "ui", "fonts", "PressStart2P-Regular.ttf")

# Speech bubble visual constants — Bootoshi style
BUBBLE_BG_COLOR = (20, 20, 30, 240)        # Near-black at ~94% opacity
BUBBLE_BORDER_COLOR = (80, 80, 100, 255)    # Subtle light border
BUBBLE_BORDER_WIDTH = 2
TEXT_COLOR = (255, 255, 255)
FONT_SIZE = 16
BUBBLE_PADDING = 16                          # Interior padding around text
BUBBLE_MAX_WIDTH = 500                       # Default max bubble width
BUBBLE_CORNER_RADIUS = 6                     # Pixel-art rounded corners
TAIL_HEIGHT = 12                             # Triangular tail below bubble body
TAIL_WIDTH = 16                              # Base width of tail triangle
LINE_SPACING = 6                             # Vertical gap between text lines


def _load_character_data():
    with open(os.path.join(DATA_DIR, "characters.json"), "r") as f:
        return json.load(f)["characters"]


def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def render_dialogue_frames(
    character_id,
    text,
    output_dir=None,
    frame_rate=30,
    chars_per_second=12,
    include_portrait=True,
    render_config=None,
):
    """Render frame-by-frame typewriter animation as a speech bubble.

    Returns auto-sized speech bubble images with a triangular tail at the
    bottom. The scene builder positions these above the speaking character.

    Args:
        character_id: Character ID (e.g., "pens")
        text: The dialogue text
        output_dir: Deprecated — ignored (frames are in-memory)
        frame_rate: Video frame rate
        chars_per_second: Typewriter speed
        include_portrait: Deprecated — ignored (bubbles have no portraits)
        render_config: Optional RenderConfig. text_box_width controls max bubble width.

    Returns:
        List of PIL Image objects (RGBA).
    """
    # Max bubble width from render_config or default
    if render_config is not None:
        max_width = render_config.text_box_width
    else:
        max_width = BUBBLE_MAX_WIDTH

    # Load font
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except OSError:
        font = ImageFont.load_default()

    # Word wrap text within the available text area
    text_area_width = max_width - 2 * BUBBLE_PADDING
    wrapped_lines = _word_wrap(text, font, text_area_width)

    if not wrapped_lines:
        wrapped_lines = [""]

    # Calculate bubble dimensions based on actual text content
    line_widths = []
    for line in wrapped_lines:
        bbox = font.getbbox(line)
        line_widths.append(bbox[2] - bbox[0])
    longest_line_width = max(line_widths) if line_widths else 0

    # Bubble body dimensions
    bubble_width = min(longest_line_width + 2 * BUBBLE_PADDING, max_width)
    # Enforce a minimum width so the tail doesn't look awkward
    bubble_width = max(bubble_width, TAIL_WIDTH + 2 * BUBBLE_PADDING)

    text_block_height = len(wrapped_lines) * (FONT_SIZE + LINE_SPACING) - LINE_SPACING
    bubble_body_height = text_block_height + 2 * BUBBLE_PADDING

    # Total image height includes the tail
    total_height = bubble_body_height + TAIL_HEIGHT

    # Calculate frames needed for typewriter effect
    total_chars = sum(len(line) for line in wrapped_lines)
    frames_per_char = frame_rate / chars_per_second
    typewriter_frames = int(total_chars * frames_per_char)
    # Hold the full text for 2 seconds after typewriter completes
    hold_frames = frame_rate * 2
    total_frames = typewriter_frames + hold_frames

    frames = []

    for frame_num in range(total_frames):
        # How many characters to show this frame
        if frame_num < typewriter_frames:
            chars_shown = min(total_chars, int(frame_num / frames_per_char) + 1)
        else:
            chars_shown = total_chars

        # Create transparent canvas
        img = Image.new("RGBA", (bubble_width, total_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw bubble body — rounded rectangle
        draw.rounded_rectangle(
            [0, 0, bubble_width - 1, bubble_body_height - 1],
            radius=BUBBLE_CORNER_RADIUS,
            fill=BUBBLE_BG_COLOR,
            outline=BUBBLE_BORDER_COLOR,
            width=BUBBLE_BORDER_WIDTH,
        )

        # Draw triangular tail at bottom-center
        tail_cx = bubble_width // 2
        tail_points = [
            (tail_cx - TAIL_WIDTH // 2, bubble_body_height - 1),
            (tail_cx, bubble_body_height + TAIL_HEIGHT - 1),
            (tail_cx + TAIL_WIDTH // 2, bubble_body_height - 1),
        ]
        draw.polygon(tail_points, fill=BUBBLE_BG_COLOR)
        # Draw tail border lines (left edge and right edge only, not top)
        draw.line(
            [tail_points[0], tail_points[1]],
            fill=BUBBLE_BORDER_COLOR, width=BUBBLE_BORDER_WIDTH,
        )
        draw.line(
            [tail_points[1], tail_points[2]],
            fill=BUBBLE_BORDER_COLOR, width=BUBBLE_BORDER_WIDTH,
        )

        # Draw typewriter text
        chars_remaining = chars_shown
        y = BUBBLE_PADDING
        for line in wrapped_lines:
            if chars_remaining <= 0:
                break
            visible = line[:chars_remaining]
            draw.text((BUBBLE_PADDING, y), visible, fill=TEXT_COLOR, font=font)
            chars_remaining -= len(line)
            y += FONT_SIZE + LINE_SPACING

        frames.append(img)

    return frames


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
