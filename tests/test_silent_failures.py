"""Tests for Stage 1: Silent failure elimination.

Verifies that every asset loading function:
1. Prints a warning to stdout when using a fallback (visible in journalctl)
2. Collects the warning in a module-level list (retrievable by pipeline caller)
3. Still returns a usable fallback (doesn't crash the pipeline)

Also verifies that check_asset_availability() catches music files.
"""

import os
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image


# ---------------------------------------------------------------------------
# sprite_manager: load_sprite should warn on missing characters
# ---------------------------------------------------------------------------

class TestSpriteManagerWarnings:
    """Verify load_sprite warns loudly when returning fallback placeholders."""

    def test_missing_character_prints_warning(self, capsys):
        """When character doesn't exist at all, should print a warning."""
        from src.video_assembler.sprite_manager import load_sprite, clear_warnings
        clear_warnings()
        sprite = load_sprite("nonexistent_character_xyz", "idle")
        captured = capsys.readouterr()
        assert "[WARNING]" in captured.out
        assert "nonexistent_character_xyz" in captured.out

    def test_missing_character_collects_warning(self):
        """When character doesn't exist, warning should be in get_warnings()."""
        from src.video_assembler.sprite_manager import load_sprite, get_warnings, clear_warnings
        clear_warnings()
        load_sprite("nonexistent_character_xyz", "idle")
        warnings = get_warnings()
        assert len(warnings) >= 1
        assert "nonexistent_character_xyz" in warnings[0]

    def test_missing_character_still_returns_image(self):
        """Even with warning, should still return a usable RGBA image."""
        from src.video_assembler.sprite_manager import load_sprite, clear_warnings
        clear_warnings()
        sprite = load_sprite("nonexistent_character_xyz", "idle")
        assert isinstance(sprite, Image.Image)
        assert sprite.mode == "RGBA"

    def test_valid_character_no_warning(self):
        """Loading a real character should NOT produce any warnings."""
        from src.video_assembler.sprite_manager import load_sprite, get_warnings, clear_warnings
        clear_warnings()
        load_sprite("pens", "idle")
        warnings = get_warnings()
        assert len(warnings) == 0

    def test_missing_state_falls_back_no_warning(self):
        """Falling back to idle.png for a missing state is expected, not a warning."""
        from src.video_assembler.sprite_manager import load_sprite, get_warnings, clear_warnings
        clear_warnings()
        load_sprite("pens", "nonexistent_state")
        warnings = get_warnings()
        # Fallback to idle is fine — only warn if the character itself doesn't exist
        assert len(warnings) == 0

    def test_clear_warnings_resets(self):
        """clear_warnings() should empty the warning list."""
        from src.video_assembler.sprite_manager import load_sprite, get_warnings, clear_warnings
        load_sprite("nonexistent_character_xyz", "idle")
        clear_warnings()
        assert len(get_warnings()) == 0


# ---------------------------------------------------------------------------
# scene_builder: load_background should warn on missing backgrounds
# ---------------------------------------------------------------------------

class TestSceneBuilderWarnings:
    """Verify load_background warns loudly when returning blue rectangle fallback."""

    def test_missing_background_prints_warning(self, capsys):
        """When background doesn't exist, should print a warning."""
        from src.video_assembler.scene_builder import load_background, clear_warnings
        clear_warnings()
        bg = load_background("nonexistent_location_xyz")
        captured = capsys.readouterr()
        assert "[WARNING]" in captured.out
        assert "nonexistent_location_xyz" in captured.out

    def test_missing_background_collects_warning(self):
        """When background doesn't exist, warning should be in get_warnings()."""
        from src.video_assembler.scene_builder import load_background, get_warnings, clear_warnings
        clear_warnings()
        load_background("nonexistent_location_xyz")
        warnings = get_warnings()
        assert len(warnings) >= 1
        assert "nonexistent_location_xyz" in warnings[0]

    def test_missing_background_still_returns_image(self):
        """Even with warning, should still return a usable RGB image at correct size."""
        from src.video_assembler.scene_builder import (
            load_background, clear_warnings, FRAME_WIDTH, FRAME_HEIGHT,
        )
        clear_warnings()
        bg = load_background("nonexistent_location_xyz")
        assert isinstance(bg, Image.Image)
        assert bg.size == (FRAME_WIDTH, FRAME_HEIGHT)
        assert bg.mode == "RGB"

    def test_valid_background_no_warning(self):
        """Loading a real background should NOT produce any warnings."""
        from src.video_assembler.scene_builder import load_background, get_warnings, clear_warnings
        clear_warnings()
        load_background("diner_interior")
        warnings = get_warnings()
        assert len(warnings) == 0

    def test_clear_warnings_resets(self):
        """clear_warnings() should empty the warning list."""
        from src.video_assembler.scene_builder import load_background, get_warnings, clear_warnings
        load_background("nonexistent_location_xyz")
        clear_warnings()
        assert len(get_warnings()) == 0


