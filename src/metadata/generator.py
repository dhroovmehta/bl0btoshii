"""Metadata generator — creates platform-specific titles, descriptions, and hashtags."""

import json
import os
import random
from datetime import datetime

import yaml

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def _load_metadata_rules():
    """Load metadata generation rules from config."""
    path = os.path.join(CONFIG_DIR, "metadata_rules.yaml")
    with open(path, "r") as f:
        return yaml.safe_load(f).get("metadata_rules", {})


def _load_characters():
    """Load character nicknames."""
    with open(os.path.join(DATA_DIR, "characters.json"), "r") as f:
        chars = json.load(f)["characters"]
    return {cid: c["nickname"] for cid, c in chars.items()}


def generate_metadata(script):
    """Generate platform-specific metadata for an episode.

    Creates titles, descriptions, and hashtags following the rules engine
    in config/metadata_rules.yaml.

    Args:
        script: Full episode script dict.

    Returns:
        Dict with platform-specific metadata:
        {
            "tiktok": {"title": str, "description": str, "hashtags": list[str]},
            "youtube": {"title": str, "description": str, "tags": list[str]},
            "instagram": {"caption": str, "hashtags": list[str]},
        }
    """
    rules = _load_metadata_rules()
    char_names = _load_characters()

    metadata = script.get("metadata", {})
    title = script.get("title", "Untitled")
    episode_id = script.get("episode_id", "EP000")
    characters_featured = metadata.get("characters_featured", [])

    # Build character name string for descriptions
    featured_names = [char_names.get(c, c.capitalize()) for c in characters_featured[:3]]
    char_string = " & ".join(featured_names) if featured_names else "the gang"

    # Get first scene description for context
    scenes = script.get("scenes", [])
    premise = scenes[0].get("description", title)[:80] if scenes else title

    # Base hashtags from config
    base_tags = rules.get("base_hashtags", ["#pixelart", "#comedy", "#Blobtoshi"])

    # Character-specific hashtags
    char_tags = [f"#{name}" for name in featured_names]

    # --- TikTok ---
    tiktok_rules = rules.get("tiktok", {})
    tiktok_title = _generate_title(title, char_string, max_len=55)
    tiktok_desc = f"{premise}\n\nFollow for more island chaos!"
    tiktok_hashtag_count = tiktok_rules.get("hashtag_count", 5)
    tiktok_hashtags = _pick_hashtags(base_tags, char_tags, tiktok_hashtag_count)

    # --- YouTube ---
    yt_rules = rules.get("youtube", {})
    yt_suffix = yt_rules.get("title_suffix", "| Blobtoshi #Shorts")
    yt_title = _generate_title(title, char_string, max_len=55)
    if not yt_title.endswith(yt_suffix):
        if len(yt_title) + len(yt_suffix) + 1 <= 100:
            yt_title = f"{yt_title} {yt_suffix}"
    yt_desc = (
        f"{premise}\n\n"
        f"Featuring: {char_string}\n"
        f"Episode: {episode_id}\n\n"
        f"New episode every day! Subscribe for more island adventures.\n\n"
        f"#Shorts #Blobtoshi"
    )
    yt_tag_count = yt_rules.get("tag_count", 15)
    yt_tags = _pick_hashtags(
        base_tags + ["#Shorts", "#animation", "#funny", "#cartoon", "#retrogaming", "#8bit"],
        char_tags,
        yt_tag_count,
    )

    # --- Instagram ---
    ig_rules = rules.get("instagram", {})
    ig_cta = ig_rules.get("default_cta", "Follow for more island chaos!")
    ig_caption = f"{tiktok_title}\n\n{premise}\n\n{ig_cta}"
    ig_hashtag_count = ig_rules.get("hashtag_count", 15)
    ig_hashtags = _pick_hashtags(
        base_tags + ["#reels", "#reelsinstagram", "#animationreels", "#funnyvideos"],
        char_tags,
        ig_hashtag_count,
    )

    return {
        "tiktok": {
            "title": tiktok_title,
            "description": tiktok_desc,
            "hashtags": tiktok_hashtags,
        },
        "youtube": {
            "title": yt_title,
            "description": yt_desc,
            "tags": yt_tags,
        },
        "instagram": {
            "caption": ig_caption,
            "hashtags": ig_hashtags,
        },
    }


def _generate_title(episode_title, char_string, max_len=55):
    """Generate a hook-driven title from the episode title and characters.

    Args:
        episode_title: Raw episode title.
        char_string: Character names string.
        max_len: Maximum title length.

    Returns:
        Title string.
    """
    # If the episode title is already a good hook and short enough, use it
    if len(episode_title) <= max_len:
        return episode_title

    # Truncate and add character context
    truncated = episode_title[:max_len - 3] + "..."
    return truncated


def _pick_hashtags(base_tags, char_tags, count):
    """Pick a set of hashtags mixing base, character, and niche tags.

    Ensures variety by shuffling and picking up to `count`.

    Args:
        base_tags: Common hashtags.
        char_tags: Character-specific hashtags.
        count: Target number of hashtags.

    Returns:
        List of hashtag strings.
    """
    all_tags = list(set(base_tags + char_tags))
    random.shuffle(all_tags)
    return all_tags[:count]


def safety_check(metadata):
    """Scan metadata for content safety issues.

    Checks titles, descriptions, and hashtags for profanity,
    offensive content, or misleading text.

    Args:
        metadata: Dict from generate_metadata().

    Returns:
        (is_safe, list_of_issues)
    """
    import re as _re

    issues = []
    block_words = [
        "damn", "hell", "crap", "stupid", "idiot", "hate", "kill", "die",
        "blood", "violence", "sexy", "drug", "drunk", "weapon",
    ]

    # Check all text fields
    all_text = []
    for platform, data in metadata.items():
        for key, value in data.items():
            if isinstance(value, str):
                all_text.append(value)
            elif isinstance(value, list):
                all_text.extend([str(v) for v in value])

    combined = " ".join(all_text).lower()

    for word in block_words:
        # Use word boundaries to avoid false positives (e.g., "die" in "diet")
        if _re.search(r"\b" + _re.escape(word) + r"\b", combined):
            issues.append(f"Blocked word found: '{word}'")

    # Check for clickbait patterns
    clickbait_phrases = [
        "you won't believe", "shocking", "gone wrong", "not clickbait",
        "must see", "insane",
    ]
    for phrase in clickbait_phrases:
        if phrase in combined:
            issues.append(f"Clickbait phrase detected: '{phrase}'")

    is_safe = len(issues) == 0
    return is_safe, issues
