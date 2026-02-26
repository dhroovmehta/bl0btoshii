"""Scheduled trigger configuration — defines exact times for daily and weekly tasks."""

import datetime
import os
import zoneinfo

from dotenv import load_dotenv

load_dotenv()

# Timezone from .env (defaults to America/New_York)
PIPELINE_TZ = zoneinfo.ZoneInfo(os.getenv("PIPELINE_TIMEZONE", "America/New_York"))

# Daily idea generation: 9:15 AM ET
DAILY_TRIGGER_TIME = datetime.time(hour=9, minute=15, tzinfo=PIPELINE_TZ)

# Weekly analytics report: Monday at 9:00 AM ET
WEEKLY_REPORT_DAY = 0  # Monday (Python weekday: Mon=0, Sun=6)
WEEKLY_REPORT_TIME = datetime.time(hour=9, minute=0, tzinfo=PIPELINE_TZ)


def is_pipeline_paused():
    """Check if the pipeline is paused via PIPELINE_PAUSED env var.

    Returns:
        True if PIPELINE_PAUSED is set to a truthy value (true/1/yes).
    """
    return os.getenv("PIPELINE_PAUSED", "").strip().lower() in ("true", "1", "yes")


def is_weekly_report_day(now=None):
    """Check if the current day is the weekly report day (Monday).

    Args:
        now: Optional datetime to check. Defaults to current time in PIPELINE_TZ.

    Returns:
        True if it's the weekly report day.
    """
    if now is None:
        now = datetime.datetime.now(PIPELINE_TZ)
    return now.weekday() == WEEKLY_REPORT_DAY