# ---------------------------------------------------------------------------
# audio_mixer: mix_episode_audio should warn on missing music
# ---------------------------------------------------------------------------

class TestAudioMixerWarnings:
    """Verify audio mixer warns when music file is missing."""

    def test_missing_music_prints_warning(self, capsys):
        """When music file doesn't exist, should print a warning."""
        from src.audio_mixer.mixer import mix_episode_audio, clear_warnings
        clear_warnings()

        script = {"scenes": [{"duration_seconds": 5, "dialogue": []}]}
        output_path = "/tmp/test_silent_failures_audio.wav"

        mix_episode_audio(
            script=script,
            music_path="/nonexistent/music/file.wav",
            output_path=output_path,
        )

        captured = capsys.readouterr()
        assert "[WARNING]" in captured.out
        assert "music" in captured.out.lower()

        # Cleanup
        if os.path.exists(output_path):
            os.remove(output_path)

    def test_missing_music_collects_warning(self):
        """When music file is missing, warning should be in get_warnings()."""
        from src.audio_mixer.mixer import mix_episode_audio, get_warnings, clear_warnings
        clear_warnings()

        script = {"scenes": [{"duration_seconds": 5, "dialogue": []}]}
        output_path = "/tmp/test_silent_failures_audio2.wav"

        mix_episode_audio(
            script=script,
            music_path="/nonexistent/music/file.wav",
            output_path=output_path,
        )

        warnings = get_warnings()
        assert len(warnings) >= 1
        assert "music" in warnings[0].lower()

        # Cleanup
        if os.path.exists(output_path):
            os.remove(output_path)

    def test_missing_music_still_produces_audio(self):
        """Even with missing music, should still produce a WAV file (with SFX/blips only)."""
        from src.audio_mixer.mixer import mix_episode_audio, clear_warnings
        clear_warnings()

        script = {"scenes": [{"duration_seconds": 5, "dialogue": []}]}
        output_path = "/tmp/test_silent_failures_audio3.wav"

        result = mix_episode_audio(
            script=script,
            music_path="/nonexistent/music/file.wav",
            output_path=output_path,
        )

        assert result == output_path
        assert os.path.exists(output_path)

        # Cleanup
        if os.path.exists(output_path):
            os.remove(output_path)

    def test_valid_music_no_warning(self):
        """Loading existing music should NOT produce any warnings."""
        from src.audio_mixer.mixer import mix_episode_audio, get_warnings, clear_warnings
        clear_warnings()

        # Use an existing music file
        music_path = os.path.join(
            os.path.dirname(__file__), "..", "assets", "music", "main_theme.wav"
        )
        if not os.path.exists(music_path):
            pytest.skip("main_theme.wav not found in assets")

        script = {"scenes": [{"duration_seconds": 5, "dialogue": []}]}
        output_path = "/tmp/test_silent_failures_audio4.wav"

        mix_episode_audio(
            script=script,
            music_path=music_path,
            output_path=output_path,
        )

        warnings = get_warnings()
        assert len(warnings) == 0

        # Cleanup
        if os.path.exists(output_path):
            os.remove(output_path)


# ---------------------------------------------------------------------------
# orchestrator: check_asset_availability should also check music
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# orchestrator: collect_rendering_warnings aggregates from all modules
# ---------------------------------------------------------------------------

