"""Tests for Mealie API client."""

import pytest
from unittest.mock import MagicMock, patch
from src.mealie_api import MealieClient


@pytest.fixture
def client():
    """Create a test API client."""
    return MealieClient(base_url="http://mealie:9000", api_token="test-token")


@pytest.fixture
def mock_response():
    """Create a mock response object."""
    response = MagicMock()
    response.status_code = 200
    return response


class TestMealieClientHeaders:
    """Test header generation."""

    def test_auth_header_format(self, client):
        """Test that auth header is correctly formatted."""
        headers = client._build_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"


class TestGetBackups:
    """Test get_backups method."""

    @patch("requests.request")
    def test_get_backups_success(self, mock_request, client):
        """Test successful backup listing."""
        backups_data = {
            "imports": [
                {"name": "backup1", "date": "2025-03-10T10:00:00"},
                {"name": "backup2", "date": "2025-03-11T10:00:00"},
            ],
            "templates": [],
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = backups_data
        mock_request.return_value = mock_response

        backups = client.get_backups()
        assert len(backups) == 2
        assert backups[0]["name"] == "backup1"
        assert backups[1]["name"] == "backup2"

    @patch("requests.request")
    def test_get_backups_empty(self, mock_request, client):
        """Test empty backup list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"imports": [], "templates": []}
        mock_request.return_value = mock_response

        backups = client.get_backups()
        assert backups == []

    @patch("requests.request")
    def test_get_backups_http_error(self, mock_request, client):
        """Test error handling on HTTP error."""
        import requests
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 error", response=mock_response)
        mock_request.return_value = mock_response

        with pytest.raises(ValueError):
            client.get_backups()


class TestCreateBackup:
    """Test create_backup method."""

    @patch("requests.request")
    def test_create_backup_success(self, mock_request, client):
        """Test successful backup creation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Backup has been created", "error": False}
        mock_request.return_value = mock_response

        result = client.create_backup()
        assert "Backup has been created" in result

    @patch("requests.request")
    def test_create_backup_get_name(self, mock_request, client):
        """Test create_backup_and_get_name flow."""
        # First call: create backup (returns success)
        create_response = MagicMock()
        create_response.status_code = 200
        create_response.json.return_value = {"message": "Backup has been created", "error": False}

        # Second call: get backups (returns list with new backup)
        get_response = MagicMock()
        get_response.status_code = 200
        get_response.json.return_value = {
            "imports": [
                {"name": "backup_2025_03_15", "date": "2025-03-15T10:00:00"},
                {"name": "backup_2025_03_14", "date": "2025-03-14T10:00:00"},
            ],
            "templates": [],
        }

        mock_request.side_effect = [create_response, get_response]

        backup_name = client.create_backup_and_get_name()
        assert backup_name == "backup_2025_03_15"  # Latest

    @patch("requests.request")
    def test_create_backup_no_backups_found(self, mock_request, client):
        """Test error when created backup is not found in list."""
        # First call: create backup
        create_response = MagicMock()
        create_response.status_code = 200
        create_response.json.return_value = {"message": "Backup has been created", "error": False}

        # Second call: get backups (empty list)
        get_response = MagicMock()
        get_response.status_code = 200
        get_response.json.return_value = {"imports": [], "templates": []}

        mock_request.side_effect = [create_response, get_response]

        with pytest.raises(ValueError, match="Backup created but no backups found"):
            client.create_backup_and_get_name()


class TestDeleteBackup:
    """Test delete_backup method."""

    @patch("requests.request")
    def test_delete_backup_success(self, mock_request, client):
        """Test successful backup deletion."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Backup deleted", "error": False}
        mock_request.return_value = mock_response

        # Should not raise
        client.delete_backup("backup_name")
        mock_request.assert_called_once()

    @patch("requests.request")
    def test_delete_backup_not_found(self, mock_request, client):
        """Test error when backup not found."""
        import requests
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 error", response=mock_response)
        mock_request.return_value = mock_response

        with pytest.raises(ValueError):
            client.delete_backup("nonexistent")


class TestURLHandling:
    """Test URL handling."""

    def test_trailing_slash_removed(self):
        """Test that trailing slashes are removed from base URL."""
        client = MealieClient("http://mealie:9000/", "token")
        assert client.base_url == "http://mealie:9000"

    def test_no_trailing_slash(self):
        """Test URL without trailing slash."""
        client = MealieClient("http://mealie:9000", "token")
        assert client.base_url == "http://mealie:9000"

    @patch("requests.request")
    def test_endpoint_concatenation(self, mock_request):
        """Test that URLs are correctly concatenated."""
        client = MealieClient("http://mealie:9000", "token")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"imports": []}
        mock_request.return_value = mock_response

        client.get_backups()
        # Check that the full URL was correct
        call_args = mock_request.call_args
        assert call_args[0][1] == "http://mealie:9000/api/admin/backups"
