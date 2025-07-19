# Development Guide

This guide covers setting up a development environment for the Homie Orchestrator project.

## Prerequisites

### Development Tools
- **Python 3.11+**
- **Docker** and **Docker Compose**
- **Git**
- **Code Editor** (VS Code recommended)

### Optional Tools
- **pytest** for testing
- **black** for code formatting
- **flake8** for linting
- **mypy** for type checking

## Setup Development Environment

### 1. Clone Repository

```bash
git clone https://github.com/your-org/homie_orchestrator.git
cd homie_orchestrator
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Dependencies

```bash
# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Or install in development mode
pip install -e .
```

### 4. Setup Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run on all files (optional)
pre-commit run --all-files
```

## Development Dependencies

Create `requirements-dev.txt`:

```txt
# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.25.2

# Code Quality
black==23.11.0
flake8==6.1.0
isort==5.12.0
mypy==1.7.1

# Development Tools
pre-commit==3.5.0
ipython==8.17.2
ipdb==0.13.13

# Documentation
mkdocs==1.5.3
mkdocs-material==9.4.8
```

## Project Structure

```
homie_orchestrator/
├── src/orchestrator/           # Main application code
│   ├── __init__.py
│   ├── main.py                # Application entry point
│   ├── config.py              # Configuration management
│   ├── metrics.py             # Prometheus metrics
│   ├── api/                   # FastAPI routes
│   │   ├── __init__.py
│   │   ├── router.py          # Main API router
│   │   ├── dependencies.py    # API dependencies
│   │   └── models.py          # Pydantic models
│   └── core/                  # Core business logic
│       ├── __init__.py
│       ├── container_manager.py
│       ├── backup_manager.py
│       ├── health_monitor.py
│       ├── scheduler.py
│       └── database.py
├── tests/                     # Test files
├── config/                    # Configuration templates
├── docs/                      # Documentation
├── docker/                    # Docker-related files
├── scripts/                   # Utility scripts
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
├── requirements.txt
├── requirements-dev.txt
├── Makefile
├── .gitignore
├── .pre-commit-config.yaml
└── README.md
```

## Running in Development Mode

### 1. Start Dependencies

```bash
# Start PostgreSQL and Redis
docker-compose -f docker-compose.dev.yml up -d postgres redis

# Wait for services to be ready
sleep 10
```

### 2. Setup Database

```bash
# Run database migrations
python -c "
from src.orchestrator.database import create_tables
import asyncio
asyncio.run(create_tables())
"
```

### 3. Run Application

```bash
# Set environment variables
export ORCHESTRATOR_SECRET_KEY="dev-secret-key-not-for-production"
export ORCHESTRATOR_CONFIG="config/orchestrator.yaml"
export PYTHONPATH="$(pwd)"

# Run with auto-reload
python -m src.orchestrator.main

# Or using uvicorn directly
uvicorn src.orchestrator.main:app --reload --host 0.0.0.0 --port 8080
```

### 4. Access Application

- **API**: http://localhost:8080
- **Health Check**: http://localhost:8080/health
- **Metrics**: http://localhost:9090/metrics
- **API Docs**: http://localhost:8080/docs

## Development Configuration

Create `config/orchestrator.dev.yaml`:

```yaml
orchestrator:
  name: "Homie Orchestrator Dev"
  version: "1.0.0-dev"
  
  api:
    host: "0.0.0.0"
    port: 8080
    cors_origins:
      - "*"  # Allow all origins in development
  
  security:
    secret_key: "dev-secret-key-not-for-production"
    access_token_expire_minutes: 1440  # 24 hours for development
  
  database:
    url: "postgresql+asyncpg://homie:homie_password@localhost:5432/homie"
    
  redis:
    url: "redis://localhost:6379/0"
    
  logging:
    level: "DEBUG"
    format: "plain"
    
  monitoring:
    enabled: true
    metrics_port: 9090
    health_check_interval: 10  # Faster checks in dev
    
  backup:
    enabled: false  # Disable backups in development

services: {}  # No managed services in development
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/orchestrator

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest -v

# Run and watch for changes
pytest --watch
```

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest configuration and fixtures
├── test_api/
│   ├── __init__.py
│   ├── test_health.py
│   ├── test_services.py
│   └── test_containers.py
├── test_core/
│   ├── __init__.py
│   ├── test_container_manager.py
│   ├── test_backup_manager.py
│   └── test_health_monitor.py
└── test_config.py
```

### Example Test

```python
# tests/test_api/test_health.py

