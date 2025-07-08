# Triangulum Self-Healing System Testing Framework

This directory contains the comprehensive testing framework for the Triangulum Self-Healing System. The framework is designed to verify the functionality, robustness, performance, and scalability of the system through multiple layers of testing.

## Test Architecture

The testing framework follows a layered approach:

```
tests/
├── unit/                 # Unit tests for individual components
├── integration/          # Integration tests for component interaction
├── edge_cases/           # Tests for unusual or extreme scenarios
├── benchmarks/           # Performance and scalability tests
├── README.md             # This documentation
└── run_comprehensive_tests.py  # Test runner script
```

## Test Categories

### Unit Tests

Unit tests verify the correct behavior of individual components in isolation. Each agent, tool, and utility in the Triangulum system has corresponding unit tests that validate:

- Initialization with various configurations
- Core functionality and business logic
- Edge case handling at the component level
- Error states and recovery

**Key Unit Tests:**
- `test_base_agent.py` - Tests for the base agent class functionality
- `test_bug_detector_agent.py` - Tests for the bug detection capabilities
- `test_priority_analyzer_agent.py` - Tests for prioritization logic
- `test_dependency_graph.py` - Tests for code relationship analysis
- `test_code_relationship_analyzer.py` - Tests for code relationship detection

### Integration Tests

Integration tests verify that components work together correctly. These tests focus on agent interactions, message passing, and workflow coordination.

**Key Integration Tests:**
- `test_triangulum_system.py` - Tests the full system integration
- `test_folder_healing.py` - Tests the folder-level healing workflow
- `test_dependency_analysis.py` - Tests the integration of dependency analysis with other components

### Edge Case Tests

Edge case tests verify the system's robustness when handling unusual or extreme scenarios that might occur in real-world situations.

**Key Edge Case Tests:**
- `test_folder_healing_edge_cases.py` - Tests folder healing with challenging inputs:
  - Empty folders
  - Very large files
  - Files with unusual encodings
  - Corrupted files
  - Circular dependencies
  - Mixed language files
  - Unusual file extensions
  - Deep directory structures
  - Many small files

### Benchmarks

Benchmarks measure the performance and scalability of the system under various conditions, providing insights into system behavior at different scales.

**Key Benchmarks:**
- `benchmark_folder_healing.py` - Measures performance across different project sizes:
  - Small projects (few files)
  - Medium projects (dozens of files)
  - Large projects (hundreds of files)
  - Different types and frequencies of bugs
  - Serial vs. parallel execution modes

## Running Tests

### Using the Comprehensive Test Runner

The `run_comprehensive_tests.py` script provides a unified interface for running all tests and generating reports.

**Basic Usage:**
```bash
python run_comprehensive_tests.py
```

This will:
1. Install required test dependencies
2. Run all unit tests
3. Run all integration tests
4. Run all edge case tests
5. Run quick benchmarks
6. Generate code coverage reports
7. Create a test summary

**Options:**

```
usage: run_comprehensive_tests.py [-h] [--skip-unit] [--skip-integration]
                                 [--skip-edge-cases] [--skip-benchmarks]
                                 [--skip-dependencies] [--no-coverage]
                                 [--no-summary] [--verbose]

Run comprehensive tests for Triangulum Self-Healing System

optional arguments:
  -h, --help           show this help message and exit
  --skip-unit          Skip unit tests
  --skip-integration   Skip integration tests
  --skip-edge-cases    Skip edge case tests
  --skip-benchmarks    Skip benchmark tests
  --skip-dependencies  Skip dependency installation
  --no-coverage        Skip generating coverage reports
  --no-summary         Skip generating test summary
  --verbose            Enable verbose output
```

### Running Specific Test Categories

To run specific test categories directly:

**Unit Tests:**
```bash
python -m pytest tests/unit
```

**Integration Tests:**
```bash
python -m pytest tests/integration
```

**Edge Case Tests:**
```bash
python -m pytest tests/edge_cases
```

**Benchmarks:**
```bash
python tests/benchmarks/benchmark_folder_healing.py --size small --runs 1
```

### Running with Coverage

To run tests with coverage reports:

```bash
python -m pytest tests/unit --cov=triangulum_lx --cov-report=html:coverage_reports/unit_tests
```

## Test Results and Reports

### Coverage Reports

After running tests with coverage enabled, reports are generated in the `coverage_reports/` directory:

- `coverage_reports/unit_tests/` - Coverage from unit tests
- `coverage_reports/integration_tests/` - Coverage from integration tests
- `coverage_reports/edge_case_tests/` - Coverage from edge case tests
- `coverage_reports/combined/` - Combined coverage from all tests
- `coverage_reports/coverage.xml` - XML coverage report for CI/CD integration

Open `coverage_reports/combined/index.html` in a browser to view the detailed coverage report.

### Benchmark Results

Benchmark results are saved in:

- `tests/benchmarks/results/` - Contains JSON result files and visualization charts

## Adding New Tests

### Adding a Unit Test

1. Create a new test file in `tests/unit/` with the naming convention `test_*.py`
2. Import the component to test
3. Create a test class extending `unittest.TestCase`
4. Implement test methods with naming convention `test_*`
5. Use assertions to verify expected behavior

Example:

```python
import unittest
from triangulum_lx.agents.example_agent import ExampleAgent

class TestExampleAgent(unittest.TestCase):
    def setUp(self):
        self.agent = ExampleAgent(agent_id="test")
    
    def test_initialization(self):
        self.assertEqual(self.agent.agent_id, "test")
    
    def test_specific_functionality(self):
        result = self.agent.some_method()
        self.assertTrue(result)
```

### Adding an Integration Test

Integration tests follow the same pattern as unit tests but focus on component interactions. Place these in `tests/integration/`.

### Adding an Edge Case Test

Edge case tests should target specific unusual scenarios. Add these to `tests/edge_cases/`.

### Adding a Benchmark

Benchmarks require more setup to properly measure performance metrics. Use the existing benchmark file as a template.

## Best Practices

1. **Test Independence**: Each test should be independent of others and not rely on side effects
2. **Mock External Dependencies**: Use `unittest.mock` to isolate components from external dependencies
3. **Descriptive Test Names**: Use clear, descriptive test method names that explain what's being tested
4. **Test Both Success and Failure Paths**: Verify that components handle both valid and invalid inputs
5. **Maintain Test Coverage**: Aim for high test coverage, especially for critical components
6. **Keep Tests Fast**: Unit tests should execute quickly to enable rapid development cycles
7. **Test Real-World Scenarios**: Edge case tests should represent realistic challenging situations

## Continuous Integration

The test suite is designed to run in CI/CD environments. The XML coverage report can be used by CI systems to track coverage metrics over time.
