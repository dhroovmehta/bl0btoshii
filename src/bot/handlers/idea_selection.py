"""Handler for #idea-selection channel — v2.

Bot posts 3 episode ideas daily. User picks one by replying 1, 2, or 3.
On selection, runs the full automated pipeline:
  script → video → Drive → YouTube → done.

No human review steps. Status updates go to #pipeline-status.
Errors go to #errors.
"""

import asyncio
import json
import os
import re
from datetime import datetime

from src.bot.state import load_state, save_state

# Lazy imports — these are imported at the top of _run_full_pipeline so tests
# can patch them at the module level (src.bot.handlers.idea_selection.XXX).
# Using top-level imports from heavy modules (video_assembler, publisher) would
# slow down bot startup and make patching harder.
from src.story_generator.engine import generate_episode, assign_episode_number
from src.pipeline.orchestrator import (
    check_asset_availability, check_video_quality,
    collect_rendering_warnings, clear_all_rendering_warnings,
)
from src.video_assembler.composer import compose_episode
from src.video_assembler.render_config import HORIZONTAL, VERTICAL
from src.metadata.generator import generate_metadata, safety_check
from src.publisher.drive import upload_to_drive, format_drive_filename
from src.publisher.platforms import publish_to_youtube
from src.continuity.engine import log_episode
from src.pipeline.orchestrator import log_episode_to_index

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")


def parse_selection(text):
    """Parse user's idea selection from their message.

    Accepts: "1", "2", "3", "option 1", "option 2", "the first one", etc.
    Returns: 0-indexed selection (0, 1, 2) or None if not understood.
    """
    text = text.strip().lower()

    # Direct number
    if text in ("1", "2", "3"):
        return int(text) - 1

    # "option X" pattern
    match = re.search(r"option\s*(\d)", text)
    if match:
        num = int(match.group(1))
        if 1 <= num <= 3:
            return num - 1

    # Ordinal words
    ordinals = {"first": 0, "second": 1, "third": 2}
    for word, idx in ordinals.items():
        if word in text:
            return idx

    return None


async def post_daily_ideas(channel):
    """Generate and post 3 episode ideas to #idea-selection."""
    from src.story_generator.slot_machine import generate_daily_ideas

    ideas = generate_daily_ideas(3)
    today = datetime.now().strftime("%B %d, %Y")

    lines = [f"**Daily Episode Ideas — {today}**\n"]
    for i, idea in enumerate(ideas):
        char_a = idea["character_a"]
        char_b = idea["character_b"]
        additional = idea.get("additional_characters", [])
        location = idea["location"].replace("_", " ").title()

        if additional:
            chars = "Full Cast"
        else:
            chars = f"{char_a.capitalize()} + {char_b.capitalize()}"

        concept = idea["concept"]
        trending = idea.get("trending_tie_in")
        trending_text = f" Trending tie-in: {trending}." if trending else ""

        callbacks = idea.get("continuity_callbacks", [])
        callback_text = ""
        if callbacks:
            refs = [cb.get("reference", "") for cb in callbacks]
            callback_text = f" Callback: {', '.join(refs)}."

        lines.append(
            f"**Option {i + 1}:** {chars} | {location} | "
            f"{concept}{trending_text}{callback_text}\n"
        )

    lines.append('Reply with **1**, **2**, or **3**.')

    await channel.send("\n".join(lines))

    # Save state
    state = load_state()
    state["stage"] = "ideas_posted"
    state["ideas"] = ideas
    state["selected_idea_index"] = None
    save_state(state)


async def handle_idea_selection(message, bot):
    """Handle user replies in #idea-selection."""
    state = load_state()

    if state["stage"] != "ideas_posted":
        await message.channel.send(
            "No ideas are currently posted. Type `!generate` in any channel to trigger idea generation."
        )
        return

    selection = parse_selection(message.content)

    if selection is None:
        await message.channel.send(
            "I didn't understand your selection. Reply with **1**, **2**, or **3**."
        )
        return

    ideas = state.get("ideas", [])
    if selection >= len(ideas):
        await message.channel.send(
            f"Only {len(ideas)} options available. Reply with a number between 1 and {len(ideas)}."
        )
        return

    # Save selection and kick off the full pipeline
    selected_idea = ideas[selection]
    state["selected_idea_index"] = selection
    state["stage"] = "pipeline_running"
    save_state(state)

    await message.channel.send(
        f"Option {selection + 1} selected. Starting full pipeline..."
    )

    # Run full pipeline in background
    from src.bot.tasks import safe_task
    safe_task(
        _run_full_pipeline(selected_idea, bot),
        error_channel=message.channel,
        bot=bot,
        stage="Pipeline",
    )


