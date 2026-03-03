"""Simplified integration tests for Docker container validation."""

import pytest
import subprocess
import logging
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
logger = logging.getLogger(__name__)

TEST_IMAGE_TAG = "mealie-backup:test"


@pytest.fixture(scope="session", autouse=True)
def cleanup_docker_resources_after_tests():
    """Session-level cleanup: runs after all tests to remove any orphaned resources.
    
    This cleanup is guaranteed to run even if tests timeout because:
    - pytest-timeout uses thread-based interruption (not process kill)
    - pytest's fixture cleanup protocol always runs fixture teardown
    - The try/finally blocks in nested fixtures also guarantee cleanup
    """
    yield
    logger.info("=" * 60)
    logger.info("SESSION CLEANUP: Removing all test Docker resources")
    logger.info("=" * 60)
    _cleanup_orphaned_containers(TEST_IMAGE_TAG)
    _cleanup_image(TEST_IMAGE_TAG)
    logger.info("Session cleanup complete")


def _run_docker_command(cmd, timeout=60):
    """Helper to run Docker commands with proper error handling."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result
    except subprocess.TimeoutExpired:
        logger.error(f"Docker command timed out: {' '.join(cmd)}")
        raise


def _cleanup_image(tag):
    """Clean up Docker image, ensuring it's removed."""
    logger.info(f"Cleaning up Docker image: {tag}")
    result = _run_docker_command(["docker", "rmi", tag], timeout=30)
    if result.returncode != 0:
        # Image might not exist, which is fine
        if "No such image" not in result.stderr:
            logger.warning(f"Failed to remove image {tag}: {result.stderr}")
    else:
        logger.info(f"Successfully removed image: {tag}")


def _cleanup_orphaned_containers(tag_prefix="mealie-backup:test"):
    """Kill any remaining containers from test image."""
    logger.info(f"Killing any orphaned containers from {tag_prefix}")
    # Find containers based on image name
    result = _run_docker_command(
        ["docker", "ps", "-a", "-q", "-f", f"ancestor={tag_prefix}"],
        timeout=30
    )
    if result.returncode == 0 and result.stdout.strip():
        container_ids = result.stdout.strip().split('\n')
        for cid in container_ids:
            if cid.strip():
                logger.warning(f"Killing orphaned container: {cid}")
                _run_docker_command(["docker", "kill", cid], timeout=10)
                _run_docker_command(["docker", "rm", cid], timeout=10)
    else:
        logger.info("No orphaned containers found")


class TestDockerBuild:
    """Test that the Docker image builds successfully."""

    def test_dockerfile_builds(self):
        """Verify the Dockerfile builds without errors."""
        result = _run_docker_command(
            ["docker", "build", "-t", TEST_IMAGE_TAG, str(PROJECT_ROOT)],
            timeout=600
        )
        
        combined_output = result.stdout + result.stderr
        assert result.returncode == 0, f"Docker build failed: {result.stderr}"
        assert "naming to docker.io" in combined_output or "Successfully" in combined_output


