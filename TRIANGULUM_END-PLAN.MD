PLAN-TRIANGULUM-CONSOLIDATE
FS-UNBLOCK ROADMAP (attach this to TRIANGULUM_END-PLAN.md under a new section “FS-01”) ID Objective Files to create / modify Definition of Done FS-01.1 Introduce an AtomicFileOps utility that wraps every write/rename/delete in an O_TMPFILE → fsync → atomic rename sequence. triangulum_lx/tooling/fs_ops.py • All file-mutating calls in core & tooling go through this module. • Unit test writes 1 000 temp files in parallel and detects 0 stale reads. FS-01.2 Add a FileSystemStateCache with explicit invalidation after each atomic op. triangulum_lx/core/fs_state.py • exists(path) and listdir(path) always reflect reality after any op. • Cache hit ratio logged; mismatch counter remains 0 in stress test. FS-01.3 Implement a post-op verifier (assert_fs_consistency) run in CI: reads back every path touched in last commit and fails on “file not found” or unexpected presence. tests/fs/test_consistency.py • Fails if stale metadata occurs; passes on clean repo. FS-01.4 Wire all tooling scripts (repair.py, rollback_manager.py, cleanup scripts) to call AtomicFileOps and invalidate the cache. Modify listed files (search “open(…,'w')” / os.rename) • Grep for direct mutating calls → 0 remaining. FS-01.5 Add a watchdog fallback (Linux: inotify, macOS: FSEvents, else polling) to auto-invalidate the cache when any external process changes files. triangulum_lx/core/fs_watch.py • Integration test spawns a separate process to delete a file; cache reflects change within ≤ 1 s.


**Inventory**
* Total files scanned : 457
* Directories : 62
* Estimated essential files in final system: ~150-200 (after consolidation)

**Global Findings**
* Duplicate clusters : 7
    1. Dashboards (multiple instances)
    2. Agent Coordinators (`triangulum_lx/agents/coordinator.py`, `enhanced_coordinator.py`, `meta_agent.py` vs. `orchestrator_agent.py`)
    3. Message Bus (`triangulum_lx/agents/message_bus.py` vs. `enhanced_message_bus.py`)
    4. Ad-hoc Fix Scripts (numerous `fix_*.py` at root)
    5. Example/Demo Projects (multiple small projects/copies)
    6. Project Snapshots/Backups (`fixwurx_eval/`)
    7. LLM Provider Factories (`llm_providers.py` vs `triangulum_lx/providers/factory.py`)
* Orphan files : ~22 (examples: `file1.py`, old `fix_*.py` scripts, `.bak` files, unlinked old reports)
* Conflicting APIs : 3
    1. Agent Coordinators
    2. Message Bus implementations
    3. Dashboard Backend Connectors (if not unified)
* Missing deps :
    * `astroid` (Python package, clarify if mandatory for `bug_detector_agent.py`)
    * OS-level: `docker`, `git`
    * Implied by Dockerfiles: `grafana`, `prometheus` (if not using pre-built service images)

