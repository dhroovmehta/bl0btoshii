"""Tests for Stage 4: Dual format output (horizontal + vertical).

The same episode script renders as both 16:9 horizontal (1920x1080) and
9:16 vertical (1080x1920). The render_config module holds the format
presets. Rendering functions accept a config so the same code path
produces both sizes.

Test groups:
1. RenderConfig — HORIZONTAL and VERTICAL presets
2. Text renderer — text box adapts to format
3. Scene builder — frames match config dimensions
4. Composer — produces video at config dimensions
5. End card — adapts to format
6. Pipeline integration — produces two video files
"""

import os
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from PIL import Image


# ---------------------------------------------------------------------------
# RenderConfig presets
# ---------------------------------------------------------------------------

class TestRenderConfig:
    """RenderConfig must define HORIZONTAL and VERTICAL presets."""

    def test_horizontal_preset_exists(self):
        from src.video_assembler.render_config import HORIZONTAL
        assert HORIZONTAL is not None

    def test_vertical_preset_exists(self):
        from src.video_assembler.render_config import VERTICAL
        assert VERTICAL is not None

    def test_horizontal_dimensions(self):
        """HORIZONTAL must be 1920x1080."""
        from src.video_assembler.render_config import HORIZONTAL
        assert HORIZONTAL.width == 1920
        assert HORIZONTAL.height == 1080

    def test_vertical_dimensions(self):
        """VERTICAL must be 1080x1920."""
        from src.video_assembler.render_config import VERTICAL
        assert VERTICAL.width == 1080
        assert VERTICAL.height == 1920

    def test_horizontal_text_box(self):
        """HORIZONTAL text box: 1200px wide, near bottom of 1080 frame."""
        from src.video_assembler.render_config import HORIZONTAL
        assert HORIZONTAL.text_box_width == 1200
        assert HORIZONTAL.text_box_y == 880

    def test_vertical_text_box(self):
        """VERTICAL text box: 900px wide, near bottom of 1920 frame."""
        from src.video_assembler.render_config import VERTICAL
        assert VERTICAL.text_box_width == 900
        assert VERTICAL.text_box_y == 1680

    def test_both_have_labels(self):
        """Presets have human-readable labels for filenames."""
        from src.video_assembler.render_config import HORIZONTAL, VERTICAL
        assert HORIZONTAL.label == "horizontal"
        assert VERTICAL.label == "vertical"

    def test_text_box_height_same_both_formats(self):
        """Text box height is the same for both formats."""
        from src.video_assembler.render_config import HORIZONTAL, VERTICAL
        assert HORIZONTAL.text_box_height == VERTICAL.text_box_height
        assert HORIZONTAL.text_box_height == 180


# ---------------------------------------------------------------------------
# Text renderer — adapts to format
# ---------------------------------------------------------------------------

class TestTextRendererDualFormat:
    """Text renderer produces correctly-sized text boxes for each format."""

    def test_horizontal_text_box_width(self):
        """In horizontal mode, text box is 1200px wide."""
        from src.video_assembler.render_config import HORIZONTAL
        from src.text_renderer.renderer import render_dialogue_frames
        frames = render_dialogue_frames(
            character_id="pens",
            text="Hello.",
            frame_rate=30,
            render_config=HORIZONTAL,
        )
        assert frames[0].width == 1200

    def test_vertical_text_box_width(self):
        """In vertical mode, text box is 900px wide."""
        from src.video_assembler.render_config import VERTICAL
        from src.text_renderer.renderer import render_dialogue_frames
        frames = render_dialogue_frames(
            character_id="pens",
            text="Hello.",
            frame_rate=30,
            render_config=VERTICAL,
        )
        assert frames[0].width == 900

    def test_default_uses_horizontal(self):
        """Without render_config, uses horizontal (backward compat)."""
        from src.text_renderer.renderer import render_dialogue_frames
        frames = render_dialogue_frames(
            character_id="pens",
            text="Hello.",
            frame_rate=30,
        )
        # Default should be 1200 (horizontal)
        assert frames[0].width == 1200


