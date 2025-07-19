# Dependency Analysis System

The Dependency Analysis System is a core component of Triangulum that analyzes, visualizes, and leverages code relationships within a project.

## Components

The system consists of several interconnected components:

- `triangulum_lx/tooling/graph_models.py`: The foundation of the dependency analysis system, providing data structures to represent and manipulate code relationships.
- `triangulum_lx/tooling/dependency_graph.py`: Builds and manages dependency graphs.
- `triangulum_lx/agents/relationship_analyst_agent.py`: An agent that analyzes code relationships and provides actionable insights.

## Usage

To analyze the dependencies of a project, use the `analyze` command of the `triangulum` CLI:

```bash
python -m triangulum_lx.scripts.cli analyze path/to/your/code
```
