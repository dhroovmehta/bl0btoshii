"""Pipeline orchestrator — manages the daily automated pipeline and quality gates."""

import json
import os
import subprocess
import time

import yaml

from src.bot.state import load_state, save_state, get_stage

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def run_with_retry(func, max_retries=3, backoff_seconds=None, args=None,
                   kwargs=None, raise_on_failure=True, error_log=None):
    """Run a function with retry logic and configurable backoff.

    Args:
        func: The callable to execute.
        max_retries: Maximum number of attempts.
        backoff_seconds: List of wait times between retries (e.g., [30, 120, 600]).
        args: Positional arguments to pass to func.
        kwargs: Keyword arguments to pass to func.
        raise_on_failure: If True, re-raises the last exception after all retries.
                          If False, returns None on total failure.
        error_log: Optional list to append caught exceptions to.

    Returns:
        The return value of func on success, or None if all retries fail
        and raise_on_failure is False.
    """
    if backoff_seconds is None:
        backoff_seconds = [0]
    if args is None:
        args = ()
    if kwargs is None:
        kwargs = {}

    last_error = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if error_log is not None:
                error_log.append(e)
            if attempt < max_retries - 1 and attempt < len(backoff_seconds):
                wait = backoff_seconds[attempt]
                if wait > 0:
                    time.sleep(wait)

    if raise_on_failure and last_error is not None:
        raise last_error
    return None


def _load_quality_gates():
    """Load quality gate configuration."""
    path = os.path.join(CONFIG_DIR, "quality_gates.yaml")
    with open(path, "r") as f:
        return yaml.safe_load(f).get("quality_gates", {})


def check_asset_availability(script):
    """Check if all required assets exist for a script.

    Verifies backgrounds, character sprites, SFX, and music referenced
    in the script are available.

    Args:
        script: Full episode script dict.

    Returns:
        (all_present, missing_assets) — bool and list of missing asset paths.
    """
    missing = []
    scenes = script.get("scenes", [])

    for scene in scenes:
        # Check background
        bg_id = scene.get("background", "")
        bg_path = os.path.join(ASSETS_DIR, "backgrounds", f"{bg_id}.png")
        if bg_id and not os.path.exists(bg_path):
            missing.append(f"backgrounds/{bg_id}.png")

        # Check character sprites
        for char_id in scene.get("characters_present", []):
            for state in ["idle", "talking"]:
                sprite_path = os.path.join(ASSETS_DIR, "characters", char_id, f"{state}.png")
                if not os.path.exists(sprite_path):
                    missing.append(f"characters/{char_id}/{state}.png")

        # Check SFX (try with .wav extension if not already present)
        for sfx in scene.get("sfx_triggers", []):
            sfx_file = sfx.get("sfx", "")
            if sfx_file:
                sfx_path = os.path.join(ASSETS_DIR, "sfx", sfx_file)
                if not os.path.exists(sfx_path):
                    if not sfx_file.endswith(".wav"):
                        sfx_path_wav = os.path.join(ASSETS_DIR, "sfx", f"{sfx_file}.wav")
                        if not os.path.exists(sfx_path_wav):
                            missing.append(f"sfx/{sfx_file}")
                    else:
                        missing.append(f"sfx/{sfx_file}")

    # Deduplicate
    missing = list(set(missing))
    return len(missing) == 0, missing


def check_video_quality(video_path):
    """Run quality checks on a generated video.

    Validates resolution, duration, file size, and audio presence.

    Args:
        video_path: Path to the MP4 file.

    Returns:
        (passed, issues) — bool and list of quality issues.
    """
    gates = _load_quality_gates().get("video_assembly", {})
    issues = []

    if not os.path.exists(video_path):
        return False, ["Video file does not exist"]

    # File size check
    file_size_kb = os.path.getsize(video_path) / 1024
    file_size_mb = file_size_kb / 1024

    min_size_kb = gates.get("min_file_size_kb", 500)
    max_size_mb = gates.get("max_file_size_mb", 100)

    if file_size_kb < min_size_kb:
        issues.append(f"File too small: {file_size_kb:.0f}KB (min: {min_size_kb}KB)")
    if file_size_mb > max_size_mb:
        issues.append(f"File too large: {file_size_mb:.1f}MB (max: {max_size_mb}MB)")

    # Use ffprobe for detailed checks
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", video_path],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            issues.append("ffprobe failed — cannot verify video specs")
            return len(issues) == 0, issues

        probe = json.loads(result.stdout)

        # Resolution check
        if gates.get("resolution_check", True):
            for stream in probe.get("streams", []):
                if stream.get("codec_type") == "video":
                    width = stream.get("width", 0)
                    height = stream.get("height", 0)
                    if width != 1080 or height != 1920:
                        issues.append(f"Resolution: {width}x{height} (expected 1080x1920)")

        # Duration check
        duration = float(probe.get("format", {}).get("duration", 0))
        tolerance = gates.get("duration_tolerance_pct", 15)
        if duration < 5:
            issues.append(f"Duration too short: {duration:.1f}s")
        elif duration > 60:
            issues.append(f"Duration too long: {duration:.1f}s (max ~45s + tolerance)")

        # Audio check
        if gates.get("audio_sync_check", True):
            has_audio = any(
                s.get("codec_type") == "audio" for s in probe.get("streams", [])
            )
            if not has_audio:
                issues.append("No audio stream found")

    except FileNotFoundError:
        issues.append("ffprobe not installed — cannot verify video specs")

    passed = len(issues) == 0
    return passed, issues


