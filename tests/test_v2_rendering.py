"""Tests for v2 rendering engine (Stage 3).

Covers:
1. Camera system — interpolation, parallax offsets
2. Parallax backgrounds — folder-based loading with v1 fallback
3. 16:9 frame dimensions — 1920x1080 output
4. Text renderer — in-memory frames, wider text box for widescreen
5. Scene builder — generator-based frame output, position scaling
6. Composer — frame streaming via FFmpeg stdin (no intermediate PNGs)
7. End card — correct dimensions for 16:9
"""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image


# ---------------------------------------------------------------------------
# Camera system
# ---------------------------------------------------------------------------

class TestCamera:
    """Camera system for pan and zoom with parallax support."""

    def test_default_camera_at_origin(self):
        """Default camera starts at (0, 0) with zoom 1.0."""
        from src.video_assembler.camera import Camera
        cam = Camera()
        assert cam.x == 0.0
        assert cam.y == 0.0
        assert cam.zoom == 1.0

    def test_interpolate_midpoint(self):
        """At t=0.5, camera is halfway between start and end."""
        from src.video_assembler.camera import Camera, interpolate
        start = Camera(x=0, y=0, zoom=1.0)
        end = Camera(x=100, y=50, zoom=2.0)
        mid = interpolate(start, end, 0.5)
        assert mid.x == pytest.approx(50.0)
        assert mid.y == pytest.approx(25.0)
        assert mid.zoom == pytest.approx(1.5)

    def test_interpolate_at_zero_returns_start(self):
        """At t=0, camera is at start position."""
        from src.video_assembler.camera import Camera, interpolate
        start = Camera(x=10, y=20, zoom=1.5)
        end = Camera(x=100, y=200, zoom=3.0)
        result = interpolate(start, end, 0.0)
        assert result.x == pytest.approx(10.0)
        assert result.y == pytest.approx(20.0)
        assert result.zoom == pytest.approx(1.5)

    def test_interpolate_at_one_returns_end(self):
        """At t=1, camera is at end position."""
        from src.video_assembler.camera import Camera, interpolate
        start = Camera(x=10, y=20, zoom=1.5)
        end = Camera(x=100, y=200, zoom=3.0)
        result = interpolate(start, end, 1.0)
        assert result.x == pytest.approx(100.0)
        assert result.y == pytest.approx(200.0)
        assert result.zoom == pytest.approx(3.0)

    def test_parallax_offset_background_layer(self):
        """Background layer (depth=0.2) moves at 20% of camera speed."""
        from src.video_assembler.camera import parallax_offset
        ox, oy = parallax_offset(camera_x=100, camera_y=0, depth=0.2)
        assert ox == pytest.approx(20.0)
        assert oy == pytest.approx(0.0)

    def test_parallax_offset_foreground_layer(self):
        """Foreground layer (depth=1.0) moves at full camera speed."""
        from src.video_assembler.camera import parallax_offset
        ox, oy = parallax_offset(camera_x=100, camera_y=50, depth=1.0)
        assert ox == pytest.approx(100.0)
        assert oy == pytest.approx(50.0)

    def test_parallax_offset_zero_depth(self):
        """Depth 0.0 means the layer never moves (infinitely far away)."""
        from src.video_assembler.camera import parallax_offset
        ox, oy = parallax_offset(camera_x=500, camera_y=300, depth=0.0)
        assert ox == pytest.approx(0.0)
        assert oy == pytest.approx(0.0)

    def test_camera_from_scene_no_spec(self):
        """Scene with no camera spec returns static camera at origin."""
        from src.video_assembler.camera import Camera, camera_from_scene
        scene = {"duration_seconds": 10, "background": "diner_interior"}
        start, end = camera_from_scene(scene)
        assert start.x == 0.0 and start.y == 0.0 and start.zoom == 1.0
        assert end.x == 0.0 and end.y == 0.0 and end.zoom == 1.0

    def test_camera_from_scene_with_spec(self):
        """Scene with camera spec returns correct start/end cameras."""
        from src.video_assembler.camera import Camera, camera_from_scene
        scene = {
            "duration_seconds": 10,
            "camera": {
                "start": {"x": 0, "y": 0, "zoom": 1.0},
                "end": {"x": 200, "y": 0, "zoom": 1.2},
            },
        }
        start, end = camera_from_scene(scene)
        assert start.x == 0.0
        assert end.x == 200.0
        assert end.zoom == pytest.approx(1.2)


