"""Render configuration presets for dual format output.

Two format presets:
  HORIZONTAL — 1920x1080, 16:9, for YouTube regular videos
  VERTICAL   — 1080x1920, 9:16, for YouTube Shorts / TikTok / Reels

Each preset defines the frame dimensions and speech bubble layout so the
same rendering code produces both formats.

Note: text_box_width now controls max speech bubble width (not a full-width text box).
text_box_height and text_box_y are kept for backward compatibility but unused —
bubbles auto-size and position above the speaking character.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderConfig:
    """All format-specific rendering parameters in one place."""

    width: int
    height: int
    text_box_width: int      # Max speech bubble width
    text_box_height: int     # Unused — bubble height is auto-calculated
    text_box_y: int          # Unused — bubble position is character-relative
    label: str  # "horizontal" or "vertical" — used in filenames


HORIZONTAL = RenderConfig(
    width=1920,
    height=1080,
    text_box_width=500,
    text_box_height=180,
    text_box_y=880,
    label="horizontal",
)

VERTICAL = RenderConfig(
    width=1080,
    height=1920,
    text_box_width=450,
    text_box_height=180,
    text_box_y=1680,
    label="vertical",
)
