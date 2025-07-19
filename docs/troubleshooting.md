# Troubleshooting Guide

This guide helps resolve common issues with the Homei Orchestrator.

## Common Issues

### Installation Issues

#### Docker Permission Denied

**Problem**: `permission denied while trying to connect to the Docker daemon socket`

**Solution**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Apply group changes
newgrp docker

# Or logout/login again
```

#### Port Already in Use

**Problem**: `Port 8080 is already allocated`

**Solution**:
```bash
# Find process using the port
sudo lsof -i :8080
sudo netstat -tulpn | grep :8080

# Kill the process
sudo kill -9 <PID>

# Or change the port in configuration
```

#### Database Connection Failed

**Problem**: `connection to server at "postgres" failed`

**Solution**:
```bash
# Check if PostgreSQL container is running
docker ps | grep postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test database connectivity
docker exec -it postgres psql -U homei -d homei

# Restart PostgreSQL
docker-compose restart postgres
```

#### Redis Connection Failed

**Problem**: `Error connecting to Redis`

**Solution**:
```bash
# Check Redis container
docker ps | grep redis

# Check Redis logs
docker-compose logs redis

# Test Redis connectivity
docker exec -it redis redis-cli ping

# Restart Redis
docker-compose restart redis
```

### Runtime Issues

#### Orchestrator Won't Start

**Problem**: Orchestrator fails to start or crashes immediately

**Diagnosis**:
```bash
# Check orchestrator logs
docker-compose logs orchestrator

# Check container status
docker ps -a | grep orchestrator

# Check system resources
df -h
free -h
```

**Common Solutions**:

1. **Configuration Error**:
   ```bash
   # Validate YAML syntax
   python -c "import yaml; yaml.safe_load(open('config/orchestrator.yaml'))"
   
   # Check environment variables
   echo $ORCHESTRATOR_SECRET_KEY
   ```

2. **Missing Secret Key**:
   ```bash
   export ORCHESTRATOR_SECRET_KEY=$(openssl rand -hex 32)
   ```

3. **Database Not Ready**:
   ```bash
   # Wait for database
   docker-compose up -d postgres
   sleep 30
   docker-compose up orchestrator
   ```

#### Service Health Checks Failing

**Problem**: `/health` endpoint returns errors

**Diagnosis**:
```bash
# Check health endpoint
curl -v http://localhost:8080/health

# Check specific health components
curl http://localhost:8080/health/ready
curl http://localhost:8080/health/live
```

**Solutions**:

1. **Database Health**:
   ```bash
   # Test database connection
   docker exec -it postgres psql -U homei -d homei -c "SELECT 1;"
   ```

2. **Redis Health**:
   ```bash
   # Test Redis connection
   docker exec -it redis redis-cli ping
   ```

3. **Docker Socket**:
   ```bash
   # Check Docker socket permissions
   ls -la /var/run/docker.sock
   
   # Test Docker connectivity
   docker ps
   ```

#### Container Management Issues

**Problem**: Can't start/stop managed containers

**Diagnosis**:
```bash
# Check Docker daemon
sudo systemctl status docker

# Check Docker socket in container
docker exec -it orchestrator ls -la /var/run/docker.sock

# Check container labels
docker ps --filter "label=io.homei.managed=true"
```

**Solutions**:

1. **Docker Socket Mount**:
   ```yaml
   # In docker-compose.yml
   volumes:
     - /var/run/docker.sock:/var/run/docker.sock:rw
   ```

2. **Network Issues**:
   ```bash
   # Check Docker networks
   docker network ls
   docker network inspect homei_network
   ```

### Configuration Issues

#### YAML Syntax Errors

**Problem**: Configuration file has syntax errors

**Diagnosis**:
```bash
# Validate YAML
python -c "
import yaml
try:
    with open('config/orchestrator.yaml') as f:
        yaml.safe_load(f)
    print('YAML is valid')
except yaml.YAMLError as e:
    print(f'YAML error: {e}')
"
```

**Solutions**:
- Use proper YAML indentation (spaces, not tabs)
- Quote strings with special characters
- Check for missing colons or incorrect nesting

#### Environment Variable Substitution

**Problem**: Environment variables not being substituted

**Diagnosis**:
```bash
# Check environment variables
env | grep ORCHESTRATOR

# Test substitution
docker-compose config
```

**Solutions**:
```bash
# Ensure variables are exported
export ORCHESTRATOR_SECRET_KEY="your-secret-key"

# Use .env file
echo "ORCHESTRATOR_SECRET_KEY=your-secret-key" > .env
```

#### Service Definition Errors

**Problem**: Managed services won't start

**Diagnosis**:
```bash
# Check service configuration
curl http://localhost:8080/api/v1/services

