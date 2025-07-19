# Installation Guide - Jetson Nano with RAUC

This guide covers the complete installation of Homei Orchestrator on a Jetson Nano device with RAUC (Robust Auto-Update Client) for A/B system updates.

## Prerequisites

### Hardware Requirements
- **NVIDIA Jetson Nano** (4GB recommended)
- **SD Card**: 64GB+ (Class 10 or better)
- **Network**: Ethernet or WiFi connectivity

### Software Requirements
- **JetPack 4.6.x** or later
- **Ubuntu 18.04/20.04** (included with JetPack)
- **Docker** 20.10+
- **RAUC** for A/B updates

## Step 1: Prepare Jetson Nano

### 1.1 Flash JetPack
```bash
# Download JetPack SDK Manager or use pre-built image
# Flash to SD card using balenaEtcher or dd command
sudo dd if=jetpack-image.img of=/dev/sdX bs=4M status=progress
sync
```

### 1.2 Initial Setup
```bash
# Boot Jetson Nano and complete initial setup
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget git vim htop
```

## Step 2: Install Docker

### 2.1 Docker Installation
```bash
# Remove old Docker versions
sudo apt remove docker docker-engine docker.io containerd runc

# Install Docker using convenience script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Enable Docker service
sudo systemctl enable docker
sudo systemctl start docker

# Verify installation
docker --version
docker run hello-world
```

### 2.2 Docker Compose Installation
```bash
# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

## Step 3: Install RAUC

### 3.1 RAUC Installation
```bash
# Install RAUC for A/B updates
sudo apt update
sudo apt install -y rauc

# Verify installation
rauc --version
```

### 3.2 Configure RAUC
```bash
# Create RAUC system configuration
sudo mkdir -p /etc/rauc

# Create system.conf
sudo tee /etc/rauc/system.conf << 'EOF'
[system]
compatible=jetson-nano-homei
bootloader=uboot

[keyring]
path=/etc/rauc/ca.cert.pem

[slot.rootfs.0]
device=/dev/mmcblk0p1
type=ext4
bootname=A

[slot.rootfs.1]
device=/dev/mmcblk0p2
type=ext4
bootname=B
EOF

# Generate RAUC certificates (for development)
openssl req -x509 -newkey rsa:4096 -nodes -keyout /tmp/private-key.pem -out /tmp/ca.cert.pem -days 7300 -subj "/CN=Homei Development CA"
sudo cp /tmp/ca.cert.pem /etc/rauc/
```

## Step 4: Partition Setup for A/B Updates

### 4.1 Create A/B Partitions
```bash
# Warning: This will modify your SD card partitions
# Backup your data before proceeding

# Resize existing partition and create A/B slots
sudo parted /dev/mmcblk0 resizepart 1 16GB
sudo parted /dev/mmcblk0 mkpart primary ext4 16GB 32GB

# Format new partition
sudo mkfs.ext4 /dev/mmcblk0p2

# Create data partition (survives updates)
sudo parted /dev/mmcblk0 mkpart primary ext4 32GB 100%
sudo mkfs.ext4 /dev/mmcblk0p3

# Create mount points
sudo mkdir -p /data /config /backups
```

### 4.2 Configure fstab
```bash
# Add persistent data partition to fstab
echo "/dev/mmcblk0p3 /data ext4 defaults 0 2" | sudo tee -a /etc/fstab

# Mount data partition
sudo mount -a
```

## Step 5: Install Homei Orchestrator

### 5.1 Clone Repository
```bash
# Clone the orchestrator repository
cd /opt
sudo git clone https://github.com/your-org/homei_orchestrator.git
cd homei_orchestrator

# Set permissions
sudo chown -R $USER:$USER /opt/homei_orchestrator
```

### 5.2 Create Directory Structure
```bash
# Create necessary directories
sudo mkdir -p /data/{postgres,redis,core,backups}
sudo mkdir -p /config/core
sudo chown -R $USER:$USER /data /config

# Create Docker network
docker network create homei_network || true
```

### 5.3 Configure Environment
```bash
# Copy configuration template
cp config/orchestrator.yaml.template config/orchestrator.yaml

# Generate secret key
export ORCHESTRATOR_SECRET_KEY=$(openssl rand -hex 32)
echo "export ORCHESTRATOR_SECRET_KEY=$ORCHESTRATOR_SECRET_KEY" >> ~/.bashrc

