"""Startup recovery — detects and recovers from stuck pipeline states after a crash or restart."""

from src.bot.state import load_state, save_state

# States that are "in-flight" (bot was actively processing) vs "waiting on human"
# In-flight states get reset on startup because the background task is dead.
# Human-waiting states are left alone — the user can still reply.
RECOVERY_MAP = {
    "script_generating": "idle",       # Script gen task died → restart from scratch
    "video_generating": "script_review",  # Video gen task died → re-approve script
    "publishing": "video_review",      # Publish task died → re-approve video
}

# States that require no recovery (idle, waiting on human, or done)
SAFE_STATES = {"idle", "ideas_posted", "script_review", "video_review", "done"}


async def recover_stuck_state(bot):
    """Check pipeline state and recover from any in-flight state that was interrupted.

    Called from on_ready() after the bot reconnects. If the pipeline was in the
    middle of a background task (script_generating, video_generating, publishing),
    the task is now dead because the process restarted. This function rolls back
    to the last safe state so the user can re-trigger.

    Args:
        bot: Discord bot instance.
    """
    state = load_state()
    current_stage = state.get("stage", "idle")

    if current_stage in SAFE_STATES:
        return

    recovery_stage = RECOVERY_MAP.get(current_stage)
    if recovery_stage is None:
        return

    episode = state.get("current_episode", "?")

    # Roll back
    state["stage"] = recovery_stage
    save_state(state)

    print(
        f"[Recovery] Pipeline was stuck in '{current_stage}' on startup. "
        f"Rolled back to '{recovery_stage}' for episode {episode}."
    )

    # Notify #errors channel
    try:
        from src.bot.bot import CHANNEL_IDS
        channel_id = CHANNEL_IDS.get("errors")
        if channel_id:
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send(
                    f"**Startup Recovery**\n"
                    f"Pipeline was stuck in `{current_stage}` (episode: `{episode}`). "
                    f"Rolled back to `{recovery_stage}`.\n"
                    f"Please re-trigger the interrupted step."
                )
    except Exception as e:
        print(f"[Recovery] Failed to send recovery notification: {e}")