# Check container status
docker ps -a --filter "label=io.homei.managed=true"
```

**Common Issues**:

1. **Image Not Found**:
   ```bash
   # Pull image manually
   docker pull postgres:15
   ```

2. **Volume Mount Errors**:
   ```bash
   # Check directory permissions
   ls -la /data/postgres
   
   # Create missing directories
   mkdir -p /data/postgres
   chown -R 999:999 /data/postgres  # PostgreSQL user
   ```

3. **Port Conflicts**:
   ```bash
   # Check for port conflicts
   sudo netstat -tulpn | grep :5432
   ```

### Performance Issues

#### High Memory Usage

**Problem**: Orchestrator consuming too much memory

**Diagnosis**:
```bash
# Check memory usage
docker stats

# Check Python memory usage
docker exec -it orchestrator ps aux
```

**Solutions**:

1. **Adjust Database Pool**:
   ```yaml
   database:
     pool_size: 5        # Reduce from 10
     max_overflow: 10    # Reduce from 20
   ```

2. **Limit Container Memory**:
   ```yaml
   services:
     orchestrator:
       mem_limit: 512m
   ```

#### Slow API Response

**Problem**: API endpoints are slow

**Diagnosis**:
```bash
# Test response times
time curl http://localhost:8080/health

# Check database performance
docker exec -it postgres psql -U homei -d homei -c "
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
"
```

**Solutions**:

1. **Database Optimization**:
   ```bash
   # Add database indexes
   # Optimize queries
   # Increase connection pool
   ```

2. **Redis Caching**:
   ```bash
   # Verify Redis is working
   docker exec -it redis redis-cli monitor
   ```

### RAUC Integration Issues

#### RAUC Installation Failed

**Problem**: RAUC not installing on Jetson Nano

**Solution**:
```bash
# Update package lists
sudo apt update

# Install dependencies
sudo apt install -y build-essential autotools-dev

# Install RAUC from source if package unavailable
wget https://github.com/rauc/rauc/releases/download/v1.10/rauc-1.10.tar.xz
tar xf rauc-1.10.tar.xz
cd rauc-1.10
./configure
make
sudo make install
```

#### U-Boot Configuration Issues

**Problem**: Dual boot not working

**Diagnosis**:
```bash
# Check U-Boot environment
sudo fw_printenv | grep BOOT

# Check partition layout
lsblk
sudo fdisk -l /dev/mmcblk0
```

**Solutions**:
```bash
# Reset U-Boot environment
sudo fw_setenv BOOT_ORDER "A B"
sudo fw_setenv BOOT_A_LEFT 3
sudo fw_setenv BOOT_B_LEFT 3
```

#### Bundle Installation Failed

**Problem**: RAUC bundle won't install

**Diagnosis**:
```bash
# Check bundle integrity
rauc info bundle.raucb

# Check RAUC status
rauc status

