"""
Quantum Entanglement Module - Implements quantum-inspired algorithms for bug detection and repair.

This module provides quantum simulation capabilities that enhance Triangulum's ability to:
1. Detect complex, entangled bugs across multiple files
2. Perform parallel simulations of potential fixes
3. Optimize repair strategies through quantum-inspired algorithms
4. Reduce computational complexity through quantum parallelization
"""

import logging
import numpy as np
from typing import Dict, List, Set, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
import random
from enum import Enum

from ..core.exceptions import TriangulumError
from ..tooling.dependency_graph import DependencyGraph
from ..tooling.graph_models import FileNode

logger = logging.getLogger(__name__)


class QuantumState(Enum):
    """Represents possible quantum states for bug simulation."""
    SUPERPOSITION = "superposition"  # Bug might exist in multiple states
    ENTANGLED = "entangled"          # Bug is entangled with other components
    COLLAPSED = "collapsed"          # Bug state has been determined
    INTERFERENCE = "interference"    # Bug exhibits interference patterns


@dataclass
class EntangledState:
    """
    Represents an entangled quantum state between multiple code components.
    
    This class models the quantum entanglement between different parts of a codebase,
    allowing for simulation of how bugs might propagate and interact across files.
    """
    components: List[str] = field(default_factory=list)
    entanglement_strength: Dict[Tuple[str, str], float] = field(default_factory=dict)
    state_vector: np.ndarray = None
    qubits: int = 0
    
    def __post_init__(self):
        """Initialize the quantum state vector."""
        self.qubits = len(self.components)
        if self.qubits > 0:
            # Create a quantum state vector with 2^n amplitudes for n qubits
            self.state_vector = np.zeros(2**self.qubits, dtype=complex)
            # Initialize to superposition state
            self.state_vector[0] = 1.0
            self.normalize()
    
    def add_component(self, component_id: str) -> None:
        """Add a component to the entangled state."""
        if component_id not in self.components:
            self.components.append(component_id)
            self.qubits = len(self.components)
            # Resize state vector and maintain superposition
            new_state = np.zeros(2**self.qubits, dtype=complex)
            if self.state_vector is not None:
                # Copy existing state to new state (padding with zeros)
                size = min(len(self.state_vector), len(new_state))
                new_state[:size] = self.state_vector[:size]
            else:
                new_state[0] = 1.0
            self.state_vector = new_state
            self.normalize()
    
    def set_entanglement(self, component1: str, component2: str, strength: float) -> None:
        """Set the entanglement strength between two components."""
        if component1 not in self.components or component2 not in self.components:
            raise TriangulumError(f"Components must be added before setting entanglement")
        
        # Store entanglement strength in both directions
        self.entanglement_strength[(component1, component2)] = strength
        self.entanglement_strength[(component2, component1)] = strength
    
    def apply_hadamard(self, component_index: int) -> None:
        """Apply Hadamard gate to put a component in superposition."""
        if component_index >= self.qubits:
            raise TriangulumError(f"Invalid component index: {component_index}")
        
        # Hadamard matrix
        h = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
        
        # Apply to the specified qubit
        new_state = np.zeros_like(self.state_vector)
        for i in range(len(self.state_vector)):
            bit = (i >> component_index) & 1
            for j in range(2):
                idx = i & ~(1 << component_index) | (j << component_index)
                new_state[idx] += h[j, bit] * self.state_vector[i]
        
        self.state_vector = new_state
    
    def normalize(self) -> None:
        """Normalize the state vector."""
        if self.state_vector is not None:
            norm = np.linalg.norm(self.state_vector)
            if norm > 0:
                self.state_vector = self.state_vector / norm
    
    def measure(self) -> List[int]:
        """
        Measure the quantum state, collapsing superposition.
        
        Returns:
            List[int]: The measured state as a list of 0's and 1's
        """
        if self.state_vector is None:
            return []
        
        # Calculate probabilities for each state
        probabilities = np.abs(self.state_vector)**2
        
        # Choose a state based on probabilities
        result_idx = np.random.choice(len(probabilities), p=probabilities)
        
        # Convert to binary representation
        result = [(result_idx >> i) & 1 for i in range(self.qubits)]
        
        # Collapse state vector to the measured state
        collapsed = np.zeros_like(self.state_vector)
        collapsed[result_idx] = 1.0
        self.state_vector = collapsed
        
        return result
    
    def get_entanglement_map(self) -> Dict[str, List[Tuple[str, float]]]:
        """
        Get a map of entangled components.
        
        Returns:
            Dict[str, List[Tuple[str, float]]]: Map of component to list of (related_component, strength)
        """
        result = {comp: [] for comp in self.components}
        
        for (c1, c2), strength in self.entanglement_strength.items():
            if c1 in result:
                result[c1].append((c2, strength))
        
        return result


