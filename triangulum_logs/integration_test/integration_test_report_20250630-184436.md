# Triangulum Integration Test Report

Generated: 2025-06-30 18:52:55

## Summary

- Total tests: 3
- Tests passed: 2
- Success rate: 0.67

## Test Results

### Test 1: test_bug.py - PASSED

- Description: Simple test bug
- Expected success: True
- Actual success: True
- Log file: triangulum_logs\integration_test\integrated_test_test_bug_20250630-184436.log

### Test 2: event_loop_bug.py - PASSED

- Description: Asyncio event loop bug
- Expected success: True
- Actual success: True
- Log file: triangulum_logs\integration_test\integrated_test_event_loop_bug_20250630-184436.log

### Test 3: file_resource_bug.py - FAILED

- Description: File resource leak
- Expected success: True
- Actual success: False
- Log file: triangulum_logs\integration_test\integrated_test_file_resource_bug_20250630-184436.log

## Conclusion

Some tests failed. The system was able to fix 2 out of 3 bugs.

See individual log files for detailed information about each test run.
