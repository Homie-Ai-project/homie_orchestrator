#!/bin/bash

# Homei Orchestrator Installation Script for Jetson Nano
# This script automates the installation process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ORCHESTRATOR_DIR="/opt/homei_orchestrator"
DATA_DIR="/data"
CONFIG_DIR="/config"
BACKUP_DIR="/backups"
SERVICE_USER="homei"

# Functions
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "Please run this script as root (use sudo)"
    fi
}

check_system() {
    log "Checking system requirements..."
    
    # Check if running on ARM64 (Jetson Nano)
    if [ "$(uname -m)" != "aarch64" ]; then
        warn "This script is designed for ARM64 architecture (Jetson Nano)"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Check available disk space (minimum 8GB)
    AVAILABLE_SPACE=$(df / | awk 'NR==2{print int($4/1024/1024)}')
    if [ "$AVAILABLE_SPACE" -lt 8 ]; then
        error "Insufficient disk space. Need at least 8GB, available: ${AVAILABLE_SPACE}GB"
    fi
    
    success "System requirements check passed"
}

install_dependencies() {
    log "Installing system dependencies..."
    
    apt update
    apt install -y \
        curl \
        wget \
        git \
        vim \
        htop \
        unzip \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release
    
    success "System dependencies installed"
}

install_docker() {
    log "Installing Docker..."
    
    # Remove old Docker versions
    apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Install Docker using convenience script
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    
    # Install Docker Compose
    curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    
    # Start and enable Docker
    systemctl enable docker
    systemctl start docker
    
    success "Docker and Docker Compose installed"
}

install_rauc() {
    log "Installing RAUC..."
    
    # Try package manager first
    if apt install -y rauc 2>/dev/null; then
        success "RAUC installed from package manager"
    else
        warn "RAUC not available in package manager, skipping"
        warn "You may need to install RAUC manually for A/B updates"
    fi
}

create_user() {
    log "Creating service user..."
    
    # Create homei user if it doesn't exist
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -r -s /bin/bash -m "$SERVICE_USER"
        usermod -aG docker "$SERVICE_USER"
        success "User $SERVICE_USER created"
    else
        log "User $SERVICE_USER already exists"
        usermod -aG docker "$SERVICE_USER"
    fi
}

create_directories() {
    log "Creating directory structure..."
    
    # Create main directories
    mkdir -p "$DATA_DIR"/{postgres,redis,core,backups,logs}
    mkdir -p "$CONFIG_DIR"/core
    mkdir -p "$BACKUP_DIR"
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$DATA_DIR" "$CONFIG_DIR" "$BACKUP_DIR"
    
    success "Directory structure created"
}

install_orchestrator() {
    log "Installing Homei Orchestrator..."
    
    # Clone or copy orchestrator code
    if [ -d "$ORCHESTRATOR_DIR" ]; then
        warn "Orchestrator directory already exists, backing up..."
        mv "$ORCHESTRATOR_DIR" "${ORCHESTRATOR_DIR}.backup.$(date +%Y%m%d%H%M%S)"
    fi
    
    mkdir -p "$ORCHESTRATOR_DIR"
    
    # If running from the orchestrator directory, copy files
    if [ -f "$(dirname "$0")/../src/orchestrator/main.py" ]; then
        log "Copying orchestrator files..."
        cp -r "$(dirname "$0")/.." "$ORCHESTRATOR_DIR"
    else
        error "Orchestrator source files not found. Please run this script from the orchestrator directory."
    fi
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$ORCHESTRATOR_DIR"
    
    success "Orchestrator files installed"
}

configure_orchestrator() {
    log "Configuring orchestrator..."
    
    # Copy configuration template
    if [ -f "$ORCHESTRATOR_DIR/config/orchestrator.yaml.template" ]; then
        cp "$ORCHESTRATOR_DIR/config/orchestrator.yaml.template" "$CONFIG_DIR/orchestrator.yaml"
    fi
    
    # Generate secret key
    SECRET_KEY=$(openssl rand -hex 32)
    
    # Create environment file
    cat > "$ORCHESTRATOR_DIR/.env" << EOF
ORCHESTRATOR_SECRET_KEY=$SECRET_KEY
ORCHESTRATOR_CONFIG=$CONFIG_DIR/orchestrator.yaml
POSTGRES_DB=homei
POSTGRES_USER=homei
POSTGRES_PASSWORD=$(openssl rand -hex 16)
PYTHONPATH=$ORCHESTRATOR_DIR
EOF
    
    # Set permissions
    chmod 600 "$ORCHESTRATOR_DIR/.env"
    chown "$SERVICE_USER:$SERVICE_USER" "$ORCHESTRATOR_DIR/.env"
    chown "$SERVICE_USER:$SERVICE_USER" "$CONFIG_DIR/orchestrator.yaml"
    
    success "Orchestrator configured"
}

