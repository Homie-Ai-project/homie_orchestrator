"""
FastAPI dependencies for the Orchestrator API
"""

from fastapi import HTTPException, status
from typing import Optional


def get_container_manager():
    """Dependency to get container manager from app state"""
    from fastapi import Request
    
    def _get_container_manager(request: Request):
        container_manager = getattr(request.app.state, 'container_manager', None)
        if container_manager is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Container manager not available"
            )
        return container_manager
    
    return _get_container_manager


def get_health_monitor():
    """Dependency to get health monitor from app state"""
    from fastapi import Request
    
    def _get_health_monitor(request: Request):
        health_monitor = getattr(request.app.state, 'health_monitor', None)
        if health_monitor is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Health monitor not available"
            )
        return health_monitor
    
    return _get_health_monitor


def get_scheduler():
    """Dependency to get scheduler from app state"""
    from fastapi import Request
    
    def _get_scheduler(request: Request):
        scheduler = getattr(request.app.state, 'scheduler', None)
        if scheduler is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scheduler not available"
            )
        return scheduler
    
    return _get_scheduler


def get_backup_manager():
    """Dependency to get backup manager from app state"""
    from fastapi import Request
    
    def _get_backup_manager(request: Request):
        backup_manager = getattr(request.app.state, 'backup_manager', None)
        if backup_manager is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Backup manager not available"
            )
        return backup_manager
    
    return _get_backup_manager


def get_database():
    """Dependency to get database from app state"""
    from fastapi import Request
    
    def _get_database(request: Request):
        database = getattr(request.app.state, 'database', None)
        if database is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not available"
            )
        return database
    
    return _get_database
