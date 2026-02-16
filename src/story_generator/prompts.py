"""Claude prompt construction for story generation and editing."""

import json
import os
from datetime import datetime

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "templates")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def _load_template(filename):
    path = os.path.join(TEMPLATES_DIR, filename)
    with open(path, "r") as f:
        return f.read()


def _load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r") as f:
        return json.load(f)


def build_story_prompt(idea, episode_id):
    """Build the full Claude prompt for generating an episode script.

    Args:
        idea: Dict from slot_machine.generate_daily_ideas()
        episode_id: str like "EP001"

    Returns:
        The complete prompt string to send to Claude.
    """
    template = _load_template("claude_story_prompt.txt")
    characters_data = _load_json("characters.json")["characters"]
    locations_data = _load_json("locations.json")["locations"]
    situations_data = _load_json("situations.json")["situations"]
    punchlines_data = _load_json("punchlines.json")["punchline_types"]

    char_a = idea["character_a"]
    char_b = idea["character_b"]
    additional = idea.get("additional_characters", [])
    all_chars = [char_a, char_b] + additional
    location = idea["location"]
    situation = idea["situation"]
    punchline_type = idea["punchline_type"]

    # Build character descriptions
    char_descriptions = []
    for cid in all_chars:
        c = characters_data[cid]
        char_descriptions.append(
            f"**{c['nickname']}** ({c['animal']}) — {c['archetype']}\n"
            f"  Comedy function: {c['comedy_function']}\n"
            f"  Dialogue style: {c['dialogue_style']}\n"
            f"  Catchphrases: {', '.join(c['catchphrases'][:3])}\n"
            f"  Sprite states: {', '.join(c['sprite_states'])}\n"
            f"  Text blip: {c['text_blip_sound']}"
        )
    character_data_str = "\n\n".join(char_descriptions)

    # Build character names for description
    char_names = " + ".join([characters_data[c]["nickname"] for c in all_chars])

    # Location details
    loc = locations_data[location]
    loc_desc = f"{loc['name']}: {loc['description']}\nPositions: {json.dumps(loc['character_positions'], indent=2)}"

    # Situation and punchline
    sit = situations_data[situation]
    punch = punchlines_data[punchline_type]

    # Trending and seasonal sections
    trending = idea.get("trending_tie_in")
    trending_section = f"Trending Tie-in: {trending}" if trending else "Trending Tie-in: None"
    seasonal = idea.get("seasonal_theme")
    seasonal_section = f"Seasonal Theme: {seasonal}" if seasonal else "Seasonal Theme: None"

    # Continuity callbacks
    callbacks = idea.get("continuity_callbacks", [])
    if callbacks:
        continuity_section = "Continuity Callbacks:\n" + "\n".join(
            [f"  - {cb.get('reference', '')} (from {cb.get('episode_id', '?')})" for cb in callbacks]
        )
    else:
        continuity_section = "Continuity Callbacks: None (this is an early episode)"

    now = datetime.utcnow().isoformat() + "Z"

    prompt = template.format(
        characters_description=char_names,
        location_description=f"{loc['name']} — {loc['description']}",
        situation_description=f"{sit['name']}: {sit['description']}",
        punchline_description=f"{punch['name']}: {punch['description']}. Execution: {punch['execution']}",
        duration_target=35,
        trending_section=trending_section,
        seasonal_section=seasonal_section,
        continuity_section=continuity_section,
        character_data=character_data_str,
        episode_id=episode_id,
        created_at=now,
        character_a=char_a,
        character_b=char_b,
        location=location,
        situation=situation,
        punchline_type=punchline_type,
        trending_tie_in=json.dumps(trending),
        seasonal_theme=json.dumps(seasonal),
        continuity_callbacks=json.dumps(callbacks),
    )

    return prompt


def build_edit_prompt(original_script, edit_notes):
    """Build the Claude prompt for interpreting edit notes and revising a script.

    Args:
        original_script: The current script dict.
        edit_notes: Freeform text from the user.

    Returns:
        The complete prompt string to send to Claude.
    """
    template = _load_template("claude_edit_prompt.txt")
    characters_data = _load_json("characters.json")["characters"]

    # Build character data for relevant characters
    featured = original_script.get("metadata", {}).get("characters_featured", [])
    char_descriptions = []
    for cid in featured:
        if cid in characters_data:
            c = characters_data[cid]
            char_descriptions.append(
                f"**{c['nickname']}** ({c['animal']})\n"
                f"  Dialogue style: {c['dialogue_style']}\n"
                f"  Catchphrases: {', '.join(c['catchphrases'][:3])}"
            )

    prompt = template.format(
        original_script_json=json.dumps(original_script, indent=2),
        edit_notes=edit_notes,
        character_data="\n\n".join(char_descriptions),
    )

    return prompt
