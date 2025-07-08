# Triangulum Lx 1.1: Operational Refactoring and Unification Plan

## 1. Project Mandate and Goals

**Primary Mandate:** To transform the Triangulum project from a fragmented collection of experimental scripts and a core library into a single, coherent, and powerful autonomous system.

**Core Goals:**

1.  **Unify Architecture:** Formally reject the top-down, script-driven "Domino-Effect Model" and fully embrace the bottom-up, emergent "Agent Triangulation Model" as the single source of truth for system behavior.
2.  **Consolidate Logic:** Absorb all valuable, non-redundant concepts from experimental scripts (e.g., self-healing, autonomous improvement, health metrics) into the core `triangulum_lx` library.
3.  **Establish a Robust Foundation:** Create a stable, well-documented, and rigorously tested codebase that enables reliable self-healing and provides a clear path for future development.
4.  **Empower the Relationship Tree:** Ensure the core engine and agent systems are designed to fully leverage the power of the `code_relationship_analyzer` as a primary tool for decision-making and self-modification.

---

## 2. File Disposition Lists

This section provides a definitive, at-a-glance reference for the fate of every file in the project, based on the previous analysis.

### **Files for Immediate Deletion**

*   `questions.md`
*   `zeroDeferred.md`
*   `TriangulumSystemStatus.md`
*   `triangulum_project_summary.md`
*   `triangulum_summary.md`
*   `triangulum_system_exploration.md`
*   `TRIANGULUM_DEBUG_README.md`
*   `TRIANGULUM_FOLDER_DEBUG_README.md`
*   `debug_imports.py`
*   `debug_triangulum_workflow.py`
*   `event_loop_bug.py` / `event_loop_bug_fixed.py`
*   `file_resource_bug.py` / `file_resource_bug_fixed.py`
*   `fix_test_bug.py`
*   `integrated_triangulum_debug.py`
*   `test_bug.py` / `test_bug_fixed.py`
*   `triangulum_adaptive_health.py`
*   `triangulum_autogen_implementation.py`
*   `triangulum_autogen_o3_demo.py`
*   `triangulum_autonomous_improvement_executor.py`
*   `triangulum_autonomous_startup.py`
*   `triangulum_continuous_self_improvement.py`
*   `triangulum_debug_orchestrator.py`
*   `triangulum_debug_system.py`
*   `triangulum_fix.py`
*   `triangulum_folder_debugger.py`
*   `triangulum_full_system_activation.py`
*   `triangulum_gpt.py`
*   `triangulum_mathematical_self_healing.py`
*   `triangulum_next_improvement_cycle.py`
*   `triangulum_real_world_application.py`
*   `triangulum_self_healing_session.py`
*   `triangulum_true_agent_demonstration.py`
*   `triangulum_ultimate_self_test.py`
*   `triangulum_lx/agents/coordinator.py`
*   `triangulum_lx/agents/enhanced_nine_agent_system.py`
*   `triangulum_lx/providers/state_management.py`
*   `triangulum_lx/monitoring/dashboard_stub.py`
*   `triangulum_lx/spec/performance_guarantees.py`
*   `triangulum_lx/quantum/entanglement.py`
*   `triangulum_lx/future/roadmap.py`
*   `triangulum_lx/scripts/bootstrap_demo.sh`
*   `scripts/discover_capabilities.py`

### **Files to Keep (As-Is or with Minor Updates)**

