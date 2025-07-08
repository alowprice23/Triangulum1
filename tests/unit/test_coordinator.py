import unittest
from unittest.mock import MagicMock, patch
from triangulum_lx.agents.coordinator import Coordinator

class TestCoordinator(unittest.TestCase):

    def setUp(self):
        """Set up a new Coordinator instance for each test."""
        self.mock_engine = MagicMock()
        self.mock_agents = {
            'code_analyzer': MagicMock(),
            'bug_finder': MagicMock(),
            'repair_agent': MagicMock()
        }
        self.coordinator = Coordinator(self.mock_engine, self.mock_agents)

    def test_coordinator_initialization(self):
        """Test that the coordinator and its components are initialized correctly."""
        self.assertIsInstance(self.coordinator, Coordinator)
        self.assertEqual(self.coordinator.engine, self.mock_engine)
        self.assertEqual(self.coordinator.agents, self.mock_agents)
        self.assertIsNotNone(self.coordinator.current_state)

    def test_dispatch_task(self):
        """Test that the coordinator can dispatch tasks to agents."""
        agent_id = 'code_analyzer'
        task = 'Analyze this code for bugs'
        
        self.coordinator.dispatch_task(agent_id, task)
        
        # Verify that the task was dispatched to the correct agent
        self.mock_agents[agent_id].execute_task.assert_called_once_with(task)

    def test_dispatch_task_unknown_agent(self):
        """Test that the coordinator handles unknown agents correctly."""
        agent_id = 'unknown_agent'
        task = 'This task should not be dispatched'
        
        with self.assertRaises(KeyError):
            self.coordinator.dispatch_task(agent_id, task)
        
        # Verify that no tasks were dispatched
        for agent in self.mock_agents.values():
            agent.execute_task.assert_not_called()

if __name__ == '__main__':
    unittest.main()
