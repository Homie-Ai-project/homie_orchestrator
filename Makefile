# Makefile for Homei Orchestrator

.PHONY: help build start stop restart logs clean setup dev ai-deploy ai-stop ai-status

# Default target
help:
	@echo "Homei Orchestrator - AI-First Container Management System"
	@echo ""
	@echo "Available commands:"
	@echo "  setup      - Initial setup (create directories, networks)"
	@echo "  build      - Build the orchestrator Docker image"
	@echo "  start      - Start the orchestrator and all services"
	@echo "  stop       - Stop all services"
	@echo "  restart    - Restart all services"
	@echo "  logs       - Show orchestrator logs"
	@echo "  dev        - Start in development mode"
	@echo "  clean      - Clean up containers and volumes"
	@echo "  ai-deploy  - Deploy the homei_ai stack"
	@echo "  ai-stop    - Stop the homei_ai stack"
	@echo "  ai-status  - Show homei_ai stack status"
	@echo "  cli        - Run CLI commands (use ARGS='command')"

# Setup directories and Docker network
setup:
	@echo "Setting up Homei Orchestrator..."
	mkdir -p config data backups
	mkdir -p data/postgres data/redis data/ai data/ollama data/open_webui
	mkdir -p config/ai config/services
	docker network create homei_network 2>/dev/null || true
	@echo "Setup complete!"

# Build the orchestrator image
build:
	@echo "Building orchestrator image..."
	docker-compose build orchestrator

# Start all services
start: setup
	@echo "Starting Homei Orchestrator..."
	docker-compose up -d

# Stop all services
stop:
	@echo "Stopping Homei Orchestrator..."
	docker-compose down

# Restart all services
restart: stop start

# Deploy AI stack
ai-deploy:
	@echo "Deploying homei_ai stack..."
	./scripts/deploy-ai-stack.sh

# Stop AI stack
ai-stop:
	@echo "Stopping homei_ai stack..."
	./scripts/deploy-ai-stack.sh stop

# Show AI stack status
ai-status:
	@echo "homei_ai stack status:"
	./scripts/deploy-ai-stack.sh status

# Show orchestrator logs
logs:
	docker-compose logs -f orchestrator

# Development mode with live reload
dev: setup
	@echo "Starting in development mode..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Clean up everything
clean:
	@echo "Cleaning up..."
	docker-compose down -v
	docker system prune -f
	docker network rm homei_network 2>/dev/null || true

# CLI commands
cli:
	python cli.py $(ARGS)

# Quick status check
status:
	@echo "=== Orchestrator Status ==="
	@docker-compose ps
	@echo ""
	@echo "=== API Health Check ==="
	@curl -s http://localhost:8080/health | python -m json.tool 2>/dev/null || echo "API not responding"

# Show container information
containers:
	@echo "=== Managed Containers ==="
	@curl -s http://localhost:8080/api/v1/containers | python -m json.tool 2>/dev/null || echo "API not responding"

# Install Python dependencies for development
install-deps:
	pip install -r requirements.txt

# Run tests (placeholder)
test:
	@echo "Running tests..."
	# python -m pytest tests/

# Format code
format:
	black src/ cli.py
	isort src/ cli.py

# Lint code
lint:
	flake8 src/ cli.py
	pylint src/ cli.py

# Create a backup
backup:
	@echo "Creating backup..."
	@curl -X POST http://localhost:8080/api/v1/backup || echo "Backup failed"

# List available backups
list-backups:
	@echo "Available backups:"
	@curl -s http://localhost:8080/api/v1/backups | python -m json.tool 2>/dev/null || echo "API not responding"
