import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Callable
import json
import tempfile # For visualize_graph temp file

from triangulum_lx.tooling.fs_ops import atomic_write, atomic_rename
from triangulum_lx.core.fs_state import FileSystemStateCache

from .ltl_properties import LTLFormula, triangulum_properties, predicate_mapping
from ..core.state import Phase, BugState
from ..core.transition import step
from ..core.engine import TriangulationEngine


class TriangulumModelChecker:
    """
    Model checker for verifying Triangulum system properties.
    
    This implements a basic model checker that generates a state transition graph
    for the Triangulum system and verifies LTL properties against it.
    """
    
    def __init__(self, max_states: int = 1000, fs_cache: Optional[FileSystemStateCache] = None):
        self.max_states = max_states
        self.graph = nx.DiGraph()
        self.states: Dict[int, Dict[str, Any]] = {}
        self.counter_examples: Dict[str, List[Dict[str, Any]]] = {}
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()
    
    def build_state_graph(self, engine: TriangulationEngine = None) -> nx.DiGraph:
        """
        Build a state transition graph from the system model.
        
        Args:
            engine: TriangulationEngine instance to model (uses default if None)
            
        Returns:
            nx.DiGraph: State transition graph where nodes are state IDs
                       and edges represent transitions
        """
        if engine is None:
            engine = TriangulationEngine()
        
        # Start with initial state
        initial_state = self._extract_state(engine)
        initial_state_id = self._hash_state(initial_state)
        
        self.states[initial_state_id] = initial_state
        self.graph.add_node(initial_state_id)
        
        # BFS exploration of state space
        frontier = [initial_state_id]
        visited = set(frontier)
        
        while frontier and len(self.states) < self.max_states:
            current_id = frontier.pop(0)
            current_state = self.states[current_id]
            
            # Get possible transitions
            next_states = self._get_next_states(current_state)
            
            for next_state in next_states:
                next_id = self._hash_state(next_state)
                
                # Add state if new
                if next_id not in self.states:
                    self.states[next_id] = next_state
                    self.graph.add_node(next_id)
                
                # Add transition
                self.graph.add_edge(current_id, next_id)
                
                # Add to frontier if not visited
                if next_id not in visited:
                    visited.add(next_id)
                    frontier.append(next_id)
        
        return self.graph
    
    def _extract_state(self, engine: TriangulationEngine) -> Dict[str, Any]:
        """Extract state representation from engine."""
        return {
            'tick_no': engine.tick_no,
            'free_agents': engine.free_agents,
            'bugs': [
                {
                    'phase': bug.phase,
                    'timer': bug.timer,
                    'attempts': bug.attempts
                }
                for bug in engine.bugs
            ],
            'entropy_bits': engine.monitor.g_bits if hasattr(engine.monitor, 'g_bits') else 0,
            'entropy_threshold': engine.monitor.H0_bits if hasattr(engine.monitor, 'H0_bits') else 3.32
        }
    
    def _hash_state(self, state: Dict[str, Any]) -> int:
        """Create a hashable representation of a state."""
        # Convert to tuple of immutable values
        bugs_tuple = tuple(
            (bug['phase'].value, bug['timer'], bug['attempts'])
            for bug in state['bugs']
        )
        
        state_tuple = (
            state['tick_no'],
            state['free_agents'],
            bugs_tuple,
            state['entropy_bits']
        )
        
        return hash(state_tuple)
    
    def _get_next_states(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get all possible next states from the current state.
        
        Args:
            state: Current state dictionary
            
        Returns:
            List of possible next state dictionaries
        """
        # Create an engine instance with the current state
        engine = TriangulationEngine()
        engine.tick_no = state['tick_no']
        engine.free_agents = state['free_agents']
        
        # Set bug states
        engine.bugs = [
            BugState(
                phase=bug['phase'],
                timer=bug['timer'],
                attempts=bug['attempts']
            )
            for bug in state['bugs']
        ]
        
        # Set monitor state if possible
        if hasattr(engine, 'monitor') and engine.monitor:
            engine.monitor.g_bits = state.get('entropy_bits', 0)
            
        # Calculate next state after a tick
        try:
            engine.tick()
            next_state = self._extract_state(engine)
            return [next_state]
        except Exception as e:
            # If tick fails, return empty list
            print(f"Error calculating next state: {e}")
            return []
    
    def verify_properties(self, 
                         properties: List[LTLFormula] = None,
                         max_trace_length: int = 100) -> Dict[str, bool]:
        """
        Verify LTL properties against the state graph.
        
        Args:
            properties: List of LTLFormula objects to verify (uses default if None)
            max_trace_length: Maximum length of traces to check
            
        Returns:
            Dict mapping property descriptions to verification results (True/False)
        """
        if properties is None:
            properties = triangulum_properties
            
        if not self.graph:
            raise ValueError("State graph not built. Call build_state_graph first.")
            
        results = {}
        
        for formula in properties:
            # For each starting state
            for start_node in self.graph.nodes():
                # Generate all possible traces from this node
                traces = self._generate_traces(start_node, max_trace_length)
                
                # Check formula against all traces
                formula_result = True
                for trace in traces:
                    trace_states = [self.states[node_id] for node_id in trace]
                    
                    # If any trace fails, record a counter-example
                    if not formula.evaluate(trace_states, predicate_mapping):
                        formula_result = False
                        self.counter_examples[formula.description] = trace_states
                        break
                
                results[formula.description] = formula_result
                
                # If formula already failed, no need to check other starting states
                if not formula_result:
                    break
        
        return results
    
    def _generate_traces(self, 
                        start_node: int, 
                        max_length: int, 
                        max_traces: int = 100) -> List[List[int]]:
        """
        Generate traces (paths) through the state graph.
        
        Args:
            start_node: Node ID to start from
            max_length: Maximum length of traces
            max_traces: Maximum number of traces to generate
            
        Returns:
            List of traces (each trace is a list of node IDs)
        """
        traces = []
        
        # DFS to find paths
        def dfs(node, path, visited_set):
            # Add current node to path
            path.append(node)
            
            # If path is max length or node has no outgoing edges, return the path
            if len(path) >= max_length or self.graph.out_degree(node) == 0:
                traces.append(path.copy())
                path.pop()
                return
            
            # If we have enough traces, stop
            if len(traces) >= max_traces:
                path.pop()
                return
            
            # Visit all neighbors
            for next_node in self.graph.successors(node):
                # Detect cycles - only visit a node again if it's not in the current path
                if next_node not in visited_set:
                    visited_set.add(next_node)
                    dfs(next_node, path, visited_set)
                    visited_set.remove(next_node)
                # Special case - allow revisiting the last node to capture loops
                elif next_node == path[-1]:
                    traces.append(path.copy() + [next_node])
            
            path.pop()
        
        # Start DFS
        dfs(start_node, [], {start_node})
        
        return traces[:max_traces]
    
    def visualize_graph(self, output_path: str = "state_graph.png") -> str:
        """
        Generate visualization of the state transition graph.
        
        Args:
            output_path: Path to save the visualization
            
        Returns:
            str: Path to the saved visualization
        """
        if not self.graph:
            raise ValueError("State graph not built. Call build_state_graph first.")
            
        plt.figure(figsize=(12, 10))
        
        # Use hierarchical layout for state transition graphs
        pos = nx.spring_layout(self.graph)
        
        # Draw with node labels as phase summaries
        labels = {}
        for node in self.graph.nodes():
            state = self.states[node]
            phase_counts = {}
            for bug in state['bugs']:
                phase = bug['phase'].name
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
            
            label = f"A:{state['free_agents']}"
            for phase, count in phase_counts.items():
                if count > 0:
                    label += f"\n{phase[0]}:{count}"
            
            labels[node] = label
        
        nx.draw(
            self.graph,
            pos=pos,
            with_labels=True,
            labels=labels,
            node_size=2000,
            node_color="lightblue",
            font_size=8,
            font_weight="bold",
            edge_color="gray",
            width=1.0,
            arrowsize=15,
            connectionstyle="arc3,rad=0.1"
        )
        
        plt.title("Triangulum State Transition Graph")
        
        # Save to a temporary file first
        temp_file_descriptor, temp_file_path_str = tempfile.mkstemp(suffix=".png", dir=".")
        os.close(temp_file_descriptor) # Close descriptor, savefig will open/close
        temp_file_path = Path(temp_file_path_str)

        try:
            plt.savefig(temp_file_path, dpi=300, bbox_inches="tight")
            plt.close() # Close the plot to free memory

            # Atomically move to final output_path
            Path(output_path).parent.mkdir(parents=True, exist_ok=True) # Ensure parent dir
            self.fs_cache.invalidate(str(Path(output_path).parent))

            atomic_rename(str(temp_file_path), output_path)
            self.fs_cache.invalidate(output_path)
            logger.info(f"State graph visualization saved to {output_path} using atomic_rename")
        except Exception as e:
            logger.error(f"Error saving graph visualization to {output_path}: {e}")
            # Clean up temp file if rename failed
            if temp_file_path.exists():
                try:
                    os.remove(temp_file_path)
                except OSError:
                    logger.error(f"Failed to remove temporary graph file {temp_file_path}")
            raise # Re-raise the exception
        finally:
            plt.close() # Ensure plot is closed even on error before rename
            # Temp file should be removed by atomic_rename on success, or by except block on failure.
            # If atomic_rename fails but doesn't raise, or if an error occurs after atomic_rename
            # but before this finally, then temp_file_path might not exist.
            if temp_file_path.exists(): # Final cleanup if somehow still there
                 try:
                    os.remove(temp_file_path)
                 except OSError:
                    pass # Already logged if problematic

        return output_path
    
    def save_results(self, results: Dict[str, bool], path: str = "verification_results.json") -> str:
        """
        Save verification results and counter-examples to file.
        
        Args:
            results: Dictionary mapping property descriptions to results
            path: Path to save the results
            
        Returns:
            str: Path to the saved results
        """
        output = {
            "results": results,
            "counter_examples": {
                # Convert counter-examples to serializable format
                desc: [
                    {
                        "tick_no": state.get('tick_no'),
                        "free_agents": state.get('free_agents'),
                        "bugs": [
                            {
                                "phase": bug.get('phase').name,
                                "timer": bug.get('timer'),
                                "attempts": bug.get('attempts')
                            }
                            for bug in state.get('bugs', [])
                        ],
                        "entropy_bits": state.get('entropy_bits')
                    }
                    for state in trace
                ]
                for desc, trace in self.counter_examples.items()
            }
        }
        
        Path(path).parent.mkdir(parents=True, exist_ok=True) # Ensure parent dir
        self.fs_cache.invalidate(str(Path(path).parent))

        content_str = json.dumps(output, indent=2)
        atomic_write(path, content_str.encode('utf-8'))
        self.fs_cache.invalidate(path)
        logger.info(f"Saved verification results to {path} using atomic_write")
        
        return path
    
    def generate_report(self, results: Dict[str, bool], output_path: str = "verification_report.md") -> str:
        """
        Generate a human-readable verification report.
        
        Args:
            results: Dictionary mapping property descriptions to results
            output_path: Path to save the report
            
        Returns:
            str: Path to the generated report
        """
        # Count verified and failed properties
        verified = sum(1 for result in results.values() if result)
        failed = sum(1 for result in results.values() if not result)
        
        report = [
            "# Triangulum Formal Verification Report",
            "",
            f"## Summary",
            f"",
            f"* **Properties verified:** {verified}",
            f"* **Properties failed:** {failed}",
            f"* **Total properties:** {len(results)}",
            f"",
            f"## Property Results",
            f""
        ]
        
        # Add results for each property
        for desc, result in results.items():
            status = "✅ VERIFIED" if result else "❌ FAILED"
            report.append(f"### {status}: {desc}")
            report.append("")
            
            # Add counter-example if property failed
            if not result and desc in self.counter_examples:
                report.append("#### Counter-example:")
                report.append("```")
                
                for i, state in enumerate(self.counter_examples[desc]):
                    report.append(f"State {i}:")
                    report.append(f"  Tick: {state.get('tick_no')}")
                    report.append(f"  Free agents: {state.get('free_agents')}")
                    report.append(f"  Entropy: {state.get('entropy_bits')}")
                    report.append("  Bugs:")
                    
                    for j, bug in enumerate(state.get('bugs', [])):
                        phase = bug.get('phase').name if hasattr(bug.get('phase', None), 'name') else bug.get('phase')
                        report.append(f"    Bug {j}: {phase}, Timer: {bug.get('timer')}, Attempts: {bug.get('attempts')}")
                    
                    report.append("")
                
                report.append("```")
                report.append("")
        
        # Add graph information
        report.append("## State Graph Information")
        report.append("")
        report.append(f"* **States explored:** {len(self.states)}")
        report.append(f"* **Transitions:** {self.graph.number_of_edges()}")
        
        # Write report to file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True) # Ensure parent dir
        self.fs_cache.invalidate(str(Path(output_path).parent))

        report_content_str = "\n".join(report)
        atomic_write(output_path, report_content_str.encode('utf-8'))
        self.fs_cache.invalidate(output_path)
        logger.info(f"Generated verification report to {output_path} using atomic_write")
        
        return output_path
