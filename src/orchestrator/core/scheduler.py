"""
Scheduler module for Homei Orchestrator

Handles scheduled tasks like backups, health checks, and maintenance.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from croniter import croniter


logger = logging.getLogger(__name__)


class Task:
    """Represents a scheduled task"""
    
    def __init__(
        self,
        task_id: str,
        name: str,
        func: Callable,
        schedule: str,
        enabled: bool = True,
        **kwargs
    ):
        self.task_id = task_id
        self.name = name
        self.func = func
        self.schedule = schedule
        self.enabled = enabled
        self.kwargs = kwargs
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.job = None


class Scheduler:
    """Task scheduler for the orchestrator"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.tasks: Dict[str, Task] = {}
        self._running = False
    
    async def start(self):
        """Start the scheduler"""
        if self._running:
            return
        
        try:
            self.scheduler.start()
            self._running = True
            logger.info("Scheduler started")
            
            # Add default tasks
            await self._add_default_tasks()
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the scheduler"""
        if not self._running:
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Scheduler stopped")
            
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    async def add_task(
        self,
        task_id: str,
        name: str,
        func: Callable,
        schedule: str,
        enabled: bool = True,
        **kwargs
    ) -> bool:
        """Add a new scheduled task"""
        try:
            task = Task(task_id, name, func, schedule, enabled, **kwargs)
            
            if enabled:
                # Parse schedule and create job
                if self._is_cron_schedule(schedule):
                    trigger = CronTrigger.from_crontab(schedule)
                elif self._is_interval_schedule(schedule):
                    seconds = self._parse_interval(schedule)
                    trigger = IntervalTrigger(seconds=seconds)
                else:
                    logger.error(f"Invalid schedule format: {schedule}")
                    return False
                
                # Add job to scheduler
                job = self.scheduler.add_job(
                    self._task_wrapper,
                    trigger=trigger,
                    id=task_id,
                    args=[task],
                    name=name
                )
                
                task.job = job
                task.next_run = job.next_run_time
            
            self.tasks[task_id] = task
            logger.info(f"Added task: {name} ({task_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add task {task_id}: {e}")
            return False
    
    async def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task"""
        try:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                
                if task.job:
                    self.scheduler.remove_job(task_id)
                
                del self.tasks[task_id]
                logger.info(f"Removed task: {task.name} ({task_id})")
                return True
            else:
                logger.warning(f"Task not found: {task_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove task {task_id}: {e}")
            return False
    
    async def enable_task(self, task_id: str) -> bool:
        """Enable a task"""
        try:
            if task_id not in self.tasks:
                logger.warning(f"Task not found: {task_id}")
                return False
            
            task = self.tasks[task_id]
            
            if not task.enabled:
                task.enabled = True
                
                # Add job to scheduler
                if self._is_cron_schedule(task.schedule):
                    trigger = CronTrigger.from_crontab(task.schedule)
                elif self._is_interval_schedule(task.schedule):
                    seconds = self._parse_interval(task.schedule)
                    trigger = IntervalTrigger(seconds=seconds)
                else:
                    logger.error(f"Invalid schedule format: {task.schedule}")
                    return False
                
                job = self.scheduler.add_job(
                    self._task_wrapper,
                    trigger=trigger,
                    id=task_id,
                    args=[task],
                    name=task.name
                )
                
                task.job = job
                task.next_run = job.next_run_time
                
                logger.info(f"Enabled task: {task.name} ({task_id})")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable task {task_id}: {e}")
            return False
    
    async def disable_task(self, task_id: str) -> bool:
        """Disable a task"""
        try:
            if task_id not in self.tasks:
                logger.warning(f"Task not found: {task_id}")
                return False
            
            task = self.tasks[task_id]
            
            if task.enabled:
                task.enabled = False
                
                if task.job:
                    self.scheduler.remove_job(task_id)
                    task.job = None
                    task.next_run = None
                
                logger.info(f"Disabled task: {task.name} ({task_id})")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable task {task_id}: {e}")
            return False
    
    async def get_tasks(self) -> List[Dict[str, Any]]:
        """Get list of all tasks"""
        return [
            {
                "id": task.task_id,
                "name": task.name,
                "schedule": task.schedule,
                "enabled": task.enabled,
                "last_run": task.last_run,
                "next_run": task.next_run
            }
            for task in self.tasks.values()
        ]
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific task"""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        return {
            "id": task.task_id,
            "name": task.name,
            "schedule": task.schedule,
            "enabled": task.enabled,
            "last_run": task.last_run,
            "next_run": task.next_run
        }
    
    async def _task_wrapper(self, task: Task):
        """Wrapper for task execution"""
        try:
            logger.info(f"Executing task: {task.name}")
            task.last_run = datetime.now()
            
            # Execute the task function
            if asyncio.iscoroutinefunction(task.func):
                await task.func(**task.kwargs)
            else:
                task.func(**task.kwargs)
            
            # Update next run time
            if task.job:
                task.next_run = task.job.next_run_time
            
            logger.info(f"Task completed: {task.name}")
            
        except Exception as e:
            logger.error(f"Task execution failed: {task.name} - {e}")
    
    def _is_cron_schedule(self, schedule: str) -> bool:
        """Check if schedule is in cron format"""
        try:
            croniter(schedule)
            return True
        except ValueError:
            return False
    
    def _is_interval_schedule(self, schedule: str) -> bool:
        """Check if schedule is in interval format (e.g., '30s', '5m', '1h')"""
        return schedule.endswith(('s', 'm', 'h', 'd'))
    
    def _parse_interval(self, schedule: str) -> int:
        """Parse interval schedule and return seconds"""
        if schedule.endswith('s'):
            return int(schedule[:-1])
        elif schedule.endswith('m'):
            return int(schedule[:-1]) * 60
        elif schedule.endswith('h'):
            return int(schedule[:-1]) * 3600
        elif schedule.endswith('d'):
            return int(schedule[:-1]) * 86400
        else:
            raise ValueError(f"Invalid interval format: {schedule}")
    
    async def _add_default_tasks(self):
        """Add default system tasks"""
        # Example default tasks
        await self.add_task(
            "health_check",
            "System Health Check",
            self._default_health_check,
            "*/5 * * * *",  # Every 5 minutes
            enabled=True
        )
        
        await self.add_task(
            "cleanup",
            "System Cleanup",
            self._default_cleanup,
            "0 3 * * *",  # Daily at 3 AM
            enabled=True
        )
    
    async def _default_health_check(self):
        """Default health check task"""
        logger.info("Running default health check")
        # This would typically check system health
        pass
    
    async def _default_cleanup(self):
        """Default cleanup task"""
        logger.info("Running default cleanup")
        # This would typically clean up old logs, temp files, etc.
        pass
