"""
Integration tests for the learning capabilities of Triangulum.

These tests validate the integration of the learning components with the
Triangulum engine and other systems.
"""

import os
import sys
import unittest
import tempfile
import json
import shutil
from pathlib import Path
from unittest import mock

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from triangulum_lx.core.learning_enabled_engine import LearningEnabledEngine
from triangulum_lx.core.engine import TriangulumEngine
from triangulum_lx.core.engine_learning_integration import (
    integrate_learning_with_engine,
    run_improvement_cycle,
    get_learning_report
)
from triangulum_lx.core.engine_event_extension import EventHandlerMixin, extend_engine_with_events


class MockEngine(EventHandlerMixin):
    """Mock engine for testing."""
    
    def __init__(self, config=None):
        super().__init__()
        self.config = config or {}
        self.context = {}
    
    def repair_file(self, file_path, **kwargs):
        return {"success": True, "file_path": file_path}
    
    def repair_folder(self, folder_path, **kwargs):
        return {"success": True, "folder_path": folder_path}
    
    def get_status(self):
        return {"running": True}


class TestEngineLearningIntegration(unittest.TestCase):
    """Test the integration of the learning system with the engine."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.engine = MockEngine({"test": "config"})
        
        # Set up learning configuration
        self.learning_config = {
            "learning_enabled": True,
            "learning_storage_path": self.temp_dir,
            "improvement_interval": 60,
            "min_episodes_for_learning": 3
        }
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_integrate_learning_with_engine(self):
        """Test integrating learning with the engine."""
        from triangulum_lx.core.learning_manager import LearningManager
        
        # Create learning manager
        manager = LearningManager(self.learning_config)
        
        # Integrate with engine
        integrate_learning_with_engine(self.engine, manager)
        
        # Engine should have learning manager in context
        self.assertIn('learning_manager', self.engine.context)
        self.assertEqual(self.engine.context['learning_manager'], manager)
    
    def test_engine_events(self):
        """Test engine events for learning integration."""
        from triangulum_lx.core.learning_manager import LearningManager
        
        # Create learning manager
        manager = LearningManager(self.learning_config)
        
        # Integrate with engine
        integrate_learning_with_engine(self.engine, manager)
        
        # Mock the record_repair_episode method
        with mock.patch.object(manager, 'record_repair_episode') as mock_record:
            # Emit repair_completed event
            self.engine.emit("repair_completed", {
                "success": True,
                "cycles": 2,
                "timer_val": 30,
                "entropy_gain": 5.0,
                "fix_attempt": 0
            })
            
            # record_repair_episode should be called
            mock_record.assert_called_once()
    
    def test_run_improvement_cycle(self):
        """Test running improvement cycle through the engine."""
        from triangulum_lx.core.learning_manager import LearningManager
        
        # Create learning manager
        manager = LearningManager(self.learning_config)
        
        # Integrate with engine
        integrate_learning_with_engine(self.engine, manager)
        
        # Run improvement cycle
        result = run_improvement_cycle(self.engine)
        
        # Should get insufficient_data status
        self.assertEqual(result["status"], "insufficient_data")
    
    def test_get_learning_report(self):
        """Test getting learning report through the engine."""
        from triangulum_lx.core.learning_manager import LearningManager
        
        # Create learning manager
        manager = LearningManager(self.learning_config)
        
        # Integrate with engine
        integrate_learning_with_engine(self.engine, manager)
        
        # Get learning report
        report = get_learning_report(self.engine)
        
        # Should have learning_manager section
        self.assertIn('learning_manager', report)
        self.assertEqual(report['learning_manager']['enabled'], True)


class TestLearningEnabledEngine(unittest.TestCase):
    """Test the LearningEnabledEngine class."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
        # Set up configuration
        self.config = {
            "learning": {
                "learning_enabled": True,
                "learning_storage_path": self.temp_dir,
                "improvement_interval": 60,
                "min_episodes_for_learning": 3
            },
            "timer_val": 30,
            "entropy_threshold": 5.0
        }
        
        # Create engine
        self.engine = LearningEnabledEngine(self.config)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test engine initialization."""
        # Engine should have learning manager
        self.assertTrue(hasattr(self.engine, 'learning_manager'))
        
        # Engine should have event handling methods
        self.assertTrue(hasattr(self.engine, 'on'))
        self.assertTrue(hasattr(self.engine, 'emit'))
    
    @mock.patch('triangulum_lx.core.learning_enabled_engine.super')
    def test_repair_file(self, mock_super):
        """Test repair_file with learning events."""
        # Set up mock
        mock_parent = mock.MagicMock()
        mock_parent.repair_file.return_value = {"success": True, "file_path": "test.py"}
        mock_super.return_value = mock_parent
        
        # Spy on emit method
        with mock.patch.object(self.engine, 'emit') as mock_emit:
            # Call repair_file
            result = self.engine.repair_file("test.py", bug_id="test_bug_1")
            
            # Check that emit was called twice (start and complete)
            self.assertEqual(mock_emit.call_count, 2)
            
            # Check first call (repair_started)
            self.assertEqual(mock_emit.call_args_list[0][0][0], "repair_started")
            
            # Check second call (repair_completed)
            self.assertEqual(mock_emit.call_args_list[1][0][0], "repair_completed")
    
    def test_run_tests(self):
        """Test run_tests method."""
        # Create test results
        before_results = [
            {"test_name": "test_1", "success": False, "execution_time": 2.0},
            {"test_name": "test_2", "success": True, "execution_time": 1.5}
        ]
        
        after_results = [
            {"test_name": "test_1", "success": True, "execution_time": 1.8},
            {"test_name": "test_2", "success": True, "execution_time": 1.2}
        ]
        
        # Spy on emit method
        with mock.patch.object(self.engine, 'emit') as mock_emit:
            # Call run_tests
            result = self.engine.run_tests("test.py", before_results, after_results)
            
            # Check that emit was called once
            mock_emit.assert_called_once()
            
            # Check call arguments
            self.assertEqual(mock_emit.call_args[0][0], "test_run_completed")
            self.assertEqual(mock_emit.call_args[0][1]["file_path"], "test.py")
            self.assertEqual(mock_emit.call_args[0][1]["before_results"], before_results)
            self.assertEqual(mock_emit.call_args[0][1]["after_results"], after_results)
    
    def test_record_user_feedback(self):
        """Test record_user_feedback method."""
        # Spy on emit method
        with mock.patch.object(self.engine, 'emit') as mock_emit:
            # Call record_user_feedback
            self.engine.record_user_feedback(
                repair_id="test_repair_1",
                score=0.9,
                comments="Great fix!",
                categories=["code_quality", "efficiency"]
            )
            
            # Check that emit was called once
            mock_emit.assert_called_once()
            
            # Check call arguments
            self.assertEqual(mock_emit.call_args[0][0], "user_feedback_received")
            self.assertEqual(mock_emit.call_args[0][1]["repair_id"], "test_repair_1")
            self.assertEqual(mock_emit.call_args[0][1]["score"], 0.9)
            self.assertEqual(mock_emit.call_args[0][1]["comments"], "Great fix!")
            self.assertEqual(mock_emit.call_args[0][1]["categories"], ["code_quality", "efficiency"])


if __name__ == "__main__":
    unittest.main()
