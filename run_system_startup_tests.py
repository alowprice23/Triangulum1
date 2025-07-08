#!/usr/bin/env python3
"""
Run System Startup Tests

This script runs the system startup unit and integration tests to verify
the startup sequence, error handling, recovery, and health monitoring.
"""

import os
import sys
import unittest
import logging
import argparse
from pathlib import Path


def setup_logging(log_level='INFO'):
    """Set up logging configuration."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )


def run_tests(unit_only=False, integration_only=False, verbose=False):
    """
    Run system startup tests.
    
    Args:
        unit_only: Run only unit tests
        integration_only: Run only integration tests
        verbose: Run tests in verbose mode
    """
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add unit tests
    if not integration_only:
        sys.path.insert(0, os.path.abspath('.'))
        from tests.unit.test_system_startup import TestSystemStartup, TestStartupRecovery
        
        unit_suite = unittest.TestSuite()
        unit_suite.addTest(unittest.makeSuite(TestSystemStartup))
        unit_suite.addTest(unittest.makeSuite(TestStartupRecovery))
        test_suite.addTest(unit_suite)
    
    # Add integration tests
    if not unit_only:
        from tests.integration.test_system_startup_integration import TestSystemStartupIntegration
        
        integration_suite = unittest.TestSuite()
        integration_suite.addTest(unittest.makeSuite(TestSystemStartupIntegration))
        test_suite.addTest(integration_suite)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(test_suite)
    
    # Return exit code based on test result
    return 0 if result.wasSuccessful() else 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run system startup tests')
    
    parser.add_argument('--unit-only', action='store_true',
                        help='Run only unit tests')
    parser.add_argument('--integration-only', action='store_true',
                        help='Run only integration tests')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Run tests in verbose mode')
    parser.add_argument('--log-level', default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set logging level')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    # Run tests
    return run_tests(
        unit_only=args.unit_only,
        integration_only=args.integration_only,
        verbose=args.verbose
    )


if __name__ == '__main__':
    sys.exit(main())
