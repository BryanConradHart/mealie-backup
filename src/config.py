"""Configuration and validation for mealie-backup."""

import os
import logging
import requests
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Config:
    """Load and validate configuration from environment variables."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        # Required variables
        self.mealie_url = os.getenv("MEALIE_URL", "").rstrip("/")
        self.mealie_api_token = os.getenv("MEALIE_API_TOKEN", "")

        # Scheduling
        self.backup_schedule = os.getenv("BACKUP_SCHEDULE", "0 0 * * *")

        # Timezone
        self.tz = os.getenv("TZ", "UTC")

        # Retention (defaults: 7 daily, 4 weekly, 6 monthly, 1 yearly)
        self.retention_daily = self._parse_int("RETENTION_DAILY", 7)
        self.retention_weekly = self._parse_int("RETENTION_WEEKLY", 4)
        self.retention_monthly = self._parse_int("RETENTION_MONTHLY", 6)
        self.retention_yearly = self._parse_int("RETENTION_YEARLY", 1)

    @staticmethod
    def _parse_int(env_var: str, default: int) -> int:
        """Parse an integer from environment variable or return default."""
        try:
            value = os.getenv(env_var, str(default))
            result = int(value)
            if result < 0:
                raise ValueError(f"{env_var} must be non-negative, got {result}")
            return result
        except ValueError as e:
            raise ValueError(f"Invalid {env_var}: {e}") from e

    def validate(self) -> None:
        """
        Validate configuration.

        Raises ValueError if configuration is invalid.
        """
        # Check required variables
        if not self.mealie_url:
            raise ValueError("MEALIE_URL is required")
        if not self.mealie_api_token:
            raise ValueError("MEALIE_API_TOKEN is required")

        # Validate retention values
        for attr in [
            "retention_daily",
            "retention_weekly",
            "retention_monthly",
            "retention_yearly",
        ]:
            if getattr(self, attr) < 0:
                raise ValueError(f"{attr} must be non-negative")

        # Ensure at least one retention tier is configured
        if (
            self.retention_daily == 0
            and self.retention_weekly == 0
            and self.retention_monthly == 0
            and self.retention_yearly == 0
        ):
            raise ValueError(
                "At least one retention tier (daily, weekly, monthly, or yearly) must be greater than 0"
            )

        # Test API connectivity
        self._test_api_connectivity()

        logger.info("Configuration validated successfully")

    def _test_api_connectivity(self) -> None:
        """Test that the API is reachable and token is valid."""
        try:
            url = f"{self.mealie_url}/api/admin/backups"
            headers = {"Authorization": f"Bearer {self.mealie_api_token}"}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 401:
                raise ValueError("API token is invalid (401 Unauthorized)")
            if response.status_code == 403:
                raise ValueError("API token does not have admin access (403 Forbidden)")
            if response.status_code >= 500:
                raise ValueError(
                    f"Mealie server error: {response.status_code} {response.text}"
                )
            if response.status_code >= 400:
                raise ValueError(
                    f"API error: {response.status_code} {response.text}"
                )

            logger.info(f"Successfully connected to Mealie at {self.mealie_url}")

        except requests.RequestException as e:
            raise ValueError(f"Failed to connect to Mealie API: {e}") from e

    def write_healthy_marker(self) -> None:
        """Write a healthcheck marker file."""
        try:
            with open("/tmp/healthy", "w") as f:
                f.write("OK\n")
            logger.info("Healthcheck marker written to /tmp/healthy")
        except IOError as e:
            logger.warning(f"Failed to write healthcheck marker: {e}")


def load_config() -> Config:
    """Load and validate configuration."""
    config = Config()
    config.validate()
    config.write_healthy_marker()
    return config


if __name__ == "__main__":
    try:
        config = load_config()
        logger.info("Configuration validation passed")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        sys.exit(1)
