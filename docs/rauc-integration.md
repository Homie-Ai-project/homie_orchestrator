# RAUC Integration Guide

This guide explains how to integrate the Homie Orchestrator with RAUC (Robust Auto-Update Client) for reliable A/B system updates on Jetson Nano.

## Overview

RAUC provides atomic system updates using A/B partitioning. This ensures:
- **Rollback capability** if updates fail
- **Minimal downtime** during updates
- **Data persistence** across updates
- **Atomic updates** (all or nothing)

## Architecture

```
┌─────────────────────────────────────┐
│              Jetson Nano            │
│                                     │
│  ┌─────────────┐  ┌─────────────┐   │
│  │   Slot A    │  │   Slot B    │   │
│  │  (Active)   │  │ (Inactive)  │   │
│  │             │  │             │   │
│  │ Root FS     │  │ Root FS     │   │
│  │ Homie       │  │ Homie       │   │
│  │ Orchestrator│  │ Orchestrator│   │
│  └─────────────┘  └─────────────┘   │
│                                     │
│  ┌─────────────────────────────────┐ │
│  │        Data Partition           │ │
│  │     (Persistent across         │ │
│  │       updates)                 │ │
│  │                                │ │
│  │ - Database data                │ │
│  │ - Configuration files          │ │
│  │ - Application data             │ │
│  │ - User data                    │ │
│  └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

## Prerequisites

1. **Jetson Nano** with JetPack installed
2. **RAUC** installed (`sudo apt install rauc`)
3. **U-Boot** configured for dual boot
4. **Partitioned SD card** with A/B slots

## Partition Setup

### Partition Layout

```
/dev/mmcblk0p1 - Boot partition (shared)
/dev/mmcblk0p2 - Root FS Slot A (16GB)
/dev/mmcblk0p3 - Root FS Slot B (16GB)
/dev/mmcblk0p4 - Data partition (remaining space)
```

### Create Partitions

```bash
# Backup current system first!
sudo dd if=/dev/mmcblk0 of=/backup/jetson-backup.img bs=4M

# Create new partition table
sudo parted /dev/mmcblk0 mklabel gpt

# Create partitions
sudo parted /dev/mmcblk0 mkpart primary fat32 1MiB 512MiB    # Boot
sudo parted /dev/mmcblk0 mkpart primary ext4 512MiB 16.5GB  # Slot A
sudo parted /dev/mmcblk0 mkpart primary ext4 16.5GB 32.5GB  # Slot B
sudo parted /dev/mmcblk0 mkpart primary ext4 32.5GB 100%    # Data

# Format partitions
sudo mkfs.fat -F32 /dev/mmcblk0p1
sudo mkfs.ext4 /dev/mmcblk0p2
sudo mkfs.ext4 /dev/mmcblk0p3
sudo mkfs.ext4 /dev/mmcblk0p4

# Set partition labels
sudo e2label /dev/mmcblk0p2 "rootfs-a"
sudo e2label /dev/mmcblk0p3 "rootfs-b"
sudo e2label /dev/mmcblk0p4 "data"
```

## RAUC Configuration

### System Configuration

Create `/etc/rauc/system.conf`:

```ini
[system]
compatible=jetson-nano-homie
bootloader=uboot
bundle-formats=plain

[keyring]
path=/etc/rauc/ca.cert.pem
use-bundle-signing-time=true

[slot.rootfs.0]
device=/dev/mmcblk0p2
type=ext4
bootname=A

[slot.rootfs.1]
device=/dev/mmcblk0p3
type=ext4
bootname=B

[slot.data.0]
device=/dev/mmcblk0p4
type=ext4
readonly=false
```

### Certificate Management

```bash
# Generate CA certificate (development)
openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout /tmp/ca.key.pem \
    -out /tmp/ca.cert.pem \
    -days 7300 \
    -subj "/CN=Homie RAUC CA"

