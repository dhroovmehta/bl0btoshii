"""Tests for the speech bubble renderer (src/text_renderer/renderer.py).

Tests cover:
- Word wrapping logic
- Bubble constant validation
- Speech bubble rendering (auto-sizing, tail, typewriter, transparency)
"""

import numpy as np
from unittest.mock import patch

import pytest
from PIL import Image, ImageFont

from src.text_renderer.renderer import (
    _word_wrap,
    render_dialogue_frames,
    FONT_SIZE,
    BUBBLE_BG_COLOR,
    BUBBLE_PADDING,
    BUBBLE_MAX_WIDTH,
    TAIL_HEIGHT,
    TAIL_WIDTH,
    LINE_SPACING,
)


class TestWordWrap:
    """Test the word wrapping function."""

    def test_short_text_single_line(self):
        font = ImageFont.load_default()
        lines = _word_wrap("hello", font, 500)
        assert len(lines) == 1
        assert lines[0] == "hello"

    def test_empty_text(self):
        font = ImageFont.load_default()
        lines = _word_wrap("", font, 500)
        assert lines == []

    def test_single_word(self):
        font = ImageFont.load_default()
        lines = _word_wrap("word", font, 500)
        assert lines == ["word"]

    def test_wraps_long_text(self):
        font = ImageFont.load_default()
        long_text = "this is a very long sentence that should wrap across multiple lines"
        lines = _word_wrap(long_text, font, 100)
        assert len(lines) > 1
        # All words should be present
        all_words = " ".join(lines).split()
        assert all_words == long_text.split()

    def test_preserves_all_words(self):
        font = ImageFont.load_default()
        text = "one two three four five"
        lines = _word_wrap(text, font, 50)
        reassembled = " ".join(lines)
        assert reassembled == text


class TestBubbleConstants:
    """Test that speech bubble constants are sensible."""

    def test_font_size(self):
        assert FONT_SIZE == 16

    def test_bubble_bg_is_dark(self):
        """Bubble background should be dark (near-black)."""
        r, g, b = BUBBLE_BG_COLOR[:3]
        assert r < 50 and g < 50 and b < 50

    def test_bubble_bg_is_opaque(self):
        """Bubble should be mostly opaque."""
        alpha = BUBBLE_BG_COLOR[3]
        assert alpha >= 200

    def test_padding_positive(self):
        assert BUBBLE_PADDING > 0

    def test_tail_height_positive(self):
        assert TAIL_HEIGHT > 0

    def test_tail_width_positive(self):
        assert TAIL_WIDTH > 0

    def test_max_width_reasonable(self):
        """Max width should be reasonable for a speech bubble (not full screen)."""
        assert 300 <= BUBBLE_MAX_WIDTH <= 700

    def test_line_spacing_positive(self):
        assert LINE_SPACING > 0


class TestSpeechBubbleRendering:
    """Test the speech bubble frame rendering."""

    def test_returns_pil_images_rgba(self):
        """Frames should be RGBA PIL Images."""
        frames = render_dialogue_frames(
            character_id="pens",
            text="hello",
            frame_rate=30,
        )
        assert isinstance(frames, list)
        assert len(frames) > 0
        for frame in frames:
            assert isinstance(frame, Image.Image)
            assert frame.mode == "RGBA"

    def test_bubble_has_transparency(self):
        """The bubble image should have transparent pixels around the bubble body."""
        frames = render_dialogue_frames(
            character_id="pens",
            text="hi",
            frame_rate=30,
        )
        # Check that corners of the image are transparent (bubble has rounded shape + tail)
        arr = np.array(frames[-1])  # Last frame (full text)
        # Top-left corner should be transparent (or near-transparent)
        assert arr[0, 0, 3] < 50, "Top-left corner should be transparent"

    def test_bubble_width_auto_sizes(self):
        """Short text should produce narrower bubble than long text."""
        short_frames = render_dialogue_frames(
            character_id="pens",
            text="hi",
            frame_rate=30,
        )
        long_frames = render_dialogue_frames(
            character_id="pens",
            text="this is a much longer piece of dialogue",
            frame_rate=30,
        )
        assert short_frames[0].width < long_frames[0].width

    def test_bubble_width_capped(self):
        """Very long text should not exceed BUBBLE_MAX_WIDTH."""
        frames = render_dialogue_frames(
            character_id="pens",
            text="this is a very long sentence that would normally be extremely wide if not capped at maximum width",
            frame_rate=30,
        )
        assert frames[0].width <= BUBBLE_MAX_WIDTH

    def test_bubble_includes_tail(self):
        """Image height should include extra space for the tail."""
        frames = render_dialogue_frames(
            character_id="pens",
            text="hello",
            frame_rate=30,
        )
        # The total image height should be more than just padding + text
        # because the tail adds TAIL_HEIGHT at the bottom
        assert frames[0].height >= FONT_SIZE + 2 * BUBBLE_PADDING + TAIL_HEIGHT

    def test_typewriter_effect(self):
        """Early frames should have less visible content than later frames."""
        frames = render_dialogue_frames(
            character_id="pens",
            text="hello world test",
            frame_rate=30,
            chars_per_second=12,
        )
        # First frame should have fewer opaque pixels than last frame
        first_arr = np.array(frames[0])
        last_arr = np.array(frames[-1])
        first_opaque = np.sum(first_arr[:, :, 3] > 128)
        last_opaque = np.sum(last_arr[:, :, 3] > 128)
        assert first_opaque <= last_opaque

    def test_no_portrait_in_bubble(self):
        """Bubble should be compact — no 48px portrait taking up space."""
        frames = render_dialogue_frames(
            character_id="pens",
            text="hi",
            frame_rate=30,
        )
        # A bubble for "hi" should be much narrower than the old 1200px text box
        assert frames[0].width < 300

    def test_hold_frames_at_end(self):
        """Should have extra frames at the end holding the full text."""
        frames = render_dialogue_frames(
            character_id="pens",
            text="ok",
            frame_rate=30,
            chars_per_second=12,
        )
        # 2 chars at 12 CPS = 2 * (30/12) = 5 typewriter frames + 60 hold = 65 total
        assert len(frames) >= 60  # At least 2 seconds of hold

    def test_longer_text_more_frames(self):
        """Longer text should produce more frames due to typewriter effect."""
        short_frames = render_dialogue_frames(
            character_id="pens",
            text="hi",
            frame_rate=30,
        )
        long_frames = render_dialogue_frames(
            character_id="pens",
            text="this is a much longer piece of dialogue for testing",
            frame_rate=30,
        )
        assert len(long_frames) > len(short_frames)

    def test_output_dir_ignored(self):
        """output_dir parameter is deprecated and ignored."""
        frames = render_dialogue_frames(
            character_id="pens",
            text="test",
            output_dir="/nonexistent/path",
            frame_rate=30,
        )
        assert len(frames) > 0
        assert isinstance(frames[0], Image.Image)

    def test_render_config_controls_max_width(self):
        """render_config.text_box_width should control max bubble width."""
        from src.video_assembler.render_config import RenderConfig
        narrow_config = RenderConfig(
            width=1080, height=1920,
            text_box_width=300, text_box_height=180, text_box_y=1680,
            label="narrow_test",
        )
        frames = render_dialogue_frames(
            character_id="pens",
            text="this is a long sentence that needs wrapping at the narrow width",
            frame_rate=30,
            render_config=narrow_config,
        )
        assert frames[0].width <= 300
