"""
Health Monitor for Homei Orchestrator

Monitors the health of managed containers and services.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..api.models import HealthCheck, OverallHealth


logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors health of containers and services"""
    
    def __init__(self, container_manager, check_interval: int = 30):
        self.container_manager = container_manager
        self.check_interval = check_interval
        self.health_checks: Dict[str, HealthCheck] = {}
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the health monitoring task"""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitor started")
    
    async def stop(self):
        """Stop the health monitoring task"""
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _perform_health_checks(self):
        """Perform health checks on all managed containers"""
        try:
            containers = await self.container_manager.list_containers()
            
            for service_name, container_info in containers.items():
                await self._check_container_health(service_name, container_info)
                
        except Exception as e:
            logger.error(f"Failed to perform health checks: {e}")
    
    async def _check_container_health(self, service_name: str, container_info: Dict[str, Any]):
        """Check health of a specific container"""
        try:
            status = container_info.get("status", "unknown")
            
            # Determine health based on container status
            if status == "running":
                health_status = "healthy"
                message = "Container is running normally"
            elif status == "restarting":
                health_status = "warning"
                message = "Container is restarting"
            elif status in ["stopped", "exited"]:
                health_status = "unhealthy"
                message = f"Container is {status}"
            elif "error" in container_info:
                health_status = "error"
                message = container_info["error"]
            else:
                health_status = "unknown"
                message = f"Unknown container status: {status}"
            
            # Create health check result
            health_check = HealthCheck(
                service=service_name,
                status=health_status,
                message=message,
                last_check=datetime.now()
            )
            
            self.health_checks[service_name] = health_check
            
            # Log unhealthy containers
            if health_status in ["unhealthy", "error"]:
                logger.warning(f"Unhealthy container detected: {service_name} - {message}")
            
        except Exception as e:
            # Create error health check
            health_check = HealthCheck(
                service=service_name,
                status="error",
                message=f"Health check failed: {str(e)}",
                last_check=datetime.now()
            )
            self.health_checks[service_name] = health_check
            logger.error(f"Failed to check health for {service_name}: {e}")
    
    async def get_service_health(self, service_name: str) -> Optional[HealthCheck]:
        """Get health status for a specific service"""
        return self.health_checks.get(service_name)
    
    async def get_all_health_checks(self) -> List[HealthCheck]:
        """Get all health check results"""
        return list(self.health_checks.values())
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """Get overall health status"""
        health_checks = await self.get_all_health_checks()
        
        # Determine overall health
        healthy_count = sum(1 for check in health_checks if check.status == "healthy")
        total_count = len(health_checks)
        
        # Consider system healthy if at least 80% of services are healthy
        overall_healthy = total_count == 0 or (healthy_count / total_count) >= 0.8
        
        return {
            "healthy": overall_healthy,
            "checks": health_checks,
            "timestamp": datetime.now(),
            "summary": {
                "total_services": total_count,
                "healthy_services": healthy_count,
                "unhealthy_services": total_count - healthy_count
            }
        }
    
    async def get_unhealthy_services(self) -> List[HealthCheck]:
        """Get list of unhealthy services"""
        return [
            check for check in self.health_checks.values()
            if check.status in ["unhealthy", "error", "warning"]
        ]
    
    async def is_service_healthy(self, service_name: str) -> bool:
        """Check if a specific service is healthy"""
        health_check = await self.get_service_health(service_name)
        return health_check is not None and health_check.status == "healthy"
