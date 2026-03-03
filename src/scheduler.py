"""Cron-based scheduler for backup execution (container-safe, no system cron needed)."""

import logging
import time
from datetime import datetime
from croniter import croniter

logger = logging.getLogger(__name__)


def run_scheduler(cron_schedule: str, backup_func) -> None:
    """
    Run the scheduler loop indefinitely, executing backup_func on schedule.

    Args:
        cron_schedule: Cron expression (e.g., "0 0 * * *" for daily at midnight)
        backup_func: Callable to execute at scheduled times
    """
    logger.info(f"Starting scheduler with cron: {cron_schedule}")

    # Validate cron expression
    try:
        cron = croniter(cron_schedule)
    except Exception as e:
        logger.error(f"Invalid cron schedule '{cron_schedule}': {e}")
        raise

    while True:
        try:
            # Get next scheduled execution time
            next_run = cron.get_next(datetime)
            now = datetime.now()
            sleep_seconds = (next_run - now).total_seconds()

            logger.info(f"Next backup scheduled for {next_run} (in {sleep_seconds:.0f} seconds)")

            # Sleep until the scheduled time
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

            # Execute backup
            logger.info("Executing scheduled backup...")
            backup_func()

            # Advance croniter to next occurrence for the next iteration
            cron = croniter(cron_schedule)

        except KeyboardInterrupt:
            logger.info("Scheduler interrupted")
            break
        except Exception as e:
            logger.error(f"Scheduler error: {e}. Retrying in 60 seconds...")
            time.sleep(60)
