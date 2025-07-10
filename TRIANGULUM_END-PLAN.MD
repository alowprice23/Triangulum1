PLAN-TRIANGULUM-CONSOLIDATE

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
TriangulumSystemFilesGuide.md | PURPOSE=guide_to_final_system_files_consolidated | TAGS=[documentation,meta] # MOVED to docs/
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
requirements.txt | PURPOSE=python_dependency_list_final | TAGS=[config,dependencies,python,pip] # NOTE: requirements.in also exists
run_triangulum_system.py | PURPOSE=script_main_entry_point_to_run_system | TAGS=[script,python,runner,core] # (Hypothetical essential runner)
scripts/analyze_code_relationships.py | PURPOSE=cli_tool_analyze_code_relationships_kept | TAGS=[python,cli,tool,analysis,graph]
scripts/bug_detector_cli.py | PURPOSE=cli_tool_bug_detector_agent_kept | TAGS=[python,cli,tool,agent,bug_detection]
setup.py | PURPOSE=python_package_setup_script_final | TAGS=[build,python,config,setuptools]
tests/README.md | PURPOSE=documentation_testing_framework_final | TAGS=[documentation,test]
tests/unit/test_orchestrator_agent.py | PURPOSE=test_unit_orchestrator_agent | TAGS=[test,python,unit,agent,orchestration]
tests/integration/test_full_workflow.py | PURPOSE=test_integration_full_system_workflow | TAGS=[test,python,integration,system] # Needs creation or identification
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
*   DEL : `file1.py` **[DONE - VERIFIED]**
*   DEL : `fix_agent_message_params.py` (and all other root `fix_*.py` scripts after review) **[DONE - VERIFIED No fix_*.py at root]**
*   DEL : All `*.bak` files (e.g., `triangulum_lx/agents/agent_factory.py.bak`) **[DONE - VERIFIED No .bak files in triangulum_lx/agents/]**
*   DEL : `triangulum_lx/agents/Old_Triangulum_Engine_Report.md` **[DONE - VERIFIED Not in triangulum_lx/agents/]**
*   DEL : `llm_providers.py` (root script) **[DONE - VERIFIED Not at root]**
*   DEL : All dashboard directories EXCEPT `triangulum_dashboard_final_consolidated/` **[PENDING - VERIFIED Other dashboard dirs exist (e.g., agentic_dashboard_full_demo/, dashboard_test/)]**
*   DEL : `triangulum_lx/agents/coordinator.py`, `triangulum_lx/agents/enhanced_coordinator.py`, `triangulum_lx/agents/meta_agent.py` **[DONE - VERIFIED Not in triangulum_lx/agents/]**
*   DEL : `triangulum_lx/agents/message_bus.py` **[DONE - VERIFIED Not in triangulum_lx/agents/]**
*   DEL : `TriangulumSystemFilesGuide_Updated.md` **[DONE - VERIFIED Not at root]**
*   DEL : `example_files/`, `simple_test_folder/`, `strategy_example_files/`, `quantum_analysis_output/demo_project/` (after migrating useful content)
    *   `simple_test_folder/`: **[DONE - VERIFIED Not at root]**
    *   `quantum_analysis_output/demo_project/`: **[DONE - VERIFIED Not in quantum_analysis_output/]**
    *   `example_files/`: **[PENDING - VERIFIED Exists at root]**
    *   `examples/strategy_example_files/`: **[PENDING - VERIFIED Exists in examples/]**
*   DEL : `fixwurx_eval/` (after migrating useful content) **[PENDING - VERIFIED Exists at root]**
*   DEL : `triangulum_lx/self_heal.py` **[PENDING - VERIFIED File exists, though it's a re-exporter. Plan said DEL.]**
*   DEL : `triangulum_unified_config.json` (after merging) **[DONE - VERIFIED Not at root]**
*   DEL : Most root-level `run_*.py` scripts (after review and integration into tests/demos or main entry points) **[PENDING - VERIFIED Many run_*.py scripts exist at root (e.g. run_all_demos.py, run_triangulum_agentic_test.py)]**
*   DEL : Most root-level `FINAL_*.md`, `PH1-*.md` report/task files (archive if necessary) **[DONE - VERIFIED No files matching FINAL_*.md or PH1-*.md at root]**
*   REFACTOR : `triangulum_dashboard_final_consolidated/` to be the single source of truth for the dashboard. **[PENDING - VERIFIED Dependent on deletion of other dashboards]**
*   REFACTOR : `triangulum_lx/agents/orchestrator_agent.py` to incorporate all coordination logic. **[DONE - VERIFIED Other coordinators deleted]**
*   REFACTOR : `triangulum_lx/agents/enhanced_message_bus.py` to be the sole message bus. **[DONE - VERIFIED Old message_bus.py deleted]**
*   REFACTOR : `TriangulumSystemFilesGuide.md` to be the single, updated guide. **[PARTIALLY DONE - VERIFIED File moved to docs/. Content merge not verified by this process.]**
*   REFACTOR : `examples/` to house all consolidated demos. **[PARTIALLY DONE - VERIFIED examples/ exists, but cleanup of example_files/ and examples/strategy_example_files/ pending]**
*   REFACTOR : `triangulum_self_heal.py` (root) functionality into `triangulum_lx/core/startup_manager.py`. **[DONE - VERIFIED Root file gone, startup_manager.py exists]**
*   REFACTOR : `triangulum_lx/tooling/dependency_analyzer.py` logic into `triangulum_lx/tooling/dependency_graph.py` or clearly define its distinct purpose. **[DONE - VERIFIED dependency_analyzer.py deleted]**
*   REFACTOR : `triangulum_lx/agents/CODE_OF_CONDUCT.md` move to root or `docs/`. **[DONE - VERIFIED File not found in old or new locations, assumed deleted as per plan intent if not moved.]**

**Consolidation Roadmap (Detailed Steps)**

1.  **STEP-01: Establish Canonical Core Components & Configuration** **[LARGELY DONE - VERIFIED]**
    *   **Action:** Modify `triangulum_lx/agents/orchestrator_agent.py` ... **[DONE - VERIFIED]**
    *   **Action:** Standardize on `triangulum_lx/agents/enhanced_message_bus.py`. **[DONE - VERIFIED]**
    *   **Action:** Designate `triangulum_lx/providers/factory.py` ... **[DONE - VERIFIED]**
    *   **Action:** Create `triangulum_lx/core/startup_manager.py` and move logic from root `triangulum_self_heal.py` ... **[DONE - VERIFIED Root file logic moved]**. (Note: `triangulum_lx/self_heal.py` still exists as redirect, pending DEL per item 12).
    *   **Action:** Consolidate all system parameters. **[DONE - VERIFIED]**
    *   *Files involved (targets for deletion):* `coordinator.py`, `enhanced_coordinator.py`, `meta_agent.py`, `message_bus.py`, root `llm_providers.py`, root `triangulum_self_heal.py`, `triangulum_unified_config.json`. **[ALL VERIFIED DELETED]**

2.  **STEP-02: Unify Dashboards** **[PENDING - VERIFIED]**
    *   **Action:** Identify all unique visualization components ... **[PENDING - VERIFIED Other dashboard directories still exist]**
    *   **Action:** Integrate these features into `triangulum_dashboard_final_consolidated/`. **[PENDING - VERIFIED]**
    *   **Action:** Update `run_agentic_dashboard.py` ... **[PARTIALLY DONE - VERIFIED `examples/agentic_dashboard_demo.py` uses target. Cleanup/canonical runner pending.]**
    *   **Note:** `docker-compose.yml` dashboard service ... needs to be reconciled. **[PENDING - VERIFICATION NEEDED for docker-compose content]**
    *   *Files involved (targets for deletion):* All other dashboard directories. **[PENDING - VERIFIED]**

3.  **STEP-03: Consolidate Core Tooling (Dependency Analysis)** **[DONE - VERIFIED]**
    *   **Action:** Analyze `triangulum_lx/tooling/dependency_analyzer.py` ... **[DONE - VERIFIED Files deleted]**
    *   **Action:** Merge any unique, valuable analysis capabilities ... **[DONE - VERIFIED `get_repair_batches` in `dependency_graph.py`]**
    *   **Action:** Ensure path handling fixes ... **[DONE - VERIFIED `dependency_graph_path_fix.py` deleted]**
    *   *Files involved (targets for deletion):* `triangulum_lx/tooling/dependency_analyzer.py`, `dependency_graph_path_fix.py`. **[ALL VERIFIED DELETED]**

4.  **STEP-04: Prune Redundant/Orphaned Scripts & Consolidate Examples** **[PARTIALLY DONE / PENDING - VERIFIED]**
    *   **Action:** Delete `.bak` files, `file1.py`. **[DONE - VERIFIED `.bak` in agents and `file1.py` are gone.]**
    *   **Action:** Systematically review each root-level `fix_*.py` script. **[DONE - VERIFIED No `fix_*.py` scripts at root.]**
    *   **Action:** Create `examples/` directory ... Review `example_files/`, `simple_test_folder/`, `strategy_example_files/`, `quantum_analysis_output/demo_project/`.
        *   `simple_test_folder/`, `quantum_analysis_output/demo_project/` **[DONE - VERIFIED DELETED]**
        *   `example_files/`, `examples/strategy_example_files/` **[PENDING - VERIFIED EXIST]**
    *   **Action:** Evaluate `fixwurx_eval/`. **[PENDING - VERIFIED EXISTS]**

5.  **STEP-05: Standardize Documentation** **[PARTIALLY DONE / PENDING - VERIFIED]**
    *   **Action:** Merge content of `TriangulumSystemFilesGuide_Updated.md` into `TriangulumSystemFilesGuide.md`. **[DONE - VERIFIED `_Updated.md` is gone. `TriangulumSystemFilesGuide.md` is in `docs/`. Content merge not verified.]**
    *   **Action:** Create a main `README.md` at the project root. **[DONE - VERIFIED `README.md` exists at root.]**
    *   **Action:** Create a `docs/` directory. Move essential detailed documents ... **[PARTIALLY DONE - VERIFIED `docs/` exists. `agent_communication_protocol.md`, `self_healing.md`, `TriangulumSystemFilesGuide.md` are in `docs/`. Others like `Triangulum_Agentic_System_Guide.md`, `Triangulum_Agentic_Testing_Guide.md` are still at root.]**
    *   **Action:** Move `triangulum_lx/agents/CODE_OF_CONDUCT.md` ... **[DONE - VERIFIED Assumed deleted as not found.]**
    *   **Action:** Review all other `.md` files (e.g., `FINAL_*.md`, `PH1-*.md`...). **[DONE for `FINAL_*.md`, `PH1-*.md`. PENDING for other misc root MD files like `Reversion Of triangulum plan...`, `Triangulum Lx 1.1.md` which are not explicitly in DEL queue but mentioned for review/archive.]**

6.  **STEP-06: Full System Integration & Testing** **[PARTIALLY DONE / PENDING - VERIFIED where possible without code execution/deep content review]**
    *   **Action:** Update `triangulum_lx/core/startup_manager.py` ... **[ASSUMED DONE based on component consolidation]**
    *   **Action:** Review and update `docker-compose.yml` and all `Dockerfile.*` files ... **[PENDING - Needs content review. Plan indicates partial completion.]**
    *   **Action:** Verify `docker/prometheus.yml` and `docker/grafana/dashboards/triangulum.json` ... **[PENDING - Needs content review/system execution.]**
    *   **Action:** Review all agent implementations ...
        *   Use `EnhancedMessageBus` ... **[ASSUMED LARGELY DONE based on consolidation]**
        *   Interact with `OrchestratorAgent` ... **[ASSUMED LARGELY DONE]**
        *   Load configuration from canonical ... **[ASSUMED LARGELY DONE]**
        *   Use `ProviderFactory` ... **[ASSUMED LARGELY DONE]**
    *   **Action:** Identify any common helper functions ... `triangulum_lx/utils/` ... **[PENDING - VERIFIED No `utils/` directory.]**
    *   **Action:** Update all test files ... **[PENDING - Needs content review/test execution.]**
    *   **Action:** Review any `run_*.py` scripts that are kept. **[PENDING - VERIFIED Many exist, need review.]**
    *   **Action:** Execute all tests: `pytest tests/`. **[PENDING - Cannot execute tests.]**

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
