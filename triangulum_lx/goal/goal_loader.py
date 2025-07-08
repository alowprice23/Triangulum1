#!/usr/bin/env python3
"""
Goal Loader

Loads and manages debugging goals from various sources including YAML files,
JSON configurations, and programmatic definitions.
"""

import logging
import yaml
import json
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class Goal:
    """Represents a debugging goal."""
    id: str
    description: str
    target_file: str
    priority: int = 1
    max_iterations: int = 10
    timeout_seconds: int = 300
    error_message: Optional[str] = None
    expected_outcome: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert goal to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Goal':
        """Create goal from dictionary."""
        return cls(**data)
    
    def validate(self) -> List[str]:
        """Validate the goal and return any errors."""
        errors = []
        
        if not self.id:
            errors.append("Goal ID is required")
        
        if not self.description:
            errors.append("Goal description is required")
        
        if not self.target_file:
            errors.append("Target file is required")
        
        if self.priority < 1:
            errors.append("Priority must be >= 1")
        
        if self.max_iterations < 1:
            errors.append("Max iterations must be >= 1")
        
        if self.timeout_seconds < 1:
            errors.append("Timeout must be >= 1 second")
        
        # Check if target file exists
        if self.target_file and not Path(self.target_file).exists():
            errors.append(f"Target file does not exist: {self.target_file}")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if the goal is valid."""
        return len(self.validate()) == 0


class GoalLoader:
    """Loads and manages debugging goals."""
    
    def __init__(self):
        """Initialize the goal loader."""
        self.goals: Dict[str, Goal] = {}
        self.goal_sources: Dict[str, str] = {}  # goal_id -> source_path
        
        logger.info("Goal Loader initialized")
    
    def load_from_file(self, file_path: str) -> List[Goal]:
        """Load goals from a file (YAML or JSON).
        
        Args:
            file_path: Path to the goal file
            
        Returns:
            List of loaded goals
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Goal file not found: {file_path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif path.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported file format: {path.suffix}")
            
            goals = self._parse_goal_data(data, str(path))
            
            logger.info(f"Loaded {len(goals)} goals from {file_path}")
            return goals
            
        except Exception as e:
            logger.error(f"Error loading goals from {file_path}: {e}")
            raise
    
    def load_from_directory(self, directory_path: str, pattern: str = "*.yaml") -> List[Goal]:
        """Load goals from all matching files in a directory.
        
        Args:
            directory_path: Path to directory containing goal files
            pattern: File pattern to match (default: *.yaml)
            
        Returns:
            List of all loaded goals
        """
        directory = Path(directory_path)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory_path}")
        
        all_goals = []
        goal_files = list(directory.glob(pattern))
        
        for goal_file in goal_files:
            try:
                goals = self.load_from_file(str(goal_file))
                all_goals.extend(goals)
            except Exception as e:
                logger.warning(f"Failed to load goals from {goal_file}: {e}")
        
        logger.info(f"Loaded {len(all_goals)} goals from {len(goal_files)} files in {directory_path}")
        return all_goals
    
    def _parse_goal_data(self, data: Any, source_path: str) -> List[Goal]:
        """Parse goal data from loaded file content.
        
        Args:
            data: Parsed file data
            source_path: Source file path for tracking
            
        Returns:
            List of parsed goals
        """
        goals = []
        
        if isinstance(data, dict):
            # Single goal or goals dictionary
            if 'goals' in data:
                # Multiple goals in 'goals' key
                goal_list = data['goals']
            elif 'id' in data or 'description' in data:
                # Single goal
                goal_list = [data]
            else:
                # Dictionary of goals with IDs as keys
                goal_list = []
                for goal_id, goal_data in data.items():
                    if isinstance(goal_data, dict):
                        goal_data['id'] = goal_id
                        goal_list.append(goal_data)
        elif isinstance(data, list):
            # List of goals
            goal_list = data
        else:
            raise ValueError(f"Invalid goal data format in {source_path}")
        
        for i, goal_data in enumerate(goal_list):
            try:
                goal = self._create_goal_from_data(goal_data, source_path, i)
                goals.append(goal)
                
                # Store in internal registry
                self.goals[goal.id] = goal
                self.goal_sources[goal.id] = source_path
                
            except Exception as e:
                logger.warning(f"Failed to parse goal {i} from {source_path}: {e}")
        
        return goals
    
    def _create_goal_from_data(self, data: Dict[str, Any], source_path: str, index: int) -> Goal:
        """Create a Goal object from parsed data.
        
        Args:
            data: Goal data dictionary
            source_path: Source file path
            index: Goal index in file
            
        Returns:
            Goal object
        """
        # Ensure required fields have defaults
        if 'id' not in data:
            data['id'] = f"goal_{Path(source_path).stem}_{index}"
        
        if 'description' not in data:
            data['description'] = f"Goal from {source_path}"
        
        if 'target_file' not in data:
            raise ValueError("target_file is required for each goal")
        
        # Convert relative paths to absolute paths relative to the goal file
        target_file = data['target_file']
        if not Path(target_file).is_absolute():
            goal_dir = Path(source_path).parent
            data['target_file'] = str(goal_dir / target_file)
        
        # Create goal object
        goal = Goal.from_dict(data)
        
        # Validate the goal
        errors = goal.validate()
        if errors:
            raise ValueError(f"Goal validation failed: {', '.join(errors)}")
        
        return goal
    
    def create_goal(self, id: str, description: str, target_file: str, **kwargs) -> Goal:
        """Create a goal programmatically.
        
        Args:
            id: Goal ID
            description: Goal description
            target_file: Target file path
            **kwargs: Additional goal parameters
            
        Returns:
            Created goal
        """
        goal_data = {
            'id': id,
            'description': description,
            'target_file': target_file,
            **kwargs
        }
        
        goal = Goal.from_dict(goal_data)
        
        # Validate the goal
        errors = goal.validate()
        if errors:
            raise ValueError(f"Goal validation failed: {', '.join(errors)}")
        
        # Store in registry
        self.goals[goal.id] = goal
        self.goal_sources[goal.id] = "programmatic"
        
        logger.info(f"Created goal: {goal.id}")
        return goal
    
    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID.
        
        Args:
            goal_id: Goal identifier
            
        Returns:
            Goal object or None if not found
        """
        return self.goals.get(goal_id)
    
    def list_goals(self, tags: Optional[List[str]] = None, priority_min: Optional[int] = None) -> List[Goal]:
        """List goals with optional filtering.
        
        Args:
            tags: Filter by tags (goals must have at least one matching tag)
            priority_min: Minimum priority level
            
        Returns:
            List of matching goals
        """
        goals = list(self.goals.values())
        
        if tags:
            goals = [g for g in goals if any(tag in g.tags for tag in tags)]
        
        if priority_min is not None:
            goals = [g for g in goals if g.priority >= priority_min]
        
        # Sort by priority (higher first)
        goals.sort(key=lambda g: g.priority, reverse=True)
        
        return goals
    
    def remove_goal(self, goal_id: str) -> bool:
        """Remove a goal from the registry.
        
        Args:
            goal_id: Goal identifier
            
        Returns:
            True if goal was removed, False if not found
        """
        if goal_id in self.goals:
            del self.goals[goal_id]
            if goal_id in self.goal_sources:
                del self.goal_sources[goal_id]
            logger.info(f"Removed goal: {goal_id}")
            return True
        return False
    
    def save_goals_to_file(self, file_path: str, goal_ids: Optional[List[str]] = None) -> None:
        """Save goals to a file.
        
        Args:
            file_path: Output file path
            goal_ids: Optional list of goal IDs to save (default: all goals)
        """
        if goal_ids is None:
            goals_to_save = list(self.goals.values())
        else:
            goals_to_save = [self.goals[gid] for gid in goal_ids if gid in self.goals]
        
        # Convert goals to dictionaries
        goals_data = [goal.to_dict() for goal in goals_to_save]
        
        path = Path(file_path)
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump({'goals': goals_data}, f, default_flow_style=False, indent=2)
                elif path.suffix.lower() == '.json':
                    json.dump({'goals': goals_data}, f, indent=2)
                else:
                    raise ValueError(f"Unsupported file format: {path.suffix}")
            
            logger.info(f"Saved {len(goals_to_save)} goals to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving goals to {file_path}: {e}")
            raise
    
    def validate_all_goals(self) -> Dict[str, List[str]]:
        """Validate all loaded goals.
        
        Returns:
            Dictionary mapping goal IDs to validation errors (empty list if valid)
        """
        validation_results = {}
        
        for goal_id, goal in self.goals.items():
            errors = goal.validate()
            validation_results[goal_id] = errors
        
        return validation_results
    
    def get_goal_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded goals.
        
        Returns:
            Statistics dictionary
        """
        total_goals = len(self.goals)
        
        if total_goals == 0:
            return {
                'total_goals': 0,
                'valid_goals': 0,
                'invalid_goals': 0,
                'priority_distribution': {},
                'tag_distribution': {},
                'sources': []
            }
        
        validation_results = self.validate_all_goals()
        valid_goals = sum(1 for errors in validation_results.values() if not errors)
        invalid_goals = total_goals - valid_goals
        
        # Priority distribution
        priorities = [goal.priority for goal in self.goals.values()]
        priority_dist = {}
        for priority in set(priorities):
            priority_dist[priority] = priorities.count(priority)
        
        # Tag distribution
        all_tags = []
        for goal in self.goals.values():
            all_tags.extend(goal.tags)
        
        tag_dist = {}
        for tag in set(all_tags):
            tag_dist[tag] = all_tags.count(tag)
        
        # Sources
        sources = list(set(self.goal_sources.values()))
        
        return {
            'total_goals': total_goals,
            'valid_goals': valid_goals,
            'invalid_goals': invalid_goals,
            'priority_distribution': priority_dist,
            'tag_distribution': tag_dist,
            'sources': sources
        }
    

    def load_goal(self, goal_id: str) -> Optional[Goal]:
        """Load a specific goal by ID (alias for get_goal).
        
        Args:
            goal_id: Goal identifier
            
        Returns:
            Goal object or None if not found
        """
        return self.get_goal(goal_id)

    def clear_goals(self) -> None:
        """Clear all loaded goals."""
        self.goals.clear()
        self.goal_sources.clear()
        logger.info("Cleared all goals")


# Global loader instance
_loader_instance: Optional[GoalLoader] = None

def get_loader() -> GoalLoader:
    """Get the global goal loader instance.
    
    Returns:
        Global GoalLoader instance
    """
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = GoalLoader()
    return _loader_instance

def load_goals_from_file(file_path: str) -> List[Goal]:
    """Convenience function to load goals from a file.
    
    Args:
        file_path: Path to goal file
        
    Returns:
        List of loaded goals
    """
    loader = get_loader()
    return loader.load_from_file(file_path)

def create_goal(id: str, description: str, target_file: str, **kwargs) -> Goal:
    """Convenience function to create a goal.
    
    Args:
        id: Goal ID
        description: Goal description
        target_file: Target file path
        **kwargs: Additional goal parameters
        
    Returns:
        Created goal
    """
    loader = get_loader()
    return loader.create_goal(id, description, target_file, **kwargs)
