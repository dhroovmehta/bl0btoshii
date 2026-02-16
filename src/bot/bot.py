"""Mootoshi Discord Bot — Command Center for the Blobtoshi content pipeline."""

import asyncio
import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
AUTHORIZED_USER_ID = int(os.getenv("DISCORD_AUTHORIZED_USER_ID", "0"))

# Channel IDs
CHANNEL_IDS = {
    "idea_selection": int(os.getenv("DISCORD_CHANNEL_IDEA_SELECTION", "0")),
    "script_review": int(os.getenv("DISCORD_CHANNEL_SCRIPT_REVIEW", "0")),
    "video_preview": int(os.getenv("DISCORD_CHANNEL_VIDEO_PREVIEW", "0")),
    "publishing_log": int(os.getenv("DISCORD_CHANNEL_PUBLISHING_LOG", "0")),
    "weekly_analytics": int(os.getenv("DISCORD_CHANNEL_WEEKLY_ANALYTICS", "0")),
}

# Bot setup with required intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"[Mootoshi Bot] Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"[Mootoshi Bot] Connected to guild: {DISCORD_GUILD_ID}")
    print(f"[Mootoshi Bot] Authorized user: {AUTHORIZED_USER_ID}")
    print(f"[Mootoshi Bot] Channels:")
    for name, cid in CHANNEL_IDS.items():
        channel = bot.get_channel(cid)
        status = f"#{channel.name}" if channel else "NOT FOUND"
        print(f"  - {name}: {cid} ({status})")
    print("[Mootoshi Bot] Ready and listening.")

    # Start scheduled tasks
    if not daily_pipeline_trigger.is_running():
        daily_pipeline_trigger.start()
        print("[Mootoshi Bot] Daily pipeline scheduler started.")
    if not weekly_analytics_trigger.is_running():
        weekly_analytics_trigger.start()
        print("[Mootoshi Bot] Weekly analytics scheduler started.")


@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author.id == bot.user.id:
        return

    # Only respond to authorized user
    if message.author.id != AUTHORIZED_USER_ID:
        return

    # Only respond in designated channels
    channel_id = message.channel.id
    if channel_id not in CHANNEL_IDS.values():
        return

    # Route to the correct handler based on channel
    from src.bot.handlers.idea_selection import handle_idea_selection
    from src.bot.handlers.script_review import handle_script_review
    from src.bot.handlers.video_preview import handle_video_preview
    from src.bot.handlers.publishing_log import handle_publishing_log
    from src.bot.handlers.analytics import handle_analytics

    if channel_id == CHANNEL_IDS["idea_selection"]:
        await handle_idea_selection(message, bot)
    elif channel_id == CHANNEL_IDS["script_review"]:
        await handle_script_review(message, bot)
    elif channel_id == CHANNEL_IDS["video_preview"]:
        await handle_video_preview(message, bot)
    elif channel_id == CHANNEL_IDS["publishing_log"]:
        await handle_publishing_log(message, bot)
    elif channel_id == CHANNEL_IDS["weekly_analytics"]:
        await handle_analytics(message, bot)

    # Process commands (like !status, !reset)
    await bot.process_commands(message)


@bot.command(name="status")
async def status_command(ctx):
    """Show current pipeline status."""
    if ctx.author.id != AUTHORIZED_USER_ID:
        return

    from src.bot.state import load_state
    state = load_state()
    stage = state["stage"]
    episode = state.get("current_episode", "None")

    await ctx.send(
        f"**Pipeline Status**\n"
        f"Stage: `{stage}`\n"
        f"Current Episode: `{episode}`"
    )


@bot.command(name="reset")
async def reset_command(ctx):
    """Reset pipeline to idle state."""
    if ctx.author.id != AUTHORIZED_USER_ID:
        return

    from src.bot.state import reset_state
    reset_state()
    await ctx.send("Pipeline reset to idle.")


@bot.command(name="generate")
async def generate_command(ctx):
    """Manually trigger daily idea generation."""
    if ctx.author.id != AUTHORIZED_USER_ID:
        return

    from src.bot.state import load_state
    state = load_state()
    if state["stage"] != "idle":
        await ctx.send(
            f"Pipeline is busy (stage: `{state['stage']}`). "
            f"Use `!reset` to clear, or finish the current episode first."
        )
        return

    # Post ideas to #idea-selection channel
    idea_channel = bot.get_channel(CHANNEL_IDS["idea_selection"])
    if not idea_channel:
        await ctx.send("Error: #idea-selection channel not found.")
        return

    await ctx.send("Generating episode ideas...")

    from src.bot.handlers.idea_selection import post_daily_ideas
    await post_daily_ideas(idea_channel)


@bot.command(name="report")
async def report_command(ctx):
    """Manually trigger weekly analytics report."""
    if ctx.author.id != AUTHORIZED_USER_ID:
        return

    await ctx.send("Generating weekly analytics report...")
    from src.pipeline.orchestrator import run_weekly_analytics
    asyncio.create_task(run_weekly_analytics(bot))


@bot.command(name="quality")
async def quality_command(ctx):
    """Run quality check on the current video."""
    if ctx.author.id != AUTHORIZED_USER_ID:
        return

    from src.bot.state import load_state
    state = load_state()
    variants = state.get("video_variants", [])
    selected_idx = state.get("selected_video_index")

    if not variants:
        await ctx.send("No video variants available to check.")
        return

    idx = selected_idx if selected_idx is not None else 0
    video_path = variants[idx].get("video_path", "")

    from src.pipeline.orchestrator import check_video_quality
    passed, issues = check_video_quality(video_path)

    if passed:
        await ctx.send(f"Video quality check **PASSED** for {variants[idx].get('name', 'video')}.")
    else:
        issue_list = "\n".join(f"- {i}" for i in issues)
        await ctx.send(f"Video quality check **FAILED**:\n{issue_list}")


# --- Scheduled Tasks ---

@tasks.loop(hours=24)
async def daily_pipeline_trigger():
    """Run the daily pipeline at the configured time."""
    from src.pipeline.orchestrator import run_daily_pipeline
    try:
        await run_daily_pipeline(bot)
    except Exception as e:
        print(f"[Scheduler] Daily pipeline error: {e}")


@daily_pipeline_trigger.before_loop
async def before_daily_pipeline():
    """Wait until bot is ready before starting the daily loop."""
    await bot.wait_until_ready()


@tasks.loop(hours=168)  # Weekly (7 days)
async def weekly_analytics_trigger():
    """Run weekly analytics report."""
    from src.pipeline.orchestrator import run_weekly_analytics
    try:
        await run_weekly_analytics(bot)
    except Exception as e:
        print(f"[Scheduler] Weekly analytics error: {e}")


@weekly_analytics_trigger.before_loop
async def before_weekly_analytics():
    """Wait until bot is ready before starting the weekly loop."""
    await bot.wait_until_ready()


def run():
    """Start the bot."""
    if not DISCORD_BOT_TOKEN:
        print("[Mootoshi Bot] ERROR: DISCORD_BOT_TOKEN not set in .env")
        return
    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    run()
