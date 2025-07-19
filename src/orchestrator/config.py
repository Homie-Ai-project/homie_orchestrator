"""
Configuration management for Homei Orchestrator
"""

import os
from pathlib import Path
from typing import List, Optional
from functools import lru_cache

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class APIConfig(BaseModel):
    """API configuration"""
    host: str = "0.0.0.0"
    port: int = 8080
    cors_origins: List[str] = ["*"]


class SecurityConfig(BaseModel):
    """Security configuration"""
    secret_key: str = "changeme"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30


class DockerConfig(BaseModel):
    """Docker configuration"""
    socket_path: str = "/var/run/docker.sock"
    network_name: str = "homei_network"
    registry_url: Optional[str] = "docker.io"
    registry_username: Optional[str] = None
    registry_password: Optional[str] = None


class StorageConfig(BaseModel):
    """Storage configuration"""
    data_path: str = "/data"
    config_path: str = "/config"
    backup_path: str = "/backups"


class DatabaseConfig(BaseModel):
    """Database configuration"""
    url: str = "postgresql+asyncpg://homei:homei_password@postgres:5432/homei"
    pool_size: int = 10
    max_overflow: int = 20


class RedisConfig(BaseModel):
    """Redis configuration"""
    url: str = "redis://redis:6379/0"


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = "INFO"
    format: str = "structured"


class MonitoringConfig(BaseModel):
    """Monitoring configuration"""
    enabled: bool = True
    metrics_port: int = 9090
    health_check_interval: int = 30


class BackupConfig(BaseModel):
    """Backup configuration"""
    enabled: bool = True
    schedule: str = "0 2 * * *"  # Daily at 2 AM
    retention_days: int = 30


class OrchestratorConfig(BaseModel):
    """Main orchestrator configuration"""
    name: str = "Homei Orchestrator"
    version: str = "1.0.0"
    timezone: str = "UTC"
    api: APIConfig = Field(default_factory=APIConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    backup: BackupConfig = Field(default_factory=BackupConfig)


class ServiceConfig(BaseModel):
    """Configuration for a managed service"""
    image: str
    enabled: bool = True
    restart_policy: str = "unless-stopped"
    environment: dict = Field(default_factory=dict)
    ports: List[str] = Field(default_factory=list)
    volumes: List[str] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)
    labels: dict = Field(default_factory=dict)
    networks: List[str] = Field(default_factory=list)
    command: Optional[str] = None
    entrypoint: Optional[str] = None
    working_dir: Optional[str] = None
    user: Optional[str] = None
    privileged: bool = False
    cap_add: List[str] = Field(default_factory=list)
    cap_drop: List[str] = Field(default_factory=list)
    devices: List[str] = Field(default_factory=list)
    memory_limit: Optional[str] = None
    cpu_limit: Optional[float] = None


class Settings(BaseSettings):
    """Main settings class"""
    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
    services: dict[str, ServiceConfig] = Field(default_factory=dict)
    
    class Config:
        env_prefix = "ORCHESTRATOR_"
        env_nested_delimiter = "__"


def load_config_from_file(config_path: str) -> dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML configuration: {e}")


@lru_cache()
def get_settings() -> Settings:
    """Get application settings with caching"""
    # Default config path
    config_path = os.getenv("ORCHESTRATOR_CONFIG_PATH", "/config")
    config_file = Path(config_path) / "orchestrator.yaml"
    
    # Load configuration from file if it exists
    config_data = {}
    if config_file.exists():
        config_data = load_config_from_file(str(config_file))
    
    # Create settings object
    settings = Settings(**config_data)
    
    # Override with environment variables
    settings = Settings()
    
    return settings


def get_service_config(service_name: str) -> Optional[ServiceConfig]:
    """Get configuration for a specific service"""
    settings = get_settings()
    return settings.services.get(service_name)


def update_service_config(service_name: str, config: ServiceConfig) -> None:
    """Update configuration for a specific service"""
    # This would typically persist to file or database
    # For now, we'll just update the in-memory cache
    settings = get_settings()
    settings.services[service_name] = config
    
    # Clear cache to force reload
    get_settings.cache_clear()


def save_config_to_file(config_path: str, settings: Settings) -> None:
    """Save configuration to YAML file"""
    config_data = settings.dict()
    
    with open(config_path, 'w') as f:
        yaml.safe_dump(config_data, f, default_flow_style=False, indent=2)
