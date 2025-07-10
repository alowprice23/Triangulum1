"""
Enhanced Repair Tool for Triangulum

Provides comprehensive, transaction-based multi-file repair capabilities with
conflict detection, consistency validation, and failure recovery.
"""

import os
import sys
import logging
import json
import hashlib
import tempfile
import time
import threading
import uuid
import difflib
import re
from pathlib import Path
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable
from contextlib import contextmanager

from triangulum_lx.tooling.fs_ops import atomic_write, atomic_delete
from triangulum_lx.core.fs_state import FileSystemStateCache

from .code_relationship_analyzer_stub import CodeRelationshipAnalyzer # Use the stub
from .relationship_context_provider import RelationshipContextProvider
from .test_runner import TestRunner
from .patch_bundle import PatchBundle
from .dependency_graph import DependencyGraph
from .incremental_analyzer import IncrementalAnalyzer
from ..core.rollback_manager import RollbackManager, SnapshotType

logger = logging.getLogger(__name__)


class RepairStatus(Enum):
    """Status of a repair operation."""
    PENDING = auto()    # Repair is pending
    IN_PROGRESS = auto() # Repair is in progress
    COMPLETED = auto()  # Repair completed successfully
    FAILED = auto()     # Repair failed
    ROLLED_BACK = auto() # Repair was rolled back


class ConflictType(Enum):
    """Type of conflict between repairs."""
    NONE = auto()           # No conflict
    SAME_LINE = auto()      # Changes affect the same line
    ADJACENT_LINES = auto() # Changes affect adjacent lines
    SEMANTIC = auto()       # Changes have semantic conflicts
    DEPENDENCY = auto()     # Changes affect dependent code


class ConflictResolutionStrategy(Enum):
    """Strategy for resolving conflicts between repairs."""
    ABORT = auto()          # Abort both repairs
    PRIORITIZE_FIRST = auto() # Prioritize the first repair
    PRIORITIZE_SECOND = auto() # Prioritize the second repair
    MERGE = auto()          # Attempt to merge the repairs
    SEQUENTIAL = auto()     # Apply repairs sequentially


@dataclass
class FileChange:
    """Represents a change to a file."""
    file_path: str
    start_line: int
    end_line: int
    original_content: str
    new_content: str
    change_type: str = "replace"  # replace, insert, delete
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_diff(self) -> str:
        """
        Get a unified diff of the change.
        
        Returns:
            Unified diff string
        """
        original_lines = self.original_content.splitlines(keepends=True)
        new_lines = self.new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{self.file_path}",
            tofile=f"b/{self.file_path}",
            fromfiledate="",
            tofiledate="",
            n=3  # Context lines
        )
        
        return "".join(diff)
    
    def conflicts_with(self, other: 'FileChange') -> ConflictType:
        """
        Check if this change conflicts with another change.
        
        Args:
            other: Another FileChange to check against
            
        Returns:
            ConflictType indicating the type of conflict, or NONE if no conflict
        """
        # Different files can't conflict
        if self.file_path != other.file_path:
            return ConflictType.NONE
        
        # Check for line overlaps
        if (self.start_line <= other.end_line and self.end_line >= other.start_line):
            return ConflictType.SAME_LINE
        
        # Check for adjacent lines
        if (abs(self.end_line - other.start_line) <= 1 or 
            abs(self.start_line - other.end_line) <= 1):
            return ConflictType.ADJACENT_LINES
        
        # More sophisticated semantic conflict detection would go here
        # For now, we'll just return NONE for non-overlapping changes
        return ConflictType.NONE


@dataclass
class RepairPlan:
    """A plan for repairing one or more files."""
    id: str
    name: str
    description: str
    changes: List[FileChange]
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: RepairStatus = RepairStatus.PENDING
    created_at: float = field(default_factory=time.time)
    
    def get_affected_files(self) -> Set[str]:
        """
        Get the set of files affected by this repair plan.
        
        Returns:
            Set of file paths
        """
        return {change.file_path for change in self.changes}
    
    def conflicts_with(self, other: 'RepairPlan') -> List[Tuple[FileChange, FileChange, ConflictType]]:
        """
        Check if this repair plan conflicts with another repair plan.
        
        Args:
            other: Another RepairPlan to check against
            
        Returns:
            List of tuples (change1, change2, conflict_type) for each conflict
        """
        conflicts = []
        
        for change1 in self.changes:
            for change2 in other.changes:
                conflict_type = change1.conflicts_with(change2)
                if conflict_type != ConflictType.NONE:
                    conflicts.append((change1, change2, conflict_type))
        
        return conflicts


