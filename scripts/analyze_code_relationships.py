#!/usr/bin/env python3
"""
Code Relationship Analyzer CLI for Triangulum GPT

This script provides a command-line interface to the Code Relationship Analyzer,
allowing users to analyze code relationships in a project for debugging purposes.
It implements the 5-pass pipeline approach to generate a "family tree" model of
code relationships.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path

# Add the parent directory to sys.path to import Triangulum modules
sys.path.append(str(Path(__file__).parent.parent))

from triangulum_lx.tooling.code_relationship_analyzer import CodeRelationshipAnalyzer
from triangulum_lx.providers.factory import get_provider

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('code_relationship_analyzer')

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze code relationships in a project using a 5-pass pipeline"
    )
    
    parser.add_argument(
        "project_path", 
        help="Path to the project directory or file to analyze"
    )
    
    parser.add_argument(
        "--max-pass", 
        type=int, 
        choices=[0, 1, 2, 3, 4], 
        default=4,
        help="Maximum pass to run (0-4). Higher passes are more thorough but slower."
    )
    
    parser.add_argument(
        "--llm-provider", 
        help="LLM provider to use for Pass 2 (semantic analysis)"
    )
    
    parser.add_argument(
        "--cache-dir", 
        help="Directory to store cache files"
    )
    
    parser.add_argument(
        "--output", 
        help="Output file for the relationship graph (JSON format)"
    )
    
    parser.add_argument(
        "--visualize", 
        help="Generate an HTML visualization of the graph and save to the specified file"
    )
    
    parser.add_argument(
        "--query-file", 
        help="Get relationships for a specific file"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Check if the project path exists
    if not os.path.exists(args.project_path):
        logger.error(f"Project path does not exist: {args.project_path}")
        return 1
    
    logger.info(f"Analyzing code relationships in: {args.project_path}")
    
    # Create and run the analyzer
    analyzer = CodeRelationshipAnalyzer(
        project_path=args.project_path,
        llm_provider=args.llm_provider,
        cache_dir=args.cache_dir
    )
    
    analyzer.analyze(max_pass=args.max_pass)
    
    logger.info(f"Analysis complete: {len(analyzer.graph.nodes)} nodes, {len(analyzer.graph.edges)} edges")
    
    # Query a specific file if requested
    if args.query_file:
        if not os.path.exists(args.query_file):
            logger.error(f"Query file does not exist: {args.query_file}")
        else:
            related_files = analyzer.get_related_files(args.query_file)
            
            print(f"\nRelationships for {args.query_file}:")
            for relationship_type, files in related_files.items():
                print(f"\n  {relationship_type.upper()}:")
                for file in files:
                    print(f"    - {file}")
    
    # Export the graph to JSON if requested
    if args.output:
        analyzer.export_to_json(args.output)
        logger.info(f"Graph exported to {args.output}")
    
    # Generate visualization if requested
    if args.visualize:
        try:
            analyzer.visualize_graph(args.visualize)
            logger.info(f"Visualization saved to {args.visualize}")
        except ImportError:
            logger.error("Visualization requires pyvis. Install with 'pip install pyvis'")
    
    return 0

if __name__ == "__main__":
    exit(main())
