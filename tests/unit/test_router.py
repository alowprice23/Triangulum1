import unittest
from unittest.mock import MagicMock, patch
from triangulum_lx.agents.router import Router

class TestRouter(unittest.TestCase):

    def setUp(self):
        """Set up a new Router instance for each test."""
        self.mock_engine = MagicMock()
        self.router = Router(self.mock_engine)

    def test_router_initialization(self):
        """Test that the router is initialized correctly."""
        self.assertIsInstance(self.router, Router)
        self.assertEqual(self.router.engine, self.mock_engine)

    def test_route_code_analysis_task(self):
        """Test that code analysis tasks are routed to the code analyzer."""
        task = "Analyze this code for bugs and inefficiencies"
        
        result = self.router.route(task)
        
        self.assertEqual(result, "CODE_ANALYZER")

    def test_route_bug_fixing_task(self):
        """Test that bug fixing tasks are routed to the bug fixer."""
        task = "Fix the bug in the event loop implementation"
        
        result = self.router.route(task)
        
        self.assertEqual(result, "BUG_FIXER")

    def test_route_refactoring_task(self):
        """Test that refactoring tasks are routed to the refactorer."""
        task = "Refactor this code to improve maintainability"
        
        result = self.router.route(task)
        
        self.assertEqual(result, "REFACTORER")

    def test_route_unknown_task(self):
        """Test that unknown tasks are routed to the default agent."""
        task = "This is a completely unrelated task"
        
        result = self.router.route(task)
        
        self.assertEqual(result, "GENERAL_AGENT")

if __name__ == '__main__':
    unittest.main()