**File Map (Essential Files for Final System)**
.gitignore | PURPOSE=vcs_ignore_patterns | TAGS=[config,vcs]
CONTRIBUTING.md | PURPOSE=contribution_guidelines | TAGS=[documentation,community]
README.md | PURPOSE=main_project_overview_consolidated | TAGS=[documentation,project]
TRIANGULUM_DASHBOARD_INTEGRATION_SOLUTION.md | PURPOSE=dashboard_integration_plan_final | TAGS=[documentation,dashboard,integration,planning]
Triangulum Lx 1.1.md | PURPOSE=high_level_refactor_unification_plan_guiding_document | TAGS=[documentation,planning,architecture]
TriangulumSystemFilesGuide.md | PURPOSE=guide_to_final_system_files_consolidated | TAGS=[documentation,meta]
Triangulum_Agentic_System_Guide.md | PURPOSE=guide_final_agentic_system | TAGS=[documentation,agent]
Triangulum_Agentic_Testing_Guide.md | PURPOSE=testing_guide_final_agentic_system | TAGS=[documentation,agent,test]
Triangulum_Testing_Plan.md | PURPOSE=project_testing_plan_final | TAGS=[documentation,planning,test]
config/triangulum_config.json | PURPOSE=main_system_configuration_canonical | TAGS=[config,json,core,system_parameters]
docker-compose.yml | PURPOSE=docker_compose_configuration_final_services | TAGS=[config,docker,deployment,orchestration]
docker/Dockerfile.dashboard | PURPOSE=dockerfile_consolidated_dashboard_service | TAGS=[build,docker,gui,dashboard,deployment]
docker/Dockerfile.engine | PURPOSE=dockerfile_main_engine_service | TAGS=[build,docker,core,engine,deployment]
docker/Dockerfile.hub | PURPOSE=dockerfile_human_hub_service_if_kept | TAGS=[build,docker,api,human_interaction,deployment]
docker/grafana/dashboards/triangulum.json | PURPOSE=grafana_dashboard_definition_final | TAGS=[config,json,monitoring,visualization,grafana]
docker/grafana/provisioning/datasources/prometheus.yml | PURPOSE=grafana_datasource_config_prometheus_final | TAGS=[config,yaml,monitoring,grafana,prometheus]
docker/prometheus.yml | PURPOSE=prometheus_scrape_configuration_final | TAGS=[config,yaml,monitoring,metrics,prometheus]
docs/agent_communication_protocol.md | PURPOSE=documentation_agent_communication_protocol_final | TAGS=[documentation,api,agent,communication]
docs/self_healing.md | PURPOSE=documentation_self_healing_mechanism_final | TAGS=[documentation,core,self_healing,design]
examples/agent_communication_demo.py | PURPOSE=demo_script_agent_communication_canonical | TAGS=[example,python,demo,agent,communication]
examples/self_healing_demo.py | PURPOSE=demo_script_self_healing_canonical | TAGS=[example,python,demo,self_healing]
pyproject.toml | PURPOSE=python_project_configuration_final | TAGS=[config,build,python,poetry]
pytest.ini | PURPOSE=pytest_configuration_final | TAGS=[config,test,python,pytest]
requirements.txt | PURPOSE=python_dependency_list_final | TAGS=[config,dependencies,python,pip]
run_triangulum_system.py | PURPOSE=script_main_entry_point_to_run_system | TAGS=[script,python,runner,core] # (Hypothetical essential runner)
scripts/analyze_code_relationships.py | PURPOSE=cli_tool_analyze_code_relationships_kept | TAGS=[python,cli,tool,analysis,graph]
scripts/bug_detector_cli.py | PURPOSE=cli_tool_bug_detector_agent_kept | TAGS=[python,cli,tool,agent,bug_detection]
setup.py | PURPOSE=python_package_setup_script_final | TAGS=[build,python,config,setuptools]
tests/README.md | PURPOSE=documentation_testing_framework_final | TAGS=[documentation,test]
tests/unit/test_orchestrator_agent.py | PURPOSE=test_unit_orchestrator_agent | TAGS=[test,python,unit,agent,orchestration]
tests/integration/test_full_workflow.py | PURPOSE=test_integration_full_system_workflow | TAGS=[test,python,integration,system]
triangulum_dashboard_final_consolidated/index.html | PURPOSE=gui_entrypoint_canonical_dashboard | TAGS=[gui,dashboard,report,visualization,canonical]
triangulum_dashboard_final_consolidated/js/main.js | PURPOSE=gui_logic_main_javascript_canonical_dashboard | TAGS=[javascript,gui,dashboard,client_side]
triangulum_dashboard_final_consolidated/css/style.css | PURPOSE=styling_canonical_dashboard | TAGS=[css,gui,dashboard]
triangulum_data/feedback.db | PURPOSE=database_user_system_feedback_storage_persisted | TAGS=[data,database,feedback,sqldb]
triangulum_data/llm_response_cache.db | PURPOSE=database_llm_response_cache_persisted | TAGS=[data,database,llm,cache,sqldb]
triangulum_lx/__init__.py | PURPOSE=python_package_initializer_triangulum_lx | TAGS=[python,core]
triangulum_lx/agents/__init__.py | PURPOSE=python_package_initializer_agents_submodule | TAGS=[python,core,agent]
triangulum_lx/agents/agent_factory.py | PURPOSE=core_agent_creation_management_factory | TAGS=[python,core,agent,factory_pattern]
triangulum_lx/agents/base_agent.py | PURPOSE=core_abstract_base_class_specialized_agents | TAGS=[python,core,agent,abc]
triangulum_lx/agents/bug_detector_agent.py | PURPOSE=agent_logic_bug_detection_canonical | TAGS=[python,agent,analysis,bug_detection]
triangulum_lx/agents/enhanced_message_bus.py | PURPOSE=core_agent_communication_message_queue_canonical | TAGS=[python,core,agent,communication]
triangulum_lx/agents/implementation_agent.py | PURPOSE=agent_logic_code_generation_repair_canonical | TAGS=[python,agent,repair,code_generation]
triangulum_lx/agents/llm_config.py | PURPOSE=config_llm_provider_agent_model_mappings | TAGS=[python,config,llm]
triangulum_lx/agents/memory_manager.py | PURPOSE=core_agent_communication_memory_management | TAGS=[python,core,agent,communication]
triangulum_lx/agents/message.py | PURPOSE=core_data_model_agent_communication_protocol | TAGS=[python,core,agent,communication,schema]
triangulum_lx/agents/message_schema.json | PURPOSE=schema_validation_agent_communication_protocol | TAGS=[json,schema,agent,communication]
triangulum_lx/agents/message_schema.py | PURPOSE=core_validation_logic_agent_communication_protocol | TAGS=[python,core,agent,communication,validation]
triangulum_lx/agents/message_schema_validator.py | PURPOSE=core_message_schema_validation_tool | TAGS=[python,core,agent,communication,validation]
triangulum_lx/agents/orchestrator_agent.py | PURPOSE=core_agent_workflow_coordination_management_canonical | TAGS=[python,core,agent,orchestration,workflow]
triangulum_lx/agents/priority_analyzer_agent.py | PURPOSE=agent_logic_task_issue_prioritization_canonical | TAGS=[python,agent,analysis]
triangulum_lx/agents/relationship_analyst_agent.py | PURPOSE=agent_logic_code_relationship_analysis_canonical | TAGS=[python,agent,analysis,graph]
triangulum_lx/agents/response_cache.py | PURPOSE=core_llm_response_caching_determinism | TAGS=[python,core,llm,cache]
triangulum_lx/agents/response_handling.py | PURPOSE=core_agent_communication_large_response_utilities | TAGS=[python,core,agent,communication,utility]
triangulum_lx/agents/roles.py | PURPOSE=config_llm_prompts_agent_roles | TAGS=[python,config,llm,agent]
triangulum_lx/agents/router.py | PURPOSE=core_agent_task_routing_canonical | TAGS=[python,core,agent,coordination]
triangulum_lx/agents/strategy_agent.py | PURPOSE=agent_logic_repair_strategy_formulation_canonical | TAGS=[python,agent,planning,repair]
triangulum_lx/agents/thought_chain.py | PURPOSE=core_data_structure_reasoning_chain_persistence | TAGS=[python,core,agent,reasoning]
triangulum_lx/agents/thought_chain_manager.py | PURPOSE=core_reasoning_chain_management_coordination | TAGS=[python,core,agent,reasoning]
triangulum_lx/agents/verification_agent.py | PURPOSE=agent_logic_fix_verification_validation_canonical | TAGS=[python,agent,test,validation]
triangulum_lx/config/parameters.json | PURPOSE=config_system_operational_parameters_canonical | TAGS=[json,config,core,tuning]
triangulum_lx/core/__init__.py | PURPOSE=python_package_initializer_core_submodule | TAGS=[python,core,engine]
triangulum_lx/core/engine.py | PURPOSE=core_engine_component_management_lifecycle_canonical | TAGS=[python,core,engine,orchestration]
triangulum_lx/core/exceptions.py | PURPOSE=core_custom_exception_hierarchy | TAGS=[python,core,error_handling]
triangulum_lx/core/state.py | PURPOSE=core_system_state_definitions_management | TAGS=[python,core,engine,state]
triangulum_lx/core/transition.py | PURPOSE=core_state_machine_transition_logic | TAGS=[python,core,engine,state_machine]
triangulum_lx/core/monitor.py | PURPOSE=core_system_monitoring_progress_tracking | TAGS=[python,core,monitoring,metrics]
triangulum_lx/core/parallel_executor.py | PURPOSE=core_concurrent_task_execution_management | TAGS=[python,core,concurrency,scheduler]
triangulum_lx/core/rollback_manager.py | PURPOSE=core_transactional_rollback_state_management | TAGS=[python,core,state,transaction,rollback]
triangulum_lx/core/startup_manager.py | PURPOSE=core_system_startup_self_healing_manager_canonical | TAGS=[python,core,self_healing,startup]
triangulum_lx/core/compatibility.py | PURPOSE=core_utility_version_control_migration | TAGS=[python,core,utility,versioning]
triangulum_lx/core/tracing.py | PURPOSE=core_observability_tracing_monitoring | TAGS=[python,core,utility,monitoring,telemetry]
triangulum_lx/core/entropy_explainer.py | PURPOSE=core_utility_entropy_explanations | TAGS=[python,core,utility,entropy]
triangulum_lx/core/engine_event_extension.py | PURPOSE=core_event_system_learning_interface | TAGS=[python,core,event_handling,learning]
triangulum_lx/core/engine_learning_integration.py | PURPOSE=core_integration_engine_learning_components | TAGS=[python,core,learning,integration]
triangulum_lx/core/learning_enabled_engine.py | PURPOSE=core_engine_with_learning_capabilities | TAGS=[python,core,engine,learning]
triangulum_lx/core/learning_manager.py | PURPOSE=core_learning_coordination_data_model_management | TAGS=[python,core,learning]
triangulum_lx/providers/__init__.py | PURPOSE=python_package_initializer_providers_submodule | TAGS=[python,core,llm,provider_interface]
triangulum_lx/providers/base.py | PURPOSE=core_llm_provider_abstract_base_class | TAGS=[python,core,llm,provider_interface,abc]
triangulum_lx/providers/factory.py | PURPOSE=core_llm_provider_factory_management_canonical | TAGS=[python,core,llm,factory,configuration]
triangulum_lx/providers/request_manager.py | PURPOSE=core_llm_resilient_request_management | TAGS=[python,core,llm,resilience,cache]
triangulum_lx/providers/openai.py | PURPOSE=llm_provider_openai_api_client | TAGS=[python,llm,provider,openai]
triangulum_lx/providers/anthropic.py | PURPOSE=llm_provider_anthropic_api_client | TAGS=[python,llm,provider,anthropic]
triangulum_lx/providers/groq.py | PURPOSE=llm_provider_groq_api_client | TAGS=[python,llm,provider,groq]
triangulum_lx/providers/openrouter.py | PURPOSE=llm_provider_openrouter_api_client | TAGS=[python,llm,provider,openrouter]
triangulum_lx/providers/local.py | PURPOSE=llm_provider_local_model_support_ollama_lmstudio | TAGS=[python,llm,provider,local]
triangulum_lx/providers/o3_provider.py | PURPOSE=llm_provider_openai_o3_specialized | TAGS=[python,llm,provider,openai,o3]
triangulum_lx/providers/capability_discovery.py | PURPOSE=llm_provider_capability_discovery_utility | TAGS=[python,llm,utility,introspection]
triangulum_lx/tooling/__init__.py | PURPOSE=python_package_initializer_tooling_submodule | TAGS=[python,core,tooling]
triangulum_lx/tooling/graph_models.py | PURPOSE=core_data_model_dependency_graph_representation | TAGS=[python,core,tooling,graph,data_structure]
triangulum_lx/tooling/dependency_graph.py | PURPOSE=tooling_dependency_graph_construction_analysis_canonical | TAGS=[python,tooling,graph,analysis,parser]
triangulum_lx/tooling/patch_bundle.py | PURPOSE=tooling_patch_bundle_management | TAGS=[python,tooling,patch,git]
triangulum_lx/tooling/repair.py | PURPOSE=tooling_code_repair_change_management_canonical | TAGS=[python,tooling,repair,patch,transaction]
triangulum_lx/tooling/test_runner.py | PURPOSE=tooling_test_execution_automation_canonical | TAGS=[python,tooling,test,pytest,unittest,automation]
triangulum_lx/tooling/scope_filter.py | PURPOSE=utility_file_filtering_scope_management | TAGS=[python,utility,file_system,filter]
triangulum_lx/tooling/compress.py | PURPOSE=utility_text_compression_summarization | TAGS=[python,utility,text]
triangulum_lx/tooling/auto_verification.py | PURPOSE=tooling_automated_fix_verification | TAGS=[python,tooling,test,verification]
triangulum_lx/tooling/canary_runner.py | PURPOSE=tooling_canary_test_execution_docker | TAGS=[python,tooling,test,deployment,docker]
triangulum_lx/tooling/fix_impact_tracker.py | PURPOSE=tooling_fix_impact_analysis_tracking | TAGS=[python,tooling,analysis,change_tracking]
triangulum_lx/tooling/incremental_analyzer.py | PURPOSE=tooling_incremental_dependency_analysis | TAGS=[python,tooling,graph,analysis,optimization]
triangulum_lx/tooling/relationship_context_provider.py | PURPOSE=tooling_code_relationship_context_provision | TAGS=[python,tooling,analysis,context]
triangulum_lx/tooling/repo_analyzer.py | PURPOSE=tooling_repository_wide_code_analysis | TAGS=[python,tooling,analysis,repository]
triangulum_lx/tooling/smoke_runner.py | PURPOSE=tooling_smoke_test_execution | TAGS=[python,tooling,test,smoke_test]
triangulum_lx/tooling/timeout_manager.py | PURPOSE=utility_adaptive_timeout_checkpoint_management | TAGS=[python,utility,timeout,state_management]
triangulum_lx/verification/__init__.py | PURPOSE=python_package_initializer_verification_submodule | TAGS=[python,core,verification]
triangulum_lx/verification/core.py | PURPOSE=core_verification_system_test_generation_sandbox_canonical | TAGS=[python,core,verification,test,automation,sandbox]
triangulum_lx/verification/metrics.py | PURPOSE=core_metrics_collection_reporting_verification | TAGS=[python,core,verification,metrics,reporting]
triangulum_lx/verification/code_fixer.py | PURPOSE=tooling_automated_code_fixing_verification | TAGS=[python,tooling,verification,repair,automation]
triangulum_lx/verification/adaptive.py | PURPOSE=core_adaptive_verification_strategy_selection | TAGS=[python,core,verification,test,ai,learning]
triangulum_lx/verification/ci.py | PURPOSE=tooling_ci_cd_integration_reporting | TAGS=[python,tooling,ci,reporting,verification]
triangulum_lx/verification/plugins/__init__.py | PURPOSE=python_package_initializer_verification_plugins | TAGS=[python,core,verification,plugin]
triangulum_lx/verification/plugins/python.py | PURPOSE=verification_plugin_python_specific_checks | TAGS=[python,verification,plugin,linter,security]

