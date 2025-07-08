import unittest
import numpy as np
from pathlib import Path
import sys
import time

# Ensure triangulum_lx is in the path
sys.path.append(str(Path(__file__).parent.parent.parent))

from triangulum_lx.quantum.parallelization import (
    QuantumParallelizer,
    ParallelizationMode,
    RepairTask,
    parallel_repair_example
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
        
        # Create parallelizer in different modes
        self.quantum_parallelizer = QuantumParallelizer(max_workers=2, mode=ParallelizationMode.QUANTUM)
        self.classical_parallelizer = QuantumParallelizer(max_workers=2, mode=ParallelizationMode.CLASSICAL)
        self.hybrid_parallelizer = QuantumParallelizer(max_workers=2, mode=ParallelizationMode.HYBRID)
    
    def test_initialization(self):
        """Test that QuantumParallelizer initializes correctly."""
        self.assertEqual(self.quantum_parallelizer.max_workers, 2)
        self.assertEqual(self.quantum_parallelizer.mode, ParallelizationMode.QUANTUM)
        self.assertEqual(len(self.quantum_parallelizer.tasks), 0)
        self.assertIsNone(self.quantum_parallelizer.simulator)
        self.assertIsNone(self.quantum_parallelizer.dependency_graph)
    
    def test_set_dependency_graph(self):
        """Test setting the dependency graph."""
        self.quantum_parallelizer.set_dependency_graph(self.graph)
        
        # Should initialize the simulator
        self.assertIsNotNone(self.quantum_parallelizer.simulator)
        self.assertEqual(self.quantum_parallelizer.dependency_graph, self.graph)
        
        # Simulator should be initialized from the graph
        self.assertEqual(len(self.quantum_parallelizer.simulator.entangled_state.components), 3)
    
    def test_add_task(self):
        """Test adding tasks to the parallelizer."""
        self.quantum_parallelizer.set_dependency_graph(self.graph)
        
        # Calculate bug probabilities
        self.quantum_parallelizer.simulator.calculate_bug_probabilities()
        
        # Add tasks
        self.quantum_parallelizer.add_task("file1.py", "syntax_error")
        self.quantum_parallelizer.add_task("file2.py", "logical_error")
        
        # Should have added the tasks
        self.assertEqual(len(self.quantum_parallelizer.tasks), 2)
        
        # Tasks should have the correct file paths and bug types
        self.assertEqual(self.quantum_parallelizer.tasks[0].file_path, "file1.py")
        self.assertEqual(self.quantum_parallelizer.tasks[0].bug_type, "syntax_error")
        self.assertEqual(self.quantum_parallelizer.tasks[1].file_path, "file2.py")
        self.assertEqual(self.quantum_parallelizer.tasks[1].bug_type, "logical_error")
        
        # Tasks should have dependencies
        self.assertIn("file2.py", self.quantum_parallelizer.tasks[0].dependencies)
    
    def test_compute_repair_strategies(self):
        """Test computing repair strategies."""
        self.quantum_parallelizer.set_dependency_graph(self.graph)
        
        # Add tasks
        self.quantum_parallelizer.add_task("file1.py")
        self.quantum_parallelizer.add_task("file2.py")
        
        # Compute repair strategies
        self.quantum_parallelizer.compute_repair_strategies()
        
        # Should have repair strategies for each task
        for task in self.quantum_parallelizer.tasks:
            self.assertTrue(len(task.repair_strategies) > 0)
            
            # Should have selected a strategy
            self.assertIsNotNone(task.selected_strategy)
            
            # Selected strategy should have the highest success probability
            max_prob = max(s["success_probability"] for s in task.repair_strategies)
            self.assertEqual(task.selected_strategy["success_probability"], max_prob)
    
    def test_prioritize_tasks(self):
        """Test prioritizing tasks."""
        self.quantum_parallelizer.set_dependency_graph(self.graph)
        
        # Add tasks with different priorities
        self.quantum_parallelizer.add_task("file1.py")
        self.quantum_parallelizer.tasks[0].priority = 0.3
        
        self.quantum_parallelizer.add_task("file2.py")
        self.quantum_parallelizer.tasks[1].priority = 0.7
        
        # Add dependencies
        self.quantum_parallelizer.tasks[0].dependencies = ["file2.py"]
        self.quantum_parallelizer.tasks[1].dependencies = ["file3.py"]
        
        # Compute repair strategies to get selected strategies
        self.quantum_parallelizer.compute_repair_strategies()
        
        # Prioritize tasks
        self.quantum_parallelizer.prioritize_tasks()
        
        # Tasks should be sorted by priority (high to low)
        self.assertEqual(self.quantum_parallelizer.tasks[0].file_path, "file2.py")
        self.assertEqual(self.quantum_parallelizer.tasks[1].file_path, "file1.py")
        
        # Priorities should be adjusted based on quantum interference
        for task in self.quantum_parallelizer.tasks:
            self.assertTrue(0.0 <= task.priority <= 1.0)
    
    def test_execute_parallel_repairs(self):
        """Test executing repairs in parallel."""
        self.quantum_parallelizer.set_dependency_graph(self.graph)
        
        # Add tasks
        self.quantum_parallelizer.add_task("file1.py")
        self.quantum_parallelizer.add_task("file2.py")
        self.quantum_parallelizer.add_task("file3.py")
        
        # Compute repair strategies
        self.quantum_parallelizer.compute_repair_strategies()
        
        # Execute repairs in parallel
        results = self.quantum_parallelizer.execute_parallel_repairs(parallel_repair_example)
        
        # Should have results for all tasks
        self.assertEqual(len(results), 3)
        
        # Each result should have the correct structure
        for result in results:
            self.assertIn("file_path", result)
            self.assertIn("success", result)
            self.assertIn("priority", result)
            
            # File path should match one of the tasks
            self.assertIn(result["file_path"], ["file1.py", "file2.py", "file3.py"])
            
            # Success should be a boolean
            self.assertIsInstance(result["success"], bool)
            
            # Priority should be between 0 and 1
            self.assertTrue(0.0 <= result["priority"] <= 1.0)
            
            # If successful, should have details
            if result["success"]:
                self.assertIn("details", result)
                self.assertIn("fixes_applied", result["details"])
                self.assertIn("execution_time", result["details"])
    
    def test_quantum_vs_classical_mode(self):
        """Test differences between quantum and classical modes."""
        # Set up both parallelizers
        self.quantum_parallelizer.set_dependency_graph(self.graph)
        self.classical_parallelizer.set_dependency_graph(self.graph)
        
        # Add identical tasks to both
        for parallelizer in [self.quantum_parallelizer, self.classical_parallelizer]:
            parallelizer.add_task("file1.py")
            parallelizer.add_task("file2.py")
            parallelizer.compute_repair_strategies()
        
        # Set identical initial priorities
        for i in range(2):
            self.quantum_parallelizer.tasks[i].priority = 0.5
            self.classical_parallelizer.tasks[i].priority = 0.5
        
        # Prioritize tasks in both modes
        self.quantum_parallelizer.prioritize_tasks()
        self.classical_parallelizer.prioritize_tasks()
        
        # In quantum mode, priorities should be adjusted by quantum interference
        # In classical mode, priorities should remain unchanged
        quantum_priorities = [task.priority for task in self.quantum_parallelizer.tasks]
        classical_priorities = [task.priority for task in self.classical_parallelizer.tasks]
        
        # At least one of the priorities should differ between modes
        self.assertNotEqual(quantum_priorities, classical_priorities)
    
    def test_parallel_repair_example(self):
        """Test the example repair function."""
        # Create a task with a selected strategy
        task = RepairTask(file_path="file1.py", bug_type="syntax_error")
        task.dependencies = ["file2.py", "file3.py"]
        task.selected_strategy = {"id": 1, "success_probability": 0.8}
        
        # Execute the repair function
        result = parallel_repair_example(task)
        
        # Result should have the expected structure
        self.assertIn("success", result)
        self.assertIn("fixes_applied", result)
        self.assertIn("affected_files", result)
        self.assertIn("execution_time", result)
        self.assertIn("strategy_used", result)
        
        # Strategy used should match the selected strategy
        self.assertEqual(result["strategy_used"], 1)
        
        # If successful, should have fixes applied
        if result["success"]:
            self.assertEqual(result["fixes_applied"], 1)
        else:
            self.assertEqual(result["fixes_applied"], 0)


if __name__ == '__main__':
    unittest.main()
