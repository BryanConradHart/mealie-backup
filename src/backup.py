"""Main backup orchestrator."""

import logging
import sys
from src.config import load_config
from src.mealie_api import MealieClient
from src.retention import apply_retention

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_backup() -> None:
    """
    Execute the backup operation.

    This is the main function called by the container scheduler:
    1. Load and validate configuration
    2. Create a new backup via Mealie API
    3. List all existing backups
    4. Apply retention policy
    5. Delete expired backups
    6. Update healthcheck marker
    """
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config()

        # Initialize API client
        logger.info(f"Connecting to Mealie at {config.mealie_url}...")
        client = MealieClient(config.mealie_url, config.mealie_api_token)

        # Create a new backup
        logger.info("Creating backup...")
        backup_name = client.create_backup_and_get_name()

        # Get all backups for retention analysis
        logger.info("Listing backups for retention analysis...")
        backups = client.get_backups()

        # Apply retention policy
        logger.info("Applying retention policy...")
        to_delete = apply_retention(
            backups,
            retention_daily=config.retention_daily,
            retention_weekly=config.retention_weekly,
            retention_monthly=config.retention_monthly,
            retention_yearly=config.retention_yearly,
        )

        # Delete expired backups
        if to_delete:
            logger.info(f"Deleting {len(to_delete)} expired backups...")
            for backup_to_delete in to_delete:
                try:
                    client.delete_backup(backup_to_delete)
                except ValueError as e:
                    logger.error(f"Failed to delete backup {backup_to_delete}: {e}")
        else:
            logger.info("No backups to delete")

        # Update healthcheck marker
        config.write_healthy_marker()

        logger.info("Backup operation completed successfully")

    except Exception as e:
        logger.error(f"Backup operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_backup()
