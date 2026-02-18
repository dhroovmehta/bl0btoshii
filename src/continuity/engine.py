"""Continuity engine — tracks events, running gags, and character growth across episodes."""

import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
CONTINUITY_DIR = os.path.join(DATA_DIR, "continuity")

TIMELINE_FILE = os.path.join(CONTINUITY_DIR, "timeline.json")
GAGS_FILE = os.path.join(CONTINUITY_DIR, "running_gags.json")
GROWTH_FILE = os.path.join(CONTINUITY_DIR, "character_growth.json")


def _load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_timeline():
    """Load the full event timeline."""
    return _load_json(TIMELINE_FILE).get("events", [])


def get_running_gags():
    """Load all running gags."""
    return _load_json(GAGS_FILE).get("running_gags", [])


def get_character_growth():
    """Load character growth data."""
    return _load_json(GROWTH_FILE).get("character_growth", {})


def find_callback_opportunities(characters, situation, location):
    """Search for relevant callback opportunities given upcoming episode parameters.

    Searches timeline, running gags, and character growth for references
    that match the characters, situation type, or location of the new episode.

    Args:
        characters: List of character IDs (e.g., ["pens", "reows"]).
        situation: Situation type string (e.g., "misunderstanding").
        location: Location ID (e.g., "diner_interior").

    Returns:
        List of callback dicts ranked by relevance, each with:
        - source_episode: Episode ID where the event occurred
        - reference: What happened
        - suggestion: How to reference it
        - relevance_score: 0.0 to 1.0
    """
    callbacks = []

    # Search timeline events
    events = get_timeline()
    for event in events:
        score = 0.0
        # Character overlap
        event_chars = event.get("characters_involved", [])
        char_overlap = set(characters) & set(event_chars)
        if char_overlap:
            score += 0.3 * len(char_overlap)

        # Location match
        if event.get("location") == location:
            score += 0.2

        # Tag relevance — check if situation keywords match event tags
        tags = event.get("tags", [])
        situation_words = situation.lower().replace("_", " ").split()
        tag_overlap = set(situation_words) & set(tags)
        if tag_overlap:
            score += 0.2

        # High callback potential
        if event.get("callback_potential") == "high":
            score += 0.1

        if score > 0.2:
            callbacks.append({
                "source_episode": event.get("episode_id", "?"),
                "reference": event.get("event", ""),
                "suggestion": f"Reference the {event.get('event', 'event')[:50]} from {event.get('episode_id', '?')}",
                "relevance_score": min(score, 1.0),
            })

    # Search running gags
    gags = get_running_gags()
    for gag in gags:
        if gag.get("status") != "active":
            continue

        score = 0.0
        # Check if the gag description mentions any of our characters
        desc_lower = gag.get("description", "").lower()
        for char in characters:
            if char in desc_lower:
                score += 0.4

        # Gags that haven't been referenced recently get a boost
        times_ref = gag.get("times_referenced", 0)
        if times_ref < 3:
            score += 0.2
        elif times_ref > 6:
            score -= 0.1  # Avoid overusing

        if score > 0.2:
            escalation = gag.get("escalation_ideas", [])
            suggestion = escalation[0] if escalation else f"Reference the {gag.get('id', 'gag')}"
            callbacks.append({
                "source_episode": gag.get("origin_episode", "?"),
                "reference": gag.get("description", ""),
                "suggestion": suggestion,
                "relevance_score": min(score, 1.0),
            })

    # Search character growth
    growth = get_character_growth()
    for char in characters:
        char_devs = growth.get(char, {}).get("developments", [])
        for dev in char_devs[-3:]:  # Only recent developments
            callbacks.append({
                "source_episode": dev.get("episode_id", "?"),
                "reference": dev.get("development", ""),
                "suggestion": f"Build on {dev.get('development', '')[:50]}",
                "relevance_score": 0.3,
            })

    # Sort by relevance score (highest first)
    callbacks.sort(key=lambda x: x["relevance_score"], reverse=True)

    # Return top 5
    return callbacks[:5]


def log_episode(script):
    """Extract and log continuity data from a published episode script.

    Automatically called after each episode is published. Updates:
    - timeline.json with new events
    - running_gags.json with new/updated gags
    - character_growth.json with character developments

    Args:
        script: The full episode script dict.
    """
    metadata = script.get("metadata", {})
    episode_id = script.get("episode_id", "?")
    title = script.get("title", "Untitled")
    characters_featured = metadata.get("characters_featured", [])
    continuity_log = script.get("continuity_log", {})

    today = datetime.utcnow().strftime("%Y-%m-%d")

    # 1. Log timeline events
    timeline_data = _load_json(TIMELINE_FILE)
    events = timeline_data.get("events", [])

    # Extract events from continuity_log
    new_events = continuity_log.get("events", [])
    for event_text in new_events:
        # Determine location from first scene
        scenes = script.get("scenes", [])
        location = scenes[0].get("background", "unknown") if scenes else "unknown"

        events.append({
            "episode_id": episode_id,
            "episode_title": title,
            "date": today,
            "event": event_text,
            "characters_involved": characters_featured,
            "location": location,
            "tags": _extract_tags(event_text),
            "callback_potential": "medium",
        })

    timeline_data["events"] = events
    _save_json(TIMELINE_FILE, timeline_data)

    # 2. Update running gags
    gags_data = _load_json(GAGS_FILE)
    gags = gags_data.get("running_gags", [])

    new_gags = continuity_log.get("new_running_gags", [])
    for gag in new_gags:
        gags.append({
            "id": gag.get("id", f"gag_{episode_id}"),
            "origin_episode": episode_id,
            "description": gag.get("description", ""),
            "last_referenced": episode_id,
            "times_referenced": 1,
            "status": "active",
            "escalation_ideas": gag.get("escalation_ideas", []),
        })

    # Update reference counts for callbacks used
    callbacks_used = continuity_log.get("callbacks_used", [])
    for cb_episode in callbacks_used:
        for gag in gags:
            if gag.get("origin_episode") == cb_episode:
                gag["times_referenced"] = gag.get("times_referenced", 0) + 1
                gag["last_referenced"] = episode_id

    gags_data["running_gags"] = gags
    _save_json(GAGS_FILE, gags_data)

    # 3. Update character growth
    growth_data = _load_json(GROWTH_FILE)
    char_growth = growth_data.get("character_growth", {})

    developments = continuity_log.get("character_developments", [])
    for dev in developments:
        char_id = dev.get("character", "")
        if char_id not in char_growth:
            char_growth[char_id] = {"developments": []}
        char_growth[char_id]["developments"].append({
            "episode_id": episode_id,
            "development": dev.get("development", ""),
            "personality_impact": dev.get("impact", ""),
        })

    growth_data["character_growth"] = char_growth
    _save_json(GROWTH_FILE, growth_data)


def _extract_tags(text):
    """Extract simple keyword tags from event text."""
    # Common words to filter out
    stop_words = {"the", "a", "an", "is", "was", "were", "has", "had", "and", "or",
                  "but", "in", "on", "at", "to", "for", "of", "with", "from", "that",
                  "this", "it", "he", "she", "they"}
    words = text.lower().split()
    tags = [w.strip(".,!?'\"") for w in words if w.strip(".,!?'\"") not in stop_words and len(w) > 2]
    return list(set(tags))[:8]
