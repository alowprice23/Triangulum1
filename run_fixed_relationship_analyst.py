#!/usr/bin/env python3
"""
This script runs the relationship analyst CLI with the path handling fix applied.
It will analyze code relationships in the specified directory with proper path handling.
"""

import sys
import os
import logging
import glob
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fixed_relationship_analyst")

def main():
    """Main function to run the fixed relationship analyst."""
    # Check if a target path was provided
    if len(sys.argv) < 2:
        logger.error("Usage: python run_fixed_relationship_analyst.py <target_directory>")
        return 1

    target_path = sys.argv[1]

    # First check if there are any Python files in the directory
    py_files = []
    for root, _, files in os.walk(target_path):
        for file in files:
            if file.endswith('.py'):
                py_file = os.path.join(root, file)
                py_files.append(py_file)
                logger.info(f"Found Python file: {py_file}")

    if not py_files:
        logger.error(f"No Python files found in {target_path}")
        return 1

    logger.info(f"Found {len(py_files)} Python files in {target_path}")

    # Apply the path handling fix
    logger.info("Applying path handling fix to dependency graph builder...")
    from triangulum_lx.tooling.dependency_graph_path_fix import fix_dependency_graph_builder
    success = fix_dependency_graph_builder()

    if not success:
        logger.error("Failed to apply path handling fix")
        return 1

    logger.info(f"Analyzing code relationships in {target_path}")

    # Import the relationship analyst agent with the fix applied
    from triangulum_lx.agents.relationship_analyst_agent import RelationshipAnalystAgent

    # Create the agent
    agent = RelationshipAnalystAgent(
        agent_id="fixed_relationship_analyst",
        cache_dir="./cache"
    )

    # Run the analysis with all Python files included
    # Use a simpler pattern that's guaranteed to match Python files
    include_patterns = ["*.py"]
    exclude_patterns = ["*venv*", "*__pycache__*"]

    summary = agent.analyze_codebase(
        root_dir=target_path,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        incremental=False,
        perform_static_analysis=True
    )

    # Print a summary of the analysis
    print("\n=== Code Relationship Analysis Summary ===")
    print(f"Files analyzed: {summary['files_analyzed']}")
    print(f"Dependencies found: {summary['dependencies_found']}")
    print(f"Cycles detected: {summary['cycles_detected']}")

    # Display language breakdown
    print("\n=== Language Breakdown ===")
    for lang, count in summary['languages_detected'].items():
        print(f"{lang}: {count} files")

    # Only attempt to get central files if files were analyzed
    if summary['files_analyzed'] > 0:
        try:
            # Display central files
            central_files = agent.get_most_central_files(n=10, metric='pagerank')

            print("\n=== Top 10 Most Central Files (pagerank) ===")
            print(f"{'File':<50} {'Score':<10}")
            print("-" * 60)
            for file_path, score in central_files:
                print(f"{file_path:<50} {score:.4f}")

            # Save the results to a JSON file
            output_path = "relationship_analysis_results.json"
            
            # Get the report data
            if agent.analyzer:
                cycles = agent.analyzer.find_cycles()
                central_files = agent.analyzer.get_most_central_files(n=20)
            else:
                cycles = []
                central_files = []
                
            # Create a report
            report = {
                "summary": summary,
                "cycles": cycles,
                "central_files": central_files,
                "metadata": {
                    "timestamp": summary["analysis_timestamp"],
                    "target_path": target_path
                }
            }
            
            # Save the report
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
                
            logger.info(f"Generated relationship report at {output_path}")
        except Exception as e:
            logger.error(f"Error generating report: {e}")
    else:
        logger.warning("No files were analyzed, skipping centrality and report generation")

    return 0

if __name__ == "__main__":
    sys.exit(main())