# ---------------------------------------------------------------------------
# Parallax background loading
# ---------------------------------------------------------------------------

class TestParallaxLoading:
    """Multi-layer background support with v1 single-file fallback."""

    def test_load_layers_from_folder(self, tmp_path):
        """If backgrounds/location/ folder has layer files, load all layers."""
        from src.video_assembler.scene_builder import load_background_layers

        loc_dir = tmp_path / "backgrounds" / "test_loc"
        loc_dir.mkdir(parents=True)
        for name in ["background.png", "midground.png", "foreground.png"]:
            img = Image.new("RGBA", (1920, 1080), (100, 100, 100, 255))
            img.save(str(loc_dir / name))

        with patch("src.video_assembler.scene_builder.ASSETS_DIR", str(tmp_path)):
            layers = load_background_layers("test_loc")
        assert len(layers) == 3

    def test_layers_have_correct_dimensions(self, tmp_path):
        """All loaded layers must be 1920x1080."""
        from src.video_assembler.scene_builder import load_background_layers, FRAME_WIDTH, FRAME_HEIGHT

        loc_dir = tmp_path / "backgrounds" / "test_loc"
        loc_dir.mkdir(parents=True)
        # Create layers at non-standard size — they should be scaled
        for name in ["background.png", "midground.png"]:
            img = Image.new("RGBA", (960, 540), (100, 100, 100, 255))
            img.save(str(loc_dir / name))

        with patch("src.video_assembler.scene_builder.ASSETS_DIR", str(tmp_path)):
            layers = load_background_layers("test_loc")
        for layer in layers:
            assert layer.size == (FRAME_WIDTH, FRAME_HEIGHT)

    def test_fallback_to_single_file(self, tmp_path):
        """If no folder, fall back to single backgrounds/location.png."""
        from src.video_assembler.scene_builder import load_background_layers, FRAME_WIDTH, FRAME_HEIGHT

        bg_dir = tmp_path / "backgrounds"
        bg_dir.mkdir()
        # v1-sized background (1080x1920)
        img = Image.new("RGB", (1080, 1920), (50, 50, 50))
        img.save(str(bg_dir / "test_loc.png"))

        with patch("src.video_assembler.scene_builder.ASSETS_DIR", str(tmp_path)):
            layers = load_background_layers("test_loc")
        assert len(layers) == 1
        assert layers[0].size == (FRAME_WIDTH, FRAME_HEIGHT)

    def test_missing_background_warns(self, tmp_path):
        """Missing background produces warning and solid color fallback."""
        from src.video_assembler.scene_builder import (
            load_background_layers, clear_warnings, get_warnings, FRAME_WIDTH, FRAME_HEIGHT,
        )
        clear_warnings()
        with patch("src.video_assembler.scene_builder.ASSETS_DIR", str(tmp_path)):
            layers = load_background_layers("nonexistent_xyz")
        assert len(layers) == 1
        assert layers[0].size == (FRAME_WIDTH, FRAME_HEIGHT)
        assert len(get_warnings()) >= 1
        assert "nonexistent_xyz" in get_warnings()[0]

    def test_effects_layer_loaded_if_present(self, tmp_path):
        """Optional effects.png layer loaded when it exists."""
        from src.video_assembler.scene_builder import load_background_layers

        loc_dir = tmp_path / "backgrounds" / "test_loc"
        loc_dir.mkdir(parents=True)
        for name in ["background.png", "midground.png", "foreground.png", "effects.png"]:
            img = Image.new("RGBA", (1920, 1080), (100, 100, 100, 128))
            img.save(str(loc_dir / name))

        with patch("src.video_assembler.scene_builder.ASSETS_DIR", str(tmp_path)):
            layers = load_background_layers("test_loc")
        assert len(layers) == 4


