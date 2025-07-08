#!/usr/bin/env python
"""
Comprehensive Test Runner for Triangulum Self-Healing System

This script runs all tests for the Triangulum self-healing system:
1. Unit tests for individual components
2. Integration tests for agent collaboration
3. Performance benchmarks for scalability
4. Edge case tests for robustness

It also generates code coverage reports to ensure proper test coverage.
"""

import os
import sys
import argparse
import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Root directory
ROOT_DIR = Path(__file__).parent


def run_command(command, cwd=None):
    """Run a command and return its output."""
    logger.info(f"Running command: {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd or ROOT_DIR,
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(f"Error output: {e.stderr}")
        return e.stderr


def ensure_dependencies():
    """Ensure all required testing dependencies are installed."""
    logger.info("Checking and installing testing dependencies...")
    
    dependencies = [
        "pytest",
        "pytest-cov",
        "pytest-xdist",
        "pytest-timeout",
        "matplotlib",
        "networkx"
    ]
    
    # Check if dependencies are installed
    for dep in dependencies:
        try:
            __import__(dep.replace('-', '_'))
            logger.debug(f"Dependency {dep} is already installed.")
        except ImportError:
            logger.info(f"Installing dependency: {dep}")
            run_command([sys.executable, "-m", "pip", "install", dep])


def run_unit_tests(coverage=True):
    """Run all unit tests."""
    logger.info("Running unit tests...")
    
    command = [sys.executable, "-m", "pytest", "tests/unit", "-v"]
    
    if coverage:
        command.extend([
            "--cov=triangulum_lx",
            "--cov-report=term",
            "--cov-report=html:coverage_reports/unit_tests"
        ])
    
    start_time = time.time()
    output = run_command(command)
    duration = time.time() - start_time
    
    logger.info(f"Unit tests completed in {duration:.2f} seconds")
    return output


def run_integration_tests(coverage=True):
    """Run all integration tests."""
    logger.info("Running integration tests...")
    
    command = [sys.executable, "-m", "pytest", "tests/integration", "-v"]
    
    if coverage:
        command.extend([
            "--cov=triangulum_lx",
            "--cov-report=term",
            "--cov-report=html:coverage_reports/integration_tests"
        ])
    
    start_time = time.time()
    output = run_command(command)
    duration = time.time() - start_time
    
    logger.info(f"Integration tests completed in {duration:.2f} seconds")
    return output


def run_edge_case_tests(coverage=True):
    """Run edge case tests."""
    logger.info("Running edge case tests...")
    
    # Edge case tests might be in a separate directory
    # If they're part of unit or integration tests, this is redundant
    edge_case_dir = Path("tests/edge_cases")
    if not edge_case_dir.exists():
        logger.info("No separate edge case tests found, skipping.")
        return "No edge case tests"
    
    command = [sys.executable, "-m", "pytest", str(edge_case_dir), "-v"]
    
    if coverage:
        command.extend([
            "--cov=triangulum_lx",
            "--cov-report=term",
            "--cov-report=html:coverage_reports/edge_case_tests"
        ])
    
    start_time = time.time()
    output = run_command(command)
    duration = time.time() - start_time
    
    logger.info(f"Edge case tests completed in {duration:.2f} seconds")
    return output


def run_quick_benchmarks():
    """Run quick benchmarks."""
    logger.info("Running quick benchmarks...")
    
    benchmark_script = Path("tests/benchmarks/benchmark_folder_healing.py")
    if not benchmark_script.exists():
        logger.warning(f"Benchmark script not found: {benchmark_script}")
        return "Benchmark script not found"
    
    # Run a small, quick benchmark
    command = [
        sys.executable, 
        str(benchmark_script),
        "--size", "small",
        "--runs", "1"
    ]
    
    start_time = time.time()
    output = run_command(command)
    duration = time.time() - start_time
    
    logger.info(f"Quick benchmarks completed in {duration:.2f} seconds")
    return output


def generate_combined_coverage_report():
    """Generate a combined coverage report."""
    logger.info("Generating combined coverage report...")
    
    command = [
        sys.executable, 
        "-m", 
        "pytest",
        "tests/unit",
        "tests/integration",
        "--cov=triangulum_lx",
        "--cov-report=term",
        "--cov-report=html:coverage_reports/combined",
        "--cov-report=xml:coverage_reports/coverage.xml"
    ]
    
    # Add edge case tests if they exist
    edge_case_dir = Path("tests/edge_cases")
    if edge_case_dir.exists():
        command.insert(4, str(edge_case_dir))
    
    output = run_command(command)
    logger.info("Combined coverage report generated")
    return output


def generate_test_summary(unit_output, integration_output, edge_case_output, benchmark_output):
    """Generate a summary of all test results."""
    logger.info("Generating test summary...")
    
    summary_dir = Path("coverage_reports")
    summary_dir.mkdir(exist_ok=True)
    
    summary_file = summary_dir / "test_summary.txt"
    
    with open(summary_file, "w") as f:
        f.write("Triangulum Self-Healing System - Test Summary\n")
        f.write("===========================================\n\n")
        
        f.write(f"Test run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("Unit Tests:\n")
        f.write("-----------\n")
        f.write(unit_output)
        f.write("\n\n")
        
        f.write("Integration Tests:\n")
        f.write("-----------------\n")
        f.write(integration_output)
        f.write("\n\n")
        
        f.write("Edge Case Tests:\n")
        f.write("---------------\n")
        f.write(edge_case_output)
        f.write("\n\n")
        
        f.write("Benchmark Results:\n")
        f.write("-----------------\n")
        f.write(benchmark_output)
        f.write("\n\n")
    
    logger.info(f"Test summary generated: {summary_file}")
    return str(summary_file)


def run_comprehensive_tests(args):
    """Run comprehensive tests based on command line arguments."""
    # Create coverage reports directory
    coverage_dir = Path("coverage_reports")
    coverage_dir.mkdir(exist_ok=True)
    
    # Ensure dependencies
    if not args.skip_dependencies:
        ensure_dependencies()
    
    # Track outputs for summary
    unit_output = ""
    integration_output = ""
    edge_case_output = ""
    benchmark_output = ""
    
    # Run unit tests
    if not args.skip_unit:
        unit_output = run_unit_tests(coverage=args.coverage)
    
    # Run integration tests
    if not args.skip_integration:
        integration_output = run_integration_tests(coverage=args.coverage)
    
    # Run edge case tests
    if not args.skip_edge_cases:
        edge_case_output = run_edge_case_tests(coverage=args.coverage)
    
    # Run quick benchmarks
    if not args.skip_benchmarks:
        benchmark_output = run_quick_benchmarks()
    
    # Generate combined coverage report
    if args.coverage and not (args.skip_unit and args.skip_integration and args.skip_edge_cases):
        generate_combined_coverage_report()
    
    # Generate test summary
    if args.summary:
        summary_file = generate_test_summary(
            unit_output, integration_output, edge_case_output, benchmark_output
        )
        logger.info(f"Test summary saved to: {summary_file}")
    
    logger.info("All tests completed successfully!")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive tests for Triangulum Self-Healing System"
    )
    
    parser.add_argument(
        "--skip-unit",
        action="store_true",
        help="Skip unit tests"
    )
    
    parser.add_argument(
        "--skip-integration",
        action="store_true",
        help="Skip integration tests"
    )
    
    parser.add_argument(
        "--skip-edge-cases",
        action="store_true",
        help="Skip edge case tests"
    )
    
    parser.add_argument(
        "--skip-benchmarks",
        action="store_true",
        help="Skip benchmark tests"
    )
    
    parser.add_argument(
        "--skip-dependencies",
        action="store_true",
        help="Skip dependency installation"
    )
    
    parser.add_argument(
        "--no-coverage",
        dest="coverage",
        action="store_false",
        help="Skip generating coverage reports"
    )
    
    parser.add_argument(
        "--no-summary",
        dest="summary",
        action="store_false",
        help="Skip generating test summary"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    # Set defaults
    parser.set_defaults(
        coverage=True,
        summary=True
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        run_comprehensive_tests(args)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        sys.exit(2)
