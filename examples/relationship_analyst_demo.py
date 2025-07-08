#!/usr/bin/env python
"""
Relationship Analyst Agent Demo

This script demonstrates the Relationship Analyst Agent in Triangulum.
It shows how the agent can analyze a codebase to identify important files,
dependencies, cycles, and prioritize files for repair.
"""

import os
import sys
import logging
import argparse
import json
from pathlib import Path

# Add parent directory to path to import Triangulum modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.agents.relationship_analyst_agent import RelationshipAnalystAgent

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def analyze_codebase(agent, args):
    """
    Use the agent to analyze the codebase.
    
    Args:
        agent: The RelationshipAnalystAgent instance
        args: Command-line arguments
    """
    # Analyze the codebase
    summary = agent.analyze_codebase(
        root_dir=args.path,
        include_patterns=args.include,
        exclude_patterns=args.exclude,
        incremental=args.incremental
    )
    
    # Print a summary of the analysis
    logger.info("\n=== Codebase Analysis Summary ===")
    logger.info(f"Files analyzed: {summary['files_analyzed']}")
    logger.info(f"Dependencies found: {summary['dependencies_found']}")
    logger.info(f"Cycles detected: {summary['cycles_detected']}")
    
    # Display language breakdown
    logger.info("\n=== Language Breakdown ===")
    for lang, count in summary['languages_detected'].items():
        logger.info(f"{lang}: {count} files")


def display_central_files(agent, args):
    """
    Display the most central files in the codebase.
    
    Args:
        agent: The RelationshipAnalystAgent instance
        args: Command-line arguments
    """
    # Get the most central files by PageRank
    central_files = agent.get_most_central_files(n=args.top_n, metric=args.metric)
    
    # Display in a table format
    logger.info(f"\n=== Top {args.top_n} Most Central Files ({args.metric}) ===")
    logger.info(f"{'File':<50} {'Score':<10}")
    logger.info("-" * 60)
    for file_path, score in central_files:
        logger.info(f"{file_path:<50} {score:.4f}")


def display_cycles(agent):
    """
    Display cycles in the dependency graph.
    
    Args:
        agent: The RelationshipAnalystAgent instance
    """
    cycles = agent.find_cycles()
    
    logger.info(f"\n=== Dependency Cycles ({len(cycles)}) ===")
    if not cycles:
        logger.info("No cycles found (acyclic dependency graph)")
        return
    
    for i, cycle in enumerate(cycles[:10], 1):  # Show at most 10 cycles
        logger.info(f"Cycle {i}: {' -> '.join(cycle)} -> {cycle[0]}")
    
    if len(cycles) > 10:
        logger.info(f"... and {len(cycles) - 10} more cycles")


def suggest_repair_priorities(agent, args):
    """
    Suggest priorities for repairing files.
    
    Args:
        agent: The RelationshipAnalystAgent instance
        args: Command-line arguments
    """
    # Prioritize files for repair
    priorities = agent.prioritize_files_for_repair(strategy=args.strategy)
    
    # Display in a table format
    logger.info(f"\n=== Suggested Repair Priorities ({args.strategy}) ===")
    logger.info(f"{'File':<50} {'Score':<10} {'Dependents':<10}")
    logger.info("-" * 75)
    
    for file_path, score in priorities[:args.top_n]:
        if agent.graph:
            dependents = len(agent.get_file_dependents(file_path, transitive=True))
            logger.info(f"{file_path:<50} {score:.4f} {dependents:>10}")
        else:
            logger.info(f"{file_path:<50} {score:.4f}")


def analyze_specific_file(agent, args):
    """
    Analyze a specific file in the codebase.
    
    Args:
        agent: The RelationshipAnalystAgent instance
        args: Command-line arguments
    """
    if not args.file:
        return
    
    file_path = args.file
    logger.info(f"\n=== Analysis of {file_path} ===")
    
    # Get dependencies (files this file depends on)
    try:
        deps = agent.get_file_dependencies(file_path)
        trans_deps = agent.get_file_dependencies(file_path, transitive=True)
        
        logger.info(f"Direct dependencies: {len(deps)}")
        if deps:
            for dep in sorted(deps):
                logger.info(f"  - {dep}")
        
        logger.info(f"Transitive dependencies: {len(trans_deps)}")
        if len(trans_deps) > 10:
            logger.info(f"  (showing 10 of {len(trans_deps)})")
            for dep in sorted(list(trans_deps))[:10]:
                logger.info(f"  - {dep}")
        elif trans_deps:
            for dep in sorted(trans_deps):
                logger.info(f"  - {dep}")
        
        # Get dependents (files that depend on this file)
        deps = agent.get_file_dependents(file_path)
        trans_deps = agent.get_file_dependents(file_path, transitive=True)
        
        logger.info(f"Direct dependents: {len(deps)}")
        if deps:
            for dep in sorted(deps):
                logger.info(f"  - {dep}")
        
        logger.info(f"Transitive dependents: {len(trans_deps)}")
        if len(trans_deps) > 10:
            logger.info(f"  (showing 10 of {len(trans_deps)})")
            for dep in sorted(list(trans_deps))[:10]:
                logger.info(f"  - {dep}")
        elif trans_deps:
            for dep in sorted(trans_deps):
                logger.info(f"  - {dep}")
        
        # Get impact score
        impact = agent.analyzer.get_impact_score(file_path)
        logger.info(f"Impact score: {impact:.4f}")
        
    except ValueError as e:
        logger.error(f"Error analyzing file: {e}")


def main():
    """Main function to run the demo."""
    parser = argparse.ArgumentParser(description="Demonstrate the Relationship Analyst Agent")
    parser.add_argument("--path", type=str, default=".", help="Path to project root")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker threads")
    parser.add_argument("--exclude", type=str, nargs="*", 
                        default=["**/venv/**", "**/__pycache__/**", "**/.git/**", "**/node_modules/**"],
                        help="Glob patterns to exclude")
    parser.add_argument("--include", type=str, nargs="*", 
                        default=["**/*.py", "**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx"],
                        help="Glob patterns to include")
    parser.add_argument("--incremental", action="store_true", help="Perform incremental analysis")
    parser.add_argument("--top-n", type=int, default=10, help="Number of top files to display")
    parser.add_argument("--metric", type=str, default="pagerank", 
                        choices=["pagerank", "betweenness", "in_degree", "out_degree"],
                        help="Centrality metric to use")
    parser.add_argument("--strategy", type=str, default="impact", 
                        choices=["impact", "pagerank", "betweenness", "in_degree"],
                        help="Strategy for prioritizing files")
    parser.add_argument("--file", type=str, help="Specific file to analyze")
    parser.add_argument("--cache-dir", type=str, help="Directory to use for caching graphs")
    args = parser.parse_args()
    
    # Make path absolute
    abs_path = os.path.abspath(args.path)
    
    # Create the agent
    agent = RelationshipAnalystAgent(
        max_workers=args.workers,
        cache_dir=args.cache_dir
    )
    
    # Analyze the codebase
    analyze_codebase(agent, args)
    
    # Display central files
    display_central_files(agent, args)
    
    # Display cycles
    display_cycles(agent)
    
    # Suggest repair priorities
    suggest_repair_priorities(agent, args)
    
    # Analyze a specific file if requested
    analyze_specific_file(agent, args)
    
    logger.info("\nRelationship analysis complete.")


if __name__ == "__main__":
    main()
