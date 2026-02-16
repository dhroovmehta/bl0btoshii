"""Analytics collector — pulls performance data and auto-adjusts content weights."""

import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
WEIGHTS_FILE = os.path.join(DATA_DIR, "analytics", "content_weights.json")
EPISODES_DIR = os.path.join(DATA_DIR, "episodes")


def _load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


async def collect_episode_analytics(episode_id):
    """Pull performance data from all platforms for an episode.

    Called 24-48 hours after publishing to gather metrics.

    Args:
        episode_id: Episode ID string (e.g., "EP001").

    Returns:
        Dict with per-platform metrics:
        {
            "episode_id": str,
            "collected_at": str,
            "platforms": {
                "tiktok": {"views": int, "likes": int, "comments": int, "shares": int, ...},
                "youtube": {...},
                "instagram": {...},
            },
            "totals": {"views": int, "likes": int, ...}
        }
    """
    # Platform APIs not yet connected — return placeholder data
    # When platform publishers are implemented, this will pull real data
    placeholder = {
        "views": 0,
        "likes": 0,
        "comments": 0,
        "shares": 0,
        "avg_watch_time_seconds": 0,
        "completion_rate": 0.0,
    }

    analytics = {
        "episode_id": episode_id,
        "collected_at": datetime.utcnow().isoformat(),
        "platforms": {
            "tiktok": placeholder.copy(),
            "youtube": placeholder.copy(),
            "instagram": placeholder.copy(),
        },
        "totals": placeholder.copy(),
    }

    # Save analytics data for this episode
    ep_analytics_path = os.path.join(EPISODES_DIR, f"{episode_id}_analytics.json")
    _save_json(ep_analytics_path, analytics)

    return analytics


def update_content_weights():
    """Analyze all episode performance and update content weights.

    Adjusts weights for characters, situations, punchlines, and locations
    based on cumulative performance data. Higher-performing elements get
    slightly higher weights (boosted probability in slot machine).

    No human approval needed — runs automatically.

    Returns:
        Updated weights dict.
    """
    weights = _load_json(WEIGHTS_FILE)

    # Load all episode analytics
    all_analytics = _load_all_episode_analytics()
    if not all_analytics:
        return weights  # No data yet — keep defaults

    # Load episode index to map episodes to their content parameters
    index_path = os.path.join(EPISODES_DIR, "index.json")
    if not os.path.exists(index_path):
        return weights

    index = _load_json(index_path)
    episodes = index.get("episodes", [])

    # Build performance scores per content element
    char_scores = {}
    situation_scores = {}
    punchline_scores = {}
    location_scores = {}

    for ep in episodes:
        ep_id = ep.get("episode_id", "")
        analytics = all_analytics.get(ep_id)
        if not analytics:
            continue

        # Score = views + (likes * 2) + (comments * 3) + (shares * 5)
        totals = analytics.get("totals", {})
        score = (
            totals.get("views", 0)
            + totals.get("likes", 0) * 2
            + totals.get("comments", 0) * 3
            + totals.get("shares", 0) * 5
        )

        if score == 0:
            continue

        # Attribute score to content elements
        for char in ep.get("characters_featured", []):
            char_scores[char] = char_scores.get(char, [])
            char_scores[char].append(score)

        situation = ep.get("situation", "")
        if situation:
            situation_scores[situation] = situation_scores.get(situation, [])
            situation_scores[situation].append(score)

        punchline = ep.get("punchline_type", "")
        if punchline:
            punchline_scores[punchline] = punchline_scores.get(punchline, [])
            punchline_scores[punchline].append(score)

        location = ep.get("location", "")
        if location:
            location_scores[location] = location_scores.get(location, [])
            location_scores[location].append(score)

    # Convert scores to weights (normalized around 1.0)
    weights["character_weights"] = _scores_to_weights(
        char_scores, weights.get("character_weights", {})
    )
    weights["situation_weights"] = _scores_to_weights(
        situation_scores, weights.get("situation_weights", {})
    )
    weights["punchline_weights"] = _scores_to_weights(
        punchline_scores, weights.get("punchline_weights", {})
    )
    weights["location_weights"] = _scores_to_weights(
        location_scores, weights.get("location_weights", {})
    )

    _save_json(WEIGHTS_FILE, weights)
    return weights