async def _run_full_pipeline(idea, bot):
    """Run the full automated pipeline: script -> video -> Drive -> YouTube.

    Steps:
      1. Generate script with Claude
      2. Asset check
      3. Render video
      4. Quality check (warn, don't block)
      5. Generate metadata + safety check
      6. Upload to Google Drive (assigns real EP number on success)
      7. Publish to YouTube (skipped if safety check failed)
      8. Log continuity + episode index
      9. Mark pipeline done

    Sends progress notifications to #pipeline-status at each step.
    Sends errors to #errors on any failure.
    """
    from src.bot.bot import CHANNEL_IDS

    status_channel = bot.get_channel(CHANNEL_IDS.get("pipeline_status"))
    idea_channel = bot.get_channel(CHANNEL_IDS.get("idea_selection"))

    state = load_state()

    try:
        loop = asyncio.get_event_loop()

        # ------------------------------------------------------------------
        # Step 1: Generate script
        # ------------------------------------------------------------------
        script, errors = await loop.run_in_executor(None, generate_episode, idea)

        if not script:
            if idea_channel:
                await idea_channel.send(f"Script generation failed: {errors}")
            state["stage"] = "idle"
            save_state(state)
            return

        state["current_episode"] = script.get("episode_id", "?")
        state["current_script"] = script
        save_state(state)

        episode_title = script.get("title", "Untitled")
        episode_id = script.get("episode_id", "?")

        if status_channel:
            scenes = len(script.get("scenes", []))
            total_dur = sum(s.get("duration_seconds", 0) for s in script.get("scenes", []))
            msg = f"**Script written** — {episode_id}: {episode_title} ({scenes} scenes, {total_dur}s)"
            if errors:
                msg += f"\nWarnings: {', '.join(errors)}"
            await status_channel.send(msg)

        # ------------------------------------------------------------------
        # Step 2: Asset check
        # ------------------------------------------------------------------
        assets_ok, missing = check_asset_availability(script)
        if not assets_ok:
            missing_list = "\n".join(f"- `{m}`" for m in missing)
            if status_channel:
                await status_channel.send(
                    f"**Asset check failed.** Missing:\n{missing_list}"
                )
            from src.bot.alerts import notify_error
            await notify_error(bot, "Asset Check", episode_id, f"Missing: {', '.join(missing)}")
            state["stage"] = "idle"
            save_state(state)
            return

        # ------------------------------------------------------------------
        # Step 3: Render video (dual format — horizontal + vertical)
        # ------------------------------------------------------------------
        if status_channel:
            await status_channel.send(f"Rendering video for {episode_id} (horizontal + vertical)...")

        clear_all_rendering_warnings()

        # Mood-based music selection with v1 fallback
        mood = script.get("metadata", {}).get("mood", "playful")
        music_path = os.path.join(ASSETS_DIR, "music", f"{mood}.wav")
        if not os.path.exists(music_path):
            v1_fallback = {
                "playful": "main_theme.wav",
                "calm": "main_theme.wav",
                "tense": "tense_theme.wav",
            }
            music_path = os.path.join(ASSETS_DIR, "music", v1_fallback.get(mood, "main_theme.wav"))

        output_name = episode_id.lower().replace("-", "_")

        # Render horizontal (1920x1080) for YouTube
        video_path_h = await loop.run_in_executor(
            None, compose_episode, script, music_path, output_name, HORIZONTAL
        )

        # Render vertical (1080x1920) for Shorts/TikTok/Reels
        clear_all_rendering_warnings()
        video_path_v = await loop.run_in_executor(
            None, compose_episode, script, music_path, output_name, VERTICAL
        )

        # Check for rendering warnings (missing sprites, backgrounds, etc.)
        warnings = collect_rendering_warnings()
        if warnings:
            from src.bot.alerts import notify_error
            await notify_error(bot, "Rendering Warnings", episode_id, "\n".join(warnings))

        # ------------------------------------------------------------------
        # Step 4: Quality check both formats (warn, don't block)
        # ------------------------------------------------------------------
        for label, vpath in [("horizontal", video_path_h), ("vertical", video_path_v)]:
            passed, issues = check_video_quality(vpath)
            if not passed:
                issue_text = "\n".join(f"- {i}" for i in issues)
                if status_channel:
                    await status_channel.send(f"**Quality warnings ({label}):**\n{issue_text}")

        if status_channel:
            await status_channel.send(
                f"**Video rendered** — {episode_id}: {episode_title} (horizontal + vertical)"
            )

        # ------------------------------------------------------------------
        # Step 5: Generate metadata + safety check
        # ------------------------------------------------------------------
        metadata = await loop.run_in_executor(None, generate_metadata, script)
        is_safe, safety_issues = safety_check(metadata)
        if not is_safe:
            issue_text = "\n".join(f"- {i}" for i in safety_issues)
            if status_channel:
                await status_channel.send(f"**Safety warnings:**\n{issue_text}")

        # ------------------------------------------------------------------
        # Step 6: Upload both videos to Google Drive
        # ------------------------------------------------------------------
        # Peek at next episode number for Drive filename
        episode_num = 1
        try:
            index_path = os.path.join(DATA_DIR, "episodes", "index.json")
            if os.path.exists(index_path):
                with open(index_path, "r") as f:
                    index = json.load(f)
                episode_num = index.get("next_episode_number", 1)
        except Exception:
            pass

        drive_filename_h = format_drive_filename(episode_num, episode_title)
        # Vertical filename: same but with _vertical suffix before .mp4
        drive_filename_v = drive_filename_h.replace(".mp4", "_vertical.mp4")

        drive_result_h = await loop.run_in_executor(
            None, upload_to_drive, video_path_h, drive_filename_h
        )
        drive_result_v = await loop.run_in_executor(
            None, upload_to_drive, video_path_v, drive_filename_v
        )

        # Assign episode number on first successful upload
        any_upload_ok = drive_result_h["success"] or drive_result_v["success"]
        if any_upload_ok:
            real_episode_id = assign_episode_number()
            state["current_episode"] = real_episode_id
            script["episode_id"] = real_episode_id
            if "metadata" in script:
                script["metadata"]["episode_id"] = real_episode_id
            state["current_script"] = script
            save_state(state)

        if drive_result_h["success"]:
            if status_channel:
                await status_channel.send(
                    f"**Uploaded to Google Drive (horizontal)** — {drive_filename_h}\n"
                    f"Link: {drive_result_h['file_url']}"
                )
        else:
            if status_channel:
                await status_channel.send(
                    f"**Drive upload failed (horizontal):** {drive_result_h['error']}"
                )
            from src.bot.alerts import notify_error
            await notify_error(bot, "Drive Upload (horizontal)", episode_id, drive_result_h["error"])

        if drive_result_v["success"]:
            if status_channel:
                await status_channel.send(
                    f"**Uploaded to Google Drive (vertical)** — {drive_filename_v}\n"
                    f"Link: {drive_result_v['file_url']}"
                )
        else:
            if status_channel:
                await status_channel.send(
                    f"**Drive upload failed (vertical):** {drive_result_v['error']}"
                )
            from src.bot.alerts import notify_error
            await notify_error(bot, "Drive Upload (vertical)", episode_id, drive_result_v["error"])

        # ------------------------------------------------------------------
        # Step 7: Publish to YouTube — horizontal as regular, vertical as Short
        # (skip both if safety check failed)
        # ------------------------------------------------------------------
        if is_safe:
            yt_metadata = metadata.get("youtube", {})

            # Horizontal → regular YouTube video (is_short=False strips #Shorts)
            yt_result_h = await publish_to_youtube(video_path_h, yt_metadata, is_short=False)

            if yt_result_h.get("success"):
                if status_channel:
                    await status_channel.send(
                        f"**Published to YouTube (horizontal)** — {yt_result_h.get('post_url', '')}"
                    )
            else:
                if status_channel:
                    await status_channel.send(
                        f"**YouTube publish failed (horizontal):** {yt_result_h.get('error', 'Unknown')}"
                    )
                from src.bot.alerts import notify_error
                await notify_error(
                    bot, "YouTube Publish (horizontal)",
                    state.get("current_episode", episode_id),
                    yt_result_h.get("error", "Unknown"),
                )

            # Vertical → YouTube Short (is_short=True keeps #Shorts)
            yt_result_v = await publish_to_youtube(video_path_v, yt_metadata, is_short=True)

            if yt_result_v.get("success"):
                if status_channel:
                    await status_channel.send(
                        f"**Published to YouTube Shorts (vertical)** — {yt_result_v.get('post_url', '')}"
                    )
            else:
                if status_channel:
                    await status_channel.send(
                        f"**YouTube Shorts publish failed (vertical):** {yt_result_v.get('error', 'Unknown')}"
                    )
                from src.bot.alerts import notify_error
                await notify_error(
                    bot, "YouTube Shorts (vertical)",
                    state.get("current_episode", episode_id),
                    yt_result_v.get("error", "Unknown"),
                )
        else:
            if status_channel:
                await status_channel.send(
                    "**YouTube publish skipped** — safety check failed. "
                    "Fix metadata and publish manually."
                )

        # ------------------------------------------------------------------
        # Step 8: Log continuity + episode index (non-blocking)
        # ------------------------------------------------------------------
        try:
            await loop.run_in_executor(None, log_episode, script)
        except Exception as e:
            print(f"[Pipeline] Continuity logging failed (non-blocking): {e}")

        try:
            await loop.run_in_executor(None, log_episode_to_index, script)
        except Exception as e:
            print(f"[Pipeline] Episode index logging failed (non-blocking): {e}")

        # ------------------------------------------------------------------
        # Step 9: Done
        # ------------------------------------------------------------------
        state["stage"] = "done"
        save_state(state)

        real_id = state.get("current_episode", episode_id)
        if status_channel:
            await status_channel.send(
                f"**Pipeline complete** — {real_id}: {episode_title}"
            )

    except Exception as e:
        print(f"[Pipeline] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        from src.bot.alerts import notify_error
        ep = state.get("current_episode", "?")
        await notify_error(bot, "Pipeline", ep, str(e))
        if status_channel:
            await status_channel.send(f"**Pipeline failed:** {e}")
        state["stage"] = "idle"
        save_state(state)
