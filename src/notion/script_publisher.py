"""Publish episode scripts to Notion as formatted pages."""

from datetime import datetime
from src.notion.client import get_client, get_scripts_db_id


def publish_script(script_data):
    """Publish an episode script to Notion.

    Args:
        script_data: Episode script dict matching the PRD schema (Section 7.5).

    Returns:
        The Notion page URL for the published script.
    """
    client = get_client()
    db_id = get_scripts_db_id()

    episode_id = script_data.get("episode_id", "EP001")
    title = script_data.get("title", "Untitled")
    episode_num = int(episode_id.replace("EP", ""))
    version = script_data.get("version", 1)
    date_str = script_data.get("created_at", datetime.utcnow().isoformat())
    date_display = datetime.fromisoformat(date_str.replace("Z", "+00:00")).strftime("%b %d, %Y")

    # Page title: EP # XXX | Title | Date
    page_title = f"EP # {episode_num:03d} | {title} | {date_display}"
    if version > 1:
        page_title += f" (v{version})"

    # Characters featured
    characters = script_data.get("metadata", {}).get("characters_featured", [])
    char_names = [c.capitalize() for c in characters]

    # Location
    location = script_data.get("metadata", {}).get("primary_location", "")
    location_display = location.replace("_", " ").title() if location else ""

    # Situation and punchline
    situation = script_data.get("generation_params", {}).get("situation", "")
    situation_display = situation.replace("_", " ").title() if situation else ""
    punchline = script_data.get("metadata", {}).get("punchline_type", "")
    punchline_display = punchline.replace("_", " ").title() if punchline else ""

    # Build page properties
    properties = {
        "title": {
            "title": [{"text": {"content": page_title}}]
        },
    }

    # Build page body — formatted script content
    body_blocks = _build_script_body(script_data)

    # Create the page
    response = client.pages.create(
        parent={"database_id": db_id},
        properties=properties,
        children=body_blocks,
    )

    page_url = response.get("url", "")
    return page_url


def _build_script_body(script_data):
    """Convert script data into Notion blocks for readable formatting."""
    blocks = []

    # Header
    title = script_data.get("title", "Untitled")
    episode_id = script_data.get("episode_id", "EP001")
    blocks.append(_heading(f"{episode_id}: {title}", level=1))

    # Generation params summary
    params = script_data.get("generation_params", {})
    chars = params.get("character_a", "?") + " + " + params.get("character_b", "?")
    location = params.get("location", "?").replace("_", " ").title()
    situation = params.get("situation", "?").replace("_", " ").title()
    blocks.append(_paragraph(f"Characters: {chars} | Location: {location} | Situation: {situation}"))
    blocks.append(_divider())

    # Scenes
    scenes = script_data.get("scenes", [])
    for scene in scenes:
        scene_num = scene.get("scene_number", 0)
        bg = scene.get("background", "").replace("_", " ").title()
        duration = scene.get("duration_seconds", 0)
        blocks.append(_heading(f"Scene {scene_num} — {bg} ({duration}s)", level=2))

        # Action description
        action = scene.get("action_description", "")
        if action:
            blocks.append(_paragraph(f"_{action}_"))

        # Dialogue
        dialogue = scene.get("dialogue", [])
        for line in dialogue:
            char = line.get("character", "?").upper()
            text = line.get("text", "")
            blocks.append(_paragraph(f"**{char}:** {text}"))

        # SFX
        sfx = scene.get("sfx_triggers", [])
        if sfx:
            sfx_text = ", ".join([s.get("sfx", "") for s in sfx])
            blocks.append(_paragraph(f"SFX: {sfx_text}"))

        blocks.append(_divider())

    # End card
    end_card = script_data.get("end_card", {})
    if end_card:
        blocks.append(_heading("End Card", level=2))
        blocks.append(_paragraph(end_card.get("text", "")))

    # Continuity log
    continuity = script_data.get("continuity_log", {})
    if continuity:
        blocks.append(_divider())
        blocks.append(_heading("Continuity Notes", level=2))
        events = continuity.get("events", [])
        for event in events:
            blocks.append(_bullet(event))
        gags = continuity.get("new_running_gags", [])
        if gags:
            blocks.append(_paragraph("**New Running Gags:**"))
            for gag in gags:
                blocks.append(_bullet(gag))

    return blocks


def _heading(text, level=1):
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _paragraph(text):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _bullet(text):
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _divider():
    return {"object": "block", "type": "divider", "divider": {}}
