import unittest
import sys
from pathlib import Path

# Add parent directory to path to make imports work
sys.path.append(str(Path(__file__).resolve().parents[2]))

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

if __name__ == '__main__':
    unittest.main()