**Dependency Hotspots (Top 10 by in-degree - Based on *Final System* Files)**
1.  `triangulum_lx/agents/message.py` (↑ most agents, orchestrator_agent)
2.  `triangulum_lx/agents/base_agent.py` (↑ all concrete agent implementations)
3.  `triangulum_lx/core/engine.py` (↑ orchestrator_agent, startup_manager)
4.  `triangulum_lx/providers/base.py` (↑ all concrete LLM provider implementations)
5.  `triangulum_lx/tooling/graph_models.py` (↑ dependency_graph.py)
6.  `triangulum_lx/agents/llm_config.py` (↑ providers/factory.py, request_manager.py, agents using LLMs)
7.  `triangulum_lx/core/exceptions.py` (↑ many modules)
8.  `config/triangulum_config.json` (↑ core/engine.py, various agents)
9.  `triangulum_lx/agents/enhanced_message_bus.py` (↑ all agents)
10. `triangulum_lx/agents/orchestrator_agent.py` (↑ startup_manager, potentially some CLI runners)

**Deletion / Refactor Queue**
*   DEL : `file1.py`
*   DEL : `fix_agent_message_params.py` (and all other root `fix_*.py` scripts after review)
*   DEL : All `*.bak` files (e.g., `triangulum_lx/agents/agent_factory.py.bak`)
*   DEL : `triangulum_lx/agents/Old_Triangulum_Engine_Report.md`
*   DEL : `llm_providers.py` (root script)
*   DEL : All dashboard directories EXCEPT `triangulum_dashboard_final_consolidated/`
*   DEL : `triangulum_lx/agents/coordinator.py`, `triangulum_lx/agents/enhanced_coordinator.py`, `triangulum_lx/agents/meta_agent.py`
*   DEL : `triangulum_lx/agents/message_bus.py`
*   DEL : `TriangulumSystemFilesGuide_Updated.md`
*   DEL : `example_files/`, `simple_test_folder/`, `strategy_example_files/`, `quantum_analysis_output/demo_project/` (after migrating useful content)
*   DEL : `fixwurx_eval/` (after migrating useful content)
*   DEL : `triangulum_lx/self_heal.py`
*   DEL : `triangulum_unified_config.json` (after merging)
*   DEL : Most root-level `run_*.py` scripts (after review and integration into tests/demos or main entry points)
*   DEL : Most root-level `FINAL_*.md`, `PH1-*.md` report/task files (archive if necessary)
*   REFACTOR : `triangulum_dashboard_final_consolidated/` to be the single source of truth for the dashboard.
*   REFACTOR : `triangulum_lx/agents/orchestrator_agent.py` to incorporate all coordination logic.
*   REFACTOR : `triangulum_lx/agents/enhanced_message_bus.py` to be the sole message bus.
*   REFACTOR : `TriangulumSystemFilesGuide.md` to be the single, updated guide.
*   REFACTOR : `examples/` to house all consolidated demos.
*   REFACTOR : `triangulum_self_heal.py` (root) functionality into `triangulum_lx/core/startup_manager.py`.
*   REFACTOR : `triangulum_lx/tooling/dependency_analyzer.py` logic into `triangulum_lx/tooling/dependency_graph.py` or clearly define its distinct purpose.
*   REFACTOR : `triangulum_lx/agents/CODE_OF_CONDUCT.md` move to root or `docs/`.

