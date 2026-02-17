"""Tests for Google Drive upload module.

Tests cover:
- format_drive_filename: episode number + slugified title
- upload_to_drive: OAuth token refresh, file upload, shareable link
- format_publishing_alert: Discord alert message with Drive link + hashtags
"""

import os
from io import BytesIO
from unittest.mock import patch, MagicMock, mock_open

import pytest

from src.publisher.drive import (
    format_drive_filename,
    upload_to_drive,
    format_publishing_alert,
)


# ---------------------------------------------------------------------------
# format_drive_filename
# ---------------------------------------------------------------------------

class TestFormatDriveFilename:
    """Test Drive filename generation: ep0001_short-title.mp4"""

    def test_basic_format(self):
        result = format_drive_filename(1, "The Pink Donut")
        assert result == "ep0001_the-pink-donut.mp4"

    def test_episode_number_padding(self):
        result = format_drive_filename(42, "Test Title")
        assert result == "ep0042_test-title.mp4"

    def test_large_episode_number(self):
        result = format_drive_filename(1234, "Big Number")
        assert result == "ep1234_big-number.mp4"

    def test_special_characters_removed(self):
        result = format_drive_filename(1, "Pens's Big Day! (Part 1)")
        assert result == "ep0001_penss-big-day-part-1.mp4"

    def test_multiple_spaces_collapsed(self):
        result = format_drive_filename(1, "Too   Many   Spaces")
        assert result == "ep0001_too-many-spaces.mp4"

    def test_leading_trailing_hyphens_stripped(self):
        result = format_drive_filename(1, "  Extra Whitespace  ")
        assert result == "ep0001_extra-whitespace.mp4"

    def test_empty_title_fallback(self):
        result = format_drive_filename(1, "")
        assert result == "ep0001_untitled.mp4"

    def test_unicode_characters(self):
        result = format_drive_filename(1, "Café Adventures")
        assert result == "ep0001_caf-adventures.mp4"


# ---------------------------------------------------------------------------
# upload_to_drive
# ---------------------------------------------------------------------------

class TestUploadToDrive:
    """Test Google Drive file upload."""

    @patch.dict(os.environ, {
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "GOOGLE_REFRESH_TOKEN": "test-refresh-token",
        "GOOGLE_DRIVE_FOLDER_ID": "test-folder-id",
    })
    @patch("builtins.open", mock_open(read_data=b"fake video data"))
    @patch("src.publisher.drive.requests")
    def test_successful_upload(self, mock_requests):
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "fresh-token"}
        upload_response = MagicMock()
        upload_response.status_code = 200
        upload_response.json.return_value = {"id": "drive-file-123"}

        mock_requests.post.side_effect = [token_response, upload_response]

        result = upload_to_drive("/tmp/test.mp4", "ep0001_test.mp4")

        assert result["success"] is True
        assert "drive-file-123" in result["file_url"]
        assert result["error"] is None

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials(self):
        result = upload_to_drive("/tmp/test.mp4", "ep0001_test.mp4")
        assert result["success"] is False
        assert "GOOGLE_DRIVE_FOLDER_ID" in result["error"]

    @patch.dict(os.environ, {
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "GOOGLE_REFRESH_TOKEN": "test-refresh-token",
        "GOOGLE_DRIVE_FOLDER_ID": "test-folder-id",
    })
    @patch("src.publisher.drive.requests")
    def test_token_refresh_failure(self, mock_requests):
        token_response = MagicMock()
        token_response.json.return_value = {"error": "invalid_grant"}

        mock_requests.post.return_value = token_response

        result = upload_to_drive("/tmp/test.mp4", "ep0001_test.mp4")
        assert result["success"] is False
        assert "token" in result["error"].lower() or "invalid_grant" in result["error"]

    @patch.dict(os.environ, {
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "GOOGLE_REFRESH_TOKEN": "test-refresh-token",
        "GOOGLE_DRIVE_FOLDER_ID": "test-folder-id",
    })
    @patch("builtins.open", mock_open(read_data=b"fake video data"))
    @patch("src.publisher.drive.requests")
    def test_upload_failure(self, mock_requests):
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "fresh-token"}
        upload_response = MagicMock()
        upload_response.status_code = 403
        upload_response.text = "Insufficient permissions"

        mock_requests.post.side_effect = [token_response, upload_response]

        result = upload_to_drive("/tmp/test.mp4", "ep0001_test.mp4")
        assert result["success"] is False
        assert result["error"] is not None

    @patch.dict(os.environ, {
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "GOOGLE_REFRESH_TOKEN": "test-refresh-token",
        "GOOGLE_DRIVE_FOLDER_ID": "",
    })
    def test_missing_folder_id(self):
        result = upload_to_drive("/tmp/test.mp4", "ep0001_test.mp4")
        assert result["success"] is False
        assert "GOOGLE_DRIVE_FOLDER_ID" in result["error"]

    @patch.dict(os.environ, {
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "GOOGLE_REFRESH_TOKEN": "test-refresh-token",
        "GOOGLE_DRIVE_FOLDER_ID": "test-folder-id",
    })
    @patch("builtins.open", mock_open(read_data=b"fake video data"))
    @patch("src.publisher.drive.requests")
    def test_returns_shareable_link(self, mock_requests):
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "fresh-token"}
        upload_response = MagicMock()
        upload_response.status_code = 200
        upload_response.json.return_value = {"id": "abc123"}

        mock_requests.post.side_effect = [token_response, upload_response]

        result = upload_to_drive("/tmp/test.mp4", "ep0001_test.mp4")
        assert result["file_url"] == "https://drive.google.com/file/d/abc123/view"


