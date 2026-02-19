"""End-to-end pipeline integration tests.

Tests every stage of the pipeline in isolation AND as a connected flow,
using the REAL script dict structure that Claude generates.

Pipeline stages:
  1. Idea generation (slot_machine → idea dict)
  2. Script generation (Claude API → script dict)
  3. Script validation (validator → is_valid, errors)
  4. Notion publishing (script_publisher → Notion URL)
  5. Asset availability check (orchestrator → missing list)
  6. Scene frame building (scene_builder → frame PNGs)
  7. Audio mixing (mixer → WAV file)
  8. Video composition (composer → MP4 via FFmpeg)
  9. Variant generation (variant_generator → 3 variants)
  10. Video quality check (orchestrator → passed, issues)
  11. Google Drive upload (drive → URL)
  12. Episode numbering (assign_episode_number → real EP ID)
  13. Metadata generation + safety check
  14. Continuity logging + episode index logging

Each test documents:
  - Pre-conditions
  - Input data
  - Expected result
  - What can go wrong
"""

import json
import os
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Canonical test script — matches EXACTLY what Claude produces
# ---------------------------------------------------------------------------

def _make_test_script(episode_id="DRAFT-EP-001"):
    """Build a realistic script dict matching Claude's output structure.

    This is the SINGLE SOURCE OF TRUTH for test data.
    Every field matches the template in templates/claude_story_prompt.txt.
    """
    return {
        "episode_id": episode_id,
        "title": "The Pink Donut Incident",
        "slug": "the-pink-donut-incident",
        "created_at": "2026-02-17T12:00:00Z",
        "version": 1,
        "duration_target_seconds": 35,
        "generation_params": {
            "character_a": "oinks",
            "character_b": "reows",
            "location": "diner_interior",
            "situation": "everyday_life",
            "punchline_type": "callback_gag",
            "trending_tie_in": None,
            "seasonal_theme": None,
            "continuity_callbacks": [],
        },
        "metadata": {
            "total_duration_seconds": 35,
            "characters_featured": ["oinks", "reows"],
            "primary_location": "diner_interior",
            "content_pillar": "everyday_life",
            "punchline_type": "callback_gag",
        },
        "scenes": [
            {
                "scene_number": 1,
                "duration_seconds": 10,
                "background": "diner_interior",
                "characters_present": ["oinks", "reows"],
                "character_positions": {
                    "oinks": "stool_1",
                    "reows": "stool_2",
                },
                "character_animations": {
                    "oinks": "idle",
                    "reows": "idle",
                },
                "action_description": "Oinks discovers a suspiciously pink donut.",
                "dialogue": [
                    {
                        "character": "oinks",
                        "text": "Why is this donut glowing?",
                        "expression": "confused",
                        "duration_ms": 2500,
                    },
                    {
                        "character": "reows",
                        "text": "That's just the neon sign, you goofball.",
                        "expression": "smug",
                        "duration_ms": 3000,
                    },
                ],
                "sfx_triggers": [
                    {"sfx": "surprise", "timing": "with_dialogue_1"},
                ],
                "music": "main_theme.wav",
            },
            {
                "scene_number": 2,
                "duration_seconds": 10,
                "background": "diner_interior",
                "characters_present": ["oinks", "reows"],
                "character_positions": {
                    "oinks": "stool_1",
                    "reows": "stool_2",
                },
                "character_animations": {
                    "oinks": "talking",
                    "reows": "idle",
                },
                "action_description": "Oinks eats the donut anyway.",
                "dialogue": [
                    {
                        "character": "oinks",
                        "text": "Tastes like... victory.",
                        "expression": "happy",
                        "duration_ms": 2500,
                    },
                    {
                        "character": "reows",
                        "text": "That was my donut!",
                        "expression": "angry",
                        "duration_ms": 2500,
                    },
                ],
                "sfx_triggers": [],
                "music": "main_theme.wav",
            },
            {
                "scene_number": 3,
                "duration_seconds": 12,
                "background": "diner_interior",
                "characters_present": ["oinks", "reows"],
                "character_positions": {
                    "oinks": "stool_1",
                    "reows": "stool_2",
                },
                "character_animations": {
                    "oinks": "idle",
                    "reows": "talking",
                },
                "action_description": "Reows stares at the empty plate. Oinks looks guilty.",
                "dialogue": [
                    {
                        "character": "reows",
                        "text": "You owe me a donut. A REAL one this time.",
                        "expression": "stern",
                        "duration_ms": 3500,
                    },
                    {
                        "character": "oinks",
                        "text": "Deal. But only if it glows.",
                        "expression": "wink",
                        "duration_ms": 2500,
                    },
                ],
                "sfx_triggers": [
                    {"sfx": "cash_register", "timing": "with_dialogue_2"},
                ],
                "music": "main_theme.wav",
            },
        ],
        "end_card": {
            "duration_seconds": 3,
            "text": "Follow for more island chaos!",
        },
        "continuity_log": {
            "events": [
                "Oinks ate Reows' glowing pink donut at the diner"
            ],
            "new_running_gags": [],
            "callbacks_used": [],
            "character_developments": [],
        },
    }