**Consolidation Roadmap (Detailed Steps)**

1.  **STEP-01: Establish Canonical Core Components & Configuration**
    *   **Action:** Modify `triangulum_lx/agents/orchestrator_agent.py` to be the sole system coordinator.
        *   *Inspiration:* Review `meta_agent.py` for any unique task decomposition or advanced routing logic not present in `orchestrator_agent.py` and merge it. Ensure `enhanced_coordinator.py`'s loop prevention and effectiveness scoring are considered or adapted if superior to `orchestrator_agent.py`'s task management.
    *   **Action:** Standardize on `triangulum_lx/agents/enhanced_message_bus.py`.
        *   *Inspiration:* Ensure all features of `message_bus.py` (if any unique ones exist) are covered by `enhanced_message_bus.py`. Update all agent constructors and references.
    *   **Action:** Designate `triangulum_lx/providers/factory.py` as the single LLM provider factory.
        *   *Inspiration:* Delete root `llm_providers.py`. Ensure `factory.py` can handle all provider types previously managed by the root script.
    *   **Action:** Create `triangulum_lx/core/startup_manager.py` and move the logic from the root `triangulum_self_heal.py` (specifically `SystemStartupManager`) into it.
        *   *Inspiration:* `triangulum_self_heal.py` contains `SystemStartupManager`. This class should be relocated. Update all import paths that referenced the old location (e.g., in `triangulum_lx/self_heal.py` which was just a re-export).
    *   **Action:** Consolidate all system parameters.
        *   *Inspiration:* Review `config/triangulum_config.json`, `triangulum_lx/config/parameters.json`, and the (potentially redundant) `triangulum_unified_config.json`. Merge all unique and necessary parameters into `config/triangulum_config.json` (for static structural config) and `triangulum_lx/config/parameters.json` (for tunable operational parameters).
    *   *Files involved (targets for modification/creation):* `orchestrator_agent.py`, `enhanced_message_bus.py`, `factory.py`, `startup_manager.py`, `triangulum_config.json`, `parameters.json`.
    *   *Files involved (targets for deletion):* `coordinator.py`, `enhanced_coordinator.py`, `meta_agent.py`, `message_bus.py`, root `llm_providers.py`, root `triangulum_self_heal.py`, `triangulum_unified_config.json`.

