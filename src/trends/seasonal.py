"""Trending topics & seasonal themes — checks for timely content angles."""

import os
from datetime import datetime

import yaml

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config")


def _load_seasonal_themes():
    """Load seasonal themes from config."""
    path = os.path.join(CONFIG_DIR, "seasonal_themes.yaml")
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return data.get("themes", [])


def get_seasonal_theme(date=None):
    """Check if today matches any seasonal theme.

    Args:
        date: Optional datetime. Defaults to today.

    Returns:
        Dict with theme info if matched, None otherwise.
        {"theme": str, "story_angles": list[str]}
    """
    if date is None:
        date = datetime.utcnow()

    month_day = date.strftime("%m-%d")
    themes = _load_seasonal_themes()

    for entry in themes:
        date_range = entry.get("date_range", "")

        if ":" in date_range:
            # Range format: "MM-DD:MM-DD"
            start, end = date_range.split(":")
            if start <= month_day <= end:
                return {
                    "theme": entry.get("theme", ""),
                    "story_angles": entry.get("story_angles", []),
                }
        else:
            # Single day format: "MM-DD"
            if month_day == date_range:
                return {
                    "theme": entry.get("theme", ""),
                    "story_angles": entry.get("story_angles", []),
                }

    return None


async def get_trending_topics():
    """Check for trending topics that could be adapted to the island setting.

    Currently returns from a curated list of evergreen/generic topics.
    In the future, this can be expanded to pull from TikTok Creative Center,
    YouTube Trending, etc.

    Returns:
        List of topic dicts:
        [{"topic": str, "source": str, "relevance_score": float, "story_angle": str}]
    """
    # For now, return seasonal themes as "trending" topics
    seasonal = get_seasonal_theme()
    topics = []

    if seasonal:
        for angle in seasonal.get("story_angles", []):
            topics.append({
                "topic": seasonal["theme"],
                "source": "seasonal_calendar",
                "relevance_score": 0.8,
                "story_angle": angle,
            })

    return topics
