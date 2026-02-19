"""Scene builder — generates all frames for a single scene.

v2 changes:
- 16:9 horizontal format (1920x1080)
- Parallax multi-layer backgrounds with v1 single-file fallback
- Camera pan/zoom support
- Generator-based frame output (yields PIL Images, no disk writes)
- Position scaling from v1 (1080x1920) to v2 (1920x1080)
"""

import os
from PIL import Image
from src.video_assembler.sprite_manager import composite_character, load_sprite, resolve_scene_positions
from src.video_assembler.camera import Camera, camera_from_scene, interpolate, parallax_offset, LAYER_DEPTHS
from src.text_renderer.renderer import render_dialogue_frames

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")

# v2: 16:9 horizontal format
FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080
FRAME_RATE = 30
# Text box positioned near bottom of 16:9 frame
TEXT_BOX_Y = 880

# v1 reference size — positions in locations.json are calibrated for this
V1_REF_WIDTH = 1080
V1_REF_HEIGHT = 1920

# Parallax layer filenames in order (back to front)
PARALLAX_LAYER_NAMES = ["background.png", "midground.png", "foreground.png", "effects.png"]
PARALLAX_LAYER_DEPTHS = [
    LAYER_DEPTHS["background"],
    LAYER_DEPTHS["midground"],
    LAYER_DEPTHS["foreground"],
    LAYER_DEPTHS["effects"],
]

# Warning collection — caller can check for silent fallbacks after rendering
_warnings = []


def get_warnings():
    """Return list of warnings collected during rendering."""
    return list(_warnings)


def clear_warnings():
    """Clear the warning list. Call before starting a new render."""
    _warnings.clear()


def scale_position_v1(x, y, target_width=FRAME_WIDTH, target_height=FRAME_HEIGHT):
    """Scale a v1 position (calibrated for 1080x1920) to a new frame size.

    Args:
        x: Original x position (0-1080 range).
        y: Original y position (0-1920 range).
        target_width: Target frame width (default: 1920).
        target_height: Target frame height (default: 1080).

    Returns:
        (scaled_x, scaled_y) tuple.
    """
    return (
        int(x * target_width / V1_REF_WIDTH),
        int(y * target_height / V1_REF_HEIGHT),
    )


def load_background_layers(location_id, target_width=None, target_height=None):
    """Load background layers for a location.

    Checks for parallax folder first: assets/backgrounds/{location_id}/
    Falls back to single file: assets/backgrounds/{location_id}.png
    Last resort: solid color + warning.

    Args:
        location_id: e.g., "diner_interior"
        target_width: Target width to scale layers to. Defaults to FRAME_WIDTH.
        target_height: Target height to scale layers to. Defaults to FRAME_HEIGHT.

    Returns:
        List of PIL Images (RGBA). Single-layer for v1, multi-layer for parallax.
        All layers are scaled to target_width x target_height.
    """
    tw = target_width or FRAME_WIDTH
    th = target_height or FRAME_HEIGHT

    # Check for parallax folder first
    folder_path = os.path.join(ASSETS_DIR, "backgrounds", location_id)
    if os.path.isdir(folder_path):
        layers = []
        for layer_name in PARALLAX_LAYER_NAMES:
            layer_path = os.path.join(folder_path, layer_name)
            if os.path.exists(layer_path):
                layer = Image.open(layer_path).convert("RGBA")
                if layer.size != (tw, th):
                    layer = layer.resize((tw, th), Image.NEAREST)
                layers.append(layer)
        if layers:
            return layers

    # Fall back to single file (v1 backgrounds)
    single_path = os.path.join(ASSETS_DIR, "backgrounds", f"{location_id}.png")
    if os.path.exists(single_path):
        bg = Image.open(single_path).convert("RGBA")
        if bg.size != (tw, th):
            bg = bg.resize((tw, th), Image.NEAREST)
        return [bg]

    # Nothing found — warn and return solid color
    msg = f"[WARNING] Missing background: backgrounds/{location_id} — using solid color fallback"
    print(msg)
    _warnings.append(msg)
    return [Image.new("RGBA", (tw, th), (26, 26, 58, 255))]


def load_background(location_id):
    """Load and composite a background to FRAME_WIDTH x FRAME_HEIGHT.

    Backward-compatible wrapper: returns a single composited RGB image.
    Internally uses load_background_layers for parallax support.

    Args:
        location_id: e.g., "diner_interior"

    Returns:
        PIL Image (RGB) at FRAME_WIDTH x FRAME_HEIGHT.
    """
    layers = load_background_layers(location_id)
    # Composite layers (back to front)
    base = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (0, 0, 0, 255))
    for layer in layers:
        base = Image.alpha_composite(base, layer)
    return base.convert("RGB")


def _composite_parallax_layers(layers, camera_state, frame_width, frame_height):
    """Composite parallax layers with camera offset applied.

    Each layer scrolls at a different rate based on its depth.

    Args:
        layers: List of PIL Images (RGBA), back-to-front order.
        camera_state: Camera object with current x, y, zoom.
        frame_width: Output frame width.
        frame_height: Output frame height.

    Returns:
        PIL Image (RGBA) of the composited background.
    """
    base = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 255))

    for i, layer in enumerate(layers):
        depth = PARALLAX_LAYER_DEPTHS[i] if i < len(PARALLAX_LAYER_DEPTHS) else 0.5
        ox, oy = parallax_offset(camera_state.x, camera_state.y, depth)

        # For layers the same size as viewport, parallax offset just shifts the image.
        # Pixels that shift off-screen are lost (layer would need to be wider for full parallax).
        offset_x = -int(ox)
        offset_y = -int(oy)

        # Create a canvas and paste the layer at the offset position
        canvas = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
        canvas.paste(layer, (offset_x, offset_y), layer)
        base = Image.alpha_composite(base, canvas)

    return base