2.  **STEP-02: Unify Dashboards**
    *   **Action:** Identify all unique visualization components and data handling logic from the various dashboard directories (e.g., agent network from `agentic_dashboard_full_demo`, specific views from `quantum_analysis_output/dashboard`).
    *   **Action:** Integrate these features into `triangulum_dashboard_final_consolidated/`. This will involve modifying its `index.html`, `js/main.js`, and potentially adding new JS/CSS files or data structures.
        *   *Inspiration:* The `backend_connector.js` files in different dashboards might hint at different data sources or formats that need to be supported by the consolidated dashboard's `main.js`.
    *   **Action:** Update `run_agentic_dashboard.py` (or a new canonical `run_dashboard.py`) to exclusively launch `triangulum_dashboard_final_consolidated/index.html`.
    *   *Files involved (targets for modification/creation):* `triangulum_dashboard_final_consolidated/*`, `run_agentic_dashboard.py`.
    *   *Files involved (targets for deletion):* All other dashboard directories.

3.  **STEP-03: Consolidate Core Tooling (Dependency Analysis)**
    *   **Action:** Analyze `triangulum_lx/tooling/dependency_analyzer.py` and the `DependencyAnalyzer` within `triangulum_lx/tooling/dependency_graph.py`.
        *   *Inspiration:* `dependency_graph.py` uses `graph_models.py` and supports multiple languages. `dependency_analyzer.py` seems more Python/JS focused with regex. Prioritize `dependency_graph.py`'s structure.
    *   **Action:** Merge any unique, valuable analysis capabilities (e.g., "repair batches" logic if distinct and useful) from `dependency_analyzer.py` into the `DependencyAnalyzer` class within `dependency_graph.py`.
    *   **Action:** Ensure the path handling fixes from `dependency_graph_path_fix.py` are correctly integrated into the chosen `DependencyGraphBuilder` in `dependency_graph.py`.
    *   *Files involved (targets for modification/creation):* `triangulum_lx/tooling/dependency_graph.py`.
    *   *Files involved (targets for deletion):* `triangulum_lx/tooling/dependency_analyzer.py`, `dependency_graph_path_fix.py`.

4.  **STEP-04: Prune Redundant/Orphaned Scripts & Consolidate Examples**
    *   **Action:** Delete `.bak` files, `file1.py`.
    *   **Action:** Systematically review each root-level `fix_*.py` script. Determine if its functionality is now handled by an agent (e.g., `ImplementationAgent`, `CodeFixer`) or a core tool. If so, delete. If a script provides unique, still-needed functionality not covered elsewhere (e.g., a very specific data migration or setup step), document it and consider moving it to `scripts/` with a clear name.
    *   **Action:** Create `examples/` directory if it doesn't exist. Review `example_files/`, `simple_test_folder/`, `strategy_example_files/`, `quantum_analysis_output/demo_project/`. Migrate *distinct and valuable* demo scripts to `examples/`, ensuring they use canonical components. Delete the source directories.
    *   **Action:** Evaluate `fixwurx_eval/`. If `fixwurx_snapshot` or `fixwurx_backup` represent a useful, self-contained test case for the system, consider cleaning it up and moving it to `tests/integration/fixwurx_case/` or `examples/fixwurx_case/`. Delete the rest of `fixwurx_eval/` (cache, reports, intermediate repair plans).
    *   *Files involved (targets for modification/creation):* `examples/` directory.
    *   *Files involved (targets for deletion):* As listed.

