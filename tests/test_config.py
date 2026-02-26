"""Tests for configuration loading and validation."""

import pytest
import os
from unittest.mock import patch, MagicMock
from src.config import Config


class TestConfigLoading:
    """Test configuration loading from environment variables."""

    def test_required_urls_stripped(self):
        """Test that trailing slashes are stripped from URLs."""
        with patch.dict(
            os.environ,
            {
                "MEALIE_URL": "http://mealie:9000/",
                "MEALIE_API_TOKEN": "test-token",
            },
        ):
            config = Config()
            assert config.mealie_url == "http://mealie:9000"

    def test_defaults_applied(self):
        """Test that default values are applied."""
        with patch.dict(
            os.environ,
            {
                "MEALIE_URL": "http://mealie:9000",
                "MEALIE_API_TOKEN": "test-token",
            },
            clear=True,
        ):
            config = Config()
            assert config.backup_schedule == "0 0 * * *"
            assert config.tz == "UTC"
            assert config.retention_daily == 7
            assert config.retention_weekly == 4
            assert config.retention_monthly == 6
            assert config.retention_yearly == 1

    def test_custom_values_loaded(self):
        """Test that custom environment values are loaded."""
        with patch.dict(
            os.environ,
            {
                "MEALIE_URL": "http://mealie:9000",
                "MEALIE_API_TOKEN": "test-token",
                "BACKUP_SCHEDULE": "0 3 * * *",
                "TZ": "America/New_York",
                "RETENTION_DAILY": "14",
                "RETENTION_WEEKLY": "8",
                "RETENTION_MONTHLY": "12",
                "RETENTION_YEARLY": "2",
            },
        ):
            config = Config()
            assert config.backup_schedule == "0 3 * * *"
            assert config.tz == "America/New_York"
            assert config.retention_daily == 14
            assert config.retention_weekly == 8
            assert config.retention_monthly == 12
            assert config.retention_yearly == 2


class TestConfigValidation:
    """Test configuration validation."""

    def test_missing_mealie_url_fails(self):
        """Test that missing MEALIE_URL raises ValueError."""
        with patch.dict(
            os.environ,
            {
                "MEALIE_API_TOKEN": "test-token",
            },
            clear=True,
        ):
            config = Config()
            with pytest.raises(ValueError, match="MEALIE_URL is required"):
                config.validate()

    def test_missing_api_token_fails(self):
        """Test that missing MEALIE_API_TOKEN raises ValueError."""
        with patch.dict(
            os.environ,
            {
                "MEALIE_URL": "http://mealie:9000",
            },
            clear=True,
        ):
            config = Config()
            with pytest.raises(ValueError, match="MEALIE_API_TOKEN is required"):
                config.validate()

    def test_negative_retention_fails(self):
        """Test that negative retention values are rejected."""
        with patch.dict(
            os.environ,
            {
                "MEALIE_URL": "http://mealie:9000",
                "MEALIE_API_TOKEN": "test-token",
                "RETENTION_DAILY": "-1",
            },
        ):
            with pytest.raises(ValueError, match="must be non-negative"):
                config = Config()

    def test_invalid_retention_integer_fails(self):
        """Test that non-integer retention values are rejected."""
        with patch.dict(
            os.environ,
            {
                "MEALIE_URL": "http://mealie:9000",
                "MEALIE_API_TOKEN": "test-token",
                "RETENTION_DAILY": "not-a-number",
            },
        ):
            with pytest.raises(ValueError, match="Invalid RETENTION_DAILY"):
                config = Config()

    @patch("requests.get")
    def test_api_connectivity_success(self, mock_get):
        """Test successful API connectivity validation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"imports": []}
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {
                "MEALIE_URL": "http://mealie:9000",
                "MEALIE_API_TOKEN": "test-token",
            },
        ):
            config = Config()
            config.validate()  # Should not raise

    @patch("requests.get")
    def test_api_connectivity_unauthorized(self, mock_get):
        """Test that 401 unauthorized is caught."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {
                "MEALIE_URL": "http://mealie:9000",
                "MEALIE_API_TOKEN": "invalid-token",
            },
        ):
            config = Config()
            with pytest.raises(ValueError, match="invalid.*401"):
                config.validate()

    @patch("requests.get")
    def test_api_connectivity_forbidden(self, mock_get):
        """Test that 403 forbidden is caught."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {
                "MEALIE_URL": "http://mealie:9000",
                "MEALIE_API_TOKEN": "non-admin-token",
            },
        ):
            config = Config()
            with pytest.raises(ValueError, match="does not have admin"):
                config.validate()

    @patch("requests.get")
    def test_api_connectivity_network_error(self, mock_get):
        """Test that network errors are caught."""
        import requests
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        with patch.dict(
            os.environ,
            {
                "MEALIE_URL": "http://unreachable:9000",
                "MEALIE_API_TOKEN": "test-token",
            },
        ):
            config = Config()
            with pytest.raises(ValueError, match="Failed to connect"):
                config.validate()

    @patch("builtins.open", create=True)
    def test_healthy_marker_written(self, mock_open):
        """Test that healthcheck marker file is written."""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        with patch.dict(
            os.environ,
            {
                "MEALIE_URL": "http://mealie:9000",
                "MEALIE_API_TOKEN": "test-token",
            },
        ):
            config = Config()
            config.write_healthy_marker()
            mock_open.assert_called_once_with("/tmp/healthy", "w")
            mock_file.write.assert_called_once()

    @patch("requests.get")
    def test_all_retention_zero_fails(self, mock_get):
        """Test that all retention values set to 0 raises ValueError."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"imports": []}
        mock_get.return_value = mock_response

        with patch.dict(
            os.environ,
            {
                "MEALIE_URL": "http://mealie:9000",
                "MEALIE_API_TOKEN": "test-token",
                "RETENTION_DAILY": "0",
                "RETENTION_WEEKLY": "0",
                "RETENTION_MONTHLY": "0",
                "RETENTION_YEARLY": "0",
            },
        ):
            config = Config()
            with pytest.raises(ValueError, match="At least one retention tier"):
                config.validate()
