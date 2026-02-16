"""Google Drive uploader — saves final episode videos to a shared Drive folder."""

import json
import logging
import os
import re

from requests.exceptions import RequestException

import requests

logger = logging.getLogger(__name__)


def format_drive_filename(episode_number, title):
    """Format a Drive-friendly filename: ep0001_short-title.mp4

    Args:
        episode_number: Integer episode number.
        title: Episode title string.

    Returns:
        Formatted filename string.
    """
    slug = title.strip().lower()
    # Remove non-alphanumeric characters (keep spaces and hyphens)
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    # Collapse whitespace and convert to hyphens
    slug = re.sub(r"\s+", "-", slug).strip("-")

    if not slug:
        slug = "untitled"

    return f"ep{episode_number:04d}_{slug}.mp4"


def _get_drive_access_token():
    """Exchange refresh token for a fresh Google access token with Drive scope."""
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
        return None, f"Failed to get Drive access token: {error_desc}"

    return data["access_token"], None


def upload_to_drive(video_path, filename):
    """Upload a video file to the configured Google Drive folder.

    Args:
        video_path: Local path to the MP4 file.
        filename: Desired filename on Drive (e.g., ep0001_the-pink-donut.mp4).

    Returns:
        Dict: {"success": bool, "file_url": str or None, "error": str or None}
    """
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        return {"success": False, "file_url": None, "error": "GOOGLE_DRIVE_FOLDER_ID not set in .env"}

    access_token, error = _get_drive_access_token()
    if error:
        return {"success": False, "file_url": None, "error": error}

    file_metadata = json.dumps({
        "name": filename,
        "parents": [folder_id],
    })

    logger.info(f"Drive upload: {filename} to folder {folder_id}")

    try:
        # Multipart upload: metadata + file content
        boundary = "mootoshi_upload_boundary"
        body = (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{file_metadata}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: video/mp4\r\n\r\n"
        ).encode("utf-8")

        with open(video_path, "rb") as f:
            video_data = f.read()

        body += video_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

        upload_response = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
            data=body,
        )
    except (RequestException, OSError) as e:
        return {"success": False, "file_url": None, "error": f"Drive upload failed: {e}"}

    if upload_response.status_code != 200:
        error_body = upload_response.text[:300]
        logger.error(f"Drive upload failed ({upload_response.status_code}): {error_body}")
        return {"success": False, "file_url": None, "error": f"Drive upload failed ({upload_response.status_code}): {error_body}"}

    result = upload_response.json()
    file_id = result.get("id", "")
    file_url = f"https://drive.google.com/file/d/{file_id}/view" if file_id else None

    logger.info(f"Drive upload success: {file_url}")
    return {"success": True, "file_url": file_url, "error": None}


def format_publishing_alert(filename, drive_url, metadata):
    """Format a Discord alert message for the #publishing-log channel.

    Args:
        filename: Drive filename (e.g., ep0001_the-pink-donut.mp4).
        drive_url: Google Drive shareable link.
        metadata: Full metadata dict from generate_metadata().

    Returns:
        Formatted Discord message string.
    """
    lines = [
        f"**New Episode Ready:** {filename}",
        f"**Google Drive:** {drive_url}",
        "",
    ]

    for platform, label in [("tiktok", "TikTok"), ("youtube", "YouTube"), ("instagram", "Instagram")]:
        data = metadata.get(platform, {})
        tags = data.get("hashtags", data.get("tags", []))
        # Show up to 5 hashtags per platform
        display_tags = " ".join(tags[:5]) if tags else "(none)"
        lines.append(f"**{label}:** {display_tags}")

    return "\n".join(lines)
