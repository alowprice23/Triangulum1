import unittest
import numpy as np
from pathlib import Path
import sys

# Ensure triangulum_lx is in the path
sys.path.append(str(Path(__file__).parent.parent.parent))

from triangulum_lx.quantum.entanglement import EntangledState, QuantumBugSimulator
from triangulum_lx.tooling.dependency_graph import DependencyGraph
from triangulum_lx.tooling.graph_models import FileNode, DependencyEdge, DependencyMetadata, DependencyType, LanguageType


class MockDependencyGraph:
    """Mock dependency graph for testing."""
    
    def __init__(self):
        self.nodes = []
        self.edges = []
    
    def add_node(self, file_path):
        node = FileNode(
            path=file_path,
            language=LanguageType.PYTHON
        )
        self.nodes.append(node)
        return node
    
    def add_edge(self, source, target, weight=0.5):
        metadata = DependencyMetadata(dependency_type=DependencyType.IMPORT)
        metadata.weight = weight
        edge = DependencyEdge(
            source=source.path,
            target=target.path,
            metadata=metadata
        )
        self.edges.append(edge)
        return edge
    
    def get_all_nodes(self):
        return self.nodes
    
    def get_all_edges(self):
        return self.edges


class TestEntangledState(unittest.TestCase):
    """Test cases for the EntangledState class."""
    
    def test_initialization(self):
        """Test that EntangledState initializes correctly."""
        state = EntangledState()
        self.assertEqual(len(state.components), 0)
        self.assertEqual(state.qubits, 0)
        self.assertIsNone(state.state_vector)
    
    def test_add_component(self):
        """Test adding components to the state."""
        state = EntangledState()
        state.add_component("file1.py")
        self.assertEqual(len(state.components), 1)
        self.assertEqual(state.qubits, 1)
        self.assertIsNotNone(state.state_vector)
        self.assertEqual(len(state.state_vector), 2)  # 2^1 = 2
        
        state.add_component("file2.py")
        self.assertEqual(len(state.components), 2)
        self.assertEqual(state.qubits, 2)
        self.assertEqual(len(state.state_vector), 4)  # 2^2 = 4
    
    def test_set_entanglement(self):
        """Test setting entanglement between components."""
        state = EntangledState()
        state.add_component("file1.py")
        state.add_component("file2.py")
        
        state.set_entanglement("file1.py", "file2.py", 0.7)
        self.assertEqual(state.entanglement_strength[("file1.py", "file2.py")], 0.7)
        self.assertEqual(state.entanglement_strength[("file2.py", "file1.py")], 0.7)
    
    def test_hadamard_and_measure(self):
        """Test applying Hadamard gate and measuring."""
        state = EntangledState()
        state.add_component("file1.py")
        
        # Initial state should be |0⟩
        self.assertAlmostEqual(abs(state.state_vector[0]), 1.0)
        self.assertAlmostEqual(abs(state.state_vector[1]), 0.0)
        
        # Apply Hadamard to put in superposition
        state.apply_hadamard(0)
        
        # Should now be in superposition
        self.assertAlmostEqual(abs(state.state_vector[0]), 1.0 / np.sqrt(2))
        self.assertAlmostEqual(abs(state.state_vector[1]), 1.0 / np.sqrt(2))
        
        # Measure 100 times and verify roughly 50/50 distribution
        results = []
        for _ in range(100):
            temp_state = EntangledState()
            temp_state.add_component("file1.py")
            temp_state.state_vector = np.copy(state.state_vector)
            results.append(temp_state.measure()[0])
        
        # Should be roughly 50/50
        zeros = results.count(0)
        ones = results.count(1)
        
        self.assertTrue(30 <= zeros <= 70)  # Allow some statistical variation
        self.assertTrue(30 <= ones <= 70)
        self.assertEqual(zeros + ones, 100)
    
    def test_get_entanglement_map(self):
        """Test getting the entanglement map."""
        state = EntangledState()
        state.add_component("file1.py")
        state.add_component("file2.py")
        state.add_component("file3.py")
        
        state.set_entanglement("file1.py", "file2.py", 0.7)
        state.set_entanglement("file1.py", "file3.py", 0.3)
        
        entanglement_map = state.get_entanglement_map()
        
        self.assertEqual(len(entanglement_map["file1.py"]), 2)
        self.assertEqual(len(entanglement_map["file2.py"]), 1)
        self.assertEqual(len(entanglement_map["file3.py"]), 1)
        
        # Check entanglement strengths
        found_f2 = False
        found_f3 = False
        for comp, strength in entanglement_map["file1.py"]:
            if comp == "file2.py":
                self.assertEqual(strength, 0.7)
                found_f2 = True
            elif comp == "file3.py":
                self.assertEqual(strength, 0.3)
                found_f3 = True
        
        self.assertTrue(found_f2)
        self.assertTrue(found_f3)