# ---------------------------------------------------------------------------
# Scene builder — frames match config dimensions
# ---------------------------------------------------------------------------

class TestSceneBuilderDualFormat:
    """Scene builder produces frames at the config's dimensions."""

    def _make_scene(self, duration=1):
        return {
            "background": "diner_interior",
            "duration_seconds": duration,
            "characters_present": [],
            "character_positions": {},
            "character_animations": {},
            "dialogue": [],
            "sfx_triggers": [],
        }

    def test_horizontal_frames_1920x1080(self):
        """With HORIZONTAL config, frames are 1920x1080."""
        from src.video_assembler.render_config import HORIZONTAL
        from src.video_assembler.scene_builder import build_scene_frames
        frame_iter, total_frames, _ = build_scene_frames(
            self._make_scene(), frame_offset=0, render_config=HORIZONTAL
        )
        first_frame = next(frame_iter)
        assert first_frame.size == (1920, 1080)

    def test_vertical_frames_1080x1920(self):
        """With VERTICAL config, frames are 1080x1920."""
        from src.video_assembler.render_config import VERTICAL
        from src.video_assembler.scene_builder import build_scene_frames
        frame_iter, total_frames, _ = build_scene_frames(
            self._make_scene(), frame_offset=0, render_config=VERTICAL
        )
        first_frame = next(frame_iter)
        assert first_frame.size == (1080, 1920)

    def test_default_uses_horizontal(self):
        """Without render_config, defaults to 1920x1080."""
        from src.video_assembler.scene_builder import build_scene_frames
        frame_iter, _, _ = build_scene_frames(self._make_scene(), frame_offset=0)
        first_frame = next(frame_iter)
        assert first_frame.size == (1920, 1080)

    def test_vertical_position_no_scaling(self):
        """In vertical mode (1080x1920), v1 positions should map 1:1."""
        from src.video_assembler.scene_builder import scale_position_v1
        # v1 coords are for 1080x1920; targeting 1080x1920 = identity transform
        x, y = scale_position_v1(370, 1300, target_width=1080, target_height=1920)
        assert x == 370
        assert y == 1300


# ---------------------------------------------------------------------------
# Composer — produces video at config dimensions
# ---------------------------------------------------------------------------

class TestComposerDualFormat:
    """Composer produces videos at the specified format dimensions."""

    def _make_script(self):
        return {
            "episode_id": "EP099",
            "title": "Dual Format Test",
            "scenes": [{
                "scene_number": 1,
                "duration_seconds": 1,
                "background": "diner_interior",
                "characters_present": [],
                "character_positions": {},
                "character_animations": {},
                "dialogue": [],
                "sfx_triggers": [],
                "music": "main_theme.wav",
            }],
        }

    def test_horizontal_video_created(self):
        """compose_episode with HORIZONTAL config creates a valid MP4."""
        from src.video_assembler.composer import compose_episode
        from src.video_assembler.render_config import HORIZONTAL

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.video_assembler.composer.OUTPUT_DIR", tmpdir):
                video_path = compose_episode(
                    self._make_script(),
                    output_name="test_h",
                    render_config=HORIZONTAL,
                )
                assert os.path.exists(video_path)
                assert video_path.endswith(".mp4")

    def test_vertical_video_created(self):
        """compose_episode with VERTICAL config creates a valid MP4."""
        from src.video_assembler.composer import compose_episode
        from src.video_assembler.render_config import VERTICAL

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.video_assembler.composer.OUTPUT_DIR", tmpdir):
                video_path = compose_episode(
                    self._make_script(),
                    output_name="test_v",
                    render_config=VERTICAL,
                )
                assert os.path.exists(video_path)
                assert video_path.endswith(".mp4")

    def test_default_is_horizontal(self):
        """Without render_config, compose_episode defaults to horizontal."""
        from src.video_assembler.composer import compose_episode

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.video_assembler.composer.OUTPUT_DIR", tmpdir):
                video_path = compose_episode(
                    self._make_script(),
                    output_name="test_default",
                )
                assert os.path.exists(video_path)

    def test_output_name_includes_format_label(self):
        """When render_config given, output file name includes the format label."""
        from src.video_assembler.composer import compose_episode
        from src.video_assembler.render_config import VERTICAL

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.video_assembler.composer.OUTPUT_DIR", tmpdir):
                video_path = compose_episode(
                    self._make_script(),
                    output_name="test_ep",
                    render_config=VERTICAL,
                )
                # Filename should contain the format label
                basename = os.path.basename(video_path)
                assert "vertical" in basename


