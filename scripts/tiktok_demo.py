"""TikTok Content Posting API — End-to-End Demo

Demonstrates the full OAuth + video upload flow:
1. Opens TikTok authorization in your browser
2. You authorize the app and copy the redirect URL
3. Script exchanges the auth code for an access token
4. Script uploads a test video via the Content Posting API

Usage:
    python scripts/tiktok_demo.py
"""

import os
import sys
import json
import webbrowser
import urllib.parse
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
REDIRECT_URI = "https://dhroovmehta.github.io/bl0btoshii-legal/callback/"
VIDEO_PATH = os.path.join(os.path.dirname(__file__), "test_upload.mp4")

SCOPES = "user.info.basic,video.upload,video.publish"

# TikTok API endpoints
AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"
UPLOAD_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"


def print_step(step_num, message):
    print(f"\n{'='*60}")
    print(f"  STEP {step_num}: {message}")
    print(f"{'='*60}\n")


def check_prerequisites():
    """Verify all required configuration is present."""
    print_step(0, "Checking prerequisites")

    if not CLIENT_KEY:
        print("ERROR: TIKTOK_CLIENT_KEY not set in .env")
        sys.exit(1)
    print(f"  Client Key: {CLIENT_KEY[:8]}...{CLIENT_KEY[-4:]}")

    if not CLIENT_SECRET:
        print("ERROR: TIKTOK_CLIENT_SECRET not set in .env")
        sys.exit(1)
    print(f"  Client Secret: {'*' * 16}")

    if not os.path.exists(VIDEO_PATH):
        print(f"ERROR: Test video not found at {VIDEO_PATH}")
        sys.exit(1)
    size_kb = os.path.getsize(VIDEO_PATH) / 1024
    print(f"  Test video: {VIDEO_PATH} ({size_kb:.1f} KB)")

    print(f"  Redirect URI: {REDIRECT_URI}")
    print(f"  Scopes: {SCOPES}")
    print("\n  All prerequisites OK!")


def step1_authorize():
    """Open TikTok authorization page in browser."""
    print_step(1, "Opening TikTok Authorization")

    params = {
        "client_key": CLIENT_KEY,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "state": "bl0btoshii_demo",
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    print(f"  Opening browser to TikTok authorization page...")
    print(f"  URL: {auth_url}\n")
    webbrowser.open(auth_url)

    print("  After authorizing, you will be redirected to a callback page.")
    print("  Copy the FULL URL from your browser's address bar and paste it below.\n")

    redirect_url = input("  Paste the full redirect URL here: ").strip()

    # Extract the authorization code from the redirect URL
    parsed = urllib.parse.urlparse(redirect_url)
    query_params = urllib.parse.parse_qs(parsed.query)

    if "code" not in query_params:
        print("\n  ERROR: No authorization code found in the URL.")
        print(f"  URL params received: {query_params}")
        sys.exit(1)

    code = query_params["code"][0]
    print(f"\n  Authorization code received: {code[:10]}...")
    return code


def step2_get_access_token(auth_code):
    """Exchange authorization code for an access token."""
    print_step(2, "Exchanging code for access token")

    payload = {
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }

    print("  Sending token request to TikTok...")
    response = requests.post(TOKEN_URL, data=payload)
    data = response.json()

    if "access_token" not in data:
        print(f"\n  ERROR: Failed to get access token.")
        print(f"  Response: {json.dumps(data, indent=2)}")
        sys.exit(1)

    access_token = data["access_token"]
    open_id = data.get("open_id", "unknown")
    expires_in = data.get("expires_in", "unknown")

    print(f"  Access token received: {access_token[:10]}...")
    print(f"  Open ID: {open_id}")
    print(f"  Expires in: {expires_in} seconds")

    return access_token, open_id


def step3_get_user_info(access_token):
    """Fetch the authenticated user's basic info."""
    print_step(3, "Fetching user info")

    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    params = {
        "fields": "open_id,display_name,avatar_url",
    }

    print("  Requesting user info from TikTok...")
    response = requests.get(USER_INFO_URL, headers=headers, params=params)
    data = response.json()

    if "data" in data and "user" in data["data"]:
        user = data["data"]["user"]
        print(f"  Display Name: {user.get('display_name', 'N/A')}")
        print(f"  Open ID: {user.get('open_id', 'N/A')}")
        print(f"  Avatar: {user.get('avatar_url', 'N/A')[:50]}...")
    else:
        print(f"  Response: {json.dumps(data, indent=2)}")
        print("  (User info may be limited in sandbox mode)")


def step4_upload_video(access_token):
    """Upload a test video using the Content Posting API."""
    print_step(4, "Uploading test video to TikTok")

    video_size = os.path.getsize(VIDEO_PATH)
    print(f"  Video file: {VIDEO_PATH}")
    print(f"  Video size: {video_size} bytes")

    # Initialize the upload
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }

    init_payload = {
        "post_info": {
            "title": "bl0btoshii test upload #pixelart #animation",
            "privacy_level": "SELF_ONLY",
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": video_size,
            "total_chunk_count": 1,
        },
    }

    print("\n  Initializing video upload...")
    print(f"  Title: {init_payload['post_info']['title']}")
    print(f"  Privacy: SELF_ONLY (only you can see it)")

    response = requests.post(
        UPLOAD_INIT_URL,
        headers=headers,
        json=init_payload,
    )
    data = response.json()
    print(f"\n  Init response: {json.dumps(data, indent=2)}")

    if "data" in data and "upload_url" in data["data"]:
        upload_url = data["data"]["upload_url"]
        publish_id = data["data"].get("publish_id", "N/A")
        print(f"\n  Upload URL received!")
        print(f"  Publish ID: {publish_id}")

        # Upload the video file
        print("\n  Uploading video file...")
        upload_headers = {
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
        }

        with open(VIDEO_PATH, "rb") as f:
            upload_response = requests.put(
                upload_url,
                headers=upload_headers,
                data=f,
            )

        print(f"  Upload status: {upload_response.status_code}")
        if upload_response.status_code in (200, 201):
            print("\n  VIDEO UPLOADED SUCCESSFULLY!")
            print(f"  Publish ID: {publish_id}")
            print("  Privacy: SELF_ONLY (visible only to you)")
        else:
            print(f"  Upload response: {upload_response.text[:500]}")
    else:
        print("\n  Note: Upload initialization response above.")
        print("  In sandbox mode, some features may behave differently.")


def main():
    print("\n" + "=" * 60)
    print("  bl0btoshii — TikTok Content Posting API Demo")
    print("  Sandbox Environment")
    print("=" * 60)

    check_prerequisites()
    auth_code = step1_authorize()
    access_token, open_id = step2_get_access_token(auth_code)
    step3_get_user_info(access_token)
    step4_upload_video(access_token)

    print_step(5, "Demo Complete!")
    print("  The end-to-end flow has been demonstrated:")
    print("  1. OAuth authorization via Login Kit")
    print("  2. Access token obtained")
    print("  3. User info retrieved via user.info.basic scope")
    print("  4. Video uploaded via Content Posting API")
    print(f"\n  Access token (save to .env as TIKTOK_ACCESS_TOKEN):")
    print(f"  {access_token}")
    print()


if __name__ == "__main__":
    main()
