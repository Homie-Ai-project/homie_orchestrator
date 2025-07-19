"""
Backup Manager for Homie Orchestrator

Handles automated backups of container data and configurations.
"""

import asyncio
import logging
import shutil
import tarfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any


logger = logging.getLogger(__name__)


class BackupManager:
    """Manages automated backups of the orchestrator system"""
    
    def __init__(self, backup_path: Path, schedule: str, retention_days: int = 30):
        self.backup_path = backup_path
        self.schedule = schedule
        self.retention_days = retention_days
        self._running = False
        self._backup_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize the backup manager"""
        try:
            # Ensure backup directory exists
            self.backup_path.mkdir(parents=True, exist_ok=True)
            
            # Clean up old backups
            await self._cleanup_old_backups()
            
            logger.info(f"Backup manager initialized - path: {self.backup_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize backup manager: {e}")
            raise
    
    async def start(self):
        """Start the backup manager"""
        if self._running:
            return
        
        self._running = True
        logger.info("Backup manager started")
    
    async def stop(self):
        """Stop the backup manager"""
        self._running = False
        
        if self._backup_task:
            self._backup_task.cancel()
            try:
                await self._backup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Backup manager stopped")
    
    async def create_backup(self, services: Optional[List[str]] = None) -> Optional[str]:
        """Create a backup of specified services or all services"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"orchestrator_backup_{timestamp}.tar.gz"
            backup_file_path = self.backup_path / backup_filename
            
            logger.info(f"Creating backup: {backup_filename}")
            
            # Create temporary directory for backup preparation
            temp_dir = self.backup_path / f"temp_{timestamp}"
            temp_dir.mkdir(exist_ok=True)
            
            try:
                # Backup configuration files
                await self._backup_configs(temp_dir)
                
                # Backup service data
                await self._backup_service_data(temp_dir, services)
                
                # Create metadata
                await self._create_backup_metadata(temp_dir, services)
                
                # Create tar.gz archive
                await self._create_archive(temp_dir, backup_file_path)
                
                # Cleanup temp directory
                shutil.rmtree(temp_dir)
                
                logger.info(f"Backup created successfully: {backup_filename}")
                return backup_filename
                
            except Exception as e:
                # Cleanup on error
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                if backup_file_path.exists():
                    backup_file_path.unlink()
                raise e
                
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    async def restore_backup(self, backup_filename: str) -> bool:
        """Restore from a backup file"""
        try:
            backup_file_path = self.backup_path / backup_filename
            
            if not backup_file_path.exists():
                logger.error(f"Backup file not found: {backup_filename}")
                return False
            
            logger.info(f"Restoring from backup: {backup_filename}")
            
            # Create temporary directory for extraction
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_dir = self.backup_path / f"restore_{timestamp}"
            temp_dir.mkdir(exist_ok=True)
            
            try:
                # Extract backup
                await self._extract_archive(backup_file_path, temp_dir)
                
                # Read metadata
                metadata_file = temp_dir / "metadata.json"
                if metadata_file.exists():
                    with metadata_file.open('r') as f:
                        metadata = json.load(f)
                    logger.info(f"Backup metadata: {metadata}")
                
                # Restore configuration files
                await self._restore_configs(temp_dir)
                
                # Restore service data
                await self._restore_service_data(temp_dir)
                
                # Cleanup temp directory
                shutil.rmtree(temp_dir)
                
                logger.info(f"Backup restored successfully: {backup_filename}")
                return True
                
            except Exception as e:
                # Cleanup on error
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                raise e
                
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        try:
            backups = []
            
            for backup_file in self.backup_path.glob("orchestrator_backup_*.tar.gz"):
                stat = backup_file.stat()
                
                # Try to extract metadata
                metadata = await self._get_backup_metadata(backup_file)
                
                backup_info = {
                    "filename": backup_file.name,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime),
                    "services": metadata.get("services", []) if metadata else [],
                    "orchestrator_version": metadata.get("orchestrator_version", "unknown") if metadata else "unknown"
                }
                
                backups.append(backup_info)
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
    async def delete_backup(self, backup_filename: str) -> bool:
        """Delete a specific backup"""
        try:
            backup_file_path = self.backup_path / backup_filename
            
            if not backup_file_path.exists():
                logger.error(f"Backup file not found: {backup_filename}")
                return False
            
            backup_file_path.unlink()
            logger.info(f"Backup deleted: {backup_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False
    
    async def _backup_configs(self, temp_dir: Path):
        """Backup configuration files"""
        config_backup_dir = temp_dir / "config"
        config_backup_dir.mkdir(exist_ok=True)
        
        # Backup orchestrator config
        config_source = Path("/config")
        if config_source.exists():
            shutil.copytree(config_source, config_backup_dir / "orchestrator", dirs_exist_ok=True)
    
    async def _backup_service_data(self, temp_dir: Path, services: Optional[List[str]]):
        """Backup service data directories"""
        data_backup_dir = temp_dir / "data"
        data_backup_dir.mkdir(exist_ok=True)
        
        data_source = Path("/data")
        if data_source.exists():
            if services:
                # Backup only specified services
                for service in services:
                    service_data_dir = data_source / service
                    if service_data_dir.exists():
                        shutil.copytree(
                            service_data_dir,
                            data_backup_dir / service,
                            dirs_exist_ok=True
                        )
            else:
                # Backup all data
                shutil.copytree(data_source, data_backup_dir / "all", dirs_exist_ok=True)
    
    async def _create_backup_metadata(self, temp_dir: Path, services: Optional[List[str]]):
        """Create backup metadata file"""
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "orchestrator_version": "1.0.0",
            "services": services or ["all"],
            "backup_type": "partial" if services else "full"
        }
        
        metadata_file = temp_dir / "metadata.json"
        with metadata_file.open('w') as f:
            json.dump(metadata, f, indent=2)
    
    async def _create_archive(self, temp_dir: Path, archive_path: Path):
        """Create tar.gz archive from temporary directory"""
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(temp_dir, arcname=".")
    
    async def _extract_archive(self, archive_path: Path, extract_dir: Path):
        """Extract tar.gz archive to directory"""
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(extract_dir)
    
    async def _restore_configs(self, temp_dir: Path):
        """Restore configuration files from backup"""
        config_backup_dir = temp_dir / "config" / "orchestrator"
        config_target = Path("/config")
        
        if config_backup_dir.exists():
            shutil.copytree(config_backup_dir, config_target, dirs_exist_ok=True)
    
    async def _restore_service_data(self, temp_dir: Path):
        """Restore service data from backup"""
        data_backup_dir = temp_dir / "data"
        data_target = Path("/data")
        
        if data_backup_dir.exists():
            # Check if it's a full backup or partial
            if (data_backup_dir / "all").exists():
                # Full backup
                shutil.copytree(data_backup_dir / "all", data_target, dirs_exist_ok=True)
            else:
                # Partial backup - restore individual services
                for service_dir in data_backup_dir.iterdir():
                    if service_dir.is_dir():
                        target_dir = data_target / service_dir.name
                        shutil.copytree(service_dir, target_dir, dirs_exist_ok=True)
    
    async def _get_backup_metadata(self, backup_file: Path) -> Optional[Dict[str, Any]]:
        """Extract metadata from backup file"""
        try:
            with tarfile.open(backup_file, "r:gz") as tar:
                try:
                    metadata_member = tar.getmember("metadata.json")
                    metadata_file = tar.extractfile(metadata_member)
                    if metadata_file:
                        return json.load(metadata_file)
                except KeyError:
                    # No metadata file in backup
                    pass
            return None
        except Exception:
            return None
    
    async def _cleanup_old_backups(self):
        """Remove backups older than retention period"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            for backup_file in self.backup_path.glob("orchestrator_backup_*.tar.gz"):
                stat = backup_file.stat()
                file_date = datetime.fromtimestamp(stat.st_mtime)
                
                if file_date < cutoff_date:
                    backup_file.unlink()
                    logger.info(f"Deleted old backup: {backup_file.name}")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
