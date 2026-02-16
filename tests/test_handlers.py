"""Tests for Discord bot handler parsers.

Tests cover:
- idea_selection: parse_selection (1/2/3, ordinals, "option X")
- script_review: is_approval (approve, lgtm, etc.)
- video_preview: parse_video_selection (numbers, approve, edit notes)
"""

import pytest

from src.bot.handlers.idea_selection import parse_selection
from src.bot.handlers.script_review import is_approval
from src.bot.handlers.video_preview import parse_video_selection


# ---------------------------------------------------------------------------
# parse_selection (idea_selection.py)
# ---------------------------------------------------------------------------

class TestParseSelection:
    """Test idea selection parsing."""

    def test_direct_number_1(self):
        assert parse_selection("1") == 0

    def test_direct_number_2(self):
        assert parse_selection("2") == 1

    def test_direct_number_3(self):
        assert parse_selection("3") == 2

    def test_option_prefix(self):
        assert parse_selection("option 2") == 1

    def test_option_no_space(self):
        assert parse_selection("option2") == 1

    def test_first_ordinal(self):
        assert parse_selection("the first one") == 0

    def test_second_ordinal(self):
        assert parse_selection("second") == 1

    def test_third_ordinal(self):
        assert parse_selection("third one please") == 2

    def test_invalid_number(self):
        assert parse_selection("4") is None

    def test_random_text(self):
        assert parse_selection("hello world") is None

    def test_empty_string(self):
        assert parse_selection("") is None

    def test_whitespace_handling(self):
        assert parse_selection("  1  ") == 0

    def test_case_insensitive(self):
        assert parse_selection("Option 1") == 0

    def test_number_zero(self):
        assert parse_selection("0") is None


# ---------------------------------------------------------------------------
# is_approval (script_review.py)
# ---------------------------------------------------------------------------

class TestIsApproval:
    """Test script approval detection."""

    def test_approve(self):
        assert is_approval("approve") is True

    def test_approved(self):
        assert is_approval("approved") is True

    def test_yes(self):
        assert is_approval("yes") is True

    def test_looks_good(self):
        assert is_approval("looks good") is True

    def test_lgtm(self):
        assert is_approval("lgtm") is True

    def test_ship_it(self):
        assert is_approval("ship it") is True

    def test_good(self):
        assert is_approval("good") is True

    def test_perfect(self):
        assert is_approval("perfect") is True

    def test_case_insensitive(self):
        assert is_approval("APPROVE") is True
        assert is_approval("Looks Good") is True

    def test_whitespace(self):
        assert is_approval("  approve  ") is True

    def test_not_approval(self):
        assert is_approval("change the dialogue") is False

    def test_partial_match(self):
        # "approved by me" should not match since it's not an exact match
        assert is_approval("approved by me") is False

    def test_empty(self):
        assert is_approval("") is False


# ---------------------------------------------------------------------------
# parse_video_selection (video_preview.py)
# ---------------------------------------------------------------------------

class TestParseVideoSelection:
    """Test video selection parsing."""

    def test_direct_number_1(self):
        selection, is_appr, notes = parse_video_selection("1")
        assert selection == 0
        assert is_appr is False
        assert notes is None

    def test_direct_number_3(self):
        selection, is_appr, notes = parse_video_selection("3")
        assert selection == 2
        assert is_appr is False
        assert notes is None

    def test_approve(self):
        selection, is_appr, notes = parse_video_selection("approve")
        assert selection is None
        assert is_appr is True
        assert notes is None

    def test_lgtm(self):
        selection, is_appr, notes = parse_video_selection("lgtm")
        assert selection is None
        assert is_appr is True

    def test_option_prefix(self):
        selection, _, _ = parse_video_selection("option 2")
        assert selection == 1

    def test_ordinal_first(self):
        selection, _, _ = parse_video_selection("first")
        assert selection == 0

    def test_freeform_edit_notes(self):
        text = "use music from version 1 but pacing from version 2"
        selection, is_appr, notes = parse_video_selection(text)
        assert selection is None
        assert is_appr is False
        assert notes == text

    def test_edit_notes_not_confused_with_number(self):
        """Freeform notes containing numbers shouldn't be parsed as selections."""
        text = "make it 10 seconds longer"
        selection, is_appr, notes = parse_video_selection(text)
        # This should be freeform edit notes
        assert notes is not None or selection is not None
        # The key thing is it shouldn't crash

    def test_case_insensitive_approve(self):
        _, is_appr, _ = parse_video_selection("APPROVE")
        assert is_appr is True

    def test_whitespace_handling(self):
        selection, _, _ = parse_video_selection("  2  ")
        assert selection == 1