# Check RAUC logs
journalctl -u rauc
```

**Solutions**:

1. **Certificate Issues**:
   ```bash
   # Verify certificate
   openssl x509 -in /etc/rauc/ca.cert.pem -text -noout
   
   # Re-sign bundle
   rauc bundle --cert=/etc/rauc/ca.cert.pem --key=/etc/rauc/ca.key.pem bundle/ bundle.raucb
   ```

2. **Insufficient Space**:
   ```bash
   # Check disk space
   df -h
   
   # Clean up old bundles
   rm -f /tmp/*.raucb
   ```

### Network Issues

#### API Not Accessible

**Problem**: Can't access orchestrator API from other machines

**Diagnosis**:
```bash
# Check if service is listening
sudo netstat -tulpn | grep :8080

# Check firewall
sudo ufw status
```

**Solutions**:

1. **Firewall Configuration**:
   ```bash
   sudo ufw allow 8080/tcp
   sudo ufw allow 9090/tcp
   ```

2. **Network Binding**:
   ```yaml
   # Ensure binding to all interfaces
   api:
     host: "0.0.0.0"  # Not "127.0.0.1"
   ```

#### DNS Resolution Issues

**Problem**: Containers can't resolve service names

**Diagnosis**:
```bash
# Check Docker networks
docker network ls
docker network inspect homei_network

# Test DNS resolution
docker exec -it orchestrator nslookup postgres
```

**Solutions**:
```bash
# Recreate Docker network
docker network rm homei_network
docker network create homei_network

# Restart all services
docker-compose down
docker-compose up -d
```

### Log Analysis

#### Enable Debug Logging

```yaml
# In orchestrator.yaml
logging:
  level: "DEBUG"
  format: "structured"
```

#### Log Locations

```bash
# Application logs
docker-compose logs -f orchestrator

# System logs
journalctl -u homei-orchestrator

# Docker daemon logs
journalctl -u docker

# RAUC logs
journalctl -u rauc

# Database logs
docker-compose logs postgres

# Redis logs
docker-compose logs redis
```

#### Log Analysis Commands

```bash
# Filter error logs
docker-compose logs orchestrator | grep ERROR

# Follow logs in real-time
docker-compose logs -f --tail=100 orchestrator

# Search for specific patterns
journalctl -u homei-orchestrator | grep "database"

# Export logs for analysis
docker-compose logs orchestrator > orchestrator.log
```

## Diagnostic Scripts

### Health Check Script

Create `scripts/health-check.sh`:

```bash
#!/bin/bash

echo "=== Homei Orchestrator Health Check ==="

# Check Docker
echo "Checking Docker..."
if docker ps >/dev/null 2>&1; then
    echo "✓ Docker is running"
else
    echo "✗ Docker is not running"
    exit 1
fi

# Check containers
echo "Checking containers..."
CONTAINERS=("postgres" "redis" "orchestrator")
for container in "${CONTAINERS[@]}"; do
    if docker ps --filter "name=$container" --format "table {{.Names}}" | grep -q "$container"; then
        echo "✓ $container is running"
    else
        echo "✗ $container is not running"
    fi
done

# Check API
echo "Checking API..."
if curl -f http://localhost:8080/health >/dev/null 2>&1; then
    echo "✓ API is responding"
else
    echo "✗ API is not responding"
fi

# Check metrics
echo "Checking metrics..."
if curl -f http://localhost:9090/metrics >/dev/null 2>&1; then
    echo "✓ Metrics endpoint is responding"
else
    echo "✗ Metrics endpoint is not responding"
fi

echo "Health check complete."
```

### System Information Script

Create `scripts/system-info.sh`:

```bash
#!/bin/bash

echo "=== System Information ==="

# System details
echo "System: $(uname -a)"
echo "Distribution: $(lsb_release -d 2>/dev/null | cut -f2)"
echo "Uptime: $(uptime)"

# Docker info
echo -e "\n=== Docker Information ==="
echo "Docker version: $(docker --version)"
echo "Docker Compose version: $(docker-compose --version)"

# Container status
echo -e "\n=== Container Status ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Network info
echo -e "\n=== Network Information ==="
docker network ls

# Volume info
echo -e "\n=== Volume Information ==="
docker volume ls

# Disk usage
echo -e "\n=== Disk Usage ==="
df -h

# Memory usage
echo -e "\n=== Memory Usage ==="
free -h

# Process info
echo -e "\n=== Process Information ==="
ps aux | grep -E "(orchestrator|postgres|redis)" | grep -v grep
```

## Recovery Procedures

### Complete System Recovery

```bash
#!/bin/bash
# recovery.sh

echo "Starting recovery procedure..."

# Stop all services
docker-compose down

# Clean up containers and networks
docker system prune -f

# Recreate network
docker network create homei_network

# Restore configuration
cp config/orchestrator.yaml.template config/orchestrator.yaml

# Set environment variables
export ORCHESTRATOR_SECRET_KEY=$(openssl rand -hex 32)

# Restart services
docker-compose up -d

echo "Recovery complete. Check logs for any issues."
```

### Database Recovery

```bash
#!/bin/bash
# database-recovery.sh

echo "Recovering database..."

# Stop orchestrator
docker-compose stop orchestrator

# Backup current data
sudo cp -r /data/postgres /data/postgres.backup.$(date +%Y%m%d_%H%M%S)

# Reset database
docker-compose stop postgres
docker volume rm homei_orchestrator_postgres_data
docker-compose up -d postgres

# Wait for database
sleep 30

# Run migrations
docker-compose run --rm orchestrator python -m alembic upgrade head

# Restart orchestrator
docker-compose up -d orchestrator

echo "Database recovery complete."
```

## When to Seek Help

Contact support or file an issue when:

1. **Security concerns** (potential vulnerabilities)
2. **Data corruption** (database or file system issues)
3. **Hardware problems** (Jetson Nano specific issues)
4. **Persistent crashes** after following troubleshooting steps
5. **Performance degradation** that can't be resolved
6. **RAUC update failures** that prevent system boot

## Support Channels

- **Documentation**: Check all guides in `/docs`
- **Logs**: Always include relevant logs when reporting issues
- **System Info**: Provide output of `scripts/system-info.sh`
- **Reproduction Steps**: Detail exact steps to reproduce the issue
- **Environment**: Specify Jetson Nano model, JetPack version, etc.

Include this information when reporting issues:
```bash
# System information
./scripts/system-info.sh > system-info.txt

# Health check
./scripts/health-check.sh > health-check.txt

# Recent logs
docker-compose logs --tail=500 orchestrator > orchestrator.log
journalctl -u homei-orchestrator --since "1 hour ago" > systemd.log
```
