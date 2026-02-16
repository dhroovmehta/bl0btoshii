"""Video variant generator — creates 2-3 versions of each episode for preview selection."""

import copy
import os

from src.video_assembler.composer import compose_episode

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")

# Variant presets
VARIANT_PRESETS = [
    {
        "name": "Standard",
        "description": "Default pacing, location-default music",
        "music": "default_theme.wav",
        "pacing_multiplier": 1.0,
        "punchline_hold_seconds": 2,
    },
    {
        "name": "Upbeat",
        "description": "Alternate music, slightly faster pacing",
        "music": "action_theme.wav",
        "pacing_multiplier": 0.85,
        "punchline_hold_seconds": 1,
    },
    {
        "name": "Chill",
        "description": "Chill music, slower pacing with extended punchline hold",
        "music": "chill_theme.wav",
        "pacing_multiplier": 1.15,
        "punchline_hold_seconds": 3,
    },
]

# Music options for location-based defaults
LOCATION_MUSIC = {
    "diner_interior": "default_theme.wav",
    "town_square": "town_theme.wav",
    "beach_cove": "chill_theme.wav",
    "forest_clearing": "mystery_theme.wav",
    "hilltop_lookout": "chill_theme.wav",
    "market_stalls": "town_theme.wav",
}


def _adjust_script_pacing(script, pacing_multiplier, punchline_hold_seconds):
    """Create a copy of the script with adjusted scene durations.

    Args:
        script: Original script dict.
        pacing_multiplier: Factor to multiply scene durations by (< 1 = faster, > 1 = slower).
        punchline_hold_seconds: How long to hold the final scene's last frame.

    Returns:
        New script dict with adjusted timing.
    """
    adjusted = copy.deepcopy(script)
    scenes = adjusted.get("scenes", [])

    for i, scene in enumerate(scenes):
        original_duration = scene.get("duration_seconds", 8)
        new_duration = max(4, int(original_duration * pacing_multiplier))
        scene["duration_seconds"] = new_duration

        # Adjust dialogue timing proportionally
        for line in scene.get("dialogue", []):
            original_ms = line.get("duration_ms", 2500)
            line["duration_ms"] = max(1000, int(original_ms * pacing_multiplier))

    # Adjust the last scene's duration for punchline hold
    if scenes:
        last_scene = scenes[-1]
        base = last_scene.get("duration_seconds", 8)
        last_scene["duration_seconds"] = base + punchline_hold_seconds

    return adjusted


def _get_location_music(script):
    """Determine default music based on the primary location in the script."""
    scenes = script.get("scenes", [])
    if not scenes:
        return "default_theme.wav"

    # Use the first scene's background as primary location
    primary_location = scenes[0].get("background", "diner_interior")
    return LOCATION_MUSIC.get(primary_location, "default_theme.wav")


def generate_variants(script, count=3):
    """Generate 2-3 video variants of an episode.

    Variant 1: Standard — default pacing, location-appropriate music
    Variant 2: Upbeat — faster pacing, alternate music
    Variant 3: Chill — slower pacing, extended punchline hold, chill music

    Args:
        script: Approved episode script dict.
        count: Number of variants to generate (2-3).

    Returns:
        List of dicts with variant info:
        [{"name": str, "description": str, "video_path": str, "duration_seconds": int}]
    """
    episode_id = script.get("metadata", {}).get("episode_id", "EP000").lower()
    count = max(2, min(count, len(VARIANT_PRESETS)))
    presets = VARIANT_PRESETS[:count]

    # Override first variant's music with location-appropriate default
    location_music = _get_location_music(script)
    presets[0]["music"] = location_music

    variants = []

    for i, preset in enumerate(presets):
        variant_num = i + 1
        print(f"[Variants] Generating variant {variant_num}/{count}: {preset['name']}...")

        # Adjust script pacing
        adjusted_script = _adjust_script_pacing(
            script,
            preset["pacing_multiplier"],
            preset["punchline_hold_seconds"],
        )

        # Music path
        music_path = os.path.join(ASSETS_DIR, "music", preset["music"])
        if not os.path.exists(music_path):
            music_path = os.path.join(ASSETS_DIR, "music", "default_theme.wav")

        # Compose with unique output name
        output_name = f"{episode_id}_v{variant_num}"
        video_path = compose_episode(
            adjusted_script,
            music_path=music_path,
            output_name=output_name,
        )

        # Calculate actual duration
        total_seconds = sum(
            s.get("duration_seconds", 8)
            for s in adjusted_script.get("scenes", [])
        ) + 3  # +3 for end card

        variants.append({
            "name": f"Version {variant_num}: {preset['name']}",
            "description": preset["description"],
            "video_path": video_path,
            "duration_seconds": total_seconds,
            "preset": preset["name"].lower(),
        })

    print(f"[Variants] Done — {len(variants)} variants generated.")
    return variants


def generate_custom_variant(script, edit_notes, existing_variants):
    """Generate a custom variant by mixing attributes from existing variants.

    Parses edit notes like "music from v2, pacing from v1" and creates a new version.

    Args:
        script: Original episode script dict.
        edit_notes: Freeform text describing desired mix (e.g., "music from v2, pacing from v1").
        existing_variants: List of variant dicts from generate_variants().

    Returns:
        Dict with custom variant info: {"name": str, "description": str, "video_path": str, "duration_seconds": int}
    """
    # Default to standard preset
    music = VARIANT_PRESETS[0]["music"]
    pacing = VARIANT_PRESETS[0]["pacing_multiplier"]
    punchline_hold = VARIANT_PRESETS[0]["punchline_hold_seconds"]

    notes_lower = edit_notes.lower()

    # Parse music preference
    for i, variant in enumerate(existing_variants):
        v_num = str(i + 1)
        preset_name = variant.get("preset", "")
        if f"music from v{v_num}" in notes_lower or f"music from version {v_num}" in notes_lower:
            music = VARIANT_PRESETS[min(i, len(VARIANT_PRESETS) - 1)]["music"]
            break

    # Parse pacing preference
    for i, variant in enumerate(existing_variants):
        v_num = str(i + 1)
        if f"pacing from v{v_num}" in notes_lower or f"pacing from version {v_num}" in notes_lower:
            pacing = VARIANT_PRESETS[min(i, len(VARIANT_PRESETS) - 1)]["pacing_multiplier"]
            punchline_hold = VARIANT_PRESETS[min(i, len(VARIANT_PRESETS) - 1)]["punchline_hold_seconds"]
            break

    # Check for explicit pacing words
    if "faster" in notes_lower:
        pacing = 0.85
    elif "slower" in notes_lower:
        pacing = 1.15

    # Adjust script
    adjusted_script = _adjust_script_pacing(script, pacing, punchline_hold)

    # Music path
    music_path = os.path.join(ASSETS_DIR, "music", music)
    if not os.path.exists(music_path):
        music_path = os.path.join(ASSETS_DIR, "music", "default_theme.wav")

    # Compose custom version
    episode_id = script.get("metadata", {}).get("episode_id", "EP000").lower()
    output_name = f"{episode_id}_custom"

    print(f"[Variants] Generating custom variant: music={music}, pacing={pacing}...")
    video_path = compose_episode(
        adjusted_script,
        music_path=music_path,
        output_name=output_name,
    )

    total_seconds = sum(
        s.get("duration_seconds", 8)
        for s in adjusted_script.get("scenes", [])
    ) + 3

    return {
        "name": "Custom Version",
        "description": f"Custom: {edit_notes}",
        "video_path": video_path,
        "duration_seconds": total_seconds,
        "preset": "custom",
    }
