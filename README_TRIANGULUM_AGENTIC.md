# Triangulum Agentic System

## Overview

Triangulum is a powerful, fully agentic system with LLM-powered components that communicate and coordinate autonomously to analyze, detect, and repair code issues. The system uses a network of specialized agents working together through a structured message bus and thought chain system to provide sophisticated code analysis and repair capabilities.

## Key Features

- **Multi-Agent Architecture**: Network of specialized LLM-powered agents that collaborate to solve complex problems
- **Autonomous Decision Making**: Agents make context-aware decisions using advanced reasoning capabilities
- **Inter-Agent Communication**: Robust message passing through the enhanced message bus
- **Thought Chain Preservation**: Reasoning context maintained across agent interactions
- **Real-Time Progress Visibility**: Comprehensive visualization of all internal agent activities
- **Interactive Dashboard**: Multi-view visualization of agent thoughts, communication, and decision-making
- **Adaptive Learning**: System learns from past repairs to improve future recommendations
- **FixWurx Integration**: Full support for analyzing and repairing the FixWurx codebase
- **Quantum-Inspired Acceleration**: Optional quantum computing simulation for accelerated analysis

## Agentic Components

Triangulum consists of the following specialized LLM-powered agents:

- **Orchestrator Agent**: Coordinates all other agents and manages the overall workflow
- **Bug Detector Agent**: Identifies bugs and issues in code using multiple detection strategies
- **Relationship Analyst Agent**: Analyzes code relationships and dependencies
- **Verification Agent**: Validates code changes and tests bug fixes
- **Priority Analyzer Agent**: Determines the importance and urgency of tasks
- **Code Fixer Agent**: Applies repairs while maintaining code consistency

These agents communicate through the Enhanced Message Bus and maintain reasoning context via Thought Chains, enabling sophisticated problem-solving through collaborative intelligence.

## Agentic Dashboard

The Agentic Dashboard provides comprehensive visibility into all internal LLM agent activities:

### Thought Chain Visualization
- Shows the reasoning processes of each agent
- Displays how thoughts connect and develop over time
- Categorizes thoughts by type (analysis, decision, discovery, etc.)
- Updates in real-time as agents generate new thoughts

### Agent Network Visualization
- Displays the communication patterns between agents
- Shows message flow and interaction in real-time
- Supports filtering by message type, agent, or time period
- Provides detailed message content on demand

### Decision Tree Visualization
- Reveals the decision-making processes of agents
- Shows alternatives considered and paths not taken
- Displays confidence levels for different decision points
- Supports interactive exploration of complex decisions

### Progress Tracking
- Provides real-time updates on all agent operations
- Shows percentage completion and ETA for long-running tasks
- Displays current activity for each agent
- Identifies bottlenecks and stalled operations

### Timeline View
- Shows chronological progression of system activities
- Integrates thoughts and messages in a unified view
- Provides temporal context for agent actions
- Supports filtering and zooming for detailed analysis

## Running the System

### Dashboard Demo

To run the Agentic Dashboard demo and explore the visualization capabilities:

```bash
python run_agentic_dashboard_demo.py
```

This will launch a browser window with the full dashboard, showing simulated agent activities, thought chains, communication patterns, and decision trees.

### Feedback Handler Demo

To run the Feedback Handler demo which showcases real-time interaction with agents:

```bash
python examples/feedback_handler_demo.py --auto-open
```

This demo allows you to provide feedback to agents through the dashboard interface and see how they respond to user guidance.

### FixWurx Integration

To run the FixWurx repair and verification pipeline:

```bash
python run_triangulum_fixwurx_verify.py
```

This demonstrates how Triangulum's agents work together to analyze and repair issues in the FixWurx codebase, with full visibility into the process through the dashboard.

### Quantum Acceleration Demo

To run the Quantum-Accelerated Code Analyzer demo:

```bash
python examples/quantum_code_analyzer_demo.py --use-quantum
```

This showcases the quantum-inspired acceleration capabilities for code analysis tasks.

## Key Implementation Details

### Progress Visibility

The system provides continuous visibility into internal LLM processing to address the "frozen terminal" problem:

- Real-time progress updates during long-running operations
- Detailed step-by-step visibility into agent processing
- Percentage-based completion tracking with ETA estimates
- Clear indication of current system activity
- Heartbeat signals from internal agent operations
- Visualization of agent reasoning processes during execution

### Dynamic Port Selection

To avoid socket address conflicts, the system implements automatic port selection:

- Random port selection within configurable ranges
- Fallback mechanisms when preferred ports are unavailable
- Clear reporting of selected ports for client connections

### Error Handling and Type Safety

The system includes robust error handling and type checking:

- Defensive programming to handle unexpected data formats
- Graceful degradation when faced with invalid inputs
- Comprehensive error reporting with actionable information
- Recovery mechanisms for various failure scenarios
- Proper exception handling with appropriate fallbacks

## Development and Testing

### Testing the Agentic System

To verify the agentic capabilities, the system includes comprehensive testing:

- **Agent Communication Tests**: Verify message passing between LLM agents
- **Thought Chain Tests**: Validate reasoning preservation across agent boundaries
- **Progress Monitoring Tests**: Ensure continuous visibility of internal operations
- **Dashboard Visualization Tests**: Verify real-time display of agent activities
- **Agentic Reasoning Tests**: Validate complex problem-solving capabilities
- **Error Recovery Tests**: Ensure graceful handling of failure conditions

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing to the Triangulum project.

## Conclusion

Triangulum represents a significant advancement in agentic systems, combining LLM-powered specialized agents with comprehensive visualization capabilities. The system provides a powerful framework for code analysis and repair, with full visibility into all internal agent activities. The dashboard makes the internal "thought processes" of the LLM agents transparent to users, addressing the key challenge of making complex AI systems understandable and trustworthy.
