"""
Canary test runner for Triangulum.

Runs canary tests in an isolated environment to verify patches before full deployment.
"""

import subprocess
import time
import os
import docker
import logging
import tempfile
import shutil
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# Setup logging
logger = logging.getLogger("triangulum.canary")


class CanaryRunner:
    """
    Runs a canary test in an isolated Docker environment.
    
    This ensures that patches can be tested in a clean environment
    before being fully deployed.
    """
    
    def __init__(self, 
                project_path: Union[str, Path],
                image_name: str = "triangulum-canary",
                port_mapping: Dict[int, int] = None,
                health_endpoint: str = "/health",
                health_port: int = 8080):
        """
        Initialize the canary runner.
        
        Args:
            project_path: Path to the project to test
            image_name: Name for the Docker image
            port_mapping: Dictionary mapping container ports to host ports
            health_endpoint: Path for health check
            health_port: Port for health check
        """
        self.project_path = Path(project_path)
        self.image_name = image_name
        self.port_mapping = port_mapping or {8080: 8080}
        self.health_endpoint = health_endpoint
        self.health_port = health_port
        
        # Docker client
        self.client = docker.from_env()
        self.container = None
        
        # Prepare temporary working directory
        self.temp_dir = None
    
    def _setup_environment(self) -> Path:
        """
        Set up the environment for canary testing.
        
        Returns:
            Path to the temporary directory
        """
        # Create a temporary directory for the canary
        self.temp_dir = tempfile.mkdtemp(prefix="triangulum_canary_")
        temp_path = Path(self.temp_dir)
        
        # Copy the project to the temporary directory
        for item in self.project_path.glob("*"):
            if item.is_dir():
                shutil.copytree(item, temp_path / item.name)
            else:
                shutil.copy2(item, temp_path / item.name)
        
        logger.info(f"Prepared canary environment in {temp_path}")
        return temp_path
    
    def _build_docker_image(self, path: Path) -> bool:
        """
        Build Docker image for the canary test.
        
        Args:
            path: Path to the project directory
            
        Returns:
            bool: True if the image was built successfully
        """
        # Check if Dockerfile exists
        dockerfile_path = path / "Dockerfile"
        if not dockerfile_path.exists():
            logger.error("Dockerfile not found in project directory")
            return False
        
        try:
            # Build Docker image
            image, logs = self.client.images.build(
                path=str(path),
                tag=self.image_name,
                rm=True
            )
            logger.info(f"Built Docker image: {self.image_name}")
            return True
            
        except docker.errors.BuildError as e:
            logger.error(f"Docker build error: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Error building Docker image: {e}")
            return False
    
    def _spin_up(self) -> bool:
        """
        Spin up the Docker container for canary testing.
        
        Returns:
            bool: True if the container was started successfully
        """
        try:
            # Create port mappings
            ports = {}
            for container_port, host_port in self.port_mapping.items():
                ports[f"{container_port}/tcp"] = host_port
            
            # Run the container
            self.container = self.client.containers.run(
                self.image_name,
                detach=True,
                ports=ports,
                remove=True,
                auto_remove=True
            )
            
            logger.info(f"Started canary container {self.container.id[:12]}")
            return True
            
        except docker.errors.ImageNotFound:
            logger.error(f"Docker image not found: {self.image_name}")
            return False
            
        except Exception as e:
            logger.error(f"Error starting canary container: {e}")
            return False
    
    def _health_check(self) -> bool:
        """
        Check if the canary container is healthy.
        
        Returns:
            bool: True if the container is healthy
        """
        if not self.container:
            return False
            
        try:
            # Check container state
            self.container.reload()
            if self.container.status != "running":
                logger.warning(f"Container is not running: {self.container.status}")
                return False
            
            # Use curl to check health endpoint
            host_port = self.port_mapping.get(self.health_port, self.health_port)
            curl_cmd = [
                "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                f"http://localhost:{host_port}{self.health_endpoint}"
            ]
            
            result = subprocess.run(curl_cmd, capture_output=True, text=True)
            
            # Check if status code is 200-299 (success)
            status_code = result.stdout.strip()
            is_healthy = status_code.startswith("2")
            
            if is_healthy:
                logger.info(f"Health check passed: {status_code}")
            else:
                logger.warning(f"Health check failed: {status_code}")
                
            return is_healthy
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return False
    
    def run(self, window_sec: int = 90) -> bool:
        """
        Run the canary test.
        
        Args:
            window_sec: Time window in seconds to wait for health checks
            
        Returns:
            bool: True if the canary test passed
        """
        try:
            # Setup environment
            temp_path = self._setup_environment()
            
            # Build Docker image
            if not self._build_docker_image(temp_path):
                logger.error("Failed to build canary Docker image")
                return False
            
            # Start container
            if not self._spin_up():
                logger.error("Failed to start canary container")
                return False
            
            # Wait for container to start and become healthy
            deadline = time.time() + window_sec
            while time.time() < deadline:
                if self._health_check():
                    logger.info("Canary test passed")
                    return True
                time.sleep(3)
            
            logger.error(f"Canary test timed out after {window_sec} seconds")
            return False
            
        except Exception as e:
            logger.error(f"Canary test failed: {e}")
            return False
            
        finally:
            # Cleanup
            self._cleanup()
    
    def _cleanup(self) -> None:
        """Clean up resources used by the canary test."""
        try:
            # Stop container if running
            if self.container:
                try:
                    self.container.stop(timeout=5)
                    logger.info(f"Stopped canary container {self.container.id[:12]}")
                except Exception as e:
                    logger.warning(f"Error stopping container: {e}")
            
            # Remove temp directory
            if self.temp_dir and Path(self.temp_dir).exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"Removed temporary directory {self.temp_dir}")
                
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")


def run_canary_test(project_path: str, 
                   timeout_sec: int = 90, 
                   port_mapping: Dict[int, int] = None) -> Dict[str, Any]:
    """
    Run a canary test on the specified project.
    
    Args:
        project_path: Path to the project to test
        timeout_sec: Timeout in seconds
        port_mapping: Dictionary mapping container ports to host ports
        
    Returns:
        Dict with test results
    """
    # Configure default port mapping if none provided
    if port_mapping is None:
        port_mapping = {8080: 8080}
    
    # Create and run canary
    canary = CanaryRunner(
        project_path=project_path,
        port_mapping=port_mapping
    )
    
    start_time = time.time()
    success = canary.run(window_sec=timeout_sec)
    duration = time.time() - start_time
    
    # Return results
    return {
        "success": success,
        "duration_seconds": round(duration, 2),
        "timeout_seconds": timeout_sec,
        "timestamp": time.time()
    }
