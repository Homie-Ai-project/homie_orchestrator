# Configuration Guide

This guide explains how to configure the Homei Orchestrator using the `orchestrator.yaml` configuration file.

## Configuration File Location

The configuration file is located at:
- **Development**: `config/orchestrator.yaml`
- **Production**: `/config/orchestrator.yaml` (inside container)
- **Template**: `config/orchestrator.yaml.template`

## Environment Variables

Configuration values can be overridden using environment variables:

```bash
# Security
export ORCHESTRATOR_SECRET_KEY="your-secret-key-here"

# Database
export POSTGRES_PASSWORD="secure-password"

# Redis
export REDIS_PASSWORD="redis-password"
```

## Configuration Sections

### Basic Configuration

```yaml
orchestrator:
  name: "Homei Orchestrator"
  version: "1.0.0"
  timezone: "UTC"  # or "America/New_York", "Europe/London", etc.
```

### API Configuration

```yaml
api:
  host: "0.0.0.0"        # Bind to all interfaces
  port: 8080             # API server port
  cors_origins:          # Allowed CORS origins
    - "*"                # Allow all (development only)
    - "https://your-domain.com"  # Production setting
```

### Security Configuration

```yaml
security:
  secret_key: "${ORCHESTRATOR_SECRET_KEY:-changeme}"
  access_token_expire_minutes: 60    # JWT token expiration
  refresh_token_expire_days: 30      # Refresh token expiration
```

**Important**: Always change the secret key in production!

### Docker Configuration

```yaml
docker:
  socket_path: "/var/run/docker.sock"  # Docker socket
  network_name: "homei_network"        # Docker network name
  registry:
    url: "docker.io"                   # Docker registry
    username: null                     # Registry username (optional)
    password: null                     # Registry password (optional)
```

### Storage Configuration

```yaml
storage:
  data_path: "/data"        # Persistent data directory
  config_path: "/config"    # Configuration directory
  backup_path: "/backups"   # Backup storage directory
```

### Database Configuration

```yaml
database:
  url: "postgresql+asyncpg://homei:homei_password@postgres:5432/homei"
  pool_size: 10        # Connection pool size
  max_overflow: 20     # Maximum pool overflow
```

**URL Format**: `postgresql+asyncpg://username:password@host:port/database`

### Redis Configuration

```yaml
redis:
  url: "redis://redis:6379/0"  # Redis connection URL
```

**URL Format**: `redis://[username:password@]host:port/database`

### Logging Configuration

```yaml
logging:
  level: "INFO"           # DEBUG, INFO, WARNING, ERROR
  format: "structured"    # structured or plain
```

### Monitoring Configuration

```yaml
monitoring:
  enabled: true                    # Enable monitoring
  metrics_port: 9090              # Prometheus metrics port
  health_check_interval: 30       # Health check interval (seconds)
```

### Backup Configuration

```yaml
backup:
  enabled: true                    # Enable automatic backups
  schedule: "0 2 * * *"           # Cron schedule (daily at 2 AM)
  retention_days: 30              # Backup retention period
```

## Managed Services Configuration

The orchestrator can manage Docker services defined in the configuration:

### Core Application Service

```yaml
services:
  homei_core:
    image: "homei/core:latest"
    enabled: true
    restart_policy: "unless-stopped"
    environment:
      POSTGRES_URL: "postgresql://homei:homei_password@postgres:5432/homei"
      REDIS_URL: "redis://redis:6379/0"
    ports:
      - "8123:8123"
    volumes:
      - "./config/core:/config"
      - "./data/core:/data"
    depends_on:
      - postgres
      - redis
    labels:
      io.homei.managed: "true"
      io.homei.service: "core"
```

### Database Service

```yaml
services:
  postgres:
    image: "postgres:15"
    enabled: true
    restart_policy: "unless-stopped"
    environment:
      POSTGRES_DB: "homei"
      POSTGRES_USER: "homei"
      POSTGRES_PASSWORD: "homei_password"
    volumes:
      - "./data/postgres:/var/lib/postgresql/data"
    labels:
      io.homei.managed: "true"
      io.homei.service: "database"
```

### Cache Service

```yaml
services:
  redis:
    image: "redis:7-alpine"
    enabled: true
    restart_policy: "unless-stopped"
    volumes:
      - "./data/redis:/data"
    labels:
      io.homei.managed: "true"
      io.homei.service: "cache"
```

## Service Configuration Options

### Required Fields

- `image`: Docker image name and tag
- `enabled`: Whether the service should be started

### Optional Fields

- `restart_policy`: Docker restart policy (`no`, `always`, `unless-stopped`, `on-failure`)
- `environment`: Environment variables (key-value pairs)
- `ports`: Port mappings (`"host_port:container_port"`)
- `volumes`: Volume mounts (`"host_path:container_path"`)
- `depends_on`: List of services this service depends on
- `labels`: Docker labels (key-value pairs)
- `networks`: Docker networks to connect to
- `command`: Override container command
- `healthcheck`: Container health check configuration

### Advanced Service Example

```yaml
services:
  my_service:
    image: "nginx:alpine"
    enabled: true
    restart_policy: "unless-stopped"
    environment:
      NGINX_HOST: "localhost"
      NGINX_PORT: "80"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "./config/nginx:/etc/nginx/conf.d"
      - "./data/www:/var/www/html"
    depends_on:
      - backend_service
    labels:
      io.homei.managed: "true"
      io.homei.service: "webserver"
      traefik.enable: "true"
    networks:
      - homei_network
      - external_network
    command: ["nginx", "-g", "daemon off;"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Environment-Specific Configurations

### Development Configuration

```yaml
orchestrator:
  api:
    cors_origins:
      - "*"
  logging:
    level: "DEBUG"
  monitoring:
    health_check_interval: 10
