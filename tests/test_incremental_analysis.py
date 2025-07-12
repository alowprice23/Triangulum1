#!/usr/bin/env python3
"""
This script tests the incremental analysis capability of Triangulum.
It performs:
1. Initial full analysis on a directory
2. Makes a small change to a file
3. Runs incremental analysis
4. Compares the execution time between full and incremental analysis
"""

import sys
import os
import time
import logging
import tempfile
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("incremental_analysis_test")

def copy_files_to_temp(source_dir):
    """
    Create a temporary directory and copy files for testing
    
    Args:
        source_dir: Source directory to copy files from
        
    Returns:
        Path to temporary directory
    """
    temp_dir = tempfile.mkdtemp(prefix="triangulum_test_")
    logger.info(f"Created temporary directory: {temp_dir}")
    
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.py'):
                src_file = os.path.join(root, file)
                # Get relative path from source_dir
                rel_path = os.path.relpath(src_file, source_dir)
                # Create destination path
                dst_file = os.path.join(temp_dir, rel_path)
                # Create parent directories if they don't exist
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                # Copy the file
                shutil.copy2(src_file, dst_file)
                logger.debug(f"Copied {src_file} to {dst_file}")
    
    logger.info(f"Copied Python files from {source_dir} to {temp_dir}")
    return temp_dir

def modify_file(temp_dir):
    """
    Make a small change to a Python file in the temporary directory
    
    Args:
        temp_dir: Temporary directory containing files
        
    Returns:
        Path to the modified file
    """
    # Find a Python file to modify
    for root, _, files in os.walk(temp_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Add a comment at the end of the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    f.write("\n# Modified for incremental analysis test\n")
                
                logger.info(f"Modified file: {file_path}")
                return file_path
    
    raise FileNotFoundError("No Python files found to modify")

def run_analysis(target_dir, incremental=False):
    """
    Run dependency graph analysis on the target directory
    
    Args:
        target_dir: Directory to analyze
        incremental: Whether to use incremental analysis
        
    Returns:
        Execution time in seconds
    """
    # Apply the path handling fix first
    from triangulum_lx.tooling.dependency_graph_path_fix import fix_dependency_graph_builder
    fix_dependency_graph_builder()
    
    # Import the dependency graph builder
    from triangulum_lx.tooling.dependency_graph import DependencyGraphBuilder
    
    # Create a builder with the cache_dir only
    builder = DependencyGraphBuilder(cache_dir="./cache")
    
    # Define include and exclude patterns
    include_patterns = ["*.py"]
    exclude_patterns = ["*venv*", "*__pycache__*"]
    
    # Run the analysis and measure time
    start_time = time.time()
    
    if incremental:
        logger.info(f"Running incremental analysis on {target_dir}")
        graph = builder.load_cached_graph("dependency_graph")
        graph = builder.build_graph(
            target_dir, 
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            previous_graph=graph, 
            incremental=True
        )
    else:
        logger.info(f"Running full analysis on {target_dir}")
        graph = builder.build_graph(
            target_dir, 
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            incremental=False
        )
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Count the nodes and edges
    node_count = len(graph)
    edge_count = sum(1 for _ in graph.edges()) if hasattr(graph, 'edges') else 0
    
    logger.info(f"Analysis completed in {execution_time:.4f} seconds")
    logger.info(f"Graph has {node_count} nodes and {edge_count} edges")
    
    return execution_time

def main():
    """Main function to run the incremental analysis test."""
    # Check if a target path was provided
    if len(sys.argv) < 2:
        logger.error("Usage: python test_incremental_analysis.py <target_directory>")
        return 1
    
    source_dir = sys.argv[1]
    
    try:
        # Create a temporary copy of the files
        temp_dir = copy_files_to_temp(source_dir)
        
        # Run initial full analysis
        full_time = run_analysis(temp_dir, incremental=False)
        
        # Modify a file
        modified_file = modify_file(temp_dir)
        
        # Run incremental analysis
        incremental_time = run_analysis(temp_dir, incremental=True)
        
        # Compare times
        speedup = full_time / incremental_time if incremental_time > 0 else float('inf')
        
        print("\n=== Incremental Analysis Test Results ===")
        print(f"Full analysis time:        {full_time:.4f} seconds")
        print(f"Incremental analysis time: {incremental_time:.4f} seconds")
        print(f"Speedup factor:            {speedup:.2f}x")
        
        # Clean up temporary directory
        shutil.rmtree(temp_dir)
        logger.info(f"Cleaned up temporary directory: {temp_dir}")
        
        if speedup > 1.0:
            print("\nTEST PASSED: Incremental analysis is faster than full analysis")
            return 0
        else:
            print("\nTEST FAILED: Incremental analysis is not faster than full analysis")
            return 1
        
    except Exception as e:
        logger.error(f"Error during incremental analysis test: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
