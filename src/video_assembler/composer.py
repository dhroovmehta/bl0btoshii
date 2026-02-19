"""Video composer — orchestrates full episode assembly from script to MP4.

v2 changes:
- Frame streaming: pipes raw pixel data to FFmpeg stdin (no intermediate PNGs)
- 16:9 horizontal format (1920x1080) as default, with dual format support
- End card generator yields PIL Images
- Eliminates disk I/O for thousands of frame PNGs
- Optional render_config for horizontal/vertical output
"""

import os
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


def generate_end_card_frames(episode_title, episode_id, render_config=None):
    """Generate end card frames as a generator of PIL Images.

    Args:
        episode_title: Episode title text.
        episode_id: e.g., "EP001"
        render_config: Optional RenderConfig for dual format. Defaults to HORIZONTAL.

    Yields:
        PIL Image (RGB, config width x height) for each frame.
    """
    # Resolve dimensions from render_config or module defaults
    if render_config is not None:
        fw = render_config.width
        fh = render_config.height
    else:
        fw = FRAME_WIDTH
        fh = FRAME_HEIGHT

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
        if base.size != (fw, fh):
            base = base.resize((fw, fh), Image.NEAREST)
    else:
        base = Image.new("RGB", (fw, fh), END_CARD_BG_COLOR)

    draw = ImageDraw.Draw(base)

    # Center vertically — episode ID at ~40%, title at ~50%, brand at ~65%
    center_y = fh // 2

    # Draw episode ID
    ep_text = episode_id
    ep_bbox = draw.textbbox((0, 0), ep_text, font=ep_font)
    ep_w = ep_bbox[2] - ep_bbox[0]
    draw.text(((fw - ep_w) // 2, center_y - 80), ep_text, fill=END_CARD_TEXT_COLOR, font=ep_font)

    # Draw title (word-wrapped)
    max_title_width = fw - 400
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

    y = center_y - 40
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        w = bbox[2] - bbox[0]
        draw.text(((fw - w) // 2, y), line, fill=END_CARD_TEXT_COLOR, font=title_font)
        y += 30

    # Brand text
    brand = "BLOBTOSHI"
    brand_bbox = draw.textbbox((0, 0), brand, font=brand_font)
    brand_w = brand_bbox[2] - brand_bbox[0]
    draw.text(((fw - brand_w) // 2, center_y + 80), brand, fill=(150, 150, 200), font=brand_font)

    # Yield the same frame for all end card frames (static)
    for _ in range(total_frames):
        yield base.copy()


def compose_episode(script, music_path=None, output_name=None, render_config=None):
    """Compose a full episode video from a script.

    v2 pipeline:
    1. Stream scene frames directly to FFmpeg via stdin (no PNGs on disk)
    2. Generate end card frames in-memory
    3. Mix audio (music + SFX + text blips)
    4. Mux audio onto video

    Args:
        script: Full episode script dict.
        music_path: Path to background music. If None, uses main_theme.
        output_name: Output filename (without extension). Defaults to episode_id.
        render_config: Optional RenderConfig for dual format. Defaults to HORIZONTAL.

    Returns:
        Path to the final MP4 file.
    """
    # Resolve dimensions from render_config or module defaults
    if render_config is not None:
        fw = render_config.width
        fh = render_config.height
        format_label = render_config.label
    else:
        fw = FRAME_WIDTH
        fh = FRAME_HEIGHT
        format_label = None

    episode_id = script.get("episode_id", "EP000")
    title = script.get("title", "Untitled Episode")
    scenes = script.get("scenes", [])

    if output_name is None:
        output_name = episode_id.lower()

    # Append format label to output name when render_config is explicit
    if format_label:
        full_output_name = f"{output_name}_{format_label}"
    else:
        full_output_name = output_name

    # Create working directories
    episode_dir = os.path.join(OUTPUT_DIR, full_output_name)
    audio_dir = os.path.join(episode_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    # Default music
    if music_path is None:
        music_path = os.path.join(ASSETS_DIR, "music", "main_theme.wav")

    print(f"[Composer] Building {episode_id}: {title} ({format_label or 'default'})")

    # Collect scene generators and metadata before starting FFmpeg
    scene_data = []
    all_sfx_events = []
    total_frame_count = 0

    for i, scene in enumerate(scenes):
        print(f"[Composer]   Scene {i+1}/{len(scenes)}: {scene.get('action_description', scene.get('description', ''))[:50]}...")
        frame_iter, num_frames, sfx_events = build_scene_frames(
            scene, frame_offset=total_frame_count, render_config=render_config
        )
        scene_data.append((frame_iter, num_frames))
        all_sfx_events.extend(sfx_events)
        total_frame_count += num_frames

    # End card
    end_card_frames = END_CARD_DURATION_SECONDS * FRAME_RATE
    total_frame_count += end_card_frames

    total_duration_ms = int((total_frame_count / FRAME_RATE) * 1000)
    print(f"[Composer]   Total frames: {total_frame_count} ({total_duration_ms}ms)")

    # Mix audio
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

    # Stream frames to FFmpeg
    print("[Composer]   Encoding video (streaming)...")
    temp_video_path = os.path.join(episode_dir, "temp_video.mp4")
    final_video_path = os.path.join(episode_dir, f"{full_output_name}.mp4")

    # FFmpeg process reads raw RGB frames from stdin
    ffmpeg_proc = subprocess.Popen(
        [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{fw}x{fh}",
            "-pix_fmt", "rgb24",
            "-r", str(FRAME_RATE),
            "-i", "pipe:0",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-crf", "18",
            temp_video_path,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    frames_written = 0

    # Stream scene frames
    for frame_iter, num_frames in scene_data:
        for frame in frame_iter:
            # Ensure frame is RGB and correct size
            if frame.mode != "RGB":
                frame = frame.convert("RGB")
            if frame.size != (fw, fh):
                frame = frame.resize((fw, fh), Image.NEAREST)
            ffmpeg_proc.stdin.write(frame.tobytes())
            frames_written += 1

    # Stream end card frames
    print("[Composer]   Generating end card...")
    for frame in generate_end_card_frames(title, episode_id, render_config=render_config):
        if frame.mode != "RGB":
            frame = frame.convert("RGB")
        ffmpeg_proc.stdin.write(frame.tobytes())
        frames_written += 1

    # Close stdin and wait for FFmpeg to finish
    ffmpeg_proc.stdin.close()
    ffmpeg_proc.wait()
    stderr = ffmpeg_proc.stderr.read()

    if ffmpeg_proc.returncode != 0:
        print(f"[Composer] FFmpeg encoding error: {stderr.decode()[:500]}")
        raise RuntimeError(f"FFmpeg frame encoding failed: {stderr.decode()[:200]}")

    print(f"[Composer]   Frames streamed: {frames_written}")

    # Mux audio onto video
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
