"""Integration tests for the backup orchestrator."""

import pytest
from unittest.mock import patch, MagicMock
from src.backup import run_backup


@patch("src.backup.MealieClient")
@patch("src.backup.load_config")
def test_backup_success(mock_load_config, mock_client_class):
    """Test successful backup operation."""
    # Setup mocks
    mock_config = MagicMock()
    mock_config.mealie_url = "http://mealie:9000"
    mock_config.mealie_api_token = "test-token"
    mock_config.retention_daily = 7
    mock_config.retention_weekly = 4
    mock_config.retention_monthly = 6
    mock_config.retention_yearly = 1
    mock_load_config.return_value = mock_config

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # Mock API calls
    mock_client.create_backup_and_get_name.return_value = "backup_2025_03_15"
    mock_client.get_backups.return_value = [
        {"name": "backup_2025_03_15", "date": "2025-03-15T10:00:00"},
        {"name": "backup_2025_03_14", "date": "2025-03-14T10:00:00"},
        {"name": "backup_2025_03_13", "date": "2025-03-13T10:00:00"},
    ]

    # Run backup
    run_backup()

    # Verify calls
    mock_load_config.assert_called_once()
    mock_client.create_backup_and_get_name.assert_called_once()
    mock_client.get_backups.assert_called_once()


@patch("src.backup.MealieClient")
@patch("src.backup.load_config")
def test_backup_handles_delete_errors(mock_load_config, mock_client_class):
    """Test that backup operation continues even if delete fails."""
    # Setup mocks
    mock_config = MagicMock()
    mock_config.mealie_url = "http://mealie:9000"
    mock_config.mealie_api_token = "test-token"
    mock_config.retention_daily = 2  # Keep only 2 daily
    mock_config.retention_weekly = 0
    mock_config.retention_monthly = 0
    mock_config.retention_yearly = 0
    mock_load_config.return_value = mock_config

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # Mock API calls
    mock_client.create_backup_and_get_name.return_value = "backup_2025_03_15"
    mock_client.get_backups.return_value = [
        {"name": "backup_2025_03_15", "date": "2025-03-15T10:00:00"},
        {"name": "backup_2025_03_14", "date": "2025-03-14T10:00:00"},
        {"name": "backup_2025_03_13", "date": "2025-03-13T10:00:00"},
    ]

    # Make delete fail for one backup
    mock_client.delete_backup.side_effect = [
        ValueError("Delete failed"),
        None,  # Second delete succeeds
    ]

    # Run backup - should not raise even with delete error
    run_backup()

    # Verify that delete was attempted (error is caught and logged)
    assert mock_client.delete_backup.call_count >= 1


@patch("src.backup.load_config")
def test_backup_fails_on_config_error(mock_load_config):
    """Test that backup fails gracefully on config error."""
    mock_load_config.side_effect = ValueError("Missing required config")

    with pytest.raises(SystemExit):
        run_backup()


@patch("src.backup.MealieClient")
@patch("src.backup.load_config")
def test_backup_fails_on_create_error(mock_load_config, mock_client_class):
    """Test that backup fails on creation error."""
    # Setup mocks
    mock_config = MagicMock()
    mock_load_config.return_value = mock_config

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.create_backup_and_get_name.side_effect = ValueError("API error")

    with pytest.raises(SystemExit):
        run_backup()
