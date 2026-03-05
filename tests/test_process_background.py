"""Tests for the background processing script.

Verifies watermark removal, resizing, and filename mapping
for converting source background images into pipeline-ready assets.
"""

import os
import tempfile
import shutil

import pytest
from PIL import Image


# Import after defining — the script lives in scripts/, not src/
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.process_background import (
    NAME_MAP,
    HORIZONTAL_SIZE,
    VERTICAL_SIZE,
    build_output_filename,
    crop_dark_edges,
    process_single_background,
)


class TestNameMapping:
    """Source filenames map correctly to pipeline location IDs."""

    def test_name_map_has_four_locations(self):
        assert len(NAME_MAP) == 4

    def test_reows_maps_to_reows_place(self):
        assert NAME_MAP["reows"] == "reows_place"

    def test_diner_maps_to_diner(self):
        assert NAME_MAP["diner"] == "diner"

    def test_farmers_market_maps_to_farmers_market(self):
        assert NAME_MAP["farmers_market"] == "farmers_market"

    def test_town_square_maps_to_town_square(self):
        assert NAME_MAP["town_square"] == "town_square"


class TestOutputFilenames:
    """Output filenames follow the correct convention."""

    def test_horizontal_output_name(self):
        assert build_output_filename("diner", "horizontal") == "diner.png"

    def test_vertical_output_name(self):
        assert build_output_filename("diner", "vertical") == "diner_vertical.png"

    def test_reows_horizontal_uses_pipeline_name(self):
        assert build_output_filename("reows_place", "horizontal") == "reows_place.png"

    def test_reows_vertical_uses_pipeline_name(self):
        assert build_output_filename("reows_place", "vertical") == "reows_place_vertical.png"

    def test_all_eight_output_filenames(self):
        expected = {
            "diner.png", "diner_vertical.png",
            "farmers_market.png", "farmers_market_vertical.png",
            "reows_place.png", "reows_place_vertical.png",
            "town_square.png", "town_square_vertical.png",
        }
        actual = set()
        for pipeline_name in NAME_MAP.values():
            actual.add(build_output_filename(pipeline_name, "horizontal"))
            actual.add(build_output_filename(pipeline_name, "vertical"))
        assert actual == expected


class TestProcessSingleBackground:
    """Processing a single background: watermark patch + resize."""

    @pytest.fixture
    def work_dir(self):
        d = tempfile.mkdtemp()
        yield d
        shutil.rmtree(d, ignore_errors=True)

    def _make_test_image(self, path, width, height):
        """Create a solid-color test image at the given dimensions."""
        img = Image.new("RGB", (width, height), (100, 150, 200))
        img.save(path)
        return path

    def test_horizontal_output_dimensions(self, work_dir):
        src = self._make_test_image(
            os.path.join(work_dir, "src.png"), 2752, 1536
        )
        out = os.path.join(work_dir, "out.png")
        process_single_background(src, out, HORIZONTAL_SIZE)
        result = Image.open(out)
        assert result.size == HORIZONTAL_SIZE

    def test_vertical_output_dimensions(self, work_dir):
        src = self._make_test_image(
            os.path.join(work_dir, "src.png"), 1536, 2752
        )
        out = os.path.join(work_dir, "out.png")
        process_single_background(src, out, VERTICAL_SIZE)
        result = Image.open(out)
        assert result.size == VERTICAL_SIZE

    def test_output_is_rgb(self, work_dir):
        """Pipeline backgrounds must be RGB (no alpha channel)."""
        src = self._make_test_image(
            os.path.join(work_dir, "src.png"), 2752, 1536
        )
        out = os.path.join(work_dir, "out.png")
        process_single_background(src, out, HORIZONTAL_SIZE)
        result = Image.open(out)
        assert result.mode == "RGB"

    def test_source_content_preserved_no_watermark_patching(self, work_dir):
        """Pipeline no longer patches the corner — watermarks removed externally."""
        # Create image with a distinct red corner (simulating already-clean source)
        img = Image.new("RGB", (2752, 1536), (100, 150, 200))
        for x in range(2600, 2752):
            for y in range(1400, 1536):
                img.putpixel((x, y), (255, 0, 0))
        src = os.path.join(work_dir, "src.png")
        img.save(src)

        out = os.path.join(work_dir, "out.png")
        process_single_background(src, out, HORIZONTAL_SIZE)
        result = Image.open(out)

        # The red corner should survive (resized but not patched away)
        # LANCZOS may blend edge pixels, so check a pixel well inside the red zone
        corner_pixel = result.getpixel((result.width - 10, result.height - 10))
        assert corner_pixel[0] > 200, "Source content should be preserved, not patched"

    def test_output_file_created(self, work_dir):
        src = self._make_test_image(
            os.path.join(work_dir, "src.png"), 2752, 1536
        )
        out = os.path.join(work_dir, "out.png")
        process_single_background(src, out, HORIZONTAL_SIZE)
        assert os.path.exists(out)