# Create environment file
cat > .env << EOF
ORCHESTRATOR_SECRET_KEY=$ORCHESTRATOR_SECRET_KEY
ORCHESTRATOR_CONFIG=/config/orchestrator.yaml
POSTGRES_DB=homei
POSTGRES_USER=homei
POSTGRES_PASSWORD=homei_password
PYTHONPATH=/app
EOF
```

### 5.4 Build and Start Services
```bash
# Build the orchestrator image
docker-compose build

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

## Step 6: Verify Installation

### 6.1 Health Checks
```bash
# Check orchestrator health
curl http://localhost:8080/health

# Check metrics endpoint
curl http://localhost:9090/metrics

# Check container status
docker ps

# Check logs
docker-compose logs -f orchestrator
```

### 6.2 API Testing
```bash
# Test API endpoints
curl -X GET http://localhost:8080/api/v1/services
curl -X GET http://localhost:8080/api/v1/containers

# Expected response: JSON with service/container information
```

## Step 7: Configure Auto-Start

### 7.1 Create Systemd Service
```bash
# Create systemd service for auto-start
sudo tee /etc/systemd/system/homei-orchestrator.service << 'EOF'
[Unit]
Description=Homei Orchestrator
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/homei_orchestrator
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=300
User=homei
Group=homei

[Install]
WantedBy=multi-user.target
EOF

# Create homei user if it doesn't exist
sudo useradd -r -s /bin/false homei || true
sudo usermod -aG docker homei

# Set ownership
sudo chown -R homei:homei /opt/homei_orchestrator /data /config

# Enable and start service
sudo systemctl enable homei-orchestrator.service
sudo systemctl start homei-orchestrator.service

# Check status
sudo systemctl status homei-orchestrator.service
```

## Step 8: Configure Firewall (Optional)

### 8.1 UFW Configuration
```bash
# Install and configure UFW
sudo apt install -y ufw

# Allow SSH
sudo ufw allow ssh

# Allow orchestrator ports
sudo ufw allow 8080/tcp comment 'Homei Orchestrator API'
sudo ufw allow 9090/tcp comment 'Homei Orchestrator Metrics'

# Allow core service port
sudo ufw allow 8123/tcp comment 'Homei Core Service'

# Enable firewall
sudo ufw --force enable

# Check status
sudo ufw status
```

## Step 9: RAUC Update Configuration

### 9.1 Create Update Bundle Structure
```bash
# Create RAUC bundle configuration
sudo mkdir -p /opt/rauc-bundles

cat > /opt/rauc-bundles/bundle.conf << 'EOF'
[update]
compatible=jetson-nano-homei
version=1.0.0

[bundle]
format=verity

[image.rootfs]
filename=homei-orchestrator.ext4

[hooks]
filename=update-hook.sh
EOF
```

### 9.2 Create Update Script
```bash
# Create update hook script
cat > /opt/rauc-bundles/update-hook.sh << 'EOF'
#!/bin/bash

case "$1" in
    slot-post-install)
        # Update orchestrator after slot installation
        cd /opt/homei_orchestrator
        docker-compose pull
        docker-compose up -d
        ;;
esac
EOF

chmod +x /opt/rauc-bundles/update-hook.sh
```

## Step 10: Monitoring and Maintenance

### 10.1 Log Management
```bash
# Configure log rotation
sudo tee /etc/logrotate.d/homei-orchestrator << 'EOF'
/data/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    copytruncate
}
EOF
```

### 10.2 Backup Verification
```bash
# Check backup configuration
curl http://localhost:8080/api/v1/backup/status

# List backups
ls -la /data/backups/
```

## Troubleshooting

### Common Issues

1. **Docker permission denied**:
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

2. **Port conflicts**:
   ```bash
   sudo netstat -tulpn | grep :8080
   sudo lsof -i :8080
   ```

3. **Database connection issues**:
   ```bash
   docker-compose logs postgres
   docker exec -it postgres psql -U homei -d homei
   ```

4. **RAUC installation fails**:
   ```bash
   sudo apt update
   sudo apt install -y rauc
   ```

### Log Locations
- **Orchestrator logs**: `docker-compose logs orchestrator`
- **System logs**: `/var/log/syslog`
- **Docker logs**: `journalctl -u docker`
- **Service logs**: `journalctl -u homei-orchestrator`

## Next Steps

1. Review the [Configuration Guide](configuration.md) for advanced settings
2. Set up monitoring and alerting
3. Configure backup schedules
4. Test RAUC update process
5. Set up remote access and security

## Security Considerations

1. **Change default passwords** in configuration
2. **Generate strong secret keys**
3. **Configure firewall rules**
4. **Enable SSL/TLS** for production
5. **Regular security updates**
6. **Monitor access logs**

For additional help, see the [Troubleshooting Guide](troubleshooting.md) or check the project documentation.
