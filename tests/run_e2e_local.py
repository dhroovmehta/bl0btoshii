#!/usr/bin/env python3
"""Real end-to-end pipeline test — runs EVERY stage with real API calls.

Usage:
    python tests/run_e2e_local.py

This script:
  1. Generates an idea (slot machine)
  2. Calls Claude API to generate a script
  3. Validates the script
  4. Publishes to Notion
  5. Checks asset availability
  6. Builds frames for ALL scenes
  7. Mixes audio
  8. Composes video via FFmpeg (full MP4)
  9. Runs video quality check
  10. Uploads to Google Drive
  11. Assigns real episode number
  12. Generates metadata + safety check
  13. Logs continuity data + episode index

Each stage prints PASS/FAIL and the result. If any stage fails, subsequent
stages still attempt to run using fallback data where possible.
"""

import json
import os
import sys
import tempfile
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

ISSUES = []
STAGE_RESULTS = {}


def log_stage(stage_num, name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    print(f"\n{'='*60}")
    print(f"  STAGE {stage_num}: {name} — {status}")
    if detail:
        print(f"  {detail}")
    print(f"{'='*60}")
    STAGE_RESULTS[stage_num] = {"name": name, "passed": passed, "detail": detail}
    if not passed:
        ISSUES.append(f"Stage {stage_num} ({name}): {detail}")


def main():
    print("\n" + "="*60)
    print("  MOOTOSHI PIPELINE — REAL END-TO-END TEST")
    print("="*60)
    start_time = time.time()

    # ---------------------------------------------------------------
    # STAGE 1: Idea Generation
    # ---------------------------------------------------------------
    print("\n[Stage 1] Generating ideas...")
    try:
        from src.story_generator.slot_machine import generate_daily_ideas
        ideas = generate_daily_ideas(3)
        assert len(ideas) == 3
        idea = ideas[0]
        assert "character_a" in idea
        assert "character_b" in idea
        log_stage(1, "Idea Generation", True,
                  f"{idea['character_a']} + {idea['character_b']} at {idea['location']}")
    except Exception as e:
        log_stage(1, "Idea Generation", False, str(e))
        idea = None

    # ---------------------------------------------------------------
    # STAGE 2: Script Generation (Claude API)
    # ---------------------------------------------------------------
    print("\n[Stage 2] Generating script via Claude API...")
    script = None
    if idea:
        try:
            from src.story_generator.engine import generate_episode
            script, errors = generate_episode(idea)
            assert script is not None, f"generate_episode returned None: {errors}"
            assert "episode_id" in script, "Missing episode_id at root"
            assert "title" in script, "Missing title at root"
            assert script["episode_id"].startswith("DRAFT-EP-"), f"Expected DRAFT prefix, got: {script['episode_id']}"
            log_stage(2, "Script Generation", True,
                      f"{script['episode_id']}: {script['title']} ({len(script.get('scenes', []))} scenes)")
            if errors:
                print(f"  Warnings: {errors}")
        except Exception as e:
            log_stage(2, "Script Generation", False, str(e))

    # ---------------------------------------------------------------
    # STAGE 3: Script Validation
    # ---------------------------------------------------------------
    print("\n[Stage 3] Validating script...")
    if script:
        try:
            from src.story_generator.validator import validate_script
            is_valid, val_errors = validate_script(script)
            if is_valid:
                log_stage(3, "Script Validation", True, "No errors")
            else:
                log_stage(3, "Script Validation", False, f"Errors: {val_errors}")
        except Exception as e:
            log_stage(3, "Script Validation", False, str(e))
    else:
        log_stage(3, "Script Validation", False, "No script from Stage 2")

    # ---------------------------------------------------------------
    # STAGE 4: Notion Publishing
    # ---------------------------------------------------------------
    print("\n[Stage 4] Publishing to Notion...")
    notion_url = None
    if script:
        try:
            from src.notion.script_publisher import publish_script
            notion_url = publish_script(script)
            assert notion_url, "publish_script returned empty URL"
            log_stage(4, "Notion Publishing", True, f"URL: {notion_url}")
        except Exception as e:
            log_stage(4, "Notion Publishing", False, str(e))
    else:
        log_stage(4, "Notion Publishing", False, "No script")

    # ---------------------------------------------------------------
    # STAGE 5: Asset Availability Check
    # ---------------------------------------------------------------
    print("\n[Stage 5] Checking asset availability...")
    if script:
        try:
            from src.pipeline.orchestrator import check_asset_availability
            all_present, missing = check_asset_availability(script)
            if all_present:
                log_stage(5, "Asset Check", True, "All assets present")
            else:
                log_stage(5, "Asset Check", False, f"Missing: {missing}")
        except Exception as e:
            log_stage(5, "Asset Check", False, str(e))
    else:
        log_stage(5, "Asset Check", False, "No script")

    # ---------------------------------------------------------------
    # STAGE 6: Video Composition (frames + audio + FFmpeg)
    # ---------------------------------------------------------------
    print("\n[Stage 6] Composing video (this takes several minutes)...")
    video_path = None
    if script:
        try:
            from src.video_assembler.composer import compose_episode
            with tempfile.TemporaryDirectory() as tmpdir:
                # Use temp dir for output to avoid polluting output/
                from unittest.mock import patch
                with patch("src.video_assembler.composer.OUTPUT_DIR", tmpdir):
                    video_path = compose_episode(script, output_name="e2e_test")

                assert video_path is not None
                assert os.path.exists(video_path)
                size_kb = os.path.getsize(video_path) / 1024
                log_stage(6, "Video Composition", True,
                          f"Output: {video_path} ({size_kb:.0f} KB)")

                # -------------------------------------------------------
                # STAGE 7: Video Quality Check
                # -------------------------------------------------------
                print("\n[Stage 7] Running video quality check...")
                try:
                    from src.pipeline.orchestrator import check_video_quality
                    passed, issues = check_video_quality(video_path)
                    if passed:
                        log_stage(7, "Video Quality Check", True, "All checks passed")
                    else:
                        log_stage(7, "Video Quality Check", False, f"Issues: {issues}")
                except Exception as e:
                    log_stage(7, "Video Quality Check", False, str(e))

                # -------------------------------------------------------
                # STAGE 8: Google Drive Upload
                # -------------------------------------------------------
                print("\n[Stage 8] Uploading to Google Drive...")
                try:
                    from src.publisher.drive import upload_to_drive, format_drive_filename

                    # Read next episode number for filename
                    index_path = os.path.join(
                        os.path.dirname(__file__), "..", "data", "episodes", "index.json"
                    )
                    episode_num = 1
                    if os.path.exists(index_path):
                        with open(index_path) as f:
                            episode_num = json.load(f).get("next_episode_number", 1)

                    episode_title = script.get("title", "Untitled")
                    drive_filename = format_drive_filename(episode_num, episode_title)
                    print(f"  Drive filename: {drive_filename}")
                    assert "untitled" not in drive_filename.lower() or "untitled" in episode_title.lower(), \
                        f"Drive filename has 'untitled' but title is '{episode_title}'"

                    drive_result = upload_to_drive(video_path, drive_filename)
                    if drive_result["success"]:
                        log_stage(8, "Google Drive Upload", True,
                                  f"URL: {drive_result['file_url']}")
                    else:
                        log_stage(8, "Google Drive Upload", False, drive_result["error"])
                except Exception as e:
                    log_stage(8, "Google Drive Upload", False, str(e))

        except Exception as e:
            log_stage(6, "Video Composition", False, str(e))
            log_stage(7, "Video Quality Check", False, "Skipped — no video")
            log_stage(8, "Google Drive Upload", False, "Skipped — no video")
    else:
        log_stage(6, "Video Composition", False, "No script")
        log_stage(7, "Video Quality Check", False, "Skipped")
        log_stage(8, "Google Drive Upload", False, "Skipped")

    # ---------------------------------------------------------------
    # STAGE 9: Episode Numbering
    # ---------------------------------------------------------------
    print("\n[Stage 9] Assigning episode number...")
    if script:
        try:
            from src.story_generator.engine import assign_episode_number
            real_id = assign_episode_number()
            assert real_id.startswith("EP"), f"Expected EP prefix, got: {real_id}"
            script["episode_id"] = real_id
            if "metadata" in script:
                script["metadata"]["episode_id"] = real_id
            log_stage(9, "Episode Numbering", True, f"Assigned: {real_id}")
        except Exception as e:
            log_stage(9, "Episode Numbering", False, str(e))
    else:
        log_stage(9, "Episode Numbering", False, "No script")

    # ---------------------------------------------------------------
    # STAGE 10: Metadata Generation + Safety Check
    # ---------------------------------------------------------------
    print("\n[Stage 10] Generating metadata...")
    if script:
        try:
            from src.metadata.generator import generate_metadata, safety_check
            metadata = generate_metadata(script)
            assert "tiktok" in metadata
            assert "youtube" in metadata
            assert "instagram" in metadata

            yt_title = metadata["youtube"]["title"]
            assert "Untitled" not in yt_title, f"YouTube title is 'Untitled': {yt_title}"

            is_safe, issues = safety_check(metadata)
            safety_status = "Safe" if is_safe else f"Issues: {issues}"
            log_stage(10, "Metadata + Safety", True,
                      f"YT title: {yt_title} | {safety_status}")
        except Exception as e:
            log_stage(10, "Metadata + Safety", False, str(e))
    else:
        log_stage(10, "Metadata + Safety", False, "No script")

    # ---------------------------------------------------------------
    # STAGE 11: Continuity Logging
    # ---------------------------------------------------------------
    print("\n[Stage 11] Logging continuity data...")
    if script:
        try:
            from src.continuity.engine import log_episode
            with tempfile.TemporaryDirectory() as tmpdir:
                timeline_path = os.path.join(tmpdir, "timeline.json")
                gags_path = os.path.join(tmpdir, "gags.json")
                growth_path = os.path.join(tmpdir, "growth.json")

                from unittest.mock import patch
                with patch("src.continuity.engine.TIMELINE_FILE", timeline_path), \
                     patch("src.continuity.engine.GAGS_FILE", gags_path), \
                     patch("src.continuity.engine.GROWTH_FILE", growth_path):
                    log_episode(script)

                with open(timeline_path) as f:
                    timeline = json.load(f)
                events = timeline.get("events", [])

                detail = f"{len(events)} event(s) logged"
                if events:
                    assert events[0]["episode_id"] == script["episode_id"], \
                        f"Event has wrong episode_id: {events[0]['episode_id']}"
                    detail += f" | First: {events[0].get('event', '')[:50]}"

                log_stage(11, "Continuity Logging", True, detail)
        except Exception as e:
            log_stage(11, "Continuity Logging", False, str(e))
    else:
        log_stage(11, "Continuity Logging", False, "No script")

    # ---------------------------------------------------------------
    # STAGE 12: Episode Index Logging
    # ---------------------------------------------------------------
    print("\n[Stage 12] Logging to episode index...")
    if script:
        try:
            from src.pipeline.orchestrator import log_episode_to_index
            with tempfile.TemporaryDirectory() as tmpdir:
                index_path = os.path.join(tmpdir, "episodes", "index.json")
                os.makedirs(os.path.dirname(index_path))
                with open(index_path, "w") as f:
                    json.dump({"next_episode_number": 99, "episodes": []}, f)

                from unittest.mock import patch
                with patch("src.pipeline.orchestrator.DATA_DIR", tmpdir):
                    log_episode_to_index(script)

                with open(index_path) as f:
                    data = json.load(f)

                assert len(data["episodes"]) == 1
                logged = data["episodes"][0]
                assert logged["episode_id"] == script["episode_id"]
                assert logged["title"] == script["title"]
                assert data["next_episode_number"] == 99, "Counter was incremented!"

                log_stage(12, "Episode Index", True,
                          f"Logged: {logged['episode_id']} — {logged['title']}")
        except Exception as e:
            log_stage(12, "Episode Index", False, str(e))
    else:
        log_stage(12, "Episode Index", False, "No script")

    # ---------------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------------
    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)

    passed = sum(1 for r in STAGE_RESULTS.values() if r["passed"])
    total = len(STAGE_RESULTS)
    print(f"\n  {passed}/{total} stages passed in {elapsed:.1f}s")

    if ISSUES:
        print(f"\n  ISSUES FOUND ({len(ISSUES)}):")
        for issue in ISSUES:
            print(f"    - {issue}")
    else:
        print("\n  NO ISSUES FOUND")

    print("\n" + "="*60)
    return 0 if not ISSUES else 1


if __name__ == "__main__":
    sys.exit(main())