def build_scene_frames(scene, frame_offset=0, render_config=None):
    """Build all frames for a single scene.

    v2: Returns a generator of PIL Images (no disk writes), plus metadata.

    Args:
        scene: Scene dict from the script.
        frame_offset: Starting frame number (for audio sync timing).
        render_config: Optional RenderConfig for dual format. Defaults to HORIZONTAL.

    Returns:
        (frame_iter, total_frames, sfx_events) where:
        - frame_iter: generator yielding PIL Image frames (RGB, config width x height)
        - total_frames: int, total number of frames that will be yielded
        - sfx_events: list of (timestamp_ms, sfx_filename) for audio mixer
    """
    # Resolve dimensions from render_config or module defaults
    if render_config is not None:
        fw = render_config.width
        fh = render_config.height
        text_box_y = render_config.text_box_y
    else:
        fw = FRAME_WIDTH
        fh = FRAME_HEIGHT
        text_box_y = TEXT_BOX_Y

    background_id = scene.get("background", "diner_interior")
    duration_seconds = scene.get("duration_seconds", 8)
    characters_present = scene.get("characters_present", [])
    char_positions = scene.get("character_positions", {})
    char_animations = scene.get("character_animations", {})
    dialogue = scene.get("dialogue", [])
    sfx_triggers = scene.get("sfx_triggers", [])

    total_frames = duration_seconds * FRAME_RATE

    # Load background layers at the config's dimensions
    bg_layers = load_background_layers(background_id, target_width=fw, target_height=fh)

    # Get camera start/end for this scene
    cam_start, cam_end = camera_from_scene(scene)

    # Pre-render dialogue text box frames (in-memory PIL Images)
    dialogue_frame_sets = []
    for line in dialogue:
        char_id = line.get("character", "pens")
        text = line.get("text", "")
        text_frames = render_dialogue_frames(
            character_id=char_id,
            text=text,
            frame_rate=FRAME_RATE,
            render_config=render_config,
        )
        dialogue_frame_sets.append({
            "character": char_id,
            "frames": text_frames,
            "duration_ms": line.get("duration_ms", 2500),
        })

    # Calculate when each dialogue line starts
    dialogue_timeline = []
    intro_frames = FRAME_RATE  # 1 second intro before dialogue starts
    dialogue_start = intro_frames

    for dset in dialogue_frame_sets:
        line_frames = len(dset["frames"])
        dialogue_timeline.append({
            "start_frame": dialogue_start,
            "end_frame": dialogue_start + line_frames,
            "frames": dset["frames"],
            "character": dset["character"],
        })
        dialogue_start += line_frames

    # Auto-extend scene if dialogue needs more time
    min_frames_for_dialogue = dialogue_start + FRAME_RATE  # +1s buffer
    if min_frames_for_dialogue > total_frames:
        total_frames = min_frames_for_dialogue

    # Collect SFX events
    sfx_events = []
    scene_start_ms = (frame_offset / FRAME_RATE) * 1000
    for sfx in sfx_triggers:
        sfx_events.append((
            scene_start_ms + sfx.get("time_ms", 0),
            sfx.get("sfx", "")
        ))

    # Resolve all character positions and scale to target frame size
    resolved_positions = resolve_scene_positions(
        background_id, characters_present, char_positions
    )
    for char_id in resolved_positions:
        x, y = resolved_positions[char_id]
        resolved_positions[char_id] = scale_position_v1(x, y, target_width=fw, target_height=fh)

    def _frame_generator():
        """Yield one PIL Image per frame."""
        for frame_num in range(total_frames):
            # Interpolate camera position for this frame
            t = frame_num / max(total_frames - 1, 1)
            cam = interpolate(cam_start, cam_end, t)

            # Composite parallax background layers with camera offset
            frame = _composite_parallax_layers(bg_layers, cam, fw, fh)

            # Composite characters
            for char_id in characters_present:
                position = resolved_positions.get(char_id, char_positions.get(char_id, "center"))
                animation = char_animations.get(char_id, "idle")

                # Check if this character is currently speaking — use talking state
                is_speaking = False
                for dt in dialogue_timeline:
                    if dt["start_frame"] <= frame_num < dt["end_frame"] and dt["character"] == char_id:
                        is_speaking = True
                        break

                state = "talking" if is_speaking else animation
                frame = composite_character(frame, char_id, state, background_id, position)

            # Composite text box if dialogue is active
            for dt in dialogue_timeline:
                if dt["start_frame"] <= frame_num < dt["end_frame"]:
                    text_frame_idx = frame_num - dt["start_frame"]
                    if text_frame_idx < len(dt["frames"]):
                        text_box = dt["frames"][text_frame_idx]
                        if not isinstance(text_box, Image.Image):
                            text_box = Image.open(text_box).convert("RGBA")
                        else:
                            text_box = text_box.convert("RGBA")
                        # Center text box horizontally at bottom
                        tx = (fw - text_box.width) // 2
                        ty = text_box_y
                        frame.paste(text_box, (tx, ty), text_box)
                    break  # Only show one dialogue at a time

            # Yield as RGB (no alpha in final video)
            yield frame.convert("RGB")

    return _frame_generator(), total_frames, sfx_events
