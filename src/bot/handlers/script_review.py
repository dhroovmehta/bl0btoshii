"""Handler for #script-review channel.

Bot posts Notion link to script. User approves or submits edit notes.
Edit notes trigger Claude to revise the script and post a new version.
"""

import asyncio
from src.bot.state import load_state, save_state


def is_approval(text):
    """Check if the message is an approval."""
    approvals = {"approve", "approved", "yes", "looks good", "lgtm", "ship it", "good", "perfect"}
    return text.strip().lower() in approvals


async def handle_script_review(message, bot):
    """Handle user replies in #script-review."""
    state = load_state()

    if state["stage"] != "script_review":
        await message.channel.send(
            "No script is currently awaiting review."
        )
        return

    if is_approval(message.content):
        # Script approved — advance to video production
        state["stage"] = "video_generating"
        save_state(state)

        episode_id = state.get("current_episode", "?")
        await message.channel.send(
            f"Script approved for **{episode_id}**. Starting video production..."
        )

        # Trigger video generation in background
        from src.bot.tasks import safe_task
        safe_task(
            _generate_and_post_videos(bot, message.channel),
            error_channel=message.channel,
            bot=bot,
            stage="Video Generation",
        )

    else:
        # User submitted edit notes — trigger Claude revision
        edit_notes = message.content
        await message.channel.send("Revising script with your notes...")

        from src.bot.tasks import safe_task
        safe_task(
            _revise_and_post_script(edit_notes, bot, message.channel),
            error_channel=message.channel,
            bot=bot,
            stage="Script Revision",
        )


async def _revise_and_post_script(edit_notes, bot, channel):
    """Revise the script with Claude and post the new version."""
    from src.story_generator.engine import apply_edit_notes
    from src.notion.script_publisher import publish_script

    state = load_state()
    original_script = state.get("current_script")

    if not original_script:
        await channel.send("Error: no script found in pipeline state.")
        return

    try:
        loop = asyncio.get_event_loop()
        revised, errors = await loop.run_in_executor(
            None, apply_edit_notes, original_script, edit_notes
        )

        if not revised:
            await channel.send(f"Revision failed: {errors}")
            return

        # Publish revised script to Notion
        notion_url = await loop.run_in_executor(None, publish_script, revised)

        # Update state
        version = state.get("script_version", 1) + 1
        state["current_script"] = revised
        state["script_notion_url"] = notion_url
        state["script_version"] = version
        save_state(state)

        # Post updated review
        episode_id = revised.get("episode_id", "?")
        title = revised.get("title", "Untitled")
        scenes = len(revised.get("scenes", []))
        total_dur = sum(s.get("duration_seconds", 0) for s in revised.get("scenes", []))

        review_msg = (
            f"**Updated Script — {episode_id}: {title} (v{version})**\n\n"
            f"[Notion Link]({notion_url})\n\n"
            f"Scenes: {scenes} | Duration: {total_dur}s\n\n"
            f"Reply **approve** or submit more edits."
        )

        if errors:
            review_msg += f"\n\nWarnings: {', '.join(errors)}"

        await channel.send(review_msg)

    except Exception as e:
        print(f"[Script Review] Error revising script: {e}")
        await channel.send(f"Error revising script: {e}")
        from src.bot.alerts import notify_error
        ep = state.get("current_episode")
        await notify_error(bot, "Script Revision", ep, str(e))