# ---------------------------------------------------------------------------
# 16:9 frame dimensions
# ---------------------------------------------------------------------------

class TestFrameDimensions:
    """v2 rendering must target 1920x1080 (16:9 horizontal)."""

    def test_frame_width_is_1920(self):
        from src.video_assembler.scene_builder import FRAME_WIDTH
        assert FRAME_WIDTH == 1920

    def test_frame_height_is_1080(self):
        from src.video_assembler.scene_builder import FRAME_HEIGHT
        assert FRAME_HEIGHT == 1080

    def test_frame_rate_unchanged(self):
        from src.video_assembler.scene_builder import FRAME_RATE
        assert FRAME_RATE == 30

    def test_load_background_returns_16x9(self):
        """load_background() still works and returns 1920x1080."""
        from src.video_assembler.scene_builder import (
            load_background, FRAME_WIDTH, FRAME_HEIGHT, clear_warnings,
        )
        clear_warnings()
        bg = load_background("diner_interior")
        assert bg.size == (FRAME_WIDTH, FRAME_HEIGHT)


# ---------------------------------------------------------------------------
# Text renderer — in-memory, wider for widescreen
# ---------------------------------------------------------------------------

class TestTextRendererV2:
    """Text renderer must return PIL Images (not file paths) and be sized for 16:9."""

    def test_render_returns_pil_images(self):
        """render_dialogue_frames must return list of PIL Images, not file paths."""
        from src.text_renderer.renderer import render_dialogue_frames
        frames = render_dialogue_frames(
            character_id="pens",
            text="Hello world.",
            frame_rate=30,
        )
        assert len(frames) > 0
        assert isinstance(frames[0], Image.Image)

    def test_text_box_width_for_widescreen(self):
        """Text box must be wider for 16:9 format."""
        from src.text_renderer.renderer import BOX_WIDTH
        # Should be wider than v1's 900px
        assert BOX_WIDTH >= 1100

    def test_text_box_is_rgba(self):
        """Text box frames must be RGBA (for alpha compositing)."""
        from src.text_renderer.renderer import render_dialogue_frames
        frames = render_dialogue_frames(
            character_id="pens",
            text="Test.",
            frame_rate=30,
        )
        assert frames[0].mode == "RGBA"

    def test_typewriter_animation_still_works(self):
        """More frames than just one (typewriter + hold)."""
        from src.text_renderer.renderer import render_dialogue_frames
        frames = render_dialogue_frames(
            character_id="pens",
            text="This is a test line with many characters for typewriter.",
            frame_rate=30,
        )
        # At 12 cps, 54 chars = 4.5s typewriter + 2s hold = 6.5s * 30fps = 195 frames
        assert len(frames) > 100


# ---------------------------------------------------------------------------
# Scene builder — generator output, position scaling
# ---------------------------------------------------------------------------