*   `.gitignore`
*   `pyproject.toml`
*   `pytest.ini`
*   `docker-compose.yml`
*   `triangulum_lx/core/__init__.py`
*   `triangulum_lx/core/state.py`
*   `triangulum_lx/core/transition.py`
*   `triangulum_lx/core/exceptions.py`
*   `triangulum_lx/core/rollback_manager.py`
*   `triangulum_lx/core/tracing.py`
*   `triangulum_lx/core/compatibility.py`
*   `triangulum_lx/core/parallel_executor.py`
*   `triangulum_lx/agents/__init__.py`
*   `triangulum_lx/agents/router.py`
*   `triangulum_lx/agents/roles.py`
*   `triangulum_lx/agents/llm_config.py`
*   `triangulum_lx/agents/response_cache.py`
*   `triangulum_lx/providers/__init__.py`
*   `triangulum_lx/providers/base.py`
*   `triangulum_lx/providers/factory.py`
*   `triangulum_lx/providers/request_manager.py`
*   `triangulum_lx/providers/anthropic.py`, `groq.py`, `openrouter.py`, `openai.py`, `local.py`
*   `triangulum_lx/tooling/__init__.py`
*   `triangulum_lx/tooling/code_relationship_analyzer.py`
*   `triangulum_lx/tooling/relationship_context_provider.py`
*   `triangulum_lx/tooling/dependency_analyzer.py`
*   `triangulum_lx/tooling/test_runner.py`
*   `triangulum_lx/tooling/patch_bundle.py`
*   `triangulum_lx/tooling/canary_runner.py`
*   `triangulum_lx/tooling/smoke_runner.py`
*   `triangulum_lx/tooling/scope_filter.py`
*   `triangulum_lx/tooling/compress.py`
*   `triangulum_lx/monitoring/__init__.py`
*   `triangulum_lx/monitoring/metrics.py`
*   `triangulum_lx/monitoring/metrics_exporter.py`
*   `triangulum_lx/monitoring/visualization.py`
*   `triangulum_lx/learning/__init__.py`
*   `triangulum_lx/learning/replay_buffer.py`
*   `triangulum_lx/goal/__init__.py`
*   `triangulum_lx/goal/goal_loader.py`
*   `triangulum_lx/goal/prioritiser.py`
*   `triangulum_lx/human/__init__.py`
*   `triangulum_lx/human/feedback.py`
*   `triangulum_lx/human/hub.py`
*   `triangulum_lx/spec/__init__.py`
*   `triangulum_lx/quantum/__init__.py`
*   `triangulum_lx/future/__init__.py`
*   `triangulum_lx/scripts/__init__.py`
*   `scripts/run_benchmarks.py`
*   `docker/Dockerfile.engine`, `Dockerfile.dashboard`, `Dockerfile.hub`
*   `docker/prometheus.yml`
*   `docker/grafana/` (and all contents)

### **Files to Refactor**

*   `setup.py`
*   `triangulum.py`
*   `start_triangulum.py`
*   `debug_with_relationships.py`
*   `run_triangulum_autonomous.py`
*   `run_triangulum_demo.py`
*   `triangulum_adaptive_breakthrough.py`
*   `triangulum_comprehensive_self_assessment.py`
*   `triangulum_final_breakthrough.py`
*   `triangulum_monitor.py`
*   `triangulum_self_heal.py`
*   `triangulum_ultimate_breakthrough.py`
*   `triangulum_lx/core/engine.py`
*   `triangulum_lx/core/monitor.py`
*   `triangulum_lx/core/entropy_explainer.py`
*   `triangulum_lx/agents/meta_agent.py`
*   `triangulum_lx/providers/capability_discovery.py`
*   `triangulum_lx/tooling/repair.py`
*   `triangulum_lx/learning/bug_predictor.py`
*   `triangulum_lx/learning/optimizer.py`
*   `triangulum_lx/human/interactive_mode.py`
*   `triangulum_lx/spec/ltl_properties.py`
*   `triangulum_lx/spec/model_checker.py`
*   `triangulum_lx/spec/Triangulation.tla` / `Triangulation.cfg`
*   `triangulum_lx/scripts/cli.py`
*   `scripts/analyze_code_relationships.py`

### **Files to Update / Replace**

*   `requirements.txt` (Update)
*   `README.md` (Replace)
*   `CONTRIBUTING.md` (Update)
*   `TriangulumSystemFilesGuide.md` (Replace with this plan)
*   `triangulum_lx/goal/app_goal.yaml` (Update)
*   `triangulum_lx/tests/` (and all sub-directories) (Update)
*   `tests/` (and all sub-directories) (Update)

---

## 3. Phase-Based Execution Plan

### **Phase 1: Project Reset and Foundation Setting**

**Objective:** To aggressively clean the repository of all distractions and establish a clean, stable baseline for focused development.