class TestBackgroundUsesLanczosResampling:
    """Backgrounds must use LANCZOS resampling to avoid vertical seam artifacts.

    Nearest-neighbor at non-integer scale factors (e.g., 2752→1920 = 0.698x)
    creates uneven column widths — visible vertical stripes in smooth images.
    Backgrounds are illustrations (NOT pixel art), so they need LANCZOS.
    """

    @pytest.fixture
    def work_dir(self):
        d = tempfile.mkdtemp()
        yield d
        shutil.rmtree(d, ignore_errors=True)

    def _make_test_image(self, path, width, height):
        img = Image.new("RGB", (width, height), (100, 150, 200))
        img.save(path)
        return path

    def test_process_single_background_uses_lanczos(self, work_dir):
        """process_single_background must resize with LANCZOS, not NEAREST."""
        from unittest.mock import patch
        src = self._make_test_image(
            os.path.join(work_dir, "src.png"), 2752, 1536
        )
        out = os.path.join(work_dir, "out.png")

        resize_methods = []
        _original_resize = Image.Image.resize

        def _tracking_resize(self, size, resample=None, *args, **kwargs):
            resize_methods.append(resample)
            return _original_resize(self, size, resample, *args, **kwargs)

        with patch.object(Image.Image, "resize", _tracking_resize):
            process_single_background(src, out, HORIZONTAL_SIZE)

        assert any(r == Image.LANCZOS for r in resize_methods), (
            f"Expected LANCZOS for background resize, got: {resize_methods}"
        )
        assert not any(r == Image.NEAREST for r in resize_methods), (
            f"NEAREST must NOT be used for backgrounds: {resize_methods}"
        )

    def test_vertical_background_also_uses_lanczos(self, work_dir):
        """Vertical backgrounds must also use LANCZOS."""
        from unittest.mock import patch
        src = self._make_test_image(
            os.path.join(work_dir, "src.png"), 1536, 2752
        )
        out = os.path.join(work_dir, "out.png")

        resize_methods = []
        _original_resize = Image.Image.resize

        def _tracking_resize(self, size, resample=None, *args, **kwargs):
            resize_methods.append(resample)
            return _original_resize(self, size, resample, *args, **kwargs)

        with patch.object(Image.Image, "resize", _tracking_resize):
            process_single_background(src, out, VERTICAL_SIZE)

        assert any(r == Image.LANCZOS for r in resize_methods), (
            f"Expected LANCZOS for vertical background resize, got: {resize_methods}"
        )
        assert not any(r == Image.NEAREST for r in resize_methods), (
            f"NEAREST must NOT be used for vertical backgrounds: {resize_methods}"
        )