5.  **STEP-05: Standardize Documentation**
    *   **Action:** Merge content of `TriangulumSystemFilesGuide_Updated.md` into `TriangulumSystemFilesGuide.md`.
    *   **Action:** Create a main `README.md` at the project root. This README should provide a high-level overview, setup instructions, and links to more detailed documentation.
    *   **Action:** Create a `docs/` directory. Move essential detailed documents like `agent_communication_protocol.md`, `self_healing.md`, `Triangulum_Agentic_System_Guide.md`, `Triangulum_Agentic_Testing_Guide.md`, and the merged `TriangulumSystemFilesGuide.md` into `docs/`. Update links in the main `README.md`.
    *   **Action:** Move `triangulum_lx/agents/CODE_OF_CONDUCT.md` to the project root or `docs/community/`.
    *   **Action:** Review all other `.md` files (e.g., `FINAL_*.md`, `PH1-*.md`, `monitoring_readme.md`). If they contain currently relevant information not covered elsewhere, integrate it into the new `docs/` structure or the main `README.md`. Otherwise, archive them outside the repository or delete if obsolete.
    *   *Files involved (targets for modification/creation):* `README.md`, `docs/` directory and its contents.
    *   *Files involved (targets for deletion):* Old `README*.md`, `*_Updated.md` docs, old reports, `CODE_OF_CONDUCT.md` from agents.

