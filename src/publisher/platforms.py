"""Platform publishers — upload videos to TikTok, YouTube, and Instagram.

These are skeleton implementations. Each platform requires OAuth setup:
- TikTok: Content Posting API (OAuth 2.0)
- YouTube: Data API v3 (OAuth 2.0)
- Instagram: Graph API via Meta Business SDK

API keys should be configured in .env and config/platforms.yaml.
"""

import os

import yaml

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config")


def _load_platform_config():
    """Load platform configuration."""
    path = os.path.join(CONFIG_DIR, "platforms.yaml")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _is_platform_enabled(platform):
    """Check if a platform is enabled in config."""
    config = _load_platform_config()
    platform_config = config.get("platforms", {}).get(platform, {})
    return platform_config.get("enabled", False)


async def publish_to_tiktok(video_path, metadata):
    """Upload a video to TikTok.

    Args:
        video_path: Path to the MP4 file.
        metadata: TikTok metadata dict with title, description, hashtags.

    Returns:
        Dict with result: {"success": bool, "post_url": str or None, "error": str or None}
    """
    if not _is_platform_enabled("tiktok"):
        return {"success": False, "post_url": None, "error": "TikTok publishing not enabled. Configure API keys in .env and enable in config/platforms.yaml."}

    tiktok_access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
    if not tiktok_access_token:
        return {"success": False, "post_url": None, "error": "TIKTOK_ACCESS_TOKEN not set in .env"}

    # TODO: Implement TikTok Content Posting API upload
    # Docs: https://developers.tiktok.com/doc/content-posting-api-get-started
    # Steps:
    # 1. Initialize upload with POST /v2/post/publish/video/init/
    # 2. Upload video chunks
    # 3. Publish with title, description, hashtags
    # 4. Get post URL from response

    return {"success": False, "post_url": None, "error": "TikTok publisher not yet implemented. API integration pending."}


async def publish_to_youtube(video_path, metadata):
    """Upload a video to YouTube Shorts.

    Args:
        video_path: Path to the MP4 file.
        metadata: YouTube metadata dict with title, description, tags.

    Returns:
        Dict with result: {"success": bool, "post_url": str or None, "error": str or None}
    """
    if not _is_platform_enabled("youtube"):
        return {"success": False, "post_url": None, "error": "YouTube publishing not enabled. Configure API keys in .env and enable in config/platforms.yaml."}

    youtube_api_key = os.getenv("YOUTUBE_API_KEY")
    if not youtube_api_key:
        return {"success": False, "post_url": None, "error": "YOUTUBE_API_KEY not set in .env"}

    # TODO: Implement YouTube Data API v3 upload
    # Docs: https://developers.google.com/youtube/v3/guides/uploading_a_video
    # Steps:
    # 1. Authenticate with OAuth 2.0
    # 2. Upload video with snippet (title, description, tags)
    # 3. Set privacy to "public" and category to "Entertainment"
    # 4. Get video URL from response

    return {"success": False, "post_url": None, "error": "YouTube publisher not yet implemented. API integration pending."}


async def publish_to_instagram(video_path, metadata):
    """Upload a video to Instagram Reels.

    Args:
        video_path: Path to the MP4 file.
        metadata: Instagram metadata dict with caption, hashtags.

    Returns:
        Dict with result: {"success": bool, "post_url": str or None, "error": str or None}
    """
    if not _is_platform_enabled("instagram"):
        return {"success": False, "post_url": None, "error": "Instagram publishing not enabled. Configure API keys in .env and enable in config/platforms.yaml."}

    ig_access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    if not ig_access_token:
        return {"success": False, "post_url": None, "error": "INSTAGRAM_ACCESS_TOKEN not set in .env"}

    # TODO: Implement Instagram Graph API upload
    # Docs: https://developers.facebook.com/docs/instagram-api/guides/content-publishing
    # Steps:
    # 1. Create media container with video URL
    # 2. Wait for container to finish processing
    # 3. Publish the container
    # 4. Get post URL from response

    return {"success": False, "post_url": None, "error": "Instagram publisher not yet implemented. API integration pending."}


async def publish_to_all(video_path, metadata, slots=None):
    """Publish to all enabled platforms.

    Args:
        video_path: Path to the MP4 file.
        metadata: Full metadata dict from generate_metadata().
        slots: Optional scheduling slots (not used yet — publishes immediately).

    Returns:
        Dict of platform → result.
    """
    results = {}

    results["tiktok"] = await publish_to_tiktok(video_path, metadata.get("tiktok", {}))
    results["youtube"] = await publish_to_youtube(video_path, metadata.get("youtube", {}))
    results["instagram"] = await publish_to_instagram(video_path, metadata.get("instagram", {}))

    return results
