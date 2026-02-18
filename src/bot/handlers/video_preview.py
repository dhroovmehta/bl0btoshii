"""Handler for #video-preview channel.

Bot posts 2-3 video versions. User picks one or requests changes.
"""

import asyncio
import os
import re
import discord
from src.bot.state import load_state, save_state


def parse_video_selection(text):
    """Parse user's video selection.

    Accepts: "1", "2", "3", "approve", or freeform edit notes.
    Returns: (selection_index, is_approval, edit_notes)
    """
    text_lower = text.strip().lower()

    # Check for approval
    if text_lower in ("approve", "approved", "yes", "looks good", "lgtm", "ship it"):
        return (None, True, None)

    # Direct number
    if text_lower in ("1", "2", "3"):
        return (int(text_lower) - 1, False, None)

    # "option X" or ordinal
    match = re.search(r"option\s*(\d)", text_lower)
    if match:
        num = int(match.group(1))
        if 1 <= num <= 3:
            return (num - 1, False, None)

    ordinals = {"first": 0, "second": 1, "third": 2}
    for word, idx in ordinals.items():
        if word in text_lower:
            return (idx, False, None)

    # Freeform edit notes (e.g., "use music from 1 but pacing from 2")
    return (None, False, text)


async def handle_video_preview(message, bot):
    """Handle user replies in #video-preview."""
    state = load_state()

    if state["stage"] != "video_review":
        await message.channel.send(
            "No videos are currently awaiting review."
        )
        return

    selection, is_approval, edit_notes = parse_video_selection(message.content)

    if is_approval:
        # Approve default (version 1) — advance to metadata/publishing
        state["selected_video_index"] = 0
        state["stage"] = "publishing"
        save_state(state)

        selected = state.get("video_variants", [{}])[0]
        await message.channel.send(
            f"**{selected.get('name', 'Version 1')}** approved! Generating metadata..."
        )
        from src.bot.tasks import safe_task
        safe_task(
            _generate_metadata_and_schedule(bot, message.channel),
            error_channel=message.channel,
            bot=bot,
            stage="Publishing & Metadata",
        )

    elif selection is not None:
        # User picked a specific version
        variants = state.get("video_variants", [])
        if selection >= len(variants):
            await message.channel.send(
                f"Only {len(variants)} versions available. Reply with a number between 1 and {len(variants)}."
            )
            return

        state["selected_video_index"] = selection
        state["stage"] = "publishing"
        save_state(state)

        selected = variants[selection]
        await message.channel.send(
            f"**{selected['name']}** selected! Generating metadata..."
        )
        from src.bot.tasks import safe_task
        safe_task(
            _generate_metadata_and_schedule(bot, message.channel),
            error_channel=message.channel,
            bot=bot,
            stage="Publishing & Metadata",
        )

    elif edit_notes:
        # User wants a custom version — generate it
        await message.channel.send("Generating custom version with your notes...")
        from src.bot.tasks import safe_task
        safe_task(
            _generate_custom_variant(edit_notes, bot, message.channel),
            error_channel=message.channel,
            bot=bot,
            stage="Custom Video Variant",
        )


async def _generate_custom_variant(edit_notes, bot, channel):
    """Generate a custom variant based on user's edit notes."""
    from src.video_assembler.variant_generator import generate_custom_variant

    state = load_state()
    script = state.get("current_script")
    variants = state.get("video_variants", [])

    if not script:
        await channel.send("Error: no script found for video generation.")
        return

    try:
        loop = asyncio.get_event_loop()
        custom = await loop.run_in_executor(
            None, generate_custom_variant, script, edit_notes, variants
        )

        # Add custom variant to state
        variants.append({
            "name": custom["name"],
            "description": custom["description"],
            "video_path": custom["video_path"],
            "duration_seconds": custom["duration_seconds"],
            "preset": custom["preset"],
        })
        state["video_variants"] = variants
        save_state(state)

        # Post the custom version
        episode_id = state.get("current_episode", "?")
        title = script.get("metadata", {}).get("title", script.get("title", "Untitled"))
        custom_idx = len(variants)

        await channel.send(
            f"**Custom Version — {episode_id}: {title}**\n"
            f"{custom['description']} ({custom['duration_seconds']}s)\n\n"
            f"Reply **approve** to use this version, "
            f"pick a version (**1**-**{custom_idx}**), or submit more changes."
        )

        # Attach the video file
        video_path = custom["video_path"]
        if os.path.exists(video_path):
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            if file_size_mb <= 25:
                await channel.send(
                    f"**Custom Version:**",
                    file=discord.File(video_path)
                )
            else:
                await channel.send(
                    f"**Custom Version:** File too large ({file_size_mb:.1f}MB). "
                    f"Path: `{video_path}`"
                )

    except Exception as e:
        print(f"[Video Preview] Error generating custom variant: {e}")
        await channel.send(f"Error generating custom version: {e}")
        from src.bot.alerts import notify_error
        ep = state.get("current_episode")
        await notify_error(bot, "Custom Video Variant", ep, str(e))