6.  **STEP-06: Full System Integration & Testing**
    *   **Action:** Update `triangulum_lx/core/startup_manager.py` to correctly initialize all canonical components (Orchestrator, EnhancedMessageBus, ProviderFactory, consolidated config paths).
    *   **Action:** Review and update `docker-compose.yml` and all `Dockerfile.*` files in `docker/` to ensure they build and run services using the consolidated components, correct paths, and unified configuration.
    *   **Action:** Verify `docker/prometheus.yml` and `docker/grafana/dashboards/triangulum.json` correctly target metrics exposed by the unified system.
    *   **Action:** Review all agent implementations in `triangulum_lx/agents/` (e.g., `BugDetectorAgent`, `StrategyAgent`, `ImplementationAgent`, `VerificationAgent`, `RelationshipAnalystAgent`, `PriorityAnalyzerAgent`) to ensure they:
        *   Use `EnhancedMessageBus` for all communications.
        *   Interact with the `OrchestratorAgent` for tasking and coordination.
        *   Load configuration from the canonical `config/triangulum_config.json` and `triangulum_lx/config/parameters.json`.
        *   Use the `ProviderFactory` for LLM access.
    *   **Action:** Identify any common helper functions currently duplicated across agents or core modules. Refactor these into a new `triangulum_lx/utils/` package or appropriate existing core modules.
    *   **Action:** Update all test files in `tests/` to import and test the canonical components. Ensure test configurations (`pytest.ini`) are valid.
    *   **Action:** Review any `run_*.py` scripts that are kept. If they are for testing, integrate them into the `pytest` framework. If they are demo runners, ensure they use consolidated components and update documentation. If they are essential CLI entry points for system operation (like a hypothetical `run_triangulum_system.py`), ensure they are robust.
    *   **Action:** Execute all tests: `pytest tests/`. Address any failures.
    *   *Files involved:* All files in the system are potentially touched or verified in this step.

**ETA & Risk**
*   Est. commits : ~20-35
*   Major risks :
    *   Circular dependencies during refactoring.
    *   Hidden assumptions in different duplicated components causing issues when unified.
    *   Breaking changes to essential `run_*.py` script interfaces or deployment methods.
    *   Incomplete feature migration from deprecated components to canonical ones.
    *   Test suite gaps after refactoring, leading to undetected regressions.
    *   Misinterpretation of "essential" files, leading to accidental deletion of a subtly used script or config.
END-PLAN
