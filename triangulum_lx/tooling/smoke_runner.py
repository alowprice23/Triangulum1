"""
Smoke test runner for Triangulum.

Runs smoke tests against the canary container to verify basic functionality.
"""

import logging
import time
import requests
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from .test_runner import run_tests, run_pytest, run_npm_test, TestResult
from .canary_runner import CanaryRunner

# Setup logging
logger = logging.getLogger("triangulum.smoke_runner")


class SmokeTestRunner:
    """
    Runs smoke tests to verify basic functionality.
    
    Smoke tests are lightweight tests that verify the application is
    working at a basic level after changes have been made.
    """
    
    def __init__(self, 
                project_path: Union[str, Path],
                smoke_tests_path: str = "tests/smoke",
                config_path: Optional[str] = None):
        """
        Initialize the smoke test runner.
        
        Args:
            project_path: Path to the project
            smoke_tests_path: Path to smoke tests
            config_path: Path to smoke test configuration
        """
        self.project_path = Path(project_path)
        self.smoke_tests_path = smoke_tests_path
        self.config_path = config_path
        
        # Load configuration if provided
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load smoke test configuration.
        
        Returns:
            Dict with configuration
        """
        config = {
            "endpoints": [],
            "commands": [],
            "default_timeout": 30
        }
        
        if self.config_path:
            try:
                config_path = Path(self.config_path)
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        custom_config = json.load(f)
                    config.update(custom_config)
                    logger.info(f"Loaded smoke test configuration from {config_path}")
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
        
        return config
    
    def _check_endpoints(self) -> bool:
        """
        Check that critical endpoints are responding.
        
        Returns:
            bool: True if all endpoints are responsive
        """
        if not self.config["endpoints"]:
            logger.info("No endpoints defined for smoke test")
            return True
        
        success = True
        for endpoint in self.config["endpoints"]:
            url = endpoint.get("url")
            method = endpoint.get("method", "GET")
            timeout = endpoint.get("timeout", self.config["default_timeout"])
            expected_status = endpoint.get("expected_status", 200)
            
            if not url:
                continue
                
            try:
                logger.info(f"Checking endpoint: {method} {url}")
                response = requests.request(
                    method=method,
                    url=url,
                    timeout=timeout
                )
                
                if response.status_code == expected_status:
                    logger.info(f"Endpoint check passed: {url} ({response.status_code})")
                else:
                    logger.warning(f"Endpoint check failed: {url} "
                                  f"(got {response.status_code}, expected {expected_status})")
                    success = False
                    
            except requests.RequestException as e:
                logger.error(f"Error checking endpoint {url}: {e}")
                success = False
                
        return success
    
    def _run_commands(self) -> bool:
        """
        Run smoke test commands.
        
        Returns:
            bool: True if all commands succeeded
        """
        if not self.config["commands"]:
            logger.info("No commands defined for smoke test")
            return True
        
        success = True
        for command in self.config["commands"]:
            cmd = command.get("command")
            cwd = command.get("cwd", str(self.project_path))
            timeout = command.get("timeout", self.config["default_timeout"])
            
            if not cmd:
                continue
                
            try:
                logger.info(f"Running command: {cmd}")
                result = subprocess.run(
                    cmd,
                    shell=True,
                    text=True,
                    capture_output=True,
                    cwd=cwd,
                    timeout=timeout
                )
                
                if result.returncode == 0:
                    logger.info(f"Command succeeded: {cmd}")
                else:
                    logger.warning(f"Command failed: {cmd} (exit code {result.returncode})")
                    logger.debug(f"Command output: {result.stdout}")
                    logger.debug(f"Command error: {result.stderr}")
                    success = False
                    
            except subprocess.TimeoutExpired:
                logger.error(f"Command timed out after {timeout}s: {cmd}")
                success = False
                
            except Exception as e:
                logger.error(f"Error running command {cmd}: {e}")
                success = False
                
        return success
    
    def _run_pytest_smoke(self) -> TestResult:
        """
        Run pytest smoke tests.
        
        Returns:
            TestResult with results
        """
        smoke_tests = Path(self.project_path) / self.smoke_tests_path
        if not smoke_tests.exists():
            logger.info(f"No smoke tests found at {smoke_tests}")
            return TestResult(passed=0, failed=0)
        
        logger.info(f"Running smoke tests at {smoke_tests}")
        result_dict = run_pytest(str(smoke_tests))
        
        # Convert to TestResult object if it's a dictionary
        if isinstance(result_dict, dict):
            return TestResult.from_dict(result_dict)
        else:
            logger.error(f"Unexpected result type from run_pytest: {type(result_dict)}")
            return TestResult(passed=0, failed=1)
    
    def run(self) -> Dict[str, Any]:
        """
        Run all smoke tests.
        
        Returns:
            Dict with smoke test results
        """
        start_time = time.time()
        
        # Run the different smoke test types
        endpoint_results = self._check_endpoints()
        command_results = self._run_commands()
        pytest_results = self._run_pytest_smoke()
        
        # Combine results
        duration = time.time() - start_time
        overall_success = (endpoint_results and 
                          command_results and 
                          pytest_results.success)
        
        # Compile results
        results = {
            "success": overall_success,
            "duration_seconds": round(duration, 2),
            "endpoints_success": endpoint_results,
            "commands_success": command_results,
            "pytest_results": pytest_results.to_dict(),
            "timestamp": time.time()
        }
        
        # Log summary
        if overall_success:
            logger.info("All smoke tests passed!")
        else:
            logger.warning("Some smoke tests failed")
        
        return results


def run_smoke(project_path: Union[str, Path] = ".",
             config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Run smoke tests for a project.
    
    Args:
        project_path: Path to the project
        config_path: Path to smoke test configuration file
    
    Returns:
        Dict with smoke test results
    """
    logger.info(f"Starting smoke tests for {project_path}")
    
    runner = SmokeTestRunner(
        project_path=project_path,
        config_path=config_path
    )
    
    return runner.run()


def run_smoke_with_canary(project_path: Union[str, Path] = ".",
                         timeout_sec: int = 120,
                         port_mapping: Dict[int, int] = None) -> Dict[str, Any]:
    """
    Run smoke tests in a canary environment.
    
    This combines the canary runner with smoke tests to provide
    a complete verification of changes in an isolated environment.
    
    Args:
        project_path: Path to the project
        timeout_sec: Timeout in seconds
        port_mapping: Dictionary mapping container ports to host ports
        
    Returns:
        Dict with test results
    """
    logger.info(f"Starting canary with smoke tests for {project_path}")
    
    # First run the canary
    canary = CanaryRunner(
        project_path=project_path,
        port_mapping=port_mapping
    )
    
    try:
        # Start the canary container
        canary_success = canary.run(window_sec=timeout_sec // 2)
        
        if not canary_success:
            logger.error("Canary startup failed, skipping smoke tests")
            return {
                "success": False,
                "canary_success": False,
                "smoke_tests_run": False,
                "smoke_results": None,
                "timestamp": time.time()
            }
        
        # Now run smoke tests
        smoke_results = run_smoke(project_path)
        
        # Combine results
        return {
            "success": smoke_results["success"],
            "canary_success": True,
            "smoke_tests_run": True,
            "smoke_results": smoke_results,
            "timestamp": time.time()
        }
    
    except Exception as e:
        logger.error(f"Error in combined canary and smoke test: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }
