"""Audio mixer — combines background music, SFX, and text blips into a single WAV."""

import json
import os
from pydub import AudioSegment

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

# Default volume levels (dB)
MUSIC_VOLUME_DB = -12.0
SFX_VOLUME_DB = -3.0
BLIP_VOLUME_DB = -6.0


def _load_character_blips():
    """Load character → blip sound mapping from characters.json."""
    with open(os.path.join(DATA_DIR, "characters.json"), "r") as f:
        characters = json.load(f)["characters"]
    return {cid: c.get("text_blip_sound", "text_blip_mid.wav") for cid, c in characters.items()}


def _load_audio(path):
    """Load an audio file, return None if not found."""
    if not os.path.exists(path):
        return None
    return AudioSegment.from_file(path)


def mix_episode_audio(
    script,
    music_path,
    sfx_events=None,
    blip_events=None,
    total_duration_ms=None,
    output_path="output/mixed_audio.wav",
    music_volume_db=MUSIC_VOLUME_DB,
    sfx_volume_db=SFX_VOLUME_DB,
    blip_volume_db=BLIP_VOLUME_DB,
):
    """Mix background music, SFX, and text blips into a single audio file.

    Args:
        script: Episode script dict (used for duration calculation).
        music_path: Path to background music WAV/MP3.
        sfx_events: List of (timestamp_ms, sfx_filename) tuples.
        blip_events: List of (timestamp_ms, blip_filename) tuples.
        total_duration_ms: Total episode duration in ms. If None, calculated from script.
        output_path: Where to save the mixed audio.
        music_volume_db: Music volume adjustment in dB.
        sfx_volume_db: SFX volume adjustment in dB.
        blip_volume_db: Text blip volume adjustment in dB.

    Returns:
        Path to the mixed audio WAV file.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if sfx_events is None:
        sfx_events = []
    if blip_events is None:
        blip_events = []

    # Calculate total duration from script if not provided
    if total_duration_ms is None:
        total_duration_ms = 0
        for scene in script.get("scenes", []):
            total_duration_ms += scene.get("duration_seconds", 8) * 1000

    # 1. Load and prepare background music
    music = _load_audio(music_path)
    if music is None:
        # Create silence as fallback
        music = AudioSegment.silent(duration=total_duration_ms)
    else:
        # Loop music if shorter than episode
        if len(music) < total_duration_ms:
            loops_needed = (total_duration_ms // len(music)) + 1
            music = music * loops_needed
        # Trim to exact duration
        music = music[:total_duration_ms]

    # Apply volume adjustment
    music = music.apply_gain(music_volume_db)

    # 2. Create the mix track starting with music
    mix = music

    # 3. Overlay SFX at their trigger timestamps
    sfx_dir = os.path.join(ASSETS_DIR, "sfx")
    for timestamp_ms, sfx_filename in sfx_events:
        if not sfx_filename:
            continue
        sfx_path = os.path.join(sfx_dir, sfx_filename)
        if not sfx_filename.endswith(".wav"):
            sfx_path = os.path.join(sfx_dir, f"{sfx_filename}.wav")
        sfx = _load_audio(sfx_path)
        if sfx is None:
            continue
        sfx = sfx.apply_gain(sfx_volume_db)
        # Ensure we don't overlay past the end
        if timestamp_ms < len(mix):
            mix = mix.overlay(sfx, position=int(timestamp_ms))

    # 4. Overlay text blips at their timestamps
    for timestamp_ms, blip_filename in blip_events:
        if not blip_filename:
            continue
        blip_path = os.path.join(sfx_dir, blip_filename)
        if not blip_filename.endswith(".wav"):
            blip_path = os.path.join(sfx_dir, f"{blip_filename}.wav")
        blip = _load_audio(blip_path)
        if blip is None:
            continue
        blip = blip.apply_gain(blip_volume_db)
        if timestamp_ms < len(mix):
            mix = mix.overlay(blip, position=int(timestamp_ms))

    # 5. Export mixed audio
    mix.export(output_path, format="wav")
    return output_path


def generate_blip_events(script, frame_rate=30):
    """Generate text blip event timestamps from a script's dialogue.

    Creates a blip sound for each character of dialogue during the typewriter
    animation, synced to the frame-by-frame timing.

    Args:
        script: Episode script dict with scenes containing dialogue.
        frame_rate: Video frame rate.

    Returns:
        List of (timestamp_ms, blip_filename) tuples.
    """
    char_blips = _load_character_blips()
    blip_events = []
    scene_start_ms = 0

    for scene in script.get("scenes", []):
        duration_s = scene.get("duration_seconds", 8)
        dialogue = scene.get("dialogue", [])

        # Dialogue starts 1 second into the scene
        dialogue_offset_ms = 1000
        chars_per_second = 20
        ms_per_char = 1000.0 / chars_per_second

        for line in dialogue:
            char_id = line.get("character", "pens")
            text = line.get("text", "")
            blip_file = char_blips.get(char_id, "text_blip_mid.wav")

            # Generate a blip for every Nth character (not every char — too rapid)
            blip_interval = 3  # One blip every 3 characters
            for i, ch in enumerate(text):
                if ch == " ":
                    continue
                if i % blip_interval == 0:
                    char_time_ms = scene_start_ms + dialogue_offset_ms + (i * ms_per_char)
                    blip_events.append((char_time_ms, blip_file))

            # Advance dialogue offset for next line
            line_duration_ms = line.get("duration_ms", len(text) * ms_per_char + 500)
            dialogue_offset_ms += line_duration_ms

        scene_start_ms += duration_s * 1000

    return blip_events
