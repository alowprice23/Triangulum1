# Triangulum Lx v2: Operational Refactoring and Unification Plan

## 1. Project Mandate and Goals

**Primary Mandate:** To transform the Triangulum project into a single, coherent, and powerful autonomous system.

**Core Goals:**

1.  **Unify Architecture:** Embrace the bottom-up, emergent "Agent Triangulation Model" as the single source of truth for system behavior.
2.  **Consolidate Logic:** Absorb all valuable, non-redundant concepts into the core `triangulum_lx` library.
3.  **Establish a Robust Foundation:** Create a stable, well-documented, and rigorously tested codebase.
4.  **Empower the Relationship Tree:** Ensure the core engine and agent systems are designed to fully leverage the power of the `code_relationship_analyzer`.

## 2. Phase-Based Execution Plan

### **Phase 1: Core Logic Consolidation**

- **Refactor `triangulum_lx/agents/meta_agent.py`**: Merge the logic from `coordinator.py` and the concepts from `enhanced_nine_agent_system.py` into `meta_agent.py`.
- **Refactor `triangulum_lx/tooling/repair.py`**: Elevate this module to be the "Patcher Agent" and integrate it with the `meta_agent.py`.
- **Refactor `triangulum_lx/core/engine.py`**: Integrate the core self-healing concepts.
- **Refactor `triangulum_lx/monitoring/`**: Integrate the health metrics into the existing monitoring system.
- **Unify Entry Points**: Refactor `triangulum_lx/scripts/cli.py` to become the single entry point for the entire system.

### **Phase 2: Advanced Capabilities Integration**

- **Refactor Formal Verification (`spec/`)**: Update the TLA+ specification to match the new architecture.
- **Integrate Learning (`learning/`)**: Connect the `bug_predictor.py` and `optimizer.py` modules to the core engine's main loop.
- **Redefine the Goal (`goal/`)**: Update the `app_goal.yaml` to define a clear, high-level objective for the newly unified system.

### **Phase 3: Stabilization and Documentation**

- **Rebuild Unit Tests**: Write new unit tests for every module in the refactored `triangulum_lx` library.
- **Create Integration Tests**: Write a new suite of integration tests that verify the interactions between the major components.
- **Develop End-to-End (E2E) Tests**: Create a small number of high-value E2E tests that run the entire system via the new CLI.
- **Write New Documentation**: Create new documentation for the project.