async def _generate_metadata_and_schedule(bot, video_preview_channel):
    """Generate metadata, run safety check, publish, and log episode.

    Steps 15-21 of the pipeline:
    15. Metadata generation
    16. Safety check
    17. Post metadata to #publishing-log
    18-19. Auto-publish to platforms (if configured)
    20. Post confirmation
    21. Continuity update + episode logging
    """
    from src.metadata.generator import generate_metadata, safety_check
    from src.publisher.scheduler import get_next_posting_slots, format_schedule_message
    from src.publisher.platforms import publish_to_all
    from src.publisher.drive import upload_to_drive, format_drive_filename, format_publishing_alert
    from src.continuity.engine import log_episode
    from src.pipeline.orchestrator import log_episode_to_index
    from src.story_generator.engine import assign_episode_number
    from src.bot.bot import CHANNEL_IDS

    state = load_state()
    script = state.get("current_script")

    if not script:
        await video_preview_channel.send("Error: no script found for metadata generation.")
        return

    try:
        loop = asyncio.get_event_loop()

        # Step 15: Generate metadata
        metadata = await loop.run_in_executor(None, generate_metadata, script)

        # Step 16: Safety check
        is_safe, issues = safety_check(metadata)

        # Get posting schedule
        slots = get_next_posting_slots()

        # Store in state
        state["metadata"] = metadata
        state["safety_check"] = {"passed": is_safe, "issues": issues}
        state["posting_slots"] = {
            platform: slot.isoformat() for platform, slot in slots.items()
        }
        save_state(state)

        # Step 17: Post to #publishing-log
        pub_channel = bot.get_channel(CHANNEL_IDS["publishing_log"])
        if not pub_channel:
            await video_preview_channel.send("Error: #publishing-log channel not found.")
            return

        schedule_msg = format_schedule_message(slots, metadata)

        if not is_safe:
            schedule_msg += f"\n\n**Safety Issues Found:**\n"
            for issue in issues:
                schedule_msg += f"- {issue}\n"
            schedule_msg += "\nPlease review and override metadata before publishing."

        await pub_channel.send(schedule_msg)

        # Steps 18-19: Auto-publish to all platforms
        selected_idx = state.get("selected_video_index", 0)
        variants = state.get("video_variants", [])
        video_path = variants[selected_idx]["video_path"] if variants else None

        # Upload selected video to Google Drive
        if video_path:
            episode_title = script.get("metadata", {}).get("title", "Untitled")

            # Peek at next episode number for Drive filename (don't increment yet)
            episode_num = 1
            try:
                import json
                index_path = os.path.join(
                    os.path.dirname(__file__), "..", "..", "..", "data", "episodes", "index.json"
                )
                if os.path.exists(index_path):
                    with open(index_path, "r") as f:
                        index = json.load(f)
                    episode_num = index.get("next_episode_number", 1)
            except Exception as idx_err:
                print(f"[Video Preview] Warning: could not read episode index: {idx_err}")

            drive_filename = format_drive_filename(episode_num, episode_title)
            drive_result = await loop.run_in_executor(
                None, upload_to_drive, video_path, drive_filename
            )

            if drive_result["success"]:
                # Assign real episode number now that Drive upload succeeded
                real_episode_id = assign_episode_number()
                state["current_episode"] = real_episode_id
                # Update script metadata so downstream (continuity, index) uses real ID
                script["episode_id"] = real_episode_id
                if "metadata" in script:
                    script["metadata"]["episode_id"] = real_episode_id
                state["current_script"] = script
                save_state(state)
                print(f"[Video Preview] Assigned real episode ID: {real_episode_id}")

                alert_msg = format_publishing_alert(
                    drive_filename, drive_result["file_url"], metadata
                )
                await pub_channel.send(alert_msg)
            else:
                await pub_channel.send(
                    f"**Google Drive upload failed:** {drive_result['error']}"
                )
                from src.bot.alerts import notify_error
                ep = state.get("current_episode")
                await notify_error(bot, "Google Drive Upload", ep, drive_result["error"])

        publish_results = {}
        if video_path and is_safe:
            try:
                publish_results = await publish_to_all(video_path, metadata, slots)
            except Exception as pub_err:
                print(f"[Video Preview] Publishing error: {pub_err}")
                publish_results = {"error": str(pub_err)}
                from src.bot.alerts import notify_error
                ep = state.get("current_episode")
                await notify_error(bot, "Platform Publishing", ep, str(pub_err))

        # Step 20: Post confirmation
        episode_id = state.get("current_episode", "?")

        # Summarize publish results
        pub_summary_parts = []
        for platform, result in publish_results.items():
            if platform == "error":
                continue
            if isinstance(result, dict) and result.get("success"):
                url = result.get("post_url", "")
                pub_summary_parts.append(f"- **{platform.capitalize()}:** Published ({url})")
            elif isinstance(result, dict):
                pub_summary_parts.append(f"- **{platform.capitalize()}:** {result.get('error', 'Failed')}")

        if pub_summary_parts:
            pub_summary = "\n".join(pub_summary_parts)
            await pub_channel.send(f"**Publishing Results:**\n{pub_summary}")

        await video_preview_channel.send(
            f"Metadata generated for **{episode_id}**. "
            f"Check **#publishing-log** for the schedule."
        )

        # Step 21: Log continuity data + episode index (non-blocking — failures logged but don't block)
        try:
            await loop.run_in_executor(None, log_episode, script)
        except Exception as cont_err:
            print(f"[Video Preview] Continuity logging failed (non-blocking): {cont_err}")

        try:
            await loop.run_in_executor(None, log_episode_to_index, script)
        except Exception as idx_err:
            print(f"[Video Preview] Episode index logging failed (non-blocking): {idx_err}")

        # Mark episode as done
        state["stage"] = "done"
        save_state(state)

    except Exception as e:
        print(f"[Video Preview] Error generating metadata: {e}")
        await video_preview_channel.send(f"Error generating metadata: {e}")
        from src.bot.alerts import notify_error
        ep = state.get("current_episode")
        await notify_error(bot, "Publishing & Metadata", ep, str(e))
