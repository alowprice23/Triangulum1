import unittest
from unittest.mock import MagicMock
import sys
from pathlib import Path

# Add parent directory to path to make imports work
sys.path.append(str(Path(__file__).resolve().parents[2]))

from triangulum_lx.core.state import Phase, BugState
from triangulum_lx.core.transition import step

class TestTransition(unittest.TestCase):
    async def test_wait_to_repro(self):
        """Test transition from WAIT to REPRO when agents available"""
        bug = BugState(Phase.WAIT, 0, 0)
        free_agents = 3  # Exactly enough agents
        
        new_bug, delta = await step(bug, free_agents, MagicMock())
        
        self.assertEqual(new_bug.phase, Phase.REPRO)
        self.assertEqual(new_bug.timer, 3)
        self.assertEqual(new_bug.attempts, 0)
        self.assertEqual(delta, -3)  # 3 agents should be consumed
    
    async def test_wait_stays_waiting(self):
        """Test WAIT state remains when not enough agents"""
        bug = BugState(Phase.WAIT, 0, 0)
        free_agents = 2  # Not enough agents
        
        new_bug, delta = await step(bug, free_agents, MagicMock())
        
        self.assertEqual(new_bug.phase, Phase.WAIT)
        self.assertEqual(delta, 0)  # No agents consumed
    
    async def test_timer_countdown(self):
        """Test timer countdown for active phases"""
        for phase in [Phase.REPRO, Phase.PATCH, Phase.VERIFY]:
            bug = BugState(phase, 3, 0)
            new_bug, delta = await step(bug, 0, MagicMock())  # Free agents irrelevant here
            
            self.assertEqual(new_bug.phase, phase)
            self.assertEqual(new_bug.timer, 2)  # Decreased by 1
            self.assertEqual(delta, 0)  # No agents consumed or released
    
    async def test_phase_transitions(self):
        """Test transitions between phases when timer reaches zero"""
        # REPRO -> PATCH
        bug = BugState(Phase.REPRO, 0, 0)
        new_bug, _ = await step(bug, 0, MagicMock())
        self.assertEqual(new_bug.phase, Phase.PATCH)
        self.assertEqual(new_bug.timer, 3)
        
        # PATCH -> VERIFY
        bug = BugState(Phase.PATCH, 0, 0)
        new_bug, _ = await step(bug, 0, MagicMock())
        self.assertEqual(new_bug.phase, Phase.VERIFY)
        self.assertEqual(new_bug.timer, 3)
        
        # VERIFY -> PATCH (first attempt fails)
        bug = BugState(Phase.VERIFY, 0, 0)
        new_bug, _ = await step(bug, 0, MagicMock())
        self.assertEqual(new_bug.phase, Phase.PATCH)
        self.assertEqual(new_bug.attempts, 1)
        
        # VERIFY -> DONE (second attempt succeeds)
        bug = BugState(Phase.VERIFY, 0, 1)
        new_bug, delta = await step(bug, 0, MagicMock())
        self.assertEqual(new_bug.phase, Phase.DONE)
        self.assertEqual(delta, 3)  # 3 agents released
    
    async def test_terminal_states(self):
        """Test terminal states don't change"""
        # DONE state
        bug = BugState(Phase.DONE, 0, 0)
        new_bug, delta = await step(bug, 0, MagicMock())
        self.assertEqual(new_bug.phase, Phase.DONE)
        self.assertEqual(delta, 0)
        
        # ESCALATE state
        bug = BugState(Phase.ESCALATE, 0, 0)
        new_bug, delta = await step(bug, 0, MagicMock())
        self.assertEqual(new_bug.phase, Phase.ESCALATE)
        self.assertEqual(delta, 0)

if __name__ == '__main__':
    unittest.main()