# Install certificate
sudo cp /tmp/ca.cert.pem /etc/rauc/
sudo chmod 644 /etc/rauc/ca.cert.pem

# Keep private key secure for signing bundles
sudo cp /tmp/ca.key.pem /etc/rauc/ca.key.pem
sudo chmod 600 /etc/rauc/ca.key.pem
sudo chown root:root /etc/rauc/ca.key.pem
```

## U-Boot Configuration

### Enable Dual Boot

Add to U-Boot environment:

```bash
# Create U-Boot script
cat > /tmp/boot.txt << 'EOF'
# RAUC boot script
if test "${BOOT_ORDER}" = "A B"; then
    if test "${BOOT_A_LEFT}" -gt 0; then
        setenv bootargs root=/dev/mmcblk0p2 rootfstype=ext4
        setexpr BOOT_A_LEFT ${BOOT_A_LEFT} - 1
    else
        setenv BOOT_ORDER "B A"
        setenv BOOT_B_LEFT 3
        setenv bootargs root=/dev/mmcblk0p3 rootfstype=ext4
    fi
else
    if test "${BOOT_B_LEFT}" -gt 0; then
        setenv bootargs root=/dev/mmcblk0p3 rootfstype=ext4
        setexpr BOOT_B_LEFT ${BOOT_B_LEFT} - 1
    else
        setenv BOOT_ORDER "A B"
        setenv BOOT_A_LEFT 3
        setenv bootargs root=/dev/mmcblk0p2 rootfstype=ext4
    fi
fi
saveenv
EOF

# Compile U-Boot script
mkimage -A arm64 -T script -C none -d /tmp/boot.txt /boot/boot.scr
```

### U-Boot Environment Variables

```bash
# Set initial boot configuration
sudo fw_setenv BOOT_ORDER "A B"
sudo fw_setenv BOOT_A_LEFT 3
sudo fw_setenv BOOT_B_LEFT 3
```

## Data Persistence Configuration

### Mount Data Partition

Add to `/etc/fstab`:

```
/dev/mmcblk0p4 /data ext4 defaults,noatime 0 2
```

### Create Data Structure

```bash
# Mount data partition
sudo mkdir -p /data
sudo mount /data

# Create directory structure
sudo mkdir -p /data/{postgres,redis,core,backups,config,logs}
sudo chown -R 1000:1000 /data
```

### Orchestrator Data Mapping

Update orchestrator configuration to use data partition:

```yaml
orchestrator:
  storage:
    data_path: "/data"
    config_path: "/data/config"
    backup_path: "/data/backups"

services:
  postgres:
    volumes:
      - "/data/postgres:/var/lib/postgresql/data"
  
  redis:
    volumes:
      - "/data/redis:/data"
  
  homie_core:
    volumes:
      - "/data/config/core:/config"
      - "/data/core:/data"
```

## Bundle Creation

### Bundle Structure

```
bundle/
├── manifest.raucm
├── rootfs.ext4
├── update-hooks/
│   ├── pre-install
│   ├── post-install
│   └── post-activate
└── bundle.conf
```

### Bundle Configuration

Create `bundle.conf`:

```ini
[update]
compatible=jetson-nano-homie
version=1.1.0
description=Homie Orchestrator Update v1.1.0
build=$(date +%Y%m%d%H%M%S)

[bundle]
format=plain

[image.rootfs]
filename=rootfs.ext4

[hooks]
filename=update-hooks
```

### Create Root Filesystem

```bash
#!/bin/bash
# create-rootfs.sh

# Create temporary directory
TEMP_DIR=$(mktemp -d)
ROOTFS_DIR="$TEMP_DIR/rootfs"
ROOTFS_IMAGE="rootfs.ext4"

# Create base root filesystem
sudo debootstrap --arch=arm64 focal "$ROOTFS_DIR" http://ports.ubuntu.com/ubuntu-ports

