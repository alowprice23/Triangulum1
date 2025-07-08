"""
Triangulum Quantum Module

This module provides quantum-inspired algorithms and simulations to accelerate
certain operations within the Triangulum system. It focuses on:

1. Quantum-inspired parallelization algorithms
2. Simulation of quantum speedup for classical tasks
3. Integration with classical computation components
4. Performance benchmarking for quantum vs. classical approaches

Note: This is an experimental module and does not require actual quantum hardware.
It uses quantum-inspired algorithms that can run on classical hardware.
"""

from triangulum_lx.quantum.parallelization import (
    QuantumParallelizer,
    QuantumCircuitSimulator,
    QuantumSpeedupEstimator,
    ClassicalFallbackHandler,
    ParallelizationStrategy,
    BenchmarkFramework
)

__all__ = [
    'QuantumParallelizer',
    'QuantumCircuitSimulator',
    'QuantumSpeedupEstimator',
    'ClassicalFallbackHandler',
    'ParallelizationStrategy',
    'BenchmarkFramework'
]
