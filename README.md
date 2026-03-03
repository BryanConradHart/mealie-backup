# Mealie-backup
This project is intended to be a simple solution for people who want to schedule their [mealie](https://mealie.io/) backups, and use docker compose.

**Warning:** This is AI slop, I made this messing around with AI doing little projects I had no energy to do myself.

## Why

Mealie has an [extensive API](https://docs.mealie.io/documentation/getting-started/api-usage/) with the ability to manage backups, but there is no built-in way to schedule automatic backups. This project fills that gap by providing a simple, dependency-minimal container that:

- Runs on a schedule of your choice (default: daily at midnight)
- Automatically creates backups via the Mealie API
- Manages backup retention using a GFS (Grandfather-Father-Son) policy
- Integrates seamlessly with docker-compose
- Provides healthcheck support for monitoring

## How It Works

1. The container validates your Mealie configuration on startup
2. On the configured schedule, it creates a backup via the Mealie API
3. It evaluates all existing backups against your retention policy
4. It deletes any backups that fall outside the retention policy
5. It updates a healthcheck marker file after each successful run

## Configuration

All configuration is done via environment variables. Add the container to your docker-compose file and set these variables:

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `MEALIE_URL` | Base URL of your Mealie instance | `http://mealie:9000` |
| `MEALIE_API_TOKEN` | Long-lived API token with admin access | `your-api-token-here` |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKUP_SCHEDULE` | `0 0 * * *` | Cron schedule for backups (midnight daily) |
| `TZ` | `UTC` | Container timezone (e.g., `America/New_York`) |
| `RETENTION_DAILY` | `7` | Number of daily backups to keep (0 to disable) |
| `RETENTION_WEEKLY` | `4` | Number of weekly backups to keep (0 to disable) |
| `RETENTION_MONTHLY` | `6` | Number of monthly backups to keep (0 to disable) |
| `RETENTION_YEARLY` | `1` | Number of yearly backups to keep (0 to disable) |

**Note:** At least one retention tier must be set to a value greater than 0. For example, you could keep only daily backups by setting:
```
RETENTION_DAILY=7
RETENTION_WEEKLY=0
RETENTION_MONTHLY=0
RETENTION_YEARLY=0
```

### Retention Policy Details

The retention policy follows GFS (Grandfather-Father-Son) scheduling:

- **Daily**: Latest backup from each calendar day (up to 7 backups)
- **Weekly**: Latest backup from each ISO week (up to 4 backups)
- **Monthly**: Latest backup from each calendar month (up to 6 backups)
- **Yearly**: Latest backup from each calendar year (up to 1 backup)

Backups are kept if they satisfy **any** retention tier. For example, if you keep 7 daily, 4 weekly, and 6 monthly backups, a backup created 60 days ago might be retained as a monthly representative even if it's older than 7 days.

## Getting Your API Token

1. Log in to your Mealie instance as an admin user
2. Navigate to Profile → API Tokens
3. Click "Create API Token" and give it a descriptive name (e.g., "Backup Service")
4. Copy the generated token and keep it safe

## Docker Compose Example

Add this service to your existing docker-compose file:

```yaml
services:
  mealie:
    image: ghcr.io/mealie-community/mealie:latest
    # ... other mealie configuration ...

  mealie-backup:
    image: ghcr.io/bryanconradhart/mealie-backup:latest
    environment:
      - MEALIE_URL=http://mealie:9000
      - MEALIE_API_TOKEN=${MEALIE_BACKUP_TOKEN}
      - TZ=America/New_York
      - BACKUP_SCHEDULE=0 0 * * *
      - RETENTION_DAILY=7
      - RETENTION_WEEKLY=4
      - RETENTION_MONTHLY=6
      - RETENTION_YEARLY=1
    healthcheck:
      test: ["CMD", "test", "-f", "/tmp/healthy"]
      interval: 86400s
      timeout: 60s
      retries: 3
      start_period: 30s
    restart: unless-stopped
    depends_on:
      - mealie
```

**Important:** `MEALIE_URL=http://mealie:9000` uses the service name from docker-compose. This works because both containers are on the same Docker network. No need to change this unless your Mealie service has a different name.

Then set the `MEALIE_BACKUP_TOKEN` environment variable in your `.env` file:

```
MEALIE_BACKUP_TOKEN=your-api-token-here
```

## Healthcheck

The container includes a built-in healthcheck that verifies:
- The healthcheck marker file exists
- The marker file has been updated within the last 24 hours (indicating recent successful backup runs)

Docker Compose will mark the container as unhealthy if:
- The marker file doesn't exist (configuration validation failed)
- The marker file hasn't been updated in 24+ hours (backups are not running)

## Development

### Setting Up

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/yourusername/mealie-backup.git
cd mealie-backup

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Testing

The project includes both unit tests and Docker integration tests to catch runtime issues.

**Install development dependencies:**

```bash
pip install -r requirements-dev.txt
```

**Run unit tests only:**

```bash
pytest tests/ -v -m "not slow" --ignore=tests/test_docker_integration.py
```

**Run Docker integration tests:**

*Requires Docker to be installed and running*

```bash
pytest tests/test_docker_integration.py -v
```

**Run all tests (unit + integration):**

```bash
pytest tests/ -v
```

**What integration tests validate:**
- ✅ Docker image builds successfully
- ✅ Container starts without permission errors
- ✅ Configuration validation works  
- ✅ Scheduler initializes with cron expressions
- ✅ Invalid configurations are rejected

**Integration Test Architecture:**

The integration tests use a subprocess-based approach (Docker CLI) rather than testcontainers. This is intentional:

- **Testcontainers limitations on Windows**: testcontainers has known issues with tar archive creation on Windows due to WSL2 filesystem interop performance. The Docker Python SDK's `tar()` operation can timeout on Windows when building images.
- **Subprocess reliability**: Direct Docker CLI invocation via subprocess is more reliable on Windows and doesn't require complex resource management libraries.
- **Cleanup strategy**: Tests use multi-layer cleanup (try/finally in fixtures, autouse fixtures at class/session scope) to guarantee resource cleanup even if tests timeout or fail.
- **Timeout protection**: pytest-timeout provides framework-level protection (120s default), while subprocess calls have individual timeouts (30-600s based on operation).

**Test backup operation locally with your own Mealie instance:**

```bash
export MEALIE_URL=http://localhost:9000
export MEALIE_API_TOKEN=your-test-token
python -m src.backup
```

### Changing the Dockerfile Base Image Version

Update the `FROM` line in [Dockerfile](Dockerfile) and rebuild:

```dockerfile
FROM python:3.12-alpine
```

```bash
docker build -t mealie-backup:latest .
```

## Usage Guide

### Quick Start

1. **Get your Mealie API Token:**
   - Log in to your Mealie instance
   - Go to Profile → API Tokens
   - Create a new token and copy it

2. **Add mealie-backup to your docker-compose file:**
```yaml
services:
  mealie:
    image: ghcr.io/mealie-community/mealie:latest
    # ... your existing mealie config ...

  mealie-backup:
    image: ghcr.io/yourusername/mealie-backup:latest
    environment:
      - MEALIE_URL=http://mealie:9000
      - MEALIE_API_TOKEN=${MEALIE_BACKUP_TOKEN}
      - TZ=America/New_York
    healthcheck:
      test: ["CMD", "test", "-f", "/tmp/healthy"]
      interval: 86400s
      timeout: 5s
      retries: 3
      start_period: 30s
    restart: unless-stopped
    depends_on:
      - mealie
```

3. **Set the token in `.env`:**
```
MEALIE_BACKUP_TOKEN=your-api-token-here
```

4. **Start the services:**
```bash
docker-compose up -d
```

5. **Verify it's working:**
```bash
# Check logs
docker-compose logs mealie-backup

# Verify healthcheck
docker-compose ps
```

### Common Configurations

Only include overrides; everything else uses defaults.

**Daily backups only (keep 7 days):**
```yaml
environment:
  - RETENTION_WEEKLY=0
  - RETENTION_MONTHLY=0
  - RETENTION_YEARLY=0
```

**One year of backups with weekly snapshots:**
```yaml
environment:
  - RETENTION_DAILY=1
  - RETENTION_MONTHLY=12
```

**Backup every 6 hours for 3 days:**
```yaml
environment:
  - BACKUP_SCHEDULE=0 */6 * * *
  - RETENTION_DAILY=3
  - RETENTION_WEEKLY=0
  - RETENTION_MONTHLY=0
  - RETENTION_YEARLY=0
```

**Custom timezone:**
```yaml
environment:
  - TZ=Europe/London
  - BACKUP_SCHEDULE=0 2 * * *  # 2 AM London time
```

### Monitoring

Check backup status:
```bash
# View logs
docker-compose logs mealie-backup

# Check if container is healthy
docker-compose ps

# Check backup marker file
docker-compose exec mealie-backup test -f /tmp/healthy && echo "Healthy" || echo "Unhealthy"
```

List all backups via API:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://your-mealie:9000/api/admin/backups
```

## CI/CD

This project includes a GitHub Actions workflow that:

1. Runs the test suite on every push and pull request
2. Builds and publishes the Docker image to GitHub Container Registry (ghcr.io) on version tags
3. Supports multi-platform builds (amd64 and arm64)

To publish a release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The image will be available at `ghcr.io/YOUR_USERNAME/mealie-backup:v1.0.0`

## Troubleshooting

### Container won't start: "Configuration validation failed"

Check the logs for the specific error:
```bash
docker logs <container_id>
```

Common issues:
- `MEALIE_URL` is required
- `MEALIE_API_TOKEN` is required
- API token is invalid or doesn't have admin access
- Mealie instance is not reachable from the container
- All retention tiers (daily, weekly, monthly, yearly) are set to 0 — at least one must be > 0

### No backups are being created

1. Check that the backup schedule cron expression is valid (use https://crontab.guru/)
2. Verify the container is running: `docker ps`
3. Check the logs for errors: `docker logs <container_id>`
4. Verify the healthcheck is passing: `docker inspect <container_id>`

### Backups not being deleted

Check the retention policy configuration and the dates of existing backups:
```bash
# List backups via Mealie API
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://your-mealie:9000/api/admin/backups
```

Verify that the backup dates are being parsed correctly by checking the logs.