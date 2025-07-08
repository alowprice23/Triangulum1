# Triangulum: Advanced Multi-Agent Code Analysis and Repair System

![Triangulum Logo](https://via.placeholder.com/800x200?text=Triangulum)

## Overview

Triangulum is a cutting-edge multi-agent system designed to detect, analyze, and automatically repair issues in code. It leverages a sophisticated network of specialized agents that work together to understand code relationships, identify bugs, prioritize issues, and apply coordinated fixes across multiple files while maintaining code consistency.

## Key Features

- **Multi-Agent Architecture**: Specialized agents for relationship analysis, bug detection, verification, and orchestration
- **Quantum-Inspired Acceleration**: Simulation of quantum computing concepts to accelerate specific operations
- **Learning Capabilities**: Pattern extraction from successful repairs to improve future fixes
- **Folder-Level Repairs**: Coordinated fixes across multiple files with transaction safety
- **Advanced Dependency Analysis**: Sophisticated code relationship tracking and impact analysis
- **Real-time Monitoring**: Dashboard for system status and performance metrics

## System Architecture

Triangulum consists of several interconnected components:

### Core Agent Framework

- **Enhanced Message Bus**: Advanced routing and filtering for agent communication
- **Thought Chain Manager**: Orchestrates reasoning sequences for multi-step problem-solving
- **Orchestrator Agent**: Coordinates activities of specialized agents
- **Priority Analyzer Agent**: Determines importance and urgency of tasks

### Specialized Agents

- **Relationship Analyst Agent**: Analyzes code relationships and dependencies
- **Bug Detector Agent**: Identifies bugs using multiple detection strategies
- **Verification Agent**: Validates code changes and tests bug fixes

### Tooling Components

- **Dependency Graph**: Structured representation of code relationships
- **Incremental Analyzer**: Efficient updates to relationship information
- **Repair Tool**: Applies coordinated fixes across multiple files
- **Rollback Manager**: Ensures changes can be safely reversed if issues occur

### Learning Components

- **Repair Pattern Extractor**: Identifies patterns from successful repairs
- **Feedback Processor**: Analyzes user and test feedback
- **Continuous Improvement**: Adjusts system parameters based on operational experience

### Quantum Components

- **Quantum Parallelizer**: Simulates quantum algorithms for specific operations
- **Quantum Circuit Simulator**: Simulates quantum circuits on classical hardware
- **Quantum Speedup Estimator**: Estimates potential speedup from quantum algorithms

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Required packages (install via `pip install -r requirements.txt`)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-organization/triangulum.git
   cd triangulum
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the setup script:
   ```bash
   python setup.py install
   ```

### Basic Usage

Run the comprehensive demo to see Triangulum in action:

```bash
python run_triangulum_demo.py --test-folder ./example_files
```

Options:
- `--test-folder`: Path to the folder containing code to analyze (default: ./example_files)
- `--no-quantum`: Disable quantum acceleration

### Example Output

```
================================================================================
TRIANGULUM DEMO SUMMARY
================================================================================

Test Folder: ./example_files
Quantum Acceleration: Enabled

Statistics:
  Total Issues Detected: 12
  Repairs Attempted: 10
  Successful Repairs: 8
  Success Rate: 80.0%

Top Issues:
  1. [CRITICAL] NULL_POINTER in null_pointer_example.py:15
     Potential null pointer dereference when accessing 'data' without null check
  2. [HIGH] RESOURCE_LEAK in resource_leak_example.py:8
     Resource leak: file is not closed in all execution paths
  3. [CRITICAL] SQL_INJECTION in sql_injection_example.py:12
     SQL injection vulnerability in user input handling
  4. [MEDIUM] EXCEPTION_SWALLOWING in exception_swallowing_example.py:7
     Exception is caught but not properly handled or logged
  5. [HIGH] HARDCODED_CREDENTIALS in hardcoded_credentials_example.py:5
     Hardcoded credentials detected in source code

  ... and 7 more issues

Report saved to: C:\Users\Yusuf\Downloads\Triangulum\triangulum_demo_output\triangulum_report.json

================================================================================
TRIANGULUM DEMO COMPLETED SUCCESSFULLY
================================================================================
```

## Advanced Usage

### Custom Agent Configuration

You can configure individual agents by modifying their configuration files in the `config/` directory.

### Integration with Existing Systems

Triangulum can be integrated with existing development workflows:

```python
from triangulum_lx.core.learning_enabled_engine import LearningEnabledEngine
from triangulum_lx.agents.orchestrator_agent import OrchestratorAgent

# Initialize the engine
engine = LearningEnabledEngine(
    orchestrator=OrchestratorAgent(...),
    pattern_extractor=RepairPatternExtractor(...),
    feedback_processor=FeedbackProcessor(...),
    continuous_improvement=ContinuousImprovement(...)
)

# Analyze code
results = engine.analyze_folder("/path/to/your/code")

# Apply fixes
repair_results = engine.repair_issues(results["issues"])

# Generate report
report = engine.generate_report(results, repair_results)
```

### Quantum Acceleration

Triangulum includes quantum-inspired algorithms that can accelerate specific operations:

```python
from triangulum_lx.quantum.parallelization import (
    QuantumParallelizer,
    ParallelizationStrategy
)

# Initialize quantum parallelizer
parallelizer = QuantumParallelizer(num_qubits=10)

# Execute a task with quantum acceleration
result = parallelizer.execute_task(
    your_function,
    your_input_data,
    strategy=ParallelizationStrategy.QUANTUM_AMPLITUDE_AMPLIFICATION
)
```

## Contributing

We welcome contributions to Triangulum! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- The Triangulum team for their dedication and innovation
- Contributors to the open-source libraries used in this project
- The quantum computing research community for inspiration

## Contact

For questions, feedback, or support, please contact:
- Email: triangulum-support@example.com
- GitHub Issues: https://github.com/your-organization/triangulum/issues
