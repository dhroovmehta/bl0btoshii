"""YouTube Data API v3 — Upload Test

Demonstrates the video upload flow:
1. Uses refresh token to get a fresh access token
2. Uploads a test video as Private (not publicly visible)
3. Confirms the upload succeeded

Usage:
    python scripts/youtube_demo.py
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_upload.mp4")

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


def print_step(step_num, message):
    print(f"\n{'='*60}")
    print(f"  STEP {step_num}: {message}")
    print(f"{'='*60}\n")


def check_prerequisites():
    print_step(0, "Checking prerequisites")

    if not CLIENT_ID:
        print("  ERROR: GOOGLE_CLIENT_ID not set in .env")
        return False
    print(f"  Client ID: {CLIENT_ID[:20]}...")

    if not CLIENT_SECRET:
        print("  ERROR: GOOGLE_CLIENT_SECRET not set in .env")
        return False
    print(f"  Client Secret: {'*' * 16}")

    if not REFRESH_TOKEN:
        print("  ERROR: GOOGLE_REFRESH_TOKEN not set in .env")
        return False
    print(f"  Refresh Token: {REFRESH_TOKEN[:15]}...")

    if not os.path.exists(VIDEO_PATH):
        print(f"  ERROR: Test video not found at {VIDEO_PATH}")
        return False
    size_kb = os.path.getsize(VIDEO_PATH) / 1024
    print(f"  Test video: {VIDEO_PATH} ({size_kb:.1f} KB)")

    print("\n  All prerequisites OK!")
    return True


def get_access_token():
    print_step(1, "Getting fresh access token")

    print("  Exchanging refresh token for access token...")
    response = requests.post(TOKEN_URL, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    })
    data = response.json()

    if "access_token" not in data:
        print(f"  ERROR: {json.dumps(data, indent=2)}")
        return None

    access_token = data["access_token"]
    expires_in = data.get("expires_in", "unknown")
    print(f"  Access token received: {access_token[:15]}...")
    print(f"  Expires in: {expires_in} seconds")
    return access_token


def upload_video(access_token):
    print_step(2, "Uploading test video to YouTube")

    video_size = os.path.getsize(VIDEO_PATH)
    print(f"  Video file: {VIDEO_PATH}")
    print(f"  Video size: {video_size} bytes")

    metadata = {
        "snippet": {
            "title": "bl0btoshii test upload — pixel art animation",
            "description": "Test upload from the bl0btoshii automated pipeline. This video is private.",
            "tags": ["pixelart", "animation", "bl0btoshii", "test"],
            "categoryId": "1",
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
        },
    }

    print(f"  Title: {metadata['snippet']['title']}")
    print(f"  Privacy: private (only you can see it)")
    print()
    print("  Initiating resumable upload...")

    # Step 1: Initiate resumable upload
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=utf-8",
        "X-Upload-Content-Type": "video/mp4",
        "X-Upload-Content-Length": str(video_size),
    }

    init_response = requests.post(
        f"{UPLOAD_URL}?uploadType=resumable&part=snippet,status",
        headers=headers,
        json=metadata,
    )

    if init_response.status_code != 200:
        print(f"  ERROR: Init failed ({init_response.status_code})")
        print(f"  {init_response.text[:500]}")
        return None

    upload_url = init_response.headers.get("Location")
    if not upload_url:
        print("  ERROR: No upload URL in response headers")
        return None

    print(f"  Resumable upload URL received!")
    print()
    print("  Uploading video file...")

    # Step 2: Upload the video
    with open(VIDEO_PATH, "rb") as f:
        upload_response = requests.put(
            upload_url,
            headers={
                "Content-Type": "video/mp4",
                "Content-Length": str(video_size),
            },
            data=f,
        )

    if upload_response.status_code in (200, 201):
        result = upload_response.json()
        video_id = result.get("id", "unknown")
        title = result.get("snippet", {}).get("title", "unknown")
        status = result.get("status", {}).get("uploadStatus", "unknown")
        privacy = result.get("status", {}).get("privacyStatus", "unknown")

        print(f"  Upload status: {upload_response.status_code}")
        print()
        print("  VIDEO UPLOADED SUCCESSFULLY!")
        print(f"  Video ID: {video_id}")
        print(f"  Title: {title}")
        print(f"  Upload status: {status}")
        print(f"  Privacy: {privacy}")
        print(f"  URL: https://youtu.be/{video_id}")
        return video_id
    else:
        print(f"  ERROR: Upload failed ({upload_response.status_code})")
        print(f"  {upload_response.text[:500]}")
        return None


def main():
    print("\n" + "=" * 60)
    print("  bl0btoshii — YouTube Data API v3 Upload Test")
    print("=" * 60)

    if not check_prerequisites():
        return

    access_token = get_access_token()
    if not access_token:
        return

    video_id = upload_video(access_token)

    print_step(3, "Test Complete!")
    if video_id:
        print("  The YouTube upload flow works end-to-end:")
        print("  1. Refresh token exchanged for access token")
        print("  2. Video uploaded via YouTube Data API v3")
        print(f"  3. Video is live (private): https://youtu.be/{video_id}")
        print()
        print("  YouTube automation is ready for production.")
    else:
        print("  Upload failed — check the errors above.")


if __name__ == "__main__":
    main()
