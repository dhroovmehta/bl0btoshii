"""Scheduler — determines optimal posting times and manages the publishing queue."""

import os
from datetime import datetime, timedelta

import yaml

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config")


def _load_scheduling_config():
    """Load scheduling configuration."""
    path = os.path.join(CONFIG_DIR, "scheduling.yaml")
    with open(path, "r") as f:
        return yaml.safe_load(f).get("scheduling", {})


def get_next_posting_slots():
    """Calculate the next optimal posting time for each platform.

    Reads optimal times from config/scheduling.yaml and finds the next
    available slot. Staggers platforms by 30 minutes.

    Returns:
        Dict of platform → datetime:
        {
            "tiktok": datetime,
            "youtube": datetime,
            "instagram": datetime,
        }
    """
    config = _load_scheduling_config()
    stagger_min = config.get("stagger_minutes", 30)
    optimal_times = config.get("optimal_times", {})

    now = datetime.utcnow()
    slots = {}

    # Start with TikTok at the next optimal time
    tiktok_time_str = optimal_times.get("tiktok", "10:00")
    base_time = _next_time_slot(now, tiktok_time_str)

    slots["tiktok"] = base_time
    slots["youtube"] = base_time + timedelta(minutes=stagger_min)
    slots["instagram"] = base_time + timedelta(minutes=stagger_min * 2)

    return slots


def _next_time_slot(now, time_str):
    """Find the next occurrence of a given time.

    Args:
        now: Current datetime.
        time_str: Time string like "10:00".

    Returns:
        datetime of the next occurrence.
    """
    hour, minute = map(int, time_str.split(":"))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If the time has already passed today, schedule for tomorrow
    if target <= now:
        target += timedelta(days=1)

    return target


def format_schedule_message(slots, metadata):
    """Format a human-readable schedule message for the #publishing-log channel.

    Args:
        slots: Dict from get_next_posting_slots().
        metadata: Dict from generate_metadata().

    Returns:
        Formatted message string.
    """
    lines = ["**Publishing Schedule**\n"]

    for platform in ["tiktok", "youtube", "instagram"]:
        slot = slots.get(platform)
        meta = metadata.get(platform, {})

        time_str = slot.strftime("%b %d, %Y at %I:%M %p UTC") if slot else "TBD"
        title = meta.get("title", meta.get("caption", "N/A"))[:50]

        lines.append(f"**{platform.capitalize()}:** {time_str}")
        lines.append(f"  Title: {title}")

        # Show hashtags/tags
        tags = meta.get("hashtags", meta.get("tags", []))
        if tags:
            lines.append(f"  Tags: {' '.join(tags[:5])}")
        lines.append("")

    lines.append("Reply to override any metadata before publishing.")
    return "\n".join(lines)
