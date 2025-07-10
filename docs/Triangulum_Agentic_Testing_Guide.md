# Triangulum Agentic System Testing Guide

## Overview

This guide provides comprehensive instructions for testing the Triangulum agentic system. The Triangulum system is fundamentally an **AGENTIC SYSTEM with LLM-powered components** that communicate and coordinate tasks. Unlike traditional software, testing an agentic system requires specialized approaches to verify the communication between agents, track internal thought processes, and ensure continuous progress visibility.

## Understanding the Agentic Architecture

Triangulum's architecture consists of multiple specialized LLM agents working together:

1. **Orchestrator Agent**: Coordinates all other agents and manages workflow
2. **Bug Detector Agent**: Identifies potential bugs in code
3. **Relationship Analyst Agent**: Analyzes code relationships and dependencies
4. **Verification Agent**: Validates code changes and tests fixes
5. **Priority Analyzer Agent**: Determines task importance and scheduling

These agents communicate through a structured message bus and maintain their reasoning via thought chains. The key differentiator of Triangulum is that these are not just passive components - they are active agents with internal reasoning processes that can make decisions, learn from experience, and coordinate with each other.

## Core Testing Principles

When testing an agentic system like Triangulum, standard testing approaches are insufficient. You must verify:

1. **Agent Communication**: Ensure agents can properly exchange messages
2. **Thought Chain Persistence**: Verify reasoning processes remain intact across agent boundaries
3. **Progress Visibility**: Confirm continuous progress updates during internal processing
4. **Error Recovery**: Test how agents handle errors and recover from failures
5. **Decision Making**: Validate that agents make appropriate decisions based on context

## Detailed Testing Procedures

### 1. Agent Communication Testing

Use the following approach to test agent communication:

```python
# Example: Testing message passing between agents
def test_agent_communication():
    # Initialize test environment
    test_env = AgenticSystemTester("./test_files")
    test_env.setup()
    
    # Send a test message requiring agent collaboration
    result = test_env.test_agent_communication()
    
    # Verify message exchange
    assert result is True, "Agent communication test failed"
```

Key verification points:
- Messages are correctly routed between agents
- Message content is preserved during transit
- Agents respond appropriately to different message types
- Message history is accurately maintained
- Progress is visible during message processing

### 2. Thought Chain Testing

Thought chains represent the internal reasoning processes of LLM agents. Test them as follows:

```python
# Example: Testing thought chain persistence
def test_thought_chain_persistence():
    # Initialize test environment
    test_env = AgenticSystemTester("./test_files")
    test_env.setup()
    
    # Test multi-agent reasoning
    result = test_env.test_thought_chain_persistence()
    
    # Verify thought chains
    assert result is True, "Thought chain persistence test failed"
```

Key verification points:
- Thought chains include reasoning steps from multiple agents
- Context is preserved across agent boundaries
- Reasoning builds coherently toward solutions
- Thought chains can be visualized and inspected
- Progress is visible during thought chain development

### 3. Progress Visibility Testing

The system must provide continuous feedback during internal processing:

```python
# Example: Testing progress visibility
def test_long_running_operation_visibility():
    # Initialize test environment
    test_env = AgenticSystemTester("./test_files")
    test_env.setup()
    
    # Test visibility during long operations
    result = test_env.test_long_running_operation_visibility()
    
    # Verify progress updates
    assert result is True, "Progress visibility test failed"
```

Key verification points:
- Progress updates occur at regular intervals (< 1 second)
- Progress accurately reflects internal completion percentage
- Each agent provides visibility into its current activity
- Users can see which agent is currently active
- ETA estimates are provided for long-running operations

### 4. Timeout and Cancellation Testing

Test how the system handles interruptions:

```python
# Example: Testing timeout handling
def test_timeout_handling():
    # Initialize test environment
    test_env = AgenticSystemTester("./test_files")
    test_env.setup()
    
    # Test timeout mechanism
    result = test_env.test_timeout_handling()
    
    # Verify proper handling
    assert result is True, "Timeout handling test failed"
```

Key verification points:
- System properly detects and handles timeouts
- Resources are cleaned up after cancellation
- Agents return to idle state after interruption
- Users receive clear feedback about the cancellation
- Progress indicators show the cancellation state

## Test Environment Setup

To properly test the Triangulum agentic system, set up your environment as follows:

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure test files directory:
   ```bash
   mkdir -p test_files
   cp -r example_files/* test_files/
   ```

3. Run the agentic system tests:
   ```bash
   python run_agentic_system_test.py
   ```

## Testing Specific Agent Capabilities

### Testing Bug Detector Agent

The Bug Detector Agent uses LLM reasoning to identify potential bugs:

```bash
python run_agentic_system_test.py --test=bug_detection
```

Verify that:
- The agent correctly identifies bugs in test files
- False positive rate is within acceptable limits
- Agent provides meaningful descriptions of identified issues
- Progress is visible throughout the detection process

### Testing Relationship Analyst Agent

The Relationship Analyst Agent analyzes code dependencies:

```bash
python run_agentic_system_test.py --test=relationship_analysis
```

Verify that:
- Dependencies are correctly identified across files
- Relationship graphs accurately represent code structure
- Analysis depth matches configuration settings
- Progress is visible during relationship analysis

### Testing Orchestrator Coordination

The Orchestrator Agent coordinates other agents:

```bash
python run_agentic_system_test.py --test=orchestration
```

Verify that:
- The orchestrator properly assigns tasks to specialized agents
- Workflow proceeds in a logical and efficient sequence
- System recovers from individual agent failures
- Progress reflects the overall system state

## Addressing Common Testing Challenges

### 1. Apparent System Freezing

If the system appears to freeze during testing, this is typically not a system failure but rather insufficient progress visibility. Check:

- Is the progress monitor properly initialized?
- Are progress callbacks registered for all agents?
- Is the progress update interval appropriate?
- Are agents updating their progress during internal processing?

### 2. Inconsistent Agent Behavior

LLM-powered agents may show some variability in behavior. To test consistently:

- Use fixed seeds for randomized operations
- Create deterministic test scenarios
- Focus on testing outcome correctness rather than exact steps
- Verify progress indicators work regardless of specific agent decisions

### 3. Long-Running Tests

Testing agentic systems often involves long-running operations:

- Use timeouts to prevent indefinite test execution
- Implement cancellation mechanisms for manual interruption
- Add detailed logging throughout the test process
- Monitor progress indicators to confirm system activity

## Visualizing Agent Activities

The Triangulum system provides visualization of agent activities:

```bash
python run_agentic_system_test.py --visualize
```

This generates visualizations showing:
- Agent activity timeline
- Progress over time for different operations
- Inter-agent communication patterns
- Thought chain development

Use these visualizations to verify the agentic nature of the system and ensure proper progress visibility.

## Conclusion

Testing an agentic system like Triangulum requires specialized approaches that focus on agent communication, thought processes, and progress visibility. By following this guide, you can verify that Triangulum's LLM-powered agents are functioning correctly, communicating effectively, and providing continuous progress feedback to users.

Remember that when the system appears to freeze, it's often actually working internally without providing sufficient progress indicators. The enhanced monitoring components now address this issue by ensuring continuous visibility into the system's internal processing.
