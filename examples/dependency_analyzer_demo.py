#!/usr/bin/env python3
"""
Triangulum Dependency Analyzer Demo

This script demonstrates the capabilities of the consolidated DependencyAnalyzer.
"""

import os
import sys
import tempfile
import shutil
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from triangulum_lx.tooling.dependency_analyzer import analyze_dependencies, DependencyGraphBuilder, DependencyAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("triangulum.dependency_analyzer_demo")

def create_demo_project_files(base_dir: Path):
    """Creates a small demo project with inter-file dependencies."""
    project_files = {
        "module_a.py": """
import module_b
from module_c import specific_function_c

class A:
    def do_something_a(self):
        b_instance = module_b.B()
        b_instance.do_something_b()
        specific_function_c()
""",
        "module_b.py": """
import module_c

class B:
    def do_something_b(self):
        c_instance = module_c.C()
        c_instance.do_something_else_c()
""",
        "module_c.py": """
class C:
    def do_something_c(self):
        print("C.do_something_c")
    def do_something_else_c(self):
        print("C.do_something_else_c")

def specific_function_c():
    print("specific_function_c called")

def another_function_c():
    print("another_function_c called")
""",
        "main.py": """
import module_a

def run():
    a_instance = module_a.A()
    a_instance.do_something_a()

if __name__ == "__main__":
    run()
"""
    }

    for file_path_str, content in project_files.items():
        path = base_dir / file_path_str
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    logger.info(f"Created demo project files in {base_dir}")

def run_demo():
    """Runs the dependency analyzer demo."""
    with tempfile.TemporaryDirectory(prefix="dep_analyzer_demo_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        create_demo_project_files(temp_dir)

        logger.info(f"\n--- Running Dependency Analysis on: {temp_dir} ---")

        # Use the high-level analyze_dependencies function
        # This uses DependencyGraphBuilder internally and returns a DependencyAnalyzer instance
        # It's important that the stubbed graph models and parser logic in dependency_analyzer.py are functional.
        try:
            # For the demo, disable caching and incremental builds for clarity unless specifically testing that.
            analyzer = analyze_dependencies(
                repo_path=temp_dir_str,
                cache_dir=None, # Disable caching for simple demo
                incremental=False
            )
        except Exception as e:
            logger.error(f"Failed to initialize or run dependency analyzer: {e}", exc_info=True)
            return

        if not analyzer or not analyzer.nx_graph or not analyzer.nx_graph.nodes():
            logger.error("Dependency analysis did not produce a graph. Exiting demo.")
            return

        logger.info(f"Graph built with {analyzer.nx_graph.number_of_nodes()} nodes and {analyzer.nx_graph.number_of_edges()} edges.")

        logger.info("\n--- Getting Dependencies for module_a.py ---")
        deps_a = analyzer.get_dependencies("module_a.py")
        logger.info(f"module_a.py depends on: {deps_a}")

        logger.info("\n--- Getting Files Dependent on module_c.py ---")
        dependents_c = analyzer.get_dependent_files("module_c.py")
        logger.info(f"Files dependent on module_c.py: {dependents_c}")

        logger.info("\n--- Strongly Connected Components (SCCs) ---")
        sccs = analyzer.get_strongly_connected_components()
        if sccs:
            for i, scc in enumerate(sccs):
                if len(scc) > 1: # Only print non-trivial SCCs (cycles)
                    logger.info(f"SCC {i+1}: {scc}")
            if not any(len(scc) > 1 for scc in sccs):
                logger.info("No non-trivial SCCs (cycles with more than 1 node) found.")
        else:
            logger.info("No SCCs found.")


        logger.info("\n--- Repair Batches (based on SCCs and topological sort) ---")
        batches = analyzer.get_repair_batches()
        for i, batch in enumerate(batches):
            logger.info(f"Batch {i+1}: {batch}")

        logger.info("\n--- Centrality Measures (Top 3 by PageRank) ---")
        central_files = analyzer.get_most_central_files(n=3, metric='pagerank')
        if central_files:
            for f_path, score in central_files:
                logger.info(f"{f_path}: PageRank = {score:.4f}")
        else:
            logger.info("Could not calculate centrality or graph is too small.")

        logger.info("\n--- Impact Score for module_c.py ---")
        impact_c = analyzer.get_impact_score("module_c.py")
        logger.info(f"Impact score for module_c.py: {impact_c:.4f}")

        # Optional: Visualize graph
        visualization_path = temp_dir / "dependency_graph_visualization.png"
        try:
            analyzer.visualize_graph(str(visualization_path))
            logger.info(f"Graph visualization saved to: {visualization_path}")
            logger.info("Note: Matplotlib is required for graph visualization.")
        except ImportError:
            logger.warning("Matplotlib not found. Skipping graph visualization.")
        except Exception as e:
            logger.error(f"Error during graph visualization: {e}", exc_info=True)

        logger.info("\nDependency Analyzer Demo finished.")
        logger.info(f"Temporary project and outputs were in: {temp_dir_str}")
        # temp_dir is automatically cleaned up by TemporaryDirectory context manager

if __name__ == "__main__":
    run_demo()
