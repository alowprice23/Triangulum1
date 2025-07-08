#!/usr/bin/env python3
"""
Comprehensive Quantum Acceleration Demo

This script demonstrates the advanced features of the quantum parallelization module,
including multiple parallelization strategies, circuit simulation, and benchmarking.
"""

import time
import random
import numpy as np
from typing import List, Dict, Tuple, Any
import matplotlib.pyplot as plt

from triangulum_lx.quantum import (
    QuantumParallelizer,
    QuantumCircuitSimulator,
    QuantumSpeedupEstimator,
    ClassicalFallbackHandler,
    ParallelizationStrategy,
    BenchmarkFramework
)

# ===== Example Problem 1: Matrix Multiplication =====
def matrix_multiply(matrices: Tuple[np.ndarray, np.ndarray]) -> np.ndarray:
    """
    Multiply two matrices.
    
    Args:
        matrices: Tuple containing two matrices to multiply
        
    Returns:
        Result of matrix multiplication
    """
    a, b = matrices
    return np.matmul(a, b)

def generate_matrix_data(size: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate random matrices for multiplication.
    
    Args:
        size: Size of the matrices (size x size)
        
    Returns:
        Tuple containing two random matrices
    """
    a = np.random.rand(size, size)
    b = np.random.rand(size, size)
    return a, b

# ===== Example Problem 2: Graph Traversal =====
def find_shortest_path(graph_data: Dict[str, Any]) -> List[str]:
    """
    Find the shortest path in a graph using Dijkstra's algorithm.
    
    Args:
        graph_data: Dictionary containing graph data
            - 'graph': Dict mapping nodes to {neighbor: distance} dicts
            - 'start': Start node
            - 'end': End node
            
    Returns:
        List of nodes representing the shortest path
    """
    graph = graph_data['graph']
    start = graph_data['start']
    end = graph_data['end']
    
    # Initialize distances with infinity for all nodes except start
    distances = {node: float('infinity') for node in graph}
    distances[start] = 0
    
    # Initialize previous nodes for path reconstruction
    previous = {node: None for node in graph}
    
    # Nodes to visit
    unvisited = list(graph.keys())
    
    while unvisited:
        # Find the unvisited node with the smallest distance
        current = min(unvisited, key=lambda node: distances[node])
        
        # If we've reached the end node or if the smallest distance is infinity
        if current == end or distances[current] == float('infinity'):
            break
            
        # Remove the current node from unvisited
        unvisited.remove(current)
        
        # Check all neighbors of the current node
        for neighbor, distance in graph[current].items():
            # Calculate the distance through the current node
            new_distance = distances[current] + distance
            
            # If this path is shorter than the previously known path
            if new_distance < distances[neighbor]:
                # Update the distance and previous node
                distances[neighbor] = new_distance
                previous[neighbor] = current
    
    # Reconstruct the path
    path = []
    current = end
    
    while current:
        path.append(current)
        current = previous[current]
        
    # Reverse the path to get start -> end
    path.reverse()
    
    # If the end node is not reachable, return an empty path
    if path[0] != start:
        return []
        
    return path

def generate_graph_data(size: int) -> Dict[str, Any]:
    """
    Generate a random graph for shortest path finding.
    
    Args:
        size: Number of nodes in the graph
        
    Returns:
        Dictionary containing graph data
    """
    # Create nodes
    nodes = [f"node_{i}" for i in range(size)]
    
    # Create random edges
    graph = {node: {} for node in nodes}
    
    # Ensure the graph is connected
    for i in range(size - 1):
        # Connect each node to the next one
        node1 = nodes[i]
        node2 = nodes[i + 1]
        distance = random.randint(1, 10)
        graph[node1][node2] = distance
        graph[node2][node1] = distance
    
    # Add some random edges
    num_extra_edges = size * 2
    for _ in range(num_extra_edges):
        node1 = random.choice(nodes)
        node2 = random.choice(nodes)
        
        # Avoid self-loops and duplicate edges
        if node1 != node2 and node2 not in graph[node1]:
            distance = random.randint(1, 10)
            graph[node1][node2] = distance
            graph[node2][node1] = distance
    
    # Select random start and end nodes
    start = nodes[0]
    end = nodes[-1]
    
    return {
        'graph': graph,
        'start': start,
        'end': end
    }

# ===== Quantum Circuit Demonstration =====
def demonstrate_quantum_circuit():
    """Demonstrate the quantum circuit simulator."""
    print("\n" + "=" * 80)
    print("QUANTUM CIRCUIT SIMULATION DEMONSTRATION")
    print("=" * 80)
    
    # Create a quantum circuit with 3 qubits
    print("\nCreating a 3-qubit quantum circuit...")
    circuit = QuantumCircuitSimulator(3)
    
    # Apply Hadamard gates to create superposition
    print("Applying Hadamard gates to all qubits (creating superposition)...")
    circuit.hadamard(0).hadamard(1).hadamard(2)
    
    # Get the state vector before measurement
    state_vector = circuit.get_state_vector()
    print("\nState vector before measurement:")
    for i, amplitude in enumerate(state_vector):
        if abs(amplitude) > 1e-10:  # Only show non-zero amplitudes
            # Convert index to binary for qubit state representation
            binary = format(i, f'0{circuit.num_qubits}b')
            print(f"|{binary}⟩: {amplitude:.4f}")
    
    # Run the circuit and measure
    print("\nMeasuring the quantum state...")
    result, probabilities = circuit.run()
    
    # Display the result
    binary_result = format(result, f'0{circuit.num_qubits}b')
    print(f"Measured state: |{binary_result}⟩")
    
    print("\nProbability distribution of all states:")
    for state, prob in probabilities.items():
        binary = format(state, f'0{circuit.num_qubits}b')
        print(f"|{binary}⟩: {prob:.4f}")
    
    # Create a more complex circuit with entanglement
    print("\nCreating a circuit with entanglement (Bell state)...")
    bell_circuit = QuantumCircuitSimulator(2)
    
    # Create a Bell state (entangled state)
    bell_circuit.hadamard(0).cnot(0, 1)
    
    # Get the state vector
    bell_state = bell_circuit.get_state_vector()
    print("\nBell state vector:")
    for i, amplitude in enumerate(bell_state):
        if abs(amplitude) > 1e-10:
            binary = format(i, f'0{bell_circuit.num_qubits}b')
            print(f"|{binary}⟩: {amplitude:.4f}")
    
    # Measure multiple times to demonstrate probabilistic nature
    print("\nPerforming multiple measurements of the Bell state...")
    measurements = {}
    
    for i in range(10):
        # Reset and recreate the Bell state for each measurement
        bell_circuit = QuantumCircuitSimulator(2)
        bell_circuit.hadamard(0).cnot(0, 1)
        
        # Measure
        result, _ = bell_circuit.run()
        binary = format(result, f'0{bell_circuit.num_qubits}b')
        
        # Count occurrences
        measurements[binary] = measurements.get(binary, 0) + 1
    
    print("\nMeasurement results from 10 runs:")
    for state, count in measurements.items():
        print(f"|{state}⟩: {count} times ({count/10:.2f})")
    
    print("\nQuantum circuit demonstration completed!")

# ===== Benchmark Different Strategies =====
def benchmark_strategies():
    """Benchmark different quantum parallelization strategies."""
    print("\n" + "=" * 80)
    print("QUANTUM PARALLELIZATION STRATEGY BENCHMARKS")
    print("=" * 80)
    
    # Initialize components
    parallelizer = QuantumParallelizer(num_qubits=10)
    benchmark = BenchmarkFramework(parallelizer)
    estimator = QuantumSpeedupEstimator()
    
    # Problem types to benchmark
    problems = [
        {
            "name": "Matrix Multiplication",
            "function": matrix_multiply,
            "data_generator": generate_matrix_data,
            "sizes": [5, 10, 20],
            "problem_type": "simulation"
        },
        {
            "name": "Graph Shortest Path",
            "function": find_shortest_path,
            "data_generator": generate_graph_data,
            "sizes": [10, 20, 30],
            "problem_type": "search"
        }
    ]
    
    # Strategies to benchmark
    strategies = [
        ParallelizationStrategy.QUANTUM_AMPLITUDE_AMPLIFICATION,
        ParallelizationStrategy.QUANTUM_WALK,
        ParallelizationStrategy.QUANTUM_PHASE_ESTIMATION,
        ParallelizationStrategy.CLASSICAL_FALLBACK
    ]
    
    # Run benchmarks for each problem
    for problem in problems:
        print(f"\nBenchmarking {problem['name']}...")
        
        # Generate test data
        test_data = []
        test_sizes = []
        
        for size in problem['sizes']:
            data = problem['data_generator'](size)
            test_data.append(data)
            test_sizes.append(size)
            
        # Get strategy recommendation
        recommended_strategy = estimator.recommend_strategy(
            max(problem['sizes']),
            problem['problem_type']
        )
        
        print(f"Recommended strategy: {recommended_strategy.name}")
        
        # Run benchmarks
        results = benchmark.benchmark_batch(
            problem['function'],
            test_data,
            test_sizes,
            strategies
        )
        
        # Display results
        print(f"\nResults for {problem['name']}:")
        
        # Group results by size and strategy
        by_size_strategy = {}
        for result in results:
            key = (result.problem_size, result.strategy)
            by_size_strategy[key] = result
        
        # Print results in a table format
        print(f"{'Size':<6} {'Strategy':<30} {'Classical (s)':<15} {'Quantum (s)':<15} {'Speedup':<10} {'Match':<6}")
        print("-" * 85)
        
        for size in problem['sizes']:
            for strategy in strategies:
                key = (size, strategy)
                if key in by_size_strategy:
                    result = by_size_strategy[key]
                    print(f"{size:<6} {strategy.name:<30} {result.classical_time:<15.6f} {result.quantum_time:<15.6f} {result.speedup_factor:<10.2f} {result.results_match}")
    
    # Generate overall report
    print("\nGenerating overall benchmark report...")
    report = benchmark.generate_report()
    
    print("\nOverall Benchmark Summary:")
    print(f"  Total benchmarks: {report['total_benchmarks']}")
    print(f"  Successful benchmarks: {report['successful_benchmarks']}")
    print(f"  Result match rate: {report['result_match_rate']:.2f}")
    print(f"  Average speedup: {report['average_speedup']:.2f}x")
    print(f"  Maximum speedup: {report['max_speedup']:.2f}x")
    
    print("\nStrategy-specific results:")
    for strategy_name, stats in report['by_strategy'].items():
        print(f"  {strategy_name}:")
        print(f"    Average speedup: {stats['average_speedup']:.2f}x")
        print(f"    Maximum speedup: {stats['max_speedup']:.2f}x")
        print(f"    Result match rate: {stats['result_match_rate']:.2f}")
    
    print("\nStrategy benchmarking completed!")

# ===== Main Demo Function =====
def run_demo():
    """Run the comprehensive quantum acceleration demo."""
    print("=" * 80)
    print("TRIANGULUM QUANTUM ACCELERATION - COMPREHENSIVE DEMO")
    print("=" * 80)
    print("\nThis demo showcases the quantum parallelization capabilities of Triangulum,")
    print("including circuit simulation, multiple parallelization strategies, and")
    print("performance benchmarking against classical approaches.")
    
    # Demonstrate quantum circuit simulation
    demonstrate_quantum_circuit()
    
    # Benchmark different parallelization strategies
    benchmark_strategies()
    
    print("\n" + "=" * 80)
    print("QUANTUM ACCELERATION DEMO COMPLETED SUCCESSFULLY")
    print("=" * 80)

if __name__ == "__main__":
    run_demo()
