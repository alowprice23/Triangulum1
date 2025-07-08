import unittest
import sys
import os

# Add the project root to the path so we can import from triangulum_lx
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
sys.path.insert(0, project_root)

# Import the test class
from tests.unit.test_patcher_agent import TestPatcherAgent

if __name__ == '__main__':
    # Create a test suite with all tests from TestPatcherAgent
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestPatcherAgent)
    
    # Run the tests with a TextTestRunner for detailed output
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    
    # Print summary
    print("\nTest Summary:")
    print(f"Ran {result.testsRun} tests")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    # Print failures details
    if result.failures:
        print("\nFailures:")
        for i, (test, traceback) in enumerate(result.failures):
            print(f"\n--- Failure {i+1} ---")
            print(f"Test: {test}")
            print(f"Traceback: {traceback}")
    
    # Print error details
    if result.errors:
        print("\nErrors:")
        for i, (test, traceback) in enumerate(result.errors):
            print(f"\n--- Error {i+1} ---")
            print(f"Test: {test}")
            print(f"Traceback: {traceback}")
    
    # Set exit code
    if result.wasSuccessful():
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print("\nTests failed")
        sys.exit(1)
