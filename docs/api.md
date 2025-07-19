# API Reference

This document provides comprehensive API documentation for the Homei Orchestrator REST API.

## Base URL

```
http://localhost:8080
```

## Authentication

Currently, the API uses JWT token-based authentication (to be implemented).

```http
Authorization: Bearer <token>
```

## Health Endpoints

### Health Check

Check overall system health.

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Readiness Check

Check if the system is ready to serve requests.

```http
GET /health/ready
```

**Response:**
```json
{
  "status": "ready"
}
```

### Liveness Check

Check if the system is alive and responding.

```http
GET /health/live
```

**Response:**
```json
{
  "status": "alive"
}
```

## Service Management

### List Services

Get all managed services.

```http
GET /api/v1/services
```

**Response:**
```json
{
  "services": [
    {
      "name": "postgres",
      "image": "postgres:15",
      "status": "running",
      "enabled": true,
      "restart_policy": "unless-stopped",
      "created_at": "2024-01-15T10:00:00Z",
      "labels": {
        "io.homei.managed": "true",
        "io.homei.service": "database"
      }
    }
  ]
}
```

### Get Service

Get details of a specific service.

```http
GET /api/v1/services/{service_name}
```

**Response:**
```json
{
  "name": "postgres",
  "image": "postgres:15",
  "status": "running",
  "enabled": true,
  "restart_policy": "unless-stopped",
  "environment": {
    "POSTGRES_DB": "homei",
    "POSTGRES_USER": "homei"
  },
  "ports": ["5432:5432"],
  "volumes": ["/data/postgres:/var/lib/postgresql/data"],
  "depends_on": [],
  "labels": {
    "io.homei.managed": "true",
    "io.homei.service": "database"
  },
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

### Create Service

Create a new managed service.

```http
POST /api/v1/services
```

**Request Body:**
```json
{
  "name": "my-service",
  "image": "nginx:alpine",
  "enabled": true,
  "restart_policy": "unless-stopped",
  "environment": {
    "NGINX_HOST": "localhost"
  },
  "ports": ["80:80"],
  "volumes": ["/data/nginx:/var/www/html"],
  "labels": {
    "io.homei.service": "webserver"
  }
}
```

**Response:**
```json
{
  "name": "my-service",
  "status": "created",
  "message": "Service created successfully"
}
```

### Update Service

Update an existing service.

```http
PUT /api/v1/services/{service_name}
```

**Request Body:**
```json
{
  "image": "nginx:latest",
  "enabled": true,
  "environment": {
    "NGINX_HOST": "example.com"
  }
}
```

**Response:**
```json
{
  "name": "my-service",
  "status": "updated",
  "message": "Service updated successfully"
}
```

### Delete Service

Delete a managed service.

```http
DELETE /api/v1/services/{service_name}
```

**Response:**
```json
{
  "name": "my-service",
  "status": "deleted",
  "message": "Service deleted successfully"
}
```

### Start Service

Start a stopped service.

```http
POST /api/v1/services/{service_name}/start
```

**Response:**
```json
{
  "name": "my-service",
  "status": "started",
  "message": "Service started successfully"
}
```

### Stop Service

Stop a running service.

```http
POST /api/v1/services/{service_name}/stop
```

**Response:**
```json
{
  "name": "my-service",
  "status": "stopped",
  "message": "Service stopped successfully"
}
```

### Restart Service

Restart a service.

```http
POST /api/v1/services/{service_name}/restart
```

**Response:**
```json
{
  "name": "my-service",
  "status": "restarted",
  "message": "Service restarted successfully"
}
```

## Container Management

### List Containers

Get all containers (managed and unmanaged).

```http
GET /api/v1/containers
```

**Query Parameters:**
- `managed`: Filter by managed status (`true`/`false`)
- `status`: Filter by status (`running`, `stopped`, etc.)

**Response:**
```json
{
  "containers": [
    {
      "id": "abc123def456",
      "name": "postgres",
      "image": "postgres:15",
      "status": "running",
      "managed": true,
      "created_at": "2024-01-15T10:00:00Z",
      "ports": [
        {
          "private_port": 5432,
          "public_port": 5432,
          "type": "tcp"
        }
      ]
    }
  ]
}
```

### Get Container

Get details of a specific container.

```http
GET /api/v1/containers/{container_id}
```

**Response:**
```json
{
  "id": "abc123def456",
  "name": "postgres",
  "image": "postgres:15",
  "status": "running",
  "managed": true,
  "state": {
    "status": "running",
    "running": true,
    "pid": 1234,
    "started_at": "2024-01-15T10:00:00Z"
  },
  "config": {
    "hostname": "abc123def456",
    "env": ["POSTGRES_DB=homei"],
    "cmd": ["docker-entrypoint.sh", "postgres"]
  },
  "network_settings": {
    "ports": {
      "5432/tcp": [{"host_ip": "0.0.0.0", "host_port": "5432"}]
    }
  }
}
```

### Container Logs

Get logs from a container.

```http
GET /api/v1/containers/{container_id}/logs
```

**Query Parameters:**
- `tail`: Number of lines to return (default: 100)
- `follow`: Stream logs (`true`/`false`)
- `timestamps`: Include timestamps (`true`/`false`)

**Response:**
```json
{
  "logs": [
    "2024-01-15 10:00:00 LOG:  database system is ready to accept connections",
    "2024-01-15 10:00:01 LOG:  autovacuum launcher started"
  ]
}
```

### Container Stats

Get resource usage statistics for a container.

```http
GET /api/v1/containers/{container_id}/stats
```

**Response:**
```json
{
  "cpu_percent": 12.5,
  "memory_usage": {
    "usage": 134217728,
    "limit": 1073741824,
    "percent": 12.5
  },
  "network_io": {
    "rx_bytes": 1024,
    "tx_bytes": 2048
  },
  "block_io": {
    "read_bytes": 4096,
    "write_bytes": 8192
  }
}
```

## Backup Management

### List Backups

Get all available backups.

```http
GET /api/v1/backups
```

**Response:**
```json
{
  "backups": [
    {
      "name": "backup-20240115-100000.tar.gz",
      "created_at": "2024-01-15T10:00:00Z",
      "size": 1073741824,
      "type": "full"
    }
  ]
}
```

### Create Backup

Create a new backup.

```http
POST /api/v1/backups
```

**Request Body:**
```json
{
  "name": "manual-backup",
  "type": "full",
  "include_data": true
}
```

**Response:**
```json
{
  "name": "manual-backup-20240115-103000.tar.gz",
  "status": "created",
  "message": "Backup created successfully"
}
```

### Restore Backup

Restore from a backup.

```http
POST /api/v1/backups/{backup_name}/restore
```

**Response:**
```json
{
  "status": "restored",
  "message": "Backup restored successfully"
}
```

### Delete Backup

Delete a backup.

```http
DELETE /api/v1/backups/{backup_name}
```

**Response:**
```json
{
  "status": "deleted",
  "message": "Backup deleted successfully"
}
```

## System Updates (RAUC Integration)

### Get Update Status

Check RAUC system status.

```http
GET /api/v1/update/status
```

**Response:**
```json
{
  "compatible": "jetson-nano-homei",
  "booted": "rootfs.0",
  "slots": [
    {
      "name": "rootfs.0",
      "class": "rootfs",
      "device": "/dev/mmcblk0p2",
      "type": "ext4",
      "bootname": "A",
      "state": "booted",
      "sha256": "abc123...",
      "size": 16777216000,
      "installed": {
        "timestamp": "2024-01-15T10:00:00Z",
        "count": 1
      }
    },
    {
      "name": "rootfs.1",
      "class": "rootfs",
      "device": "/dev/mmcblk0p3",
      "type": "ext4",
      "bootname": "B",
      "state": "inactive",
      "sha256": "def456...",
      "size": 16777216000,
      "installed": {
        "timestamp": "2024-01-10T10:00:00Z",
        "count": 0
      }
    }
  ]
}
```

### Install Update

Install a RAUC update bundle.

```http
POST /api/v1/update/install
```

**Request Body:**
```json
{
  "bundle_path": "/data/updates/homei-v1.1.0.raucb"
}
```

**Response:**
```json
{
  "status": "installing",
  "message": "Update installation started"
}
```

### Mark Slot as Good

Mark the current slot as good (prevents automatic rollback).

```http
POST /api/v1/update/mark-good
```

**Response:**
```json
{
  "status": "success",
  "message": "Current slot marked as good"
}
```

## Monitoring

### Get Metrics

Get Prometheus metrics.

```http
GET /metrics
```

**Response:**
```
# HELP homei_containers_total Total number of containers
# TYPE homei_containers_total gauge
homei_containers_total{status="running"} 3
homei_containers_total{status="stopped"} 1

