#!/bin/sh
# Entrypoint for mealie-backup container

set -e

echo "Starting mealie-backup container..."

# Validate configuration
echo "Validating configuration..."
python -m src.config

# Start scheduler with backup cron schedule
echo "Starting scheduler with cron schedule: $BACKUP_SCHEDULE"
exec python << 'EOF'
import sys
import logging
from src.backup import run_backup
from src.scheduler import run_scheduler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import os
cron_schedule = os.getenv('BACKUP_SCHEDULE', '0 0 * * *')
run_scheduler(cron_schedule, run_backup)
EOF
