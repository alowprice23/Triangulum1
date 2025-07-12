"""
Advanced verification system for bug fixes and code improvements.

This package provides a comprehensive verification system for validating
bug fixes and code improvements, including test generation, environment setup,
property-based testing, and CI integration.
"""

__version__ = '1.0.0'

from .core import TestGenerator
from .metrics import MetricsCollector as VerificationMetrics
from .adaptive import AdaptiveVerifier
from .ci import CIReporter, CIVerifier