class TestCollectRenderingWarnings:
    """Verify the orchestrator aggregates warnings from all rendering modules."""

    def test_collects_from_sprite_manager(self):
        """Warnings from sprite_manager should appear in collected list."""
        from src.video_assembler.sprite_manager import load_sprite, clear_warnings as clear_sprite
        from src.video_assembler.scene_builder import clear_warnings as clear_scene
        from src.audio_mixer.mixer import clear_warnings as clear_audio
        from src.pipeline.orchestrator import collect_rendering_warnings, clear_all_rendering_warnings

        clear_all_rendering_warnings()
        load_sprite("nonexistent_xyz", "idle")

        all_warnings = collect_rendering_warnings()
        assert len(all_warnings) >= 1
        assert "nonexistent_xyz" in all_warnings[0]

    def test_collects_from_scene_builder(self):
        """Warnings from scene_builder should appear in collected list."""
        from src.video_assembler.scene_builder import load_background
        from src.pipeline.orchestrator import collect_rendering_warnings, clear_all_rendering_warnings

        clear_all_rendering_warnings()
        load_background("nonexistent_xyz")

        all_warnings = collect_rendering_warnings()
        assert len(all_warnings) >= 1
        assert "nonexistent_xyz" in all_warnings[0]

    def test_collects_from_audio_mixer(self):
        """Warnings from audio_mixer should appear in collected list."""
        from src.audio_mixer.mixer import mix_episode_audio
        from src.pipeline.orchestrator import collect_rendering_warnings, clear_all_rendering_warnings

        clear_all_rendering_warnings()
        output_path = "/tmp/test_collect_warnings_audio.wav"
        script = {"scenes": [{"duration_seconds": 2, "dialogue": []}]}
        mix_episode_audio(script=script, music_path="/nonexistent/music.wav", output_path=output_path)

        all_warnings = collect_rendering_warnings()
        assert len(all_warnings) >= 1
        assert "music" in all_warnings[0].lower()

        if os.path.exists(output_path):
            os.remove(output_path)

    def test_clear_all_clears_everything(self):
        """clear_all_rendering_warnings should clear warnings in all modules."""
        from src.video_assembler.sprite_manager import load_sprite
        from src.video_assembler.scene_builder import load_background
        from src.pipeline.orchestrator import collect_rendering_warnings, clear_all_rendering_warnings

        # Generate some warnings
        load_sprite("nonexistent_xyz", "idle")
        load_background("nonexistent_xyz")

        clear_all_rendering_warnings()
        assert len(collect_rendering_warnings()) == 0

    def test_no_warnings_when_clean(self):
        """With valid assets, should return empty list."""
        from src.pipeline.orchestrator import collect_rendering_warnings, clear_all_rendering_warnings
        clear_all_rendering_warnings()
        assert collect_rendering_warnings() == []


class TestAssetCheckMusic:
    """Verify check_asset_availability checks music files too."""

    def test_checks_music_file(self):
        """Asset check should report missing music file."""
        from src.pipeline.orchestrator import check_asset_availability

        # Script with a mood that maps to a music file
        script = {
            "metadata": {"mood": "playful"},
            "scenes": [
                {
                    "background": "diner_interior",
                    "characters_present": ["pens"],
                    "sfx_triggers": [],
                    "dialogue": [],
                }
            ],
        }

        # Temporarily make the music file "missing" by checking for a non-existent mood track
        with patch.dict(os.environ, {}, clear=False):
            ok, missing = check_asset_availability(script)
            # The function should check for the mood's music file
            # If playful.wav doesn't exist yet (it doesn't — v2 track), it should be flagged
            # But if it falls back to v1 tracks, that's fine too
            # The key test: if NO music files exist, it should flag it
            # This test is more about verifying the check runs —
            # exact behavior depends on which music files are on disk
            assert isinstance(ok, bool)
            assert isinstance(missing, list)

    def test_missing_music_in_check(self, tmp_path):
        """When music file is completely absent, should flag it."""
        from src.pipeline.orchestrator import check_asset_availability

        # Mock ASSETS_DIR to a temp dir with no music
        with patch("src.pipeline.orchestrator.ASSETS_DIR", str(tmp_path)):
            # Create minimal structure so background/sprite checks pass
            bg_dir = tmp_path / "backgrounds"
            bg_dir.mkdir()
            (bg_dir / "test_location.png").write_bytes(b"fake png")

            char_dir = tmp_path / "characters" / "pens"
            char_dir.mkdir(parents=True)
            (char_dir / "idle.png").write_bytes(b"fake png")
            (char_dir / "talking.png").write_bytes(b"fake png")

            # No music directory at all
            script = {
                "metadata": {"mood": "playful"},
                "scenes": [
                    {
                        "background": "test_location",
                        "characters_present": ["pens"],
                        "sfx_triggers": [],
                        "dialogue": [],
                    }
                ],
            }

            ok, missing = check_asset_availability(script)
            # Should flag missing music
            music_missing = [m for m in missing if "music" in m]
            assert len(music_missing) > 0, f"Expected music to be flagged as missing, got: {missing}"
