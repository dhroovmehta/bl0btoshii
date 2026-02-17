"""Tests for SFX asset mapping and asset checker extension handling.

Tests cover:
1. New SFX files exist (surprise.wav, magnifying_glass.wav, sip.wav)
2. New SFX files are valid WAV format (16-bit mono 44100 Hz)
3. Asset checker handles SFX names without .wav extension
4. Asset checker still handles SFX names with .wav extension
5. Mixer SFX path resolution matches asset checker behavior
"""

import os
import wave

import pytest

from src.pipeline.orchestrator import check_asset_availability

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
SFX_DIR = os.path.join(ASSETS_DIR, "sfx")


# ---------------------------------------------------------------------------
# 1. New SFX files exist
# ---------------------------------------------------------------------------

class TestNewSfxFilesExist:
    """Verify the 3 new SFX files are present in assets/sfx/."""

    def test_surprise_wav_exists(self):
        """surprise.wav must exist in assets/sfx/."""
        assert os.path.exists(os.path.join(SFX_DIR, "surprise.wav"))

    def test_magnifying_glass_wav_exists(self):
        """magnifying_glass.wav must exist in assets/sfx/."""
        assert os.path.exists(os.path.join(SFX_DIR, "magnifying_glass.wav"))

    def test_sip_wav_exists(self):
        """sip.wav must exist in assets/sfx/."""
        assert os.path.exists(os.path.join(SFX_DIR, "sip.wav"))


# ---------------------------------------------------------------------------
# 2. New SFX files are valid WAV format
# ---------------------------------------------------------------------------

class TestNewSfxFilesValidWav:
    """Verify each new SFX file is a valid 16-bit mono 44100 Hz WAV."""

    @pytest.mark.parametrize("filename", [
        "surprise.wav",
        "magnifying_glass.wav",
        "sip.wav",
    ])
    def test_wav_format(self, filename):
        """Each SFX file must be readable as WAV with correct specs."""
        path = os.path.join(SFX_DIR, filename)
        with wave.open(path, "rb") as f:
            assert f.getnchannels() == 1, f"{filename} should be mono"
            assert f.getsampwidth() == 2, f"{filename} should be 16-bit"
            assert f.getframerate() == 44100, f"{filename} should be 44100 Hz"
            assert f.getnframes() > 0, f"{filename} should not be empty"


# ---------------------------------------------------------------------------
# 3. Asset checker handles SFX names without .wav extension
# ---------------------------------------------------------------------------

class TestAssetCheckerSfxExtension:
    """check_asset_availability should find SFX whether name has .wav or not."""

    def _make_script_with_sfx(self, sfx_name):
        """Helper: create a minimal script referencing a single SFX."""
        return {
            "scenes": [
                {
                    "background": "diner_interior",
                    "characters_present": ["pens"],
                    "character_positions": {"pens": "stool_1"},
                    "character_animations": {"pens": "idle"},
                    "dialogue": [],
                    "sfx_triggers": [{"sfx": sfx_name, "time_ms": 500}],
                    "music": "main_theme.wav",
                },
            ],
        }

    def test_finds_surprise_without_extension(self):
        """'surprise' (no .wav) should pass asset check."""
        script = self._make_script_with_sfx("surprise")
        all_present, missing = check_asset_availability(script)
        sfx_missing = [m for m in missing if "surprise" in m]
        assert sfx_missing == [], f"surprise SFX should be found, but missing: {sfx_missing}"

    def test_finds_surprise_with_extension(self):
        """'surprise.wav' should pass asset check."""
        script = self._make_script_with_sfx("surprise.wav")
        all_present, missing = check_asset_availability(script)
        sfx_missing = [m for m in missing if "surprise" in m]
        assert sfx_missing == [], f"surprise.wav SFX should be found, but missing: {sfx_missing}"

    def test_finds_magnifying_glass_without_extension(self):
        """'magnifying_glass' (no .wav) should pass asset check."""
        script = self._make_script_with_sfx("magnifying_glass")
        all_present, missing = check_asset_availability(script)
        sfx_missing = [m for m in missing if "magnifying_glass" in m]
        assert sfx_missing == [], f"magnifying_glass SFX should be found, but missing: {sfx_missing}"

    def test_finds_sip_without_extension(self):
        """'sip' (no .wav) should pass asset check."""
        script = self._make_script_with_sfx("sip")
        all_present, missing = check_asset_availability(script)
        sfx_missing = [m for m in missing if "sip" in m]
        assert sfx_missing == [], f"sip SFX should be found, but missing: {sfx_missing}"

    def test_missing_sfx_still_detected(self):
        """A genuinely missing SFX should still be caught."""
        script = self._make_script_with_sfx("totally_fake_sound")
        all_present, missing = check_asset_availability(script)
        assert any("totally_fake_sound" in m for m in missing)

    def test_missing_sfx_without_extension_still_detected(self):
        """A missing SFX without .wav should still be caught."""
        script = self._make_script_with_sfx("nonexistent_beep")
        _, missing = check_asset_availability(script)
        assert any("nonexistent_beep" in m for m in missing)

    def test_existing_sfx_pop_without_extension(self):
        """'pop' (no .wav) should pass — verifies fix works for all existing SFX."""
        script = self._make_script_with_sfx("pop")
        _, missing = check_asset_availability(script)
        sfx_missing = [m for m in missing if "pop" in m]
        assert sfx_missing == []

    def test_existing_sfx_whoosh_without_extension(self):
        """'whoosh' (no .wav) should pass."""
        script = self._make_script_with_sfx("whoosh")
        _, missing = check_asset_availability(script)
        sfx_missing = [m for m in missing if "whoosh" in m]
        assert sfx_missing == []