# Install required packages
sudo chroot "$ROOTFS_DIR" apt-get update
sudo chroot "$ROOTFS_DIR" apt-get install -y \
    docker.io \
    docker-compose \
    python3 \
    python3-pip \
    curl \
    wget \
    git

# Copy orchestrator code
sudo cp -r /opt/homie_orchestrator "$ROOTFS_DIR/opt/"

# Install Python dependencies
sudo chroot "$ROOTFS_DIR" pip3 install -r /opt/homie_orchestrator/requirements.txt

# Create systemd service
sudo cp /etc/systemd/system/homie-orchestrator.service \
    "$ROOTFS_DIR/etc/systemd/system/"

# Enable service
sudo chroot "$ROOTFS_DIR" systemctl enable homie-orchestrator

# Create filesystem image
sudo dd if=/dev/zero of="$ROOTFS_IMAGE" bs=1M count=4096
sudo mkfs.ext4 "$ROOTFS_IMAGE"

# Mount and copy files
MOUNT_DIR=$(mktemp -d)
sudo mount -o loop "$ROOTFS_IMAGE" "$MOUNT_DIR"
sudo cp -a "$ROOTFS_DIR/"* "$MOUNT_DIR/"
sudo umount "$MOUNT_DIR"

# Cleanup
sudo rm -rf "$TEMP_DIR" "$MOUNT_DIR"

echo "Root filesystem created: $ROOTFS_IMAGE"
```

### Update Hooks

#### Pre-Install Hook

```bash
#!/bin/bash
# update-hooks/pre-install

case "$1" in
    slot-pre-install)
        echo "Preparing for update..."
        
        # Stop orchestrator service
        systemctl stop homie-orchestrator || true
        
        # Create backup
        mkdir -p /data/backups/pre-update
        cp -r /data/config /data/backups/pre-update/
        
        # Save current version info
        echo "$(date): Pre-update backup created" >> /data/logs/update.log
        ;;
esac
```

#### Post-Install Hook

```bash
#!/bin/bash
# update-hooks/post-install

case "$1" in
    slot-post-install)
        echo "Post-install configuration..."
        
        # Update Docker images
        cd /opt/homie_orchestrator
        docker-compose pull
        
        # Run database migrations if needed
        docker-compose run --rm orchestrator python -m alembic upgrade head
        
        echo "$(date): Post-install completed" >> /data/logs/update.log
        ;;
esac
```

#### Post-Activate Hook

```bash
#!/bin/bash
# update-hooks/post-activate

case "$1" in
    slot-post-activate)
        echo "Activating new system..."
        
        # Start orchestrator service
        systemctl start homie-orchestrator
        
        # Wait for service to be ready
        sleep 30
        
        # Health check
        if curl -f http://localhost:8080/health; then
            echo "$(date): Update successful, service healthy" >> /data/logs/update.log
        else
            echo "$(date): Update failed, service unhealthy" >> /data/logs/update.log
            exit 1
        fi
        ;;
esac
```

### Create Bundle

```bash
#!/bin/bash
# create-bundle.sh

BUNDLE_DIR="bundle"
BUNDLE_NAME="homie-orchestrator-v1.1.0.raucb"

# Create bundle directory
mkdir -p "$BUNDLE_DIR/update-hooks"

