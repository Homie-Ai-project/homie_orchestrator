#!/bin/bash
set -e

# Initialize orchestrator
echo "Starting Homei Orchestrator..."

# Check if Docker socket is available
if [ ! -S /var/run/docker.sock ]; then
    echo "Error: Docker socket not available at /var/run/docker.sock"
    exit 1
fi

# Test Docker connectivity
docker version > /dev/null 2>&1 || {
    echo "Error: Cannot connect to Docker daemon"
    exit 1
}

# Create necessary directories
mkdir -p /data/orchestrator /config/orchestrator /backups

# Set permissions
chown -R orchestrator:orchestrator /data /config /backups 2>/dev/null || true

# Initialize configuration if not exists
if [ ! -f /config/orchestrator.yaml ]; then
    echo "Creating default configuration..."
    cp /app/config/orchestrator.yaml.template /config/orchestrator.yaml
fi

# Start the orchestrator
exec "$@"
