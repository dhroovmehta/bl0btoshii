"""Generate 3 NES 8-bit style music loops for the Mootoshi pipeline.

Tracks (inspired by Curb Your Enthusiasm's music approach):
1. main_theme.wav   — Bouncy, playful (like "Frolic") — default for most scenes
2. tense_theme.wav  — Awkward, suspenseful underscore — for mystery/scheme scenes
3. upbeat_theme.wav — Fast, energetic transition — for action/chase moments

Uses NES-authentic sound channels:
- 2 square wave channels (melody + harmony)
- 1 triangle wave channel (bass)
"""

import os
import struct
import wave
import numpy as np

SAMPLE_RATE = 44100

# NES-style note frequencies (A4 = 440Hz)
NOTE_FREQS = {
    "C3": 130.81, "D3": 146.83, "E3": 164.81, "F3": 174.61,
    "G3": 196.00, "A3": 220.00, "Bb3": 233.08, "B3": 246.94,
    "C4": 261.63, "D4": 293.66, "Eb4": 311.13, "E4": 329.63,
    "F4": 349.23, "F#4": 369.99, "G4": 392.00, "Ab4": 415.30,
    "A4": 440.00, "Bb4": 466.16, "B4": 493.88,
    "C5": 523.25, "D5": 587.33, "Eb5": 622.25, "E5": 659.26,
    "F5": 698.46, "G5": 783.99, "A5": 880.00, "B5": 987.77,
    "C6": 1046.50,
    "R": 0,  # Rest
}


def square_wave(freq, duration, sample_rate=SAMPLE_RATE, duty=0.5, volume=0.3):
    """Generate NES-style square wave. Duty cycle 0.5 = 50% (classic NES sound)."""
    if freq == 0:
        return np.zeros(int(sample_rate * duration))
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave = np.where((t * freq) % 1.0 < duty, volume, -volume)
    return wave


def triangle_wave(freq, duration, sample_rate=SAMPLE_RATE, volume=0.35):
    """Generate NES-style triangle wave (bass channel)."""
    if freq == 0:
        return np.zeros(int(sample_rate * duration))
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave = 2 * np.abs(2 * ((t * freq) % 1.0) - 1) - 1
    return wave * volume


def apply_envelope(samples, attack=0.01, release=0.05):
    """Simple attack-release envelope to avoid clicks."""
    n = len(samples)
    attack_samples = int(SAMPLE_RATE * attack)
    release_samples = int(SAMPLE_RATE * release)
    envelope = np.ones(n)
    if attack_samples > 0 and attack_samples < n:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    if release_samples > 0 and release_samples < n:
        envelope[-release_samples:] = np.linspace(1, 0, release_samples)
    return samples * envelope


def staccato_envelope(samples, staccato=0.6):
    """Cut note short for bouncy staccato feel."""
    n = len(samples)
    cutoff = int(n * staccato)
    envelope = np.ones(n)
    fade = int(SAMPLE_RATE * 0.01)
    if cutoff < n:
        envelope[cutoff:] = 0
        if fade > 0 and cutoff > fade:
            envelope[cutoff - fade:cutoff] = np.linspace(1, 0, fade)
    envelope[:min(int(SAMPLE_RATE * 0.005), n)] = np.linspace(0, 1, min(int(SAMPLE_RATE * 0.005), n))
    return samples * envelope


