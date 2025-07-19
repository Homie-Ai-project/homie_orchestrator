#!/bin/bash

# Homei AI Stack Deployment Script
# This script deploys the homei_ai stack managed by the orchestrator

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HOMEI_AI_PATH="$PROJECT_ROOT/../homei_ai"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    
    # Check if homei_ai directory exists
    if [ ! -d "$HOMEI_AI_PATH" ]; then
        log_error "homei_ai directory not found at $HOMEI_AI_PATH"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Pull latest AI models
pull_ai_models() {
    log_info "Pulling AI models..."
    
    # Start ollama if not running
    docker compose up -d ollama
    
    # Wait for ollama to be ready
    log_info "Waiting for Ollama to be ready..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if docker exec homei_ollama ollama list &> /dev/null; then
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    
    if [ $timeout -le 0 ]; then
        log_warning "Ollama startup timeout. Models will need to be pulled manually."
        return
    fi
    
    # Pull default models
    log_info "Pulling default AI models..."
    docker exec homei_ollama ollama pull llama2:7b || log_warning "Failed to pull llama2:7b"
    docker exec homei_ollama ollama pull mistral:7b || log_warning "Failed to pull mistral:7b"
    docker exec homei_ollama ollama pull tinyllama || log_warning "Failed to pull tinyllama"
    
    log_success "AI models pulled successfully"
}

# Deploy the homei_ai stack
deploy_ai_stack() {
    log_info "Deploying homei_ai stack..."
    
    # Create necessary directories
    mkdir -p data/ai data/ollama data/open_webui
    
    # Deploy the stack
    if docker compose up -d; then
        log_success "homei_ai stack deployed successfully"
    else
        log_error "Failed to deploy homei_ai stack"
        exit 1
    fi
}

# Show service status
show_status() {
    log_info "Service Status:"
    echo ""
    docker compose ps
    echo ""
    
    log_info "Access Points:"
    echo "🌐 Open WebUI (Advanced): http://localhost:8080"
    echo "💬 React Chat (Simple):  http://localhost:3000"
    echo "🤖 Ollama API:           http://localhost:11434"
    echo "🎛️  Orchestrator:        http://localhost:8080/orchestrator"
    echo ""
}

# Main deployment function
main() {
    log_info "Starting homei_ai stack deployment..."
    echo ""
    
    cd "$PROJECT_ROOT"
    
    check_prerequisites
    deploy_ai_stack
    
    # Pull models in background to not block deployment
    log_info "Starting AI model download in background..."
    pull_ai_models &
    
    show_status
    
    log_success "Deployment complete!"
    log_info "Your private AI platform is now running securely on your hardware."
    log_info "No data is sent to external servers - everything runs locally."
    echo ""
    log_info "To stop the stack: docker compose down"
    log_info "To view logs: docker compose logs -f"
}

# Handle script arguments
case "${1:-}" in
    "stop")
        log_info "Stopping homei_ai stack..."
        docker compose down
        log_success "Stack stopped"
        ;;
    "restart")
        log_info "Restarting homei_ai stack..."
        docker compose down
        sleep 2
        main
        ;;
    "status")
        show_status
        ;;
    "models")
        pull_ai_models
        ;;
    *)
        main
        ;;
esac
