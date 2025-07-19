# Homie Orchestrator Documentation

Welcome to the Homie Orchestrator documentation. This system provides container orchestration and management capabilities, specifically designed for AI workloads and self-hosted services with focus on privacy, security, and unlimited local AI usage.

## Table of Contents

- [Installation Guide](installation.md) - Complete installation instructions
- [Quick Start Guide](quick-start.md) - Get up and running in 5 minutes
- [Jetson Nano Guide](jetson-nano-installation.md) - Jetson Nano specific installation
- [Configuration](configuration.md) - Configuration options and examples
- [API Reference](api.md) - REST API documentation
- [RAUC Integration](rauc-integration.md) - A/B update system setup
- [Development](development.md) - Development setup and contributing
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

## Quick Start

1. **Prerequisites**: Docker and Docker Compose installed
2. **Installation**: Run `curl -fsSL https://get.homieos.com/install.sh | bash`
3. **Access**: Visit `http://localhost:8080` for the dashboard
4. **Deploy AI**: Use the built-in homie_ai stack template
5. **Enjoy**: Private, secure, unlimited local AI

## Architecture Overview

The Homie Orchestrator consists of:

- **API Server**: FastAPI-based REST API (port 8080)
- **AI Services**: homie_ai stack with Ollama, Open WebUI, and React Chat
- **Container Manager**: Docker container lifecycle management
- **Backup Manager**: Automated backup and restore functionality
- **Health Monitor**: Service health monitoring and alerting
- **Scheduler**: Cron-like task scheduling

## Key Features

- ✅ AI-first container management (Ollama, GPT models, ML workloads)
- ✅ Service discovery and health monitoring
- ✅ Automated backups with retention policies
- ✅ RESTful API for remote management
- ✅ GPU support for AI inference
- ✅ Private and secure - no data leaves your hardware
- ✅ Configuration-driven service deployment
- ✅ Persistent data management

## Support

For issues and questions:
- Check the [Troubleshooting Guide](troubleshooting.md)
- Review the logs: `docker-compose logs -f orchestrator`
- File an issue in the project repository