| Task ID | Task Description | Potential Issues & Risks | Contingency Plan |
| :--- | :--- | :--- | :--- |
| **1.1** | **Execute Deletions:** Delete all files listed in the "Files for Immediate Deletion" section. | **Accidental Deletion:** A file not on the list is accidentally deleted. | **Version Control Recovery:** Immediately revert the deletion using Git. The deletion script/command should be double-checked against the list before execution. |
| **1.2** | **Isolate "Breakthrough" Logic:** Move the three `_breakthrough.py` scripts and `triangulum_comprehensive_self_assessment.py` to a temporary `legacy/` directory. | **Hidden Dependencies:** These scripts might have unobvious dependencies on other files, breaking imports when moved. | **Analyze Imports:** Before moving, statically analyze the imports of these files. If they depend on other soon-to-be-deleted files, those dependencies must be noted for the refactoring phase. |
| **1.3** | **Initial Test Suite Purge:** Delete all tests corresponding to deleted files. Run the remaining test suite. | **Massive Test Failures:** The remaining tests are expected to fail massively due to the deletions. The scale might be overwhelming. | **Document, Don't Fix:** The goal is not to fix tests in this phase. The output of the test run should be saved to a `test_failures_phase1.log` file. This log becomes a to-do list for Phase 4. |
| **1.4** | **Create New `README.md`:** Replace the existing `README.md` with a new one containing only the Project Mandate from this plan and a note that the project is undergoing a major refactor. | **Loss of Old Information:** The old README might contain useful setup or historical notes. | **Archive Old README:** Rename the old file to `README_legacy.md` instead of deleting it, preserving it for reference. |
| **1.5** | **Update `.gitignore`:** Add `legacy/`, `*.log`, and any other new temporary artifacts to the `.gitignore` file. | **Forgetting Artifacts:** New temporary files created during the process might be accidentally committed. | **Pre-Commit Hook:** For developers, a local pre-commit hook can be used to check for temporary file patterns, preventing them from being staged. |

### **Phase 2: Core Logic Consolidation**

**Objective:** To refactor all scattered, high-value logic into the `triangulum_lx` library, creating a single, unified, and powerful core system.

| Task ID | Task Description | Potential Issues & Risks | Contingency Plan |
| :--- | :--- | :--- | :--- |
| **2.1** | **Refactor `triangulum_lx/agents/meta_agent.py`:** Merge the logic from `coordinator.py` and the concepts from `enhanced_nine_agent_system.py` into `meta_agent.py`. This agent should become the definitive coordinator of all other agents. | **Conflicting Logic:** The different agent systems might have conflicting assumptions about control flow or state management. | **Design First:** Before coding, write a short internal design document (`docs/design/meta_agent_v2.md`) that explicitly defines the new control flow, state transitions, and how concepts from the legacy systems are mapped to the new one. This ensures conceptual integrity before implementation. |
| **2.2** | **Refactor `triangulum_lx/tooling/repair.py`:** Elevate this module to be the "Patcher Agent." Integrate its functionality directly with the `meta_agent.py` so that repair tasks can be dispatched, executed, and verified autonomously. | **Brittle Repair Logic:** The existing repair logic might be too simple and fail on complex bugs. | **Isolate and Test:** Treat `repair.py` as a black box. Create a dedicated test harness that feeds it a variety of known-bad code snippets. The goal is to define its capabilities and limitations clearly *before* integrating it, to prevent the core engine from relying on a faulty tool. |
| **2.3** | **Refactor `triangulum_lx/core/engine.py`:** This is the central task. Integrate the core concepts from `triangulum_self_heal.py` and the `_breakthrough.py` scripts. The engine should be responsible for the main loop: Assess -> Plan -> Act -> Verify. It should use the `meta_agent` to execute plans. | **Overly Complex Engine:** Trying to merge too many "breakthrough" concepts at once could create a monolithic, unmaintainable engine. | **Incremental Integration:** Do not merge all concepts at once. Prioritize the most critical one (e.g., the core self-healing loop). Implement it, write tests, and ensure it's stable. Then, introduce the next concept (e.g., adaptive optimization) in a separate pull request. |
| **2.4** | **Refactor `triangulum_lx/monitoring/`:** Integrate the health metrics from `triangulum_comprehensive_self_assessment.py` into `metrics.py` and `system_monitor.py`. | **Metric Incompatibility:** The metrics from the script might not fit the existing monitoring schema. | **Schema Evolution:** If there are incompatibilities, formally version the metrics schema. Update the Grafana dashboard to handle both old and new metric formats during the transition, preventing loss of observability. |
| **2.5** | **Unify Entry Points:** Deprecate `start_triangulum.py` and `triangulum.py`. Refactor `triangulum_lx/scripts/cli.py` to become the single entry point for the entire system, using a library like `click` or `argparse`. | **Complex CLI:** The CLI could become a kitchen sink of commands and flags. | **Command Groups:** Use CLI framework features to group related commands (e.g., `triangulum run`, `triangulum analyze`, `triangulum test`). This keeps the interface clean and discoverable. |
| **2.6** | **Update `requirements.txt`:** After all refactoring, regenerate the `requirements.txt` file from scratch to ensure it reflects the true dependencies of the new, streamlined system. | **Missing Dependencies:** A manually maintained or poorly generated file could miss a dependency, causing runtime failures. | **Use `pip-tools`:** Use a tool like `pip-tools` to compile a `requirements.txt` from a `requirements.in` file. This ensures that only top-level dependencies need to be managed by hand, and all sub-dependencies are resolved correctly and pinned. |

### **Phase 3: Advanced Capabilities Integration**

**Objective:** To refactor and integrate the system's advanced formal verification, learning, and goal-oriented capabilities to support the newly consolidated core engine.

| Task ID | Task Description | Potential Issues & Risks | Contingency Plan |
| :--- | :--- | :--- | :--- |
| **3.1** | **Refactor Formal Verification (`spec/`):** Update the TLA+ specification (`Triangulation.tla`) to match the new, unified architecture of the `core/engine.py` and `agents/meta_agent.py`. The LTL properties should also be updated to reflect the new state machine. | **State Space Explosion:** The new, more complex engine might lead to a state space that is too large for the TLA+ model checker to handle efficiently. | **Abstraction and Refinement:** If the state space is too large, create a more abstract version of the model for initial verification. Use refinement mapping to prove that the detailed implementation correctly implements the abstract spec. This is a standard TLA+ technique for managing complexity. |
| **3.2** | **Integrate Learning (`learning/`):** Connect the `bug_predictor.py` and `optimizer.py` modules to the core engine's main loop. The engine should be able to consult the bug predictor during its "Assess" phase and use the optimizer during its "Plan" phase. | **Unstable Predictions:** The learning models might not be well-trained, leading to unstable or incorrect predictions that could send the engine on a wild goose chase. | **Gate the Output:** Do not allow the learning components to act directly. Their output should be treated as a *suggestion* or a *heuristic*. The engine should use this information to prioritize its own analysis, but it must still independently verify the bug or the optimization before acting. The learning models should have a "confidence score" and suggestions below a certain threshold should be ignored. |
| **3.3** | **Redefine the Goal (`goal/`):** Update the `app_goal.yaml` to define a clear, high-level objective for the newly unified system. This goal should be achievable via the emergent behavior of the agent system, not by direct scripting. | **Vague or Unachievable Goal:** The goal might be too abstract (e.g., "be better") or too complex for the system to decompose into actionable steps. | **Goal Decomposition Test:** Before finalizing the goal, run it through a "decomposition test." Manually (or with a separate script) try to break the goal down into the kinds of tasks the `prioritiser.py` can handle. If it can't be broken down, the goal is too complex and needs to be simplified. |
| **3.4** | **Integrate Entropy Explainer:** Refactor `entropy_explainer.py` and connect it to the `monitor`. The system should be able to report on its own internal complexity and uncertainty, which can be a valuable metric for assessing system health. | **High Computational Cost:** Calculating entropy could be computationally expensive and slow down the main engine loop. | **Asynchronous Calculation:** Move the entropy calculation to a separate thread or process. The engine should not wait for the result. The monitor can use the last known value, making the calculation asynchronous and non-blocking. |

### **Phase 4: Stabilization and Documentation**

**Objective:** To build a comprehensive test suite that validates the new architecture and to create clear, concise documentation that makes the system understandable and maintainable.

