"""
Triangulum Test Runner

Provides automated test execution capabilities.
"""

import logging
import subprocess
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

from triangulum_lx.tooling.fs_ops import atomic_write, atomic_delete
from triangulum_lx.core.fs_state import FileSystemStateCache

class TestResult:
    """Result of a test execution."""
    
    def __init__(self, success: bool, message: str, details: Optional[Dict[str, Any]] = None):
        self.success = success
        self.message = message
        self.details = details or {}

class TestRunner:
    """Automated test runner."""
    
    def __init__(self, project_root: str = ".", fs_cache: Optional[FileSystemStateCache] = None):
        self.project_root = Path(project_root)
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()
        logger.info("TestRunner initialized")
    
    def discover_tests(self) -> List[Path]:
        """Discover test files in the project."""
        test_files = []
        
        # Find test files
        test_patterns = ["test_*.py", "*_test.py"]
        for pattern in test_patterns:
            test_files.extend(self.project_root.glob(f"**/{pattern}"))
        
        logger.info(f"Discovered {len(test_files)} test files")
        return test_files
    
    def run_tests(self, test_files: Optional[List[Path]] = None) -> Dict[str, Any]:
        """Run tests and return results."""
        if test_files is None:
            test_files = self.discover_tests()
        
        results = {
            "total_tests": len(test_files),
            "passed": 0,
            "failed": 0,
            "errors": [],
            "success_rate": 0.0
        }
        
        for test_file in test_files:
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pytest", str(test_file), "-v"
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    results["passed"] += 1
                    logger.info(f"✅ {test_file.name} passed")
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "file": str(test_file),
                        "error": result.stderr
                    })
                    logger.error(f"❌ {test_file.name} failed")
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "file": str(test_file),
                    "error": str(e)
                })
                logger.error(f"❌ {test_file.name} error: {e}")
        
        if results["total_tests"] > 0:
            results["success_rate"] = results["passed"] / results["total_tests"]
        
        return results
    
    def run_specific_test(self, test_path: str) -> TestResult:
        """Run a specific test file."""
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", test_path, "-v"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return TestResult(True, f"Test {test_path} passed", {
                    "stdout": result.stdout,
                    "stderr": result.stderr
                })
            else:
                return TestResult(False, f"Test {test_path} failed", {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                })
                
        except Exception as e:
            logger.error(f"Failed to run test {test_path}: {e}")
            return TestResult(False, f"Failed to run test: {str(e)}")
    
    def run_unittest(self, test_path: str) -> TestResult:
        """Run a specific test using unittest module."""
        try:
            result = subprocess.run([
                sys.executable, "-m", "unittest", test_path, "-v"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return TestResult(True, f"Unittest {test_path} passed", {
                    "stdout": result.stdout,
                    "stderr": result.stderr
                })
            else:
                return TestResult(False, f"Unittest {test_path} failed", {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                })
                
        except Exception as e:
            logger.error(f"Failed to run unittest {test_path}: {e}")
            return TestResult(False, f"Failed to run unittest: {str(e)}")
    
    def run_coverage_analysis(self, test_files: Optional[List[Path]] = None) -> Dict[str, Any]:
        """Run tests with coverage analysis."""
        if test_files is None:
            test_files = self.discover_tests()
        
        coverage_results = {
            "coverage_percentage": 0.0,
            "covered_lines": 0,
            "total_lines": 0,
            "missing_lines": [],
            "files_analyzed": []
        }
        
        try:
            # Run tests with coverage
            test_paths = [str(f) for f in test_files]
            result = subprocess.run([
                sys.executable, "-m", "coverage", "run", "-m", "pytest"
            ] + test_paths, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                # Get coverage report
                coverage_report = subprocess.run([
                    sys.executable, "-m", "coverage", "report"
                ], capture_output=True, text=True, timeout=30)
                
                if coverage_report.returncode == 0:
                    # Parse coverage output (simplified)
                    lines = coverage_report.stdout.split('\n')
                    for line in lines:
                        if '%' in line and 'TOTAL' in line:
                            parts = line.split()
                            if len(parts) >= 4:
                                try:
                                    coverage_results["coverage_percentage"] = float(parts[-1].replace('%', ''))
                                except ValueError:
                                    pass
                
                coverage_results["success"] = True
                logger.info(f"Coverage analysis completed: {coverage_results['coverage_percentage']:.1f}%")
            else:
                coverage_results["success"] = False
                coverage_results["error"] = result.stderr
                logger.error(f"Coverage analysis failed: {result.stderr}")
                
        except Exception as e:
            coverage_results["success"] = False
            coverage_results["error"] = str(e)
            logger.error(f"Coverage analysis error: {e}")
        
        return coverage_results
    
    def validate_test_structure(self) -> Dict[str, Any]:
        """Validate the test directory structure."""
        validation_results = {
            "valid_structure": True,
            "issues": [],
            "recommendations": []
        }
        
        # Check for test directories
        test_dirs = [
            self.project_root / "tests",
            self.project_root / "test",
            self.project_root / "tests" / "unit",
            self.project_root / "tests" / "integration"
        ]
        
        existing_dirs = [d for d in test_dirs if d.exists()]
        
        if not existing_dirs:
            validation_results["valid_structure"] = False
            validation_results["issues"].append("No test directories found")
            validation_results["recommendations"].append("Create a 'tests' directory structure")
        
        # Check for __init__.py files in test directories
        for test_dir in existing_dirs:
            if test_dir.is_dir():
                init_file = test_dir / "__init__.py"
                if not init_file.exists():
                    validation_results["issues"].append(f"Missing __init__.py in {test_dir}")
                    validation_results["recommendations"].append(f"Add __init__.py to {test_dir}")
        
        # Check for pytest.ini or setup.cfg
        config_files = [
            self.project_root / "pytest.ini",
            self.project_root / "setup.cfg",
            self.project_root / "pyproject.toml"
        ]
        
        has_config = any(f.exists() for f in config_files)
        if not has_config:
            validation_results["recommendations"].append("Add pytest configuration (pytest.ini or pyproject.toml)")
        
        logger.info(f"Test structure validation: {len(validation_results['issues'])} issues found")
        return validation_results
    
    def generate_test_report(self, test_results: Dict[str, Any]) -> str:
        """Generate a formatted test report."""
        report_lines = [
            "# Test Execution Report",
            f"**Total Tests**: {test_results.get('total_tests', 0)}",
            f"**Passed**: {test_results.get('passed', 0)}",
            f"**Failed**: {test_results.get('failed', 0)}",
            f"**Success Rate**: {test_results.get('success_rate', 0):.1%}",
            ""
        ]
        
        if test_results.get('errors'):
            report_lines.append("## Failed Tests")
            for error in test_results['errors']:
                report_lines.append(f"- **{error['file']}**: {error['error'][:100]}...")
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def validate_patch(self, file_path: str, test_paths: List[str], patch_content: Optional[str] = None) -> TestResult:
        """
        Validate a patch by running tests associated with the file.
        
        This method creates a safe test environment to validate patches before applying them
        permanently, reducing the risk of breaking the codebase.
        
        Args:
            file_path: Path to the file being patched
            test_paths: List of test paths that validate this file's functionality
            patch_content: Optional patch content to apply temporarily for testing
        
        Returns:
            TestResult indicating if the patch passes tests
        """
        logger.info(f"Validating patch for {file_path}")
        
        # Create temporary backup of original file if we have patch content
        temp_backup = None
        if patch_content:
            try:
                import shutil
                import tempfile
                
                # Create temporary backup
                temp_backup_path_str = tempfile.mktemp(suffix='.bak') # Just a name
                temp_backup = Path(temp_backup_path_str)

                original_content = Path(file_path).read_bytes()
                atomic_write(str(temp_backup), original_content)
                self.fs_cache.invalidate(str(temp_backup))
                logger.info(f"Created temporary backup at {temp_backup} using atomic_write")
                
                # Apply temporary patch for testing
                atomic_write(file_path, patch_content.encode('utf-8'))
                self.fs_cache.invalidate(file_path)
                logger.info(f"Applied temporary patch to {file_path} using atomic_write")
                
            except Exception as e:
                logger.error(f"Failed to create temporary test environment for {file_path}: {e}")
                # Try to restore from backup if it was created and if the original file_path was touched
                if temp_backup and self.fs_cache.exists(str(temp_backup)): # Check cache first
                    try:
                        backup_content = temp_backup.read_bytes()
                        atomic_write(file_path, backup_content) # Restore original
                        self.fs_cache.invalidate(file_path)
                        atomic_delete(str(temp_backup)) # Delete backup
                        self.fs_cache.invalidate(str(temp_backup))
                        logger.info(f"Restored {file_path} from temp backup {temp_backup} due to setup error.")
                    except Exception as restore_e:
                        logger.error(f"Critical error: Failed to restore {file_path} from {temp_backup} after setup error: {restore_e}")
                elif temp_backup and temp_backup.exists(): # Fallback direct check
                     try:
                        backup_content = temp_backup.read_bytes()
                        atomic_write(file_path, backup_content)
                        self.fs_cache.invalidate(file_path)
                        atomic_delete(str(temp_backup))
                        self.fs_cache.invalidate(str(temp_backup))
                        logger.info(f"Restored {file_path} from temp backup {temp_backup} (direct check) due to setup error.")
                     except Exception as restore_e:
                        logger.error(f"Critical error: Failed to restore {file_path} from {temp_backup} (direct check) after setup error: {restore_e}")

                return TestResult(False, f"Failed to setup test environment: {str(e)}")
        
        try:
            # Run all tests associated with this file
            all_results = []
            for test_path in test_paths:
                logger.info(f"Running test {test_path} for patch validation")
                result = self.run_specific_test(test_path)
                all_results.append(result)
            
            # Check if all tests passed
            all_passed = all(result.success for result in all_results)
            
            if all_passed:
                message = f"All tests passed for patch on {file_path}"
                logger.info(message)
                result = TestResult(True, message, {
                    "test_results": [r.details for r in all_results]
                })
            else:
                # Find the first failing test for details
                failing_tests = [r for r in all_results if not r.success]
                message = f"{len(failing_tests)} tests failed for patch on {file_path}"
                logger.warning(message)
                result = TestResult(False, message, {
                    "failing_tests": [
                        {"message": r.message, "details": r.details} 
                        for r in failing_tests
                    ]
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error during patch validation: {e}")
            return TestResult(False, f"Error during patch validation: {str(e)}")
            
        finally:
            # Always restore from backup if we applied a temporary patch and backup exists
            if temp_backup and self.fs_cache.exists(str(temp_backup)): # Check cache
                try:
                    backup_content = temp_backup.read_bytes()
                    atomic_write(file_path, backup_content)
                    self.fs_cache.invalidate(file_path)
                    atomic_delete(str(temp_backup))
                    self.fs_cache.invalidate(str(temp_backup))
                    logger.info(f"Restored original file {file_path} from {temp_backup}")
                except Exception as e:
                    logger.error(f"Failed to restore original file {file_path} from {temp_backup}: {e}")
            elif temp_backup and temp_backup.exists(): # Fallback direct check if cache said no but it's there
                logger.warning(f"Temp backup {temp_backup} found by direct check after cache miss. Attempting restore.")
                try:
                    backup_content = temp_backup.read_bytes()
                    atomic_write(file_path, backup_content)
                    self.fs_cache.invalidate(file_path)
                    atomic_delete(str(temp_backup))
                    self.fs_cache.invalidate(str(temp_backup))
                    logger.info(f"Restored original file {file_path} from {temp_backup} (direct check).")
                except Exception as e:
                    logger.error(f"Failed to restore original file {file_path} from {temp_backup} (direct check): {e}")
    
    def find_related_tests(self, file_path: str) -> List[str]:
        """
        Find tests related to a specific file.
        
        Args:
            file_path: Path to the file to find tests for
        
        Returns:
            List of test file paths
        """
        # Get the file name without extension
        file_name = Path(file_path).stem
        
        # Common patterns for test files
        patterns = [
            f"test_{file_name}.py",
            f"{file_name}_test.py",
            f"test*{file_name}*.py"
        ]
        
        related_tests = []
        for pattern in patterns:
            for test_dir in ["tests", "test", "."]:
                search_path = self.project_root / test_dir
                if search_path.exists():
                    matches = list(search_path.glob(f"**/{pattern}"))
                    related_tests.extend([str(m) for m in matches])
        
        # Also look for tests in the same directory
        file_dir = Path(file_path).parent
        for pattern in patterns:
            matches = list(file_dir.glob(pattern))
            related_tests.extend([str(m) for m in matches])
        
        # Remove duplicates
        related_tests = list(set(related_tests))
        
        logger.info(f"Found {len(related_tests)} tests related to {file_path}")
        return related_tests
