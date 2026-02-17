"""Script validator — ensures generated scripts match the PRD schema."""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

REQUIRED_TOP_KEYS = [
    "episode_id", "title", "slug", "created_at", "version",
    "generation_params", "scenes", "end_card", "continuity_log", "metadata"
]

REQUIRED_SCENE_KEYS = [
    "scene_number", "duration_seconds", "background",
    "characters_present", "action_description", "dialogue"
]

VALID_SFX = [
    "text_blip_low", "text_blip_mid", "text_blip_high",
    "text_blip_warm", "text_blip_quick", "text_blip_bold",
    "door_burst", "surprise", "sip", "cash_register",
    "magnifying_glass", "menu_select"
]

VALID_MUSIC = [
    "main_theme.wav", "tense_theme.wav", "upbeat_theme.wav"
]


def validate_script(script):
    """Validate a generated script against the PRD schema.

    Args:
        script: The script dict to validate.

    Returns:
        (is_valid, errors) — tuple of bool and list of error strings.
    """
    errors = []

    # Check top-level keys
    for key in REQUIRED_TOP_KEYS:
        if key not in script:
            errors.append(f"Missing top-level key: {key}")

    if errors:
        return False, errors

    # Check scenes
    scenes = script.get("scenes", [])
    if not scenes:
        errors.append("Script has no scenes")

    # Load valid characters and locations
    with open(os.path.join(DATA_DIR, "characters.json"), "r") as f:
        valid_chars = list(json.load(f)["characters"].keys())
    with open(os.path.join(DATA_DIR, "locations.json"), "r") as f:
        locations_data = json.load(f)["locations"]
    valid_locations = list(locations_data.keys())

    for i, scene in enumerate(scenes):
        scene_label = f"Scene {i + 1}"

        # Check required scene keys
        for key in REQUIRED_SCENE_KEYS:
            if key not in scene:
                errors.append(f"{scene_label}: missing key '{key}'")

        # Check duration
        duration = scene.get("duration_seconds", 0)
        if duration <= 0 or duration > 30:
            errors.append(f"{scene_label}: duration {duration}s seems wrong (expected 3-30s)")

        # Check background is valid location
        bg = scene.get("background", "")
        if bg and bg not in valid_locations:
            errors.append(f"{scene_label}: unknown background '{bg}'")

        # Check characters are valid
        chars_present = scene.get("characters_present", [])
        for c in chars_present:
            if c not in valid_chars:
                errors.append(f"{scene_label}: unknown character '{c}'")

        # Check character positions are valid for the location
        scene_positions = scene.get("character_positions", {})
        if bg and bg in locations_data and scene_positions:
            valid_pos_names = set(locations_data[bg].get("character_positions", {}).keys())
            for char_id, pos_name in scene_positions.items():
                if pos_name not in valid_pos_names:
                    errors.append(
                        f"{scene_label}: invalid position '{pos_name}' for {char_id} "
                        f"in {bg}. Valid positions: {', '.join(sorted(valid_pos_names))}"
                    )

        # Check dialogue
        dialogue = scene.get("dialogue", [])
        for j, line in enumerate(dialogue):
            char = line.get("character", "")
            if char and char not in valid_chars:
                errors.append(f"{scene_label}, dialogue {j + 1}: unknown character '{char}'")

            text = line.get("text", "")
            if not text:
                errors.append(f"{scene_label}, dialogue {j + 1}: empty dialogue text")

            # Check Pens' 5-word limit
            if char == "pens" and len(text.split()) > 7:
                errors.append(
                    f"{scene_label}, dialogue {j + 1}: Pens has {len(text.split())} words "
                    f"(max ~5 recommended)"
                )

    # Check total duration
    total_scene_duration = sum(s.get("duration_seconds", 0) for s in scenes)
    end_card_duration = script.get("end_card", {}).get("duration_seconds", 3)
    total = total_scene_duration + end_card_duration
    target = script.get("duration_target_seconds", 35)

    if total < target * 0.7:
        errors.append(f"Total duration ({total}s) is too short for target ({target}s)")
    elif total > target * 1.4:
        errors.append(f"Total duration ({total}s) is too long for target ({target}s)")

    # Check continuity_log
    cont = script.get("continuity_log", {})
    if not cont.get("events"):
        errors.append("continuity_log.events is empty — every episode should log at least one event")

    is_valid = len(errors) == 0
    return is_valid, errors
