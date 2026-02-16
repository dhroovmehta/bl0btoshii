"""Publish weekly analytics reports to Notion."""

from datetime import datetime
from src.notion.client import get_client, get_analytics_db_id


def publish_weekly_report(report_data):
    """Publish a weekly performance report to Notion.

    Args:
        report_data: Dict with report content.
            - start_date: str (YYYY-MM-DD)
            - end_date: str (YYYY-MM-DD)
            - top_episode: dict with episode_id, title, total_views
            - best_completion: dict with episode_id, rate
            - rising_character: dict with name, engagement_change
            - adjustments: list of str
            - platform_breakdown: dict per platform
            - character_rankings: list of dicts

    Returns:
        The Notion page URL for the published report.
    """
    client = get_client()
    db_id = get_analytics_db_id()

    start = report_data.get("start_date", "")
    end = report_data.get("end_date", "")
    page_title = f"Weekly Report | {start} - {end}"

    properties = {
        "title": {
            "title": [{"text": {"content": page_title}}]
        },
    }

    body_blocks = _build_report_body(report_data)

    response = client.pages.create(
        parent={"database_id": db_id},
        properties=properties,
        children=body_blocks,
    )

    return response.get("url", "")


def _build_report_body(report_data):
    """Build Notion blocks for the weekly report."""
    blocks = []

    start = report_data.get("start_date", "")
    end = report_data.get("end_date", "")
    blocks.append(_heading(f"Weekly Performance Report — {start} to {end}", level=1))

    # Quick summary
    blocks.append(_heading("Quick Summary", level=2))

    top_ep = report_data.get("top_episode", {})
    if top_ep:
        blocks.append(_bullet(
            f"Top episode: {top_ep.get('episode_id', '?')} ({top_ep.get('title', '?')}) — "
            f"{top_ep.get('total_views', 0):,} total views"
        ))

    best = report_data.get("best_completion", {})
    if best:
        blocks.append(_bullet(
            f"Best completion rate: {best.get('episode_id', '?')} — {best.get('rate', 0)}%"
        ))

    rising = report_data.get("rising_character", {})
    if rising:
        blocks.append(_bullet(
            f"Rising character: {rising.get('name', '?')} "
            f"(engagement up {rising.get('engagement_change', 0)}% week-over-week)"
        ))

    # Adjustments
    adjustments = report_data.get("adjustments", [])
    if adjustments:
        blocks.append(_heading("System Adjustments", level=2))
        for adj in adjustments:
            blocks.append(_bullet(adj))

    # Platform breakdown
    platforms = report_data.get("platform_breakdown", {})
    if platforms:
        blocks.append(_heading("Platform Breakdown", level=2))
        for platform, data in platforms.items():
            views = data.get("total_views", 0)
            avg_completion = data.get("avg_completion_rate", 0)
            blocks.append(_bullet(
                f"{platform.title()}: {views:,} views, {avg_completion}% avg completion"
            ))

    # Character rankings
    rankings = report_data.get("character_rankings", [])
    if rankings:
        blocks.append(_heading("Character Rankings", level=2))
        for i, char in enumerate(rankings, 1):
            blocks.append(_bullet(
                f"#{i} {char.get('name', '?')} — {char.get('appearances', 0)} appearances, "
                f"{char.get('avg_views', 0):,} avg views"
            ))

    return blocks


def _heading(text, level=1):
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _bullet(text):
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _paragraph(text):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }
