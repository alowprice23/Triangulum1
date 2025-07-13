"""
Unit tests for triangulum_lx/core/state.py
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import unittest
from triangulum_lx.core.state import Phase, BugState

class TestState(unittest.TestCase):
    def test_phase_enum(self):
        """Test that Phase enum contains all required states"""
        expected_phases = ['WAIT', 'REPRO', 'PATCH', 'VERIFY', 'DONE', 'ESCALATE']
        for phase_name in expected_phases:
            self.assertTrue(hasattr(Phase, phase_name), f"Phase missing {phase_name}")

    def test_bug_state_creation(self):
        """Test BugState dataclass initialization"""
        bug = BugState(Phase.WAIT, 0, 0)
        self.assertEqual(bug.phase, Phase.WAIT)
        self.assertEqual(bug.timer, 0)
        self.assertEqual(bug.attempts, 0)

    def test_bug_state_immutability(self):
        """Test that BugState is immutable"""
        bug = BugState(Phase.WAIT, 0, 0)
        with self.assertRaises(Exception):
            bug.phase = Phase.REPRO

    def test_bug_state_equality(self):
        """Test that identical BugStates are equal"""
        bug1 = BugState(Phase.WAIT, 0, 0)
        bug2 = BugState(Phase.WAIT, 0, 0)
        bug3 = BugState(Phase.REPRO, 0, 0)

        self.assertEqual(bug1, bug2)
        self.assertNotEqual(bug1, bug3)

def test_basic_functionality():
    """Test basic functionality of the module."""
    # Placeholder test - should be expanded with actual functionality tests
    assert True

# Add more specific tests here based on the module's functionality
