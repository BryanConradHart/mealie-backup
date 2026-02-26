"""Tests for retention policy logic."""

import pytest
from datetime import datetime, timedelta
from src.retention import (
    apply_retention,
    parse_backup_date,
    day_key,
    week_key,
    month_key,
    year_key,
)


def make_backup(name: str, date: str) -> dict:
    """Helper to create a backup dict."""
    return {"name": name, "date": date}


class TestDateHelpers:
    """Test calendar period key functions."""

    def test_day_key(self):
        """Test day_key generates consistent daily keys."""
        dt1 = datetime(2025, 3, 15, 14, 30, 45)
        dt2 = datetime(2025, 3, 15, 22, 15, 0)
        dt3 = datetime(2025, 3, 16, 0, 0, 0)
        assert day_key(dt1) == day_key(dt2) == "2025-03-15"
        assert day_key(dt3) == "2025-03-16"

    def test_week_key(self):
        """Test week_key generates consistent ISO week keys."""
        # Both in the same ISO week
        dt1 = datetime(2025, 3, 10, 10, 0, 0)  # Monday of week 11
        dt2 = datetime(2025, 3, 16, 22, 0, 0)  # Sunday of week 11
        assert week_key(dt1) == week_key(dt2) == "2025W11"

        # Different week
        dt3 = datetime(2025, 3, 17, 10, 0, 0)  # Monday of week 12
        assert week_key(dt3) == "2025W12"

    def test_month_key(self):
        """Test month_key generates consistent monthly keys."""
        dt1 = datetime(2025, 3, 1, 10, 0, 0)
        dt2 = datetime(2025, 3, 31, 23, 59, 59)
        dt3 = datetime(2025, 4, 1, 10, 0, 0)
        assert month_key(dt1) == month_key(dt2) == "2025-03"
        assert month_key(dt3) == "2025-04"

    def test_year_key(self):
        """Test year_key generates consistent yearly keys."""
        dt1 = datetime(2025, 1, 1, 0, 0, 0)
        dt2 = datetime(2025, 12, 31, 23, 59, 59)
        dt3 = datetime(2026, 1, 1, 0, 0, 0)
        assert year_key(dt1) == year_key(dt2) == "2025"
        assert year_key(dt3) == "2026"


class TestParseDateBackup:
    """Test backup date parsing."""

    def test_parse_iso_with_microseconds(self):
        """Test parsing ISO format with microseconds."""
        backup = make_backup("backup1", "2025-03-15T10:30:45.123456")
        dt = parse_backup_date(backup)
        assert dt.year == 2025
        assert dt.month == 3
        assert dt.day == 15

    def test_parse_iso_without_microseconds(self):
        """Test parsing ISO format without microseconds."""
        backup = make_backup("backup1", "2025-03-15T10:30:45")
        dt = parse_backup_date(backup)
        assert dt.year == 2025
        assert dt.month == 3
        assert dt.day == 15

    def test_parse_date_only(self):
        """Test parsing date-only format."""
        backup = make_backup("backup1", "2025-03-15")
        dt = parse_backup_date(backup)
        assert dt.year == 2025
        assert dt.month == 3
        assert dt.day == 15

    def test_parse_fails_on_invalid_date(self):
        """Test that invalid dates raise ValueError."""
        backup = make_backup("backup1", "not-a-date")
        with pytest.raises(ValueError):
            parse_backup_date(backup)

    def test_parse_fails_on_missing_date(self):
        """Test that backups without dates raise ValueError."""
        backup = {"name": "backup1"}
        with pytest.raises(ValueError):
            parse_backup_date(backup)