def save_wav(filename, samples, sample_rate=SAMPLE_RATE):
    """Save numpy array as 16-bit WAV file."""
    # Normalize to prevent clipping
    peak = np.max(np.abs(samples))
    if peak > 0:
        samples = samples / peak * 0.8
    samples_16 = (samples * 32767).astype(np.int16)
    with wave.open(filename, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(samples_16.tobytes())


def generate_main_theme():
    """Track 1: Bouncy, playful theme — inspired by Frolic's carefree energy.

    C major, 132 BPM, staccato melody with bouncy bass.
    """
    bpm = 132
    beat = 60.0 / bpm  # duration of quarter note
    eighth = beat / 2
    sixteenth = beat / 4

    # Melody (square wave, 50% duty) — bouncy, playful, major key
    melody_notes = [
        # Bar 1 — opening bounce
        ("E5", eighth), ("R", sixteenth), ("E5", sixteenth),
        ("G5", eighth), ("E5", eighth),
        ("C5", eighth), ("D5", eighth),
        # Bar 2
        ("E5", eighth), ("R", sixteenth), ("C5", sixteenth),
        ("D5", eighth), ("E5", eighth),
        ("G5", eighth), ("R", eighth),
        # Bar 3 — playful variation
        ("A5", eighth), ("R", sixteenth), ("A5", sixteenth),
        ("G5", eighth), ("E5", eighth),
        ("F5", eighth), ("E5", eighth),
        # Bar 4
        ("D5", eighth), ("R", sixteenth), ("D5", sixteenth),
        ("E5", eighth), ("C5", eighth),
        ("D5", eighth), ("R", eighth),
        # Bar 5 — repeat with variation
        ("E5", eighth), ("R", sixteenth), ("E5", sixteenth),
        ("G5", eighth), ("E5", eighth),
        ("C5", eighth), ("D5", eighth),
        # Bar 6
        ("E5", eighth), ("G5", eighth),
        ("A5", eighth), ("G5", eighth),
        ("E5", eighth), ("R", eighth),
        # Bar 7 — descending resolution
        ("G5", eighth), ("R", sixteenth), ("F5", sixteenth),
        ("E5", eighth), ("D5", eighth),
        ("C5", eighth), ("D5", eighth),
        # Bar 8 — ending bounce
        ("E5", eighth), ("R", sixteenth), ("D5", sixteenth),
        ("C5", beat),
        ("R", eighth), ("R", eighth),
    ]

    # Harmony (square wave, 25% duty) — simple thirds/fifths
    harmony_notes = [
        # Bar 1
        ("C5", eighth), ("R", sixteenth), ("C5", sixteenth),
        ("E5", eighth), ("C5", eighth),
        ("A4", eighth), ("B4", eighth),
        # Bar 2
        ("C5", eighth), ("R", sixteenth), ("A4", sixteenth),
        ("B4", eighth), ("C5", eighth),
        ("E5", eighth), ("R", eighth),
        # Bar 3
        ("F5", eighth), ("R", sixteenth), ("F5", sixteenth),
        ("E5", eighth), ("C5", eighth),
        ("D5", eighth), ("C5", eighth),
        # Bar 4
        ("B4", eighth), ("R", sixteenth), ("B4", sixteenth),
        ("C5", eighth), ("A4", eighth),
        ("B4", eighth), ("R", eighth),
        # Bar 5
        ("C5", eighth), ("R", sixteenth), ("C5", sixteenth),
        ("E5", eighth), ("C5", eighth),
        ("A4", eighth), ("B4", eighth),
        # Bar 6
        ("C5", eighth), ("E5", eighth),
        ("F5", eighth), ("E5", eighth),
        ("C5", eighth), ("R", eighth),
        # Bar 7
        ("E5", eighth), ("R", sixteenth), ("D5", sixteenth),
        ("C5", eighth), ("B4", eighth),
        ("A4", eighth), ("B4", eighth),
        # Bar 8
        ("C5", eighth), ("R", sixteenth), ("B4", sixteenth),
        ("A4", beat),
        ("R", eighth), ("R", eighth),
    ]

    # Bass (triangle wave) — bouncy root notes
    bass_notes = [
        ("C3", beat), ("C3", beat), ("F3", beat), ("G3", beat),  # Bar 1-2 ish
        ("C3", beat), ("G3", beat), ("C3", beat), ("G3", beat),
        ("F3", beat), ("F3", beat), ("C3", beat), ("G3", beat),  # Bar 3-4 ish
        ("G3", beat), ("G3", beat), ("G3", beat), ("C3", beat),
        ("C3", beat), ("C3", beat), ("F3", beat), ("G3", beat),  # Bar 5-6
        ("C3", beat), ("G3", beat), ("A3", beat), ("G3", beat),
        ("F3", beat), ("G3", beat), ("A3", beat), ("G3", beat),  # Bar 7-8
        ("C3", beat), ("G3", beat), ("C3", beat), ("C3", beat),
    ]

    # Render channels
    melody_audio = np.array([])
    for note, dur in melody_notes:
        s = square_wave(NOTE_FREQS[note], dur, duty=0.5, volume=0.3)
        s = staccato_envelope(s, staccato=0.7)
        melody_audio = np.concatenate([melody_audio, s])

    harmony_audio = np.array([])
    for note, dur in harmony_notes:
        s = square_wave(NOTE_FREQS[note], dur, duty=0.25, volume=0.18)
        s = staccato_envelope(s, staccato=0.6)
        harmony_audio = np.concatenate([harmony_audio, s])

    bass_audio = np.array([])
    for note, dur in bass_notes:
        s = triangle_wave(NOTE_FREQS[note], dur, volume=0.35)
        s = apply_envelope(s, attack=0.01, release=0.03)
        bass_audio = np.concatenate([bass_audio, s])

    # Match lengths
    max_len = max(len(melody_audio), len(harmony_audio), len(bass_audio))
    melody_audio = np.pad(melody_audio, (0, max(0, max_len - len(melody_audio))))
    harmony_audio = np.pad(harmony_audio, (0, max(0, max_len - len(harmony_audio))))
    bass_audio = np.pad(bass_audio, (0, max(0, max_len - len(bass_audio))))

    mixed = melody_audio + harmony_audio + bass_audio
    return mixed


def generate_tense_theme():
    """Track 2: Tense, awkward underscore — suspenseful, minor key.

    D minor, 84 BPM, sustained notes with chromatic tension.
    """
    bpm = 84
    beat = 60.0 / bpm
    half = beat * 2
    eighth = beat / 2
    quarter = beat

    # Melody — sparse, creeping, minor key
    melody_notes = [
        # Bar 1 — slow creep
        ("D4", quarter), ("R", eighth), ("F4", eighth),
        ("E4", half),
        # Bar 2
        ("D4", quarter), ("R", eighth), ("Ab4", eighth),
        ("G4", quarter), ("F4", quarter),
        # Bar 3 — chromatic tension
        ("E4", quarter), ("F4", quarter),
        ("F#4", quarter), ("G4", quarter),
        # Bar 4 — unresolved
        ("Ab4", half),
        ("G4", quarter), ("R", quarter),
        # Bar 5 — repeat with higher register
        ("D5", quarter), ("R", eighth), ("F5", eighth),
        ("E5", half),
        # Bar 6
        ("D5", quarter), ("R", eighth), ("Ab4", eighth),
        ("G4", quarter), ("F4", quarter),
        # Bar 7
        ("E4", quarter), ("Eb4", quarter),
        ("D4", quarter), ("F4", quarter),
        # Bar 8 — dark resolution
        ("E4", half),
        ("D4", quarter), ("R", quarter),
    ]

    # Harmony — low sustained dissonance
    harmony_notes = [
        ("A4", half), ("R", half),
        ("Bb4", half), ("A4", half),
        ("Ab4", half), ("G4", half),
        ("F4", half), ("R", half),
        ("A4", half), ("R", half),
        ("Bb4", half), ("A4", half),
        ("Ab4", half), ("Bb4", half),
        ("A4", half), ("R", half),
    ]

    # Bass — slow, ominous pedal tones
    bass_notes = [
        ("D3", half), ("D3", half),
        ("Bb3", half), ("A3", half),
        ("C3", half), ("C3", half),
        ("D3", half), ("D3", half),
        ("D3", half), ("D3", half),
        ("Bb3", half), ("A3", half),
        ("C3", half), ("Bb3", half),
        ("A3", half), ("D3", half),
    ]

    # Render
    melody_audio = np.array([])
    for note, dur in melody_notes:
        s = square_wave(NOTE_FREQS[note], dur, duty=0.5, volume=0.25)
        s = apply_envelope(s, attack=0.05, release=0.1)
        melody_audio = np.concatenate([melody_audio, s])

    harmony_audio = np.array([])
    for note, dur in harmony_notes:
        s = square_wave(NOTE_FREQS[note], dur, duty=0.125, volume=0.12)
        s = apply_envelope(s, attack=0.08, release=0.15)
        harmony_audio = np.concatenate([harmony_audio, s])

    bass_audio = np.array([])
    for note, dur in bass_notes:
        s = triangle_wave(NOTE_FREQS[note], dur, volume=0.3)
        s = apply_envelope(s, attack=0.03, release=0.08)
        bass_audio = np.concatenate([bass_audio, s])

    max_len = max(len(melody_audio), len(harmony_audio), len(bass_audio))
    melody_audio = np.pad(melody_audio, (0, max(0, max_len - len(melody_audio))))
    harmony_audio = np.pad(harmony_audio, (0, max(0, max_len - len(harmony_audio))))
    bass_audio = np.pad(bass_audio, (0, max(0, max_len - len(bass_audio))))

    mixed = melody_audio + harmony_audio + bass_audio
    return mixed


def generate_upbeat_theme():
    """Track 3: Fast, energetic transition — upbeat action feel.

    G major, 160 BPM, rapid arpeggios and driving bass.
    """
    bpm = 160
    beat = 60.0 / bpm
    eighth = beat / 2
    sixteenth = beat / 4
    quarter = beat

    # Melody — fast, energetic arpeggios
    melody_notes = [
        # Bar 1 — driving opening
        ("G5", sixteenth), ("B5", sixteenth), ("D5", sixteenth), ("G5", sixteenth),
        ("B5", sixteenth), ("G5", sixteenth), ("D5", sixteenth), ("B4", sixteenth),
        # Bar 2
        ("C5", sixteenth), ("E5", sixteenth), ("G5", sixteenth), ("C6", sixteenth),
        ("G5", sixteenth), ("E5", sixteenth), ("C5", sixteenth), ("E5", sixteenth),
        # Bar 3
        ("D5", sixteenth), ("F#4", sixteenth), ("A4", sixteenth), ("D5", sixteenth),
        ("F#4", sixteenth), ("A4", sixteenth), ("D5", sixteenth), ("A5", sixteenth),
        # Bar 4
        ("G5", eighth), ("R", sixteenth), ("G5", sixteenth),
        ("A5", eighth), ("B5", eighth),
        # Bar 5
        ("G5", sixteenth), ("B5", sixteenth), ("D5", sixteenth), ("G5", sixteenth),
        ("E5", sixteenth), ("G5", sixteenth), ("B5", sixteenth), ("G5", sixteenth),
        # Bar 6
        ("C5", sixteenth), ("E5", sixteenth), ("G5", sixteenth), ("E5", sixteenth),
        ("C5", sixteenth), ("D5", sixteenth), ("E5", sixteenth), ("G5", sixteenth),
        # Bar 7
        ("A5", eighth), ("G5", eighth),
        ("F#4", eighth), ("G4", eighth),
        # Bar 8
        ("D5", eighth), ("B4", eighth),
        ("G4", quarter),
    ]

    # Harmony — power chords
    harmony_notes = [
        ("D5", quarter), ("D5", quarter), ("E5", quarter), ("E5", quarter),
        ("D5", quarter), ("D5", quarter), ("D5", quarter), ("D5", quarter),
        ("D5", quarter), ("D5", quarter), ("E5", quarter), ("E5", quarter),
        ("F#4", quarter), ("G4", quarter), ("B4", quarter), ("G4", quarter),
    ]

    # Bass — driving eighth notes
    bass_notes = [
        ("G3", eighth), ("G3", eighth), ("G3", eighth), ("G3", eighth),
        ("C3", eighth), ("C3", eighth), ("C3", eighth), ("C3", eighth),
        ("D3", eighth), ("D3", eighth), ("D3", eighth), ("D3", eighth),
        ("G3", eighth), ("G3", eighth), ("D3", eighth), ("G3", eighth),
        ("G3", eighth), ("G3", eighth), ("G3", eighth), ("G3", eighth),
        ("C3", eighth), ("C3", eighth), ("C3", eighth), ("C3", eighth),
        ("D3", eighth), ("D3", eighth), ("D3", eighth), ("D3", eighth),
        ("G3", eighth), ("D3", eighth), ("G3", quarter),
    ]

    # Render
    melody_audio = np.array([])
    for note, dur in melody_notes:
        s = square_wave(NOTE_FREQS[note], dur, duty=0.5, volume=0.28)
        s = staccato_envelope(s, staccato=0.8)
        melody_audio = np.concatenate([melody_audio, s])

    harmony_audio = np.array([])
    for note, dur in harmony_notes:
        s = square_wave(NOTE_FREQS[note], dur, duty=0.25, volume=0.15)
        s = staccato_envelope(s, staccato=0.7)
        harmony_audio = np.concatenate([harmony_audio, s])

    bass_audio = np.array([])
    for note, dur in bass_notes:
        s = triangle_wave(NOTE_FREQS[note], dur, volume=0.35)
        s = staccato_envelope(s, staccato=0.85)
        bass_audio = np.concatenate([bass_audio, s])

    max_len = max(len(melody_audio), len(harmony_audio), len(bass_audio))
    melody_audio = np.pad(melody_audio, (0, max(0, max_len - len(melody_audio))))
    harmony_audio = np.pad(harmony_audio, (0, max(0, max_len - len(harmony_audio))))
    bass_audio = np.pad(bass_audio, (0, max(0, max_len - len(bass_audio))))

    mixed = melody_audio + harmony_audio + bass_audio
    return mixed


if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "music")
    os.makedirs(output_dir, exist_ok=True)

    tracks = [
        ("main_theme.wav", generate_main_theme, "Bouncy/playful (Frolic-inspired)"),
        ("tense_theme.wav", generate_tense_theme, "Tense/awkward underscore"),
        ("upbeat_theme.wav", generate_upbeat_theme, "Fast/energetic transition"),
    ]

    for filename, generator, description in tracks:
        print(f"Generating: {filename} — {description}")
        audio = generator()
        path = os.path.join(output_dir, filename)
        save_wav(path, audio)
        duration = len(audio) / SAMPLE_RATE
        print(f"  Saved: {path} ({duration:.1f}s)")

    print("\nDone! Listen to the files in assets/music/")
