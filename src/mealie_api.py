"""Mealie API client for backup operations."""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class MealieClient:
    """Client for interacting with Mealie's backup API."""

    def __init__(self, base_url: str, api_token: str, timeout: int = 30):
        """
        Initialize the Mealie API client.

        Args:
            base_url: Base URL of the Mealie instance (e.g., http://mealie:9000)
            api_token: Long-lived API token with admin access
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout

    def _build_headers(self) -> dict:
        """Build headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _request(
        self, method: str, endpoint: str, **kwargs
    ) -> requests.Response:
        """
        Make an HTTP request to the Mealie API.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path (e.g., '/api/admin/backups')
            **kwargs: Additional arguments to pass to requests

        Returns:
            requests.Response object

        Raises:
            requests.RequestException: On network errors
            ValueError: On non-2xx responses
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._build_headers()
        kwargs.setdefault("timeout", self.timeout)
        kwargs["headers"] = headers

        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            raise ValueError(
                f"{method} {endpoint} failed: {e.response.status_code} {e.response.text}"
            ) from e
        except requests.RequestException as e:
            raise ValueError(f"Request to {endpoint} failed: {e}") from e

    def get_backups(self) -> list:
        """
        Get all backups.

        Returns:
            List of backup dictionaries with 'name', 'date', and other metadata

        Raises:
            ValueError: If the API request fails
        """
        response = self._request("GET", "/api/admin/backups")
        data = response.json()

        # The API returns { imports: [...], templates: [...] }
        backups = data.get("imports", [])
        logger.info(f"Retrieved {len(backups)} backups from Mealie")
        return backups

    def create_backup(self) -> str:
        """
        Create a new backup.

        Returns:
            The name/filename of the created backup

        Raises:
            ValueError: If the API request fails
        """
        response = self._request("POST", "/api/admin/backups")
        data = response.json()

        # The API returns { message: "Backup has been created", error: false }
        # We need to fetch the backup list to get the latest one
        # Or we can rely on the success and let the caller handle it
        logger.info(f"Backup created successfully")
        return data.get("message", "Backup created")

    def create_backup_and_get_name(self) -> str:
        """
        Create a new backup and return its filename.

        Returns:
            The filename of the created backup

        Raises:
            ValueError: If the API request fails
        """
        self.create_backup()

        # Get the latest backup (most recent)
        backups = self.get_backups()
        if not backups:
            raise ValueError("Backup created but no backups found in list")

        # Sort by date descending and return the latest
        sorted_backups = sorted(
            backups, key=lambda b: b.get("date", ""), reverse=True
        )
        backup_name = sorted_backups[0].get("name")
        logger.info(f"Created backup: {backup_name}")
        return backup_name

    def delete_backup(self, file_name: str) -> None:
        """
        Delete a backup.

        Args:
            file_name: Name of the backup file to delete

        Raises:
            ValueError: If the API request fails
        """
        self._request("DELETE", f"/api/admin/backups/{file_name}")
        logger.info(f"Deleted backup: {file_name}")
