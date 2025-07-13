import unittest
import sys
import os
import asyncio
from pathlib import Path

# Add parent directory to path to make imports work
sys.path.append(str(Path(__file__).resolve().parents[2]))

from triangulum_lx.core.state import Phase, BugState
from triangulum_lx.core.engine import TriangulumEngine
from triangulum_lx.core.monitor import EngineMonitor
from triangulum_lx.agents.orchestrator_agent import OrchestratorAgent as AutoGenCoordinator

class MockBug:
    """
    Simulates a bug for testing the Triangulum system.
    """
    def __init__(self, name, severity=3):
        self.name = name
        self.severity = severity
        self.age_ticks = 0
        self.state = BugState(Phase.WAIT, 0, 0)
        
    def increment_age(self):
        self.age_ticks += 1
        
    def __repr__(self):
        return f"Bug({self.name}, sev={self.severity}, state={self.state.phase.name})"


class TestSimpleBug(unittest.TestCase):
    def setUp(self):
        """Set up the test environment with a project structure"""
        self.test_dir = Path("test_project")
        if not self.test_dir.exists():
            self.test_dir.mkdir()
            
        # Create a simple test project
        self._create_test_project()
        
        # Initialize engine and monitor
        self.engine = TriangulumEngine()
        self.monitor = EngineMonitor(self.engine)
        self.engine.monitor = self.monitor
        
        # Initialize coordinator with mocks
        self.coordinator = self._setup_mock_coordinator()
        
    def tearDown(self):
        """Clean up test files"""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def _create_test_project(self):
        """Create a simple test project structure"""
        # Main module
        main_path = self.test_dir / "main.js"
        main_path.write_text("""
            const { processData } = require('./processor');
            
            function run() {
                const data = [1, 2, 3, null, 5];
                return processData(data);
            }
            
            module.exports = { run };
        """)
        
        # Processor module with a bug
        processor_path = self.test_dir / "processor.js"
        processor_path.write_text("""
            function processData(items) {
                // BUG: Doesn't check for null values
                return items.map(item => item * 2);
            }
            
            module.exports = { processData };
        """)
        
        # Test file
        test_path = self.test_dir / "test.js"
        test_path.write_text("""
            const { run } = require('./main');
            
            function test() {
                const result = run();
                console.log('Test result:', result);
            }
            
            test();
        """)
    
    def _setup_mock_coordinator(self):
        """Set up a mock coordinator that simulates agent interactions"""
        class MockCoordinator:
            def __init__(self, engine):
                self.engine = engine
                self.bugs_fixed = 0
                self.patches_applied = []
                
            async def process_bug(self, bug):
                # Simulate the bug going through the triangle phases
                while bug.state.phase != Phase.DONE:
                    # Advance state based on engine rules
                    new_state, delta = step(bug.state, self.engine.free_agents)
                    bug.state = new_state
                    self.engine.free_agents += delta
                    
                    # Simulate agent work
                    await asyncio.sleep(0.01)
                    
                    # For VERIFY phase with first attempt
                    if bug.state.phase == Phase.PATCH and bug.state.attempts == 1:
                        # Record a patch was created
                        patch = f"Patch for {bug.name}: Added null check"
                        self.patches_applied.append(patch)
                    
                    # Update engine state
                    self.engine.tick_no += 1
                    self.engine.monitor.after_tick()
                
                self.bugs_fixed += 1
                return True
        
        return MockCoordinator(self.engine)
    
    def test_bug_resolution_flow(self):
        """Test that a simple bug can be resolved through the triangle phases"""
        # Create a test bug
        bug = MockBug("NullPointerBug", severity=4)
        
        # Process the bug synchronously
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.coordinator.process_bug(bug))
        
        # Verify the bug was fixed
        self.assertTrue(result)
        self.assertEqual(self.coordinator.bugs_fixed, 1)
        self.assertEqual(len(self.coordinator.patches_applied), 1)
        self.assertIn("Added null check", self.coordinator.patches_applied[0])
        
        # Verify the bug state
        self.assertEqual(bug.state.phase, Phase.DONE)


if __name__ == '__main__':
    unittest.main()
