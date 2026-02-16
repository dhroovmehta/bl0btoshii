"""Notion API client wrapper."""

import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_SCRIPTS_DB_ID = os.getenv("NOTION_SCRIPTS_DB_ID")
NOTION_ANALYTICS_DB_ID = os.getenv("NOTION_ANALYTICS_DB_ID")


def get_client():
    """Get an authenticated Notion client."""
    if not NOTION_API_KEY:
        raise ValueError("NOTION_API_KEY not set in .env")
    return Client(auth=NOTION_API_KEY)


def get_scripts_db_id():
    """Get the Episode Scripts database ID."""
    if not NOTION_SCRIPTS_DB_ID:
        raise ValueError("NOTION_SCRIPTS_DB_ID not set in .env")
    return NOTION_SCRIPTS_DB_ID


def get_analytics_db_id():
    """Get the Weekly Reports database ID."""
    if not NOTION_ANALYTICS_DB_ID:
        raise ValueError("NOTION_ANALYTICS_DB_ID not set in .env")
    return NOTION_ANALYTICS_DB_ID


def test_connection():
    """Test that the Notion API connection works and databases are accessible."""
    client = get_client()

    # Test scripts database
    scripts_db = client.databases.retrieve(database_id=get_scripts_db_id())
    scripts_title = scripts_db.get("title", [{}])
    scripts_name = scripts_title[0].get("plain_text", "Unknown") if scripts_title else "Unknown"
    print(f"  Scripts DB: {scripts_name} OK")

    # Test analytics database
    analytics_db = client.databases.retrieve(database_id=get_analytics_db_id())
    analytics_title = analytics_db.get("title", [{}])
    analytics_name = analytics_title[0].get("plain_text", "Unknown") if analytics_title else "Unknown"
    print(f"  Analytics DB: {analytics_name} OK")

    return True
