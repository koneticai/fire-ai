"""
Process Manager for FireMode Compliance Platform.

This module provides robust process management for the embedded Go service,
including automatic restarts, health monitoring, and graceful shutdowns.
"""

import os
import signal
import subprocess
import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

import httpx


logger = logging.getLogger(__name__)


class ProcessState(Enum):
    """Process states for the Go service."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


@dataclass
class ProcessInfo:
    """Information about a managed process."""
    pid: Optional[int]
    state: ProcessState
    start_time: Optional[float]
    restart_count: int
    last_error: Optional[str]


class GoServiceManager:
    """Manages the Go service process with automatic restarts and health monitoring."""
    
    def __init__(self, service_dir: Path, max_restarts: int = 5, restart_delay: float = 5.0):
        self.service_dir = service_dir
        self.max_restarts = max_restarts
        self.restart_delay = restart_delay
        self.health_check_interval = 30.0  # 30 seconds
        self.health_check_timeout = 5.0   # 5 seconds
        
        self.process: Optional[subprocess.Popen] = None
        self.process_info = ProcessInfo(
            pid=None,
            state=ProcessState.STOPPED,
            start_time=None,
            restart_count=0,
            last_error=None
        )
        
        self._shutdown_event = asyncio.Event()
        self._health_check_task: Optional[asyncio.Task] = None
        
    async def start(self) -> bool:
        """
        Start the Go service process.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.process_info.state in [ProcessState.STARTING, ProcessState.RUNNING]:
            logger.warning("Go service is already running or starting")
            return True
            
        self.process_info.state = ProcessState.STARTING
        logger.info("Starting Go service...")
        
        try:
            # Build the Go service first
            if not await self._build_service():
                self.process_info.state = ProcessState.FAILED
                self.process_info.last_error = "Build failed"
                return False
            
            # Start the service process
            self.process = subprocess.Popen(
                ["./firemode-go-service"],
                cwd=self.service_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL
            )
            
            self.process_info.pid = self.process.pid
            self.process_info.start_time = time.time()
            
            # Wait a moment for startup
            await asyncio.sleep(2.0)
            
            # Check if process is still running
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                error_msg = f"Process exited immediately. stderr: {stderr.decode()}"
                logger.error(error_msg)
                self.process_info.state = ProcessState.FAILED
                self.process_info.last_error = error_msg
                return False
            
            # Health check
            if await self._health_check():
                self.process_info.state = ProcessState.RUNNING
                logger.info(f"Go service started successfully (PID: {self.process_info.pid})")
                
                # Start health monitoring
                self._health_check_task = asyncio.create_task(self._monitor_health())
                return True
            else:
                logger.error("Go service failed health check after startup")
                await self._stop_process()
                self.process_info.state = ProcessState.FAILED
                self.process_info.last_error = "Health check failed"
                return False
                
        except Exception as e:
            logger.error(f"Failed to start Go service: {e}")
            self.process_info.state = ProcessState.FAILED
            self.process_info.last_error = str(e)
            return False
    
    async def stop(self) -> bool:
        """
        Stop the Go service process gracefully.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if self.process_info.state == ProcessState.STOPPED:
            return True
            
        self.process_info.state = ProcessState.STOPPING
        self._shutdown_event.set()
        
        # Cancel health monitoring
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        return await self._stop_process()
    
    async def restart(self) -> bool:
        """
        Restart the Go service process.
        
        Returns:
            True if restarted successfully, False otherwise
        """
        logger.info("Restarting Go service...")
        await self.stop()
        await asyncio.sleep(self.restart_delay)
        return await self.start()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the Go service.
        
        Returns:
            Status information dictionary
        """
        return {
            "state": self.process_info.state.value,
            "pid": self.process_info.pid,
            "start_time": self.process_info.start_time,
            "restart_count": self.process_info.restart_count,
            "last_error": self.process_info.last_error,
            "uptime_seconds": time.time() - self.process_info.start_time if self.process_info.start_time else 0
        }
    
    async def _build_service(self) -> bool:
        """Build the Go service binary."""
        try:
            logger.info("Building Go service...")
            result = await asyncio.create_subprocess_exec(
                "go", "build", "-o", "firemode-go-service", "main.go",
                cwd=self.service_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Go service build failed: {stderr.decode()}")
                return False
                
            logger.info("Go service build completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Build process failed: {e}")
            return False
    
    async def _health_check(self) -> bool:
        """Perform health check on the Go service."""
        try:
            async with httpx.AsyncClient(timeout=self.health_check_timeout) as client:
                response = await client.get("http://localhost:9091/health")
                return response.status_code == 200
        except Exception:
            return False
    
    async def _monitor_health(self):
        """Monitor Go service health and restart if necessary."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if self._shutdown_event.is_set():
                    break
                
                # Check if process is still alive
                if self.process and self.process.poll() is not None:
                    logger.warning("Go service process has exited unexpectedly")
                    await self._handle_process_failure()
                    continue
                
                # Perform health check
                if not await self._health_check():
                    logger.warning("Go service health check failed")
                    await self._handle_process_failure()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
    
    async def _handle_process_failure(self):
        """Handle process failure with automatic restart."""
        if self.process_info.restart_count >= self.max_restarts:
            logger.error(f"Go service exceeded maximum restart attempts ({self.max_restarts})")
            self.process_info.state = ProcessState.FAILED
            self.process_info.last_error = "Maximum restart attempts exceeded"
            return
        
        self.process_info.restart_count += 1
        logger.info(f"Attempting restart {self.process_info.restart_count}/{self.max_restarts}")
        
        await self._stop_process()
        await asyncio.sleep(self.restart_delay)
        
        if not self._shutdown_event.is_set():
            await self.start()
    
    async def _stop_process(self) -> bool:
        """Stop the process gracefully with fallback to force kill."""
        if not self.process:
            self.process_info.state = ProcessState.STOPPED
            self.process_info.pid = None
            return True
        
        try:
            # Try graceful shutdown first
            if self.process.poll() is None:
                self.process.terminate()
                
                # Wait for graceful shutdown
                try:
                    await asyncio.wait_for(
                        asyncio.create_task(self._wait_for_process()),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("Go service did not shut down gracefully, forcing kill")
                    self.process.kill()
                    await self._wait_for_process()
            
            self.process = None
            self.process_info.state = ProcessState.STOPPED
            self.process_info.pid = None
            logger.info("Go service stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping Go service: {e}")
            return False
    
    async def _wait_for_process(self):
        """Wait for the process to exit."""
        if self.process:
            while self.process.poll() is None:
                await asyncio.sleep(0.1)


# Global instance
go_service_manager: Optional[GoServiceManager] = None


def get_go_service_manager() -> GoServiceManager:
    """Get the global Go service manager instance."""
    global go_service_manager
    if go_service_manager is None:
        service_dir = Path(__file__).parent.parent / "go_service"
        go_service_manager = GoServiceManager(service_dir)
    return go_service_manager