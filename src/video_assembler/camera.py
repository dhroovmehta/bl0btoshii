"""Camera system — pan, zoom, and parallax for cinematic scene rendering.

Each scene can optionally specify camera start/end states. The camera
interpolates linearly between them over the scene's duration. Parallax
layers move at different rates relative to the camera to create depth.

Layer depth values:
  0.0 = infinitely far (layer never moves)
  0.2 = background (slow movement)
  0.5 = midground
  0.8 = foreground (fast movement)
  1.0 = character plane (moves with camera)
"""


class Camera:
    """Camera state: position in world space + zoom level."""

    __slots__ = ("x", "y", "zoom")

    def __init__(self, x=0.0, y=0.0, zoom=1.0):
        self.x = float(x)
        self.y = float(y)
        self.zoom = float(zoom)


def interpolate(start, end, t):
    """Linear interpolation between two camera states.

    Args:
        start: Camera at t=0.
        end: Camera at t=1.
        t: Progress in [0.0, 1.0].

    Returns:
        New Camera at the interpolated position.
    """
    t = max(0.0, min(1.0, t))
    return Camera(
        x=start.x + (end.x - start.x) * t,
        y=start.y + (end.y - start.y) * t,
        zoom=start.zoom + (end.zoom - start.zoom) * t,
    )


def parallax_offset(camera_x, camera_y, depth):
    """Calculate pixel offset for a parallax layer given camera position.

    Layers at depth=0 don't move. Layers at depth=1 move at full camera speed.
    In-between values create the parallax illusion of depth.

    Args:
        camera_x: Camera x position in world space.
        camera_y: Camera y position in world space.
        depth: Layer depth factor (0.0 to 1.0).

    Returns:
        (offset_x, offset_y) in pixels.
    """
    return (camera_x * depth, camera_y * depth)


def camera_from_scene(scene):
    """Extract camera start/end states from a scene dict.

    If the scene has no "camera" key, returns static camera at origin.

    Args:
        scene: Scene dict from the script.

    Returns:
        (start_camera, end_camera) tuple.
    """
    cam_spec = scene.get("camera")
    if cam_spec is None:
        static = Camera()
        return static, Camera(x=static.x, y=static.y, zoom=static.zoom)

    start_data = cam_spec.get("start", {})
    end_data = cam_spec.get("end", {})

    start = Camera(
        x=start_data.get("x", 0),
        y=start_data.get("y", 0),
        zoom=start_data.get("zoom", 1.0),
    )
    end = Camera(
        x=end_data.get("x", start.x),
        y=end_data.get("y", start.y),
        zoom=end_data.get("zoom", start.zoom),
    )
    return start, end


# Standard parallax depths for each layer type
LAYER_DEPTHS = {
    "background": 0.2,
    "midground": 0.5,
    "foreground": 0.8,
    "effects": 0.9,
}