async def _generate_and_post_videos(bot, script_review_channel):
    """Generate video variants and post previews to #video-preview.

    Generates variants one at a time so each gets its own timeout and
    progress messages appear in Discord between renders.

    Includes quality gates:
    - Step 10: Asset check before generation (blocks if missing)
    - Video quality check after generation (warns but doesn't block)
    """
    import os
    import discord
    from src.video_assembler.variant_generator import generate_single_variant
    from src.pipeline.orchestrator import check_asset_availability, check_video_quality

    state = load_state()
    script = state.get("current_script")

    if not script:
        await script_review_channel.send("Error: no script found for video generation.")
        return

    # Step 10: Asset check — block if assets are missing
    assets_ok, missing = check_asset_availability(script)
    if not assets_ok:
        missing_list = "\n".join(f"- `{m}`" for m in missing)
        await script_review_channel.send(
            f"**Asset check failed.** Missing assets:\n{missing_list}\n\n"
            f"Add the missing assets, then re-approve the script."
        )
        from src.bot.alerts import notify_error
        ep = state.get("current_episode", "Unknown")
        await notify_error(bot, "Asset Check", ep, f"Missing assets: {', '.join(missing)}")
        state["stage"] = "script_review"
        save_state(state)
        return

    # 60 min per variant — at 12 cps typewriter speed, each scene renders
    # ~3x more frames than at 30 cps. 3 scenes × ~15 min + encoding ≈ 50 min.
    PER_VARIANT_TIMEOUT = 3600
    VARIANT_COUNT = 3
    variants = []

    try:
        loop = asyncio.get_event_loop()

        for i in range(VARIANT_COUNT):
            await script_review_channel.send(
                f"Rendering variant {i + 1}/{VARIANT_COUNT}..."
            )

            variant = await asyncio.wait_for(
                loop.run_in_executor(
                    None, generate_single_variant, script, i, VARIANT_COUNT
                ),
                timeout=PER_VARIANT_TIMEOUT,
            )

            if variant:
                variants.append(variant)

        if not variants:
            raise RuntimeError("No variants were generated.")

        # Run video quality checks on each variant
        quality_warnings = []
        for v in variants:
            video_path = v.get("video_path", "")
            if video_path and os.path.exists(video_path):
                passed, issues = check_video_quality(video_path)
                if not passed:
                    quality_warnings.append((v["name"], issues))

        # Store variant info in state
        state["video_variants"] = [
            {
                "name": v["name"],
                "description": v["description"],
                "video_path": v["video_path"],
                "duration_seconds": v["duration_seconds"],
                "preset": v["preset"],
            }
            for v in variants
        ]
        state["stage"] = "video_review"
        save_state(state)

        # Post to #video-preview channel
        from src.bot.bot import CHANNEL_IDS
        preview_channel = bot.get_channel(CHANNEL_IDS["video_preview"])
        if not preview_channel:
            await script_review_channel.send("Error: #video-preview channel not found.")
            return

        episode_id = state.get("current_episode", "?")
        title = script.get("metadata", {}).get("title", script.get("title", "Untitled"))

        preview_msg = f"**Video Preview — {episode_id}: {title}**\n\n"
        for i, v in enumerate(variants):
            preview_msg += (
                f"**Version {i+1}:** {v['description']} ({v['duration_seconds']}s)\n"
            )

        # Add quality warnings if any
        if quality_warnings:
            preview_msg += "\n**Quality Warnings:**\n"
            for name, issues in quality_warnings:
                preview_msg += f"- {name}: {', '.join(issues)}\n"

        preview_msg += (
            "\nReply with your pick (**1**, **2**, **3**), "
            "**approve** to use Version 1, "
            "or request changes (e.g., \"music from v2, pacing from v1\")."
        )

        await preview_channel.send(preview_msg)

        # Attach video files
        for i, v in enumerate(variants):
            video_path = v["video_path"]
            if os.path.exists(video_path):
                file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
                if file_size_mb <= 25:  # Discord file size limit
                    await preview_channel.send(
                        f"**Version {i+1}:**",
                        file=discord.File(video_path)
                    )
                else:
                    await preview_channel.send(
                        f"**Version {i+1}:** File too large for Discord ({file_size_mb:.1f}MB). "
                        f"Path: `{video_path}`"
                    )

        await script_review_channel.send(
            f"Video variants ready! Check **#video-preview** to review."
        )

    except asyncio.TimeoutError:
        completed = len(variants)
        timeout_msg = (
            f"Video generation timed out on variant {completed + 1}/{VARIANT_COUNT} "
            f"after 25 minutes. The VPS may be under heavy load or FFmpeg may be stuck."
        )
        print(f"[Script Review] {timeout_msg}")
        state["stage"] = "script_review"
        save_state(state)
        await script_review_channel.send(
            f"**Video generation timed out** on variant {completed + 1}/{VARIANT_COUNT}. "
            f"Re-approve the script to retry."
        )
        from src.bot.alerts import notify_error
        ep = state.get("current_episode", "Unknown")
        await notify_error(bot, "Video Generation", ep, timeout_msg)
    except Exception as e:
        print(f"[Script Review] Error generating videos: {e}")
        state["stage"] = "script_review"
        save_state(state)
        await script_review_channel.send(f"Error generating videos: {e}")
        from src.bot.alerts import notify_error
        ep = state.get("current_episode")
        await notify_error(bot, "Video Generation", ep, str(e))
