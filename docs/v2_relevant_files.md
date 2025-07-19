# v2 Relevant Files

## Shell

*   `triangulum_lx/scripts/cli.py`
*   `triangulum_lx/human/interactive_mode.py`
*   `docs/v2_shell_design.md`

## Core

*   `triangulum_lx/core/engine.py`
*   `triangulum_lx/core/state.py`
*   `triangulum_lx/core/transition.py`
*   `triangulum_lx/core/monitor.py`
*   `triangulum_lx/core/exceptions.py`
*   `triangulum_lx/core/rollback_manager.py`
*   `triangulum_lx/core/entropy_explainer.py`
*   `triangulum_lx/core/parallel_executor.py`
*   `triangulum_lx/core/compatibility.py`
*   `triangulum_lx/core/tracing.py`

## Agents

*   `triangulum_lx/agents/meta_agent.py`
*   `triangulum_lx/agents/coordinator.py`
*   `triangulum_lx/agents/router.py`
*   `triangulum_lx/agents/roles.py`
*   `triangulum_lx/agents/response_cache.py`
*   `triangulum_lx/agents/llm_config.py`
*   `triangulum_lx/agents/enhanced_nine_agent_system.py`

## Tooling

*   `triangulum_lx/tooling/relationship_context_provider.py`
*   `triangulum_lx/tooling/code_relationship_analyzer.py`
*   `triangulum_lx/tooling/dependency_analyzer.py`
*   `triangulum_lx/tooling/repair.py`
*   `triangulum_lx/tooling/patch_bundle.py`
*   `triangulum_lx/tooling/smoke_runner.py`
*   `triangulum_lx/tooling/canary_runner.py`
*   `triangulum_lx/tooling/scope_filter.py`
*   `triangulum_lx/tooling/compress.py`
*   `triangulum_lx/tooling/test_runner.py`

## Providers

*   `triangulum_lx/providers/base.py`
*   `triangulum_lx/providers/factory.py`
*   `triangulum_lx/providers/request_manager.py`
*   `triangulum_lx/providers/openai.py`
*   `triangulum_lx/providers/anthropic.py`
*   `triangulum_lx/providers/groq.py`
*   `triangulum_lx/providers/openrouter.py`
*   `triangulum_lx/providers/local.py`
*   `triangulum_lx/providers/state_management.py`
*   `triangulum_lx/providers/capability_discovery.py`

## Monitoring

*   `triangulum_lx/monitoring/metrics.py`
*   `triangulum_lx/monitoring/metrics_exporter.py`
*   `triangulum_lx/monitoring/visualization.py`
*   `triangulum_lx/monitoring/dashboard_stub.py`
*   `triangulum_lx/monitoring/system_monitor.py`

## Goal Management

*   `triangulum_lx/goal/app_goal.yaml`
*   `triangulum_lx/goal/goal_loader.py`
*   `triangulum_lx/goal/prioritiser.py`

## Human Interaction

*   `triangulum_lx/human/feedback.py`
*   `triangulum_lx/human/hub.py`

## Learning

*   `triangulum_lx/learning/bug_predictor.py`
*   `triangulum_lx/learning/optimizer.py`
*   `triangulum_lx/learning/replay_buffer.py`

## Specification

*   `triangulum_lx/spec/ltl_properties.py`
*   `triangulum_lx/spec/model_checker.py`
*   `triangulum_lx/spec/performance_guarantees.py`
*   `triangulum_lx/spec/Triangulation.tla`
*   `triangulum_lx/spec/Triangulation.cfg`

## Experimental

*   `triangulum_lx/quantum/entanglement.py`
*   `triangulum_lx/future/roadmap.py`

## Scripts and Entry Points

*   `triangulum.py`
*   `triangulum_lx/scripts/bootstrap_demo.sh`
*   `scripts/analyze_code_relationships.py`
*   `scripts/discover_capabilities.py`
*   `scripts/run_benchmarks.py`

## Tests

*   `triangulum_lx/tests/unit/test_state.py`
*   `triangulum_lx/tests/unit/test_transition.py`
*   `triangulum_lx/tests/unit/test_meta_agent.py`
*   `triangulum_lx/tests/unit/test_coordinator.py`
*   `triangulum_lx/tests/unit/test_router.py`
*   `triangulum_lx/tests/unit/test_relationship_context_provider.py`
*   `triangulum_lx/tests/unit/test_engine.py`
*   `triangulum_lx/tests/smoke/test_simple_bug.py`
*   `tests/benchmarks/standard_prompts.yaml`

## Debug and Fix Files

*   `debug_imports.py`
*   `debug_triangulum_workflow.py`
*   `debug_with_relationships.py`
*   `event_loop_bug.py`
*   `event_loop_bug_fixed.py`
*   `file_resource_bug.py`
*   `file_resource_bug_fixed.py`
*   `fix_test_bug.py`
*   `test_bug.py`
*   `test_bug_fixed.py`
*   `integrated_triangulum_debug.py`
*   `triangulum_debug_orchestrator.py`
*   `triangulum_debug_system.py`
*   `triangulum_folder_debugger.py`
*   `triangulum_fix.py`
*   `triangulum_monitor.py`
*   `test_engine_monitor_bug.py`

## Integration and Improvement Files

*   `test_triangulum_comprehensive.py`
*   `test_triangulum_integration.py`
*   `triangulum_autogen_implementation.py`
*   `triangulum_autogen_o3_demo.py`
*   `triangulum_autonomous_improvement_executor.py`
*   `triangulum_autonomous_startup.py`
*   `triangulum_continuous_self_improvement.py`
*   `triangulum_comprehensive_self_assessment.py`
*   `triangulum_self_heal.py`
*   `triangulum_self_healing_session.py`
*   `triangulum_mathematical_self_healing.py`
*   `triangulum_adaptive_health.py`

## Experimental and Breakthrough Files

*   `triangulum_adaptive_breakthrough.py`
*   `triangulum_ultimate_breakthrough.py`
*   `triangulum_ultimate_self_test.py`
*   `triangulum_final_breakthrough.py`
*   `triangulum_real_world_application.py`
*   `triangulum_true_agent_demonstration.py`
*   `triangulum_full_system_activation.py`
*   `triangulum_next_improvement_cycle.py`
