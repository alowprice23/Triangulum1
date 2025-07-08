"""Formal specification and verification components for Triangulum."""

from .ltl_properties import LTLFormula, LTLOperator, triangulum_properties, predicate_mapping
from .model_checker import TriangulumModelChecker
from .performance_guarantees import TriangulumBounds, DominoEffect, prove_triangulum_convergence

__all__ = [
    'LTLFormula', 'LTLOperator', 'triangulum_properties', 'predicate_mapping',
    'TriangulumModelChecker', 'TriangulumBounds', 'DominoEffect', 'prove_triangulum_convergence'
]
