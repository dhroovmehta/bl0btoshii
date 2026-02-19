"""Platform publishers — upload videos to TikTok, YouTube, and Instagram.

- TikTok: Content Posting API (OAuth 2.0) — pending approval
- YouTube: Data API v3 (OAuth 2.0) — production ready
- Instagram: Manual posting (see docs/instagram_posting_guide.md)

API keys should be configured in .env and config/platforms.yaml.
"""

import json
import logging
import os

import requests
import yaml

logger = logging.getLogger(__name__)

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


def _youtube_get_access_token():
    """Exchange refresh token for a fresh YouTube access token."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        return None, "Missing GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, or GOOGLE_REFRESH_TOKEN in .env"

    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    data = response.json()

    if "access_token" not in data:
        error_desc = data.get("error_description", data.get("error", "Unknown error"))
        return None, f"Failed to get YouTube access token: {error_desc}"

    return data["access_token"], None


async def publish_to_youtube(video_path, metadata, is_short=False):
    """Upload a video to YouTube (regular or Shorts).

    Args:
        video_path: Path to the MP4 file.
        metadata: YouTube metadata dict with title, description, tags.
        is_short: If True, ensures #Shorts tag is in description (YouTube Short).
                  If False (default), strips #Shorts from title and description
                  (regular YouTube video).

    Returns:
        Dict with result: {"success": bool, "post_url": str or None, "error": str or None}
    """
    if not _is_platform_enabled("youtube"):
        return {"success": False, "post_url": None, "error": "YouTube publishing not enabled. Configure API keys in .env and enable in config/platforms.yaml."}

    access_token, error = _youtube_get_access_token()
    if error:
        return {"success": False, "post_url": None, "error": error}

    if not os.path.exists(video_path):
        return {"success": False, "post_url": None, "error": f"Video file not found: {video_path}"}

    video_size = os.path.getsize(video_path)

    # Load platform config for privacy setting
    config = _load_platform_config()
    yt_config = config.get("platforms", {}).get("youtube", {})
    privacy = yt_config.get("privacy", "private")

    title = metadata.get("title", "bl0btoshii episode")
    description = metadata.get("description", "")
    tags = metadata.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    if is_short:
        # YouTube Short — ensure #Shorts is in description
        if "#Shorts" not in description:
            description = f"{description}\n\n#Shorts".strip()
    else:
        # Regular YouTube video — strip #Shorts from title and description
        import re
        title = re.sub(r'\s*#Shorts\b', '', title).strip()
        description = re.sub(r'\s*#Shorts\b', '', description).strip()

    video_metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "1",  # Film & Animation
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    logger.info(f"YouTube upload: '{title}' ({video_size} bytes, privacy={privacy})")

    # Step 1: Initiate resumable upload
    try:
        init_response = requests.post(
            "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8",
                "X-Upload-Content-Type": "video/mp4",
                "X-Upload-Content-Length": str(video_size),
            },
            json=video_metadata,
        )
    except requests.RequestException as e:
        return {"success": False, "post_url": None, "error": f"YouTube init request failed: {e}"}

    if init_response.status_code != 200:
        error_body = init_response.text[:300]
        logger.error(f"YouTube init failed ({init_response.status_code}): {error_body}")
        return {"success": False, "post_url": None, "error": f"YouTube init failed ({init_response.status_code}): {error_body}"}

    upload_url = init_response.headers.get("Location")
    if not upload_url:
        return {"success": False, "post_url": None, "error": "No upload URL in YouTube response headers"}

    # Step 2: Upload the video file
    try:
        with open(video_path, "rb") as f:
            upload_response = requests.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(video_size),
                },
                data=f,
            )
    except requests.RequestException as e:
        return {"success": False, "post_url": None, "error": f"YouTube upload request failed: {e}"}

    if upload_response.status_code not in (200, 201):
        error_body = upload_response.text[:300]
        logger.error(f"YouTube upload failed ({upload_response.status_code}): {error_body}")
        return {"success": False, "post_url": None, "error": f"YouTube upload failed ({upload_response.status_code}): {error_body}"}

    result = upload_response.json()
    video_id = result.get("id", "")
    post_url = f"https://youtu.be/{video_id}" if video_id else None

    logger.info(f"YouTube upload success: {post_url}")
    return {"success": True, "post_url": post_url, "error": None}


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
