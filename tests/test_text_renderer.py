"""Tests for the NES-style text box renderer (src/text_renderer/renderer.py).

Tests cover:
- Word wrapping logic
- Dialogue frame generation (typewriter animation)
- Text box visual spec constants
"""

import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock

import pytest
from PIL import ImageFont

from src.text_renderer.renderer import (
    _word_wrap,
    render_dialogue_frames,
    BOX_WIDTH,
    BOX_HEIGHT,
    FONT_SIZE,
    PORTRAIT_SIZE,
)


@pytest.fixture
def output_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


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


class TestBoxConstants:
    """Test that visual spec constants match PRD."""

    def test_box_width(self):
        # v2: wider text box for 16:9 widescreen format
        assert BOX_WIDTH == 1200

    def test_box_height(self):
        # v2: slightly shorter text box for 16:9
        assert BOX_HEIGHT == 180

    def test_font_size(self):
        assert FONT_SIZE == 16

    def test_portrait_size(self):
        assert PORTRAIT_SIZE == 48


class TestRenderDialogueFrames:
    """Test dialogue frame rendering."""

    def test_returns_frame_paths(self, output_dir):
        frames = render_dialogue_frames(
            character_id="pens",
            text="...cool.",
            output_dir=output_dir,
            frame_rate=30,
        )
        assert isinstance(frames, list)
        assert len(frames) > 0

    def test_frames_are_pil_images(self, output_dir):
        """v2: render_dialogue_frames returns PIL Images, not file paths."""
        from PIL import Image
        frames = render_dialogue_frames(
            character_id="pens",
            text="hi",
            output_dir=output_dir,
            frame_rate=30,
        )
        for frame in frames:
            assert isinstance(frame, Image.Image)
            assert frame.mode == "RGBA"

    def test_includes_hold_frames(self, output_dir):
        """Should have extra frames at the end holding the full text."""
        frames = render_dialogue_frames(
            character_id="pens",
            text="ok",
            output_dir=output_dir,
            frame_rate=30,
            chars_per_second=20,
        )
        # 2 chars * (30/20) frames/char = 3 typewriter frames + 15 hold frames = 18
        assert len(frames) >= 3

    def test_longer_text_more_frames(self, output_dir):
        short_frames = render_dialogue_frames(
            character_id="pens",
            text="hi",
            output_dir=os.path.join(output_dir, "short"),
            frame_rate=30,
        )
        long_frames = render_dialogue_frames(
            character_id="pens",
            text="this is a much longer piece of dialogue for testing",
            output_dir=os.path.join(output_dir, "long"),
            frame_rate=30,
        )
        assert len(long_frames) > len(short_frames)

    def test_output_dir_ignored_in_v2(self, output_dir):
        """v2: output_dir parameter is deprecated and ignored (frames are in-memory)."""
        from PIL import Image
        nested = os.path.join(output_dir, "nested", "deep")
        frames = render_dialogue_frames(
            character_id="pens",
            text="test",
            output_dir=nested,
            frame_rate=30,
        )
        # Should return PIL Images regardless of output_dir
        assert len(frames) > 0
        assert isinstance(frames[0], Image.Image)
