"""
Container Manager

Manages Docker containers for AI services and applications.
Provides high-level API for container lifecycle management, monitoring,
and deployment automation.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

import docker
import docker.errors
from docker.models.containers import Container
from docker.models.networks import Network

from ..config import ServiceConfig, get_service_config


logger = logging.getLogger(__name__)


class ContainerStatus:
    """Container status constants"""
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"
    UNKNOWN = "unknown"


class ContainerManager:
    """Manages Docker containers for the orchestrator"""
    
    def __init__(self, docker_socket: str = "/var/run/docker.sock", network_name: str = "homie_network"):
        self.docker_socket = docker_socket
        self.network_name = network_name
        self.client: Optional[docker.DockerClient] = None
        self.network: Optional[Network] = None
        self._containers: Dict[str, Container] = {}
        
    async def initialize(self):
        """Initialize the Docker client and network"""
        try:
            # Initialize Docker client
            self.client = docker.DockerClient(base_url=f"unix://{self.docker_socket}")
            
            # Test connection
            self.client.ping()
            logger.info("Docker client initialized successfully")
            
            # Ensure network exists
            await self._ensure_network()
            
            # Discover existing containers
            await self._discover_containers()
            
        except docker.errors.DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise
    
    async def _ensure_network(self):
        """Ensure the orchestrator network exists"""
        try:
            self.network = self.client.networks.get(self.network_name)
            logger.info(f"Using existing network: {self.network_name}")
        except docker.errors.NotFound:
            # Create the network
            self.network = self.client.networks.create(
                name=self.network_name,
                driver="bridge",
                labels={"io.homie.orchestrator": "true"}
            )
            logger.info(f"Created network: {self.network_name}")
    
    async def _discover_containers(self):
        """Discover existing managed containers"""
        try:
            containers = self.client.containers.list(
                all=True,
                filters={"label": "io.homie.managed=true"}
            )
            
            for container in containers:
                service_name = container.labels.get("io.homie.service")
                if service_name:
                    self._containers[service_name] = container
                    logger.info(f"Discovered managed container: {service_name}")
                    
        except docker.errors.DockerException as e:
            logger.error(f"Failed to discover containers: {e}")
    
    async def create_container(self, service_name: str, config: ServiceConfig) -> bool:
        """Create a new container for a service"""
        try:
            # Prepare container configuration
            container_config = await self._prepare_container_config(service_name, config)
            
            # Create the container
            container = self.client.containers.create(**container_config)
            
            # Connect to network
            if self.network:
                self.network.connect(container)
            
            self._containers[service_name] = container
            logger.info(f"Created container for service: {service_name}")
            
            return True
            
        except docker.errors.DockerException as e:
            logger.error(f"Failed to create container for {service_name}: {e}")
            return False
    
    async def start_container(self, service_name: str) -> bool:
        """Start a container"""
        try:
            container = self._containers.get(service_name)
            if not container:
                logger.error(f"Container not found for service: {service_name}")
                return False
            
            container.start()
            logger.info(f"Started container for service: {service_name}")
            return True
            
        except docker.errors.DockerException as e:
            logger.error(f"Failed to start container for {service_name}: {e}")
            return False
    
    async def stop_container(self, service_name: str, timeout: int = 30) -> bool:
        """Stop a container"""
        try:
            container = self._containers.get(service_name)
            if not container:
                logger.error(f"Container not found for service: {service_name}")
                return False
            
            container.stop(timeout=timeout)
            logger.info(f"Stopped container for service: {service_name}")
            return True
            
        except docker.errors.DockerException as e:
            logger.error(f"Failed to stop container for {service_name}: {e}")
            return False
    
    async def restart_container(self, service_name: str, timeout: int = 30) -> bool:
        """Restart a container"""
        try:
            container = self._containers.get(service_name)
            if not container:
                logger.error(f"Container not found for service: {service_name}")
                return False
            
            container.restart(timeout=timeout)
            logger.info(f"Restarted container for service: {service_name}")
            return True
            
        except docker.errors.DockerException as e:
            logger.error(f"Failed to restart container for {service_name}: {e}")
            return False
    
    async def remove_container(self, service_name: str, force: bool = False) -> bool:
        """Remove a container"""
        try:
            container = self._containers.get(service_name)
            if not container:
                logger.error(f"Container not found for service: {service_name}")
                return False
            
            # Stop first if running
            if container.status == "running":
                await self.stop_container(service_name)
            
            container.remove(force=force)
            del self._containers[service_name]
            logger.info(f"Removed container for service: {service_name}")
            return True
            
        except docker.errors.DockerException as e:
            logger.error(f"Failed to remove container for {service_name}: {e}")
            return False
    
    async def get_container_status(self, service_name: str) -> str:
        """Get container status"""
        try:
            container = self._containers.get(service_name)
            if not container:
                return ContainerStatus.UNKNOWN
            
            # Reload container to get current status
            container.reload()
            return container.status
            
        except docker.errors.DockerException:
            return ContainerStatus.ERROR
    
    async def get_container_logs(self, service_name: str, tail: int = 100) -> str:
        """Get container logs"""
        try:
            container = self._containers.get(service_name)
            if not container:
                return "Container not found"
            
            logs = container.logs(tail=tail, timestamps=True)
            return logs.decode('utf-8')
            
        except docker.errors.DockerException as e:
            return f"Error getting logs: {e}"
    
    async def get_container_stats(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get container stats"""
        try:
            container = self._containers.get(service_name)
            if not container:
                return None
            
            stats = container.stats(stream=False)
            return stats
            
        except docker.errors.DockerException as e:
            logger.error(f"Failed to get stats for {service_name}: {e}")
            return None
    
    async def list_containers(self) -> Dict[str, Dict[str, Any]]:
        """List all managed containers with their status"""
        result = {}
        
        for service_name, container in self._containers.items():
            try:
                container.reload()
                result[service_name] = {
                    "id": container.id,
                    "name": container.name,
                    "status": container.status,
                    "image": container.image.tags[0] if container.image.tags else container.image.id,
                    "created": container.attrs["Created"],
                    "ports": container.ports,
                    "labels": container.labels
                }
            except docker.errors.DockerException as e:
                result[service_name] = {
                    "error": str(e),
                    "status": ContainerStatus.ERROR
                }
        
        return result
    
    async def pull_image(self, image: str) -> bool:
        """Pull a Docker image"""
        try:
            logger.info(f"Pulling image: {image}")
            self.client.images.pull(image)
            logger.info(f"Successfully pulled image: {image}")
            return True
            
        except docker.errors.DockerException as e:
            logger.error(f"Failed to pull image {image}: {e}")
            return False
    
    async def update_container(self, service_name: str, config: ServiceConfig) -> bool:
        """Update a container with new configuration"""
        try:
            # Stop and remove existing container
            await self.stop_container(service_name)
            await self.remove_container(service_name)
            
            # Pull new image if needed
            await self.pull_image(config.image)
            
            # Create and start new container
            await self.create_container(service_name, config)
            await self.start_container(service_name)
            
            logger.info(f"Updated container for service: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update container for {service_name}: {e}")
            return False
    
    async def _prepare_container_config(self, service_name: str, config: ServiceConfig) -> Dict[str, Any]:
        """Prepare container configuration for Docker API"""
        container_config = {
            "image": config.image,
            "name": f"homie_{service_name}",
            "detach": True,
            "restart_policy": {"Name": config.restart_policy},
            "labels": {
                "io.homie.managed": "true",
                "io.homie.service": service_name,
                **config.labels
            }
        }
        
        # Environment variables
        if config.environment:
            container_config["environment"] = config.environment
        
        # Volumes
        if config.volumes:
            volumes = {}
            for volume in config.volumes:
                host_path, container_path = volume.split(":")
                volumes[host_path] = {"bind": container_path, "mode": "rw"}
            container_config["volumes"] = volumes
        
        # Ports
        if config.ports:
            ports = {}
            for port_mapping in config.ports:
                if ":" in port_mapping:
                    host_port, container_port = port_mapping.split(":")
                    ports[f"{container_port}/tcp"] = host_port
                else:
                    ports[f"{port_mapping}/tcp"] = port_mapping
            container_config["ports"] = ports
        
        # Command and entrypoint
        if config.command:
            container_config["command"] = config.command
        
        if config.entrypoint:
            container_config["entrypoint"] = config.entrypoint
        
        # Working directory
        if config.working_dir:
            container_config["working_dir"] = config.working_dir
        
        # User
        if config.user:
            container_config["user"] = config.user
        
        # Privileged mode
        if config.privileged:
            container_config["privileged"] = True
        
        # Capabilities
        if config.cap_add or config.cap_drop:
            host_config = container_config.setdefault("host_config", {})
            if config.cap_add:
                host_config["cap_add"] = config.cap_add
            if config.cap_drop:
                host_config["cap_drop"] = config.cap_drop
        
        # Devices
        if config.devices:
            host_config = container_config.setdefault("host_config", {})
            host_config["devices"] = config.devices
        
        # Resource limits
        if config.memory_limit or config.cpu_limit:
            host_config = container_config.setdefault("host_config", {})
            if config.memory_limit:
                host_config["mem_limit"] = config.memory_limit
            if config.cpu_limit:
                host_config["cpu_quota"] = int(config.cpu_limit * 100000)
        
        return container_config
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            self.client.close()
            logger.info("Docker client closed")
