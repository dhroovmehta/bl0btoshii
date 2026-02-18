"""Video composer — orchestrates full episode assembly from script to MP4."""

import json
import os
import shutil
import subprocess

from src.video_assembler.scene_builder import build_scene_frames, FRAME_RATE, FRAME_WIDTH, FRAME_HEIGHT
from src.audio_mixer.mixer import mix_episode_audio, generate_blip_events
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "output")
FONT_PATH = os.path.join(ASSETS_DIR, "ui", "fonts", "PressStart2P-Regular.ttf")

# End card settings
END_CARD_DURATION_SECONDS = 3
END_CARD_BG_COLOR = (26, 26, 58)
END_CARD_TEXT_COLOR = (255, 255, 255)


def _generate_end_card_frames(episode_title, episode_id, output_dir, frame_offset):
    """Generate end card frames with episode title and series branding.

    Args:
        episode_title: Episode title text.
        episode_id: e.g., "EP001"
        output_dir: Directory to save frames.
        frame_offset: Starting frame number.

    Returns:
        List of frame paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    total_frames = END_CARD_DURATION_SECONDS * FRAME_RATE

    # Load font
    try:
        title_font = ImageFont.truetype(FONT_PATH, 20)
        ep_font = ImageFont.truetype(FONT_PATH, 14)
        brand_font = ImageFont.truetype(FONT_PATH, 12)
    except OSError:
        title_font = ImageFont.load_default()
        ep_font = title_font
        brand_font = title_font

    # Load end card template or create from scratch
    template_path = os.path.join(ASSETS_DIR, "ui", "endcard_template.png")
    if os.path.exists(template_path):
        base = Image.open(template_path).convert("RGB")
        if base.size != (FRAME_WIDTH, FRAME_HEIGHT):
            base = base.resize((FRAME_WIDTH, FRAME_HEIGHT), Image.NEAREST)
    else:
        base = Image.new("RGB", (FRAME_WIDTH, FRAME_HEIGHT), END_CARD_BG_COLOR)

    draw = ImageDraw.Draw(base)

    # Draw episode ID
    ep_text = episode_id
    ep_bbox = draw.textbbox((0, 0), ep_text, font=ep_font)
    ep_w = ep_bbox[2] - ep_bbox[0]
    draw.text(((FRAME_WIDTH - ep_w) // 2, 800), ep_text, fill=END_CARD_TEXT_COLOR, font=ep_font)

    # Draw title (word-wrapped)
    max_title_width = FRAME_WIDTH - 200
    words = episode_title.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=title_font)
        if bbox[2] - bbox[0] <= max_title_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    y = 860
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        w = bbox[2] - bbox[0]
        draw.text(((FRAME_WIDTH - w) // 2, y), line, fill=END_CARD_TEXT_COLOR, font=title_font)
        y += 30

    # Brand text
    brand = "BLOBTOSHI"
    brand_bbox = draw.textbbox((0, 0), brand, font=brand_font)
    brand_w = brand_bbox[2] - brand_bbox[0]
    draw.text(((FRAME_WIDTH - brand_w) // 2, 1050), brand, fill=(150, 150, 200), font=brand_font)

    # Save the same frame for all end card frames (static)
    frame_paths = []
    for i in range(total_frames):
        global_num = frame_offset + i
        path = os.path.join(output_dir, f"frame_{global_num:05d}.png")
        base.save(path)
        frame_paths.append(path)

    return frame_paths


def compose_episode(script, music_path=None, output_name=None):
    """Compose a full episode video from a script.

    Full pipeline:
    1. Build frames for each scene (backgrounds + characters + text boxes)
    2. Generate end card frames
    3. Mix audio (music + SFX + text blips)
    4. Combine frames into video via FFmpeg
    5. Mux audio onto video

    Args:
        script: Full episode script dict.
        music_path: Path to background music. If None, uses main_theme.
        output_name: Output filename (without extension). Defaults to episode_id.

    Returns:
        Path to the final MP4 file.
    """
    episode_id = script.get("episode_id", "EP000")
    title = script.get("title", "Untitled Episode")
    scenes = script.get("scenes", [])

    if output_name is None:
        output_name = episode_id.lower()

    # Create working directories
    episode_dir = os.path.join(OUTPUT_DIR, output_name)
    frames_dir = os.path.join(episode_dir, "frames")
    audio_dir = os.path.join(episode_dir, "audio")
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    # Default music
    if music_path is None:
        music_path = os.path.join(ASSETS_DIR, "music", "main_theme.wav")

    print(f"[Composer] Building {episode_id}: {title}")

    # 1. Build scene frames
    all_frame_paths = []
    all_sfx_events = []
    frame_offset = 0

    for i, scene in enumerate(scenes):
        print(f"[Composer]   Scene {i+1}/{len(scenes)}: {scene.get('description', '')[:50]}...")
        scene_dir = os.path.join(frames_dir, f"scene_{i:02d}")

        scene_frames, sfx_events, blip_events = build_scene_frames(
            scene, scene_dir, frame_offset=frame_offset
        )

        all_frame_paths.extend(scene_frames)
        all_sfx_events.extend(sfx_events)
        frame_offset += len(scene_frames)

    # 2. Generate end card
    print("[Composer]   Generating end card...")
    endcard_dir = os.path.join(frames_dir, "endcard")
    endcard_frames = _generate_end_card_frames(title, episode_id, endcard_dir, frame_offset)
    all_frame_paths.extend(endcard_frames)

    # 3. Copy all frames to a single sequential directory for FFmpeg
    final_frames_dir = os.path.join(episode_dir, "final_frames")
    os.makedirs(final_frames_dir, exist_ok=True)

    for idx, src_path in enumerate(all_frame_paths):
        dst_path = os.path.join(final_frames_dir, f"frame_{idx:05d}.png")
        if os.path.abspath(src_path) != os.path.abspath(dst_path):
            shutil.copy2(src_path, dst_path)

    total_frames = len(all_frame_paths)
    total_duration_ms = int((total_frames / FRAME_RATE) * 1000)
    print(f"[Composer]   Total frames: {total_frames} ({total_duration_ms}ms)")

    # 4. Mix audio
    print("[Composer]   Mixing audio...")
    blip_events = generate_blip_events(script, FRAME_RATE)
    audio_path = os.path.join(audio_dir, "mixed_audio.wav")
    mix_episode_audio(
        script=script,
        music_path=music_path,
        sfx_events=all_sfx_events,
        blip_events=blip_events,
        total_duration_ms=total_duration_ms,
        output_path=audio_path,
    )

    # 5. Render frames to video via FFmpeg
    print("[Composer]   Encoding video...")
    temp_video_path = os.path.join(episode_dir, "temp_video.mp4")
    final_video_path = os.path.join(episode_dir, f"{output_name}.mp4")

    # Frames to video (no audio)
    ffmpeg_frames_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FRAME_RATE),
        "-i", os.path.join(final_frames_dir, "frame_%05d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "18",
        temp_video_path,
    ]

    result = subprocess.run(ffmpeg_frames_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[Composer] FFmpeg frames error: {result.stderr[:500]}")
        raise RuntimeError(f"FFmpeg frame encoding failed: {result.stderr[:200]}")

    # 6. Mux audio onto video
    print("[Composer]   Muxing audio...")
    ffmpeg_mux_cmd = [
        "ffmpeg", "-y",
        "-i", temp_video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        final_video_path,
    ]

    result = subprocess.run(ffmpeg_mux_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[Composer] FFmpeg mux error: {result.stderr[:500]}")
        raise RuntimeError(f"FFmpeg audio muxing failed: {result.stderr[:200]}")

    # Clean up temp video
    if os.path.exists(temp_video_path):
        os.remove(temp_video_path)

    file_size = os.path.getsize(final_video_path)
    print(f"[Composer] Done! Output: {final_video_path} ({file_size / 1024:.1f} KB)")

    return final_video_path
