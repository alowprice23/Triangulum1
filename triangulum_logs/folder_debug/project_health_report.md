# Triangulum Project Health Report

Generated: 2025-07-01 01:30:12

## Project Overview

- Project path: .
- Files analyzed: 122
- Relationships found: 2471

## Top 20 Files by Priority

| # | File | Priority Score | Reason |
|---|------|---------------|--------|
| 1 | triangulum_folder_debugger.py | 0.5723 | Many dependencies |
| 2 | repair.py | 0.4728 | Many dependencies |
| 3 | triangulum_gpt.py | 0.4642 | Many dependencies |
| 4 | triangulum_self_heal.py | 0.4533 | Many dependencies |
| 5 | triangulum_debug_orchestrator.py | 0.4468 | Many dependencies |
| 6 | triangulum_next_improvement_cycle.py | 0.4433 | Many dependencies |
| 7 | code_relationship_analyzer.py | 0.4329 | Many dependencies |
| 8 | debug_with_relationships.py | 0.4282 | Many dependencies |
| 9 | triangulum_monitor.py | 0.4266 | Many dependencies |
| 10 | smoke_runner.py | 0.4257 | Many dependencies |
| 11 | test_triangulum_comprehensive.py | 0.4209 | Many dependencies |
| 12 | triangulum_comprehensive_self_assessment.py | 0.4188 | Many dependencies |
| 13 | triangulum_autonomous_improvement_executor.py | 0.4117 | Many dependencies |
| 14 | debug_triangulum_workflow.py | 0.4097 | Many dependencies |
| 15 | triangulum_self_healing_session.py | 0.4067 | Many dependencies |
| 16 | integrated_triangulum_debug.py | 0.4053 | Many dependencies |
| 17 | test_triangulum_integration.py | 0.4041 | Many dependencies |
| 18 | triangulum_adaptive_health.py | 0.4008 | Many dependencies |
| 19 | triangulum_debug_system.py | 0.3981 | Many dependencies |
| 20 | triangulum_fix.py | 0.3969 | Many dependencies |

## Dependency Graph

For a visual representation of the dependency graph, run:

```
python scripts/analyze_code_relationships.py . --visualize graph.html
```

## Initial Recommendations

Based on the code relationship analysis, consider the following improvements:

### High Dependency Files

These files have a high number of dependencies and might benefit from refactoring:

- **triangulum_folder_debugger.py**: 40 incoming, 53 outgoing dependencies
- **debug_with_relationships.py**: 34 incoming, 58 outgoing dependencies
- **triangulum_gpt.py**: 38 incoming, 54 outgoing dependencies
- **test_triangulum_comprehensive.py**: 36 incoming, 55 outgoing dependencies
- **debug_triangulum_workflow.py**: 34 incoming, 56 outgoing dependencies

### Next Steps

1. Debug the top priority files to fix critical bugs
2. Review and refactor high dependency files
3. Add tests for complex files lacking coverage
4. Consider breaking down large files into smaller, more focused modules
