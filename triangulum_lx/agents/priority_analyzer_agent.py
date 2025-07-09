"""
Priority Analyzer Agent

This agent is responsible for analyzing the priority of tasks, bugs, and other issues.
It determines the importance and urgency of tasks, helping the orchestrator make optimal
allocation decisions based on impact analysis, dependency chains, resource requirements,
time criticality, and business value.
"""

import logging
import os
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Set
from enum import Enum
import math

from .base_agent import BaseAgent
from .message import AgentMessage, MessageType, ConfidenceLevel

logger = logging.getLogger(__name__)


class BugSeverity(Enum):
    """Enumeration of bug severity levels."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    INFO = 4


class PriorityAnalyzerAgent(BaseAgent):
    """
    Agent that analyzes and assigns priorities to tasks and issues.
    
    This agent implements sophisticated priority analysis based on:
    - Impact analysis of different bugs and issues
    - Dependency chain evaluation
    - Resource requirement estimation
    - Time criticality assessment
    - Business value consideration
    - Context-aware priority adjustment
    """
    AGENT_TYPE = "priority_analyzer"

    def __init__(
        self,
        agent_id: Optional[str] = None,
        # agent_type: str = "priority_analyzer", # AGENT_TYPE class var will be used
        message_bus: Optional["EnhancedMessageBus"] = None, # Forward reference for type hint
        # subscribed_message_types: Optional[List[MessageType]] = None, # Can be defined in super()
        config: Optional[Dict[str, Any]] = None,
        **kwargs # To catch other base agent params like engine_monitor
    ):
        """
        Initialize the Priority Analyzer Agent.
        
        Args:
            agent_id: Unique identifier for the agent
            message_bus: Message bus for agent communication
            config: Agent configuration dictionary
        """
        super().__init__(
            agent_id=agent_id,
            agent_type=self.AGENT_TYPE, # Use class variable
            message_bus=message_bus,
            subscribed_message_types=[MessageType.TASK_REQUEST, MessageType.QUERY], # Define here
            config=config,
            **kwargs
        )
        
        # self.config is already set by super().__init__
        
        # Priority weights
        self.weights = self.config.get("weights", {
            "severity": 0.35,           # Weight for bug severity
            "bug_count": 0.15,          # Weight for number of bugs
            "dependencies": 0.20,       # Weight for dependencies
            "dependents": 0.15,         # Weight for dependents
            "complexity": 0.05,         # Weight for code complexity
            "business_value": 0.10,     # Weight for business value
        })
        
        # Severity scores
        self.severity_scores = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3,
            "info": 0.1,
        }
        
        # Business value mapping
        self.business_value_mapping = self.config.get("business_value_mapping", {})
        
        # Cache for priority calculations
        self.priority_cache = {}
        
        # History of priority analyses
        self.analysis_history = []
        
        # Initialize priority metrics
        self.metrics = {
            "analyses_performed": 0,
            "files_analyzed": 0,
            "avg_analysis_time": 0,
            "total_analysis_time": 0,
        }
        
        logger.info(f"Priority Analyzer Agent initialized with weights: {self.weights}")

    def _handle_task_request(self, message: AgentMessage) -> None:
        """
        Handle a task request message.
        
        Args:
            message: The task request message
        """
        action = message.content.get("action")
        if action == "analyze_priorities":
            self._handle_priority_analysis(message)
        elif action == "analyze_task_priorities":
            self._handle_task_priority_analysis(message)
        elif action == "analyze_bug_priorities":
            self._handle_bug_priority_analysis(message)
        else:
            self.send_response(
                original_message=message,
                message_type=MessageType.ERROR,
                content={"error": f"Unknown action: {action}"},
            )

    def _handle_query(self, message: AgentMessage) -> None:
        """
        Handle a query message.
        
        Args:
            message: The query message
        """
        query_type = message.content.get("query_type")
        
        if query_type == "get_priority_metrics":
            self.send_response(
                original_message=message,
                message_type=MessageType.QUERY_RESPONSE,
                content={"metrics": self.metrics},
            )
        elif query_type == "get_priority_history":
            limit = message.content.get("limit", 10)
            self.send_response(
                original_message=message,
                message_type=MessageType.QUERY_RESPONSE,
                content={"history": self.analysis_history[-limit:]},
            )
        elif query_type == "get_priority_explanation":
            file_path = message.content.get("file_path")
            analysis_id = message.content.get("analysis_id")
            
            if not file_path:
                self.send_response(
                    original_message=message,
                    message_type=MessageType.ERROR,
                    content={"error": "file_path is required"},
                )
                return
                
            explanation = self._get_priority_explanation(file_path, analysis_id)
            self.send_response(
                original_message=message,
                message_type=MessageType.QUERY_RESPONSE,
                content={"explanation": explanation},
            )
        else:
            self.send_response(
                original_message=message,
                message_type=MessageType.ERROR,
                content={"error": f"Unknown query type: {query_type}"},
            )

    def _handle_priority_analysis(self, message: AgentMessage) -> None:
        """
        Handle a priority analysis request for files in a folder.
        
        Args:
            message: The priority analysis request message
        """
        start_time = time.time()
        content = message.content
        folder_path = content.get("folder_path")
        bugs_by_file = content.get("bugs_by_file", {})
        relationships = content.get("relationships", {})
        context = content.get("context", {})

        if not folder_path:
            self.send_response(
                original_message=message,
                message_type=MessageType.ERROR,
                content={"error": "folder_path is required"},
            )
            return

        try:
            # Analyze priorities
            file_priorities = self.analyze_priorities(
                folder_path, bugs_by_file, relationships, context
            )
            
            # Rank files by priority
            ranked_files = self._rank_files_by_priority(file_priorities)
            
            # Update metrics
            analysis_time = time.time() - start_time
            self._update_metrics(len(file_priorities), analysis_time)
            
            # Generate analysis ID
            analysis_id = f"analysis_{int(time.time())}"
            
            # Store analysis in history
            self.analysis_history.append({
                "id": analysis_id,
                "timestamp": datetime.now().isoformat(),
                "folder_path": folder_path,
                "file_count": len(file_priorities),
                "analysis_time": analysis_time,
                "priorities": file_priorities,
            })
            
            # Send response
            self.send_response(
                original_message=message,
                message_type=MessageType.TASK_RESULT,
                content={
                    "status": "success",
                    "file_priorities": file_priorities,
                    "ranked_files": ranked_files,
                    "analysis_id": analysis_id,
                    "analysis_time": analysis_time,
                    "metrics": {
                        "file_count": len(file_priorities),
                        "bug_count": sum(len(bugs) for bugs in bugs_by_file.values()),
                        "high_priority_count": sum(1 for p in file_priorities.values() if p["priority"] > 0.7),
                    }
                },
                confidence=ConfidenceLevel.HIGH.value
            )
        except Exception as e:
            logger.error(f"Error during priority analysis: {e}")
            self.send_response(
                original_message=message,
                message_type=MessageType.ERROR,
                content={"error": str(e)},
            )

    def _handle_task_priority_analysis(self, message: AgentMessage) -> None:
        """
        Handle a priority analysis request for tasks.
        
        Args:
            message: The task priority analysis request message
        """
        start_time = time.time()
        content = message.content
        tasks = content.get("tasks", [])
        context = content.get("context", {})

        if not tasks:
            self.send_response(
                original_message=message,
                message_type=MessageType.ERROR,
                content={"error": "tasks list is required"},
            )
            return

        try:
            # Analyze task priorities
            task_priorities = self.analyze_task_priorities(tasks, context)
            
            # Rank tasks by priority
            ranked_tasks = sorted(
                task_priorities.items(), 
                key=lambda x: x[1]["priority"], 
                reverse=True
            )
            
            # Update metrics
            analysis_time = time.time() - start_time
            self._update_metrics(len(tasks), analysis_time)
            
            # Send response
            self.send_response(
                original_message=message,
                message_type=MessageType.TASK_RESULT,
                content={
                    "status": "success",
                    "task_priorities": task_priorities,
                    "ranked_tasks": [task_id for task_id, _ in ranked_tasks],
                    "analysis_time": analysis_time,
                },
                confidence=ConfidenceLevel.HIGH.value
            )
        except Exception as e:
            logger.error(f"Error during task priority analysis: {e}")
            self.send_response(
                original_message=message,
                message_type=MessageType.ERROR,
                content={"error": str(e)},
            )

    def _handle_bug_priority_analysis(self, message: AgentMessage) -> None:
        """
        Handle a priority analysis request for bugs.
        
        Args:
            message: The bug priority analysis request message
        """
        start_time = time.time()
        content = message.content
        bugs = content.get("bugs", [])
        context = content.get("context", {})

        if not bugs:
            self.send_response(
                original_message=message,
                message_type=MessageType.ERROR,
                content={"error": "bugs list is required"},
            )
            return

        try:
            # Analyze bug priorities
            bug_priorities = self.analyze_bug_priorities(bugs, context)
            
            # Rank bugs by priority
            ranked_bugs = sorted(
                bug_priorities.items(), 
                key=lambda x: x[1]["priority"], 
                reverse=True
            )
            
            # Update metrics
            analysis_time = time.time() - start_time
            self._update_metrics(len(bugs), analysis_time)
            
            # Send response
            self.send_response(
                original_message=message,
                message_type=MessageType.TASK_RESULT,
                content={
                    "status": "success",
                    "bug_priorities": bug_priorities,
                    "ranked_bugs": [bug_id for bug_id, _ in ranked_bugs],
                    "analysis_time": analysis_time,
                },
                confidence=ConfidenceLevel.HIGH.value
            )
        except Exception as e:
            logger.error(f"Error during bug priority analysis: {e}")
            self.send_response(
                original_message=message,
                message_type=MessageType.ERROR,
                content={"error": str(e)},
            )

    def analyze_priorities(
        self,
        folder_path: str,
        bugs_by_file: Dict[str, List[Dict[str, Any]]],
        relationships: Dict[str, Dict[str, List[str]]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze the priorities of files based on bugs, relationships, and context.
        
        Args:
            folder_path: Path to the folder containing the files
            bugs_by_file: Dictionary mapping file paths to lists of bugs
            relationships: Dictionary mapping file paths to their dependencies and dependents
            context: Optional context information for priority analysis
            
        Returns:
            Dictionary mapping file paths to priority information
        """
        logger.info(f"Analyzing priorities for {len(bugs_by_file)} files in {folder_path}")
        
        # Initialize context if not provided
        context = context or {}
        
        # Get business value mapping from context or use default
        business_value_mapping = context.get("business_value_mapping", self.business_value_mapping)
        
        # Initialize result dictionary
        file_priorities = {}
        
        # Calculate dependency depth for each file
        dependency_depths = self._calculate_dependency_depths(relationships)
        
        # Calculate max values for normalization
        max_bug_count = max([len(bugs) for bugs in bugs_by_file.values()], default=1)
        max_dependencies = max([len(relationships.get(file_path, {}).get("dependencies", [])) 
                              for file_path in bugs_by_file], default=1)
        max_dependents = max([len(relationships.get(file_path, {}).get("dependents", [])) 
                            for file_path in bugs_by_file], default=1)
        max_depth = max(dependency_depths.values(), default=1)
        
        # Process each file
        for file_path, bugs in bugs_by_file.items():
            # Skip if no bugs
            if not bugs:
                file_priorities[file_path] = {
                    "priority": 0.0,
                    "bug_count": 0,
                    "factors": {
                        "severity": 0.0,
                        "bug_count": 0.0,
                        "dependencies": 0.0,
                        "dependents": 0.0,
                        "complexity": 0.0,
                        "business_value": 0.0,
                    },
                    "explanation": "No bugs found in this file."
                }
                continue
            
            # Calculate severity score
            severity_score = self._calculate_severity_score(bugs)
            
            # Calculate bug count score (normalized)
            bug_count = len(bugs)
            bug_count_score = bug_count / max_bug_count
            
            # Calculate dependency scores
            file_relationships = relationships.get(file_path, {})
            dependencies = file_relationships.get("dependencies", [])
            dependents = file_relationships.get("dependents", [])
            
            dependency_score = len(dependencies) / max_dependencies if max_dependencies > 0 else 0
            dependent_score = len(dependents) / max_dependents if max_dependents > 0 else 0
            
            # Adjust dependency score based on depth
            depth = dependency_depths.get(file_path, 0)
            depth_factor = depth / max_depth if max_depth > 0 else 0
            dependency_score = dependency_score * (1 + depth_factor)
            
            # Calculate complexity score
            complexity_score = self._estimate_complexity(file_path, bugs, relationships)
            
            # Calculate business value score
            business_value_score = self._calculate_business_value(file_path, business_value_mapping)
            
            # Calculate weighted priority score
            factors = {
                "severity": severity_score,
                "bug_count": bug_count_score,
                "dependencies": dependency_score,
                "dependents": dependent_score,
                "complexity": complexity_score,
                "business_value": business_value_score,
            }
            
            priority_score = sum(score * self.weights.get(factor, 0) for factor, score in factors.items())
            
            # Apply context-specific adjustments
            priority_score = self._apply_context_adjustments(priority_score, file_path, context)
            
            # Ensure score is between 0 and 1
            priority_score = max(0.0, min(1.0, priority_score))
            
            # Generate explanation
            explanation = self._generate_priority_explanation(
                file_path, bugs, factors, priority_score, context
            )
            
            # Store result
            file_priorities[file_path] = {
                "priority": priority_score,
                "bug_count": bug_count,
                "factors": factors,
                "explanation": explanation
            }
        
        logger.info(f"Priority analysis completed for {len(file_priorities)} files")
        return file_priorities

    def analyze_task_priorities(
        self,
        tasks: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze the priorities of tasks based on their properties and context.
        
        Args:
            tasks: List of task dictionaries
            context: Optional context information for priority analysis
            
        Returns:
            Dictionary mapping task IDs to priority information
        """
        logger.info(f"Analyzing priorities for {len(tasks)} tasks")
        
        # Initialize context if not provided
        context = context or {}
        
        # Initialize result dictionary
        task_priorities = {}
        
        # Process each task
        for task in tasks:
            task_id = task.get("id", str(id(task)))
            
            # Calculate urgency score (deadline-based)
            urgency_score = self._calculate_urgency_score(task)
            
            # Calculate importance score (impact-based)
            importance_score = self._calculate_importance_score(task)
            
            # Calculate effort score (inverse of estimated effort)
            effort_score = self._calculate_effort_score(task)
            
            # Calculate dependency score
            dependency_score = self._calculate_task_dependency_score(task, tasks)
            
            # Calculate business value score
            business_value_score = task.get("business_value", 0.5)
            
            # Calculate weighted priority score
            factors = {
                "urgency": urgency_score,
                "importance": importance_score,
                "effort": effort_score,
                "dependencies": dependency_score,
                "business_value": business_value_score,
            }
            
            # Define weights for task prioritization
            weights = {
                "urgency": 0.3,
                "importance": 0.3,
                "effort": 0.1,
                "dependencies": 0.2,
                "business_value": 0.1,
            }
            
            priority_score = sum(score * weights.get(factor, 0) for factor, score in factors.items())
            
            # Apply context-specific adjustments
            priority_score = self._apply_context_adjustments(priority_score, task_id, context)
            
            # Ensure score is between 0 and 1
            priority_score = max(0.0, min(1.0, priority_score))
            
            # Generate explanation
            explanation = self._generate_task_priority_explanation(
                task, factors, priority_score, context
            )
            
            # Store result
            task_priorities[task_id] = {
                "priority": priority_score,
                "factors": factors,
                "explanation": explanation
            }
        
        logger.info(f"Task priority analysis completed for {len(task_priorities)} tasks")
        return task_priorities

    def analyze_bug_priorities(
        self,
        bugs: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze the priorities of bugs based on their properties and context.
        
        Args:
            bugs: List of bug dictionaries
            context: Optional context information for priority analysis
            
        Returns:
            Dictionary mapping bug IDs to priority information
        """
        logger.info(f"Analyzing priorities for {len(bugs)} bugs")
        
        # Initialize context if not provided
        context = context or {}
        
        # Initialize result dictionary
        bug_priorities = {}
        
        # Process each bug
        for bug in bugs:
            bug_id = bug.get("id", str(id(bug)))
            
            # Calculate severity score
            severity = bug.get("severity", "medium").lower()
            severity_score = self.severity_scores.get(severity, 0.5)
            
            # Calculate impact score
            impact_score = self._calculate_bug_impact_score(bug)
            
            # Calculate fix complexity score (inverse of complexity)
            complexity_score = 1.0 - self._calculate_bug_complexity_score(bug)
            
            # Calculate age score (older bugs get higher priority)
            age_score = self._calculate_bug_age_score(bug)
            
            # Calculate frequency score (more frequent bugs get higher priority)
            frequency_score = self._calculate_bug_frequency_score(bug)
            
            # Calculate weighted priority score
            factors = {
                "severity": severity_score,
                "impact": impact_score,
                "complexity": complexity_score,
                "age": age_score,
                "frequency": frequency_score,
            }
            
            # Define weights for bug prioritization
            weights = {
                "severity": 0.4,
                "impact": 0.3,
                "complexity": 0.1,
                "age": 0.1,
                "frequency": 0.1,
            }
            
            priority_score = sum(score * weights.get(factor, 0) for factor, score in factors.items())
            
            # Apply context-specific adjustments
            priority_score = self._apply_context_adjustments(priority_score, bug_id, context)
            
            # Ensure score is between 0 and 1
            priority_score = max(0.0, min(1.0, priority_score))
            
            # Generate explanation
            explanation = self._generate_bug_priority_explanation(
                bug, factors, priority_score, context
            )
            
            # Store result
            bug_priorities[bug_id] = {
                "priority": priority_score,
                "factors": factors,
                "explanation": explanation
            }
        
        logger.info(f"Bug priority analysis completed for {len(bug_priorities)} bugs")
        return bug_priorities

    def _calculate_severity_score(self, bugs: List[Dict[str, Any]]) -> float:
        """
        Calculate a severity score based on the bugs in a file.
        
        Args:
            bugs: List of bug dictionaries
            
        Returns:
            Severity score between 0 and 1
        """
        if not bugs:
            return 0.0
        
        # Map severity strings to scores
        severity_scores = []
        for bug in bugs:
            severity = bug.get("severity", "medium").lower()
            score = self.severity_scores.get(severity, 0.5)
            severity_scores.append(score)
        
        # Use a weighted average that emphasizes higher severities
        if severity_scores:
            # Sort scores in descending order
            severity_scores.sort(reverse=True)
            
            # Apply exponential decay to give higher weight to more severe bugs
            weighted_sum = sum(score * math.exp(-0.5 * i) for i, score in enumerate(severity_scores))
            weight_sum = sum(math.exp(-0.5 * i) for i in range(len(severity_scores)))
            
            return weighted_sum / weight_sum
        
        return 0.0

    def _calculate_dependency_depths(self, relationships: Dict[str, Any]) -> Dict[str, int]:
        """
        Calculate the maximum dependency depth for each file.
        
        Args:
            relationships: Dictionary representing the dependency graph
            
        Returns:
            Dictionary mapping file paths to their maximum dependency depth
        """
        depths = {}
        visited = set()
        
        # Extract nodes and edges from relationships data
        nodes = relationships.get("nodes", {})
        edges = relationships.get("edges", [])
        
        # Build a dependency map
        dependency_map = {}
        for file_path in nodes:
            dependency_map[file_path] = []
        
        for edge in edges:
            source = edge.get("source", "")
            target = edge.get("target", "")
            if source and target:
                if source not in dependency_map:
                    dependency_map[source] = []
                dependency_map[source].append(target)
        
        def calculate_depth(file_path: str, current_depth: int = 0) -> int:
            if file_path in visited:
                return 0  # Avoid cycles
            
            visited.add(file_path)
            
            if file_path not in dependency_map:
                return current_depth
            
            dependencies = dependency_map[file_path]
            if not dependencies:
                return current_depth
            
            max_depth = current_depth
            for dep in dependencies:
                depth = calculate_depth(dep, current_depth + 1)
                max_depth = max(max_depth, depth)
            
            visited.remove(file_path)
            return max_depth
        
        for file_path in dependency_map:
            depths[file_path] = calculate_depth(file_path)
        
        return depths

    def _estimate_complexity(
        self, 
        file_path: str, 
        bugs: List[Dict[str, Any]], 
        relationships: Dict[str, Dict[str, List[str]]]
    ) -> float:
        """
        Estimate the complexity of a file based on bugs and relationships.
        
        Args:
            file_path: Path to the file
            bugs: List of bugs in the file
            relationships: Dictionary mapping file paths to their dependencies and dependents
            
        Returns:
            Complexity score between 0 and 1
        """
        # Start with a base complexity
        complexity = 0.3
        
        # Adjust based on file extension (proxy for language complexity)
        ext = os.path.splitext(file_path)[1].lower()
        language_complexity = {
            ".py": 0.4,
            ".js": 0.5,
            ".ts": 0.6,
            ".java": 0.7,
            ".cpp": 0.8,
            ".c": 0.7,
            ".go": 0.5,
            ".rs": 0.7,
            ".php": 0.6,
            ".rb": 0.5,
        }
        complexity += language_complexity.get(ext, 0.5)
        
        # Adjust based on relationships
        file_relationships = relationships.get(file_path, {})
        dependencies = file_relationships.get("dependencies", [])
        dependents = file_relationships.get("dependents", [])
        
        # More relationships = more complexity
        relationship_factor = min(1.0, (len(dependencies) + len(dependents)) / 20)
        complexity += relationship_factor * 0.2
        
        # Adjust based on bug types (certain bug types indicate complexity)
        complex_bug_types = {"race_condition", "memory_leak", "concurrency", "deadlock"}
        complex_bug_count = sum(1 for bug in bugs if bug.get("type", "").lower() in complex_bug_types)
        complexity += min(0.3, complex_bug_count * 0.1)
        
        # Normalize to 0-1 range
        return min(1.0, complexity)

    def _calculate_business_value(
        self, 
        file_path: str, 
        business_value_mapping: Dict[str, float]
    ) -> float:
        """
        Calculate the business value of a file based on mapping.
        
        Args:
            file_path: Path to the file
            business_value_mapping: Dictionary mapping file patterns to business value scores
            
        Returns:
            Business value score between 0 and 1
        """
        # Default business value
        business_value = 0.5
        
        # Check for matches in the mapping
        for pattern, value in business_value_mapping.items():
            if pattern in file_path:
                business_value = max(business_value, value)
        
        return business_value

    def _apply_context_adjustments(
        self, 
        score: float, 
        identifier: str, 
        context: Dict[str, Any]
    ) -> float:
        """
        Apply context-specific adjustments to the priority score.
        
        Args:
            score: The initial priority score
            identifier: The identifier (file path, task ID, bug ID)
            context: Context information for adjustments
            
        Returns:
            Adjusted priority score
        """
        # Apply manual priority overrides if specified
        overrides = context.get("priority_overrides", {})
        if identifier in overrides:
            return overrides[identifier]
        
        # Apply priority boosts for specific patterns
        boosts = context.get("priority_boosts", {})
        for pattern, boost in boosts.items():
            if pattern in identifier:
                score += boost
        
        # Apply time-based adjustments
        if "deadline" in context:
            try:
                deadline = datetime.fromisoformat(context["deadline"])
                now = datetime.now()
                days_remaining = (deadline - now).days
                
                # Increase priority as deadline approaches
                if days_remaining <= 0:
                    # Past deadline, maximum priority
                    score += 0.3
                elif days_remaining <= 3:
                    # Near deadline, high priority boost
                    score += 0.2
                elif days_remaining <= 7:
                    # Approaching deadline, medium priority boost
                    score += 0.1
            except (ValueError, TypeError):
                # Invalid deadline format, ignore
                pass
        
        # Apply project phase adjustments
        if "project_phase" in context:
            phase = context["project_phase"]
            if phase == "release":
                # Release phase, boost priority
                score += 0.15
            elif phase == "testing":
                # Testing phase, medium boost
                score += 0.1
            elif phase == "development":
                # Development phase, small boost
                score += 0.05
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
    
    def _rank_files_by_priority(self, file_priorities: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Rank files by their priority scores.
        
        Args:
            file_priorities: Dictionary mapping file paths to priority information
            
        Returns:
            List of file paths sorted by priority (highest first)
        """
        return sorted(
            file_priorities.keys(),
            key=lambda file_path: file_priorities[file_path]["priority"],
            reverse=True
        )
    
    def _update_metrics(self, file_count: int, analysis_time: float) -> None:
        """
        Update the priority analysis metrics.
        
        Args:
            file_count: Number of files analyzed
            analysis_time: Time taken for analysis
        """
        self.metrics["analyses_performed"] += 1
        self.metrics["files_analyzed"] += file_count
        self.metrics["total_analysis_time"] += analysis_time
        self.metrics["avg_analysis_time"] = (
            self.metrics["total_analysis_time"] / self.metrics["analyses_performed"]
        )
    
    def _get_priority_explanation(self, file_path: str, analysis_id: Optional[str] = None) -> str:
        """
        Get a detailed explanation of the priority calculation for a file.
        
        Args:
            file_path: Path to the file
            analysis_id: Optional ID of a specific analysis
            
        Returns:
            Explanation string
        """
        # Find the analysis
        if analysis_id:
            analysis = next(
                (a for a in self.analysis_history if a["id"] == analysis_id),
                None
            )
        else:
            analysis = self.analysis_history[-1] if self.analysis_history else None
        
        if not analysis or file_path not in analysis["priorities"]:
            return f"No priority information found for {file_path}"
        
        priority_info = analysis["priorities"][file_path]
        return priority_info.get("explanation", "No explanation available")
    
    def _generate_priority_explanation(
        self,
        file_path: str,
        bugs: List[Dict[str, Any]],
        factors: Dict[str, float],
        priority_score: float,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate a detailed explanation of the priority calculation.
        
        Args:
            file_path: Path to the file
            bugs: List of bugs in the file
            factors: Dictionary of priority factors
            priority_score: Final priority score
            context: Context information
            
        Returns:
            Explanation string
        """
        explanation = [f"Priority score for {os.path.basename(file_path)}: {priority_score:.2f}"]
        
        # Add factor explanations
        explanation.append("\nFactors contributing to this score:")
        for factor, score in factors.items():
            weight = self.weights.get(factor, 0)
            contribution = score * weight
            explanation.append(f"- {factor}: {score:.2f} × weight {weight:.2f} = {contribution:.2f}")
        
        # Add bug information
        if bugs:
            explanation.append(f"\nContains {len(bugs)} bugs:")
            for i, bug in enumerate(bugs[:3]):  # Show only top 3 bugs
                severity = bug.get("severity", "unknown")
                bug_type = bug.get("type", "unknown")
                explanation.append(f"- Bug {i+1}: {severity} severity, type: {bug_type}")
            
            if len(bugs) > 3:
                explanation.append(f"- ... and {len(bugs) - 3} more")
        
        # Add context-specific explanations
        if context:
            explanation.append("\nContext adjustments:")
            if "deadline" in context:
                explanation.append(f"- Deadline: {context['deadline']}")
            if "project_phase" in context:
                explanation.append(f"- Project phase: {context['project_phase']}")
        
        return "\n".join(explanation)
    
    def _generate_task_priority_explanation(
        self,
        task: Dict[str, Any],
        factors: Dict[str, float],
        priority_score: float,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate a detailed explanation of the task priority calculation.
        
        Args:
            task: Task dictionary
            factors: Dictionary of priority factors
            priority_score: Final priority score
            context: Context information
            
        Returns:
            Explanation string
        """
        task_id = task.get("id", "unknown")
        task_name = task.get("name", "Unnamed task")
        
        explanation = [f"Priority score for task '{task_name}' ({task_id}): {priority_score:.2f}"]
        
        # Add factor explanations
        explanation.append("\nFactors contributing to this score:")
        for factor, score in factors.items():
            weight = 0.2  # Default weight
            if factor == "urgency" or factor == "importance":
                weight = 0.3
            elif factor == "effort":
                weight = 0.1
            contribution = score * weight
            explanation.append(f"- {factor}: {score:.2f} × weight {weight:.2f} = {contribution:.2f}")
        
        # Add task details
        explanation.append("\nTask details:")
        if "deadline" in task:
            explanation.append(f"- Deadline: {task['deadline']}")
        if "estimated_effort" in task:
            explanation.append(f"- Estimated effort: {task['estimated_effort']}")
        if "dependencies" in task:
            explanation.append(f"- Dependencies: {len(task['dependencies'])}")
        
        return "\n".join(explanation)
    
    def _generate_bug_priority_explanation(
        self,
        bug: Dict[str, Any],
        factors: Dict[str, float],
        priority_score: float,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate a detailed explanation of the bug priority calculation.
        
        Args:
            bug: Bug dictionary
            factors: Dictionary of priority factors
            priority_score: Final priority score
            context: Context information
            
        Returns:
            Explanation string
        """
        bug_id = bug.get("id", "unknown")
        bug_type = bug.get("type", "unknown")
        
        explanation = [f"Priority score for bug '{bug_type}' ({bug_id}): {priority_score:.2f}"]
        
        # Add factor explanations
        explanation.append("\nFactors contributing to this score:")
        for factor, score in factors.items():
            weight = 0.1  # Default weight
            if factor == "severity":
                weight = 0.4
            elif factor == "impact":
                weight = 0.3
            contribution = score * weight
            explanation.append(f"- {factor}: {score:.2f} × weight {weight:.2f} = {contribution:.2f}")
        
        # Add bug details
        explanation.append("\nBug details:")
        if "severity" in bug:
            explanation.append(f"- Severity: {bug['severity']}")
        if "reported_date" in bug:
            explanation.append(f"- Reported: {bug['reported_date']}")
        if "frequency" in bug:
            explanation.append(f"- Frequency: {bug['frequency']}")
        
        return "\n".join(explanation)
    
    def _calculate_urgency_score(self, task: Dict[str, Any]) -> float:
        """
        Calculate the urgency score for a task based on deadline.
        
        Args:
            task: Task dictionary
            
        Returns:
            Urgency score between 0 and 1
        """
        if "deadline" not in task:
            return 0.5  # Default urgency
        
        try:
            deadline = datetime.fromisoformat(task["deadline"])
            now = datetime.now()
            days_remaining = (deadline - now).days
            
            if days_remaining <= 0:
                return 1.0  # Maximum urgency
            elif days_remaining <= 1:
                return 0.9
            elif days_remaining <= 3:
                return 0.8
            elif days_remaining <= 7:
                return 0.7
            elif days_remaining <= 14:
                return 0.6
            elif days_remaining <= 30:
                return 0.4
            else:
                return 0.2
        except (ValueError, TypeError):
            return 0.5  # Default urgency for invalid deadline
    
    def _calculate_importance_score(self, task: Dict[str, Any]) -> float:
        """
        Calculate the importance score for a task based on impact.
        
        Args:
            task: Task dictionary
            
        Returns:
            Importance score between 0 and 1
        """
        # Use explicit importance if provided
        if "importance" in task:
            importance = task["importance"]
            if isinstance(importance, (int, float)):
                return min(1.0, max(0.0, float(importance)))
            elif isinstance(importance, str):
                importance_map = {
                    "critical": 1.0,
                    "high": 0.8,
                    "medium": 0.5,
                    "low": 0.3,
                    "trivial": 0.1
                }
                return importance_map.get(importance.lower(), 0.5)
        
        # Calculate based on impact
        impact = task.get("impact", "medium").lower()
        impact_map = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3,
            "trivial": 0.1
        }
        return impact_map.get(impact, 0.5)
    
    def _calculate_effort_score(self, task: Dict[str, Any]) -> float:
        """
        Calculate the effort score for a task (inverse of estimated effort).
        
        Args:
            task: Task dictionary
            
        Returns:
            Effort score between 0 and 1
        """
        if "estimated_effort" not in task:
            return 0.5  # Default effort score
        
        effort = task["estimated_effort"]
        if isinstance(effort, (int, float)):
            # Normalize effort (0-10 scale)
            normalized_effort = min(10, max(0, effort)) / 10
            # Inverse (lower effort = higher score)
            return 1.0 - normalized_effort
        elif isinstance(effort, str):
            effort_map = {
                "trivial": 0.9,
                "easy": 0.7,
                "medium": 0.5,
                "hard": 0.3,
                "very_hard": 0.1
            }
            return effort_map.get(effort.lower(), 0.5)
        
        return 0.5  # Default effort score
    
    def _calculate_task_dependency_score(
        self, 
        task: Dict[str, Any],
        all_tasks: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate the dependency score for a task.
        
        Args:
            task: Task dictionary
            all_tasks: List of all tasks
            
        Returns:
            Dependency score between 0 and 1
        """
        if "dependencies" not in task:
            return 0.5  # Default dependency score
        
        dependencies = task["dependencies"]
        if not dependencies:
            return 0.8  # No dependencies = high score
        
        # Count completed dependencies
        task_id_map = {t.get("id"): t for t in all_tasks if "id" in t}
        completed_count = sum(
            1 for dep_id in dependencies 
            if dep_id in task_id_map and task_id_map[dep_id].get("status") == "completed"
        )
        
        # Calculate completion ratio
        completion_ratio = completed_count / len(dependencies)
        
        # Higher completion ratio = higher score
        return 0.2 + (completion_ratio * 0.8)
    
    def _calculate_bug_impact_score(self, bug: Dict[str, Any]) -> float:
        """
        Calculate the impact score for a bug.
        
        Args:
            bug: Bug dictionary
            
        Returns:
            Impact score between 0 and 1
        """
        # Use explicit impact if provided
        if "impact" in bug:
            impact = bug["impact"]
            if isinstance(impact, (int, float)):
                return min(1.0, max(0.0, float(impact)))
            elif isinstance(impact, str):
                impact_map = {
                    "critical": 1.0,
                    "high": 0.8,
                    "medium": 0.5,
                    "low": 0.3,
                    "trivial": 0.1
                }
                return impact_map.get(impact.lower(), 0.5)
        
        # Calculate based on affected users or components
        affected_users = bug.get("affected_users", 0)
        if affected_users > 0:
            # Normalize affected users (0-1000 scale)
            return min(1.0, affected_users / 1000)
        
        # Calculate based on affected components
        affected_components = bug.get("affected_components", [])
        if affected_components:
            # More affected components = higher impact
            return min(1.0, len(affected_components) / 5)
        
        return 0.5  # Default impact score
    
    def _calculate_bug_complexity_score(self, bug: Dict[str, Any]) -> float:
        """
        Calculate the complexity score for a bug.
        
        Args:
            bug: Bug dictionary
            
        Returns:
            Complexity score between 0 and 1
        """
        # Use explicit complexity if provided
        if "complexity" in bug:
            complexity = bug["complexity"]
            if isinstance(complexity, (int, float)):
                return min(1.0, max(0.0, float(complexity)))
            elif isinstance(complexity, str):
                complexity_map = {
                    "trivial": 0.1,
                    "easy": 0.3,
                    "medium": 0.5,
                    "hard": 0.7,
                    "very_hard": 0.9
                }
                return complexity_map.get(complexity.lower(), 0.5)
        
        # Calculate based on bug type
        bug_type = bug.get("type", "").lower()
        complex_types = {
            "race_condition": 0.9,
            "memory_leak": 0.8,
            "concurrency": 0.8,
            "deadlock": 0.8,
            "security": 0.7,
            "performance": 0.6,
            "logic": 0.5,
            "ui": 0.3,
            "typo": 0.1
        }
        return complex_types.get(bug_type, 0.5)
    
    def _calculate_bug_age_score(self, bug: Dict[str, Any]) -> float:
        """
        Calculate the age score for a bug (older bugs get higher priority).
        
        Args:
            bug: Bug dictionary
            
        Returns:
            Age score between 0 and 1
        """
        if "reported_date" not in bug:
            return 0.5  # Default age score
        
        try:
            reported_date = datetime.fromisoformat(bug["reported_date"])
            now = datetime.now()
            days_old = (now - reported_date).days
            
            # Normalize age (0-180 days scale)
            return min(1.0, days_old / 180)
        except (ValueError, TypeError):
            return 0.5  # Default age score for invalid date
    
    def _calculate_bug_frequency_score(self, bug: Dict[str, Any]) -> float:
        """
        Calculate the frequency score for a bug.
        
        Args:
            bug: Bug dictionary
            
        Returns:
            Frequency score between 0 and 1
        """
        # Use explicit frequency if provided
        if "frequency" in bug:
            frequency = bug["frequency"]
            if isinstance(frequency, (int, float)):
                # Normalize frequency (0-100 scale)
                return min(1.0, frequency / 100)
            elif isinstance(frequency, str):
                frequency_map = {
                    "always": 1.0,
                    "often": 0.8,
                    "sometimes": 0.5,
                    "rarely": 0.3,
                    "once": 0.1
                }
                return frequency_map.get(frequency.lower(), 0.5)
        
        # Use occurrence count if provided
        if "occurrences" in bug:
            occurrences = bug["occurrences"]
            if isinstance(occurrences, (int, float)):
                # Normalize occurrences (0-50 scale)
                return min(1.0, occurrences / 50)
        
        return 0.5  # Default frequency score