class TestSceneBuilderV2:
    """Scene builder must output generator of PIL Images at 1920x1080."""

    def test_build_scene_returns_generator_and_metadata(self):
        """build_scene_frames returns (frame_iter, total_frames, sfx_events)."""
        from src.video_assembler.scene_builder import build_scene_frames

        scene = {
            "background": "diner_interior",
            "duration_seconds": 2,
            "characters_present": ["pens"],
            "character_positions": {"pens": "stool_1"},
            "character_animations": {"pens": "idle"},
            "dialogue": [],
            "sfx_triggers": [],
        }
        result = build_scene_frames(scene, frame_offset=0)
        frame_iter, total_frames, sfx_events = result
        assert total_frames > 0
        assert isinstance(sfx_events, list)

    def test_frame_iter_yields_pil_images(self):
        """Frame iterator must yield PIL Images."""
        from src.video_assembler.scene_builder import build_scene_frames

        scene = {
            "background": "diner_interior",
            "duration_seconds": 2,
            "characters_present": [],
            "character_positions": {},
            "character_animations": {},
            "dialogue": [],
            "sfx_triggers": [],
        }
        frame_iter, total_frames, _ = build_scene_frames(scene, frame_offset=0)
        first_frame = next(frame_iter)
        assert isinstance(first_frame, Image.Image)

    def test_frames_are_1920x1080(self):
        """Each frame must be 1920x1080."""
        from src.video_assembler.scene_builder import build_scene_frames, FRAME_WIDTH, FRAME_HEIGHT

        scene = {
            "background": "diner_interior",
            "duration_seconds": 1,
            "characters_present": [],
            "character_positions": {},
            "character_animations": {},
            "dialogue": [],
            "sfx_triggers": [],
        }
        frame_iter, total_frames, _ = build_scene_frames(scene, frame_offset=0)
        first_frame = next(frame_iter)
        assert first_frame.size == (FRAME_WIDTH, FRAME_HEIGHT)

    def test_total_frames_matches_duration(self):
        """2 seconds at 30fps = 60 frames (minimum, may be more with dialogue)."""
        from src.video_assembler.scene_builder import build_scene_frames

        scene = {
            "background": "diner_interior",
            "duration_seconds": 2,
            "characters_present": [],
            "character_positions": {},
            "character_animations": {},
            "dialogue": [],
            "sfx_triggers": [],
        }
        _, total_frames, _ = build_scene_frames(scene, frame_offset=0)
        assert total_frames == 60

    def test_position_scaling_from_v1(self):
        """v1 positions (1080x1920) must be scaled to 1920x1080."""
        from src.video_assembler.scene_builder import scale_position_v1

        # stool_1 in diner: (370, 1300) in 1080x1920
        x, y = scale_position_v1(370, 1300, target_width=1920, target_height=1080)
        # x_new = 370 * 1920/1080 = ~658
        # y_new = 1300 * 1080/1920 = ~731
        assert 650 <= x <= 670
        assert 725 <= y <= 740


# ---------------------------------------------------------------------------
# Composer — frame streaming
# ---------------------------------------------------------------------------

class TestComposerStreaming:
    """Composer must stream frames to FFmpeg via stdin, not write PNGs to disk."""

    def test_compose_still_returns_video_path(self):
        """compose_episode public API unchanged: returns path to MP4."""
        from src.video_assembler.composer import compose_episode

        # Minimal 1-scene script with short duration
        script = {
            "episode_id": "EP099",
            "title": "Test",
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

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.video_assembler.composer.OUTPUT_DIR", tmpdir):
                video_path = compose_episode(script, output_name="test_stream")
                assert video_path is not None
                assert video_path.endswith(".mp4")
                assert os.path.exists(video_path)

    def test_no_intermediate_frame_pngs(self):
        """After compose_episode, no frame_*.png files should remain on disk."""
        from src.video_assembler.composer import compose_episode

        script = {
            "episode_id": "EP099",
            "title": "Test",
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

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.video_assembler.composer.OUTPUT_DIR", tmpdir):
                compose_episode(script, output_name="test_no_frames")
                # Walk the entire temp directory for frame PNGs
                frame_pngs = []
                for root, dirs, files in os.walk(tmpdir):
                    for f in files:
                        if f.startswith("frame_") and f.endswith(".png"):
                            frame_pngs.append(f)
                assert len(frame_pngs) == 0, f"Found {len(frame_pngs)} leftover frame PNGs"


# ---------------------------------------------------------------------------
# End card — 16:9 dimensions
# ---------------------------------------------------------------------------

class TestEndCardV2:
    """End card must render at 1920x1080."""

    def test_end_card_yields_correct_size(self):
        """End card frames must be 1920x1080."""
        from src.video_assembler.composer import generate_end_card_frames
        from src.video_assembler.scene_builder import FRAME_WIDTH, FRAME_HEIGHT

        frames = list(generate_end_card_frames("Test Episode", "EP001"))
        assert len(frames) > 0
        assert isinstance(frames[0], Image.Image)
        assert frames[0].size == (FRAME_WIDTH, FRAME_HEIGHT)

    def test_end_card_frame_count(self):
        """End card at 3 seconds * 30fps = 90 frames."""
        from src.video_assembler.composer import generate_end_card_frames

        frames = list(generate_end_card_frames("Test", "EP001"))
        assert len(frames) == 90  # 3s * 30fps
