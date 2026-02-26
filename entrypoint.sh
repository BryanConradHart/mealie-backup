#!/bin/sh
# Entrypoint for mealie-backup container

set -e

echo "Starting mealie-backup container..."

# Validate configuration
echo "Validating configuration..."
python -m src.config

# Export environment variables for cron
env >> /etc/environment

# Write crontab with the backup schedule
echo "Setting up backup schedule: $BACKUP_SCHEDULE"
BACKUP_CMD="cd /app && python -m src.backup"
CRON_JOB="$BACKUP_SCHEDULE $BACKUP_CMD >> /proc/1/fd/1 2>&1"

# Create crontab file
mkdir -p /etc/crontabs
echo "$CRON_JOB" > /etc/crontabs/backup

# Validate crontab
echo "Installing crontab..."
crontab /etc/crontabs/backup

# Start cron daemon in foreground
echo "Starting cron daemon..."
exec crond -f -l 2
