# Multi-stage Docker build for mealie-backup

FROM python:3.12-alpine as base

# Install runtime dependencies (minimal for Alpine)
RUN apk add --no-cache \
    ca-certificates

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY entrypoint.sh .

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Create a non-root user
RUN addgroup -g 1000 -S backup && \
    adduser -u 1000 -S backup -G backup && \
    mkdir -p /tmp && chmod 777 /tmp

# Set environment defaults
ENV MEALIE_URL=""
ENV MEALIE_API_TOKEN=""
ENV BACKUP_SCHEDULE="0 0 * * *"
ENV TZ="UTC"
ENV RETENTION_DAILY="7"
ENV RETENTION_WEEKLY="4"
ENV RETENTION_MONTHLY="6"
ENV RETENTION_YEARLY="1"

# Use non-root user
USER backup

# Health check: verify the marker file is updated within 24 hours
HEALTHCHECK --interval=60s --timeout=5s --retries=3 --start-period=30s \
    CMD test -f /tmp/healthy && [ $(find /tmp/healthy -mtime -1 2>/dev/null | wc -l) -eq 1 ] || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
