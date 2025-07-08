"""
Integration tests for the TriangulumSystem class.

These tests verify that all components of the Triangulum system work together correctly.
"""

import os
import tempfile
import unittest
import json
import shutil
from unittest.mock import patch, MagicMock, ANY

from triangulum_integrated_system import TriangulumSystem

class TestTriangulumSystem(unittest.TestCase):
    """Integration tests for the TriangulumSystem class."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create a sample Python file for analysis
        self.create_test_files()
        
        # Create a temporary config file
        self.config_path = os.path.join(self.test_dir, "test_config.json")
        with open(self.config_path, "w") as f:
            json.dump({
                "system": {
                    "log_level": "INFO",
                    "data_directory": self.test_dir,
                    "relationship_path": os.path.join(self.test_dir, "relationships.json")
                },
                "monitoring": {
                    "enabled": True,
                    "interval": 10
                },
                "feedback": {
                    "enabled": True,
                    "db_path": os.path.join(self.test_dir, "feedback.db")
                }
            }, f)
        
        # Initialize the system with mocked components
        with patch("triangulum_lx.core.engine.TriangulumEngine"), \
             patch("triangulum_lx.monitoring.system_monitor.SystemMonitor"), \
             patch("triangulum_lx.tooling.code_relationship_analyzer.CodeRelationshipAnalyzer"), \
             patch("triangulum_lx.tooling.relationship_context_provider.RelationshipContextProvider"), \
             patch("triangulum_lx.human.feedback.FeedbackCollector"), \
             patch("triangulum_lx.tooling.repair.PatcherAgent"):
            self.system = TriangulumSystem(self.config_path)

    def tearDown(self):
        """Clean up test environment."""
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def create_test_files(self):
        """Create test Python files for analysis."""
        # Create a module directory
        module_dir = os.path.join(self.test_dir, "test_module")
        os.makedirs(module_dir)
        
        # Create __init__.py in the module directory
        with open(os.path.join(module_dir, "__init__.py"), "w") as f:
            f.write("# Module initialization\n")
        
        # Create a file with some imports and functions
        with open(os.path.join(module_dir, "main.py"), "w") as f:
            f.write("""
import os
import sys

def main():
    \"\"\"Main function.\"\"\"
    print("Hello, world!")

if __name__ == "__main__":
    main()