# ---------------------------------------------------------------------------
# End card — adapts to format
# ---------------------------------------------------------------------------

class TestEndCardDualFormat:
    """End card must render at the config's dimensions."""

    def test_horizontal_end_card_size(self):
        """End card with HORIZONTAL config = 1920x1080."""
        from src.video_assembler.composer import generate_end_card_frames
        from src.video_assembler.render_config import HORIZONTAL

        frames = list(generate_end_card_frames("Test", "EP001", render_config=HORIZONTAL))
        assert frames[0].size == (1920, 1080)

    def test_vertical_end_card_size(self):
        """End card with VERTICAL config = 1080x1920."""
        from src.video_assembler.composer import generate_end_card_frames
        from src.video_assembler.render_config import VERTICAL

        frames = list(generate_end_card_frames("Test", "EP001", render_config=VERTICAL))
        assert frames[0].size == (1080, 1920)

    def test_end_card_default_is_horizontal(self):
        """Without render_config, end card defaults to 1920x1080."""
        from src.video_assembler.composer import generate_end_card_frames

        frames = list(generate_end_card_frames("Test", "EP001"))
        assert frames[0].size == (1920, 1080)


# ---------------------------------------------------------------------------
# Quality gate — accepts both resolutions
# ---------------------------------------------------------------------------

class TestQualityCheckDualFormat:
    """Quality checker must accept both 1920x1080 and 1080x1920."""

    def test_horizontal_resolution_passes(self):
        """1920x1080 video passes resolution check."""
        from src.video_assembler.composer import compose_episode
        from src.video_assembler.render_config import HORIZONTAL
        from src.pipeline.orchestrator import check_video_quality

        script = {
            "episode_id": "EP099", "title": "Test",
            "scenes": [{
                "scene_number": 1, "duration_seconds": 2,
                "background": "diner_interior",
                "characters_present": [],
                "character_positions": {},
                "character_animations": {},
                "dialogue": [],
                "sfx_triggers": [],
            }],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.video_assembler.composer.OUTPUT_DIR", tmpdir):
                video_path = compose_episode(script, output_name="test_h_qc", render_config=HORIZONTAL)
                passed, issues = check_video_quality(video_path)
                # Resolution should not be flagged as an issue
                res_issues = [i for i in issues if "Resolution" in i]
                assert len(res_issues) == 0, f"Unexpected resolution issues: {res_issues}"

    def test_vertical_resolution_passes(self):
        """1080x1920 video passes resolution check."""
        from src.video_assembler.composer import compose_episode
        from src.video_assembler.render_config import VERTICAL
        from src.pipeline.orchestrator import check_video_quality

        script = {
            "episode_id": "EP099", "title": "Test",
            "scenes": [{
                "scene_number": 1, "duration_seconds": 2,
                "background": "diner_interior",
                "characters_present": [],
                "character_positions": {},
                "character_animations": {},
                "dialogue": [],
                "sfx_triggers": [],
            }],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.video_assembler.composer.OUTPUT_DIR", tmpdir):
                video_path = compose_episode(script, output_name="test_v_qc", render_config=VERTICAL)
                passed, issues = check_video_quality(video_path)
                res_issues = [i for i in issues if "Resolution" in i]
                assert len(res_issues) == 0, f"Unexpected resolution issues: {res_issues}"
