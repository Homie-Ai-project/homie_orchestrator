"""
Pydantic models for the Orchestrator API
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ContainerInfo(BaseModel):
    """Container information model"""
    id: Optional[str] = None
    name: Optional[str] = None
    status: str
    image: Optional[str] = None
    created: Optional[str] = None
    ports: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, str]] = None
    error: Optional[str] = None


class ContainerStatus(BaseModel):
    """Container status model"""
    service_name: str
    status: str


class ContainerLogs(BaseModel):
    """Container logs model"""
    service_name: str
    logs: str


class ContainerStats(BaseModel):
    """Container statistics model"""
    service_name: str
    stats: Dict[str, Any]


class ServiceConfigModel(BaseModel):
    """Service configuration model for API"""
    image: str
    enabled: bool = True
    restart_policy: str = "unless-stopped"
    environment: Dict[str, str] = Field(default_factory=dict)
    ports: List[str] = Field(default_factory=list)
    volumes: List[str] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)
    labels: Dict[str, str] = Field(default_factory=dict)
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


class OrchestratorInfo(BaseModel):
    """Orchestrator information model"""
    name: str
    version: str
    status: str
    uptime: Optional[float] = None
    containers_managed: Optional[int] = None


class HealthCheck(BaseModel):
    """Health check result model"""
    service: str
    status: str
    message: Optional[str] = None
    last_check: datetime


class OverallHealth(BaseModel):
    """Overall health status model"""
    healthy: bool
    checks: List[HealthCheck]
    timestamp: datetime


class BackupInfo(BaseModel):
    """Backup information model"""
    filename: str
    size: int
    created_at: datetime
    services: List[str]


class TaskInfo(BaseModel):
    """Scheduled task information"""
    id: str
    name: str
    schedule: str
    next_run: datetime
    last_run: Optional[datetime] = None
    enabled: bool
