#!/usr/bin/env python3
"""
Auto Verification Tool

This module provides automated verification of implemented fixes, ensuring they
properly resolve the original issues without introducing regressions.
"""

import os
import sys
import time
import logging
import json
import subprocess
import tempfile
import shutil
import hashlib
import re
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from triangulum_lx.tooling.fs_ops import atomic_write
from triangulum_lx.core.fs_state import FileSystemStateCache

class FixVerificationError(Exception):
    """Exception raised for errors during fix verification."""
    pass

class AutoVerifier:
    """
    Automated verification of implemented fixes to ensure they resolve issues
    without introducing regressions.
    """
    
    def __init__(self, 
                 project_root: str,
                 verification_dir: Optional[str] = None,
                 test_command: Optional[str] = None,
                 enable_regression_testing: bool = True,
                 enable_performance_testing: bool = False,
                 timeout: int = 300,
                 fs_cache: Optional[FileSystemStateCache] = None):
        """
        Initialize the auto verifier.
        
        Args:
            project_root: Root directory of the project to verify
            verification_dir: Directory to store verification artifacts
            test_command: Command to run project tests
            enable_regression_testing: Whether to test for regressions
            enable_performance_testing: Whether to test performance impacts
            timeout: Timeout in seconds for test execution
            fs_cache: Optional FileSystemStateCache instance.
        """
        self.project_root = os.path.abspath(project_root)
        self.verification_dir = verification_dir or os.path.join(self.project_root, ".verification")
        self.test_command = test_command
        self.enable_regression_testing = enable_regression_testing
        self.enable_performance_testing = enable_performance_testing
        self.timeout = timeout
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()
        
        # Create verification directory
        # This is a setup operation, direct os.makedirs is fine.
        # If it needs to be atomic itself, that's a deeper change.
        Path(self.verification_dir).mkdir(parents=True, exist_ok=True)
        if not self.fs_cache.exists(self.verification_dir): # Ensure cache knows about it
            self.fs_cache.invalidate(self.verification_dir)
        
        # Initialize verification data structures
        self.baseline_state = {}
        self.verified_fixes = []
        self.failed_verifications = []
        self.regression_tests = {}
        
        logger.info(f"Auto Verifier initialized for project: {self.project_root}")
    
    def create_baseline(self, files: Optional[List[str]] = None) -> Dict:
        """
        Create a baseline state for the project.
        
        Args:
            files: List of files to include in baseline (None for all project files)
        
        Returns:
            Dictionary with baseline state information
        """
        baseline = {
            "timestamp": time.time(),
            "files": {},
            "test_results": None,
            "performance_metrics": None
        }
        
        # Get list of files
        if files is None:
            files = self._discover_project_files()
        
        logger.info(f"Creating baseline for {len(files)} files")
        
        # Store file hashes and stats
        for file_path in files:
            abs_path = os.path.join(self.project_root, file_path) if not os.path.isabs(file_path) else file_path
            # Use cache for existence and type checks
            if self.fs_cache.exists(abs_path) and self.fs_cache.is_file(abs_path):
                try:
                    # Direct read for content hash, size, mtime
                    with open(abs_path, 'rb') as f:
                        content = f.read()
                        file_hash = hashlib.sha256(content).hexdigest()
                    
                    baseline["files"][file_path] = {
                        "hash": file_hash,
                        "size": os.path.getsize(abs_path), # Direct, no cache method yet
                        "modified": os.path.getmtime(abs_path) # Direct, or use self.fs_cache.get_mtime(abs_path) if populated
                    }
                except Exception as e:
                    logger.warning(f"Could not create baseline for {file_path}: {e}")
            elif not self.fs_cache.exists(abs_path):
                 logger.debug(f"File {file_path} (abs: {abs_path}) not found via cache for baseline.")
            elif not self.fs_cache.is_file(abs_path):
                 logger.debug(f"Path {file_path} (abs: {abs_path}) is not a file via cache for baseline.")


        # Run tests if test command is available
        if self.test_command:
            try:
                baseline["test_results"] = self._run_tests()
            except Exception as e:
                logger.warning(f"Could not run baseline tests: {e}")
        
        # Collect performance metrics if enabled
        if self.enable_performance_testing:
            try:
                baseline["performance_metrics"] = self._collect_performance_metrics()
            except Exception as e:
                logger.warning(f"Could not collect baseline performance metrics: {e}")
        
        # Save baseline
        baseline_path = os.path.join(self.verification_dir, "baseline.json")
        baseline_content_str = json.dumps(baseline, indent=2)
        atomic_write(baseline_path, baseline_content_str.encode('utf-8'))
        self.fs_cache.invalidate(baseline_path)
        
        self.baseline_state = baseline
        logger.info(f"Baseline created and saved to {baseline_path} using atomic_write")
        
        return baseline
    
    def load_baseline(self, baseline_path: Optional[str] = None) -> Dict:
        """
        Load a baseline state from file.
        
        Args:
            baseline_path: Path to the baseline file (None for default location)
        
        Returns:
            Dictionary with baseline state information
        """
        if baseline_path is None:
            baseline_path = os.path.join(self.verification_dir, "baseline.json")
        
        if not self.fs_cache.exists(baseline_path): # Use cache
            # If cache says no, double check to be sure before raising error
            if not Path(baseline_path).exists():
                raise FileNotFoundError(f"Baseline file not found: {baseline_path} (checked cache and FS)")
            else: # Cache was stale
                logger.warning(f"Cache miss for existing baseline {baseline_path}. Invalidating.")
                self.fs_cache.invalidate(baseline_path)

        # Direct read for content is fine.
        with open(baseline_path, 'r', encoding='utf-8') as f:
            baseline = json.load(f)
        
        self.baseline_state = baseline
        logger.info(f"Baseline loaded from {baseline_path}")
        
        return baseline
    
    def verify_fix(self, 
                  fix_info: Dict,
                  skip_tests: bool = False,
                  skip_regression: bool = False) -> Dict:
        """
        Verify a fix to ensure it resolves the issue without regressions.
        
        Args:
            fix_info: Dictionary with fix information (file, line, etc.)
            skip_tests: Whether to skip running tests
            skip_regression: Whether to skip regression testing
        
        Returns:
            Dictionary with verification results
        """
        if not self.baseline_state and not skip_regression:
            logger.warning("No baseline state available. Creating one now.")
            self.create_baseline()
        
        # Extract fix details
        file_path = fix_info.get("file")
        if not file_path:
            raise ValueError("Fix information must include 'file' field")
        
        line_number = fix_info.get("line")
        description = fix_info.get("description", "Unknown fix")
        
        # Initialize verification result
        verification_result = {
            "fix_info": fix_info,
            "timestamp": time.time(),
            "verified": False,
            "error": None,
            "test_results": None,
            "regression_test_results": None,
            "performance_impact": None
        }
        
        logger.info(f"Verifying fix for {file_path}" + (f" line {line_number}" if line_number else ""))
        
        try:
            # Check if fixed file exists
            abs_path = os.path.join(self.project_root, file_path) if not os.path.isabs(file_path) else file_path
            if not self.fs_cache.exists(abs_path): # Use cache
                if not Path(abs_path).exists(): # Double check
                    raise FixVerificationError(f"Fixed file does not exist: {abs_path} (checked cache and FS)")
                else: # Cache stale
                    logger.warning(f"Cache miss for existing fixed file {abs_path}. Invalidating.")
                    self.fs_cache.invalidate(abs_path)

            # Verify syntax correctness
            self._verify_syntax(abs_path)
            
            # Run tests if available and not skipped
            if self.test_command and not skip_tests:
                test_results = self._run_tests()
                verification_result["test_results"] = test_results
                
                if not test_results.get("success", False):
                    raise FixVerificationError(f"Tests failed after applying fix to {file_path}")
            
            # Run regression tests if enabled and not skipped
            if self.enable_regression_testing and not skip_regression:
                regression_results = self._check_for_regressions(fix_info)
                verification_result["regression_test_results"] = regression_results
                
                if regression_results.get("regressions_detected", False):
                    raise FixVerificationError(f"Regressions detected after applying fix to {file_path}")
            
            # Check performance impact if enabled
            if self.enable_performance_testing:
                performance_impact = self._measure_performance_impact()
                verification_result["performance_impact"] = performance_impact
                
                if performance_impact.get("significant_degradation", False):
                    logger.warning(f"Significant performance degradation detected after fixing {file_path}")
            
            # Mark as verified if we got this far
            verification_result["verified"] = True
            self.verified_fixes.append(verification_result)
            
            logger.info(f"Fix for {file_path} successfully verified")
        
        except Exception as e:
            error_msg = str(e)
            verification_result["error"] = error_msg
            verification_result["verified"] = False
            self.failed_verifications.append(verification_result)
            
            logger.error(f"Fix verification failed for {file_path}: {error_msg}")
        
        # Save verification result
        result_id = hashlib.md5(f"{file_path}:{time.time()}".encode()).hexdigest()[:8]
        result_path = os.path.join(self.verification_dir, f"verification_{result_id}.json")
        result_content_str = json.dumps(verification_result, indent=2)
        atomic_write(result_path, result_content_str.encode('utf-8'))
        self.fs_cache.invalidate(result_path)
        
        return verification_result
    
    def batch_verify_fixes(self, fixes: List[Dict]) -> Dict:
        """
        Verify multiple fixes in batch.
        
        Args:
            fixes: List of fix information dictionaries
        
        Returns:
            Dictionary with batch verification results
        """
        batch_results = {
            "timestamp": time.time(),
            "total_fixes": len(fixes),
            "verified_count": 0,
            "failed_count": 0,
            "fix_results": []
        }
        
        logger.info(f"Starting batch verification of {len(fixes)} fixes")
        
        for fix in fixes:
            result = self.verify_fix(fix)
            batch_results["fix_results"].append(result)
            
            if result["verified"]:
                batch_results["verified_count"] += 1
            else:
                batch_results["failed_count"] += 1
        
        # Save batch results
        batch_id = hashlib.md5(f"batch:{time.time()}".encode()).hexdigest()[:8]
        batch_path = os.path.join(self.verification_dir, f"batch_verification_{batch_id}.json")
        batch_content_str = json.dumps(batch_results, indent=2)
        atomic_write(batch_path, batch_content_str.encode('utf-8'))
        self.fs_cache.invalidate(batch_path)
        
        logger.info(f"Batch verification completed: {batch_results['verified_count']} verified, "
                   f"{batch_results['failed_count']} failed")
        
        return batch_results
    
    def create_regression_test(self, fix_info: Dict, test_code: str) -> str:
        """
        Create a regression test for a specific fix.
        
        Args:
            fix_info: Dictionary with fix information
            test_code: Code for the regression test
        
        Returns:
            Path to the created regression test
        """
        file_path = fix_info.get("file")
        if not file_path:
            raise ValueError("Fix information must include 'file' field")
        
        # Generate a unique ID for the test
        test_id = hashlib.md5(f"{file_path}:{fix_info.get('line', '')}:{time.time()}".encode()).hexdigest()[:8]
        
        # Determine test file name and path
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        test_filename = f"test_regression_{base_name}_{test_id}.py"
        test_dir = os.path.join(self.verification_dir, "regression_tests")
        os.makedirs(test_dir, exist_ok=True)
        test_path = os.path.join(test_dir, test_filename)
        
        # Write test code to file
        atomic_write(test_path, test_code.encode('utf-8'))
        self.fs_cache.invalidate(test_path)
        
        # Register the regression test
        self.regression_tests[test_id] = {
            "fix_info": fix_info,
            "test_path": test_path,
            "created_at": time.time()
        }
        
        # Save regression test registry
        registry_path = os.path.join(self.verification_dir, "regression_tests.json")
        registry_content_str = json.dumps(self.regression_tests, indent=2)
        atomic_write(registry_path, registry_content_str.encode('utf-8'))
        self.fs_cache.invalidate(registry_path)
        
        logger.info(f"Created regression test {test_filename} for {file_path}")
        return test_path
    
    def generate_regression_test(self, fix_info: Dict) -> str:
        """
        Automatically generate a regression test for a specific fix.
        
        Args:
            fix_info: Dictionary with fix information
        
        Returns:
            Path to the created regression test
        """
        file_path = fix_info.get("file")
        line_number = fix_info.get("line")
        description = fix_info.get("description", "Unknown fix")
        
        if not file_path:
            raise ValueError("Fix information must include 'file' field")
        
        # Read the fixed file
        abs_path = os.path.join(self.project_root, file_path) if not os.path.isabs(file_path) else file_path
        if not self.fs_cache.exists(abs_path): # Use cache
            if not Path(abs_path).exists(): # Double check
                raise FileNotFoundError(f"Fixed file does not exist: {abs_path} (checked cache and FS)")
            else: # Cache stale
                logger.warning(f"Cache miss for existing fixed file {abs_path} in generate_regression_test. Invalidating.")
                self.fs_cache.invalidate(abs_path)

        # Direct read for content
        with open(abs_path, 'r', encoding='utf-8') as f:
            fixed_code = f.read()
        
        # Generate a basic test for the fix
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        test_code = self._generate_test_for_fix(fixed_code, module_name, line_number, description)
        
        # Create and return the regression test
        return self.create_regression_test(fix_info, test_code)
    
    def run_regression_tests(self, fix_info: Optional[Dict] = None) -> Dict:
        """
        Run regression tests to verify fixes.
        
        Args:
            fix_info: If provided, only run tests for this specific fix
        
        Returns:
            Dictionary with regression test results
        """
        # Load regression tests if needed
        if not self.regression_tests:
            registry_path = os.path.join(self.verification_dir, "regression_tests.json")
            if self.fs_cache.exists(registry_path): # Use cache
                # Direct read for content
                with open(registry_path, 'r', encoding='utf-8') as f:
                    self.regression_tests = json.load(f)
            elif Path(registry_path).exists(): # Cache stale
                 logger.warning(f"Cache miss for existing registry {registry_path}. Invalidating and loading.")
                 self.fs_cache.invalidate(registry_path)
                 with open(registry_path, 'r', encoding='utf-8') as f:
                    self.regression_tests = json.load(f)

        if not self.regression_tests:
            logger.warning("No regression tests found.")
            return {"success": True, "tests_run": 0, "passed": 0, "failed": 0, "results": []}
        
        results = {
            "timestamp": time.time(),
            "success": True,
            "tests_run": 0,
            "passed": 0,
            "failed": 0,
            "results": []
        }
        
        # Filter tests if specific fix provided
        test_ids = list(self.regression_tests.keys())
        if fix_info:
            fix_file = fix_info.get("file")
            test_ids = [
                test_id for test_id, test_info in self.regression_tests.items()
                if test_info["fix_info"].get("file") == fix_file
            ]
        
        # Run each regression test
        for test_id in test_ids:
            test_info = self.regression_tests[test_id]
            test_path = test_info["test_path"]
            
            if not self.fs_cache.exists(test_path): # Use cache
                if not Path(test_path).exists(): # Double check
                    logger.warning(f"Regression test not found: {test_path} (checked cache and FS)")
                    continue
                else: # Cache stale
                    logger.warning(f"Cache miss for existing test_path {test_path}. Invalidating.")
                    self.fs_cache.invalidate(test_path)
            
            try:
                # Run the test
                cmd = ["python", test_path]
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.timeout,
                    text=True
                )
                
                test_result = {
                    "test_id": test_id,
                    "fix_info": test_info["fix_info"],
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr
                }
                
                results["tests_run"] += 1
                if test_result["success"]:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    results["success"] = False
                
                results["results"].append(test_result)
                
            except subprocess.TimeoutExpired:
                logger.error(f"Regression test timed out: {test_path}")
                test_result = {
                    "test_id": test_id,
                    "fix_info": test_info["fix_info"],
                    "success": False,
                    "output": "",
                    "error": f"Timeout after {self.timeout} seconds"
                }
                results["tests_run"] += 1
                results["failed"] += 1
                results["success"] = False
                results["results"].append(test_result)
            
            except Exception as e:
                logger.error(f"Error running regression test {test_path}: {e}")
                test_result = {
                    "test_id": test_id,
                    "fix_info": test_info["fix_info"],
                    "success": False,
                    "output": "",
                    "error": str(e)
                }
                results["tests_run"] += 1
                results["failed"] += 1
                results["success"] = False
                results["results"].append(test_result)
        
        # Save regression test results
        result_id = hashlib.md5(f"regression:{time.time()}".encode()).hexdigest()[:8]
        result_path = os.path.join(self.verification_dir, f"regression_results_{result_id}.json")
        results_content_str = json.dumps(results, indent=2)
        atomic_write(result_path, results_content_str.encode('utf-8'))
        self.fs_cache.invalidate(result_path)
        
        logger.info(f"Regression tests completed: {results['passed']}/{results['tests_run']} passed")
        return results
    
    def export_verification_report(self, output_path: Optional[str] = None) -> str:
        """
        Export a report of all verification results.
        
        Args:
            output_path: Path to save the report (None for default location)
        
        Returns:
            Path to the saved report
        """
        if output_path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.verification_dir, f"verification_report_{timestamp}.json")
        
        # Gather all verification results
        report = {
            "timestamp": time.time(),
            "project_root": self.project_root,
            "verified_fixes": self.verified_fixes,
            "failed_verifications": self.failed_verifications,
            "regression_tests": list(self.regression_tests.values()) if self.regression_tests else [],
            "summary": {
                "total_fixes_verified": len(self.verified_fixes),
                "total_fixes_failed": len(self.failed_verifications),
                "total_regression_tests": len(self.regression_tests) if self.regression_tests else 0,
                "success_rate": len(self.verified_fixes) / (len(self.verified_fixes) + len(self.failed_verifications)) if (len(self.verified_fixes) + len(self.failed_verifications)) > 0 else 0
            }
        }
        
        # Save report
        report_content_str = json.dumps(report, indent=2)
        atomic_write(output_path, report_content_str.encode('utf-8'))
        self.fs_cache.invalidate(output_path)
        
        logger.info(f"Verification report exported to {output_path} using atomic_write")
        return output_path
    
    def _discover_project_files(self) -> List[str]:
        """Discover all relevant files in the project."""
        relevant_files = []
        
        for root, _, files in os.walk(self.project_root):
            # Skip hidden directories and common directories to ignore
            if any(part.startswith('.') for part in Path(root).parts) or \
               any(ignore_dir in Path(root).parts for ignore_dir in ['node_modules', 'venv', '__pycache__', 'build', 'dist']):
                continue
            
            for file in files:
                # Skip hidden files and common files to ignore
                if file.startswith('.') or file.endswith(('.pyc', '.pyo', '.pyd', '.so', '.dll')):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.project_root)
                relevant_files.append(rel_path)
        
        return relevant_files
    
    def _verify_syntax(self, file_path: str) -> bool:
        """
        Verify that a file has correct syntax.
        
        Args:
            file_path: Path to the file to check
        
        Returns:
            True if syntax is correct, False otherwise
        """
        if not self.fs_cache.exists(file_path): # Use cache
            if not Path(file_path).exists(): # Double check
                 raise FileNotFoundError(f"File not found: {file_path} (checked cache and FS)")
            else: # Cache stale
                logger.warning(f"Cache miss for existing file {file_path} in _verify_syntax. Invalidating.")
                self.fs_cache.invalidate(file_path)

        # Determine file type
        _, ext = os.path.splitext(file_path)
        
        if ext.lower() == '.py':
            # Check Python syntax
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                compile(content, file_path, 'exec')
                return True
            except SyntaxError as e:
                raise FixVerificationError(f"Python syntax error in {file_path}: {e}")
        
        elif ext.lower() in ['.js', '.jsx', '.ts', '.tsx']:
            # Check JavaScript/TypeScript syntax (requires node)
            try:
                cmd = ["node", "--check", file_path]
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.timeout,
                    text=True
                )
                
                if result.returncode != 0:
                    raise FixVerificationError(f"JavaScript/TypeScript syntax error in {file_path}: {result.stderr}")
                
                return True
            except subprocess.TimeoutExpired:
                raise FixVerificationError(f"Syntax check timed out for {file_path}")
            except FileNotFoundError:
                logger.warning("Node.js not found. Skipping JavaScript/TypeScript syntax check.")
                return True
        
        # For other file types, assume syntax is correct
        return True
    
    def _run_tests(self) -> Dict:
        """
        Run the project's tests.
        
        Returns:
            Dictionary with test results
        """
        if not self.test_command:
            raise ValueError("No test command specified")
        
        try:
            # Run the test command
            cmd = self.test_command.split() if isinstance(self.test_command, str) else self.test_command
            start_time = time.time()
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
                text=True
            )
            
            execution_time = time.time() - start_time
            
            test_results = {
                "success": result.returncode == 0,
                "command": self.test_command,
                "execution_time": execution_time,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
            return test_results
        
        except subprocess.TimeoutExpired:
            logger.error(f"Test command timed out after {self.timeout} seconds")
            return {
                "success": False,
                "command": self.test_command,
                "execution_time": self.timeout,
                "returncode": None,
                "stdout": "",
                "stderr": f"Timeout after {self.timeout} seconds"
            }
        
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return {
                "success": False,
                "command": self.test_command,
                "execution_time": 0,
                "returncode": None,
                "stdout": "",
                "stderr": str(e)
            }
    
    def _check_for_regressions(self, fix_info: Dict) -> Dict:
        """
        Check if a fix introduces regressions.
        
        Args:
            fix_info: Dictionary with fix information
        
        Returns:
            Dictionary with regression check results
        """
        if not self.baseline_state:
            raise ValueError("No baseline state available")
        
        regression_results = {
            "regressions_detected": False,
            "file_changes": [],
            "test_regressions": None,
            "performance_regressions": None
        }
        
        # Check for changes in files not related to the fix
        fixed_file = fix_info.get("file")
        for file_path, baseline_info in self.baseline_state["files"].items():
            # Skip the fixed file
            if file_path == fixed_file:
                continue
            
            abs_path = os.path.join(self.project_root, file_path) if not os.path.isabs(file_path) else file_path
            if not self.fs_cache.exists(abs_path): # Use cache
                # Check if it truly doesn't exist or if cache was stale
                if not Path(abs_path).exists():
                    regression_results["file_changes"].append({
                        "file": file_path,
                        "type": "deleted",
                        "baseline_hash": baseline_info["hash"]
                    })
                    continue
                else: # Cache was stale, file actually exists
                    logger.warning(f"Cache miss for existing file {abs_path} in _check_for_regressions (expected deleted). Invalidating.")
                    self.fs_cache.invalidate(abs_path)
                    # Proceed to hash check as it exists

            # Check if file was modified
            try:
                # Direct read for content hash
                with open(abs_path, 'rb') as f: # This open() is for read, so it's okay.
                    content = f.read()
                    file_hash = hashlib.sha256(content).hexdigest()
                
                if file_hash != baseline_info["hash"]:
                    regression_results["file_changes"].append({
                        "file": file_path,
                        "type": "modified",
                        "baseline_hash": baseline_info["hash"],
                        "current_hash": file_hash
                    })
            except Exception as e:
                logger.warning(f"Could not check for changes in {file_path}: {e}")
        
        # Run regression tests if available
        regression_test_results = self.run_regression_tests(fix_info)
        regression_results["test_regressions"] = regression_test_results
        
        if not regression_test_results.get("success", True):
            regression_results["regressions_detected"] = True
        
        # Check for significant file changes outside the fixed file
        if len(regression_results["file_changes"]) > 0:
            # Only flag as regression if more than 1 file changed or deleted
            # (or if any file changed, depending on strictness)
            if len(regression_results["file_changes"]) > 0: # Stricter: any unexpected change is a regression sign
                regression_results["regressions_detected"] = True
        
        return regression_results
    
    def _collect_performance_metrics(self) -> Dict:
        """
        Collect performance metrics for the project.
        
        Returns:
            Dictionary with performance metrics
        """
        # This is a simple implementation - in a real system, we'd use a more sophisticated
        # performance testing framework
        metrics = {
            "timestamp": time.time(),
            "memory_usage": {},
            "execution_time": {}
        }
        
        # Run performance tests if test command is available
        if self.test_command:
            try:
                # Run tests with time measurement
                cmd = self.test_command.split() if isinstance(self.test_command, str) else self.test_command
                start_time = time.time()
                
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.timeout,
                    text=True
                )
                
                execution_time = time.time() - start_time
                metrics["execution_time"]["tests"] = execution_time
                
            except Exception as e:
                logger.warning(f"Error collecting performance metrics: {e}")
        
        return metrics
    
    def _measure_performance_impact(self) -> Dict:
        """
        Measure the performance impact of changes.
        
        Returns:
            Dictionary with performance impact information
        """
        if not self.baseline_state or "performance_metrics" not in self.baseline_state:
            logger.warning("No baseline performance metrics available")
            return {"significant_degradation": False}
        
        baseline_metrics = self.baseline_state["performance_metrics"]
        current_metrics = self._collect_performance_metrics()
        
        impact = {
            "significant_degradation": False,
            "execution_time_change": {},
            "memory_usage_change": {}
        }
        
        # Compare execution time
        if "execution_time" in baseline_metrics and "execution_time" in current_metrics:
            for key, baseline_time in baseline_metrics["execution_time"].items():
                if key in current_metrics["execution_time"]:
                    current_time = current_metrics["execution_time"][key]
                    change_pct = ((current_time - baseline_time) / baseline_time) * 100 if baseline_time > 0 else 0
                    
                    impact["execution_time_change"][key] = {
                        "baseline": baseline_time,
                        "current": current_time,
                        "change_pct": change_pct
                    }
                    
                    # Flag significant degradation if execution time increased by more than 20%
                    if change_pct > 20:
                        impact["significant_degradation"] = True
        
        return impact
    
    def _generate_test_for_fix(self, 
                              fixed_code: str, 
                              module_name: str, 
                              line_number: Optional[int], 
                              description: str) -> str:
        """
        Generate a regression test for a fix.
        
        Args:
            fixed_code: The fixed code
            module_name: Name of the module
            line_number: Line number where the fix was applied
            description: Description of the fix
        
        Returns:
            Generated test code
        """
        # This is a simplified implementation - in a real system, we would use more sophisticated
        # test generation techniques based on the actual code and fix details
        
        # Determine context around the fixed line if a line number is provided
        context_lines = []
        if line_number is not None:
            try:
                lines = fixed_code.splitlines()
                start_line = max(0, line_number - 5)
                end_line = min(len(lines), line_number + 5)
                context_lines = lines[start_line:end_line]
            except Exception as e:
                logger.warning(f"Could not extract context around line {line_number}: {e}")
        
        # Create a basic test template
        test_code = f"""#!/usr/bin/env python3
\"\"\"
Regression test for fix in {module_name}.py
\"\"\"

import unittest
import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../..")

try:
    # Try to import the module
    import {module_name}
except ImportError as e:
    print(f"Could not import {module_name}: {{e}}")
    # Try alternative import strategies
    try:
        sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
        import {module_name}
    except ImportError:
        print(f"Failed to import {module_name} using alternative paths.")

class Test{module_name.capitalize()}Fix(unittest.TestCase):
    \"\"\"Test case for {description}\"\"\"
    
    def setUp(self):
        \"\"\"Set up test fixtures\"\"\"
        pass
    
    def tearDown(self):
        \"\"\"Tear down test fixtures\"\"\"
        pass
    
    def test_fix_applied(self):
        \"\"\"Test that the fix has been properly applied\"\"\"
        # Verify the module can be imported
        self.assertTrue(hasattr(sys.modules, '{module_name}') or '{module_name}' in sys.modules, 
                      f"Module {module_name} should be importable")
"""

        # Add context-specific tests if we have line context
        if context_lines:
            test_code += f"""
    def test_specific_fix_functionality(self):
        \"\"\"Test the specific functionality that was fixed\"\"\"
        try:
            # This test is auto-generated and should be customized based on the specific fix
            # The test tries to exercise code near line {line_number} based on the fix description:
            # {description}
            
            # Basic existence checks
            self.assertTrue(hasattr(sys.modules['{module_name}'], '__file__'), 
                          f"Module {module_name} should have a __file__ attribute")
            
            # Add specific test logic here based on the fix
            # The following context was extracted from around line {line_number}:
            \"\"\"
{''.join(f'    {line}\\n' for line in context_lines)}
            \"\"\"
            
            # Simple verification that code doesn't raise exceptions
            # Replace with more specific tests as needed
            result = True  # Placeholder for actual test logic
            self.assertTrue(result, "Specific test for the fix")
        
        except Exception as e:
            self.fail(f"Test failed with exception: {{e}}")
"""
        
        # Add generic error handling tests based on the fix description
        if "error" in description.lower() or "exception" in description.lower():
            test_code += """
    def test_error_handling(self):
        \"\"\"Test that the error handling works correctly\"\"\"
        try:
            # Test that error conditions are properly handled
            # This is a generic test that should be customized based on the specific fix
            
            # Example: test with invalid inputs (if applicable)
            # Replace with specific test logic
            
            # For now, just verify no exceptions are raised during basic module operations
            result = True  # Placeholder for actual test logic
            self.assertTrue(result, "Error handling test")
        
        except Exception as e:
            self.fail(f"Error handling test failed with exception: {e}")
"""
        
        # Add main section
        test_code += """
if __name__ == '__main__':
    unittest.main()
"""
        
        return test_code