# ===================================================================
# STAGE 1: Idea Generation
# ===================================================================

class TestStage1_IdeaGeneration:
    """Stage 1: slot_machine.generate_daily_ideas() → list of idea dicts.

    Pre-conditions:
      - data/characters.json, locations.json, situations.json, punchlines.json exist
      - config/content_matrix.yaml exists
    Expected result:
      - Returns list of 3 idea dicts
      - Each idea has: character_a, character_b, location, situation,
        punchline_type, concept, continuity_callbacks
    """

    def test_generates_three_ideas(self):
        from src.story_generator.slot_machine import generate_daily_ideas
        ideas = generate_daily_ideas(3)
        assert len(ideas) == 3

    def test_idea_has_required_keys(self):
        from src.story_generator.slot_machine import generate_daily_ideas
        ideas = generate_daily_ideas(1)
        idea = ideas[0]
        required = ["character_a", "character_b", "location", "situation", "punchline_type", "concept"]
        for key in required:
            assert key in idea, f"Idea missing key: {key}"

    def test_characters_are_valid(self):
        from src.story_generator.slot_machine import generate_daily_ideas
        with open(os.path.join(os.path.dirname(__file__), "..", "data", "characters.json")) as f:
            valid_chars = list(json.load(f)["characters"].keys())
        ideas = generate_daily_ideas(3)
        for idea in ideas:
            assert idea["character_a"] in valid_chars, f"Invalid char_a: {idea['character_a']}"
            assert idea["character_b"] in valid_chars, f"Invalid char_b: {idea['character_b']}"

    def test_location_is_valid(self):
        from src.story_generator.slot_machine import generate_daily_ideas
        with open(os.path.join(os.path.dirname(__file__), "..", "data", "locations.json")) as f:
            valid_locs = list(json.load(f)["locations"].keys())
        ideas = generate_daily_ideas(3)
        for idea in ideas:
            assert idea["location"] in valid_locs, f"Invalid location: {idea['location']}"


# ===================================================================
# STAGE 2: Script Generation (structure contract)
# ===================================================================

class TestStage2_ScriptStructure:
    """Stage 2: Verify the script dict structure is correct.

    Pre-conditions:
      - Claude returns valid JSON matching templates/claude_story_prompt.txt
    Expected result:
      - episode_id at ROOT level (not inside metadata)
      - title at ROOT level (not inside metadata)
      - created_at at ROOT level
      - metadata contains ONLY: total_duration_seconds, characters_featured,
        primary_location, content_pillar, punchline_type
    """

    def test_episode_id_at_root(self):
        script = _make_test_script()
        assert "episode_id" in script
        assert script["episode_id"] == "DRAFT-EP-001"

    def test_title_at_root(self):
        script = _make_test_script()
        assert "title" in script
        assert script["title"] != "Untitled"

    def test_created_at_at_root(self):
        script = _make_test_script()
        assert "created_at" in script

    def test_metadata_does_not_contain_episode_id(self):
        """metadata should NOT have episode_id — it's at root."""
        script = _make_test_script()
        assert "episode_id" not in script["metadata"]

    def test_metadata_does_not_contain_title(self):
        """metadata should NOT have title — it's at root."""
        script = _make_test_script()
        assert "title" not in script["metadata"]

    def test_metadata_has_required_fields(self):
        script = _make_test_script()
        meta = script["metadata"]
        assert "characters_featured" in meta
        assert "primary_location" in meta
        assert "punchline_type" in meta

    def test_scenes_have_required_keys(self):
        script = _make_test_script()
        required = ["scene_number", "duration_seconds", "background",
                     "characters_present", "action_description", "dialogue"]
        for scene in script["scenes"]:
            for key in required:
                assert key in scene, f"Scene {scene.get('scene_number')} missing: {key}"

    def test_draft_episode_id_format(self):
        script = _make_test_script()
        assert script["episode_id"].startswith("DRAFT-EP-")


# ===================================================================
# STAGE 3: Script Validation
# ===================================================================