class TestDockerContainerRuntime:
    """Test container runtime behavior."""

    @pytest.fixture(scope="class", autouse=True)
    def cleanup_after_class(self):
        """Ensure cleanup happens even if tests fail."""
        yield
        # Cleanup happens after all tests in this class
        logger.info("Running cleanup after test class")
        _cleanup_orphaned_containers(TEST_IMAGE_TAG)
        _cleanup_image(TEST_IMAGE_TAG)

    @pytest.fixture(scope="class")
    def built_image(self):
        """Ensure image is built before running tests. Guaranteed cleanup with try/finally.
        
        The try/finally block ensures cleanup runs even if a test times out or fails,
        including framework timeouts from pytest-timeout (which uses thread interruption).
        """
        logger.info(f"Building Docker image: {TEST_IMAGE_TAG}")
        try:
            result = _run_docker_command(
                ["docker", "build", "-t", TEST_IMAGE_TAG, str(PROJECT_ROOT)],
                timeout=600
            )
            if result.returncode != 0:
                raise RuntimeError(f"Docker build failed: {result.stderr}")
            logger.info(f"Successfully built image: {TEST_IMAGE_TAG}")
            yield
        finally:
            # Guaranteed cleanup - even if test fails
            logger.info("Fixture cleanup: removing containers and image")
            _cleanup_orphaned_containers(TEST_IMAGE_TAG)
            _cleanup_image(TEST_IMAGE_TAG)

    def test_container_starts_without_permission_errors(self, built_image):
        """Verify container starts without permission errors."""
        result = _run_docker_command(
            [
                "docker", "run", "--rm",
                "-e", "MEALIE_URL=http://example.com",
                "-e", "MEALIE_API_TOKEN=test-token",
                "-e", "BACKUP_SCHEDULE=0 0 * * *",
                "--entrypoint", "sh",
                TEST_IMAGE_TAG,
                "-c", "python -m src.scheduler & sleep 2 && kill %1 2>/dev/null || true"
            ],
            timeout=30
        )
        
        combined_output = result.stdout + result.stderr
        assert "Permission denied" not in combined_output
        assert "Operation not permitted" not in combined_output

    def test_configuration_validates_on_startup(self, built_image):
        """Verify configuration can be loaded."""
        result = _run_docker_command(
            [
                "docker", "run", "--rm",
                "-e", "MEALIE_URL=http://localhost:9000",
                "-e", "MEALIE_API_TOKEN=test-token",
                "--entrypoint", "python",
                TEST_IMAGE_TAG,
                "-c", "from src.config import Config; Config(); print('OK')"
            ],
            timeout=30
        )
        
        output = result.stdout + result.stderr
        assert "OK" in output

    def test_missing_mealie_url_fails_validation(self, built_image):
        """Verify missing MEALIE_URL causes config validation to fail."""
        result = _run_docker_command(
            [
                "docker", "run", "--rm",
                "-e", "MEALIE_API_TOKEN=test-token",
                "--entrypoint", "python",
                TEST_IMAGE_TAG,
                "-m", "src.config"
            ],
            timeout=30
        )
        
        assert result.returncode != 0
        output = result.stdout + result.stderr
        assert "required" in output.lower() or "mealie_url" in output.lower()

    def test_invalid_cron_schedule_fails(self, built_image):
        """Verify invalid cron schedule is rejected."""
        result = _run_docker_command(
            [
                "docker", "run", "--rm",
                "-e", "MEALIE_URL=http://example.com",
                "-e", "MEALIE_API_TOKEN=test-token",
                "-e", "BACKUP_SCHEDULE=invalid cron",
                "--entrypoint", "python",
                TEST_IMAGE_TAG,
                "-c", "from src.scheduler import run_scheduler; run_scheduler('invalid cron', lambda: None)"
            ],
            timeout=30
        )
        
        assert result.returncode != 0
        output = result.stdout + result.stderr
        assert "cron" in output.lower() or "invalid" in output.lower()

    def test_scheduler_starts_with_valid_config(self, built_image):
        """Verify scheduler initializes with valid config."""
        result = _run_docker_command(
            [
                "docker", "run", "--rm",
                "-e", "MEALIE_URL=http://localhost:9000",
                "-e", "MEALIE_API_TOKEN=test-token",
                "-e", "BACKUP_SCHEDULE=0 0 * * *",
                "--entrypoint", "sh",
                TEST_IMAGE_TAG,
                "-c", "timeout 3 /app/entrypoint.sh || true"
            ],
            timeout=15
        )
        
        output = result.stdout + result.stderr
        assert "Validating configuration" in output or "Starting mealie-backup" in output
        assert "Permission denied" not in output
        assert "Operation not permitted" not in output

    def test_no_permission_errors_in_container(self, built_image):
        """Verify container runs without permission errors."""
        result = _run_docker_command(
            [
                "docker", "run", "--rm",
                "-e", "MEALIE_URL=http://localhost:9000",
                "-e", "MEALIE_API_TOKEN=test-token",
                TEST_IMAGE_TAG
            ],
            timeout=15
        )
        
        output = result.stdout + result.stderr
        assert "Permission denied" not in output, "Container has permission errors"
        assert "setpgid" not in output, "Container has setpgid errors"
        assert "Operation not permitted" not in output, "Container has operation permission errors"