```

### Production Configuration

```yaml
orchestrator:
  api:
    cors_origins:
      - "https://your-domain.com"
      - "https://admin.your-domain.com"
  security:
    secret_key: "${ORCHESTRATOR_SECRET_KEY}"
  logging:
    level: "INFO"
  monitoring:
    health_check_interval: 30
```

### High Availability Configuration

```yaml
orchestrator:
  database:
    pool_size: 20
    max_overflow: 40
  redis:
    url: "redis://redis-cluster:6379/0"
  backup:
    schedule: "0 */6 * * *"  # Every 6 hours
    retention_days: 90
```

## Configuration Validation

The orchestrator validates configuration on startup. Common validation errors:

### Invalid URL Format
```
Error: Invalid database URL format
Fix: Use postgresql+asyncpg://user:pass@host:port/db
```

### Missing Required Fields
```
Error: Field 'secret_key' is required
Fix: Set ORCHESTRATOR_SECRET_KEY environment variable
```

### Port Conflicts
```
Error: Port 8080 already in use
Fix: Change api.port or stop conflicting service
```

## Configuration Best Practices

### Security
1. **Never commit secrets** to version control
2. **Use environment variables** for sensitive data
3. **Generate strong secret keys**: `openssl rand -hex 32`
4. **Rotate secrets regularly**

### Performance
1. **Tune database pool size** based on load
2. **Adjust health check intervals** based on requirements
3. **Configure appropriate timeouts**

### Monitoring
1. **Enable structured logging** for better parsing
2. **Set appropriate log levels** (INFO for production)
3. **Configure backup retention** based on storage capacity

### Networking
1. **Use specific CORS origins** in production
2. **Configure firewall rules** for exposed ports
3. **Use Docker networks** for service isolation

## Configuration Examples

### Minimal Configuration

```yaml
orchestrator:
  security:
    secret_key: "${ORCHESTRATOR_SECRET_KEY}"
  database:
    url: "postgresql+asyncpg://homei:password@postgres:5432/homei"

services:
  postgres:
    image: "postgres:15"
    enabled: true
    environment:
      POSTGRES_DB: "homei"
      POSTGRES_USER: "homei"
      POSTGRES_PASSWORD: "password"
```

### Full Production Configuration

```yaml
orchestrator:
  name: "Homei Production Orchestrator"
  version: "1.0.0"
  timezone: "UTC"
  
  api:
    host: "0.0.0.0"
    port: 8080
    cors_origins:
      - "https://homei.example.com"
  
  security:
    secret_key: "${ORCHESTRATOR_SECRET_KEY}"
    access_token_expire_minutes: 30
    refresh_token_expire_days: 7
  
  database:
    url: "postgresql+asyncpg://homei:${POSTGRES_PASSWORD}@postgres:5432/homei"
    pool_size: 15
    max_overflow: 25
  
  redis:
    url: "redis://:${REDIS_PASSWORD}@redis:6379/0"
  
  logging:
    level: "INFO"
    format: "structured"
  
  monitoring:
    enabled: true
    metrics_port: 9090
    health_check_interval: 60
  
  backup:
    enabled: true
    schedule: "0 3 * * *"
    retention_days: 90

services:
  homei_core:
    image: "homei/core:v1.0.0"
    enabled: true
    restart_policy: "unless-stopped"
    environment:
      POSTGRES_URL: "postgresql://homei:${POSTGRES_PASSWORD}@postgres:5432/homei"
      REDIS_URL: "redis://:${REDIS_PASSWORD}@redis:6379/0"
    ports:
      - "8123:8123"
    volumes:
      - "/data/core:/data"
    depends_on:
      - postgres
      - redis
    labels:
      io.homei.managed: "true"
      io.homei.service: "core"

  postgres:
    image: "postgres:15"
    enabled: true
    restart_policy: "unless-stopped"
    environment:
      POSTGRES_DB: "homei"
      POSTGRES_USER: "homei"
      POSTGRES_PASSWORD: "${POSTGRES_PASSWORD}"
    volumes:
      - "/data/postgres:/var/lib/postgresql/data"
    labels:
      io.homei.managed: "true"
      io.homei.service: "database"

  redis:
    image: "redis:7-alpine"
    enabled: true
    restart_policy: "unless-stopped"
    command: ["redis-server", "--requirepass", "${REDIS_PASSWORD}"]
    volumes:
      - "/data/redis:/data"
    labels:
      io.homei.managed: "true"
      io.homei.service: "cache"
```

## Troubleshooting Configuration

### Validate Configuration
```bash
# Test configuration syntax
python -c "import yaml; yaml.safe_load(open('config/orchestrator.yaml'))"

# Check environment variable substitution
docker-compose config
```

### Common Issues

1. **YAML syntax errors**: Use a YAML validator
2. **Environment variable not found**: Check variable names and values
3. **Service dependencies**: Ensure `depends_on` services exist
4. **Port conflicts**: Check for conflicting port mappings
5. **Volume permissions**: Ensure directories exist and are writable

For more help, see the [Troubleshooting Guide](troubleshooting.md).