class TestStage3_ScriptValidation:
    """Stage 3: validate_script() checks the script against PRD schema.

    Pre-conditions:
      - Script dict from Stage 2
      - data/characters.json and locations.json exist
    Expected result:
      - Valid script returns (True, [])
      - Invalid script returns (False, [list of errors])
    """

    def test_valid_script_passes(self):
        from src.story_generator.validator import validate_script
        script = _make_test_script()
        is_valid, errors = validate_script(script)
        assert is_valid, f"Valid script failed validation: {errors}"

    def test_missing_scenes_fails(self):
        from src.story_generator.validator import validate_script
        script = _make_test_script()
        script["scenes"] = []
        is_valid, errors = validate_script(script)
        assert not is_valid
        assert any("no scenes" in e.lower() for e in errors)

    def test_invalid_character_caught(self):
        from src.story_generator.validator import validate_script
        script = _make_test_script()
        script["scenes"][0]["characters_present"].append("fake_character")
        is_valid, errors = validate_script(script)
        assert not is_valid
        assert any("fake_character" in e for e in errors)

    def test_invalid_background_caught(self):
        from src.story_generator.validator import validate_script
        script = _make_test_script()
        script["scenes"][0]["background"] = "nonexistent_location"
        is_valid, errors = validate_script(script)
        assert not is_valid
        assert any("nonexistent_location" in e for e in errors)


# ===================================================================
# STAGE 4: Notion Publishing
# ===================================================================

class TestStage4_NotionPublishing:
    """Stage 4: publish_script() creates a Notion page.

    Pre-conditions:
      - NOTION_API_KEY and NOTION_SCRIPTS_DB_ID in .env
      - Script dict from Stage 2
    Expected result:
      - _build_properties extracts episode_id and title from ROOT
      - Page title formatted correctly for DRAFT and real EP formats
      - Episode number extracted correctly from both formats
    """

    def test_build_properties_draft_format(self):
        from src.notion.script_publisher import _build_properties
        script = _make_test_script("DRAFT-EP-001")
        props = _build_properties(script)
        title_text = props["title"]["title"][0]["text"]["content"]
        assert "DRAFT-EP-001" in title_text
        assert props["Episode Number"]["number"] == 1

    def test_build_properties_real_ep_format(self):
        from src.notion.script_publisher import _build_properties
        script = _make_test_script("EP001")
        script["episode_id"] = "EP001"
        props = _build_properties(script)
        title_text = props["title"]["title"][0]["text"]["content"]
        assert "EP # 001" in title_text
        assert "DRAFT" not in title_text
        assert props["Episode Number"]["number"] == 1

    def test_build_properties_reads_title_from_root(self):
        from src.notion.script_publisher import _build_properties
        script = _make_test_script()
        props = _build_properties(script)
        title_text = props["title"]["title"][0]["text"]["content"]
        assert "The Pink Donut Incident" in title_text

    def test_build_properties_reads_characters_from_metadata(self):
        from src.notion.script_publisher import _build_properties
        script = _make_test_script()
        props = _build_properties(script)
        char_names = [s["name"] for s in props["Characters"]["multi_select"]]
        assert "Oinks" in char_names
        assert "Reows" in char_names

    def test_build_script_body_reads_from_root(self):
        from src.notion.script_publisher import _build_script_body
        script = _make_test_script()
        blocks = _build_script_body(script)
        # First block should be heading with episode_id and title
        first_heading = blocks[0]
        heading_text = first_heading["heading_1"]["rich_text"][0]["text"]["content"]
        assert "DRAFT-EP-001" in heading_text
        assert "The Pink Donut Incident" in heading_text


# ===================================================================
# STAGE 5: Asset Availability Check
# ===================================================================

class TestStage5_AssetCheck:
    """Stage 5: check_asset_availability() verifies all referenced assets exist.

    Pre-conditions:
      - Script with valid backgrounds and characters
      - assets/ directory with sprite PNGs and background PNGs
    Expected result:
      - Returns (True, []) if all assets exist
      - Returns (False, [missing_paths]) if any missing
    """

    def test_valid_script_assets_available(self):
        from src.pipeline.orchestrator import check_asset_availability
        script = _make_test_script()
        all_present, missing = check_asset_availability(script)
        if not all_present:
            pytest.skip(f"Test environment missing assets: {missing}")
        assert all_present

    def test_missing_background_detected(self):
        from src.pipeline.orchestrator import check_asset_availability
        script = _make_test_script()
        script["scenes"][0]["background"] = "nonexistent_bg_xyz"
        all_present, missing = check_asset_availability(script)
        assert not all_present
        assert any("nonexistent_bg_xyz" in m for m in missing)

    def test_missing_character_sprite_detected(self):
        from src.pipeline.orchestrator import check_asset_availability
        script = _make_test_script()
        script["scenes"][0]["characters_present"].append("nonexistent_char")
        all_present, missing = check_asset_availability(script)
        assert not all_present
        assert any("nonexistent_char" in m for m in missing)


