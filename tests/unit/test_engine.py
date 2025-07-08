import unittest
from unittest.mock import MagicMock, patch
from triangulum_lx.core.engine import TriangulumEngine
import builtins
import sys

class TestTriangulumEngine(unittest.TestCase):

    def setUp(self):
        """Set up a new TriangulumEngine instance for each test."""
        # Create a patched Router class
        router_mock = MagicMock()
        router_instance = router_mock.return_value
        
        # Patch the import to return our mocked Router
        original_import = __import__
        def import_mock(name, *args, **kwargs):
            if name == 'triangulum_lx.agents.router' or name.endswith('router'):
                module = MagicMock()
                module.Router = router_mock
                return module
            return original_import(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=import_mock):
            self.engine = TriangulumEngine()

    def test_engine_initialization(self):
        """Test that the engine and its components are initialized correctly."""
        self.assertIsInstance(self.engine, TriangulumEngine)
        self.assertIsNotNone(self.engine.state)
        self.assertIsNotNone(self.engine.meta_agent)
        self.assertIsNotNone(self.engine.metrics)
        self.assertIsNotNone(self.engine.goal_loader)
        self.assertFalse(self.engine.running)

    @patch('triangulum_lx.core.engine.GoalLoader')
    @patch('triangulum_lx.goal.goal_loader.Path')
    def test_run_loads_goals(self, MockPath, MockGoalLoader):
        """Test that the run method correctly loads goals."""
        mock_path_instance = MockPath.return_value
        mock_path_instance.exists.return_value = True
        mock_path_instance.suffix = '.yaml'
        
        # We need to re-instantiate the engine to use the mocked GoalLoader
        # Create a patched Router class
        router_mock = MagicMock()
        router_instance = router_mock.return_value
        
        # Patch the import to return our mocked Router
        original_import = __import__
        def import_mock(name, *args, **kwargs):
            if name == 'triangulum_lx.agents.router' or name.endswith('router'):
                module = MagicMock()
                module.Router = router_mock
                return module
            return original_import(name, *args, **kwargs)
        
        with patch('builtins.open', new_callable=unittest.mock.mock_open, read_data='id: test'), \
             patch('builtins.__import__', side_effect=import_mock):
            engine = TriangulumEngine()
        
        mock_loader_instance = MockGoalLoader.return_value
        mock_loader_instance.load_from_file.return_value = [MagicMock()]
        
        # We don't want to run the full loop, so we'll patch process_goal
        with patch.object(engine, 'process_goal') as mock_process_goal:
            engine.run(goal_file='dummy_path.yaml')
            mock_loader_instance.load_from_file.assert_called_once_with('dummy_path.yaml')
            mock_process_goal.assert_called_once()

    def test_process_goal_calls_phases(self):
        """Test that process_goal calls the assessment, planning, acting, and verification phases."""
        mock_goal = MagicMock()
        
        with patch.object(self.engine, '_assess') as mock_assess, \
             patch.object(self.engine, '_plan') as mock_plan, \
             patch.object(self.engine, '_act') as mock_act, \
             patch.object(self.engine, '_verify') as mock_verify:
            
            self.engine.process_goal(mock_goal)
            
            mock_assess.assert_called_once_with(mock_goal)
            mock_plan.assert_called_once()
            mock_act.assert_called_once()
            mock_verify.assert_called_once()

if __name__ == '__main__':
    unittest.main()
