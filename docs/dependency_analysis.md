# Dependency Analysis System

The Dependency Analysis System is a core component of Triangulum that analyzes, visualizes, and leverages code relationships within a project. This system provides insights into code dependencies, identifies critical files, detects cycles, and prioritizes files for repair or enhancement.

## Components

The system consists of several interconnected components:

### 1. Graph Models (`triangulum_lx/tooling/graph_models.py`)

The foundation of the dependency analysis system, providing data structures to represent and manipulate code relationships:

- **DependencyGraph**: Core data structure representing the dependency graph
- **FileNode**: Represents a file in the dependency graph
- **DependencyMetadata**: Metadata for dependencies (type, confidence, etc.)
- **DependencyType**: Enumeration of dependency types (import, function call, etc.)
- **LanguageType**: Enumeration of supported programming languages

### 2. Dependency Graph Builder (`triangulum_lx/tooling/dependency_graph.py`)

Builds and manages dependency graphs:

- **DependencyGraphBuilder**: Creates dependency graphs from code files
- **BaseDependencyParser**: Abstract base class for language-specific parsers
- **PythonDependencyParser**: Parser for Python dependencies
- **JavaScriptDependencyParser**: Parser for JavaScript dependencies
- **TypeScriptDependencyParser**: Parser for TypeScript dependencies
- **ParserRegistry**: Registry of language-specific parsers
- **DependencyAnalyzer**: Analyzes dependency graphs for insights

### 3. Relationship Analyst Agent (`triangulum_lx/agents/relationship_analyst_agent.py`)

An agent that analyzes code relationships and provides actionable insights:

- Analyzes codebases to build dependency graphs
- Identifies central files using various centrality metrics
- Detects dependency cycles
- Prioritizes files for repair based on impact
- Provides dependency and dependent information for specific files
- Determines the impact of changes to specific files

## Usage

### Command-Line Usage

Use the dependency graph demo to analyze any project:

```bash
python examples/dependency_graph_demo.py --path /path/to/project
```

Options:
- `--path`: Path to the project root
- `--workers`: Number of worker threads for parallel processing
- `--include`: Glob patterns for files to include
- `--exclude`: Glob patterns for files to exclude
- `--file`: Specific file to analyze

The relationship analyst demo provides more detailed analysis:

```bash
python examples/relationship_analyst_demo.py --path /path/to/project --file path/to/specific/file.py
```

### Programmatic Usage

#### Building a Dependency Graph

```python
from triangulum_lx.tooling.dependency_graph import DependencyGraphBuilder, DependencyAnalyzer

# Create a builder
builder = DependencyGraphBuilder(max_workers=4)

# Build a graph
graph = builder.build_graph(
    path="/path/to/project",
    include_patterns=["**/*.py", "**/*.js"],
    exclude_patterns=["**/venv/**", "**/__pycache__/**"]
)

# Create an analyzer
analyzer = DependencyAnalyzer(graph)

# Get the most central files
central_files = analyzer.get_most_central_files(n=10, metric="pagerank")

# Find cycles
cycles = analyzer.find_cycles()

# Prioritize files for repair
priorities = analyzer.prioritize_files(
    files=list(graph),
    prioritization_strategy="pagerank"
)
```

#### Using the Relationship Analyst Agent

```python
from triangulum_lx.agents.relationship_analyst_agent import RelationshipAnalystAgent

# Create the agent
agent = RelationshipAnalystAgent(max_workers=4)

# Analyze a codebase
summary = agent.analyze_codebase(
    root_dir="/path/to/project",
    include_patterns=["**/*.py", "**/*.js"],
    exclude_patterns=["**/venv/**", "**/__pycache__/**"]
)

# Get the most central files
central_files = agent.get_most_central_files(n=10, metric="pagerank")

# Get dependencies of a specific file
dependencies = agent.get_file_dependencies("path/to/file.py", transitive=True)

# Get dependents of a specific file
dependents = agent.get_file_dependents("path/to/file.py", transitive=True)

# Get files impacted by changes to specific files
impacted = agent.get_impacted_files(["path/to/file1.py", "path/to/file2.py"])
```

#### Using the Agent Messaging System

The RelationshipAnalystAgent integrates with Triangulum's agent messaging system:

```python
from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.message_bus import MessageBus

# Create a message bus
message_bus = MessageBus()

# Create the agent
agent = RelationshipAnalystAgent(name="relationship_analyst")
agent.message_bus = message_bus

# Subscribe to messages from the agent
message_bus.subscribe(
    agent_id="consumer",
    callback=handle_message,
    message_types=[MessageType.TASK_RESULT, MessageType.QUERY_RESULT]
)

# Send a task request to analyze a codebase
message_bus.publish(
    AgentMessage(
        message_type=MessageType.TASK_REQUEST,
        content={
            "action": "analyze_codebase",
            "root_dir": "/path/to/project"
        },
        sender="consumer",
        receiver="relationship_analyst"
    )
)

# Send a query for central files
message_bus.publish(
    AgentMessage(
        message_type=MessageType.QUERY,
        content={
            "query_type": "central_files",
            "n": 10,
            "metric": "pagerank"
        },
        sender="consumer",
        receiver="relationship_analyst"
    )
)
```

## Applications

The Dependency Analysis System can be used for:

1. **Code Understanding**: Visualize and understand code relationships
2. **Bug Localization**: Identify potential sources of bugs based on dependencies
3. **Impact Analysis**: Determine the impact of changes to specific files
4. **Refactoring Planning**: Identify hotspots and cycles for refactoring
5. **Testing Prioritization**: Prioritize tests based on code centrality
6. **Maintenance Planning**: Identify critical files for maintenance
7. **Code Review Prioritization**: Prioritize code reviews based on file importance
8. **Codebase Health Monitoring**: Track metrics like cycle count over time

## Centrality Metrics

The system uses several centrality metrics to identify important files:

- **PageRank**: Identifies files that are important based on the number and quality of files that depend on them
- **Betweenness**: Identifies files that bridge different parts of the codebase
- **In-Degree**: Identifies files with many dependents
- **Out-Degree**: Identifies files with many dependencies

## Integration with Self-Healing

The Dependency Analysis System integrates with Triangulum's self-healing capabilities:

1. When a bug is detected, the system identifies potentially related files based on dependencies
2. Files are prioritized for repair based on centrality and impact
3. Repair agents can focus their efforts on the most critical files first
4. After repairs, the system can analyze the impact of changes to identify potential side effects

This integration enables more efficient and effective bug detection and repair, focusing resources on the most important parts of the codebase.
