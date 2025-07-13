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
# from .message_bus import MessageBus # Old
from .enhanced_message_bus import EnhancedMessageBus # New
# Updated import to point to the consolidated dependency_graph
from ..tooling.dependency_graph import DependencyGraphBuilder, DependencyAnalyzer, DependencyGraph, FileNode, DependencyType, DependencyMetadata
# CodeRelationshipAnalyzer is removed as its functionality is being simplified/merged or deferred.

logger = logging.getLogger(__name__)

class RelationshipAnalystAgent(BaseAgent):
    """
    Agent that analyzes the relationships between code files to provide context for other agents.
    
    The RelationshipAnalystAgent discovers, tracks, and reports on the complex
    relationships between files in a codebase. It creates a comprehensive dependency
    graph that other agents use to understand the impact of changes and identify related
    files for repair.
    """
    AGENT_TYPE = "relationship_analyst"

    def __init__(self, 
                 agent_id: Optional[str] = None, # Made Optional for factory
                 message_bus: Optional[EnhancedMessageBus] = None,
                 config: Optional[Dict[str, Any]] = None,
                 **kwargs):
        """
        Initialize the RelationshipAnalystAgent.
        
        Args:
            agent_id: Unique identifier for the agent.
            message_bus: EnhancedMessageBus for communication.
            config: Agent configuration dictionary. Expected keys:
                    'name' (optional, defaults to agent_id),
                    'cache_dir' (optional),
                    'visualization_dir' (optional, defaults to cache_dir/visualizations).
        """
        super().__init__(
            agent_id=agent_id,
            agent_type=self.AGENT_TYPE,
            message_bus=message_bus,
            config=config,
            subscribed_message_types=[MessageType.TASK_REQUEST, MessageType.QUERY],
            **kwargs
        )

        self.name = self.config.get("name", self.agent_id)
        
        # Analysis components
        self.graph: Optional[DependencyGraph] = None # Type hint with new graph model
        self.analyzer: Optional[DependencyAnalyzer] = None # Type hint with new analyzer
        
        # Historical tracking
        self.historical_graphs: List[Tuple[str, DependencyGraph]] = [] # Store (timestamp, graph_model)
        self.last_analysis_time: Optional[float] = None
        self.execution_traces: List[List[str]] = [] # List of traces, each trace is a list of file paths
        
        # Cache directory from config
        self.cache_dir = self.config.get("cache_dir")
        if self.cache_dir:
            Path(self.cache_dir).mkdir(parents=True, exist_ok=True) # Use Pathlib
            
        # Visualization settings from config
        default_viz_dir = Path(self.cache_dir, "visualizations") if self.cache_dir else None
        self.visualization_dir = self.config.get("visualization_dir", default_viz_dir)
        if self.visualization_dir:
            Path(self.visualization_dir).mkdir(parents=True, exist_ok=True)

        # CodeRelationshipAnalyzer instance is removed.
        # The _enhance_with_static_analysis method will be removed or significantly refactored.
            
    def analyze_codebase(
        self,
        root_dir: str,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        incremental: bool = True,
        # perform_static_analysis: bool = True, # This will be simplified/removed
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
                
        # _enhance_with_static_analysis (using CodeRelationshipAnalyzer) is removed for now.
        # The new DependencyGraphBuilder and its parsers (esp. PythonDependencyParser)
        # already perform AST-based import analysis. Deeper static analysis like call graphs
        # would be a future enhancement to the parsers or a new specialized analyzer.
            
        # Incorporate runtime traces if requested
        if analyze_runtime_traces and self.execution_traces:
            self._incorporate_runtime_traces() # This method might need adjustment if graph structure changed
            
        # Create an analyzer for the graph
        # The self.graph is now an instance of our stubbed DependencyGraph.
        # The DependencyAnalyzer (from tooling.dependency_analyzer) takes this.
        self.analyzer = DependencyAnalyzer(self.graph)
        
        # Return a summary
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Adjust summary to reflect new graph structure if needed
        # self.graph is DependencyGraph, self.analyzer.nx_graph is networkx
        num_nodes = len(self.analyzer.nx_graph.nodes()) if self.analyzer and self.analyzer.nx_graph else 0
        num_edges = len(self.analyzer.nx_graph.edges()) if self.analyzer and self.analyzer.nx_graph else 0
        num_cycles = len(self.analyzer.find_cycles()) if self.analyzer else 0

        summary = {
            "files_analyzed": num_nodes,
            "dependencies_found": num_edges,
            "cycles_detected": num_cycles,
            "languages_detected": self._count_languages(), # This method needs to use self.analyzer.nx_graph or self.graph
            "analysis_timestamp": timestamp,
            "temporal_snapshots": len(self.historical_graphs),
            "runtime_traces_incorporated": analyze_runtime_traces and bool(self.execution_traces),
            # "static_analysis_performed": perform_static_analysis # Removed as the method is removed
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
        if not self.analyzer or not self.analyzer.nx_graph: # Check analyzer and its nx_graph
            raise ValueError("No analysis has been performed yet. Call analyze_codebase first.")
        
        # Uses the networkx graph from the analyzer
        if file_path not in self.analyzer.nx_graph:
             return set()
        if transitive:
            # nx.ancestors gives all nodes that have a path to file_path
            # In a graph where A -> B means A imports B, ancestors are dependents.
            return set(nx.ancestors(self.analyzer.nx_graph, file_path))
        else:
            return set(self.analyzer.nx_graph.predecessors(file_path))
    
    def get_file_dependencies(self, file_path: str, transitive: bool = False) -> Set[str]:
        """
        Get files that the specified file depends on.
        
        Args:
            file_path: Path to the file
            transitive: Whether to include transitive dependencies
            
        Returns:
            Set of file paths that the specified file depends on
        """
        if not self.analyzer or not self.analyzer.nx_graph: # Check analyzer and its nx_graph
            raise ValueError("No analysis has been performed yet. Call analyze_codebase first.")

        if file_path not in self.analyzer.nx_graph:
            return set()
        if transitive:
            # nx.descendants gives all nodes reachable from file_path
            # In a graph where A -> B means A imports B, descendants are dependencies.
            return set(nx.descendants(self.analyzer.nx_graph, file_path))
        else:
            return set(self.analyzer.nx_graph.successors(file_path))
    
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
            files = list(self.analyzer.nx_graph.nodes())
            
        impact_boundaries = {}
        for file_path in files:
            if file_path not in self.analyzer.nx_graph:
                impact_boundaries[file_path] = set()
                continue

            impact_boundary = set()
            # BFS on predecessors (dependents)
            # queue stores (node, current_depth)
            queue = deque([(file_path, 0)])
            visited_for_bfs = {file_path} # Keep track of visited to avoid redundant exploration in BFS for this call

            # We are looking for files that depend on 'file_path', or files that would be affected if 'file_path' changes.
            # These are the "ancestors" in a graph where edge A->B means A imports B.

            # Iterative deepening BFS/DFS could be an option.
            # For simplicity, let's get all ancestors and then filter by path length if needed,
            # or perform a bounded BFS.

            # Bounded BFS for ancestors:
            # queue stores (node, path_to_node_from_a_dependent)
            # This is complex. Easier: get all ancestors, then if needed, filter paths.
            # For now, let's just get all transitive dependents (ancestors).
            # The original logic was also essentially getting transitive dependents but bounded by depth.

            # Simple transitive dependents (ancestors)
            # To respect max_depth is harder without iterating paths.
            # For now, this will return all transitive dependents.
            # A true depth-limited search on predecessors is needed for strict max_depth.
            # nx.bfs_tree(self.analyzer.nx_graph.reverse(), source=file_path, depth_limit=max_depth) could work.

            # Simplified: get all transitive dependents. max_depth is not strictly enforced here.
            # A proper bounded search would be:
            q = deque([(file_path, 0)]) # node, depth
            visited_bfs = {file_path}
            # Note: impact_boundary should not include file_path itself.

            while q:
                curr, depth = q.popleft()
                if depth >= max_depth:
                    continue
                for predecessor in self.analyzer.nx_graph.predecessors(curr):
                    if predecessor not in visited_bfs:
                        visited_bfs.add(predecessor)
                        impact_boundary.add(predecessor)
                        q.append((predecessor, depth + 1))
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
            if current in self.analyzer.nx_graph: # Check against nx_graph
                for neighbor in self.analyzer.nx_graph.successors(current):
                    if neighbor not in path:  # Avoid cycles
                        queue.append(path + [neighbor])
                        
        return paths
    
    def predict_impact(self, modified_files: List[str]) -> Set[str]:
        """
        Predict the impact of modifying a set of files.
        
        Args:
            modified_files: List of file paths that will be modified
            
        Returns:
            Set of file paths that might be impacted by the modifications
        """
        if not self.analyzer or not self.analyzer.nx_graph: # Check analyzer and its nx_graph
            raise ValueError("No analysis has been performed yet. Call analyze_codebase first.")
        
        impacted = set()
        for file_path in modified_files:
            if file_path in self.analyzer.nx_graph:
                # Dependents are ancestors in A->B (A imports B) graph
                dependents = nx.ancestors(self.analyzer.nx_graph, file_path)
                impacted.update(dependents)
            
        return impacted
    
    def _count_languages(self) -> Dict[str, int]:
        """
        Count the number of files for each language in the codebase.
        
        Returns:
            Dictionary mapping language to number of files
        """
        languages = defaultdict(int)
        
        if not self.analyzer or not self.analyzer.nx_graph: # Check analyzer and its nx_graph
            return dict(languages)
            
        for node_path_str in self.analyzer.nx_graph.nodes():
            # Assuming nodes in nx_graph are strings (paths)
            # If FileNode language info is needed, it should be on node attributes in nx_graph
            # Or, iterate self.graph_model._nodes if that's preferred
            node_data = self.analyzer.nx_graph.nodes[node_path_str]
            lang_val = node_data.get('language', LanguageType.UNKNOWN.value) # Get from node attribute

            # lang_type_enum = LanguageType(lang_val) if isinstance(lang_val, str) else LanguageType.UNKNOWN
            # The current stub for FileNode stores language as LanguageType enum, to_dict converts to value.
            # So lang_val should be like "python".

            if lang_val == LanguageType.PYTHON.value: languages['PYTHON'] += 1
            elif lang_val == LanguageType.JAVASCRIPT.value: languages['JAVASCRIPT'] += 1
            elif lang_val == LanguageType.TYPESCRIPT.value: languages['TYPESCRIPT'] += 1 # Added for TS
            elif lang_val == LanguageType.JAVA.value: languages['JAVA'] += 1
            elif lang_val == LanguageType.GO.value: languages['GO'] += 1
            # Add other LanguageType enum values as needed
            else: languages['OTHER'] += 1
            
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
            # This method is removed as CodeRelationshipAnalyzer was removed.
            # Its functionality (deeper static analysis for Python like function calls)
            # would need to be integrated into PythonDependencyParser or a new,
            # more focused AST analysis tool if required.
            # For now, the dependency graph relies on what the parsers (mainly import-based) provide.
            logger.info("Skipping _enhance_with_static_analysis as CodeRelationshipAnalyzer is removed/refactored.")
            pass
        except Exception as e:
            logger.error(f"Error during static analysis enhancement: {e}", exc_info=True)
    
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