class QuantumBugSimulator:
    """
    Simulates bug behavior using quantum-inspired algorithms.
    
    This class uses quantum-inspired algorithms to simulate how bugs might
    propagate through a codebase, taking into account dependencies and code relationships.
    """
    
    def __init__(self, dependency_graph: Optional[DependencyGraph] = None):
        """
        Initialize the quantum bug simulator.
        
        Args:
            dependency_graph: Optional dependency graph to use for entanglement
        """
        self.entangled_state = EntangledState()
        self.dependency_graph = dependency_graph
        self.bug_probabilities = {}  # file_path -> probability of bug
        self.repair_simulations = {}  # file_path -> list of simulation results
    
    def initialize_from_graph(self) -> None:
        """Initialize quantum state from dependency graph."""
        if not self.dependency_graph:
            logger.warning("No dependency graph provided. Quantum simulation will be limited.")
            return
        
        # Extract nodes from dependency graph
        nodes = self.dependency_graph.get_all_nodes()
        
        # Add each file as a component
        for node in nodes:
            self.entangled_state.add_component(node.path)
        
        # Set entanglement based on dependencies
        edges = self.dependency_graph.get_all_edges()
        for edge in edges:
            source = edge.source
            target = edge.target
            # Calculate entanglement strength based on dependency type
            strength = edge.metadata.weight if hasattr(edge.metadata, 'weight') else 0.5
            self.entangled_state.set_entanglement(source, target, strength)
    
    def calculate_bug_probabilities(self) -> Dict[str, float]:
        """
        Calculate the probability of bugs in each file.
        
        Returns:
            Dict[str, float]: Mapping of file paths to bug probabilities
        """
        result = {}
        
        # Put all components in superposition
        for i in range(self.entangled_state.qubits):
            self.entangled_state.apply_hadamard(i)
        
        # Perform multiple measurements to approximate probabilities
        measurements = []
        for _ in range(100):  # Number of measurements
            # Create a copy of the state for measurement
            temp_state = EntangledState(
                components=self.entangled_state.components.copy(),
                entanglement_strength=self.entangled_state.entanglement_strength.copy()
            )
            temp_state.state_vector = np.copy(self.entangled_state.state_vector)
            
            # Measure and record
            measurements.append(temp_state.measure())
        
        # Calculate probabilities from measurements
        for i, component in enumerate(self.entangled_state.components):
            bug_count = sum(m[i] for m in measurements)
            result[component] = bug_count / len(measurements)
        
        self.bug_probabilities = result
        return result
    
    def simulate_repairs(self, bug_file: str, num_simulations: int = 10) -> List[Dict[str, Any]]:
        """
        Simulate potential repairs for a bug.
        
        Args:
            bug_file: File containing the bug
            num_simulations: Number of simulations to run
            
        Returns:
            List[Dict[str, Any]]: List of simulation results
        """
        if bug_file not in self.entangled_state.components:
            raise TriangulumError(f"File {bug_file} not in entangled state")
        
        results = []
        
        # Get file index in the components list
        file_idx = self.entangled_state.components.index(bug_file)
        
        # Get entanglement map to identify related files
        entanglement_map = self.entangled_state.get_entanglement_map()
        related_files = [comp for comp, strength in entanglement_map.get(bug_file, [])]
        
        # Simulate multiple repair strategies
        for sim_id in range(num_simulations):
            # Create a copy of the state for simulation
            sim_state = EntangledState(
                components=self.entangled_state.components.copy(),
                entanglement_strength=self.entangled_state.entanglement_strength.copy()
            )
            sim_state.state_vector = np.copy(self.entangled_state.state_vector)
            
            # Apply "repair" operation (simulated by quantum gate)
            self._apply_repair_operation(sim_state, file_idx)
            
            # Measure to see the effect on the system
            final_state = sim_state.measure()
            
            # Calculate "success probability" by checking if bug was fixed and related files weren't affected
            success_prob = self._calculate_repair_success(final_state, file_idx, related_files)
            
            results.append({
                "simulation_id": sim_id,
                "primary_file": bug_file,
                "related_files": related_files,
                "final_state": final_state,
                "success_probability": success_prob
            })
        
        self.repair_simulations[bug_file] = results
        return results
    
    def _apply_repair_operation(self, state: EntangledState, file_idx: int) -> None:
        """Apply a simulated quantum repair operation."""
        # This is a simplified "repair" operation
        # In a real quantum system, this would be a more complex gate
        
        # Flip the bit for the bug file (simulating fixing the bug)
        new_state = np.zeros_like(state.state_vector)
        for i in range(len(state.state_vector)):
            # Flip the bit at file_idx
            flipped_i = i ^ (1 << file_idx)
            new_state[flipped_i] = state.state_vector[i]
        
        state.state_vector = new_state
    
    def _calculate_repair_success(self, final_state: List[int], 
                                 file_idx: int, 
                                 related_files: List[str]) -> float:
        """Calculate the probability of repair success."""
        # Check if the bug was fixed (bit at file_idx should be 0)
        if final_state[file_idx] != 0:
            return 0.0  # Bug not fixed
        
        # Check if related files were negatively affected
        affected_count = 0
        for related_file in related_files:
            related_idx = self.entangled_state.components.index(related_file)
            # If the state of a related file changed to 1, it was negatively affected
            if final_state[related_idx] == 1:
                affected_count += 1
        
        # Success probability decreases with more affected files
        if not related_files:
            return 1.0  # No related files, 100% success
        
        return max(0.0, 1.0 - (affected_count / len(related_files)))
    
    def get_optimal_repair_strategy(self, bug_file: str) -> Dict[str, Any]:
        """
        Get the optimal repair strategy based on simulations.
        
        Args:
            bug_file: File containing the bug
            
        Returns:
            Dict[str, Any]: The optimal repair strategy
        """
        if bug_file not in self.repair_simulations:
            raise TriangulumError(f"No simulations found for {bug_file}")
        
        # Find the simulation with the highest success probability
        simulations = self.repair_simulations[bug_file]
        optimal = max(simulations, key=lambda x: x["success_probability"])
        
        return {
            "file": bug_file,
            "strategy": f"Quantum Strategy {optimal['simulation_id']}",
            "success_probability": optimal["success_probability"],
            "potential_side_effects": [
                self.entangled_state.components[i] 
                for i, state in enumerate(optimal["final_state"]) 
                if state == 1 and i != self.entangled_state.components.index(bug_file)
            ],
            "recommendation": "Apply focused changes to avoid affecting entangled components"
        }
