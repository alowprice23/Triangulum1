#!/usr/bin/env python3
"""
Repository Analyzer Demo

This script demonstrates the repository analyzer, which provides a
comprehensive overview of a codebase by analyzing all its files.
"""

import os
import json
import argparse
from triangulum_lx.tooling.repo_analyzer import RepoAnalyzer

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Run Repository Analyzer Demo')
    
    parser.add_argument(
        '--repo-path',
        type=str,
        default='.',
        help='Path to the repository to analyze'
    )
    
    parser.add_argument(
        '--output-file',
        type=str,
        default='./repo_analysis.json',
        help='File to save the analysis results'
    )
    
    parser.add_argument(
        '--extensions',
        type=str,
        default='.py,.js,.html,.css',
        help='Comma-separated list of file extensions to include'
    )
    
    return parser.parse_args()

def run_demo(repo_path: str, output_file: str, extensions: str):
    """
    Run the repository analyzer demo.
    
    Args:
        repo_path: Path to the repository to analyze
        output_file: File to save the analysis results
        extensions: Comma-separated list of file extensions to include
    """
    # Create the repository analyzer
    file_extensions = extensions.split(',')
    analyzer = RepoAnalyzer(repo_path, file_extensions)
    
    # Analyze the repository
    print(f"Analyzing repository at: {repo_path}")
    analysis_results = analyzer.analyze_repo()
    
    # Save the results to a file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2)
    
    print(f"\nRepository analysis completed.")
    print(f"  - Total files analyzed: {analysis_results['total_files']}")
    print(f"  - Total lines of code: {analysis_results['total_lines']}")
    print(f"Results saved to: {output_file}")

def main():
    """Run the repository analyzer demo."""
    args = parse_arguments()
    
    print("=" * 80)
    print("TRIANGULUM REPOSITORY ANALYZER DEMO".center(80))
    print("=" * 80)
    print("\nThis demo showcases the repository analyzer, which provides a")
    print("comprehensive overview of a codebase by analyzing all its files.")
    
    run_demo(args.repo_path, args.output_file, args.extensions)

if __name__ == "__main__":
    main()
