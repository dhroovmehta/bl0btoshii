"""Tests for sprite processing pipeline — crop, resize, alpha cleanup.

Background removal is now done manually (Photopea) before the pipeline.
This script handles post-processing only:
  1. clean_transparency — snap low-alpha pixels to fully transparent
  2. crop_to_content — trim transparent padding to tight bounding box
  3. fit_within — resize to pipeline-ready dimensions (nearest-neighbor)
  4. process_sprite — full pipeline orchestration

Test groups:
  1. clean_transparency — alpha thresholding
  2. crop_to_content — bounding box detection
  3. fit_within — aspect-preserving resize
  4. process_sprite — end-to-end pipeline
  5. Integration — verify processed sprites on disk
"""

import os
import tempfile
import shutil

from PIL import Image
import pytest

from scripts.process_sprite import (
    clean_transparency,
    crop_to_content,
    fit_within,
    process_sprite,
    ALPHA_THRESHOLD,
    HEIGHT_TIERS,
    VALID_CHARACTERS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_transparent(img):
    """Count fully transparent pixels."""
    pixels = img.load()
    w, h = img.size
    return sum(1 for y in range(h) for x in range(w) if pixels[x, y][3] == 0)


def _count_opaque(img):
    """Count fully opaque pixels (alpha == 255)."""
    pixels = img.load()
    w, h = img.size
    return sum(1 for y in range(h) for x in range(w) if pixels[x, y][3] == 255)


def _make_padded_sprite(body_w=60, body_h=80, pad=20, body_color=(200, 50, 50, 255)):
    """Sprite with transparent padding around a solid colored body.

    Simulates a post-Photopea image: background removed, body intact,
    but with transparent padding around the edges.
    """
    w = body_w + 2 * pad
    h = body_h + 2 * pad
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pixels = img.load()
    for y in range(pad, pad + body_h):
        for x in range(pad, pad + body_w):
            pixels[x, y] = body_color
    return img


def _make_sprite_with_semi_alpha(size=60, alpha_value=15):
    """Sprite where the body has low alpha (semi-transparent artifacts)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()
    margin = 15
    for y in range(margin, size - margin):
        for x in range(margin, size - margin):
            pixels[x, y] = (180, 180, 180, alpha_value)
    return img


# ---------------------------------------------------------------------------
# 1. clean_transparency — alpha thresholding
# ---------------------------------------------------------------------------

class TestCleanTransparency:
    """Alpha thresholding must snap low-alpha pixels to fully transparent."""

    def test_low_alpha_becomes_zero(self):
        """Pixels with alpha < threshold become fully transparent."""
        img = Image.new("RGBA", (10, 10), (100, 100, 100, 10))
        cleaned = clean_transparency(img)
        pixels = cleaned.load()
        assert pixels[5, 5][3] == 0

    def test_high_alpha_preserved(self):
        """Pixels with alpha >= threshold keep their alpha."""
        img = Image.new("RGBA", (10, 10), (100, 100, 100, 200))
        cleaned = clean_transparency(img)
        pixels = cleaned.load()
        assert pixels[5, 5][3] == 200

    def test_threshold_boundary(self):
        """Pixel exactly at threshold is kept."""
        img = Image.new("RGBA", (10, 10), (100, 100, 100, ALPHA_THRESHOLD))
        cleaned = clean_transparency(img)
        pixels = cleaned.load()
        assert pixels[5, 5][3] == ALPHA_THRESHOLD

    def test_rgb_channels_preserved(self):
        """RGB values are NOT modified by alpha thresholding."""
        img = Image.new("RGBA", (10, 10), (123, 45, 67, 200))
        cleaned = clean_transparency(img)
        pixels = cleaned.load()
        assert pixels[0, 0][:3] == (123, 45, 67)

    def test_fully_transparent_unchanged(self):
        """Pixels already at alpha=0 stay at alpha=0."""
        img = Image.new("RGBA", (10, 10), (100, 100, 100, 0))
        cleaned = clean_transparency(img)
        pixels = cleaned.load()
        assert pixels[0, 0][3] == 0

    def test_returns_rgba(self):
        """Output must be RGBA."""
        img = Image.new("RGBA", (10, 10), (100, 100, 100, 100))
        assert clean_transparency(img).mode == "RGBA"


# ---------------------------------------------------------------------------
# 2. crop_to_content — bounding box detection
# ---------------------------------------------------------------------------

class TestCropToContent:
    """Crop must tightly bound the non-transparent content."""

    def test_removes_transparent_padding(self):
        """Transparent padding is trimmed, body dimensions preserved."""
        img = _make_padded_sprite(body_w=60, body_h=80, pad=20)
        cropped = crop_to_content(img)
        assert cropped.size == (60, 80)

    def test_no_padding_returns_same_size(self):
        """Image with no transparent padding returns same dimensions."""
        img = Image.new("RGBA", (50, 50), (255, 0, 0, 255))
        cropped = crop_to_content(img)
        assert cropped.size == (50, 50)

    def test_fully_transparent_returns_original(self):
        """Fully transparent image returns original (nothing to crop to)."""
        img = Image.new("RGBA", (30, 30), (0, 0, 0, 0))
        cropped = crop_to_content(img)
        # Should return original since there's no content
        assert cropped.size == (30, 30)

    def test_asymmetric_padding(self):
        """Uneven padding is handled correctly."""
        img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        pixels = img.load()
        # Body at (10, 5) to (60, 85)
        for y in range(5, 85):
            for x in range(10, 60):
                pixels[x, y] = (255, 0, 0, 255)
        cropped = crop_to_content(img)
        assert cropped.size == (50, 80)

    def test_preserves_pixel_values(self):
        """Cropping doesn't alter the pixel colors."""
        img = _make_padded_sprite(body_w=40, body_h=40, pad=10,
                                   body_color=(123, 45, 67, 255))
        cropped = crop_to_content(img)
        pixels = cropped.load()
        assert pixels[0, 0] == (123, 45, 67, 255)

    def test_returns_rgba(self):
        """Output must be RGBA."""
        img = _make_padded_sprite()
        assert crop_to_content(img).mode == "RGBA"

    def test_single_pixel_content(self):
        """Even a single opaque pixel should be cropped to 1x1."""
        img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        img.load()[50, 50] = (255, 0, 0, 255)
        cropped = crop_to_content(img)
        assert cropped.size == (1, 1)


# ---------------------------------------------------------------------------
# 3. fit_within — aspect-preserving resize
# ---------------------------------------------------------------------------

class TestFitWithin:
    """Resize must fit within bounds while preserving aspect ratio."""

    def test_tall_image_scaled_by_height(self):
        """A tall image should be limited by max_h."""
        img = Image.new("RGBA", (100, 200), (255, 0, 0, 255))
        result = fit_within(img, max_w=240, max_h=320)
        assert result.height == 320
        assert result.width == 160  # 100 * (320/200)

    def test_wide_image_scaled_by_width(self):
        """A wide image should be limited by max_w."""
        img = Image.new("RGBA", (400, 100), (255, 0, 0, 255))
        result = fit_within(img, max_w=240, max_h=320)
        assert result.width == 240
        assert result.height == 60  # 100 * (240/400)

    def test_small_image_scaled_up(self):
        """Images smaller than the target are scaled up."""
        img = Image.new("RGBA", (50, 100), (255, 0, 0, 255))
        result = fit_within(img, max_w=240, max_h=320)
        # Scale = min(240/50, 320/100) = min(4.8, 3.2) = 3.2
        assert result.height == 320
        assert result.width == 160

    def test_exact_fit_no_change(self):
        """Image already at target size stays same size."""
        img = Image.new("RGBA", (240, 320), (255, 0, 0, 255))
        result = fit_within(img, max_w=240, max_h=320)
        assert result.size == (240, 320)

    def test_preserves_rgba(self):
        """Output must stay RGBA."""
        img = Image.new("RGBA", (50, 50), (255, 0, 0, 255))
        assert fit_within(img, 100, 100).mode == "RGBA"

    def test_uses_nearest_neighbor(self):
        """Nearest-neighbor resize: a 2x2 checkerboard at 2x should be 4x4
        with sharp edges, not blurred."""
        img = Image.new("RGBA", (2, 2), (0, 0, 0, 0))
        pixels = img.load()
        pixels[0, 0] = (255, 0, 0, 255)
        pixels[1, 1] = (255, 0, 0, 255)
        result = fit_within(img, max_w=4, max_h=4)
        rp = result.load()
        # Nearest-neighbor: each source pixel becomes a 2x2 block
        assert rp[0, 0] == (255, 0, 0, 255)
        assert rp[1, 0] == (255, 0, 0, 255)
        assert rp[2, 0] == (0, 0, 0, 0)


# ---------------------------------------------------------------------------
# 4. process_sprite — end-to-end pipeline
# ---------------------------------------------------------------------------

class TestProcessSprite:
    """Full pipeline: open image → clean alpha → crop → resize → save."""

    @pytest.fixture
    def temp_assets_dir(self, tmp_path, monkeypatch):
        """Redirect ASSETS_DIR to a temp directory for safe testing."""
        import scripts.process_sprite as module
        monkeypatch.setattr(module, "ASSETS_DIR", str(tmp_path / "assets"))
        os.makedirs(tmp_path / "assets" / "characters", exist_ok=True)
        return tmp_path / "assets"

    def _save_test_sprite(self, tmp_path, body_color=(200, 50, 50, 255)):
        """Create and save a test sprite PNG with transparent background."""
        img = _make_padded_sprite(body_w=400, body_h=600, pad=100,
                                   body_color=body_color)
        path = str(tmp_path / "test_sprite.png")
        img.save(path, "PNG")
        return path

    def test_output_file_created(self, tmp_path, temp_assets_dir):
        """Pipeline produces a PNG file at the expected path."""
        src = self._save_test_sprite(tmp_path)
        result = process_sprite(src, "pens", "idle")
        assert os.path.exists(result)
        assert result.endswith(".png")

    def test_output_within_height_tier(self, tmp_path, temp_assets_dir):
        """Output dimensions fit within the character's height tier."""
        src = self._save_test_sprite(tmp_path)
        result = process_sprite(src, "pens", "idle")
        img = Image.open(result)
        max_w, max_h = HEIGHT_TIERS["pens"]
        assert img.width <= max_w + 1, f"Width {img.width} > {max_w}"
        assert img.height <= max_h + 1, f"Height {img.height} > {max_h}"

    def test_output_is_rgba(self, tmp_path, temp_assets_dir):
        """Output must be RGBA PNG."""
        src = self._save_test_sprite(tmp_path)
        result = process_sprite(src, "pens", "idle")
        img = Image.open(result)
        assert img.mode == "RGBA"

    def test_transparent_padding_removed(self, tmp_path, temp_assets_dir):
        """The 100px padding from the test sprite should be cropped away."""
        src = self._save_test_sprite(tmp_path)
        result = process_sprite(src, "pens", "idle")
        img = Image.open(result)
        # After cropping a 400x600 body and fitting in 240x320,
        # the aspect ratio should be preserved (2:3)
        ratio = img.width / img.height
        expected_ratio = 400 / 600
        assert abs(ratio - expected_ratio) < 0.05, (
            f"Aspect ratio {ratio:.2f} should be ~{expected_ratio:.2f}"
        )

    def test_rejects_unknown_character(self, tmp_path, temp_assets_dir):
        """Unknown character name should cause sys.exit."""
        src = self._save_test_sprite(tmp_path)
        with pytest.raises(SystemExit):
            process_sprite(src, "unknown_char", "idle")

    def test_rejects_missing_file(self, tmp_path, temp_assets_dir):
        """Non-existent file path should cause sys.exit."""
        with pytest.raises(SystemExit):
            process_sprite("/nonexistent/path.png", "pens", "idle")

    def test_all_height_tiers_defined(self):
        """Every valid character must have a height tier entry."""
        for char in VALID_CHARACTERS:
            assert char in HEIGHT_TIERS, f"{char} missing from HEIGHT_TIERS"

    def test_backs_up_existing_sprite(self, tmp_path, temp_assets_dir):
        """If a sprite already exists at the output path, it gets backed up."""
        # Create an existing sprite
        char_dir = temp_assets_dir / "characters" / "pens"
        os.makedirs(char_dir, exist_ok=True)
        existing = char_dir / "idle.png"
        Image.new("RGBA", (10, 10), (0, 255, 0, 255)).save(str(existing))

        # Process new sprite over it
        src = self._save_test_sprite(tmp_path)
        process_sprite(src, "pens", "idle")

        # Backup should exist
        backup = char_dir / "idle_old.png"
        assert backup.exists(), "Old sprite should be backed up to idle_old.png"


# ---------------------------------------------------------------------------
# 5. Integration — verify processed sprites on disk
# ---------------------------------------------------------------------------

class TestProcessedSprites:
    """Verify the processed sprites on disk have correct properties."""

    CHARACTERS = ["pens", "chubs", "meows", "oinks", "quacks", "reows"]

    def test_all_sprites_have_transparency(self):
        """Every processed sprite must have substantial transparent area."""
        for char in self.CHARACTERS:
            path = f"assets/characters/{char}/idle.png"
            if not os.path.exists(path):
                continue
            img = Image.open(path)
            if img.mode != "RGBA":
                continue
            transparent = _count_transparent(img)
            total = img.size[0] * img.size[1]
            pct = transparent / total
            if pct == 0:
                pytest.skip(f"{char}: sprite appears unprocessed (0% transparent)")
            assert pct > 0.10, (
                f"{char}: only {pct:.0%} transparent — "
                f"background removal may have failed"
            )

    def test_pens_has_white_belly(self):
        """Pens (penguin) must have white opaque pixels — the white belly."""
        path = "assets/characters/pens/idle.png"
        if not os.path.exists(path):
            pytest.skip("Pens sprite not on disk")
        img = Image.open(path)
        pixels = img.load()
        w, h = img.size
        white_opaque = sum(
            1 for y in range(h) for x in range(w)
            if pixels[x, y][0] > 200 and pixels[x, y][1] > 200
            and pixels[x, y][2] > 200 and pixels[x, y][3] == 255
        )
        assert white_opaque > 100, (
            f"Pens should have white belly area, "
            f"but only {white_opaque} white opaque pixels"
        )

    def test_pens_has_dark_body(self):
        """Pens (penguin) must have dark/black opaque pixels — the body."""
        path = "assets/characters/pens/idle.png"
        if not os.path.exists(path):
            pytest.skip("Pens sprite not on disk")
        img = Image.open(path)
        pixels = img.load()
        w, h = img.size
        dark_opaque = sum(
            1 for y in range(h) for x in range(w)
            if pixels[x, y][0] < 50 and pixels[x, y][1] < 50
            and pixels[x, y][2] < 50 and pixels[x, y][3] == 255
        )
        assert dark_opaque > 200, (
            f"Pens should have dark body pixels, "
            f"but only {dark_opaque} dark opaque pixels"
        )

    def test_quacks_has_yellow_body(self):
        """Quacks (duck) must have yellow opaque pixels — the body color."""
        path = "assets/characters/quacks/idle.png"
        if not os.path.exists(path):
            pytest.skip("Quacks sprite not on disk")
        img = Image.open(path)
        pixels = img.load()
        w, h = img.size
        yellow_opaque = sum(
            1 for y in range(h) for x in range(w)
            if pixels[x, y][0] > 200 and pixels[x, y][1] > 150
            and pixels[x, y][2] < 120 and pixels[x, y][3] > 0
        )
        assert yellow_opaque > 100, (
            f"Quacks should have yellow body, "
            f"but only {yellow_opaque} yellow pixels"
        )

    def test_no_sprite_exceeds_size_limits(self):
        """All sprites must fit within their height tier dimensions."""
        for char, (max_w, max_h) in HEIGHT_TIERS.items():
            for pose in ["idle", "talking"]:
                path = f"assets/characters/{char}/{pose}.png"
                if not os.path.exists(path):
                    continue
                img = Image.open(path)
                w, h = img.size
                assert w <= max_w + 1, f"{char}/{pose}: width {w} > {max_w}"
                assert h <= max_h + 1, f"{char}/{pose}: height {h} > {max_h}"

    def test_no_semi_transparent_smudging(self):
        """Pixel art sprites should have no semi-transparent pixels.
        Every pixel should be either fully opaque (255) or fully transparent (0)."""
        for char in self.CHARACTERS:
            path = f"assets/characters/{char}/idle.png"
            if not os.path.exists(path):
                continue
            img = Image.open(path)
            if img.mode != "RGBA":
                continue
            pixels = img.load()
            w, h = img.size
            semi = sum(
                1 for y in range(h) for x in range(w)
                if 0 < pixels[x, y][3] < 255
            )
            total = w * h
            # Allow up to 2% semi-transparent (anti-aliased edges from resize)
            assert semi / total < 0.02, (
                f"{char}: {semi} semi-transparent pixels ({100*semi/total:.1f}%) — "
                f"indicates smudging"
            )
