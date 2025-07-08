#!/usr/bin/env python3
"""
Simple Quantum Acceleration Demo

This script demonstrates the basic usage of the quantum parallelization module
with a simple search problem to showcase the potential speedup.
"""

import time
import random
import numpy as np
from typing import List, Tuple

from triangulum_lx.quantum import (
    QuantumParallelizer,
    ParallelizationStrategy,
    BenchmarkFramework
)

def find_target_value(data: List[int], target: int) -> int:
    """Find the index of a target value in a list."""
    for i, value in enumerate(data):
        if value == target:
            return i
    return -1

def generate_test_data(size: int) -> Tuple[List[int], int]:
    """Generate test data for the search problem."""
    data = list(range(size))
    random.shuffle(data)
    target_index = random.randint(0, size - 1)
    target_value = data[target_index]
    
    return data, target_value

def run_simple_demo():
    """Run a simple demonstration of quantum acceleration."""
    print("=" * 80)
    print("TRIANGULUM QUANTUM ACCELERATION - SIMPLE DEMO")
    print("=" * 80)
    
    # Initialize quantum parallelizer
    parallelizer = QuantumParallelizer(num_qubits=10)
    benchmark = BenchmarkFramework(parallelizer)
    
    # Test with different problem sizes
    problem_sizes = [10, 100, 1000]
    strategies = [
        ParallelizationStrategy.QUANTUM_AMPLITUDE_AMPLIFICATION,
        ParallelizationStrategy.CLASSICAL_FALLBACK
    ]
    
    print("\nRunning benchmarks with different problem sizes...")
    
    # Prepare data for benchmarking
    test_data = []
    test_sizes = []
    
    for size in problem_sizes:
        data, target = generate_test_data(size)
        test_data.append((data, target))
        test_sizes.append(size)
        
    # Run benchmarks
    for i, ((data, target), size) in enumerate(zip(test_data, test_sizes)):
        print(f"\nProblem size: {size}")
        
        for strategy in strategies:
            print(f"  Strategy: {strategy.name}")
            
            # Create a closure for the search function
            search_func = lambda x: find_target_value(x[0], x[1])
            
            # Benchmark the function
            result = benchmark.benchmark_function(
                search_func, (data, target), size, strategy,
                task_id=f"search_{size}_{strategy.name}"
            )
            
            print(f"    Classical time: {result.classical_time:.6f} seconds")
            print(f"    Quantum time: {result.quantum_time:.6f} seconds")
            print(f"    Speedup factor: {result.speedup_factor:.2f}x")
            print(f"    Results match: {result.results_match}")
    
    # Generate report
    print("\nGenerating benchmark report...")
    report = benchmark.generate_report()
    
    print("\nBenchmark Summary:")
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
    
    print("\nDemo completed successfully!")

if __name__ == "__main__":
    run_simple_demo()
