"""Tests for Notion script publisher module.

Tests cover:
- Block builders: _heading, _paragraph, _bullet, _divider
- _build_script_body: complete body construction
"""

import pytest

from src.notion.script_publisher import (
    _heading,
    _paragraph,
    _bullet,
    _divider,
    _build_script_body,
)


# ---------------------------------------------------------------------------
# Block builders
# ---------------------------------------------------------------------------

class TestHeading:
    """Test Notion heading block builder."""

    def test_heading_1(self):
        block = _heading("My Title", level=1)
        assert block["type"] == "heading_1"
        assert block["heading_1"]["rich_text"][0]["text"]["content"] == "My Title"
        assert block["object"] == "block"

    def test_heading_2(self):
        block = _heading("Subtitle", level=2)
        assert block["type"] == "heading_2"
        assert block["heading_2"]["rich_text"][0]["text"]["content"] == "Subtitle"

    def test_heading_3(self):
        block = _heading("Section", level=3)
        assert block["type"] == "heading_3"


class TestParagraph:
    """Test Notion paragraph block builder."""

    def test_paragraph(self):
        block = _paragraph("Hello world")
        assert block["type"] == "paragraph"
        assert block["paragraph"]["rich_text"][0]["text"]["content"] == "Hello world"
        assert block["object"] == "block"

    def test_empty_text(self):
        block = _paragraph("")
        assert block["paragraph"]["rich_text"][0]["text"]["content"] == ""


class TestBullet:
    """Test Notion bullet list item block builder."""

    def test_bullet(self):
        block = _bullet("An item")
        assert block["type"] == "bulleted_list_item"
        assert block["bulleted_list_item"]["rich_text"][0]["text"]["content"] == "An item"
        assert block["object"] == "block"


class TestDivider:
    """Test Notion divider block builder."""

    def test_divider(self):
        block = _divider()
        assert block["type"] == "divider"
        assert block["object"] == "block"
        assert "divider" in block


# ---------------------------------------------------------------------------
# _build_script_body
# ---------------------------------------------------------------------------

class TestBuildScriptBody:
    """Test full script body construction."""

    @pytest.fixture
    def sample_script(self):
        return {
            "episode_id": "EP001",
            "title": "Test Episode",
            "generation_params": {
                "character_a": "pens",
                "character_b": "chubs",
                "location": "diner_interior",
                "situation": "everyday_life",
            },
            "scenes": [
                {
                    "scene_number": 1,
                    "background": "diner_interior",
                    "duration_seconds": 10,
                    "action_description": "Pens walks in",
                    "dialogue": [
                        {"character": "pens", "text": "Hey."},
                        {"character": "chubs", "text": "Hello!"},
                    ],
                    "sfx_triggers": [{"sfx": "door_burst"}],
                },
            ],
            "end_card": {"text": "Subscribe!"},
            "continuity_log": {
                "events": ["Pens visited the diner"],
                "new_running_gags": ["Pens always sits in the same spot"],
            },
        }

    def test_returns_list(self, sample_script):
        blocks = _build_script_body(sample_script)
        assert isinstance(blocks, list)

    def test_starts_with_heading(self, sample_script):
        blocks = _build_script_body(sample_script)
        assert blocks[0]["type"] == "heading_1"
        assert "EP001" in blocks[0]["heading_1"]["rich_text"][0]["text"]["content"]

    def test_contains_generation_params(self, sample_script):
        blocks = _build_script_body(sample_script)
        all_text = " ".join(
            b.get(b["type"], {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            for b in blocks if b["type"] != "divider"
        )
        assert "pens" in all_text.lower()
        assert "Diner Interior" in all_text

    def test_contains_scene_headings(self, sample_script):
        blocks = _build_script_body(sample_script)
        scene_headings = [
            b for b in blocks
            if b["type"] == "heading_2" and "Scene" in b["heading_2"]["rich_text"][0]["text"]["content"]
        ]
        assert len(scene_headings) == 1

    def test_contains_dialogue(self, sample_script):
        blocks = _build_script_body(sample_script)
        dialogue_blocks = [
            b for b in blocks
            if b["type"] == "paragraph"
            and "PENS" in b["paragraph"]["rich_text"][0]["text"]["content"]
        ]
        assert len(dialogue_blocks) >= 1

    def test_contains_sfx(self, sample_script):
        blocks = _build_script_body(sample_script)
        sfx_blocks = [
            b for b in blocks
            if b["type"] == "paragraph"
            and "SFX" in b["paragraph"]["rich_text"][0]["text"]["content"]
        ]
        assert len(sfx_blocks) >= 1

    def test_contains_end_card(self, sample_script):
        blocks = _build_script_body(sample_script)
        end_card_headings = [
            b for b in blocks
            if b["type"] == "heading_2"
            and "End Card" in b["heading_2"]["rich_text"][0]["text"]["content"]
        ]
        assert len(end_card_headings) == 1

    def test_contains_continuity_notes(self, sample_script):
        blocks = _build_script_body(sample_script)
        cont_headings = [
            b for b in blocks
            if b["type"] == "heading_2"
            and "Continuity" in b["heading_2"]["rich_text"][0]["text"]["content"]
        ]
        assert len(cont_headings) == 1

    def test_contains_dividers(self, sample_script):
        blocks = _build_script_body(sample_script)
        dividers = [b for b in blocks if b["type"] == "divider"]
        assert len(dividers) >= 2

    def test_empty_scenes(self):
        script = {
            "episode_id": "EP001",
            "title": "Empty",
            "generation_params": {},
            "scenes": [],
            "end_card": {},
            "continuity_log": {},
        }
        blocks = _build_script_body(script)
        assert isinstance(blocks, list)
        assert len(blocks) >= 1  # At least the heading

    def test_contains_running_gags(self, sample_script):
        blocks = _build_script_body(sample_script)
        bullet_blocks = [
            b for b in blocks
            if b["type"] == "bulleted_list_item"
        ]
        # Should have events + gags as bullet items
        assert len(bullet_blocks) >= 2
