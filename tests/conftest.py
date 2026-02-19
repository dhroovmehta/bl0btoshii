"""Shared test fixtures for the Mootoshi test suite."""

import json
import os
import shutil
import tempfile

import pytest


@pytest.fixture
def tmp_dir():
    """Create a temporary directory that's cleaned up after the test."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_script():
    """A minimal valid episode script for testing."""
    return {
        "episode_id": "EP099",
        "title": "Test Episode",
        "slug": "test-episode",
        "created_at": "2026-02-15T00:00:00Z",
        "version": 1,
        "scenes": [
            {
                "scene_number": 1,
                "duration_seconds": 10,
                "background": "diner_interior",
                "characters_present": ["pens", "oinks"],
                "character_positions": {
                    "pens": "stool_1",
                    "oinks": "behind_counter",
                },
                "character_animations": {
                    "pens": "idle",
                    "oinks": "serving",
                },
                "dialogue": [
                    {
                        "character": "pens",
                        "text": "...cool.",
                        "animation_trigger": "talking",
                        "duration_ms": 2000,
                    },
                ],
                "sfx_triggers": [],
                "music": "main_theme.wav",
            },
        ],
        "metadata": {
            "episode_id": "EP099",
            "title": "Test Episode",
            "total_duration_seconds": 10,
            "characters_featured": ["pens", "oinks"],
            "primary_location": "diner_interior",
            "content_pillar": "everyday_life",
            "punchline_type": "deadpan",
            "situation_type": "everyday_life",
            "location": "diner_interior",
            "created_at": "2026-02-15T00:00:00Z",
        },
    }


@pytest.fixture
def sample_script_missing_assets():
    """A script that references assets that don't exist."""
    return {
        "episode_id": "EP999",
        "title": "Missing Assets Episode",
        "scenes": [
            {
                "scene_number": 1,
                "duration_seconds": 10,
                "background": "nonexistent_bg",
                "characters_present": ["fakeanimal"],
                "character_positions": {"fakeanimal": "center"},
                "character_animations": {"fakeanimal": "idle"},
                "dialogue": [],
                "sfx_triggers": [{"sfx": "nonexistent_sound.wav", "time_ms": 0}],
                "music": "missing.wav",
            },
        ],
        "metadata": {},
    }


@pytest.fixture
def sample_ideas():
    """Sample daily ideas for testing."""
    return [
        {
            "character_a": "pens",
            "character_b": "oinks",
            "additional_characters": [],
            "location": "diner_interior",
            "situation": "everyday_life",
            "punchline_type": "deadpan",
            "concept": "Pens orders water again",
            "title": "Pens + Oinks | Diner",
            "trending_tie_in": None,
            "continuity_callbacks": [],
        },
        {
            "character_a": "chubs",
            "character_b": "meows",
            "additional_characters": [],
            "location": "town_square",
            "situation": "business_opportunity",
            "punchline_type": "backfire",
            "concept": "Chubs pitches a new startup",
            "title": "Chubs + Meows | Town Square",
            "trending_tie_in": None,
            "continuity_callbacks": [],
        },
        {
            "character_a": "quacks",
            "character_b": "reows",
            "additional_characters": [],
            "location": "beach",
            "situation": "mystery_investigation",
            "punchline_type": "reveal",
            "concept": "Quacks investigates a missing coconut",
            "title": "Quacks + Reows | Beach",
            "trending_tie_in": None,
            "continuity_callbacks": [],
        },
    ]


@pytest.fixture
def default_state():
    """The expected default pipeline state (v2)."""
    return {
        "current_episode": None,
        "stage": "idle",
        "ideas": [],
        "selected_idea_index": None,
        "current_script": None,
    }