setup_docker_network() {
    log "Setting up Docker network..."
    
    # Create Docker network
    docker network create homei_network 2>/dev/null || true
    
    success "Docker network configured"
}

create_systemd_service() {
    log "Creating systemd service..."
    
    cat > /etc/systemd/system/homei-orchestrator.service << EOF
[Unit]
Description=Homei Orchestrator
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$ORCHESTRATOR_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=300
User=$SERVICE_USER
Group=$SERVICE_USER
EnvironmentFile=$ORCHESTRATOR_DIR/.env

[Install]
WantedBy=multi-user.target
EOF
    
    # Enable service
    systemctl daemon-reload
    systemctl enable homei-orchestrator.service
    
    success "Systemd service created and enabled"
}

setup_firewall() {
    log "Configuring firewall..."
    
    if command -v ufw >/dev/null 2>&1; then
        # Allow SSH
        ufw allow ssh
        
        # Allow orchestrator ports
        ufw allow 8080/tcp comment 'Homei Orchestrator API'
        ufw allow 9090/tcp comment 'Homei Orchestrator Metrics'
        ufw allow 8123/tcp comment 'Homei Core Service'
        
        # Enable firewall if not already enabled
        ufw --force enable
        
        success "Firewall configured"
    else
        warn "UFW not installed, skipping firewall configuration"
    fi
}

start_services() {
    log "Starting services..."
    
    cd "$ORCHESTRATOR_DIR"
    
    # Build orchestrator image
    sudo -u "$SERVICE_USER" docker-compose build
    
    # Start services
    sudo -u "$SERVICE_USER" docker-compose up -d
    
    # Wait for services to start
    sleep 30
    
    # Check if services are running
    if sudo -u "$SERVICE_USER" docker-compose ps | grep -q "Up"; then
        success "Services started successfully"
    else
        error "Failed to start services. Check logs: docker-compose logs"
    fi
}

verify_installation() {
    log "Verifying installation..."
    
    # Check if API is responding
    local retries=0
    local max_retries=10
    
    while [ $retries -lt $max_retries ]; do
        if curl -s http://localhost:8080/health >/dev/null 2>&1; then
            success "API is responding"
            break
        else
            log "Waiting for API to start... ($((retries + 1))/$max_retries)"
            sleep 10
            retries=$((retries + 1))
        fi
    done
    
    if [ $retries -eq $max_retries ]; then
        error "API is not responding after $max_retries attempts"
    fi
    
    # Show API response
    API_RESPONSE=$(curl -s http://localhost:8080/health)
    log "API Response: $API_RESPONSE"
    
    success "Installation verification completed"
}

print_summary() {
    echo
    echo "================================================================"
    echo -e "${GREEN}Homei Orchestrator Installation Complete!${NC}"
    echo "================================================================"
    echo
    echo "Services:"
    echo "  API Server:    http://localhost:8080"
    echo "  API Docs:      http://localhost:8080/docs"
    echo "  Metrics:       http://localhost:9090/metrics"
    echo "  Health Check:  http://localhost:8080/health"
    echo
    echo "Directories:"
    echo "  Installation:  $ORCHESTRATOR_DIR"
    echo "  Data:          $DATA_DIR"
    echo "  Configuration: $CONFIG_DIR"
    echo "  Backups:       $BACKUP_DIR"
    echo
    echo "Management Commands:"
    echo "  Start:         sudo systemctl start homei-orchestrator"
    echo "  Stop:          sudo systemctl stop homei-orchestrator"
    echo "  Status:        sudo systemctl status homei-orchestrator"
    echo "  Logs:          cd $ORCHESTRATOR_DIR && docker-compose logs -f"
    echo "  Health Check:  $ORCHESTRATOR_DIR/scripts/health-check.sh"
    echo
    echo "Configuration:"
    echo "  Main config:   $CONFIG_DIR/orchestrator.yaml"
    echo "  Environment:   $ORCHESTRATOR_DIR/.env"
    echo
    echo "Next Steps:"
    echo "  1. Review and customize configuration in $CONFIG_DIR/orchestrator.yaml"
    echo "  2. Configure managed services in the configuration file"
    echo "  3. Set up backup schedules"
    echo "  4. Configure RAUC for A/B updates (if needed)"
    echo "  5. Set up monitoring and alerting"
    echo
    echo "For troubleshooting, see: $ORCHESTRATOR_DIR/docs/troubleshooting.md"
    echo "================================================================"
}

# Main installation process
main() {
    echo "================================================================"
    echo "Homei Orchestrator Installation Script"
    echo "================================================================"
    echo
    
    check_root
    check_system
    
    log "Starting installation..."
    
    install_dependencies
    install_docker
    install_rauc
    create_user
    create_directories
    install_orchestrator
    configure_orchestrator
    setup_docker_network
    create_systemd_service
    setup_firewall
    start_services
    verify_installation
    
    print_summary
}

# Run main function
main "$@"