# HELP homei_services_total Total number of managed services
# TYPE homei_services_total gauge
homei_services_total{enabled="true"} 3
homei_services_total{enabled="false"} 0
```

### System Information

Get system information and statistics.

```http
GET /api/v1/system/info
```

**Response:**
```json
{
  "hostname": "jetson-nano",
  "platform": "linux",
  "architecture": "aarch64",
  "cpu_count": 4,
  "memory": {
    "total": 4294967296,
    "available": 2147483648,
    "percent": 50.0
  },
  "disk": {
    "total": 64424509440,
    "used": 32212254720,
    "free": 32212254720,
    "percent": 50.0
  },
  "uptime": 86400,
  "load_average": [0.5, 0.4, 0.3]
}
```

## Configuration

### Get Configuration

Get current orchestrator configuration.

```http
GET /api/v1/config
```

**Response:**
```json
{
  "orchestrator": {
    "name": "Homei Orchestrator",
    "version": "1.0.0",
    "api": {
      "host": "0.0.0.0",
      "port": 8080
    },
    "monitoring": {
      "enabled": true,
      "metrics_port": 9090
    }
  }
}
```

### Update Configuration

Update orchestrator configuration.

```http
PUT /api/v1/config
```

**Request Body:**
```json
{
  "orchestrator": {
    "monitoring": {
      "health_check_interval": 60
    }
  }
}
```

**Response:**
```json
{
  "status": "updated",
  "message": "Configuration updated successfully"
}
```

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "error": {
    "code": "SERVICE_NOT_FOUND",
    "message": "Service 'my-service' not found",
    "details": {
      "service_name": "my-service"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Common Error Codes

- `VALIDATION_ERROR`: Request validation failed
- `SERVICE_NOT_FOUND`: Requested service does not exist
- `CONTAINER_NOT_FOUND`: Requested container does not exist
- `DOCKER_ERROR`: Docker operation failed
- `BACKUP_ERROR`: Backup operation failed
- `UPDATE_ERROR`: Update operation failed
- `CONFIG_ERROR`: Configuration error
- `INTERNAL_ERROR`: Internal server error

## Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created
- `400 Bad Request`: Invalid request
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict
- `500 Internal Server Error`: Server error

## WebSocket Endpoints

### Container Logs Stream

Stream container logs in real-time.

```
ws://localhost:8080/ws/containers/{container_id}/logs
```

### System Events

Stream system events.

```
ws://localhost:8080/ws/events
```

**Event Format:**
```json
{
  "type": "container.start",
  "data": {
    "container_id": "abc123def456",
    "name": "postgres"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Health endpoints**: 60 requests per minute
- **Service management**: 30 requests per minute
- **Container operations**: 20 requests per minute
- **Backup operations**: 10 requests per minute
- **Update operations**: 5 requests per minute

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1642248000
```

## Examples

### cURL Examples

```bash
# Health check
curl http://localhost:8080/health

# List services
curl http://localhost:8080/api/v1/services

# Create service
curl -X POST http://localhost:8080/api/v1/services \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nginx",
    "image": "nginx:alpine",
    "enabled": true,
    "ports": ["80:80"]
  }'

# Get container logs
curl "http://localhost:8080/api/v1/containers/abc123/logs?tail=50"

# Install update
curl -X POST http://localhost:8080/api/v1/update/install \
  -H "Content-Type: application/json" \
  -d '{"bundle_path": "/data/updates/update.raucb"}'
```

### Python Examples

```python
import requests

# Health check
response = requests.get("http://localhost:8080/health")
print(response.json())

# List services
response = requests.get("http://localhost:8080/api/v1/services")
services = response.json()["services"]

# Create service
service_data = {
    "name": "redis",
    "image": "redis:alpine",
    "enabled": True,
    "ports": ["6379:6379"]
}
response = requests.post("http://localhost:8080/api/v1/services", json=service_data)
print(response.json())

# Stream container logs
import websocket

def on_message(ws, message):
    print(f"Log: {message}")

ws = websocket.WebSocketApp(
    "ws://localhost:8080/ws/containers/abc123/logs",
    on_message=on_message
)
ws.run_forever()
```

For interactive API exploration, visit the auto-generated documentation at:
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