""")

    @patch("triangulum_lx.tooling.code_relationship_analyzer.CodeRelationshipAnalyzer")
    def test_analyze_code_relationships(self, MockAnalyzer):
        """Test analyzing code relationships."""
        # Set up the mock
        mock_analyzer_instance = MockAnalyzer.return_value
        mock_analyzer_instance.analyze_directory.return_value = {"file1": {"imports": []}}
        mock_analyzer_instance.save_relationships.return_value = None
        
        # Create a new system with the mocked analyzer
        with patch("triangulum_lx.core.engine.TriangulumEngine"), \
             patch("triangulum_lx.monitoring.system_monitor.SystemMonitor"), \
             patch("triangulum_lx.tooling.relationship_context_provider.RelationshipContextProvider"), \
             patch("triangulum_lx.human.feedback.FeedbackCollector"), \
             patch("triangulum_lx.tooling.repair.PatcherAgent"):
            system = TriangulumSystem(self.config_path)
            system.relationship_analyzer = mock_analyzer_instance
        
        # Analyze code relationships
        relationships = system.analyze_code_relationships(self.test_dir)
        
        # Check that the analyzer was called with the correct directory
        mock_analyzer_instance.analyze_directory.assert_called_once_with(self.test_dir)
        
        # Check that the relationships were saved
        mock_analyzer_instance.save_relationships.assert_called_once()
        
        # Check that the returned relationships match the mock
        self.assertEqual(relationships, {"file1": {"imports": []}})

    @patch("triangulum_lx.monitoring.system_monitor.SystemMonitor")
    def test_diagnose_system(self, MockMonitor):
        """Test diagnosing the system."""
        # Set up the mock
        mock_monitor_instance = MockMonitor.return_value
        mock_monitor_instance.check_health.return_value = {
            "status": "healthy",
            "metrics": {"cpu_percent": 50.0},
            "warnings": [],
            "errors": []
        }
        
        # Create a new system with the mocked monitor
        with patch("triangulum_lx.core.engine.TriangulumEngine"), \
             patch("triangulum_lx.tooling.code_relationship_analyzer.CodeRelationshipAnalyzer"), \
             patch("triangulum_lx.tooling.relationship_context_provider.RelationshipContextProvider"), \
             patch("triangulum_lx.human.feedback.FeedbackCollector"), \
             patch("triangulum_lx.tooling.repair.PatcherAgent"):
            system = TriangulumSystem(self.config_path)
            system.monitor = mock_monitor_instance
            system.relationship_provider = MagicMock()
            system.relationship_provider.relationships = {"file1": {"imports": []}}
        
        # Diagnose the system
        diagnosis = system.diagnose_system(self.test_dir)
        
        # Check that the monitor was called
        mock_monitor_instance.check_health.assert_called_once()
        
        # Check that the diagnosis contains the expected fields
        self.assertIn("timestamp", diagnosis)
        self.assertIn("target", diagnosis)
        self.assertIn("health_check", diagnosis)
        self.assertIn("detected_issues", diagnosis)
        self.assertIn("recommendations", diagnosis)
        
        # Check that the health check matches the mock
        self.assertEqual(diagnosis["health_check"]["status"], "healthy")

    @patch("triangulum_lx.monitoring.system_monitor.SystemMonitor")
    @patch("triangulum_lx.tooling.repair.PatcherAgent")
    def test_self_heal(self, MockPatcher, MockMonitor):
        """Test self-healing."""
        # Set up the mocks
        mock_monitor_instance = MockMonitor.return_value
        mock_monitor_instance.check_health.return_value = {
            "status": "warning",
            "metrics": {"cpu_percent": 90.0},
            "warnings": ["High CPU usage"],
            "errors": []
        }
        
        mock_patcher_instance = MockPatcher.return_value
        mock_patcher_instance.apply_fix.return_value = {"success": True}
        
        # Create a new system with the mocked components
        with patch("triangulum_lx.core.engine.TriangulumEngine"), \
             patch("triangulum_lx.tooling.code_relationship_analyzer.CodeRelationshipAnalyzer"), \
             patch("triangulum_lx.tooling.relationship_context_provider.RelationshipContextProvider"), \
             patch("triangulum_lx.human.feedback.FeedbackCollector"):
            system = TriangulumSystem(self.config_path)
            system.monitor = mock_monitor_instance
            system.patcher = mock_patcher_instance
            system.relationship_provider = MagicMock()
            system.relationship_provider.relationships = {"file1": {"imports": []}}
        
        # Define some test issues
        issues = [
            {
                "type": "structure",
                "severity": "medium",
                "description": "Missing expected directory: tests",
                "location": "tests"
            }
        ]
        
        # Self-heal
        healing = system.self_heal(self.test_dir, issues)
        
        # Check that the result contains the expected fields
        self.assertIn("timestamp", healing)
        self.assertIn("target", healing)
        self.assertIn("issues_addressed", healing)
        self.assertIn("successful_fixes", healing)
        self.assertIn("failed_fixes", healing)
        self.assertIn("actions_taken", healing)
        
        # Check that the issues were addressed
        self.assertEqual(healing["issues_addressed"], 1)

    @patch("triangulum_lx.core.engine.TriangulumEngine")
    def test_run_with_goal(self, MockEngine):
        """Test running with a goal."""
        # Set up the mock
        mock_engine_instance = MockEngine.return_value
        mock_engine_instance.run.return_value = None
        mock_engine_instance.get_status.return_value = {
            "session_id": "test_session",
            "running": False,
            "state": {"status": "completed"}
        }
        
        # Create a new system with the mocked engine
        with patch("triangulum_lx.monitoring.system_monitor.SystemMonitor"), \
             patch("triangulum_lx.tooling.code_relationship_analyzer.CodeRelationshipAnalyzer"), \
             patch("triangulum_lx.tooling.relationship_context_provider.RelationshipContextProvider"), \
             patch("triangulum_lx.human.feedback.FeedbackCollector"), \
             patch("triangulum_lx.tooling.repair.PatcherAgent"):
            system = TriangulumSystem(self.config_path)
            system.engine = mock_engine_instance
        
        # Create a test goal file
        goal_path = os.path.join(self.test_dir, "test_goal.yaml")
        with open(goal_path, "w") as f:
            f.write("id: test_goal\ndescription: Test goal")
        
        # Run with the goal
        results = system.run_with_goal(goal_path)
        
        # Check that the engine was called with the correct goal file
        mock_engine_instance.run.assert_called_once_with(goal_path)
        
        # Check that the result contains the expected fields
        self.assertIn("session_id", results)
        self.assertIn("goal_file", results)
        self.assertIn("engine_status", results)
        self.assertIn("completion_time", results)
        
        # Check that the goal file matches
        self.assertEqual(results["goal_file"], goal_path)

    @patch("triangulum_lx.core.engine.TriangulumEngine")
    def test_shutdown(self, MockEngine):
        """Test shutting down the system."""
        # Set up the mock
        mock_engine_instance = MockEngine.return_value
        mock_engine_instance.shutdown.return_value = None
        
        # Create a new system with the mocked engine
        with patch("triangulum_lx.monitoring.system_monitor.SystemMonitor"), \
             patch("triangulum_lx.tooling.code_relationship_analyzer.CodeRelationshipAnalyzer"), \
             patch("triangulum_lx.tooling.relationship_context_provider.RelationshipContextProvider"), \
             patch("triangulum_lx.human.feedback.FeedbackCollector"), \
             patch("triangulum_lx.tooling.repair.PatcherAgent"):
            system = TriangulumSystem(self.config_path)
            system.engine = mock_engine_instance
            system.relationship_provider = MagicMock()
        
        # Shutdown the system
        system.shutdown()
        
        # Check that the engine was shut down
        mock_engine_instance.shutdown.assert_called_once()
        
        # Check that the relationships were saved
        system.relationship_provider.save_relationships.assert_called_once()

    def test_integration_all_components(self):
        """Test that all components work together."""
        # Create mocks for all components
        mock_engine = MagicMock()
        mock_monitor = MagicMock()
        mock_analyzer = MagicMock()
        mock_relationship_provider = MagicMock()
        mock_feedback_collector = MagicMock()
        mock_patcher = MagicMock()
        
        # Set up returns
        mock_analyzer.analyze_directory.return_value = {"file1": {"imports": []}}
        mock_monitor.check_health.return_value = {
            "status": "healthy",
            "metrics": {"cpu_percent": 50.0},
            "warnings": [],
            "errors": []
        }
        mock_engine.get_status.return_value = {
            "session_id": "test_session",
            "running": False,
            "state": {"status": "completed"}
        }
        
        # Create a new system
        system = TriangulumSystem(self.config_path)
        
        # Replace components with mocks
        system.engine = mock_engine
        system.monitor = mock_monitor
        system.relationship_analyzer = mock_analyzer
        system.relationship_provider = mock_relationship_provider
        system.feedback_collector = mock_feedback_collector
        system.patcher = mock_patcher
        
        # Test full workflow
        
        # 1. Analyze code relationships
        relationships = system.analyze_code_relationships(self.test_dir)
        mock_analyzer.analyze_directory.assert_called_once_with(self.test_dir)
        
        # 2. Diagnose the system
        diagnosis = system.diagnose_system(self.test_dir)
        mock_monitor.check_health.assert_called_once()
        
        # 3. Self-heal
        issues = [
            {
                "type": "structure",
                "severity": "medium",
                "description": "Missing expected directory: tests",
                "location": "tests"
            }
        ]
        healing = system.self_heal(self.test_dir, issues)
        
        # 4. Run with a goal
        goal_path = os.path.join(self.test_dir, "test_goal.yaml")
        with open(goal_path, "w") as f:
            f.write("id: test_goal\ndescription: Test goal")
        
        results = system.run_with_goal(goal_path)
        mock_engine.run.assert_called_once_with(goal_path)
        
        # 5. Shutdown
        system.shutdown()
        mock_engine.shutdown.assert_called_once()
        mock_relationship_provider.save_relationships.assert_called_once()

if __name__ == "__main__":
    unittest.main()
