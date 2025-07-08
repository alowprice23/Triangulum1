"""
This module fixes the path handling in the DependencyGraphBuilder class
to ensure it correctly handles absolute paths when analyzing external directories.
"""

import os
import logging
import fnmatch

logger = logging.getLogger(__name__)

def fix_dependency_graph_builder():
    """
    Apply the path handling fix to the DependencyGraphBuilder class.
    This ensures the tool can correctly analyze files in external directories.
    """
    # Import the module we want to patch
    from triangulum_lx.tooling.dependency_graph import DependencyGraphBuilder
    
    # Store the original _find_files method for reference
    original_find_files = DependencyGraphBuilder._find_files
    
    # Define the patched method with proper path handling
    def patched_find_files(self, root_dir, include_patterns, exclude_patterns):
        """
        Find all relevant files in the codebase.
        This patched version maintains absolute paths instead of relative paths.
        
        Args:
            root_dir: Root directory of the codebase
            include_patterns: List of glob patterns for files to include
            exclude_patterns: List of glob patterns for files to exclude
            
        Returns:
            List of file paths (absolute paths)
        """
        files = []
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Check if directory should be excluded
            if any(fnmatch.fnmatch(dirpath, pattern) for pattern in exclude_patterns):
                continue
                
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                # Use absolute paths to ensure files can be found
                abs_path = os.path.abspath(file_path)
                
                # Skip files that don't match include patterns
                if not any(fnmatch.fnmatch(file_path, pattern) for pattern in include_patterns):
                    continue
                    
                # Skip files that match exclude patterns
                if any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns):
                    continue
                    
                # Add the absolute path to the list
                files.append(abs_path)
                
        logger.info(f"Found {len(files)} files to analyze in {root_dir}")
        return files
    
    # Replace the original method with our patched version
    DependencyGraphBuilder._find_files = patched_find_files
    
    # Patch the _process_file method to handle absolute paths
    original_process_file = DependencyGraphBuilder._process_file
    
    def patched_process_file(self, file_path, graph, root_dir):
        """
        Process a file to extract its dependencies.
        This patched version ensures absolute paths are used.
        
        Args:
            file_path: Path to the file
            graph: Dependency graph to update
            root_dir: The root directory of the project for resolving imports
        """
        # Ensure we're using the absolute path
        abs_path = os.path.abspath(file_path)
        
        # Get the appropriate parser
        parser = self.parser_registry.get_parser_for_file(abs_path)
        if parser:
            try:
                # Use the absolute path when parsing
                dependencies = parser.parse_file(abs_path, root_dir)
                for target_path, metadata in dependencies:
                    # Make sure target_path is also absolute
                    abs_target = os.path.abspath(target_path) if os.path.exists(target_path) else target_path
                    if abs_target in graph:
                        graph.add_edge(abs_path, abs_target, metadata)
            except Exception as e:
                logger.error(f"Error processing file {abs_path}: {str(e)}")
    
    # Replace the original method with our patched version
    DependencyGraphBuilder._process_file = patched_process_file
    
    logger.info("Applied path handling fix to DependencyGraphBuilder")
    return True
