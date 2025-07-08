# PH1-BF3.T1 - Fix Bug Detector Folder Analysis

## Objective
Implement the detect_bugs_in_folder method in BugDetectorAgent to enable folder-level bug detection

## Files to touch / create
- triangulum_lx/agents/bug_detector_agent.py
- tests/unit/test_bug_detector_agent.py (if needed)

## Definition-of-Done checklist
- [x] Implement detect_bugs_in_folder method in BugDetectorAgent
- [x] Add proper handling in _handle_task_request for 'detect_bugs_in_folder' action
- [x] Include recursive file traversal with configurable depth
- [x] Add file filtering based on language/extension
- [x] Add error handling for invalid folder paths
- [x] Add proper logging for folder analysis progress
- [x] Verify method returns expected bug analysis results

## Test strategy
- Verify folder path validation works properly
- Test recursive and non-recursive traversal options
- Confirm proper handling of large files and unsupported file types
- Validate bug detection across multiple files in a folder
- Test integration with OrchestratorAgent

## Risk flags & dependencies
- Critical for folder-level self-healing functionality
- Required by OrchestratorAgent for multi-file repairs
- Must handle large codebases efficiently
- Dependent on existing bug detection patterns and algorithms