# ---------------------------------------------------------------------------
# format_publishing_alert
# ---------------------------------------------------------------------------

class TestFormatPublishingAlert:
    """Test Discord publishing alert message formatting."""

    def _sample_metadata(self):
        return {
            "tiktok": {
                "title": "Pens Finds a Donut",
                "description": "Pens discovers a mysterious pink donut...",
                "hashtags": ["#pixelart", "#comedy", "#Blobtoshi", "#animation", "#trending"],
            },
            "youtube": {
                "title": "Pens Finds a Donut | Blobtoshi #Shorts",
                "description": "Episode EP0001...",
                "tags": ["#Shorts", "#pixelart", "#comedy", "#Blobtoshi", "#animation",
                         "#retrogaming", "#8bit", "#cartoon", "#funny", "#indiegame"],
            },
            "instagram": {
                "caption": "Pens Finds a Donut\n\nPens discovers a mysterious pink donut...",
                "hashtags": ["#pixelart", "#reels", "#comedy", "#Blobtoshi", "#animation",
                             "#reelsinstagram", "#funnyvideos", "#indieanimation"],
            },
        }

    def test_contains_filename(self):
        result = format_publishing_alert(
            "ep0001_the-pink-donut.mp4",
            "https://drive.google.com/file/d/abc123/view",
            self._sample_metadata(),
        )
        assert "ep0001_the-pink-donut.mp4" in result

    def test_contains_drive_link(self):
        result = format_publishing_alert(
            "ep0001_test.mp4",
            "https://drive.google.com/file/d/abc123/view",
            self._sample_metadata(),
        )
        assert "https://drive.google.com/file/d/abc123/view" in result

    def test_contains_all_platform_hashtags(self):
        result = format_publishing_alert(
            "ep0001_test.mp4",
            "https://drive.google.com/file/d/abc123/view",
            self._sample_metadata(),
        )
        assert "TikTok" in result
        assert "YouTube" in result
        assert "Instagram" in result

    def test_hashtags_limited_to_5_per_platform(self):
        result = format_publishing_alert(
            "ep0001_test.mp4",
            "https://drive.google.com/file/d/abc123/view",
            self._sample_metadata(),
        )
        lines = result.split("\n")
        for line in lines:
            if line.startswith("**YouTube"):
                tag_count = line.count("#")
                assert tag_count <= 5

    def test_returns_string(self):
        result = format_publishing_alert(
            "ep0001_test.mp4",
            "https://drive.google.com/file/d/abc123/view",
            self._sample_metadata(),
        )
        assert isinstance(result, str)

    def test_no_metadata_still_works(self):
        result = format_publishing_alert(
            "ep0001_test.mp4",
            "https://drive.google.com/file/d/abc123/view",
            {},
        )
        assert "ep0001_test.mp4" in result
        assert isinstance(result, str)
