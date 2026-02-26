"""Retention policy enforcement for backups (GFS: daily/weekly/monthly/yearly)."""

import logging
from datetime import datetime
from typing import List, Dict, Set

logger = logging.getLogger(__name__)


def parse_backup_date(backup: Dict) -> datetime:
    """
    Parse backup date from backup dictionary.

    Args:
        backup: Backup dictionary with 'date' field

    Returns:
        datetime object

    Raises:
        ValueError: If date cannot be parsed
    """
    date_str = backup.get("date")
    if not date_str:
        raise ValueError(f"Backup {backup.get('name')} has no date field")

    # Try common ISO formats
    for fmt in [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            return datetime.strptime(date_str.split(".")[0], fmt)
        except ValueError:
            continue

    raise ValueError(f"Could not parse date: {date_str}")


def day_key(dt: datetime) -> str:
    """Return a unique key for a calendar day."""
    return dt.strftime("%Y-%m-%d")


def week_key(dt: datetime) -> str:
    """Return a unique key for an ISO calendar week."""
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}W{iso_week:02d}"


def month_key(dt: datetime) -> str:
    """Return a unique key for a calendar month."""
    return dt.strftime("%Y-%m")


def year_key(dt: datetime) -> str:
    """Return a unique key for a calendar year."""
    return dt.strftime("%Y")


def apply_retention(
    backups: List[Dict],
    retention_daily: int,
    retention_weekly: int,
    retention_monthly: int,
    retention_yearly: int,
) -> Set[str]:
    """
    Apply GFS (Grandfather-Father-Son) retention policy.

    Keeps the latest backup from each calendar period according to retention counts.

    Args:
        backups: List of backup dictionaries with 'name' and 'date' fields
        retention_daily: Number of daily backups to keep
        retention_weekly: Number of weekly backups to keep
        retention_monthly: Number of monthly backups to keep
        retention_yearly: Number of yearly backups to keep

    Returns:
        Set of backup names to delete
    """
    if not backups:
        return set()

    # Parse and sort: newest first
    try:
        sorted_backups = sorted(
            backups, key=lambda b: parse_backup_date(b), reverse=True
        )
    except ValueError as e:
        logger.error(f"Failed to parse backup dates: {e}")
        return set()

    # Track which backups to keep
    kept_names: Set[str] = set()

    # Track which periods we've seen for each tier
    daily_periods: Set[str] = set()
    weekly_periods: Set[str] = set()
    monthly_periods: Set[str] = set()
    yearly_periods: Set[str] = set()

    # Walk through backups newest-first, assigning to tiers
    for backup in sorted_backups:
        name = backup.get("name")
        if not name:
            continue

        try:
            dt = parse_backup_date(backup)
        except ValueError:
            logger.warning(f"Skipping backup with unparseable date: {name}")
            continue

        # Check each tier in order (most frequent to least)
        if (
            retention_daily > 0
            and len(daily_periods) < retention_daily
        ):
            day = day_key(dt)
            if day not in daily_periods:
                daily_periods.add(day)
                kept_names.add(name)
                logger.debug(f"Keeping {name} for daily tier ({day})")
                continue

        if (
            retention_weekly > 0
            and len(weekly_periods) < retention_weekly
        ):
            week = week_key(dt)
            if week not in weekly_periods:
                weekly_periods.add(week)
                kept_names.add(name)
                logger.debug(f"Keeping {name} for weekly tier ({week})")
                continue

        if (
            retention_monthly > 0
            and len(monthly_periods) < retention_monthly
        ):
            month = month_key(dt)
            if month not in monthly_periods:
                monthly_periods.add(month)
                kept_names.add(name)
                logger.debug(f"Keeping {name} for monthly tier ({month})")
                continue

        if (
            retention_yearly > 0
            and len(yearly_periods) < retention_yearly
        ):
            year = year_key(dt)
            if year not in yearly_periods:
                yearly_periods.add(year)
                kept_names.add(name)
                logger.debug(f"Keeping {name} for yearly tier ({year})")
                continue

    # Backups to delete are those not kept
    to_delete = {b.get("name") for b in backups if b.get("name") not in kept_names}

    logger.info(
        f"Retention policy: keeping {len(kept_names)} of {len(backups)}, "
        f"deleting {len(to_delete)}"
    )
    logger.debug(
        f"Retention breakdown: daily={len(daily_periods)}, "
        f"weekly={len(weekly_periods)}, "
        f"monthly={len(monthly_periods)}, "
        f"yearly={len(yearly_periods)}"
    )

    return to_delete
