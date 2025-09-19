"""
Robust Process Management Supervisor for FireMode Compliance Platform.

This module provides comprehensive process supervision including:
- Automatic service restarts on failure
- Health monitoring and recovery
- Signal handling for graceful shutdowns
- Process coordination between Python and Go services
"""

import subprocess
import signal
import sys
import time
import os
import threading
import logging
from pathlib import Path
from typing import Dict, Optional, Callable


logger = logging.getLogger(__name__)


class ProcessManager:
    """
    Comprehensive process manager for hybrid Python+Go architecture.
    
    Manages the entire service stack with automatic restart capabilities,
    health monitoring, and graceful shutdown handling.
    """
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.running = True
        self.restart_counts: Dict[str, int] = {}
        self.max_restarts = 5
        self.restart_delay = 2.0
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    def build_go_service(self) -> bool:
        """
        Build the Go service binary.
        
        Returns:
            True if build successful, False otherwise
        """
        logger.info("Building Go service...")
        
        try:
            # Determine paths
            go_service_dir = Path(__file__).parent.parent / "go_service"
            if not go_service_dir.exists():
                logger.error(f"Go service directory not found: {go_service_dir}")
                return False
            
            # Create bin directory if it doesn't exist
            bin_dir = Path.cwd() / "bin"
            bin_dir.mkdir(exist_ok=True)
            
            # Build Go service
            result = subprocess.run(
                ["go", "build", "-o", str(bin_dir / "go_service"), "./main.go"],
                cwd=go_service_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Go service build failed: {result.stderr}")
                return False
                
            logger.info("Go service built successfully")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Go service build timed out")
            return False
        except Exception as e:
            logger.error(f"Go service build error: {e}")
            return False
    
    def start_service(self, name: str, command: list, health_check: Optional[Callable] = None):
        """
        Start a service with automatic restart capability.
        
        Args:
            name: Service name for identification
            command: Command list to execute
            health_check: Optional health check function
        """
        def run_service():
            self.restart_counts[name] = 0
            
            while self.running:
                if self.restart_counts[name] >= self.max_restarts:
                    logger.error(f"{name} exceeded maximum restart attempts ({self.max_restarts})")
                    break
                
                try:
                    logger.info(f"Starting {name}...")
                    proc = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    self.processes[name] = proc
                    
                    # Wait for process completion
                    return_code = proc.wait()
                    
                    if self.running:
                        # Process exited unexpectedly
                        stdout, stderr = proc.communicate()
                        logger.error(f"{name} crashed with return code {return_code}")
                        if stderr:
                            logger.error(f"{name} stderr: {stderr}")
                        
                        self.restart_counts[name] += 1
                        logger.info(f"Restarting {name} in {self.restart_delay} seconds... (attempt {self.restart_counts[name]}/{self.max_restarts})")
                        time.sleep(self.restart_delay)
                    else:
                        # Normal shutdown
                        break
                        
                except Exception as e:
                    logger.error(f"Error starting {name}: {e}")
                    if self.running:
                        self.restart_counts[name] += 1
                        time.sleep(self.restart_delay)
                    else:
                        break
            
            logger.info(f"{name} service thread terminated")
        
        # Start service in a separate thread
        thread = threading.Thread(target=run_service, daemon=True, name=f"{name}-thread")
        self.threads[name] = thread
        thread.start()
    
    def stop_service(self, name: str) -> bool:
        """
        Stop a specific service gracefully.
        
        Args:
            name: Service name to stop
            
        Returns:
            True if stopped successfully
        """
        if name not in self.processes:
            logger.warning(f"Service {name} not found in processes")
            return True
        
        proc = self.processes[name]
        if proc.poll() is None:  # Process is still running
            logger.info(f"Stopping {name}...")
            
            try:
                # Try graceful termination first
                proc.terminate()
                
                # Wait for graceful shutdown
                try:
                    proc.wait(timeout=10)
                    logger.info(f"{name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    logger.warning(f"Force killing {name}")
                    proc.kill()
                    proc.wait()
                
                return True
                
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
                return False
        
        return True
    
    def signal_handler(self, signum, frame):
        """
        Handle shutdown signals gracefully.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name}, shutting down services...")
        
        self.running = False
        
        # Stop all services
        for name in list(self.processes.keys()):
            self.stop_service(name)
        
        # Wait for threads to finish
        for name, thread in self.threads.items():
            if thread.is_alive():
                logger.info(f"Waiting for {name} thread to finish...")
                thread.join(timeout=5)
        
        logger.info("All services stopped. Exiting.")
        sys.exit(0)
    
    def check_environment(self) -> bool:
        """
        Check that required environment variables and dependencies are available.
        
        Returns:
            True if environment is ready
        """
        logger.info("Checking environment...")
        
        # Check required environment variables
        required_env_vars = [
            "DATABASE_URL",
            "JWT_SECRET_KEY"
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            return False
        
        # Check for Go binary
        if not os.path.exists("bin/go_service"):
            logger.warning("Go service binary not found, will attempt to build")
        
        logger.info("Environment check passed")
        return True
    
    def run(self):
        """
        Main entry point to start the process manager.
        
        Coordinates the startup of all services and manages their lifecycle.
        """
        logger.info("Starting FireMode Compliance Platform Process Manager")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # Environment check
            if not self.check_environment():
                logger.error("Environment check failed")
                sys.exit(1)
            
            # Build Go service
            if not self.build_go_service():
                logger.error("Failed to build Go service")
                sys.exit(1)
            
            # Start Go service first (Python service depends on it)
            self.start_service("go_service", ["./bin/go_service"])
            
            # Give Go service time to start
            logger.info("Waiting for Go service to initialize...")
            time.sleep(3)
            
            # Start Python FastAPI service
            python_command = [
                "python", "-m", "uvicorn",
                "src.app.main:app",
                "--host", "0.0.0.0",
                "--port", "5000",
                "--log-level", "info"
            ]
            
            # Add reload in development
            if os.getenv("ENVIRONMENT") == "development":
                python_command.append("--reload")
            
            self.start_service("python_service", python_command)
            
            logger.info("All services started. Process manager running...")
            
            # Keep main thread alive and monitor services
            while self.running:
                time.sleep(1)
                
                # Optional: Add health checks here
                # self.perform_health_checks()
        
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt")
            self.signal_handler(signal.SIGINT, None)
        except Exception as e:
            logger.error(f"Process manager error: {e}")
            self.signal_handler(signal.SIGTERM, None)
    
    def perform_health_checks(self):
        """
        Perform health checks on running services.
        
        This can be expanded to include HTTP health checks,
        process monitoring, resource usage checks, etc.
        """
        # Check if processes are still alive
        for name, proc in list(self.processes.items()):
            if proc.poll() is not None:
                logger.warning(f"Process {name} has died (return code: {proc.returncode})")


def main():
    """Main entry point for the supervisor."""
    try:
        manager = ProcessManager()
        manager.run()
    except Exception as e:
        logger.error(f"Supervisor failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()