"""Slot Machine — generates 2-3 episode ideas for the daily Discord post.

Picks random combinations of characters, situations, locations, and punchlines,
weighted by analytics performance data when available.
"""

import json
import os
import random
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def _load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r") as f:
        return json.load(f)


def _weighted_choice(items, weights):
    """Pick a random item weighted by performance data."""
    total = sum(weights.values())
    if total == 0:
        return random.choice(items)
    weighted_items = [(item, weights.get(item, 1.0)) for item in items]
    return random.choices(
        [i[0] for i in weighted_items],
        weights=[i[1] for i in weighted_items],
        k=1
    )[0]


def generate_daily_ideas(count=3):
    """Generate 2-3 episode idea seeds.

    Each idea is a dict with:
    - character_a, character_b (and optional additional_characters)
    - location
    - situation
    - punchline_type
    - concept (2-3 sentence summary)
    - trending_tie_in (if any)
    - continuity_callbacks (if any)

    Returns list of idea dicts.
    """
    characters_data = _load_json("characters.json")["characters"]
    situations_data = _load_json("situations.json")["situations"]
    punchlines_data = _load_json("punchlines.json")["punchline_types"]
    locations_data = _load_json("locations.json")["locations"]
    weights = _load_json("analytics/content_weights.json")

    char_ids = list(characters_data.keys())
    situation_ids = list(situations_data.keys())
    punchline_ids = list(punchlines_data.keys())
    location_ids = list(locations_data.keys())

    # Check if we need a full-cast episode this week
    needs_full_cast = _needs_full_cast_episode()

    ideas = []
    used_situations = set()
    used_pairs = set()

    for i in range(count):
        # Force one full-cast idea if needed
        if needs_full_cast and i == count - 1 and not any(
            len(idea.get("additional_characters", [])) > 2 for idea in ideas
        ):
            idea = _generate_full_cast_idea(
                char_ids, characters_data, situations_data, locations_data,
                punchlines_data, weights
            )
            ideas.append(idea)
            continue

        # Pick situation (avoid repeating)
        situation = _weighted_choice(
            [s for s in situation_ids if s not in used_situations],
            weights.get("situation_weights", {})
        )
        used_situations.add(situation)
        sit_data = situations_data[situation]

        # Pick characters — prefer the situation's best characters
        best_chars = sit_data.get("best_characters", [])
        if best_chars:
            char_a = _weighted_choice(best_chars, weights.get("character_weights", {}))
        else:
            char_a = _weighted_choice(char_ids, weights.get("character_weights", {}))

        # Pick char_b different from char_a and not a repeated pair
        remaining = [c for c in char_ids if c != char_a]
        char_b = _weighted_choice(remaining, weights.get("character_weights", {}))
        pair = tuple(sorted([char_a, char_b]))
        attempts = 0
        while pair in used_pairs and attempts < 10:
            char_b = random.choice(remaining)
            pair = tuple(sorted([char_a, char_b]))
            attempts += 1
        used_pairs.add(pair)

        # Pick location — prefer the situation's best locations
        best_locs = sit_data.get("best_locations", location_ids)
        location = _weighted_choice(best_locs, weights.get("location_weights", {}))

        # Pick punchline — prefer the punchline type's best characters
        punchline = _weighted_choice(punchline_ids, weights.get("punchline_weights", {}))

        # Build concept summary from the situation template
        templates = sit_data.get("templates", [])
        template = random.choice(templates) if templates else "{char_a} and {char_b} do something"

        char_a_name = characters_data[char_a]["nickname"]
        char_b_name = characters_data[char_b]["nickname"]
        loc_name = locations_data[location]["name"]

        concept = template.replace("{char_a}", char_a_name).replace("{char_b}", char_b_name)
        concept = concept.replace("{location}", loc_name)
        concept = concept.replace("{everyday_thing}", "something mundane")
        concept = concept.replace("{mundane_event}", "a completely normal event")
        concept = concept.replace("{char_c}", random.choice(
            [characters_data[c]["nickname"] for c in char_ids if c not in (char_a, char_b)]
        ))

        # Find continuity callbacks for this combination
        from src.continuity.engine import find_callback_opportunities
        callbacks = find_callback_opportunities([char_a, char_b], situation, location)

        # Check for seasonal/trending tie-in (only for one idea)
        trending_tie_in = None
        if i == 0:  # First idea gets trending tie-in if available
            from src.trends.seasonal import get_seasonal_theme
            seasonal = get_seasonal_theme()
            if seasonal:
                trending_tie_in = f"{seasonal['theme']}: {seasonal['story_angles'][0]}" if seasonal.get("story_angles") else seasonal.get("theme")

        idea = {
            "character_a": char_a,
            "character_b": char_b,
            "additional_characters": [],
            "location": location,
            "situation": situation,
            "punchline_type": punchline,
            "concept": concept,
            "title": f"{char_a_name} + {char_b_name} | {loc_name}",
            "trending_tie_in": trending_tie_in,
            "seasonal_theme": seasonal.get("theme") if trending_tie_in else None,
            "continuity_callbacks": [
                {"episode_id": cb["source_episode"], "reference": cb["reference"]}
                for cb in callbacks[:2]
            ],
        }
        ideas.append(idea)

    return ideas


def _generate_full_cast_idea(char_ids, characters_data, situations_data,
                              locations_data, punchlines_data, weights):
    """Generate a full-cast episode idea (all 6 characters)."""
    # Full cast works best in diner or town square
    location = random.choice(["diner_interior", "town_square"])
    situation = random.choice(["everyday_life", "scheme_adventure"])
    punchline = random.choice(["escalation", "entrance", "backfire"])

    char_a = "reows"  # Reows usually drives full-cast episodes
    char_b = "oinks"  # Oinks' diner is the gathering place

    all_names = [characters_data[c]["nickname"] for c in char_ids]
    loc_name = locations_data[location]["name"]

    return {
        "character_a": char_a,
        "character_b": char_b,
        "additional_characters": [c for c in char_ids if c not in (char_a, char_b)],
        "location": location,
        "situation": situation,
        "punchline_type": punchline,
        "concept": f"Full cast at {loc_name}. {characters_data[char_a]['nickname']} "
                   f"has a plan that pulls everyone in. Chaos ensues.",
        "title": f"Full Cast | {loc_name}",
        "trending_tie_in": None,
        "continuity_callbacks": [],
    }


def _needs_full_cast_episode():
    """Check if we need a full-cast episode this week (at least 1 per week)."""
    episodes_index_path = os.path.join(DATA_DIR, "episodes", "index.json")
    if not os.path.exists(episodes_index_path):
        return False

    with open(episodes_index_path, "r") as f:
        index = json.load(f)

    episodes = index.get("episodes", [])
    if not episodes:
        return False

    # Check episodes from the last 7 days
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    recent = [ep for ep in episodes if ep.get("created_at", "") >= week_ago]

    # If any recent episode has 4+ characters, we're good
    for ep in recent:
        if len(ep.get("characters_featured", [])) >= 4:
            return False

    return True