def _scores_to_weights(scores_dict, existing_weights):
    """Convert performance score lists to weight values.

    Uses a conservative adjustment: weights shift slowly toward performance,
    with a floor of 0.5 and ceiling of 2.0 to prevent runaway bias.

    Args:
        scores_dict: {element_id: [score1, score2, ...]}
        existing_weights: Current weights dict.

    Returns:
        Updated weights dict.
    """
    if not scores_dict:
        return existing_weights

    # Calculate average score per element
    averages = {}
    for key, scores in scores_dict.items():
        averages[key] = sum(scores) / len(scores)

    # Normalize to mean = 1.0
    overall_mean = sum(averages.values()) / len(averages) if averages else 1.0
    if overall_mean == 0:
        return existing_weights

    updated = dict(existing_weights)
    for key, avg in averages.items():
        normalized = avg / overall_mean
        # Blend: 70% existing weight + 30% new performance signal
        old_weight = existing_weights.get(key, 1.0)
        new_weight = old_weight * 0.7 + normalized * 0.3
        # Clamp to [0.5, 2.0]
        updated[key] = max(0.5, min(2.0, new_weight))

    return updated


def _load_all_episode_analytics():
    """Load analytics data for all episodes."""
    analytics = {}
    if not os.path.exists(EPISODES_DIR):
        return analytics

    for filename in os.listdir(EPISODES_DIR):
        if filename.endswith("_analytics.json"):
            path = os.path.join(EPISODES_DIR, filename)
            data = _load_json(path)
            ep_id = data.get("episode_id", filename.replace("_analytics.json", ""))
            analytics[ep_id] = data

    return analytics


def get_analytics_summary():
    """Get a summary of all episode analytics for reporting.

    Returns:
        Dict with aggregated stats:
        {
            "total_episodes": int,
            "total_views": int,
            "total_likes": int,
            "total_comments": int,
            "total_shares": int,
            "top_episodes_by_views": list,
            "top_episodes_by_engagement": list,
            "platform_breakdown": dict,
        }
    """
    all_analytics = _load_all_episode_analytics()

    summary = {
        "total_episodes": len(all_analytics),
        "total_views": 0,
        "total_likes": 0,
        "total_comments": 0,
        "total_shares": 0,
        "top_episodes_by_views": [],
        "top_episodes_by_engagement": [],
        "platform_breakdown": {
            "tiktok": {"views": 0, "likes": 0},
            "youtube": {"views": 0, "likes": 0},
            "instagram": {"views": 0, "likes": 0},
        },
    }

    episode_scores = []

    for ep_id, data in all_analytics.items():
        totals = data.get("totals", {})
        views = totals.get("views", 0)
        likes = totals.get("likes", 0)
        comments = totals.get("comments", 0)
        shares = totals.get("shares", 0)

        summary["total_views"] += views
        summary["total_likes"] += likes
        summary["total_comments"] += comments
        summary["total_shares"] += shares

        engagement = likes + comments * 2 + shares * 3
        episode_scores.append({
            "episode_id": ep_id,
            "views": views,
            "engagement": engagement,
        })

        # Platform breakdown
        for platform in ["tiktok", "youtube", "instagram"]:
            p_data = data.get("platforms", {}).get(platform, {})
            summary["platform_breakdown"][platform]["views"] += p_data.get("views", 0)
            summary["platform_breakdown"][platform]["likes"] += p_data.get("likes", 0)

    # Sort for top episodes
    by_views = sorted(episode_scores, key=lambda x: x["views"], reverse=True)
    by_engagement = sorted(episode_scores, key=lambda x: x["engagement"], reverse=True)

    summary["top_episodes_by_views"] = by_views[:3]
    summary["top_episodes_by_engagement"] = by_engagement[:3]

    return summary