import pytest
from fastapi.testclient import TestClient
from src.orchestrator.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_readiness_check(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_liveness_check(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
```

### Test Configuration

Create `tests/conftest.py`:

```python
import pytest
import asyncio
from unittest.mock import Mock
from fastapi.testclient import TestClient
from src.orchestrator.main import create_app
from src.orchestrator.config import Settings, OrchestratorConfig


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return Settings(
        orchestrator=OrchestratorConfig(
            security={"secret_key": "test-secret-key"},
            database={"url": "sqlite:///test.db"},
            redis={"url": "redis://localhost:6379/1"}
        )
    )


@pytest.fixture
def app(mock_settings):
    """Create test app."""
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: mock_settings
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

## Code Quality

### Formatting

```bash
# Format code with black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Check formatting
black --check src/ tests/
isort --check src/ tests/
```

### Linting

```bash
# Run flake8
flake8 src/ tests/

# Run mypy for type checking
mypy src/
```

### Pre-commit Configuration

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-toml

  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        additional_dependencies:
          - flake8-docstrings
          - flake8-bugbear

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, fastapi]
```

## Debugging

### Using Debugger

```python
# Add breakpoint in code
import ipdb; ipdb.set_trace()

# Or use built-in breakpoint (Python 3.7+)
breakpoint()
```

### Debug Configuration for VS Code

Create `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Orchestrator",
            "type": "python",
            "request": "launch",
            "module": "src.orchestrator.main",
            "console": "integratedTerminal",
            "env": {
                "ORCHESTRATOR_SECRET_KEY": "dev-secret-key",
                "ORCHESTRATOR_CONFIG": "config/orchestrator.dev.yaml",
                "PYTHONPATH": "${workspaceFolder}"
            }
        },
        {
            "name": "Debug Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["tests/", "-v"],
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
```

## Docker Development

### Development Dockerfile

Create `Dockerfile.dev`:

```dockerfile
FROM python:3.11-slim

# Install development tools
RUN apt-get update && apt-get install -y \
    curl \
    docker.io \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt -r requirements-dev.txt

# Copy source code
COPY . .

# Development user
RUN useradd -m -u 1000 dev && \
    chown -R dev:dev /app
USER dev

# Expose ports
EXPOSE 8080 9090

# Development command
CMD ["python", "-m", "src.orchestrator.main"]
```

### Development Compose Override

Create `docker-compose.override.yml`:

```yaml
version: '3.8'

services:
  orchestrator:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - .:/app
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - ORCHESTRATOR_SECRET_KEY=dev-secret-key
      - ORCHESTRATOR_CONFIG=/app/config/orchestrator.dev.yaml
      - PYTHONPATH=/app
    command: ["python", "-m", "src.orchestrator.main"]
    
  postgres:
    environment:
      - POSTGRES_PASSWORD=dev_password
    ports:
      - "5432:5432"
      
  redis:
    ports:
      - "6379:6379"
```

## API Development

### Testing API Endpoints

```bash
# Health check
curl http://localhost:8080/health

# Get services
curl http://localhost:8080/api/v1/services

# Create service
curl -X POST http://localhost:8080/api/v1/services \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-service",
    "image": "nginx:alpine",
    "enabled": true
  }'
```

### API Documentation

The API documentation is automatically generated and available at:
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
- **OpenAPI JSON**: http://localhost:8080/openapi.json

## Performance Testing

### Load Testing with Locust

Create `tests/load_test.py`:

```python
from locust import HttpUser, task, between


class OrchestratorUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def health_check(self):
        self.client.get("/health")
    
    @task(2)
    def get_services(self):
        self.client.get("/api/v1/services")
    
    @task(1)
    def get_containers(self):
        self.client.get("/api/v1/containers")
```

Run load test:

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test.py --host=http://localhost:8080
```

## Contributing

### Workflow

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/new-feature`
3. **Make** changes and add tests
4. **Run** tests and quality checks
5. **Commit** changes: `git commit -m "Add new feature"`
6. **Push** branch: `git push origin feature/new-feature`
7. **Create** a pull request

### Commit Guidelines

Follow conventional commit format:

```
type(scope): description

feat(api): add service management endpoints
fix(docker): resolve container startup issue
docs(readme): update installation instructions
test(api): add integration tests for health endpoints
```

### Code Review Checklist

- [ ] Tests pass (`pytest`)
- [ ] Code is formatted (`black`, `isort`)
- [ ] No linting errors (`flake8`)
- [ ] Type hints are correct (`mypy`)
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] No sensitive data in commits

## Useful Make Commands

Update your `Makefile`:

```makefile
.PHONY: dev test lint format clean docs

dev: ## Start development environment
	docker-compose -f docker-compose.dev.yml up -d postgres redis
	sleep 5
	python -m src.orchestrator.main

test: ## Run tests
	pytest tests/ -v --cov=src/orchestrator

lint: ## Run linting
	flake8 src/ tests/
	mypy src/
	black --check src/ tests/
	isort --check src/ tests/

format: ## Format code
	black src/ tests/
	isort src/ tests/

clean: ## Clean development environment
	docker-compose -f docker-compose.dev.yml down -v
	docker system prune -f

docs: ## Build documentation
	mkdocs build

docs-serve: ## Serve documentation locally
	mkdocs serve

install-dev: ## Install development dependencies
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

setup: ## Complete development setup
	python -m venv venv
	source venv/bin/activate && make install-dev
```

## Troubleshooting Development Issues

### Common Problems

1. **Import errors**: Check `PYTHONPATH` environment variable
2. **Database connection**: Ensure PostgreSQL is running
3. **Port conflicts**: Check if ports 8080/9090 are available
4. **Docker permission**: Add user to docker group
5. **Module not found**: Install in development mode: `pip install -e .`

### Debug Commands

```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Test database connection
python -c "
import asyncio
from src.orchestrator.database import test_connection
asyncio.run(test_connection())
"

# Check Docker connectivity
docker ps
docker network ls
```

For more help, see the [Troubleshooting Guide](troubleshooting.md).