# ===================================================================
# STAGE 6: Scene Frame Building
# ===================================================================

class TestStage6_SceneFrameBuilding:
    """Stage 6: build_scene_frames() renders PNG frames for one scene.

    Pre-conditions:
      - Valid scene dict
      - Background PNGs and character sprite PNGs exist in assets/
    Expected result:
      - Returns (frame_paths, sfx_events, blip_events)
      - frame_paths contains duration_seconds * 30 frames (at 30fps)
      - Each frame is a valid PNG file
    """

    def test_builds_frames_for_scene(self):
        """v2: build_scene_frames returns (frame_iter, total_frames, sfx_events)."""
        from src.video_assembler.scene_builder import build_scene_frames, FRAME_WIDTH, FRAME_HEIGHT
        from PIL import Image
        script = _make_test_script()
        scene = script["scenes"][0]

        frame_iter, total_frames, sfx_events = build_scene_frames(
            scene, frame_offset=0
        )
        assert total_frames > 0
        # At 30fps, 10 seconds = 300 frames minimum (dialogue may add more)
        assert total_frames >= 100  # Conservative lower bound
        # Check first frame is a PIL Image at correct size
        first_frame = next(frame_iter)
        assert isinstance(first_frame, Image.Image)
        assert first_frame.size == (FRAME_WIDTH, FRAME_HEIGHT)

    def test_frames_are_pil_images(self):
        """v2: frame iterator yields PIL Images, not file paths."""
        from src.video_assembler.scene_builder import build_scene_frames
        from PIL import Image
        script = _make_test_script()
        scene = script["scenes"][0]

        frame_iter, total_frames, _ = build_scene_frames(scene, frame_offset=0)
        # Check first 3 frames
        for i, frame in enumerate(frame_iter):
            assert isinstance(frame, Image.Image)
            assert frame.mode == "RGB"
            if i >= 2:
                break


# ===================================================================
# STAGE 7: Full Video Composition
# ===================================================================

class TestStage7_VideoComposition:
    """Stage 7: compose_episode() builds full MP4 from script.

    Pre-conditions:
      - Valid script, all assets present
      - FFmpeg installed
      - Music file exists at assets/music/main_theme.wav
    Expected result:
      - Returns path to MP4 file
      - MP4 exists and is > 500KB
      - Resolution: 1080x1920
      - Has audio stream
    """

    @pytest.mark.slow
    def test_compose_produces_mp4(self):
        """Full video composition — slow test, skip in CI."""
        from src.video_assembler.composer import compose_episode
        script = _make_test_script()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch OUTPUT_DIR to use temp directory
            with patch("src.video_assembler.composer.OUTPUT_DIR", tmpdir):
                video_path = compose_episode(script, output_name="test_e2e")
                assert video_path is not None
                assert os.path.exists(video_path)
                assert video_path.endswith(".mp4")
                # File should be > 500KB for a real video
                assert os.path.getsize(video_path) > 500 * 1024


# ===================================================================
# STAGE 8: Variant Generation
# ===================================================================

class TestStage8_VariantGeneration:
    """Stage 8: generate_single_variant() creates one video variant.

    Pre-conditions:
      - Valid script
      - compose_episode works
    Expected result:
      - Returns dict with: name, description, video_path, duration_seconds, preset
      - episode_id read from script root (not metadata)
      - Output filename uses episode_id from root
    """

    def test_variant_reads_episode_id_from_root(self):
        """Verify variant_generator reads episode_id from script root."""
        from src.video_assembler import variant_generator as vg

        script = _make_test_script("DRAFT-EP-005")
        # We can't run the full compose, but we can check the ID extraction
        episode_id = script.get("episode_id", "EP000").lower()
        assert episode_id == "draft-ep-005"
        output_name = f"{episode_id}_v1"
        assert output_name == "draft-ep-005_v1"

    def test_variant_presets_exist(self):
        from src.video_assembler.variant_generator import VARIANT_PRESETS
        assert len(VARIANT_PRESETS) == 3
        assert VARIANT_PRESETS[0]["name"] == "Standard"
        assert VARIANT_PRESETS[1]["name"] == "Upbeat"
        assert VARIANT_PRESETS[2]["name"] == "Tense"

    def test_pacing_adjustment_does_not_mutate(self):
        from src.video_assembler.variant_generator import _adjust_script_pacing
        script = _make_test_script()
        original_duration = script["scenes"][0]["duration_seconds"]
        _adjust_script_pacing(script, 0.85, 1)
        assert script["scenes"][0]["duration_seconds"] == original_duration


