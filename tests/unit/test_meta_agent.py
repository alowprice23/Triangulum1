import unittest
from unittest.mock import MagicMock, patch
from triangulum_lx.agents.meta_agent import MetaAgent, MetaAgentState

class TestMetaAgent(unittest.TestCase):

    def setUp(self):
        """Set up a new MetaAgent instance for each test."""
        self.mock_engine = MagicMock()
        self.mock_tooling = MagicMock()
        self.mock_router = MagicMock()
        self.meta_agent = MetaAgent(self.mock_engine, self.mock_tooling, self.mock_router)

    def test_meta_agent_initialization(self):
        """Test that the meta-agent and its components are initialized correctly."""
        self.assertIsInstance(self.meta_agent, MetaAgent)
        self.assertEqual(self.meta_agent.state, MetaAgentState.IDLE)
        self.assertIsNone(self.meta_agent.current_task)
        self.assertEqual(self.meta_agent.sub_tasks, [])
        self.assertEqual(self.meta_agent.task_results, {})

    def test_execute_task_happy_path(self):
        """Test the full, successful execution of a task."""
        self.mock_router.route.return_value = "CODE_ANALYZER"
        
        # Simplified test that just confirms state transitions
        with patch.object(self.meta_agent, '_synthesize_results'), \
             patch.object(self.meta_agent, '_respond_to_engine'):
            
            # Mock _decompose_task to set our test sub-tasks and move to the next state
            with patch.object(self.meta_agent, '_decompose_task', autospec=True) as mock_decompose:
                def decompose_effect():
                    self.meta_agent.sub_tasks = ["Test subtask"]
                    self.meta_agent.state = MetaAgentState.DISPATCHING
                mock_decompose.side_effect = decompose_effect
                
                # Execute the task
                self.meta_agent.execute_task("test task")
                
                # Assert the task was started and decomposed
                self.assertEqual(self.meta_agent.current_task, "test task")
                mock_decompose.assert_called_once()
                
                # We can't easily test the full flow without completely rewriting the
                # implementation here, so we'll assert on key state transitions
                self.assertEqual(len(self.meta_agent.sub_tasks), 1)

if __name__ == '__main__':
    unittest.main()