class TestSceneBuilderBackgroundResampling:
    """scene_builder.py must use LANCZOS for background layer resizing."""

    def test_load_background_layers_uses_lanczos_for_resize(self, tmp_path):
        """When a background needs resizing at load time, use LANCZOS."""
        from unittest.mock import patch

        bg_dir = tmp_path / "assets" / "backgrounds"
        bg_dir.mkdir(parents=True)

        # Background at a wrong size — forces resize at load time
        img = Image.new("RGB", (2800, 1600), (100, 150, 200))
        img.save(str(bg_dir / "test_location.png"))

        import src.video_assembler.scene_builder as sb
        original_assets_dir = sb.ASSETS_DIR
        sb.ASSETS_DIR = str(tmp_path / "assets")

        resize_methods = []
        _original_resize = Image.Image.resize

        def _tracking_resize(self, size, resample=None, *args, **kwargs):
            resize_methods.append(resample)
            return _original_resize(self, size, resample, *args, **kwargs)

        try:
            with patch.object(Image.Image, "resize", _tracking_resize):
                layers = sb.load_background_layers("test_location")
            assert len(layers) == 1
            assert layers[0].size == (sb.FRAME_WIDTH, sb.FRAME_HEIGHT)
            assert any(r == Image.LANCZOS for r in resize_methods), (
                f"Expected LANCZOS for background layer resize, got: {resize_methods}"
            )
            assert not any(r == Image.NEAREST for r in resize_methods), (
                f"NEAREST must NOT be used for background layers: {resize_methods}"
            )
        finally:
            sb.ASSETS_DIR = original_assets_dir


class TestCropDarkEdges:
    """Auto-crop of near-black rows from image top and bottom."""

    def test_no_crop_when_image_is_clean(self):
        """A uniformly bright image should not be cropped at all."""
        img = Image.new("RGB", (200, 100), (120, 120, 120))
        result = crop_dark_edges(img)
        assert result.size == (200, 100)

    def test_crops_dark_bottom_rows(self):
        """Dark rows at the bottom are removed."""
        import numpy as np
        arr = np.full((200, 300, 3), 120, dtype=np.uint8)
        # Paint the bottom 40 rows black
        arr[-40:, :, :] = 0
        img = Image.fromarray(arr)
        result = crop_dark_edges(img)
        assert result.size == (300, 160)

    def test_crops_dark_top_rows(self):
        """Dark rows at the top are removed."""
        import numpy as np
        arr = np.full((200, 300, 3), 120, dtype=np.uint8)
        # Paint the top 30 rows black
        arr[:30, :, :] = 0
        img = Image.fromarray(arr)
        result = crop_dark_edges(img)
        assert result.size == (300, 170)

    def test_crops_both_edges(self):
        """Dark rows at both top and bottom are removed."""
        import numpy as np
        arr = np.full((200, 300, 3), 120, dtype=np.uint8)
        arr[:20, :, :] = 0
        arr[-30:, :, :] = 0
        img = Image.fromarray(arr)
        result = crop_dark_edges(img)
        assert result.size == (300, 150)

    def test_preserves_width(self):
        """Cropping only affects height, never width."""
        import numpy as np
        arr = np.full((200, 400, 3), 120, dtype=np.uint8)
        arr[-50:, :, :] = 0
        img = Image.fromarray(arr)
        result = crop_dark_edges(img)
        assert result.width == 400

    def test_near_black_treated_as_dark(self):
        """Pixels with brightness just below the threshold are cropped."""
        import numpy as np
        arr = np.full((200, 300, 3), 120, dtype=np.uint8)
        # Bottom 40 rows at brightness 10 (below default threshold of 30)
        arr[-40:, :, :] = 10
        img = Image.fromarray(arr)
        result = crop_dark_edges(img)
        assert result.size == (300, 160)

    def test_custom_threshold(self):
        """A higher threshold crops more aggressively."""
        import numpy as np
        arr = np.full((200, 300, 3), 120, dtype=np.uint8)
        # Bottom 40 rows at brightness 50 — above default, below custom
        arr[-40:, :, :] = 50
        img = Image.fromarray(arr)
        # Default threshold (30) should NOT crop these
        result_default = crop_dark_edges(img, threshold=30)
        assert result_default.size == (300, 200)
        # Higher threshold (60) SHOULD crop them
        result_custom = crop_dark_edges(img, threshold=60)
        assert result_custom.size == (300, 160)