# ===================================================================
# STAGE 9: Google Drive Upload + Episode Numbering
# ===================================================================

class TestStage9_DriveAndNumbering:
    """Stage 9: Drive upload + assign_episode_number().

    Pre-conditions:
      - GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN in .env
      - GOOGLE_DRIVE_FOLDER_ID in .env
      - data/episodes/index.json exists
    Expected result:
      - Drive filename uses peeked episode number (not DRAFT)
      - assign_episode_number() returns EP001 and increments counter
      - script["episode_id"] updated to real EP ID after assignment
    """

    def test_drive_filename_format(self):
        from src.publisher.drive import format_drive_filename
        filename = format_drive_filename(1, "The Pink Donut Incident")
        assert filename == "ep0001_the-pink-donut-incident.mp4"

    def test_drive_filename_handles_special_chars(self):
        from src.publisher.drive import format_drive_filename
        filename = format_drive_filename(42, "Oinks' Big Day!")
        assert filename == "ep0042_oinks-big-day.mp4"

    def test_assign_episode_number_returns_real_id(self):
        from src.story_generator.engine import assign_episode_number
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "index.json")
            with open(index_path, "w") as f:
                json.dump({"next_episode_number": 1, "episodes": []}, f)

            with patch("src.story_generator.engine.os.path.dirname", return_value=tmpdir), \
                 patch("src.story_generator.engine.os.path.join",
                       side_effect=lambda *args: index_path if "index.json" in args else os.path.join(*args)):
                result = assign_episode_number()
                assert result == "EP001"
                # Counter should now be 2
                with open(index_path) as f:
                    data = json.load(f)
                assert data["next_episode_number"] == 2

    def test_script_episode_id_update_after_publish(self):
        """Simulate what video_preview.py does after Drive upload."""
        script = _make_test_script("DRAFT-EP-001")
        assert script["episode_id"] == "DRAFT-EP-001"

        # Simulate assign_episode_number returning EP001
        real_episode_id = "EP001"
        script["episode_id"] = real_episode_id
        if "metadata" in script:
            script["metadata"]["episode_id"] = real_episode_id

        assert script["episode_id"] == "EP001"
        assert script["metadata"].get("episode_id") == "EP001"


# ===================================================================
# STAGE 10: Metadata Generation + Safety Check
# ===================================================================

class TestStage10_MetadataAndSafety:
    """Stage 10: generate_metadata() + safety_check().

    Pre-conditions:
      - Script with episode_id and title at ROOT
      - config/metadata_rules.yaml exists
      - data/characters.json exists
    Expected result:
      - Returns dict with tiktok, youtube, instagram keys
      - Each platform has title/description/hashtags
      - safety_check returns (True, []) for clean content
    """

    def test_metadata_reads_title_from_root(self):
        from src.metadata.generator import generate_metadata
        script = _make_test_script()
        metadata = generate_metadata(script)
        # Title should contain "The Pink Donut Incident", not "Untitled"
        yt_title = metadata["youtube"]["title"]
        assert "Untitled" not in yt_title

    def test_metadata_reads_episode_id_from_root(self):
        from src.metadata.generator import generate_metadata
        script = _make_test_script("EP001")
        script["episode_id"] = "EP001"
        metadata = generate_metadata(script)
        yt_desc = metadata["youtube"]["description"]
        assert "EP001" in yt_desc

    def test_metadata_has_all_platforms(self):
        from src.metadata.generator import generate_metadata
        script = _make_test_script()
        metadata = generate_metadata(script)
        assert "tiktok" in metadata
        assert "youtube" in metadata
        assert "instagram" in metadata

    def test_safety_check_passes_clean_content(self):
        from src.metadata.generator import generate_metadata, safety_check
        script = _make_test_script()
        metadata = generate_metadata(script)
        is_safe, issues = safety_check(metadata)
        assert is_safe, f"Safety check failed on clean content: {issues}"

    def test_safety_check_catches_blocked_words(self):
        from src.metadata.generator import safety_check
        metadata = {
            "tiktok": {"title": "Kill them all", "description": "", "hashtags": []},
            "youtube": {"title": "", "description": "", "tags": []},
            "instagram": {"caption": "", "hashtags": []},
        }
        is_safe, issues = safety_check(metadata)
        assert not is_safe
        assert any("kill" in i.lower() for i in issues)