class RepairTool:
    """
    Enhanced repair tool for applying coordinated fixes across multiple files.
    
    This class provides transaction-based multi-file updates with conflict detection,
    consistency validation, and failure recovery mechanisms.
    """
    
    def __init__(self, 
                 rollback_manager: Optional[RollbackManager] = None,
                 relationships_path: Optional[str] = None,
                 dependency_graph: Optional[DependencyGraph] = None,
                 fs_cache: Optional[FileSystemStateCache] = None):
        """
        Initialize the RepairTool.
        
        Args:
            rollback_manager: RollbackManager for transaction management
            relationships_path: Path to the relationships JSON file
            dependency_graph: DependencyGraph for code dependencies
            fs_cache: Optional FileSystemStateCache instance.
        """
        # Initialize components
        self.rollback_manager = rollback_manager or RollbackManager()
        # Pass fs_cache to CodeRelationshipAnalyzer if it also takes it, for now stub doesn't need it passed.
        self.relationship_analyzer = CodeRelationshipAnalyzer()
        self.relationship_provider = RelationshipContextProvider(relationships_path) # This might need cache too
        self.test_runner = TestRunner()
        self.dependency_graph = dependency_graph or DependencyGraph()
        self.incremental_analyzer = IncrementalAnalyzer(self.dependency_graph)
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()
        
        # Default relationships path if not provided
        self.relationships_path = relationships_path or "triangulum_relationships.json"
        
        # Track repair plans
        self.repair_plans: Dict[str, RepairPlan] = {}
        self.active_repairs: Dict[str, str] = {}  # Maps repair ID to transaction ID
        self.completed_repairs: List[str] = []
        self.failed_repairs: List[str] = []
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        logger.info("RepairTool initialized")
    
    def create_repair_plan(self, 
                          name: str, 
                          description: str, 
                          changes: List[FileChange],
                          dependencies: Optional[List[str]] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> RepairPlan:
        """
        Create a new repair plan.
        
        Args:
            name: Name of the repair plan
            description: Description of the repair plan
            changes: List of file changes
            dependencies: List of repair plan IDs that this plan depends on
            metadata: Additional metadata for the repair plan
            
        Returns:
            The created repair plan
        """
        with self.lock:
            # Generate a unique ID
            repair_id = str(uuid.uuid4())
            
            # Create the repair plan
            repair_plan = RepairPlan(
                id=repair_id,
                name=name,
                description=description,
                changes=changes,
                dependencies=dependencies or [],
                metadata=metadata or {}
            )
            
            # Add to repair plans
            self.repair_plans[repair_id] = repair_plan
            
            logger.info(f"Created repair plan {repair_id}: {name}")
            return repair_plan
    
    def get_repair_plan(self, repair_id: str) -> Optional[RepairPlan]:
        """
        Get a repair plan by ID.
        
        Args:
            repair_id: ID of the repair plan
            
        Returns:
            The repair plan, or None if not found
        """
        with self.lock:
            return self.repair_plans.get(repair_id)
    
    def detect_conflicts(self, repair_id: str, other_repair_id: str) -> List[Tuple[FileChange, FileChange, ConflictType]]:
        """
        Detect conflicts between two repair plans.
        
        Args:
            repair_id: ID of the first repair plan
            other_repair_id: ID of the second repair plan
            
        Returns:
            List of conflicts between the repair plans
        """
        with self.lock:
            repair_plan = self.get_repair_plan(repair_id)
            other_repair_plan = self.get_repair_plan(other_repair_id)
            
            if not repair_plan or not other_repair_plan:
                return []
            
            return repair_plan.conflicts_with(other_repair_plan)
    
    def resolve_conflicts(self, 
                         conflicts: List[Tuple[FileChange, FileChange, ConflictType]],
                         strategy: ConflictResolutionStrategy) -> List[FileChange]:
        """
        Resolve conflicts between file changes.
        
        Args:
            conflicts: List of conflicts to resolve
            strategy: Strategy for resolving conflicts
            
        Returns:
            List of resolved file changes
        """
        resolved_changes = []
        
        for change1, change2, conflict_type in conflicts:
            if strategy == ConflictResolutionStrategy.ABORT:
                # No changes to return
                continue
            
            elif strategy == ConflictResolutionStrategy.PRIORITIZE_FIRST:
                resolved_changes.append(change1)
            
            elif strategy == ConflictResolutionStrategy.PRIORITIZE_SECOND:
                resolved_changes.append(change2)
            
            elif strategy == ConflictResolutionStrategy.MERGE:
                # Attempt to merge the changes
                # This is a simplified merge strategy that works for non-overlapping changes
                if conflict_type == ConflictType.ADJACENT_LINES:
                    # For adjacent lines, we can often just combine the changes
                    merged_change = FileChange(
                        file_path=change1.file_path,
                        start_line=min(change1.start_line, change2.start_line),
                        end_line=max(change1.end_line, change2.end_line),
                        original_content=change1.original_content,  # This is simplified
                        new_content=change1.new_content,  # This is simplified
                        change_type="replace",
                        metadata={"merged": True, "source": [change1.metadata, change2.metadata]}
                    )
                    resolved_changes.append(merged_change)
                else:
                    # For other conflict types, fall back to prioritizing the first change
                    resolved_changes.append(change1)
            
            elif strategy == ConflictResolutionStrategy.SEQUENTIAL:
                # Apply both changes in sequence
                resolved_changes.append(change1)
                resolved_changes.append(change2)
        
        return resolved_changes
    
    def validate_consistency(self, repair_plan: RepairPlan) -> Tuple[bool, List[str]]:
        """
        Validate the consistency of a repair plan.
        
        This checks that the changes in the repair plan are consistent with each other
        and with the codebase as a whole.
        
        Args:
            repair_plan: The repair plan to validate
            
        Returns:
            Tuple of (is_valid, list of validation messages)
        """
        validation_messages = []
        
        # Check that all files exist
        for change in repair_plan.changes:
            if not self.fs_cache.exists(change.file_path):
                validation_messages.append(f"File {change.file_path} does not exist (checked via cache)")
        
        if validation_messages:
            return False, validation_messages
        
        # Check that changes don't conflict with each other
        for i, change1 in enumerate(repair_plan.changes):
            for j, change2 in enumerate(repair_plan.changes[i+1:], i+1):
                conflict_type = change1.conflicts_with(change2)
                if conflict_type != ConflictType.NONE:
                    validation_messages.append(
                        f"Conflict between changes {i} and {j}: {conflict_type.name}"
                    )
        
        if validation_messages:
            return False, validation_messages
        
        # Check for dependency consistency using the dependency graph
        affected_files = repair_plan.get_affected_files()
        
        # Build a dependency graph for the affected files
        try:
            # Use incremental analyzer to update the dependency graph
            if hasattr(self, 'incremental_analyzer') and self.incremental_analyzer:
                # Get current content of affected files
                updated_files = {}
                for file_path in affected_files:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            updated_files[file_path] = f.read()
                    except Exception as e:
                        logger.warning(f"Error reading file {file_path}: {e}")
                
                # Analyze changes incrementally
                self.incremental_analyzer.analyze_changes(updated_files)
                
                # Calculate impact boundary
                impact_boundary = self._calculate_impact_boundary(affected_files)
                if impact_boundary:
                    logger.info(f"Impact boundary for repair: {len(impact_boundary)} files")
                    # Add impact boundary to metadata for later use
                    repair_plan.metadata["impact_boundary"] = list(impact_boundary)
            else:
                # Fall back to direct graph building
                self.dependency_graph.build_graph(affected_files)
            
            # Check for cycles in the dependency graph
            cycles = self.dependency_graph.find_cycles()
            if cycles:
                for cycle in cycles:
                    validation_messages.append(f"Dependency cycle detected: {' -> '.join(cycle)}")
                    
            # Check for semantic consistency using static analysis
            semantic_issues = self._check_semantic_consistency(repair_plan)
            validation_messages.extend(semantic_issues)
        except Exception as e:
            validation_messages.append(f"Error analyzing dependencies: {e}")
            logger.error(f"Dependency analysis error: {e}", exc_info=True)
        
        if validation_messages:
            return False, validation_messages
        
        # All checks passed
        return True, ["Repair plan is consistent"]
    
    def _calculate_impact_boundary(self, affected_files: Set[str]) -> Set[str]:
        """
        Calculate the impact boundary of a set of affected files.
        
        The impact boundary includes all files that might be affected by changes
        to the given files, based on dependency analysis.
        
        Args:
            affected_files: Set of files that will be changed
            
        Returns:
            Set of files in the impact boundary
        """
        impact_boundary = set(affected_files)
        
        # Add all files that depend on affected files
        for file_path in affected_files:
            if file_path in self.dependency_graph:
                dependents = self.dependency_graph.transitive_dependents(file_path)
                impact_boundary.update(dependents)
        
        return impact_boundary
    
    def _check_semantic_consistency(self, repair_plan: RepairPlan) -> List[str]:
        """
        Check for semantic consistency issues in a repair plan.
        
        This performs deeper analysis to detect potential semantic issues
        that might not be caught by simple conflict detection.
        
        Args:
            repair_plan: The repair plan to check
            
        Returns:
            List of validation messages for any semantic issues found
        """
        issues = []
        
        # Group changes by file
        changes_by_file = {}
        for change in repair_plan.changes:
            if change.file_path not in changes_by_file:
                changes_by_file[change.file_path] = []
            changes_by_file[change.file_path].append(change)
        
        # Check for semantic issues in each file
        for file_path, changes in changes_by_file.items():
            # Read the current file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Apply all changes to get the final content
                lines = content.splitlines()
                
                # Sort changes by line number in reverse order to avoid line number shifts
                sorted_changes = sorted(changes, key=lambda c: c.start_line, reverse=True)
                
                for change in sorted_changes:
                    if change.change_type == "replace":
                        # Replace the lines
                        new_lines = change.new_content.splitlines()
                        lines[change.start_line-1:change.end_line] = new_lines
                    elif change.change_type == "insert":
                        # Insert the lines
                        new_lines = change.new_content.splitlines()
                        lines.insert(change.start_line, *new_lines)
                    elif change.change_type == "delete":
                        # Delete the lines
                        del lines[change.start_line-1:change.end_line]
                
                # Reconstruct the content
                new_content = "\n".join(lines)
                
                # Check for syntax errors in Python files
                if file_path.endswith('.py'):
                    try:
                        import ast
                        ast.parse(new_content)
                    except SyntaxError as e:
                        issues.append(f"Syntax error in {file_path} after changes: {e}")
                
                # Check for unbalanced brackets, parentheses, etc.
                bracket_pairs = [('(', ')'), ('[', ']'), ('{', '}')]
                for open_char, close_char in bracket_pairs:
                    if new_content.count(open_char) != new_content.count(close_char):
                        issues.append(
                            f"Unbalanced {open_char}{close_char} in {file_path} after changes"
                        )
                
                # Check for other common issues
                if '<<<<<<< HEAD' in new_content or '=======' in new_content or '>>>>>>>' in new_content:
                    issues.append(f"Merge conflict markers found in {file_path} after changes")
                
            except Exception as e:
                issues.append(f"Error checking semantic consistency for {file_path}: {e}")
        
        return issues
    
    def apply_repair(self, repair_id: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Apply a repair plan.
        
        Args:
            repair_id: ID of the repair plan to apply
            dry_run: If True, don't actually apply the changes
            
        Returns:
            Dictionary with the result of the operation
        """
        with self.lock:
            repair_plan = self.get_repair_plan(repair_id)
            if not repair_plan:
                return {
                    "success": False,
                    "message": f"Repair plan {repair_id} not found"
                }
            
            # Check if all dependencies are completed
            for dep_id in repair_plan.dependencies:
                dep_plan = self.get_repair_plan(dep_id)
                if not dep_plan or dep_plan.status != RepairStatus.COMPLETED:
                    return {
                        "success": False,
                        "message": f"Dependency {dep_id} is not completed"
                    }
            
            # Check for conflicts with active repairs
            active_conflicts = self._check_active_conflicts(repair_plan)
            if active_conflicts:
                return {
                    "success": False,
                    "message": "Repair conflicts with active repairs",
                    "conflicts": active_conflicts
                }
            
            # Validate consistency
            is_valid, validation_messages = self.validate_consistency(repair_plan)
            if not is_valid:
                return {
                    "success": False,
                    "message": "Repair plan is not consistent",
                    "validation_messages": validation_messages
                }
            
            # If this is a dry run, return success without applying changes
            if dry_run:
                return {
                    "success": True,
                    "message": "Dry run successful",
                    "dry_run": True,
                    "affected_files": list(repair_plan.get_affected_files()),
                    "impact_boundary": repair_plan.metadata.get("impact_boundary", [])
                }
            
            # Start a transaction
            transaction_name = f"Repair: {repair_plan.name}"
            with self.rollback_manager.transaction(transaction_name) as transaction:
                try:
                    # Update repair status
                    repair_plan.status = RepairStatus.IN_PROGRESS
                    
                    # Track the transaction ID
                    self.active_repairs[repair_id] = transaction.id
                    
                    # Take snapshots of all affected files
                    affected_files = repair_plan.get_affected_files()
                    
                    # Also take snapshots of files in the impact boundary
                    impact_boundary = set(repair_plan.metadata.get("impact_boundary", []))
                    all_affected = affected_files.union(impact_boundary)
                    
                    for file_path in all_affected:
                        if self.fs_cache.exists(file_path): # Use cache for exists check
                            self.rollback_manager.add_file_snapshot(file_path)
                    
                    # Apply changes in a specific order to minimize conflicts
                    ordered_changes = self._order_changes_for_application(repair_plan.changes)
                    
                    # Apply changes
                    applied_changes = []
                    for change in ordered_changes:
                        # Read the current file content
                        try:
                            with open(change.file_path, 'r', encoding='utf-8') as f:
                                current_content = f.read()
                        except Exception as e:
                            raise Exception(f"Failed to read file {change.file_path}: {e}")
                        
                        # Apply the change
                        if change.change_type == "replace":
                            # Get the line range to replace
                            lines = current_content.splitlines()
                            
                            # Ensure line numbers are valid
                            if change.start_line < 1 or change.end_line > len(lines):
                                raise Exception(
                                    f"Invalid line range: {change.start_line}-{change.end_line} "
                                    f"(file has {len(lines)} lines)"
                                )
                            
                            # Replace the lines
                            new_lines = lines.copy()
                            new_lines[change.start_line-1:change.end_line] = change.new_content.splitlines()
                            new_content = "\n".join(new_lines)
                            
                            # Write the new content
                            # Convert to bytes for atomic_write
                            atomic_write(change.file_path, new_content.encode('utf-8'))
                            self.fs_cache.invalidate(change.file_path) # Invalidate cache after write
                            
                            applied_changes.append({
                                "file_path": change.file_path,
                                "change_type": change.change_type,
                                "start_line": change.start_line,
                                "end_line": change.end_line,
                                "success": True
                            })
                        
                        elif change.change_type == "insert":
                            # Get the line to insert after
                            lines = current_content.splitlines()
                            
                            # Ensure line number is valid
                            if change.start_line < 0 or change.start_line > len(lines):
                                raise Exception(
                                    f"Invalid line number: {change.start_line} "
                                    f"(file has {len(lines)} lines)"
                                )
                            
                            # Insert the lines
                            new_lines = lines.copy()
                            new_lines.insert(change.start_line, change.new_content)
                            new_content = "\n".join(new_lines)
                            
                            # Write the new content
                            atomic_write(change.file_path, new_content.encode('utf-8'))
                            self.fs_cache.invalidate(change.file_path)
                            
                            applied_changes.append({
                                "file_path": change.file_path,
                                "change_type": change.change_type,
                                "start_line": change.start_line,
                                "success": True
                            })
                        
                        elif change.change_type == "delete":
                            # Get the line range to delete
                            lines = current_content.splitlines()
                            
                            # Ensure line numbers are valid
                            if change.start_line < 1 or change.end_line > len(lines):
                                raise Exception(
                                    f"Invalid line range: {change.start_line}-{change.end_line} "
                                    f"(file has {len(lines)} lines)"
                                )
                            
                            # Delete the lines
                            new_lines = lines.copy()
                            del new_lines[change.start_line-1:change.end_line]
                            new_content = "\n".join(new_lines)
                            
                            # Write the new content
                            atomic_write(change.file_path, new_content.encode('utf-8'))
                            self.fs_cache.invalidate(change.file_path)
                            
                            applied_changes.append({
                                "file_path": change.file_path,
                                "change_type": change.change_type,
                                "start_line": change.start_line,
                                "end_line": change.end_line,
                                "success": True
                            })
                    
                    # Update dependency graph with the changes
                    if hasattr(self, 'incremental_analyzer') and self.incremental_analyzer:
                        updated_files = {}
                        for file_path in affected_files:
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    updated_files[file_path] = f.read()
                            except Exception as e:
                                logger.warning(f"Error reading updated file {file_path}: {e}")
                        
                        # Update the dependency graph incrementally
                        self.incremental_analyzer.analyze_changes(updated_files)
                    
                    # Update repair status
                    repair_plan.status = RepairStatus.COMPLETED
                    self.completed_repairs.append(repair_id)
                    
                    # Remove from active repairs
                    del self.active_repairs[repair_id]
                    
                    return {
                        "success": True,
                        "message": "Repair applied successfully",
                        "applied_changes": applied_changes,
                        "affected_files": list(affected_files),
                        "impact_boundary": list(impact_boundary)
                    }
                
                except Exception as e:
                    # Update repair status
                    repair_plan.status = RepairStatus.FAILED
                    self.failed_repairs.append(repair_id)
                    
                    # Remove from active repairs
                    if repair_id in self.active_repairs:
                        del self.active_repairs[repair_id]
                    
                    # The transaction will be rolled back automatically
                    logger.error(f"Error applying repair {repair_id}: {e}", exc_info=True)
                    
                    return {
                        "success": False,
                        "message": f"Error applying repair: {e}",
                        "error": str(e)
                    }
    
    def _check_active_conflicts(self, repair_plan: RepairPlan) -> List[Dict[str, Any]]:
        """
        Check for conflicts with active repairs.
        
        Args:
            repair_plan: The repair plan to check
            
        Returns:
            List of conflict information dictionaries
        """
        conflicts = []
        
        # Get all active repairs
        for active_id, transaction_id in self.active_repairs.items():
            active_plan = self.get_repair_plan(active_id)
            if not active_plan:
                continue
            
            # Check for conflicts
            plan_conflicts = repair_plan.conflicts_with(active_plan)
            if plan_conflicts:
                for change1, change2, conflict_type in plan_conflicts:
                    conflicts.append({
                        "repair_id": active_id,
                        "repair_name": active_plan.name,
                        "file_path": change1.file_path,
                        "conflict_type": conflict_type.name,
                        "lines": f"{change1.start_line}-{change1.end_line}"
                    })
        
        return conflicts
    
    def _order_changes_for_application(self, changes: List[FileChange]) -> List[FileChange]:
        """
        Order changes for optimal application.
        
        This orders changes to minimize line number shifts and conflicts.
        
        Args:
            changes: List of file changes to order
            
        Returns:
            Ordered list of file changes
        """
        # Group changes by file
        changes_by_file = {}
        for change in changes:
            if change.file_path not in changes_by_file:
                changes_by_file[change.file_path] = []
            changes_by_file[change.file_path].append(change)
        
        # Order changes within each file
        ordered_changes = []
        for file_path, file_changes in changes_by_file.items():
            # Sort changes by line number in reverse order to avoid line number shifts
            file_changes.sort(key=lambda c: c.start_line, reverse=True)
            ordered_changes.extend(file_changes)
        
        return ordered_changes
    
    def rollback_repair(self, repair_id: str) -> Dict[str, Any]:
        """
        Rollback a repair.
        
        Args:
            repair_id: ID of the repair to rollback
            
        Returns:
            Dictionary with the result of the operation
        """
        with self.lock:
            repair_plan = self.get_repair_plan(repair_id)
            if not repair_plan:
                return {
                    "success": False,
                    "message": f"Repair plan {repair_id} not found"
                }
            
            # Check if the repair is active
            if repair_id in self.active_repairs:
                transaction_id = self.active_repairs[repair_id]
                
                # Rollback the transaction
                success = self.rollback_manager.rollback_transaction(transaction_id)
                
                if success:
                    # Update repair status
                    repair_plan.status = RepairStatus.ROLLED_BACK
                    
                    # Remove from active repairs
                    del self.active_repairs[repair_id]
                    
                    return {
                        "success": True,
                        "message": "Repair rolled back successfully"
                    }
                else:
                    return {
                        "success": False,
                        "message": "Failed to rollback repair"
                    }
            
            # Check if the repair is completed
            elif repair_id in self.completed_repairs:
                # For completed repairs, we need to find the transaction ID
                # This is a simplified approach - in a real system, you would store
                # the transaction ID with the repair plan
                transactions = self.rollback_manager.transaction_manager.get_transaction_history()
                
                # Find a transaction with a matching name
                transaction_id = None
                for transaction in transactions:
                    if transaction.name == f"Repair: {repair_plan.name}":
                        transaction_id = transaction.id
                        break
                
                if transaction_id:
                    # Rollback the transaction
                    success = self.rollback_manager.rollback_transaction(transaction_id)
                    
                    if success:
                        # Update repair status
                        repair_plan.status = RepairStatus.ROLLED_BACK
                        
                        # Remove from completed repairs
                        self.completed_repairs.remove(repair_id)
                        
                        return {
                            "success": True,
                            "message": "Repair rolled back successfully"
                        }
                    else:
                        return {
                            "success": False,
                            "message": "Failed to rollback repair"
                        }
                else:
                    return {
                        "success": False,
                        "message": "Could not find transaction for repair"
                    }
            
            # Repair is not active or completed
            return {
                "success": False,
                "message": f"Repair {repair_id} is not active or completed"
            }
    
    def verify_repair(self, repair_id: str, run_tests: bool = True, 
                     check_static_analysis: bool = True) -> Dict[str, Any]:
        """
        Verify a repair by running tests and static analysis.
        
        Args:
            repair_id: ID of the repair to verify
            run_tests: Whether to run tests
            check_static_analysis: Whether to run static analysis
            
        Returns:
            Dictionary with the verification result
        """
        with self.lock:
            repair_plan = self.get_repair_plan(repair_id)
            if not repair_plan:
                return {
                    "success": False,
                    "message": f"Repair plan {repair_id} not found"
                }
            
            # Check if the repair is completed
            if repair_plan.status != RepairStatus.COMPLETED:
                return {
                    "success": False,
                    "message": f"Repair {repair_id} is not completed"
                }
            
            # Get affected files
            affected_files = repair_plan.get_affected_files()
            
            # Also check files in the impact boundary
            impact_boundary = set(repair_plan.metadata.get("impact_boundary", []))
            all_affected = affected_files.union(impact_boundary)
            
            verification_results = {
                "test_results": [],
                "static_analysis_results": [],
                "success": True,
                "message": "Verification passed"
            }
            
            # Run tests if requested
            if run_tests:
                test_results = []
                for file_path in all_affected:
                    if not self.fs_cache.exists(file_path): # Use cache
                        continue
                        
                    # Find tests related to this file
                    related_tests = self.test_runner.find_related_tests(file_path)
                    
                    if related_tests:
                        # Run the tests
                        result = self.test_runner.validate_patch(file_path, related_tests)
                        
                        test_results.append({
                            "file_path": file_path,
                            "success": result.success,
                            "message": result.message,
                            "details": result.details
                        })
                    else:
                        # No tests found
                        test_results.append({
                            "file_path": file_path,
                            "success": True,  # Assume success if no tests
                            "message": "No tests found for this file",
                            "details": {}
                        })
                
                # Check if all tests passed
                all_tests_passed = all(result["success"] for result in test_results)
                verification_results["test_results"] = test_results
                
                if not all_tests_passed:
                    verification_results["success"] = False
                    verification_results["message"] = "Test verification failed"
            
            # Run static analysis if requested
            if check_static_analysis:
                static_analysis_results = []
                
                for file_path in all_affected:
                    if not self.fs_cache.exists(file_path): # Use cache
                        continue
                        
                    # Perform static analysis based on file type
                    if file_path.endswith('.py'):
                        # Check Python syntax
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            import ast
                            ast.parse(content)
                            
                            static_analysis_results.append({
                                "file_path": file_path,
                                "success": True,
                                "message": "Static analysis passed",
                                "details": {}
                            })
                        except SyntaxError as e:
                            static_analysis_results.append({
                                "file_path": file_path,
                                "success": False,
                                "message": f"Syntax error: {e}",
                                "details": {"error": str(e), "line": e.lineno, "offset": e.offset}
                            })
                        except Exception as e:
                            static_analysis_results.append({
                                "file_path": file_path,
                                "success": False,
                                "message": f"Error during static analysis: {e}",
                                "details": {"error": str(e)}
                            })
                    else:
                        # For other file types, just check that they exist and are readable
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                f.read()
                            
                            static_analysis_results.append({
                                "file_path": file_path,
                                "success": True,
                                "message": "File exists and is readable",
                                "details": {}
                            })
                        except Exception as e:
                            static_analysis_results.append({
                                "file_path": file_path,
                                "success": False,
                                "message": f"Error reading file: {e}",
                                "details": {"error": str(e)}
                            })
                
                # Check if all static analyses passed
                all_analyses_passed = all(result["success"] for result in static_analysis_results)
                verification_results["static_analysis_results"] = static_analysis_results
                
                if not all_analyses_passed:
                    verification_results["success"] = False
                    verification_results["message"] = "Static analysis verification failed"
            
            # If verification failed, consider rolling back
            if not verification_results["success"] and repair_plan.metadata.get("auto_rollback_on_verification_failure", False):
                logger.warning(f"Verification failed for repair {repair_id}, auto-rolling back")
                rollback_result = self.rollback_repair(repair_id)
                verification_results["rollback"] = rollback_result
            
            return verification_results
    
    def get_repair_status(self, repair_id: str) -> Dict[str, Any]:
        """
        Get the status of a repair.
        
        Args:
            repair_id: ID of the repair
            
        Returns:
            Dictionary with the repair status
        """
        with self.lock:
            repair_plan = self.get_repair_plan(repair_id)
            if not repair_plan:
                return {
                    "success": False,
                    "message": f"Repair plan {repair_id} not found"
                }
            
            return {
                "success": True,
                "repair_id": repair_id,
                "name": repair_plan.name,
                "status": repair_plan.status.name,
                "affected_files": list(repair_plan.get_affected_files()),
                "created_at": repair_plan.created_at
            }
    
    def get_all_repairs(self) -> List[Dict[str, Any]]:
        """
        Get all repair plans.
        
        Returns:
            List of dictionaries with repair plan information
        """
        with self.lock:
            return [
                {
                    "repair_id": repair_id,
                    "name": repair_plan.name,
                    "description": repair_plan.description,
                    "status": repair_plan.status.name,
                    "affected_files": list(repair_plan.get_affected_files()),
                    "created_at": repair_plan.created_at
                }
                for repair_id, repair_plan in self.repair_plans.items()
            ]


class PatcherAgent:
    """
    Agent responsible for generating and applying patches to fix bugs.
    
    The PatcherAgent uses code relationship analysis to understand the context
    of a bug and generate appropriate fixes. It then applies the patch and
    verifies that it resolves the issue.
    """
    
    def __init__(self,
                 tooling_manager=None,
                 relationships_path: Optional[str] = None,
                 fs_cache: Optional[FileSystemStateCache] = None):
        """
        Initialize the PatcherAgent.
        
        Args:
            tooling_manager: Reference to the tooling manager (optional)
            relationships_path: Path to the relationships JSON file (optional)
            fs_cache: Optional FileSystemStateCache instance.
        """
        self.tooling_manager = tooling_manager
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()

        # Pass the (potentially new) fs_cache instance to components it initializes
        self.relationship_analyzer = CodeRelationshipAnalyzer() # Stub's constructor doesn't take fs_cache yet.
                                                                # If it did: CodeRelationshipAnalyzer(fs_cache=self.fs_cache)
                                                                # The stub *internally* creates one.
        self.relationship_provider = RelationshipContextProvider(relationships_path) # This might also benefit from fs_cache
        self.test_runner = TestRunner()
        
        # Create a RepairTool instance, passing down the cache
        self.repair_tool = RepairTool(relationships_path=relationships_path, fs_cache=self.fs_cache)
        
        # Default relationships path if not provided
        self.relationships_path = relationships_path or "triangulum_relationships.json"
        
        logger.info("PatcherAgent initialized")

    def execute_repair(self, task):
        """
        The main entry point for the PatcherAgent, invoked by the MetaAgent.
        
        Args:
            task: Dictionary containing task information
                - file_path: Path to the file containing the bug
                - bug_id: Identifier for the bug
                - bug_description: Description of the bug
                - error_message: Error message if available
                
        Returns:
            String indicating success or failure
        """
        logger.info(f"PatcherAgent received repair task: {task}")

        try:
            # Ensure task is a dict, as expected by subsequent calls if we changed them
            if not isinstance(task, dict):
                 # This case should ideally not happen if called correctly,
                 # but adding a safeguard or logging if task structure is unexpected.
                 logger.error(f"PatcherAgent.execute_repair expects task to be a dict, got {type(task)}")
                 # Convert or raise, for now assume it's dict-like due to previous error

            # 1. Analyze the bug
            context = self._analyze(task)

            # 2. Generate a patch
            patch = self._generate_patch(task, context)

            # 3. Apply the patch
            self._apply(patch)

            # 4. Verify the patch
            test_result = self._verify(task)

            if test_result.success:
                logger.info("Repair successful!")
                return "SUCCESS"
            else:
                logger.warning("Repair failed: tests did not pass.")
                self._rollback(patch)
                return "FAILURE: Tests failed."

        except Exception as e:
            logger.error(f"An error occurred during repair: {e}")
            # Ensure rollback is attempted on any failure
            if 'patch' in locals() and patch:
                self._rollback(patch)
            return f"FAILURE: {e}"

    def _analyze(self, task):
        """
        Analyzes the bug to understand its context using code relationships.
        
        This method performs a deep analysis of the file containing the bug,
        its dependencies, and related files to provide comprehensive context
        for patch generation.
        
        Args:
            task: Dictionary containing task information
                - file_path: Path to the file containing the bug
                - bug_id: Identifier for the bug
                - bug_description: Description of the bug
                - error_message: Error message if available
        
        Returns:
            Dictionary containing analysis context
        """
        file_path = task['file_path'] # Changed to dict access
        logger.info(f"Analyzing bug in {file_path}")
        
        # Ensure we have analyzed the code relationships
        if not self.relationship_provider.relationships:
            # If relationships haven't been loaded yet, analyze directory
            directory = os.path.dirname(file_path)
            self.relationship_analyzer.analyze_directory(directory)
            self.relationship_provider.load_relationships(self.relationship_analyzer.relationships)
            
            # Save relationships for future use
            self.relationship_analyzer.save_relationships(self.relationships_path)
        
        # Get repair context from relationship provider
        repair_context = self.relationship_provider.get_context_for_repair(file_path)
        
        # Get impact analysis to understand potential side effects
        impact_analysis = self.relationship_provider.get_impact_analysis(file_path)
        
        # Get refactoring suggestions
        refactoring_suggestions = self.relationship_provider.suggest_refactoring(file_path)
        
        # Read the file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            file_content = "Error: Could not read file content"
        
        # Read related files if they're not too many
        related_files_content = {}
        related_files = self.relationship_provider.get_related_files(file_path, max_depth=1)
        for related_file in related_files[:5]:  # Limit to 5 related files to avoid overwhelming context
            try:
                with open(related_file, 'r', encoding='utf-8') as f:
                    related_files_content[related_file] = f.read()
            except Exception as e:
                logger.error(f"Error reading related file {related_file}: {e}")
        
        # Compile comprehensive context
        context = {
            "file_path": file_path,
            "file_content": file_content,
            "bug_id": task.get('bug_id', 'unknown'),
            "bug_description": task.get('bug_description', 'No description provided'), # Corrected key
            "error_message": task.get('error_message'),
            "repair_context": repair_context,
            "impact_analysis": impact_analysis,
            "refactoring_suggestions": refactoring_suggestions,
            "related_files": related_files,
            "related_files_content": related_files_content
        }
        
        logger.info(f"Analysis completed for {file_path}")
        return context

    def _generate_patch(self, task, context):
        """
        Generates a patch to fix the bug based on the analysis context.
        
        In a production system, this would use an LLM to generate a patch
        based on the comprehensive context provided by the analysis step.
        
        Args:
            task: Dictionary containing task information
            context: Analysis context from _analyze method
        
        Returns:
            Dictionary containing patch information
        """
        logger.info("Generating patch based on analysis context")
        
        file_path = task['file_path']
        bug_id = task.get('bug_id', 'unknown')
        
        # In a real implementation, this would use an LLM to generate a patch
        # based on the comprehensive context.
        # For demonstration purposes, we'll create a simulated patch:
        
        # Example of how this would work with a real LLM:
        # 1. Format the context for the LLM
        # 2. Send prompt to LLM requesting a patch in a specific format
        # 3. Parse the LLM response to extract the patch diff
        
        # Simulated patch for demonstration
        patch_diff = f"""
# Generated patch for bug {bug_id} in {file_path}
# This patch addresses the issue based on relationship analysis

--- {file_path}
+++ {file_path}
@@ -10,7 +10,7 @@
 # Simulated patch content would go here
 # It would include contextual fixes based on:
-# - Code relationships
+# - Code relationships and dependencies
 # - File complexity
 # - Impact analysis
 # - Related file context
"""
        
        # Log impact information for awareness
        impact = context.get('impact_analysis', {})
        if impact.get('risk_level') == 'high':
            logger.warning(f"High-risk patch: affects {impact.get('total_dependents_count', 0)} dependent files")
        
        patch = {
            "bug_id": bug_id,
            "file_path": file_path,
            "patch_diff": patch_diff,
            "impact_level": impact.get('risk_level', 'low'),
            "related_files": context.get('related_files', [])
        }
        
        logger.info(f"Generated patch for {file_path}")
        return patch

    def _apply(self, patch):
        """
        Applies the patch to the specified file and potentially related files.
        
        This method handles both the primary file patch and any necessary changes
        to related files based on impact analysis.
        
        Args:
            patch: Dictionary containing patch information
                - bug_id: Identifier for the bug
                - file_path: Path to the file to patch
                - patch_diff: Diff content for the patch (or full content replacement)
                - impact_level: Risk level of the patch
                - related_files: List of related files that might need changes
        
        Raises:
            Exception: If patch application fails
        """
        file_path = patch['file_path']
        logger.info(f"Applying patch to {file_path}")
        
        # Create backup of original file for potential rollback
        backup_path = f"{file_path}.bak"
        try:
            # Read original content first
            src_content_bytes = Path(file_path).read_bytes()
            atomic_write(backup_path, src_content_bytes)
            self.fs_cache.invalidate(backup_path) # Invalidate cache for the new backup file
            logger.info(f"Created backup at {backup_path} using atomic_write")
        except Exception as e:
            logger.error(f"Failed to create backup of {file_path}: {e}")
            raise Exception(f"Failed to create backup: {e}")
        
        # Track applied patches for potential rollback
        self.applied_patches = {
            'primary': {
                'file_path': file_path,
                'backup_path': backup_path
            },
            'related': []
        }
        
        # Apply the patch to the primary file
        try:
            # Check if the patch_diff appears to be a proper git-style patch (starts with 'diff' or '---')
            patch_content = patch['patch_diff']
            if patch_content.lstrip().startswith(('diff', '---')):
                # Use PatchBundle for git-style patches
                patch_bundle = PatchBundle(patch['bug_id'], patch_content, fs_cache=self.fs_cache) # Pass fs_cache
                patch_bundle.apply()  # PatchBundle.apply() doesn't take arguments
                logger.info(f"Applied git-style patch to {file_path}")
                # Assuming PatchBundle.apply() internally handles its own cache invalidations if necessary,
                # or it will be refactored separately. For now, focus on direct writes in this class.
                # If PatchBundle uses standard file I/O, it's a candidate for later refactoring.
                self.fs_cache.invalidate(file_path) # Invalidate after PatchBundle.apply()
            else:
                # Direct content replacement
                atomic_write(file_path, patch_content.encode('utf-8')) # Assuming patch_content is str
                self.fs_cache.invalidate(file_path)
                logger.info(f"Applied direct content replacement to {file_path} using atomic_write")
            
        except Exception as e:
            logger.error(f"Failed to apply patch to {file_path}: {e}")
            # Try to restore from backup
            self._restore_from_backup(file_path, backup_path)
            raise Exception(f"Failed to apply patch: {e}")
        
        # If patch has high impact, check if related files need updates
        # In a real implementation with an LLM, this would generate companion patches
        # for related files that need to be updated for compatibility
        if patch.get('impact_level') == 'high' and patch.get('related_files'):
            logger.info(f"High impact patch: checking {len(patch['related_files'])} related files")
            
            # For demonstration purposes, we're not actually modifying related files,
            # but in a real implementation, you would:
            # 1. Generate companion patches for related files
            # 2. Create backups of those files
            # 3. Apply the companion patches
            # 4. Track them for potential rollback
            
            for related_file in patch.get('related_files', [])[:3]:  # Limit to 3
                logger.info(f"Would update related file: {related_file}")
                
                # Simulated tracking of related file changes for rollback
                self.applied_patches['related'].append({
                    'file_path': related_file,
                    'backup_path': None  # In real implementation, would have backup path
                })

    def _verify(self, task):
        """
        Verifies the patch by running relevant tests.
        
        This method uses the test_runner to execute tests that validate the changes
        made by the patch. It considers both the primary file and any related files
        that might be affected by the changes.
        
        Args:
            task: Dictionary containing task information
        
        Returns:
            TestResult object indicating success or failure
        """
        file_path = task['file_path']
        logger.info(f"Verifying patch for {file_path}")
        
        # Find tests related to the primary file
        related_tests = self.test_runner.find_related_tests(file_path)
        
        # If no specific tests were found, fall back to running a specific test path
        if not related_tests:
            logger.warning(f"No specific tests found for {file_path}, using fallback test approach")
            return self.test_runner.run_specific_test(file_path)
        
        # Run tests for the primary file
        logger.info(f"Running {len(related_tests)} tests for {file_path}")
        primary_result = self.test_runner.validate_patch(file_path, related_tests)
        
        if not primary_result.success:
            logger.warning(f"Tests failed for primary file {file_path}")
            return primary_result
        
        logger.info(f"Tests passed for primary file {file_path}")
        
        # If we modified related files, verify those too
        related_results = []
        if hasattr(self, 'applied_patches') and self.applied_patches.get('related'):
            for related in self.applied_patches['related']:
                if related.get('file_path'):
                    related_file = related['file_path']
                    logger.info(f"Verifying related file: {related_file}")
                    
                    # Find tests for this related file
                    file_tests = self.test_runner.find_related_tests(related_file)
                    
                    if file_tests:
                        # Run tests specifically related to this file
                        related_result = self.test_runner.validate_patch(related_file, file_tests)
                        related_results.append(related_result)
                    else:
                        # If no specific tests, assume it passes if the main tests pass
                        logger.info(f"No specific tests found for related file {related_file}")
        
        # Check if any related tests failed
        failing_related = [r for r in related_results if not r.success]
        if failing_related:
            # Get details from the first failing test
            first_failure = failing_related[0]
            logger.warning(f"Tests failed for related files: {first_failure.message}")
            return TestResult(False, f"Related file tests failed: {first_failure.message}", first_failure.details)
        
        # All tests passed
        return primary_result

    def _rollback(self, patch):
        """
        Rolls back the patch if verification fails.
        
        This method restores all modified files from their backups to ensure
        the system returns to its previous state.
        
        Args:
            patch: Dictionary containing patch information
        """
        logger.info(f"Rolling back patch for {patch['file_path']}")
        
        # Check if we have applied patches to roll back
        if not hasattr(self, 'applied_patches'):
            logger.warning("No applied patches found to roll back")
            return
        
        # Roll back primary file
        primary = self.applied_patches.get('primary')
        if primary:
            self._restore_from_backup(primary['file_path'], primary['backup_path'])
        
        # Roll back related files
        for related in self.applied_patches.get('related', []):
            if related.get('file_path') and related.get('backup_path'):
                self._restore_from_backup(related['file_path'], related['backup_path'])
        
        logger.info("Rollback completed")
    
    def _restore_from_backup(self, file_path: str, backup_path: str) -> bool:
        """
        Restore a file from its backup.
        
        Args:
            file_path: Path to the file to restore
            backup_path: Path to the backup file
        
        Returns:
            True if successful, False otherwise
        """
        if not self.fs_cache.exists(backup_path): # Use cache
            logger.error(f"Backup file {backup_path} not found (checked via cache)")
            # Attempt direct check if critical, but for now trust cache or assume external check failed
            if not Path(backup_path).exists():
                 logger.error(f"Backup file {backup_path} confirmed not found by direct check.")
                 return False
            else: # Cache was stale, file actually exists
                 logger.warning(f"Cache indicated backup {backup_path} was absent, but it exists. Proceeding with restore.")
                 self.fs_cache.invalidate(backup_path) # Correct the cache
        
        try:
            backup_content_bytes = Path(backup_path).read_bytes()
            atomic_write(file_path, backup_content_bytes)
            self.fs_cache.invalidate(file_path) # Invalidate restored file
            logger.info(f"Restored {file_path} from backup {backup_path} using atomic_write")
            
            # Remove backup file
            atomic_delete(backup_path)
            self.fs_cache.invalidate(backup_path) # Invalidate deleted backup
            logger.info(f"Deleted backup file {backup_path} using atomic_delete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore {file_path} from backup {backup_path}: {e}")
            return False
