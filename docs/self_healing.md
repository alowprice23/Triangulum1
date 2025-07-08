# Triangulum Self-Healing System

## Overview

The Triangulum Self-Healing System is an advanced framework designed to automatically detect, analyze, and fix bugs in software projects. By leveraging code relationship analysis and intelligent patching mechanisms, it can restore system health with minimal human intervention.

## Architecture

The self-healing system consists of several integrated components that work together to provide comprehensive repair capabilities:

```
┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │
│  Code Relationship  │◄────►│  Relationship       │
│  Analyzer           │      │  Context Provider   │
│                     │      │                     │
└─────────┬───────────┘      └─────────┬───────────┘
          │                            │
          │                            │
          ▼                            ▼
┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │
│  Test Runner        │◄────►│  Patcher Agent      │
│                     │      │                     │
└─────────────────────┘      └─────────────────────┘
          │                            │
          │                            │
          ▼                            ▼
┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │
│  Test Results       │      │  Patch Bundle       │
│                     │      │                     │
└─────────────────────┘      └─────────────────────┘
```

### Key Components

1. **Code Relationship Analyzer**: Analyzes code to understand dependencies, imports, and relationships between files.
2. **Relationship Context Provider**: Provides context about code relationships for making informed repair decisions.
3. **Test Runner**: Executes tests to identify bugs and verify fixes.
4. **Patcher Agent**: The central component that orchestrates the repair process.
5. **Patch Bundle**: Manages patches for applying and rolling back changes.

## Self-Healing Workflow

The self-healing process follows these key steps:

1. **Detection**: The system detects bugs through test failures or explicit reporting.
2. **Analysis**: It analyzes the bug in context of code relationships to understand its impact.
3. **Patch Generation**: A patch is generated to fix the identified issue.
4. **Application**: The patch is applied to the affected file(s).
5. **Verification**: Tests are run to verify the fix resolves the issue.
6. **Acceptance or Rollback**: If tests pass, the fix is accepted; otherwise, changes are rolled back.

## Using the Self-Healing System

### Basic Usage

The simplest way to use the self-healing system is through the `PatcherAgent` class:

```python
from triangulum_lx.tooling.repair import PatcherAgent

# Initialize the patcher agent
patcher = PatcherAgent()

# Define a bug task
bug_task = {
    'bug_id': 'BUG-001',
    'file_path': 'path/to/buggy_file.py',
    'bug_description': 'Description of the bug'
}

# Execute the repair
result = patcher.execute_repair(bug_task)

# Check the result
if result == "SUCCESS":
    print("Bug fixed successfully!")
else:
    print(f"Failed to fix bug: {result}")
```

### Advanced Usage with Code Relationships

For more effective repairs, initialize the system with code relationship analysis:

```python
from triangulum_lx.tooling.repair import PatcherAgent
from triangulum_lx.tooling.code_relationship_analyzer import CodeRelationshipAnalyzer
from triangulum_lx.tooling.relationship_context_provider import RelationshipContextProvider
from triangulum_lx.tooling.test_runner import TestRunner

# Initialize components
analyzer = CodeRelationshipAnalyzer()
relationship_provider = RelationshipContextProvider()
test_runner = TestRunner()

# Analyze code relationships
analyzer.analyze_directory("path/to/project")
relationship_provider.load_relationships(analyzer.relationships)

# Initialize patcher with relationships
patcher = PatcherAgent(relationships_path="relationships.json")
patcher.relationship_analyzer = analyzer
patcher.relationship_provider = relationship_provider
patcher.test_runner = test_runner

# Define a bug task
bug_task = {
    'bug_id': 'BUG-001',
    'file_path': 'path/to/buggy_file.py',
    'bug_description': 'Description of the bug',
    'error_message': 'Error message from test failure'
}

# Execute the repair
result = patcher.execute_repair(bug_task)
```

## Key Components in Detail

### PatcherAgent

The `PatcherAgent` is the central component that orchestrates the repair process. It takes a bug task as input and attempts to fix the issue by analyzing the code, generating a patch, applying it, and verifying the fix.

**Key Methods:**
- `execute_repair(task)`: Main entry point for repair operations
- `_analyze(task)`: Analyzes the bug in context
- `_generate_patch(task, context)`: Generates a patch to fix the bug
- `_apply(patch)`: Applies the patch to the file
- `_verify(task)`: Verifies the patch with tests
- `_rollback(patch)`: Rolls back changes if verification fails

### CodeRelationshipAnalyzer

This component analyzes code to understand dependencies, imports, and relationships between files. It builds a comprehensive view of the codebase to inform repair decisions.

**Key Methods:**
- `analyze_directory(directory)`: Analyzes all files in a directory
- `analyze_file(file_path)`: Analyzes a single file
- `save_relationships(path)`: Saves analyzed relationships to a file

### RelationshipContextProvider

This component provides context about code relationships for making informed repair decisions. It leverages the analysis from `CodeRelationshipAnalyzer` to understand the impact of changes.

**Key Methods:**
- `load_relationships(relationships)`: Loads analyzed relationships
- `get_context_for_repair(file_path)`: Gets repair context for a file
- `get_impact_analysis(file_path)`: Analyzes the impact of changes to a file
- `get_related_files(file_path, max_depth)`: Gets files related to a specific file