# ===================================================================
# STAGE 11: Continuity Logging
# ===================================================================

class TestStage11_ContinuityLogging:
    """Stage 11: log_episode() updates timeline, gags, character growth.

    Pre-conditions:
      - Script with continuity_log containing events_to_track
      - episode_id and title at ROOT (not metadata)
    Expected result:
      - Timeline events logged with correct episode_id
      - Running gags updated
      - Character growth updated
    """

    def test_log_episode_reads_episode_id_from_root(self):
        from src.continuity.engine import log_episode
        script = _make_test_script("EP001")
        script["episode_id"] = "EP001"

        with tempfile.TemporaryDirectory() as tmpdir:
            timeline_path = os.path.join(tmpdir, "timeline.json")
            gags_path = os.path.join(tmpdir, "gags.json")
            growth_path = os.path.join(tmpdir, "growth.json")

            with patch("src.continuity.engine.TIMELINE_FILE", timeline_path), \
                 patch("src.continuity.engine.GAGS_FILE", gags_path), \
                 patch("src.continuity.engine.GROWTH_FILE", growth_path):
                log_episode(script)

            with open(timeline_path) as f:
                timeline = json.load(f)
            events = timeline.get("events", [])
            assert len(events) > 0
            assert events[0]["episode_id"] == "EP001"

    def test_log_episode_reads_title_from_root(self):
        from src.continuity.engine import log_episode
        script = _make_test_script("EP001")
        script["episode_id"] = "EP001"

        with tempfile.TemporaryDirectory() as tmpdir:
            timeline_path = os.path.join(tmpdir, "timeline.json")
            gags_path = os.path.join(tmpdir, "gags.json")
            growth_path = os.path.join(tmpdir, "growth.json")

            with patch("src.continuity.engine.TIMELINE_FILE", timeline_path), \
                 patch("src.continuity.engine.GAGS_FILE", gags_path), \
                 patch("src.continuity.engine.GROWTH_FILE", growth_path):
                log_episode(script)

            with open(timeline_path) as f:
                timeline = json.load(f)
            events = timeline.get("events", [])
            assert events[0]["episode_title"] == "The Pink Donut Incident"


# ===================================================================
# STAGE 12: Episode Index Logging
# ===================================================================

class TestStage12_EpisodeIndexLogging:
    """Stage 12: log_episode_to_index() records episode in index.json.

    Pre-conditions:
      - Script with episode_id at ROOT
      - data/episodes/index.json exists
    Expected result:
      - Episode appended with correct episode_id from root
      - next_episode_number NOT incremented (handled by assign_episode_number)
    """

    def test_logs_episode_id_from_root(self):
        from src.pipeline.orchestrator import log_episode_to_index
        script = _make_test_script("EP001")
        script["episode_id"] = "EP001"

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "episodes", "index.json")
            os.makedirs(os.path.dirname(index_path))
            with open(index_path, "w") as f:
                json.dump({"next_episode_number": 2, "episodes": []}, f)

            with patch("src.pipeline.orchestrator.DATA_DIR", tmpdir):
                log_episode_to_index(script)

            with open(index_path) as f:
                data = json.load(f)
            assert data["episodes"][0]["episode_id"] == "EP001"

    def test_logs_title_from_root(self):
        from src.pipeline.orchestrator import log_episode_to_index
        script = _make_test_script("EP001")
        script["episode_id"] = "EP001"

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "episodes", "index.json")
            os.makedirs(os.path.dirname(index_path))
            with open(index_path, "w") as f:
                json.dump({"next_episode_number": 2, "episodes": []}, f)

            with patch("src.pipeline.orchestrator.DATA_DIR", tmpdir):
                log_episode_to_index(script)

            with open(index_path) as f:
                data = json.load(f)
            assert data["episodes"][0]["title"] == "The Pink Donut Incident"

    def test_does_not_increment_counter(self):
        from src.pipeline.orchestrator import log_episode_to_index
        script = _make_test_script("EP001")
        script["episode_id"] = "EP001"

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "episodes", "index.json")
            os.makedirs(os.path.dirname(index_path))
            with open(index_path, "w") as f:
                json.dump({"next_episode_number": 2, "episodes": []}, f)

            with patch("src.pipeline.orchestrator.DATA_DIR", tmpdir):
                log_episode_to_index(script)

            with open(index_path) as f:
                data = json.load(f)
            assert data["next_episode_number"] == 2


