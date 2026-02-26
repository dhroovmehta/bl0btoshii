"""Tests for the scheduled trigger timing configuration."""

import datetime
import zoneinfo

import pytest

from src.bot.scheduler import (
    DAILY_TRIGGER_TIME,
    WEEKLY_REPORT_DAY,
    WEEKLY_REPORT_TIME,
    PIPELINE_TZ,
    is_weekly_report_day,
    is_pipeline_paused,
)


# ---------------------------------------------------------------------------
# Timezone configuration
# ---------------------------------------------------------------------------


class TestTimezoneConfig:
    """Tests for timezone configuration."""

    def test_pipeline_tz_is_eastern(self):
        assert str(PIPELINE_TZ) == "America/New_York"

    def test_pipeline_tz_is_zoneinfo(self):
        assert isinstance(PIPELINE_TZ, zoneinfo.ZoneInfo)


# ---------------------------------------------------------------------------
# Daily trigger time
# ---------------------------------------------------------------------------


class TestDailyTriggerTime:
    """Tests for the daily pipeline trigger time."""

    def test_daily_time_is_datetime_time(self):
        assert isinstance(DAILY_TRIGGER_TIME, datetime.time)

    def test_daily_time_hour(self):
        assert DAILY_TRIGGER_TIME.hour == 9

    def test_daily_time_minute(self):
        assert DAILY_TRIGGER_TIME.minute == 15

    def test_daily_time_has_timezone(self):
        assert DAILY_TRIGGER_TIME.tzinfo is not None

    def test_daily_time_timezone_is_eastern(self):
        assert str(DAILY_TRIGGER_TIME.tzinfo) == "America/New_York"


# ---------------------------------------------------------------------------
# Weekly report configuration
# ---------------------------------------------------------------------------


class TestWeeklyReportConfig:
    """Tests for the weekly analytics report schedule."""

    def test_weekly_time_is_datetime_time(self):
        assert isinstance(WEEKLY_REPORT_TIME, datetime.time)

    def test_weekly_time_hour(self):
        assert WEEKLY_REPORT_TIME.hour == 9

    def test_weekly_time_minute(self):
        assert WEEKLY_REPORT_TIME.minute == 0

    def test_weekly_time_has_timezone(self):
        assert WEEKLY_REPORT_TIME.tzinfo is not None

    def test_weekly_report_day_is_monday(self):
        assert WEEKLY_REPORT_DAY == 0  # Monday = 0 in Python


# ---------------------------------------------------------------------------
# is_weekly_report_day
# ---------------------------------------------------------------------------


class TestIsWeeklyReportDay:
    """Tests for the is_weekly_report_day() helper."""

    def test_monday_returns_true(self):
        # 2026-02-16 is a Monday
        monday = datetime.datetime(2026, 2, 16, 9, 0, tzinfo=zoneinfo.ZoneInfo("America/New_York"))
        assert is_weekly_report_day(monday) is True

    def test_tuesday_returns_false(self):
        tuesday = datetime.datetime(2026, 2, 17, 9, 0, tzinfo=zoneinfo.ZoneInfo("America/New_York"))
        assert is_weekly_report_day(tuesday) is False

    def test_sunday_returns_false(self):
        sunday = datetime.datetime(2026, 2, 22, 9, 0, tzinfo=zoneinfo.ZoneInfo("America/New_York"))
        assert is_weekly_report_day(sunday) is False

    def test_wednesday_returns_false(self):
        wednesday = datetime.datetime(2026, 2, 18, 9, 0, tzinfo=zoneinfo.ZoneInfo("America/New_York"))
        assert is_weekly_report_day(wednesday) is False

    def test_next_monday_returns_true(self):
        next_monday = datetime.datetime(2026, 2, 23, 9, 0, tzinfo=zoneinfo.ZoneInfo("America/New_York"))
        assert is_weekly_report_day(next_monday) is True

    def test_uses_eastern_time_for_check(self):
        # Late Sunday night UTC is already Monday ET during parts of the year
        # This tests that the function uses the provided datetime's weekday
        monday_et = datetime.datetime(2026, 2, 16, 0, 30, tzinfo=zoneinfo.ZoneInfo("America/New_York"))
        assert is_weekly_report_day(monday_et) is True


# ---------------------------------------------------------------------------
# Pipeline pause flag
# ---------------------------------------------------------------------------


class TestIsPipelinePaused:
    """Tests for the PIPELINE_PAUSED env var check."""

    def test_paused_when_env_true(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_PAUSED", "true")
        assert is_pipeline_paused() is True

    def test_paused_when_env_1(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_PAUSED", "1")
        assert is_pipeline_paused() is True

    def test_paused_when_env_yes(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_PAUSED", "yes")
        assert is_pipeline_paused() is True

    def test_paused_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_PAUSED", "TRUE")
        assert is_pipeline_paused() is True

    def test_not_paused_when_env_false(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_PAUSED", "false")
        assert is_pipeline_paused() is False

    def test_not_paused_when_env_0(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_PAUSED", "0")
        assert is_pipeline_paused() is False

    def test_not_paused_when_env_missing(self, monkeypatch):
        monkeypatch.delenv("PIPELINE_PAUSED", raising=False)
        assert is_pipeline_paused() is False

    def test_not_paused_when_env_empty(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_PAUSED", "")
        assert is_pipeline_paused() is False
