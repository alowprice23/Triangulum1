"""
Relationship Analyst Agent - Analyzes code relationships to provide context.

This agent is responsible for analyzing the relationships between code files,
such as imports, function calls, and other dependencies, to provide context
for other agents.
"""

import os
import time
import logging
import json
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime

from .base_agent import BaseAgent
from .message import AgentMessage, MessageType
from .message_bus import MessageBus
from ..tooling.dependency_graph import DependencyGraphBuilder, DependencyAnalyzer
from ..tooling.graph_models import DependencyGraph, FileNode, DependencyType, DependencyMetadata
from ..tooling.code_relationship_analyzer import CodeRelationshipAnalyzer

logger = logging.getLogger(__name__)

class RelationshipAnalystAgent(BaseAgent):
    """
    Agent that analyzes the relationships between code files to provide context for other agents.
    
    The RelationshipAnalystAgent discovers, tracks, and reports on the complex
    relationships between files in a codebase. It creates a comprehensive dependency
    graph that other agents use to understand the impact of changes and identify related
    files for repair. It provides advanced features including:
    
    - Static analysis of code relationships
    - Runtime relationship discovery via execution tracing
    - Temporal relationship tracking to detect changes over time
    - Visualization of complex relationships
    - Integration with the code relationship analyzer
    """
    
    def __init__(self, 
                 agent_id: str = "relationship_analyst",
                 name: str = "Relationship Analyst",
                 cache_dir: Optional[str] = None,
                 message_bus: Optional[MessageBus] = None):
        """
        Initialize the RelationshipAnalystAgent.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Display name for the agent
            cache_dir: Directory for caching analysis results
            message_bus: MessageBus for communication with other agents
        """
        super().__init__(agent_id, name, message_bus)
        self.name = name  # Ensure name is set for report generation
        
        # Analysis components
        self.graph = None
        self.analyzer = None
        
        # Historical tracking
        self.historical_graphs = []
        self.last_analysis_time = None
        self.execution_traces = []
        
        # Cache directory
        self.cache_dir = cache_dir
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
            
        # Code relationship analyzer integration
        self.relationship_analyzer = CodeRelationshipAnalyzer()
        
        # Visualization settings
        self.visualization_dir = os.path.join(cache_dir, "visualizations") if cache_dir else None
        if self.visualization_dir:
            os.makedirs(self.visualization_dir, exist_ok=True)
            
    def analyze_codebase(
        self,
        root_dir: str,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        incremental: bool = True,
        perform_static_analysis: bool = True,
        analyze_runtime_traces: bool = False,
        save_report: bool = True,
        report_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze the codebase to determine relationships between files.
        
        Args:
            root_dir: Root directory of the codebase
            include_patterns: List of glob patterns to include
            exclude_patterns: List of glob patterns to exclude
            incremental: Whether to perform incremental analysis
            perform_static_analysis: Whether to perform static analysis
            analyze_runtime_traces: Whether to analyze runtime traces
            save_report: Whether to save the analysis report
            report_path: Path to save the analysis report
            
        Returns:
            Dictionary with analysis summary
        """
        logger.info(f"Analyzing codebase at {root_dir}...")
        
        # Set up dependency graph builder
        builder = DependencyGraphBuilder(cache_dir=self.cache_dir)
        
        # Store the previous graph for incremental analysis and historical tracking
        previous_graph = self.graph
        
        # Perform analysis
        if incremental and previous_graph:
            # Incremental analysis
            self.graph = builder.build_graph(
                root_dir, 
                include_patterns=include_patterns, 
                exclude_patterns=exclude_patterns,
                previous_graph=previous_graph, 
                incremental=True
            )
        else:
            # Full analysis
            self.graph = builder.build_graph(
                root_dir, 
                include_patterns=include_patterns, 
                exclude_patterns=exclude_patterns,
                incremental=False
            )
            
        # Save the previous graph for historical tracking
        if previous_graph:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.historical_graphs.append((timestamp, previous_graph))
            
            # Keep only the last 10 historical graphs
            if len(self.historical_graphs) > 10:
                self.historical_graphs.pop(0)
                
        # Update analysis time
        self.last_analysis_time = time.time()
                
        # Enhance with static analysis if requested
        if perform_static_analysis:
            self._enhance_with_static_analysis(root_dir)
            
        # Incorporate runtime traces if requested
        if analyze_runtime_traces and self.execution_traces:
            self._incorporate_runtime_traces()
            
        # Create an analyzer for the graph
        self.analyzer = DependencyAnalyzer(self.graph)
        
        # Return a summary
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary = {
            "files_analyzed": len(self.graph),
            "dependencies_found": len(list(self.graph.edges())),
            "cycles_detected": len(self.analyzer.find_cycles()),
            "languages_detected": self._count_languages(),
            "analysis_timestamp": timestamp,
            "temporal_snapshots": len(self.historical_graphs),
            "runtime_traces_incorporated": analyze_runtime_traces and bool(self.execution_traces),
            "static_analysis_performed": perform_static_analysis
        }
        
        # Save report if requested
        if save_report:
            report_path = report_path or os.path.join(self.cache_dir or "", f"relationship_report_{timestamp}.json")
            self._save_report(report_path, summary)
            
        return summary
    
    def get_most_central_files(self, n: int = 10, metric: str = "pagerank") -> List[Tuple[str, float]]:
        """
        Get the most central files in the codebase based on a centrality metric.
        
        Args:
            n: Number of files to return
            metric: Centrality metric to use (pagerank, betweenness, degree)
            
        Returns:
            List of (file_path, centrality_score) tuples
        """
        if not self.analyzer:
            raise ValueError("No analysis has been performed yet. Call analyze_codebase first.")
        
        return self.analyzer.get_most_central_files(n=n, metric=metric)
    
    def find_cycles(self) -> List[List[str]]:
        """
        Find cycles in the dependency graph.
        
        Returns:
            List of cycles (each cycle is a list of file paths)
        """
        if not self.analyzer:
            raise ValueError("No analysis has been performed yet. Call analyze_codebase first.")
        
        return self.analyzer.find_cycles()
    
    def get_file_dependents(self, file_path: str, transitive: bool = False) -> Set[str]:
        """
        Get files that depend on the specified file.
        
        Args:
            file_path: Path to the file
            transitive: Whether to include transitive dependents
            
        Returns:
            Set of file paths that depend on the specified file
        """
        if not self.graph:
            raise ValueError("No analysis has been performed yet. Call analyze_codebase first.")
        
        if transitive:
            return self.graph.transitive_dependents(file_path)
        else:
            incoming = self.graph.get_incoming_edges(file_path)
            return {edge.source for edge in incoming}
    
    def get_file_dependencies(self, file_path: str, transitive: bool = False) -> Set[str]:
        """
        Get files that the specified file depends on.
        
        Args:
            file_path: Path to the file
            transitive: Whether to include transitive dependencies
            
        Returns:
            Set of file paths that the specified file depends on
        """
        if not self.graph:
            raise ValueError("No analysis has been performed yet. Call analyze_codebase first.")
        
        if transitive:
            return self.graph.transitive_dependencies(file_path)
        else:
            outgoing = self.graph.get_outgoing_edges(file_path)
            return {edge.target for edge in outgoing}
    
    def calculate_impact_boundary(self, files: Optional[List[str]] = None, max_depth: int = 2) -> Dict[str, Set[str]]:
        """
        Calculate the impact boundary for a set of files.
        
        The impact boundary is the set of files that might be affected by changes to the specified files,
        up to a certain depth in the dependency graph.
        
        Args:
            files: List of file paths to calculate the impact boundary for
            max_depth: Maximum depth to search in the dependency graph
            
        Returns:
            Dictionary mapping each file to its impact boundary
        """
        if not self.analyzer or not self.graph:
            raise ValueError("No analysis has been performed yet. Call analyze_codebase first.")
        
        # If no files specified, use all files in the graph
        if files is None:
            files = list(self.graph)
            
        impact_boundaries = {}
        for file_path in files:
            impact_boundary = set()
            current_level = {file_path}
            
            # BFS to find the impact boundary
            for depth in range(max_depth):
                next_level = set()
                for current_file in current_level:
                    if current_file in self.graph:
                        dependents = {edge.source for edge in self.graph.get_incoming_edges(current_file)}
                        next_level.update(dependents)
                
                impact_boundary.update(next_level)
                current_level = next_level
                
            impact_boundaries[file_path] = impact_boundary
            
        return impact_boundaries
    
    def find_all_paths(self, source: str, target: str, max_depth: int = 10) -> List[List[str]]:
        """
        Find all paths between two files in the dependency graph.
        
        Args:
            source: Source file path
            target: Target file path
            max_depth: Maximum depth to search
            
        Returns:
            List of paths (each path is a list of file paths)
        """
        if not self.graph:
            raise ValueError("No analysis has been performed yet. Call analyze_codebase first.")
        
        # Simple BFS to find all paths
        paths = []
        queue = [[source]]
        
        while queue:
            path = queue.pop(0)
            current = path[-1]
            
            # Found a path to the target
            if current == target:
                paths.append(path)
                continue
                
            # Max depth reached
            if len(path) >= max_depth:
                continue
                
            # Add all neighbors to the queue
            if current in self.graph:
                for edge in self.graph.get_outgoing_edges(current):
                    if edge.target not in path:  # Avoid cycles
                        queue.append(path + [edge.target])
                        
        return paths
    
    def predict_impact(self, modified_files: List[str]) -> Set[str]:
        """
        Predict the impact of modifying a set of files.
        
        Args:
            modified_files: List of file paths that will be modified
            
        Returns:
            Set of file paths that might be impacted by the modifications
        """
        if not self.graph:
            raise ValueError("No analysis has been performed yet. Call analyze_codebase first.")
        
        impacted = set()
        for file_path in modified_files:
            dependents = self.graph.transitive_dependents(file_path)
            impacted.update(dependents)
            
        return impacted
    
    def _count_languages(self) -> Dict[str, int]:
        """
        Count the number of files for each language in the codebase.
        
        Returns:
            Dictionary mapping language to number of files
        """
        languages = defaultdict(int)
        
        if not self.graph:
            return dict(languages)
            
        for node in self.graph.nodes():
            file_path = node.path if isinstance(node, FileNode) else str(node)
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.py':
                languages['PYTHON'] += 1
            elif ext in ('.js', '.jsx', '.ts', '.tsx'):
                languages['JAVASCRIPT'] += 1
            elif ext in ('.java', '.kt'):
                languages['JAVA'] += 1
            elif ext in ('.c', '.cpp', '.cc', '.h', '.hpp'):
                languages['C/C++'] += 1
            elif ext in ('.go'):
                languages['GO'] += 1
            elif ext in ('.rb'):
                languages['RUBY'] += 1
            elif ext in ('.php'):
                languages['PHP'] += 1
            elif ext in ('.rs'):
                languages['RUST'] += 1
            elif ext in ('.swift'):
                languages['SWIFT'] += 1
            elif ext in ('.scala'):
                languages['SCALA'] += 1
            else:
                languages['OTHER'] += 1
                
        return dict(languages)
    
    def _enhance_with_static_analysis(self, root_dir: str) -> None:
        """
        Enhance the dependency graph with additional relationships from static analysis.
        
        This method performs advanced static analysis to discover relationships that
        might not be apparent from simple import analysis, such as inheritance,
        composition, function calls, etc.
        
        Args:
            root_dir: Root directory of the codebase
        """
        if not self.graph:
            logger.warning("Cannot enhance with static analysis: no graph available")
            return
            
        logger.info("Enhancing dependency graph with static analysis...")
        
        try:
            # Extract file paths from the graph nodes - properly handle FileNode objects
            file_paths = []
            for node in self.graph.nodes():
                if isinstance(node, FileNode):
                    # It's a FileNode object, extract the file path
                    file_paths.append(node.path)
                elif hasattr(node, 'path'):  # Another type with path attribute
                    file_paths.append(node.path)
                elif isinstance(node, str):  # It's already a string path
                    file_paths.append(node)
                else:
                    # Log what type of node we encountered for debugging
                    logger.warning(f"Unhandled node type: {type(node).__name__} - {node}")
            
            if not file_paths:
                logger.warning("No valid file paths found in graph nodes")
                return
                
            # Print first few paths for debugging
            logger.info(f"Found {len(file_paths)} file paths for analysis")
            for i, path in enumerate(file_paths[:5]):
                logger.info(f"Sample path {i+1}: {path}")
                
            # Use the code relationship analyzer to find additional relationships
            additional_relationships = self.relationship_analyzer.analyze_code_relationships(
                file_paths=file_paths,
                base_dir=root_dir
            )
            
            # Add direct import relationships to the graph
            dependencies_added = 0
            for source_file, info in additional_relationships.items():
                for import_file in info.get('imports', []):
                    # Create a metadata object for the relationship
                    metadata = DependencyMetadata(
                        dependency_type=DependencyType.IMPORT
                    )
                    
                    # Add the edge to the graph
                    if source_file in self.graph and import_file in self.graph:
                        self.graph.add_edge(source_file, import_file, metadata)
                        dependencies_added += 1
            
            # Add function call relationships to the graph
            for source_file, info in additional_relationships.items():
                function_calls = info.get('function_calls', {})
                for function_name, count in function_calls.items():
                    # Check if we know which file this function is defined in
                    if function_name in self.relationship_analyzer.function_map:
                        target_file = self.relationship_analyzer.function_map[function_name]
                        if target_file != source_file:  # Avoid self-dependencies
                            # Create a metadata object for the relationship
                            metadata = DependencyMetadata(
                                dependency_type=DependencyType.FUNCTION_CALL
                            )
                            
                            # Add the edge to the graph
                            if source_file in self.graph and target_file in self.graph:
                                self.graph.add_edge(source_file, target_file, metadata)
                                dependencies_added += 1
            
            logger.info(f"Added {dependencies_added} additional relationships from static analysis")
            
        except Exception as e:
            logger.error(f"Error enhancing graph with static analysis: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _incorporate_runtime_traces(self) -> None:
        """
        Incorporate runtime execution traces into the dependency graph.
        
        This method analyzes runtime traces to discover dynamic relationships
        between files that might not be apparent from static analysis.
        """
        if not self.graph or not self.execution_traces:
            return
            
        logger.info("Incorporating runtime traces into dependency graph...")
        
        try:
            count = 0
            for trace in self.execution_traces:
                # Process the trace to extract file relationships
                for i in range(len(trace) - 1):
                    source_file = trace[i]
                    target_file = trace[i + 1]
                    
                    # Create a metadata object for the relationship
                    metadata = DependencyMetadata(
                        dependency_type=DependencyType.RUNTIME
                    )
                    
                    # Add the edge to the graph
                    if source_file in self.graph and target_file in self.graph:
                        self.graph.add_edge(source_file, target_file, metadata)
                        count += 1
                    
            logger.info(f"Added {count} runtime relationships from execution traces")
            
        except Exception as e:
            logger.error(f"Error incorporating runtime traces: {e}")
    
    def add_execution_trace(self, trace: List[str]) -> None:
        """
        Add an execution trace to the agent.
        
        Args:
            trace: List of file paths in the execution trace
        """
        self.execution_traces.append(trace)
        
    def _save_report(self, report_path: str, summary: Dict[str, Any]) -> None:
        """
        Save the analysis report to a file.
        
        Args:
            report_path: Path to save the report
            summary: Analysis summary
        """
        try:
            # Create the report directory if it doesn't exist
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            
            # Get additional information for the report
            cycles = self.analyzer.find_cycles() if self.analyzer else []
            central_files = self.analyzer.get_most_central_files(n=20) if self.analyzer else []
            
            # Create the report
            report = {
                "summary": summary,
                "cycles": cycles,
                "central_files": central_files,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "agent_id": self.agent_id,
                    "agent_name": self.name
                }
            }
            
            # Save the report
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info(f"Saved relationship report to {report_path}")
            
        except Exception as e:
            logger.error(f"Error saving relationship report: {e}")
    
    def _handle_query(self, message: AgentMessage) -> Optional[AgentMessage]:
        """
        Handle a query message from another agent.
        
        Args:
            message: The query message to handle
            
        Returns:
            Response message, if any
        """
        content = message.content
        if not isinstance(content, dict):
            return None
            
        query_type = content.get("query_type", "")
        
        if query_type == "central_files":
            n = content.get("n", 10)
            metric = content.get("metric", "pagerank")
            
            try:
                central_files = self.get_most_central_files(n=n, metric=metric)
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "success",
                        "central_files": central_files
                    }
                )
            except Exception as e:
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
                
        elif query_type == "cycles":
            try:
                cycles = self.find_cycles()
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "success",
                        "cycles": cycles
                    }
                )
            except Exception as e:
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
                
        elif query_type == "dependents":
            file_path = content.get("file_path", "")
            transitive = content.get("transitive", False)
            
            try:
                dependents = self.get_file_dependents(file_path, transitive=transitive)
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "success",
                        "dependents": list(dependents)
                    }
                )
            except Exception as e:
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
                
        elif query_type == "dependencies":
            file_path = content.get("file_path", "")
            transitive = content.get("transitive", False)
            
            try:
                dependencies = self.get_file_dependencies(file_path, transitive=transitive)
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "success",
                        "dependencies": list(dependencies)
                    }
                )
            except Exception as e:
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
                
        elif query_type == "impact":
            modified_files = content.get("modified_files", [])
            
            try:
                impacted = self.predict_impact(modified_files)
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "success",
                        "impacted_files": list(impacted)
                    }
                )
            except Exception as e:
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
                
        return None
    
    def _handle_task_request(self, message: AgentMessage) -> Optional[AgentMessage]:
        """
        Handle a task request message from another agent.
        
        Args:
            message: The task request message to handle
            
        Returns:
            Response message, if any
        """
        content = message.content
        if not isinstance(content, dict):
            return None
            
        task_type = content.get("task_type", "")
        
        if task_type == "analyze_codebase":
            root_dir = content.get("root_dir", ".")
            include_patterns = content.get("include_patterns")
            exclude_patterns = content.get("exclude_patterns")
            incremental = content.get("incremental", True)
            
            try:
                summary = self.analyze_codebase(
                    root_dir=root_dir,
                    include_patterns=include_patterns,
                    exclude_patterns=exclude_patterns,
                    incremental=incremental
                )
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "success",
                        "summary": summary
                    }
                )
            except Exception as e:
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
                
        elif task_type == "add_execution_trace":
            trace = content.get("trace", [])
            
            try:
                self.add_execution_trace(trace)
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "success",
                        "message": "Execution trace added"
                    }
                )
            except Exception as e:
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
                
        return None
    
    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """
        Handle a message from another agent.
        
        Args:
            message: Message to handle
            
        Returns:
            Response message, if any
        """
        if message.message_type != MessageType.REQUEST:
            return None
            
        content = message.content
        if not isinstance(content, dict):
            return None
            
        action = content.get("action", "")
        
        if action == "analyze_codebase":
            root_dir = content.get("root_dir", ".")
            include_patterns = content.get("include_patterns")
            exclude_patterns = content.get("exclude_patterns")
            incremental = content.get("incremental", True)
            
            try:
                summary = self.analyze_codebase(
                    root_dir=root_dir,
                    include_patterns=include_patterns,
                    exclude_patterns=exclude_patterns,
                    incremental=incremental
                )
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "success",
                        "summary": summary
                    }
                )
            except Exception as e:
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
                
        elif action == "get_central_files":
            n = content.get("n", 10)
            metric = content.get("metric", "pagerank")
            
            try:
                central_files = self.get_most_central_files(n=n, metric=metric)
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "success",
                        "central_files": central_files
                    }
                )
            except Exception as e:
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
                
        elif action == "predict_impact":
            modified_files = content.get("modified_files", [])
            
            try:
                impacted = self.predict_impact(modified_files)
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "success",
                        "impacted_files": list(impacted)
                    }
                )
            except Exception as e:
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.RESPONSE,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
        
        return None
    
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a message as a dictionary.
        
        This is a simplified interface for external systems that don't use the
        AgentMessage protocol.
        
        Args:
            message: Dictionary containing the message
            
        Returns:
            Dictionary containing the response
        """
        action = message.get("action")
        if not action:
            return {"status": "error", "error": "No action specified"}

        try:
            if action == "analyze_codebase":
                root_dir = message.get("root_dir", ".")
                summary = self.analyze_codebase(root_dir)
                return {"status": "success", "summary": summary}
            
            elif action == "get_central_files":
                n = message.get("n", 10)
                metric = message.get("metric", "pagerank")
                central_files = self.get_most_central_files(n=n, metric=metric)
                return {"status": "success", "central_files": central_files}

            elif action == "predict_impact":
                modified_files = message.get("modified_files", [])
                impacted_files = self.predict_impact(modified_files)
                return {"status": "success", "impacted_files": list(impacted_files)}

            else:
                return {"status": "error", "error": f"Unknown action: {action}"}
        
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