# Copy files
cp bundle.conf "$BUNDLE_DIR/"
cp rootfs.ext4 "$BUNDLE_DIR/"
cp update-hooks/* "$BUNDLE_DIR/update-hooks/"

# Make hooks executable
chmod +x "$BUNDLE_DIR/update-hooks/"*

# Create RAUC bundle
rauc bundle --cert=/etc/rauc/ca.cert.pem --key=/etc/rauc/ca.key.pem \
    "$BUNDLE_DIR" "$BUNDLE_NAME"

echo "Bundle created: $BUNDLE_NAME"
```

## Update Process

### Manual Update

```bash
# Install update bundle
sudo rauc install homie-orchestrator-v1.1.0.raucb

# Check status
rauc status

# Reboot to activate
sudo reboot
```

### Automated Update

Create update service:

```bash
# Create update script
cat > /opt/homie_orchestrator/scripts/update.sh << 'EOF'
#!/bin/bash

UPDATE_URL="${1:-http://updates.homie.local/latest.raucb}"
TEMP_BUNDLE="/tmp/update.raucb"

# Download update bundle
curl -o "$TEMP_BUNDLE" "$UPDATE_URL"

# Verify bundle
if rauc info "$TEMP_BUNDLE"; then
    echo "Bundle verified, installing..."
    rauc install "$TEMP_BUNDLE"
    
    # Schedule reboot
    echo "Update installed, rebooting in 1 minute..."
    shutdown -r +1 "System update installed, rebooting..."
else
    echo "Bundle verification failed"
    exit 1
fi
EOF

chmod +x /opt/homie_orchestrator/scripts/update.sh
```

### Orchestrator API Integration

Add update endpoint to orchestrator:

```python
# src/orchestrator/api/update.py

from fastapi import APIRouter, HTTPException
import subprocess
import os

router = APIRouter()

@router.post("/install")
async def install_update(bundle_path: str):
    """Install RAUC update bundle."""
    try:
        # Verify bundle exists
        if not os.path.exists(bundle_path):
            raise HTTPException(status_code=404, detail="Bundle not found")
        
        # Install bundle
        result = subprocess.run(
            ["rauc", "install", bundle_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return {"status": "success", "message": "Update installed"}
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Update failed: {result.stderr}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def update_status():
    """Get RAUC system status."""
    try:
        result = subprocess.run(
            ["rauc", "status", "--output-format=json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            import json
            return json.loads(result.stdout)
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Status check failed: {result.stderr}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Rollback Procedures

### Automatic Rollback

RAUC automatically rolls back if:
- System fails to boot 3 times
- Health check fails after update
- Update hooks fail

### Manual Rollback

```bash
# Check current status
rauc status

# Mark current slot as bad (triggers rollback on next boot)
rauc status mark-bad

# Or switch to other slot immediately
rauc status mark-active other

# Reboot to activate rollback
sudo reboot
```

## Monitoring and Logging

### Update Logs

```bash
# View RAUC logs
journalctl -u rauc

# View update logs
tail -f /data/logs/update.log

# View orchestrator logs
docker-compose logs -f orchestrator
```

### Health Monitoring

```bash
# Add health check to orchestrator
curl http://localhost:8080/api/v1/update/status

# Monitor system health
curl http://localhost:8080/health
```

## Troubleshooting

### Common Issues

1. **Boot loop**: Check U-Boot environment variables
2. **Mount failures**: Verify fstab and partition labels
3. **Bundle signature errors**: Check certificates
4. **Rollback issues**: Verify slot configurations

### Recovery Procedures

```bash
# Emergency recovery (from working slot)
sudo mount /dev/mmcblk0p2 /mnt  # or p3 for other slot
sudo chroot /mnt

# Restore from backup
sudo cp -r /data/backups/pre-update/config/* /data/config/

# Reset RAUC state
sudo rauc status mark-good
```

## Best Practices

1. **Always test updates** in development first
2. **Create backups** before updates
3. **Monitor health checks** after updates
4. **Keep data partition separate** from OS
5. **Use signed bundles** in production
6. **Test rollback procedures** regularly
7. **Monitor disk space** for bundle storage

## Security Considerations

1. **Sign all bundles** with proper certificates
2. **Verify bundle integrity** before installation
3. **Secure bundle distribution** (HTTPS, authentication)
4. **Rotate signing certificates** regularly
5. **Monitor update logs** for anomalies
6. **Implement update windows** for controlled deployments

For more information, see the [RAUC documentation](https://rauc.readthedocs.io/) and [Troubleshooting Guide](troubleshooting.md).
