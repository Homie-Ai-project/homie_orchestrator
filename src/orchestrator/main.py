"""
Homie Orchestrator Main Application

A supervisor-like container management system for AI workloads and services.
This orchestrator manages Docker containers, handles updates, backups, and provides
a REST API for service management.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router as api_router
from .config import get_settings
from .core.container_manager import ContainerManager
from .core.database import Database
from .core.scheduler import Scheduler
from .core.health_monitor import HealthMonitor
from .core.backup_manager import BackupManager
from .metrics import setup_metrics


# Setup structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(30),  # INFO level
    logger_factory=structlog.WriteLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class OrchestratorApp:
    """Main Orchestrator Application Class"""
    
    def __init__(self):
        self.settings = get_settings()
        self.app = FastAPI(
            title="Homie Orchestrator",
            description="Container management and supervision system",
            version=self.settings.orchestrator.version,
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Core components
        self.database = None
        self.container_manager = None
        self.scheduler = None
        self.health_monitor = None
        self.backup_manager = None
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    async def startup(self):
        """Initialize all orchestrator components"""
        logger.info("Starting Homie Orchestrator", version=self.settings.orchestrator.version)
        
        try:
            # Initialize database
            self.database = Database(self.settings.database.url)
            await self.database.initialize()
            
            # Initialize container manager
            self.container_manager = ContainerManager(
                docker_socket=self.settings.docker.socket_path,
                network_name=self.settings.docker.network_name
            )
            await self.container_manager.initialize()
            
            # Initialize scheduler
            self.scheduler = Scheduler()
            await self.scheduler.start()
            
            # Initialize health monitor
            self.health_monitor = HealthMonitor(
                container_manager=self.container_manager,
                check_interval=self.settings.monitoring.health_check_interval
            )
            await self.health_monitor.start()
            
            # Initialize backup manager
            if self.settings.backup.enabled:
                self.backup_manager = BackupManager(
                    backup_path=Path(self.settings.storage.backup_path),
                    schedule=self.settings.backup.schedule,
                    retention_days=self.settings.backup.retention_days
                )
                await self.backup_manager.initialize()
            
            # Setup metrics if enabled
            if self.settings.monitoring.enabled:
                setup_metrics(self.app, self.settings.monitoring.metrics_port)
            
            # Store components in app state for API access
            self.app.state.container_manager = self.container_manager
            self.app.state.scheduler = self.scheduler
            self.app.state.health_monitor = self.health_monitor
            self.app.state.backup_manager = self.backup_manager
            self.app.state.database = self.database
            
            logger.info("Orchestrator startup completed successfully")
            
        except Exception as e:
            logger.error("Failed to start orchestrator", error=str(e))
            raise
    
    async def shutdown(self):
        """Gracefully shutdown all components"""
        logger.info("Shutting down Homie Orchestrator")
        
        # Stop components in reverse order
        if self.backup_manager:
            await self.backup_manager.stop()
            
        if self.health_monitor:
            await self.health_monitor.stop()
            
        if self.scheduler:
            await self.scheduler.stop()
            
        if self.container_manager:
            await self.container_manager.cleanup()
            
        if self.database:
            await self.database.close()
            
        logger.info("Orchestrator shutdown completed")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal", signal=signum)
        asyncio.create_task(self.shutdown())
        sys.exit(0)
    
    def setup_middleware(self):
        """Setup FastAPI middleware"""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.settings.api.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """Setup API routes"""
        self.app.include_router(api_router, prefix="/api/v1")
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "version": self.settings.orchestrator.version,
                "timestamp": asyncio.get_event_loop().time()
            }
    
    def create_app(self) -> FastAPI:
        """Create and configure the FastAPI application"""
        self.setup_middleware()
        self.setup_routes()
        
        # Add startup and shutdown event handlers
        @self.app.on_event("startup")
        async def startup_event():
            await self.startup()
        
        @self.app.on_event("shutdown")
        async def shutdown_event():
            await self.shutdown()
        
        return self.app


def create_app() -> FastAPI:
    """Factory function to create the FastAPI app"""
    orchestrator = OrchestratorApp()
    return orchestrator.create_app()


async def main():
    """Main entry point"""
    settings = get_settings()
    
    # Configure logging level
    log_level = getattr(logging, settings.orchestrator.logging.level.upper())
    logging.basicConfig(level=log_level)
    
    # Create app
    app = create_app()
    
    # Run the server
    config = uvicorn.Config(
        app,
        host=settings.api.host,
        port=settings.api.port,
        log_level=settings.orchestrator.logging.level.lower(),
        access_log=True,
        loop="asyncio"
    )
    
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