class TestQuantumBugSimulator(unittest.TestCase):
    """Test cases for the QuantumBugSimulator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.graph = MockDependencyGraph()
        
        # Create a simple dependency graph for testing
        self.f1 = self.graph.add_node("file1.py")
        self.f2 = self.graph.add_node("file2.py")
        self.f3 = self.graph.add_node("file3.py")
        
        self.graph.add_edge(self.f1, self.f2, 0.8)
        self.graph.add_edge(self.f2, self.f3, 0.5)
        
        self.simulator = QuantumBugSimulator(self.graph)
    
    def test_initialization_from_graph(self):
        """Test initializing the simulator from a dependency graph."""
        self.simulator.initialize_from_graph()
        
        # Should have added all files as components
        self.assertEqual(len(self.simulator.entangled_state.components), 3)
        
        # Should have set entanglement based on edges
        self.assertIn(("file1.py", "file2.py"), self.simulator.entangled_state.entanglement_strength)
        self.assertIn(("file2.py", "file3.py"), self.simulator.entangled_state.entanglement_strength)
        
        # Check entanglement strengths
        self.assertEqual(self.simulator.entangled_state.entanglement_strength[("file1.py", "file2.py")], 0.8)
        self.assertEqual(self.simulator.entangled_state.entanglement_strength[("file2.py", "file3.py")], 0.5)
    
    def test_calculate_bug_probabilities(self):
        """Test calculating bug probabilities."""
        self.simulator.initialize_from_graph()
        probabilities = self.simulator.calculate_bug_probabilities()
        
        # All files should have a probability
        self.assertEqual(len(probabilities), 3)
        self.assertIn("file1.py", probabilities)
        self.assertIn("file2.py", probabilities)
        self.assertIn("file3.py", probabilities)
        
        # Probabilities should be between 0 and 1
        for prob in probabilities.values():
            self.assertTrue(0.0 <= prob <= 1.0)
    
    def test_simulate_repairs(self):
        """Test simulating repairs."""
        self.simulator.initialize_from_graph()
        simulations = self.simulator.simulate_repairs("file1.py", num_simulations=5)
        
        # Should have the requested number of simulations
        self.assertEqual(len(simulations), 5)
        
        # Each simulation should have the correct structure
        for sim in simulations:
            self.assertIn("simulation_id", sim)
            self.assertIn("primary_file", sim)
            self.assertIn("related_files", sim)
            self.assertIn("final_state", sim)
            self.assertIn("success_probability", sim)
            
            # Primary file should be what we requested
            self.assertEqual(sim["primary_file"], "file1.py")
            
            # Related files should include file2.py
            self.assertIn("file2.py", sim["related_files"])
            
            # Success probability should be between 0 and 1
            self.assertTrue(0.0 <= sim["success_probability"] <= 1.0)
    
    def test_get_optimal_repair_strategy(self):
        """Test getting the optimal repair strategy."""
        self.simulator.initialize_from_graph()
        
        # Simulate repairs first
        self.simulator.simulate_repairs("file1.py", num_simulations=5)
        
        # Get optimal strategy
        strategy = self.simulator.get_optimal_repair_strategy("file1.py")
        
        # Strategy should have the correct structure
        self.assertIn("file", strategy)
        self.assertIn("strategy", strategy)
        self.assertIn("success_probability", strategy)
        self.assertIn("potential_side_effects", strategy)
        self.assertIn("recommendation", strategy)
        
        # File should be what we requested
        self.assertEqual(strategy["file"], "file1.py")
        
        # Success probability should be between 0 and 1
        self.assertTrue(0.0 <= strategy["success_probability"] <= 1.0)


if __name__ == '__main__':
    unittest.main()