### TestRunner

This component executes tests to identify bugs and verify fixes. It can run specific tests or discover tests related to a file.

**Key Methods:**
- `run_specific_test(test_path)`: Runs a specific test
- `find_related_tests(file_path)`: Finds tests related to a file
- `validate_patch(file_path, test_paths, patch_content)`: Validates a patch

### PatchBundle

This component manages patches for applying and rolling back changes. It provides a safe way to make changes to files with the ability to revert if necessary.

**Key Methods:**
- `apply()`: Applies the patch
- `revert()`: Reverts the patch

## Best Practices

1. **Comprehensive Test Coverage**: Self-healing relies on tests to detect bugs and verify fixes. Ensure your project has good test coverage.

2. **Code Relationship Analysis**: Always run code relationship analysis before attempting repairs. Understanding the relationships between files is crucial for effective repairs.

3. **Backup Important Files**: While the system creates backups automatically, consider additional backups for critical files.

4. **Start Small**: Begin with isolated, well-understood components before applying self-healing to complex, interconnected systems.

5. **Review Generated Patches**: Even though the system is automated, review generated patches for complex bugs to ensure they align with your project's architecture and standards.

6. **Integration with CI/CD**: Consider integrating the self-healing system into your CI/CD pipeline to automatically fix issues during development and deployment.

## Example: Self-Healing in Action

The following example demonstrates a complete self-healing workflow:

```python
import os
from triangulum_lx.tooling.repair import PatcherAgent
from triangulum_lx.tooling.code_relationship_analyzer import CodeRelationshipAnalyzer
from triangulum_lx.tooling.relationship_context_provider import RelationshipContextProvider
from triangulum_lx.tooling.test_runner import TestRunner

# Initialize components
project_dir = "path/to/project"
analyzer = CodeRelationshipAnalyzer()
provider = RelationshipContextProvider()
test_runner = TestRunner(project_dir)
patcher = PatcherAgent(relationships_path=os.path.join(project_dir, "relationships.json"))

# Set up dependencies
patcher.relationship_analyzer = analyzer
patcher.relationship_provider = provider
patcher.test_runner = test_runner

# Analyze code relationships
analyzer.analyze_directory(project_dir)
provider.load_relationships(analyzer.relationships)

# Run tests to detect bugs
test_result = test_runner.run_specific_test("path/to/failing_test.py")

if not test_result.success:
    # Create a bug task
    bug_task = {
        'bug_id': 'BUG-001',
        'file_path': 'path/to/buggy_file.py',
        'bug_description': 'Bug detected by failing test',
        'error_message': test_result.message
    }
    
    # Attempt to fix the bug
    repair_result = patcher.execute_repair(bug_task)
    
    if repair_result == "SUCCESS":
        print("Bug fixed successfully!")
        
        # Run the tests again to confirm
        verification_result = test_runner.run_specific_test("path/to/failing_test.py")
        if verification_result.success:
            print("Verification passed!")
        else:
            print("Verification failed. This is unexpected since repair succeeded.")
    else:
        print(f"Failed to fix bug: {repair_result}")
else:
    print("No bugs detected.")
```

## Customizing the Self-Healing Process

The Triangulum self-healing system is designed to be flexible and extensible. You can customize various aspects of the repair process to suit your specific needs:

### Custom Patch Generation

You can customize the patch generation process by extending the `PatcherAgent` class and overriding the `_generate_patch` method:

```python
class CustomPatcherAgent(PatcherAgent):
    def _generate_patch(self, task, context):
        # Your custom patch generation logic
        # Use context to inform your decisions
        
        # Return a patch dictionary
        return {
            'bug_id': task['bug_id'],
            'file_path': task['file_path'],
            'patch_diff': 'Your patch content here',
            'impact_level': 'low',
            'related_files': []
        }
```

### Custom Analysis

You can also customize the analysis process by overriding the `_analyze` method:

```python
class CustomPatcherAgent(PatcherAgent):
    def _analyze(self, task):
        # Your custom analysis logic
        
        # Return analysis context
        return {
            'file_path': task['file_path'],
            'bug_id': task['bug_id'],
            'custom_analysis': 'Your custom analysis here',
            # ... other context information
        }
```

## Troubleshooting

### Common Issues

1. **PatchBundle Application Failures**:
   - Error: "Failed to apply patch"
   - Solution: Ensure that the patch format is correct and that the file exists.

2. **Test Runner Issues**:
   - Error: "No tests found for file"
   - Solution: Use the `find_related_tests` method to locate tests, or specify test paths manually.

3. **Relationship Analysis Failures**:
   - Error: "Failed to analyze file"
   - Solution: Check file encoding and syntax, and ensure the file is a valid Python file.

4. **Verification Failures**:
   - Error: "Verification failed"
   - Solution: Check that the tests are correctly validating the expected behavior.

### Debugging the Self-Healing Process

To debug the self-healing process, enable detailed logging:

```python
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Conclusion

The Triangulum Self-Healing System provides a powerful framework for automatically detecting and fixing bugs in your software projects. By leveraging code relationship analysis and intelligent patching mechanisms, it can significantly reduce the time and effort required to maintain system health.

For more detailed examples and use cases, refer to the `examples/self_healing_demo.py` file in the project repository.
