import unittest
import numpy as np
from pathlib import Path
import sys
import time

# Ensure triangulum_lx is in the path
sys.path.append(str(Path(__file__).parent.parent.parent))

from triangulum_lx.quantum.parallelization import (
    QuantumParallelizer,
    ParallelizationStrategy as ParallelizationMode,
)
from triangulum_lx.quantum.entanglement import EntangledState, QuantumBugSimulator, QuantumState
from tests.unit.test_quantum_entanglement import MockDependencyGraph


class TestQuantumParallelization(unittest.TestCase):
    """Test cases for the QuantumParallelizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.graph = MockDependencyGraph()
        
        # Create a simple dependency graph for testing
        self.f1 = self.graph.add_node("file1.py")
        self.f2 = self.graph.add_node("file2.py")
        self.f3 = self.graph.add_node("file3.py")
        
        self.graph.add_edge(self.f1, self.f2, 0.8)
        self.graph.add_edge(self.f2, self.f3, 0.5)
        
        # Create parallelizer
        self.parallelizer = QuantumParallelizer(max_parallel_tasks=2)
    
    def test_initialization(self):
        """Test that QuantumParallelizer initializes correctly."""
        self.assertEqual(self.parallelizer.max_parallel_tasks, 2)
        self.assertEqual(self.parallelizer.max_parallel_tasks, 2)
        self.assertIsNotNone(self.parallelizer.circuit_simulator)
        self.assertIsNotNone(self.parallelizer.speedup_estimator)
        self.assertIsNotNone(self.parallelizer.fallback_handler)
    
    
    
    
    
    


if __name__ == '__main__':
    unittest.main()