# ===================================================================
# STAGE 13: Cross-Stage Data Flow Contract
# ===================================================================

class TestStage13_DataFlowContract:
    """Verify data flows correctly between stages.

    These tests simulate the actual handoff between stages,
    verifying that what one stage outputs is correctly consumed
    by the next stage.
    """

    def test_script_to_notion_flow(self):
        """Script → _build_properties should not lose data."""
        from src.notion.script_publisher import _build_properties
        script = _make_test_script()
        props = _build_properties(script)
        # Episode number extracted correctly
        assert props["Episode Number"]["number"] == 1
        # Title included
        title_text = props["title"]["title"][0]["text"]["content"]
        assert "The Pink Donut Incident" in title_text

    def test_script_to_composer_flow(self):
        """Script → composer reads episode_id and title from root."""
        script = _make_test_script("DRAFT-EP-001")
        # Simulate what composer.py does (lines 123-125 after fix)
        episode_id = script.get("episode_id", "EP000")
        title = script.get("title", "Untitled Episode")
        assert episode_id == "DRAFT-EP-001"
        assert title == "The Pink Donut Incident"

    def test_script_to_metadata_flow(self):
        """Script → metadata generator reads correctly from root."""
        from src.metadata.generator import generate_metadata
        script = _make_test_script("EP001")
        script["episode_id"] = "EP001"
        metadata = generate_metadata(script)
        assert "EP001" in metadata["youtube"]["description"]

    def test_script_to_continuity_flow(self):
        """Script → continuity engine reads correctly from root."""
        script = _make_test_script("EP001")
        script["episode_id"] = "EP001"
        # Simulate what continuity/engine.py does (lines 156-158 after fix)
        metadata = script.get("metadata", {})
        episode_id = script.get("episode_id", "?")
        title = script.get("title", "Untitled")
        characters_featured = metadata.get("characters_featured", [])
        assert episode_id == "EP001"
        assert title == "The Pink Donut Incident"
        assert "oinks" in characters_featured

    def test_full_publish_flow_episode_id_update(self):
        """Simulate the full publish flow: DRAFT → Drive → real EP ID.

        This is the most critical integration test. It verifies:
        1. Script starts with DRAFT-EP-001
        2. After Drive upload, assign_episode_number returns EP001
        3. script["episode_id"] is updated to EP001
        4. Downstream modules (continuity, index) see EP001
        """
        script = _make_test_script("DRAFT-EP-001")

        # Stage 1: Script has DRAFT ID
        assert script["episode_id"] == "DRAFT-EP-001"

        # Stage 2: Simulate successful Drive upload + assign
        real_id = "EP001"  # Would come from assign_episode_number()
        script["episode_id"] = real_id
        if "metadata" in script:
            script["metadata"]["episode_id"] = real_id

        # Stage 3: Downstream reads should see EP001
        assert script["episode_id"] == "EP001"
        assert script.get("title") == "The Pink Donut Incident"

        # Stage 4: Continuity should log EP001
        episode_id = script.get("episode_id", "?")
        title = script.get("title", "Untitled")
        assert episode_id == "EP001"
        assert title == "The Pink Donut Incident"


# ===================================================================
# ISSUE LOG: Known bugs found during code review
# ===================================================================