| Task ID | Task Description | Potential Issues & Risks | Contingency Plan |
| :--- | :--- | :--- | :--- |
| **4.1** | **Rebuild Unit Tests:** Using the `test_failures_phase1.log` as a guide, systematically write new unit tests for every module in the refactored `triangulum_lx` library. Aim for high test coverage of all core components. | **Time Consuming:** Writing a comprehensive unit test suite from scratch is a significant time investment. | **Prioritize and Parallelize:** Prioritize the most critical modules first (`core/engine.py`, `agents/meta_agent.py`, `tooling/repair.py`). If multiple developers are available, the work can be parallelized by assigning ownership of different modules. |
| **4.2** | **Create Integration Tests:** Write a new suite of integration tests that verify the interactions between the major components (e.g., Engine -> Meta-Agent -> Repair Tool -> Test Runner). | **Complex Test Setup:** Integration tests require a more complex setup, including potentially spinning up mock services or a full Docker environment. | **Use Test Harnesses and Fixtures:** Develop a robust set of test harnesses and `pytest` fixtures that handle the setup and teardown of the required environment. This makes the tests themselves cleaner and easier to write and maintain. |
| **4.3** | **Develop End-to-End (E2E) Tests:** Create a small number of high-value E2E tests that run the entire system via the new CLI. These tests should simulate a real user scenario, such as "debug and fix this known bug in this file." | **Flaky Tests:** E2E tests can be notoriously flaky, failing due to timeouts, race conditions, or other non-deterministic issues. | **Robust Test Design:** Design E2E tests for robustness. Instead of asserting exact timing, assert final state. Build in explicit waits for certain conditions. Run them multiple times in CI to identify and fix sources of flakiness. |
| **4.4** | **Write New Documentation:** Create new documentation for the project, including a high-level architecture overview, a developer guide for setting up the environment and running tests, and a user guide for the new CLI. | **Documentation Drift:** The documentation can quickly become outdated as the code continues to evolve after the refactor. | **Docs-as-Code:** Treat documentation as code. Store it in the Git repository (e.g., in a `/docs` directory) and require that pull requests with code changes also include corresponding documentation updates. Use tools that can generate parts of the documentation from code comments (e.g., Sphinx for Python docstrings). |
| **4.5** | **Final Cleanup:** Delete the `legacy/` directory and any remaining temporary files or logs from the refactoring process. | **Premature Deletion:** A file in `legacy/` might still be needed for reference. | **Final Review:** Before the final deletion, do one last review of the files in `legacy/` to ensure all valuable concepts have been successfully migrated. If in doubt, archive it in a separate, clearly marked branch instead of deleting it outright. |

---

## 4. Dynamics that Could Solidify Improvements

This section outlines the principles and practices required to ensure the benefits of this refactoring are lasting and that the project does not regress into a fragmented state.

1.  **Architectural Supremacy of `triangulum_lx`:**
    *   **Principle:** All new system capabilities, behaviors, or experiments **must** be implemented within the `triangulum_lx` library. The root directory is for configuration and a single entry point, not for logic.
    *   **Enforcement:** Code reviews must strictly reject any pull request that adds Python logic files to the root directory. A linting rule or a CI check could be created to enforce this automatically.

2.  **Test-Driven Refactoring and Development:**
    *   **Principle:** No refactoring is considered "done" until it is covered by robust unit and integration tests. New features must be accompanied by tests.
    *   **Enforcement:** The CI pipeline must enforce a minimum code coverage threshold. Pull requests that lower the coverage percentage should be automatically flagged or blocked.

3.  **Immutable Goal-Driven Operation:**
    *   **Principle:** The system's high-level behavior should be guided exclusively by the `app_goal.yaml` file. "One-off" scripts to force a particular outcome are forbidden. To change the system's behavior, one must change the goal definition.
    *   **Enforcement:** The main `triangulum.py` entry point should be the only script capable of initiating a system run. All autonomous modes must be functions within the core library that are invoked via this single, controlled entry point.

4.  **Documentation as a Living Contract:**
    *   **Principle:** The `README.md` and other core documents must be updated in the same pull request that alters the corresponding code. Outdated documentation is a form of technical debt.
    *   **Enforcement:** Add a "Documentation Updated?" checkbox to the pull request template. While not foolproof, it serves as a strong reminder to the developer and a check for the reviewer.

5.  **The "Relationship Tree" as a First-Class Citizen:**
    *   **Principle:** When designing new features, the first question should always be: "How can the system leverage the code relationship graph to achieve this autonomously?" This forces a mindset shift from direct implementation to meta-programming and self-modification.
    *   **Enforcement:** Design review meetings for new, complex features should require the proposing developer to present a strategy for how the relationship tree will be used for analysis, planning, and execution.