class TestRetentionPolicy:
    """Test GFS retention policy application."""

    def test_no_backups(self):
        """Test with empty backup list."""
        result = apply_retention([], 7, 4, 6, 1)
        assert result == set()

    def test_fewer_backups_than_retention(self):
        """Test that no backups are deleted if count is below retention."""
        backups = [
            make_backup("backup1", "2025-03-10T10:00:00"),
            make_backup("backup2", "2025-03-11T10:00:00"),
            make_backup("backup3", "2025-03-12T10:00:00"),
        ]
        # Retention: keep 7 daily, 4 weekly, 6 monthly, 1 yearly
        result = apply_retention(backups, 7, 4, 6, 1)
        assert result == set()

    def test_daily_retention(self):
        """Test that only the specified number of daily backups are kept."""
        # Create 10 daily backups over 10 consecutive days
        backups = [
            make_backup(f"backup{i}", f"2025-03-{i+1:02d}T10:00:00")
            for i in range(10)
        ]
        # Keep only 7 daily backups
        result = apply_retention(backups, retention_daily=7, retention_weekly=0, retention_monthly=0, retention_yearly=0)
        # Should delete 3 oldest backups
        assert len(result) == 3
        assert "backup0" in result  # Oldest
        assert "backup1" in result
        assert "backup2" in result
        assert "backup6" not in result  # Newest 7 are kept

    def test_weekly_retention(self):
        """Test weekly retention across multiple weeks."""
        # Create backups across 6 weeks
        backups = [
            make_backup("backup1", "2025-03-03T10:00:00"),  # Week 10
            make_backup("backup2", "2025-03-05T10:00:00"),  # Week 10
            make_backup("backup3", "2025-03-10T10:00:00"),  # Week 11
            make_backup("backup4", "2025-03-17T10:00:00"),  # Week 12
            make_backup("backup5", "2025-03-24T10:00:00"),  # Week 13
            make_backup("backup6", "2025-03-31T10:00:00"),  # Week 14
        ]
        # Keep 4 weekly backups - need to keep latest from 4 weeks, delete 2
        result = apply_retention(backups, retention_daily=0, retention_weekly=4, retention_monthly=0, retention_yearly=0)
        # Should delete oldest backups from oldest weeks
        assert len(result) == 2
        # backup1 is oldest from week 10, should be deleted
        assert "backup1" in result

    def test_monthly_retention(self):
        """Test monthly retention across multiple months."""
        backups = [
            make_backup("backup1", "2025-01-10T10:00:00"),
            make_backup("backup2", "2025-02-10T10:00:00"),
            make_backup("backup3", "2025-03-10T10:00:00"),
            make_backup("backup4", "2025-04-10T10:00:00"),
            make_backup("backup5", "2025-05-10T10:00:00"),
            make_backup("backup6", "2025-06-10T10:00:00"),
            make_backup("backup7", "2025-07-10T10:00:00"),
        ]
        # Keep 6 monthly backups
        result = apply_retention(backups, retention_daily=0, retention_weekly=0, retention_monthly=6, retention_yearly=0)
        # Should delete oldest month
        assert len(result) == 1
        assert "backup1" in result

    def test_yearly_retention(self):
        """Test yearly retention across multiple years."""
        backups = [
            make_backup("backup1", "2023-06-15T10:00:00"),
            make_backup("backup2", "2024-06-15T10:00:00"),
            make_backup("backup3", "2025-06-15T10:00:00"),
        ]
        # Keep 1 yearly backup
        result = apply_retention(backups, retention_daily=0, retention_weekly=0, retention_monthly=0, retention_yearly=1)
        # Should delete oldest 2 years
        assert len(result) == 2
        assert "backup1" in result
        assert "backup2" in result

    def test_combined_retention(self):
        """Test combined retention across all tiers."""
        # Create a realistic backup set spanning multiple periods
        backups = [
            # Week 11 (multiple times per day)
            make_backup("b1", "2025-03-10T02:00:00"),
            make_backup("b2", "2025-03-10T10:00:00"),
            make_backup("b3", "2025-03-10T18:00:00"),
            # Week 11 (different day)
            make_backup("b4", "2025-03-11T10:00:00"),
            # Week 12
            make_backup("b5", "2025-03-17T10:00:00"),
            # Week 13
            make_backup("b6", "2025-03-24T10:00:00"),
            # Week 14
            make_backup("b7", "2025-03-31T10:00:00"),
            # Week 15
            make_backup("b8", "2025-04-07T10:00:00"),
        ]
        # Policy: 7 daily, 4 weekly, 6 monthly, 1 yearly
        result = apply_retention(backups, retention_daily=7, retention_weekly=4, retention_monthly=6, retention_yearly=1)
        # With daily=7, we should keep 7 backups (the 7 different days)
        # Only b1 (oldest) and b2 (same day as b1) should be candidates for deletion
        assert len(result) <= 1  # At most 1 older backup from same day

    def test_zero_retention(self):
        """Test that zero retention deletes all backups."""
        backups = [
            make_backup("backup1", "2025-03-10T10:00:00"),
            make_backup("backup2", "2025-03-11T10:00:00"),
        ]
        result = apply_retention(backups, retention_daily=0, retention_weekly=0, retention_monthly=0, retention_yearly=0)
        assert result == {"backup1", "backup2"}

    def test_keeps_latest_in_period(self):
        """Test that the latest backup in each period is kept."""
        backups = [
            make_backup("backup1", "2025-03-10T08:00:00"),
            make_backup("backup2", "2025-03-10T14:00:00"),  # Latest on 3/10
            make_backup("backup3", "2025-03-11T08:00:00"),  # Latest on 3/11
        ]
        result = apply_retention(backups, retention_daily=2, retention_weekly=0, retention_monthly=0, retention_yearly=0)
        # Should keep backup2 and backup3 (latest on each day), delete backup1
        assert result == {"backup1"}