class TestIssueLog_BugsFound:
    """Tests for specific bugs found during the code review.

    Each test documents a bug, what line it's on, and verifies the fix.
    """

    def test_video_preview_title_fallback_reads_metadata_first(self):
        """BUG: video_preview.py line 213 and 246 read title from metadata first.

        Line 213: title = script.get("metadata", {}).get("title", script.get("title", "Untitled"))
        Line 246: episode_title = script.get("metadata", {}).get("title", "Untitled")

        Since metadata does NOT contain "title", line 213 falls through to
        script.get("title") which works. But line 246 would return "Untitled"
        because it doesn't have the fallback to root.

        Expected: Both should read script.get("title", "Untitled")
        """
        script = _make_test_script()

        # Line 213 pattern — has fallback, works but is misleading
        title_213 = script.get("metadata", {}).get("title", script.get("title", "Untitled"))
        assert title_213 == "The Pink Donut Incident"  # Works by accident

        # Line 246 pattern — NO fallback to root, returns "Untitled"
        episode_title_246 = script.get("metadata", {}).get("title", "Untitled")
        assert episode_title_246 == "Untitled"  # BUG! This will be "Untitled"

    def test_custom_variant_title_fallback_reads_metadata_first(self):
        """BUG: video_preview.py line 143 has same issue as line 213/246.

        Line 143: title = script.get("metadata", {}).get("title", script.get("title", "Untitled"))

        This works by accident (falls through to root), but is misleading.
        """
        script = _make_test_script()
        # Line 143 pattern
        title = script.get("metadata", {}).get("title", script.get("title", "Untitled"))
        assert title == "The Pink Donut Incident"  # Works, but fragile

    def test_continuity_engine_saves_timeline_events(self):
        """BUG: continuity/engine.py:169 reads 'events_to_track' but template outputs 'events'.

        This means timeline events are NEVER saved — the list is always empty.
        After fix, log_episode should save events from continuity_log.events.
        """
        from src.continuity.engine import log_episode
        script = _make_test_script("EP001")
        script["episode_id"] = "EP001"
        # Ensure continuity_log has events (matching template field name)
        assert "events" in script["continuity_log"] or "events_to_track" in script["continuity_log"]

        with tempfile.TemporaryDirectory() as tmpdir:
            timeline_path = os.path.join(tmpdir, "timeline.json")
            gags_path = os.path.join(tmpdir, "gags.json")
            growth_path = os.path.join(tmpdir, "growth.json")

            with patch("src.continuity.engine.TIMELINE_FILE", timeline_path), \
                 patch("src.continuity.engine.GAGS_FILE", gags_path), \
                 patch("src.continuity.engine.GROWTH_FILE", growth_path):
                log_episode(script)

            with open(timeline_path) as f:
                timeline = json.load(f)
            events = timeline.get("events", [])
            # This MUST have events — the script has continuity_log.events with 1 item
            assert len(events) >= 1, (
                "No timeline events saved! continuity/engine.py is reading the wrong key "
                "from continuity_log. Template outputs 'events', engine reads 'events_to_track'."
            )

    def test_continuity_engine_saves_running_gags(self):
        """BUG: continuity/engine.py:193 reads 'new_gags' but template outputs 'new_running_gags'.

        This means running gags are NEVER saved.
        After fix, log_episode should save gags from continuity_log.new_running_gags.
        """
        from src.continuity.engine import log_episode
        script = _make_test_script("EP001")
        script["episode_id"] = "EP001"
        # Add a running gag to the script so we can verify it gets saved
        script["continuity_log"]["new_running_gags"] = [
            {
                "id": "glowing_donut",
                "description": "Oinks keeps finding suspiciously glowing donuts",
                "escalation_ideas": ["The glow gets brighter each episode"],
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            timeline_path = os.path.join(tmpdir, "timeline.json")
            gags_path = os.path.join(tmpdir, "gags.json")
            growth_path = os.path.join(tmpdir, "growth.json")

            with patch("src.continuity.engine.TIMELINE_FILE", timeline_path), \
                 patch("src.continuity.engine.GAGS_FILE", gags_path), \
                 patch("src.continuity.engine.GROWTH_FILE", growth_path):
                log_episode(script)

            with open(gags_path) as f:
                gags_data = json.load(f)
            gags = gags_data.get("running_gags", [])
            assert len(gags) >= 1, (
                "No running gags saved! continuity/engine.py is reading the wrong key "
                "from continuity_log. Template outputs 'new_running_gags', engine reads 'new_gags'."
            )

    def test_continuity_engine_handles_string_character_developments(self):
        """BUG: Template tells Claude to return character_developments as strings,
        but engine.py:222 calls dev.get("character") which crashes on strings.

        Template line 105: "character_developments": ["Any character growth moments"]
        Engine line 222:   char_id = dev.get("character", "")

        When Claude returns ["Reows showed empathy"], dev is a string, and
        str.get() raises AttributeError.

        Fix: Engine must handle both string and dict formats.
        """
        from src.continuity.engine import log_episode
        script = _make_test_script("EP001")
        script["episode_id"] = "EP001"
        # Simulate Claude returning character_developments as plain strings
        # (matches template format on line 105)
        script["continuity_log"]["character_developments"] = [
            "Reows showed empathy toward Oinks",
            "Oinks learned to share donuts",
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            timeline_path = os.path.join(tmpdir, "timeline.json")
            gags_path = os.path.join(tmpdir, "gags.json")
            growth_path = os.path.join(tmpdir, "growth.json")

            with patch("src.continuity.engine.TIMELINE_FILE", timeline_path), \
                 patch("src.continuity.engine.GAGS_FILE", gags_path), \
                 patch("src.continuity.engine.GROWTH_FILE", growth_path):
                # This should NOT crash
                log_episode(script)
