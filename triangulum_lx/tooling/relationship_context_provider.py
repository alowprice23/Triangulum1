"""
RelationshipContextProvider - Provides context based on code relationships.

This module provides context about relationships between code files
for self-healing and debugging purposes.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class RelationshipContextProvider:
    """
    Provides context based on code relationships.

    This class serves as a bridge between the code relationship analyzer
    and the self-healing system, providing context about relationships
    for diagnostic and repair purposes.
    """

    def __init__(self, relationships_path: Optional[str] = None):
        """
        Initialize the RelationshipContextProvider.

        Args:
            relationships_path: Path to the relationships JSON file (optional)
        """
        self.relationships = {}
        self.dependency_graph = {}
        self.reverse_dependency_graph = {}
        
        if relationships_path and os.path.exists(relationships_path):
            self.load_relationships_from_file(relationships_path)
        
        logger.info("RelationshipContextProvider initialized")

    def load_relationships_from_file(self, relationships_path: str) -> Dict[str, Any]:
        """
        Load relationships from a JSON file.

        Args:
            relationships_path: Path to the relationships JSON file

        Returns:
            Dictionary containing relationships
        """
        try:
            with open(relationships_path, 'r', encoding='utf-8') as f:
                self.relationships = json.load(f)
            
            logger.info(f"Loaded relationships from {relationships_path}")
            self._build_dependency_graphs()
            return self.relationships
        
        except Exception as e:
            logger.error(f"Error loading relationships from {relationships_path}: {e}")
            return {}

    def load_relationships(self, relationships: Dict[str, Any]) -> None:
        """
        Load relationships from a dictionary.

        Args:
            relationships: Dictionary containing relationships
        """
        self.relationships = relationships
        self._build_dependency_graphs()
        logger.info("Loaded relationships from dictionary")

    def save_relationships(self, output_path: Optional[str] = None) -> bool:
        """
        Save relationships to a JSON file.

        Args:
            output_path: Path to save the relationships (optional)

        Returns:
            True if successful, False otherwise
        """
        if not self.relationships:
            logger.warning("No relationships to save")
            return False
        
        if not output_path:
            output_path = "triangulum_relationships.json"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.relationships, f, indent=2)
            
            logger.info(f"Saved relationships to {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving relationships to {output_path}: {e}")
            return False

    def _build_dependency_graphs(self) -> None:
        """
        Build dependency graphs from relationships.
        """
        self.dependency_graph = {}
        self.reverse_dependency_graph = {}
        
        for file_path, info in self.relationships.items():
            # Forward dependencies (what this file imports)
            self.dependency_graph[file_path] = info.get("imports", [])
            
            # Reverse dependencies (what files import this file)
            self.reverse_dependency_graph[file_path] = info.get("imported_by", [])

    def get_related_files(self, file_path: str, max_depth: int = 2) -> List[str]:
        """
        Get files related to the given file.

        Args:
            file_path: Path to the file
            max_depth: Maximum depth of relationships to consider

        Returns:
            List of related file paths
        """
        if file_path not in self.relationships:
            return []
        
        # Start with direct dependencies
        related_files = set(self.dependency_graph.get(file_path, []))
        related_files.update(self.reverse_dependency_graph.get(file_path, []))
        
        # Add deeper dependencies if requested
        if max_depth > 1:
            for depth in range(1, max_depth):
                new_related = set()
                for related in related_files:
                    new_related.update(self.dependency_graph.get(related, []))
                    new_related.update(self.reverse_dependency_graph.get(related, []))
                
                # Remove files we've already considered
                new_related.difference_update(related_files)
                new_related.discard(file_path)
                
                # Add new related files
                related_files.update(new_related)
        
        # Remove the original file if it somehow got included
        related_files.discard(file_path)
        
        return list(related_files)

    def get_circular_dependencies(self) -> List[Tuple[str, str]]:
        """
        Get circular dependencies in the codebase.

        Returns:
            List of (file1, file2) tuples representing circular dependencies
        """
        circular = []
        
        for file_path, dependencies in self.dependency_graph.items():
            for dependency in dependencies:
                if dependency in self.dependency_graph and file_path in self.dependency_graph[dependency]:
                    # Ensure we only report each circular dependency once
                    if (dependency, file_path) not in circular:
                        circular.append((file_path, dependency))
        
        return circular

    def get_most_dependent_files(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get the most dependent files in the codebase.

        Args:
            limit: Maximum number of files to return

        Returns:
            List of (file_path, count) tuples sorted by dependency count
        """
        # Count the number of files that depend on each file
        dependents = {}
        for file_path, imported_by in self.reverse_dependency_graph.items():
            dependents[file_path] = len(imported_by)
        
        # Sort by count and limit
        sorted_dependents = sorted(dependents.items(), key=lambda x: x[1], reverse=True)
        return sorted_dependents[:limit]

    def get_file_complexity(self, file_path: str) -> Dict[str, Any]:
        """
        Get complexity metrics for a file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary containing complexity metrics
        """
        if file_path not in self.relationships:
            return {}
        
        info = self.relationships[file_path]
        complexity = {
            "functions": len(info.get("functions", [])),
            "classes": len(info.get("classes", [])),
            "imports": len(info.get("imports", [])),
            "imported_by": len(info.get("imported_by", [])),
            "dependencies": len(info.get("dependencies", []))
        }
        
        return complexity

    def suggest_refactoring(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Suggest refactoring for a file.

        Args:
            file_path: Path to the file

        Returns:
            List of refactoring suggestions
        """
        suggestions = []
        
        if file_path not in self.relationships:
            return suggestions
        
        # Check for high number of functions or classes
        complexity = self.get_file_complexity(file_path)
        if complexity.get("functions", 0) > 10:
            suggestions.append({
                "type": "split_file",
                "reason": "High number of functions",
                "description": f"File has {complexity['functions']} functions, consider splitting it into multiple files"
            })
        
        if complexity.get("classes", 0) > 5:
            suggestions.append({
                "type": "split_file",
                "reason": "High number of classes",
                "description": f"File has {complexity['classes']} classes, consider splitting it into multiple files"
            })
        
        # Check for high number of imports
        if complexity.get("imports", 0) > 15:
            suggestions.append({
                "type": "reduce_dependencies",
                "reason": "High number of imports",
                "description": f"File imports {complexity['imports']} other files, consider reducing dependencies"
            })
        
        # Check for high number of dependents
        if complexity.get("imported_by", 0) > 10:
            suggestions.append({
                "type": "extract_interface",
                "reason": "High number of dependents",
                "description": f"File is imported by {complexity['imported_by']} other files, consider extracting an interface"
            })
        
        # Check for circular dependencies
        circular = self.get_circular_dependencies()
        for file1, file2 in circular:
            if file1 == file_path or file2 == file_path:
                other = file2 if file1 == file_path else file1
                suggestions.append({
                    "type": "resolve_circular_dependency",
                    "reason": "Circular dependency",
                    "description": f"Circular dependency between {os.path.basename(file_path)} and {os.path.basename(other)}, consider refactoring"
                })
        
        return suggestions

    def get_impact_analysis(self, file_path: str) -> Dict[str, Any]:
        """
        Get impact analysis for changing a file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary containing impact analysis
        """
        if file_path not in self.relationships:
            return {}
        
        # Get all files that directly depend on this file
        direct_dependents = self.reverse_dependency_graph.get(file_path, [])
        
        # Get all files that indirectly depend on this file
        indirect_dependents = []
        for direct in direct_dependents:
            related = self.get_related_files(direct)
            indirect_dependents.extend([r for r in related if r not in direct_dependents and r != file_path])
        
        # Remove duplicates
        indirect_dependents = list(set(indirect_dependents))
        
        # Calculate risk level based on number of dependents
        risk_level = "low"
        if len(direct_dependents) > 10 or len(indirect_dependents) > 20:
            risk_level = "high"
        elif len(direct_dependents) > 5 or len(indirect_dependents) > 10:
            risk_level = "medium"
        
        return {
            "risk_level": risk_level,
            "direct_dependents": direct_dependents,
            "direct_dependents_count": len(direct_dependents),
            "indirect_dependents": indirect_dependents,
            "indirect_dependents_count": len(indirect_dependents),
            "total_dependents_count": len(direct_dependents) + len(indirect_dependents)
        }

    def get_context_for_repair(self, file_path: str) -> Dict[str, Any]:
        """
        Get context for repairing a file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary containing repair context
        """
        if file_path not in self.relationships:
            return {}
        
        # Get file info
        info = self.relationships[file_path]
        
        # Get complexity
        complexity = self.get_file_complexity(file_path)
        
        # Get impact analysis
        impact = self.get_impact_analysis(file_path)
        
        # Get related files
        related_files = self.get_related_files(file_path)
        
        return {
            "file_path": file_path,
            "functions": info.get("functions", []),
            "classes": info.get("classes", []),
            "imports": info.get("imports", []),
            "imported_by": info.get("imported_by", []),
            "complexity": complexity,
            "impact": impact,
            "related_files": related_files
        }

    # Added methods for compatibility with tests
    
    def get_imports(self, file_path: str) -> List[str]:
        """
        Get files imported by the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of imported file paths
        """
        if file_path not in self.relationships:
            return []
        return self.relationships[file_path].get("imports", [])
    
    def get_imported_by(self, file_path: str) -> List[str]:
        """
        Get files that import the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of file paths that import this file
        """
        if file_path not in self.relationships:
            return []
        return self.relationships[file_path].get("imported_by", [])
    
    def get_functions(self, file_path: str) -> List[str]:
        """
        Get functions defined in the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of function names
        """
        if file_path not in self.relationships:
            return []
        return self.relationships[file_path].get("functions", [])
    
    def get_classes(self, file_path: str) -> List[str]:
        """
        Get classes defined in the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of class names
        """
        if file_path not in self.relationships:
            return []
        return self.relationships[file_path].get("classes", [])
    
    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Get metadata for the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing file metadata
        """
        if file_path not in self.relationships:
            return {}
        
        # Extract basic file info and add complexity metrics
        return {
            "file_path": file_path,
            "complexity": self.get_file_complexity(file_path),
            "is_module": os.path.basename(file_path) == "__init__.py",
            "size": len(str(self.relationships[file_path]))  # Rough estimate of size
        }
