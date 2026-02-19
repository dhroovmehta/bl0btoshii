"""Render configuration presets for dual format output.

Two format presets:
  HORIZONTAL — 1920x1080, 16:9, for YouTube regular videos
  VERTICAL   — 1080x1920, 9:16, for YouTube Shorts / TikTok / Reels

Each preset defines the frame dimensions and text box layout so the
same rendering code produces both formats.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderConfig:
    """All format-specific rendering parameters in one place."""

    width: int
    height: int
    text_box_width: int
    text_box_height: int
    text_box_y: int
    label: str  # "horizontal" or "vertical" — used in filenames


HORIZONTAL = RenderConfig(
    width=1920,
    height=1080,
    text_box_width=1200,
    text_box_height=180,
    text_box_y=880,
    label="horizontal",
)

VERTICAL = RenderConfig(
    width=1080,
    height=1920,
    text_box_width=900,
    text_box_height=180,
    text_box_y=1680,
    label="vertical",
)
