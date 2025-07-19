"""
Database module for Homie Orchestrator

Handles database connections and operations.
"""

import asyncio
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean
from datetime import datetime


logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for database models"""
    pass


class ServiceRecord(Base):
    """Database model for service records"""
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    image = Column(String(500), nullable=False)
    status = Column(String(50), nullable=False)
    config = Column(Text, nullable=True)  # JSON config
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    enabled = Column(Boolean, default=True)


class HealthRecord(Base):
    """Database model for health check records"""
    __tablename__ = "health_checks"
    
    id = Column(Integer, primary_key=True)
    service_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    message = Column(Text, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow)


class BackupRecord(Base):
    """Database model for backup records"""
    __tablename__ = "backups"
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(500), nullable=False)
    size = Column(Integer, nullable=False)
    services = Column(Text, nullable=True)  # JSON list of services
    created_at = Column(DateTime, default=datetime.utcnow)


class Database:
    """Database manager for the orchestrator"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.session_factory = None
    
    async def initialize(self):
        """Initialize database connection and create tables"""
        try:
            # Create async engine
            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def get_session(self) -> AsyncSession:
        """Get a database session"""
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        
        return self.session_factory()
    
    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            async with self.get_session() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