async def run_daily_pipeline(bot):
    """Run the full daily pipeline sequence.

    This is the main entry point for the automated daily trigger.
    Steps that require human input will pause and wait for Discord responses.

    Args:
        bot: Discord bot instance.
    """
    from src.bot.bot import CHANNEL_IDS
    from src.bot.handlers.idea_selection import post_daily_ideas

    state = load_state()

    if state["stage"] != "idle":
        pub_channel = bot.get_channel(CHANNEL_IDS["publishing_log"])
        if pub_channel:
            await pub_channel.send(
                f"Daily pipeline skipped — pipeline is busy (stage: `{state['stage']}`). "
                f"Use `!reset` to clear if needed."
            )
        return

    # Step 1: Post daily ideas to #idea-selection
    idea_channel = bot.get_channel(CHANNEL_IDS["idea_selection"])
    if idea_channel:
        await post_daily_ideas(idea_channel)
    else:
        print("[Orchestrator] ERROR: #idea-selection channel not found")
        from src.bot.alerts import notify_error
        await notify_error(bot, "Daily Pipeline", None, "#idea-selection channel not found")

    # The rest of the pipeline is event-driven:
    # - User picks idea → triggers script generation
    # - User approves script → triggers video production
    # - User picks video → triggers metadata + publishing
    # Each step is handled by the channel-specific handler in src/bot/handlers/


async def run_weekly_analytics(bot):
    """Run the weekly analytics report.

    Called every Monday at 9:00 AM ET (configured in scheduling.yaml).

    Args:
        bot: Discord bot instance.
    """
    from src.bot.bot import CHANNEL_IDS
    from src.analytics.report_generator import generate_weekly_report, format_discord_summary
    from src.notion.report_publisher import publish_weekly_report

    try:
        report = generate_weekly_report()

        # Publish to Notion
        notion_url = publish_weekly_report(report)

        # Post summary to Discord
        analytics_channel = bot.get_channel(CHANNEL_IDS["weekly_analytics"])
        if analytics_channel:
            summary = format_discord_summary(report)
            await analytics_channel.send(
                f"{summary}\n\n"
                f"[Full Report on Notion]({notion_url})"
            )

    except Exception as e:
        print(f"[Orchestrator] Error generating weekly report: {e}")
        pub_channel = bot.get_channel(CHANNEL_IDS.get("publishing_log"))
        if pub_channel:
            await pub_channel.send(f"Error generating weekly analytics report: {e}")
        from src.bot.alerts import notify_error
        await notify_error(bot, "Weekly Analytics Report", None, str(e))


def log_episode_to_index(script):
    """Log a completed episode to the episodes index.

    Called after an episode is fully published. Records the episode's
    content parameters for analytics tracking.

    Args:
        script: The full episode script dict.
    """
    index_path = os.path.join(DATA_DIR, "episodes", "index.json")

    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            index = json.load(f)
    else:
        index = {"next_episode_number": 1, "episodes": []}

    metadata = script.get("metadata", {})

    index["episodes"].append({
        "episode_id": metadata.get("episode_id", "?"),
        "title": metadata.get("title", "Untitled"),
        "characters_featured": metadata.get("characters_featured", []),
        "situation": metadata.get("situation_type", ""),
        "punchline_type": metadata.get("punchline_type", ""),
        "location": metadata.get("location", ""),
        "created_at": metadata.get("created_at", ""),
        "published": True,
    })

    # Counter is managed by assign_episode_number() — do NOT increment here

    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)
