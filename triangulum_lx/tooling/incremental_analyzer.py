"""
Incremental analyzer for the dependency graph.

This module provides functionality for efficiently updating the dependency graph
when only parts of the codebase change, avoiding the need for full reanalysis.
"""

import os
import logging
import time
import hashlib
from typing import Dict, Set, List, Optional, Tuple, Any
from pathlib import Path
from .graph_models import DependencyGraph, FileNode, DependencyMetadata, DependencyType
from .dependency_graph import DependencyGraphBuilder, ParserRegistry

logger = logging.getLogger(__name__)

class ChangeType:
    """Types of changes that can occur in files."""
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"
    UNCHANGED = "unchanged"

class IncrementalAnalyzer:
    """
    Analyzes changes in the codebase and updates the dependency graph incrementally.
    
    This class provides efficient updates to code relationship information when only
    parts of the codebase change, avoiding the need for full reanalysis.
    """

    def __init__(self, graph: DependencyGraph, parser_registry: Optional[ParserRegistry] = None):
        """
        Initialize the incremental analyzer.
        
        Args:
            graph: The dependency graph to update
            parser_registry: Registry of parsers to use for file analysis
        """
        self.graph = graph
        self.parser_registry = parser_registry or ParserRegistry()
        self.change_history = {}  # Maps file paths to their last change type
        self.last_analysis_time = time.time()
        self.file_checksums = {}  # Maps file paths to their last known checksum
        
        # Initialize file checksums from existing graph nodes
        for path in self.graph:
            node = self.graph.get_node(path)
            if node and node.file_hash:
                self.file_checksums[path] = node.file_hash

    def analyze_changes(self, updated_files: Dict[str, str]) -> Set[str]:
        """
        Analyzes the given files for changes and updates the graph.

        Args:
            updated_files: A dictionary mapping file paths to their new content.

        Returns:
            A set of file paths that were affected by the changes.
        """
        affected_files = set()
        for file_path, content in updated_files.items():
            if self.graph.get_node(file_path) is None:
                # New file
                affected_files.add(file_path)
                self.change_history[file_path] = ChangeType.ADDED
                continue

            node = self.graph.get_node(file_path)
            old_hash = node.file_hash
            node.update_hash()
            if old_hash != node.file_hash:
                affected_files.add(file_path)
                self.change_history[file_path] = ChangeType.MODIFIED
                # Invalidate dependencies by removing the node
                self.graph.remove_node(file_path)

        return affected_files

    def detect_changes(self, root_dir: str, include_patterns: Optional[List[str]] = None, 
                      exclude_patterns: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Detect changes in the codebase since the last analysis.
        
        Args:
            root_dir: Root directory of the codebase
            include_patterns: List of glob patterns for files to include
            exclude_patterns: List of glob patterns for files to exclude
            
        Returns:
            Dictionary mapping file paths to their change type
        """
        import fnmatch
        from pathlib import Path
        
        include_patterns = include_patterns or ['*.py', '*.js', '*.jsx', '*.ts', '*.tsx', '*.java']
        exclude_patterns = exclude_patterns or ['**/node_modules/**', '**/__pycache__/**', '**/.git/**']
        
        changes = {}
        current_files = set()
        
        # Find all current files
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Check if directory should be excluded
            if any(fnmatch.fnmatch(dirpath, pattern) for pattern in exclude_patterns):
                continue
            
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                
                # Check include patterns
                if not any(fnmatch.fnmatch(file_path, pattern) for pattern in include_patterns):
                    continue
                
                # Check exclude patterns
                if any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns):
                    continue
                
                # Make path relative to root_dir
                rel_path = os.path.relpath(file_path, root_dir)
                current_files.add(rel_path)
                
                # Check if file is new or modified
                if rel_path not in self.file_checksums:
                    changes[rel_path] = ChangeType.ADDED
                else:
                    # Calculate current checksum
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read()
                        current_hash = hashlib.sha256(content).hexdigest()
                        
                        if current_hash != self.file_checksums[rel_path]:
                            changes[rel_path] = ChangeType.MODIFIED
                        else:
                            changes[rel_path] = ChangeType.UNCHANGED
                    except Exception as e:
                        logger.warning(f"Error calculating checksum for {file_path}: {str(e)}")
                        changes[rel_path] = ChangeType.MODIFIED  # Assume modified if error
        
        # Find removed files
        for file_path in self.file_checksums:
            if file_path not in current_files:
                changes[file_path] = ChangeType.REMOVED
        
        return changes

    def update_graph_incrementally(self, root_dir: str, include_patterns: Optional[List[str]] = None,
                                  exclude_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Update the dependency graph incrementally based on detected changes.
        
        Args:
            root_dir: Root directory of the codebase
            include_patterns: List of glob patterns for files to include
            exclude_patterns: List of glob patterns for files to exclude
            
        Returns:
            Dictionary with update statistics
        """
        start_time = time.time()
        
        # Detect changes
        changes = self.detect_changes(root_dir, include_patterns, exclude_patterns)
        
        # Track statistics
        stats = {
            "files_added": 0,
            "files_modified": 0,
            "files_removed": 0,
            "files_unchanged": 0,
            "dependencies_added": 0,
            "dependencies_removed": 0,
            "affected_files": set(),
            "impact_boundary": set()
        }
        
        # Process changes
        for file_path, change_type in changes.items():
            if change_type == ChangeType.ADDED:
                stats["files_added"] += 1
                self._process_added_file(root_dir, file_path, stats)
            elif change_type == ChangeType.MODIFIED:
                stats["files_modified"] += 1
                self._process_modified_file(root_dir, file_path, stats)
            elif change_type == ChangeType.REMOVED:
                stats["files_removed"] += 1
                self._process_removed_file(file_path, stats)
            else:  # UNCHANGED
                stats["files_unchanged"] += 1
        
        # Calculate impact boundary
        stats["impact_boundary"] = self._calculate_impact_boundary(stats["affected_files"])
        
        # Update analysis time and return statistics
        self.last_analysis_time = time.time()
        stats["analysis_duration"] = self.last_analysis_time - start_time
        
        logger.info(f"Incremental analysis completed in {stats['analysis_duration']:.2f} seconds")
        logger.info(f"Added: {stats['files_added']}, Modified: {stats['files_modified']}, " +
                   f"Removed: {stats['files_removed']}, Unchanged: {stats['files_unchanged']}")
        logger.info(f"Dependencies added: {stats['dependencies_added']}, " +
                   f"Dependencies removed: {stats['dependencies_removed']}")
        logger.info(f"Affected files: {len(stats['affected_files'])}, " +
                   f"Impact boundary: {len(stats['impact_boundary'])}")
        
        return stats

    def _process_added_file(self, root_dir: str, file_path: str, stats: Dict[str, Any]) -> None:
        """
        Process an added file.
        
        Args:
            root_dir: Root directory of the codebase
            file_path: Path to the added file
            stats: Statistics dictionary to update
        """
        # Add the file to affected files
        stats["affected_files"].add(file_path)
        
        # Create a new node
        from .graph_models import LanguageType
        language = LanguageType.from_extension(os.path.splitext(file_path)[1])
        node = FileNode(path=file_path, language=language)
        
        # Add the node to the graph
        self.graph.add_node(node)
        
        # Update file checksum
        full_path = os.path.join(root_dir, file_path)
        try:
            with open(full_path, 'rb') as f:
                content = f.read()
            self.file_checksums[file_path] = hashlib.sha256(content).hexdigest()
        except Exception as e:
            logger.warning(f"Error calculating checksum for {full_path}: {str(e)}")
        
        # Parse dependencies
        self._parse_file_dependencies(root_dir, file_path, stats)

    def _process_modified_file(self, root_dir: str, file_path: str, stats: Dict[str, Any]) -> None:
        """
        Process a modified file.
        
        Args:
            root_dir: Root directory of the codebase
            file_path: Path to the modified file
            stats: Statistics dictionary to update
        """
        # Add the file to affected files
        stats["affected_files"].add(file_path)
        
        # Get existing node
        node = self.graph.get_node(file_path)
        
        # If node doesn't exist (shouldn't happen), create it
        if not node:
            from .graph_models import LanguageType
            language = LanguageType.from_extension(os.path.splitext(file_path)[1])
            node = FileNode(path=file_path, language=language)
            self.graph.add_node(node)
        
        # Update file hash
        old_hash = node.file_hash
        node.update_hash()
        
        # Update file checksum
        self.file_checksums[file_path] = node.file_hash or ""
        
        # If hash changed, update dependencies
        if old_hash != node.file_hash:
            # Get dependents before removing
            dependents = self.graph.transitive_dependents(file_path)
            stats["affected_files"].update(dependents)
            
            # Remove existing dependencies
            old_deps_count = len(self.graph.get_outgoing_edges(file_path))
            stats["dependencies_removed"] += old_deps_count
            
            # Remove the node (which removes all edges)
            self.graph.remove_node(file_path)
            
            # Re-add the node
            self.graph.add_node(node)
            
            # Parse dependencies
            self._parse_file_dependencies(root_dir, file_path, stats)

    def _process_removed_file(self, file_path: str, stats: Dict[str, Any]) -> None:
        """
        Process a removed file.
        
        Args:
            file_path: Path to the removed file
            stats: Statistics dictionary to update
        """
        # Add the file to affected files
        stats["affected_files"].add(file_path)
        
        # Get dependents before removing
        dependents = self.graph.transitive_dependents(file_path)
        stats["affected_files"].update(dependents)
        
        # Count dependencies to be removed
        outgoing = len(self.graph.get_outgoing_edges(file_path))
        incoming = len(self.graph.get_incoming_edges(file_path))
        stats["dependencies_removed"] += outgoing + incoming
        
        # Remove the node from the graph
        self.graph.remove_node(file_path)
        
        # Remove from file checksums
        if file_path in self.file_checksums:
            del self.file_checksums[file_path]

    def _parse_file_dependencies(self, root_dir: str, file_path: str, stats: Dict[str, Any]) -> None:
        """
        Parse dependencies for a file and update the graph.
        
        Args:
            root_dir: Root directory of the codebase
            file_path: Path to the file
            stats: Statistics dictionary to update
        """
        parser = self.parser_registry.get_parser_for_file(file_path)
        if not parser:
            logger.warning(f"No parser available for {file_path}")
            return
        
        try:
            full_path = os.path.join(root_dir, file_path)
            dependencies = parser.parse_file(full_path)
            
            # Add edges to the graph
            for target_path, metadata in dependencies:
                if target_path in self.graph:
                    self.graph.add_edge(file_path, target_path, metadata)
                    stats["dependencies_added"] += 1
        except Exception as e:
            logger.error(f"Error parsing dependencies for {file_path}: {str(e)}")

    def _calculate_impact_boundary(self, affected_files: Set[str]) -> Set[str]:
        """
        Calculate the impact boundary of the changes.
        
        The impact boundary includes all files that might be affected by the changes,
        including files that depend on changed files and files that changed files depend on.
        
        Args:
            affected_files: Set of files directly affected by changes
            
        Returns:
            Set of files in the impact boundary
        """
        impact_boundary = set(affected_files)
        
        # Add all files that depend on affected files
        for file_path in affected_files:
            dependents = self.graph.transitive_dependents(file_path)
            impact_boundary.update(dependents)
        
        # Add all files that affected files depend on
        for file_path in affected_files:
            dependencies = self.graph.transitive_dependencies(file_path)
            impact_boundary.update(dependencies)
        
        return impact_boundary

    def optimize_for_change_patterns(self, change_patterns: Dict[str, List[str]]) -> None:
        """
        Optimize the analyzer for common change patterns.
        
        This method adjusts the analyzer's behavior based on observed change patterns
        to improve performance for future incremental analyses.
        
        Args:
            change_patterns: Dictionary mapping change types to lists of file patterns
        """
        # This is a placeholder for future optimization logic
        # In a real implementation, this would adjust analysis strategies based on patterns
        logger.info(f"Optimizing for {len(change_patterns)} change patterns")
        
        # Example optimization: Precompute impact boundaries for common change patterns
        for change_type, patterns in change_patterns.items():
            logger.info(f"Registered {len(patterns)} patterns for {change_type} changes")

    def get_change_history(self) -> Dict[str, str]:
        """
        Get the change history for all files.
        
        Returns:
            Dictionary mapping file paths to their last change type
        """
        return self.change_history.copy()

    def get_file_checksums(self) -> Dict[str, str]:
        """
        Get the current file checksums.
        
        Returns:
            Dictionary mapping file paths to their checksums
        """
        return self.file_checksums.copy()

    def reset_analysis_state(self) -> None:
        """Reset the analysis state for a fresh incremental analysis."""
        self.change_history = {}
        self.last_analysis_time = time.time()
        
        # Rebuild file checksums from graph
        self.file_checksums = {}
        for path in self.graph:
            node = self.graph.get_node(path)
            if node and node.file_hash:
                self.file_checksums[path] = node.file_hash
