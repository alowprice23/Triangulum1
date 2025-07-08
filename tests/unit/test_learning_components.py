"""
Unit tests for the learning components of Triangulum.

These tests validate the learning capabilities implemented for STEP-04.
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

from triangulum_lx.learning.replay_buffer import ReplayBuffer, Episode
from triangulum_lx.learning.repair_pattern_extractor import RepairPatternExtractor, RepairPattern
from triangulum_lx.learning.feedback_processor import (
    FeedbackProcessor, UserFeedback, TestResult, RepairComparison
)
from triangulum_lx.learning.continuous_improvement import ContinuousImprovementSystem
from triangulum_lx.core.learning_manager import LearningManager
from triangulum_lx.core.engine_event_extension import EventHandlerMixin, extend_engine_with_events


class MockEngine:
    """Mock engine for testing."""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.context = {}
    
    def repair_file(self, file_path, **kwargs):
        return {"success": True, "file_path": file_path}
    
    def repair_folder(self, folder_path, **kwargs):
        return {"success": True, "folder_path": folder_path}
    
    def get_status(self):
        return {"running": True}


class TestReplayBuffer(unittest.TestCase):
    """Test the ReplayBuffer class."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.buffer = ReplayBuffer(capacity=5, storage_path=self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_add_episode(self):
        """Test adding episodes to the buffer."""
        episode = Episode(
            bug_id="test_bug_1",
            cycles=2,
            total_wall=120.5,
            success=True,
            timer_val=30,
            entropy_gain=5.2,
            fix_attempt=0,
            agent_tokens={"agent1": 1000, "agent2": 2000}
        )
        
        self.buffer.add(episode)
        self.assertEqual(len(self.buffer.buffer), 1)
        self.assertEqual(self.buffer.buffer[0].bug_id, "test_bug_1")
    
    def test_sample(self):
        """Test sampling episodes from the buffer."""
        for i in range(3):
            episode = Episode(
                bug_id=f"test_bug_{i}",
                cycles=i + 1,
                total_wall=100.0 + i,
                success=True,
                timer_val=30,
                entropy_gain=5.0,
                fix_attempt=0,
                agent_tokens={"agent1": 1000, "agent2": 2000}
            )
            self.buffer.add(episode)
        
        samples = self.buffer.sample(2)
        self.assertEqual(len(samples), 2)
    
    def test_stats(self):
        """Test calculating statistics."""
        # Add successful episode
        episode1 = Episode(
            bug_id="test_bug_1",
            cycles=2,
            total_wall=120.0,
            success=True,
            timer_val=30,
            entropy_gain=5.0,
            fix_attempt=0,
            agent_tokens={"agent1": 1000, "agent2": 2000}
        )
        
        # Add failed episode
        episode2 = Episode(
            bug_id="test_bug_2",
            cycles=3,
            total_wall=180.0,
            success=False,
            timer_val=30,
            entropy_gain=3.0,
            fix_attempt=1,
            agent_tokens={"agent1": 1500, "agent2": 2500}
        )
        
        self.buffer.add(episode1)
        self.buffer.add(episode2)
        
        stats = self.buffer.stats()
        self.assertEqual(stats["count"], 2)
        self.assertEqual(stats["success_rate"], 0.5)
        self.assertEqual(stats["avg_cycles"], 2.5)
        self.assertEqual(stats["avg_wall_time"], 150.0)


class TestRepairPatternExtractor(unittest.TestCase):
    """Test the RepairPatternExtractor class."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.extractor = RepairPatternExtractor(storage_path=self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_classify_bug_from_description(self):
        """Test bug classification from description."""
        # Test null pointer classification
        description = "NullPointerException when calling method on null object"
        code = "item.getName()"
        bug_type = self.extractor._classify_bug_from_description(description, code)
        self.assertEqual(bug_type, "null_pointer")
        
        # Test resource leak classification
        description = "File not closed properly"
        code = "f = open('file.txt', 'r')\ndata = f.read()"
        bug_type = self.extractor._classify_bug_from_description(description, code)
        self.assertEqual(bug_type, "resource_leak")
    
    def test_get_patterns_for_bug(self):
        """Test getting patterns for a bug."""
        # Add a pattern manually
        pattern = RepairPattern(
            pattern_id="test_pattern_1",
            name="Null Check",
            description="Add null check before accessing attributes",
            bug_type="null_pointer",
            code_changes=[
                {"change_type": "replace", "from": "item.getName()", "to": "item and item.getName()"}
            ],
            confidence=0.9
        )
        
        self.extractor.patterns[pattern.pattern_id] = pattern
        
        # Get patterns for a null pointer bug
        description = "NullPointerException when accessing attribute"
        code = "return item.getName()"
        patterns = self.extractor.get_patterns_for_bug(description, code)
        
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].pattern_id, "test_pattern_1")


class TestFeedbackProcessor(unittest.TestCase):
    """Test the FeedbackProcessor class."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.processor = FeedbackProcessor(storage_path=self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_add_user_feedback(self):
        """Test adding user feedback."""
        feedback = UserFeedback(
            repair_id="test_repair_1",
            timestamp=1234567890.0,
            score=0.9,
            comments="Great fix!",
            categories=["code_quality", "efficiency"]
        )
        
        self.processor.add_user_feedback(feedback)
        self.assertEqual(len(self.processor.user_feedback), 1)
        self.assertEqual(self.processor.user_feedback["test_repair_1"].score, 0.9)
    
    def test_compare_repair(self):
        """Test comparing repair results."""
        before_results = [
            TestResult(
                repair_id="test_repair_1",
                file_path="test.py",
                timestamp=1234567890.0,
                success=False,
                test_name="test_1",
                execution_time=2.0
            ),
            TestResult(
                repair_id="test_repair_1",
                file_path="test.py",
                timestamp=1234567890.0,
                success=True,
                test_name="test_2",
                execution_time=1.5
            )
        ]
        
        after_results = [
            TestResult(
                repair_id="test_repair_1",
                file_path="test.py",
                timestamp=1234567891.0,
                success=True,
                test_name="test_1",
                execution_time=1.8
            ),
            TestResult(
                repair_id="test_repair_1",
                file_path="test.py",
                timestamp=1234567891.0,
                success=True,
                test_name="test_2",
                execution_time=1.2
            )
        ]
        
        comparison = self.processor.compare_repair(
            repair_id="test_repair_1",
            file_path="test.py",
            before_results=before_results,
            after_results=after_results
        )
        
        self.assertEqual(comparison.success_rate_before, 0.5)
        self.assertEqual(comparison.success_rate_after, 1.0)
        self.assertAlmostEqual(comparison.avg_execution_time_before, 1.75)
        self.assertAlmostEqual(comparison.avg_execution_time_after, 1.5)


class TestContinuousImprovementSystem(unittest.TestCase):
    """Test the ContinuousImprovementSystem class."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cis = ContinuousImprovementSystem(
            storage_path=self.temp_dir,
            improvement_interval=60,
            min_episodes_for_learning=3
        )
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_add_episode(self):
        """Test adding an episode."""
        episode = Episode(
            bug_id="test_bug_1",
            cycles=2,
            total_wall=120.5,
            success=True,
            timer_val=30,
            entropy_gain=5.2,
            fix_attempt=0,
            agent_tokens={"agent1": 1000, "agent2": 2000}
        )
        
        self.cis.add_episode(episode)
        self.assertEqual(len(self.cis.replay_buffer.buffer), 1)
        self.assertEqual(len(self.cis.performance_history), 1)
    
    def test_run_improvement_cycle_insufficient_data(self):
        """Test running improvement cycle with insufficient data."""
        result = self.cis.run_improvement_cycle()
        self.assertEqual(result["status"], "insufficient_data")
    
    def test_get_current_parameters(self):
        """Test getting current parameters."""
        params = self.cis.get_current_parameters()
        self.assertIn("timer_multiplier", params)
        self.assertIn("entropy_threshold", params)
        self.assertIn("agent_capacity", params)


class TestLearningManager(unittest.TestCase):
    """Test the LearningManager class."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            "learning_enabled": True,
            "learning_storage_path": self.temp_dir,
            "improvement_interval": 60,
            "min_episodes_for_learning": 3
        }
        self.manager = LearningManager(self.config)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_record_repair_episode(self):
        """Test recording a repair episode."""
        repair_id = self.manager.record_repair_episode(
            bug_id="test_bug_1",
            cycles=2,
            total_wall=120.5,
            success=True,
            timer_val=30,
            entropy_gain=5.2,
            fix_attempt=0,
            agent_tokens={"agent1": 1000, "agent2": 2000}
        )
        
        self.assertEqual(repair_id, "test_bug_1")
        self.assertEqual(len(self.manager.cis.replay_buffer.buffer), 1)
    
    def test_get_repair_recommendations(self):
        """Test getting repair recommendations."""
        # Should return empty list when no patterns available
        recommendations = self.manager.get_repair_recommendations(
            bug_description="NullPointerException when accessing attribute",
            code_context="return item.getName()"
        )
        
        self.assertEqual(len(recommendations), 0)


class TestEventHandlerMixin(unittest.TestCase):
    """Test the EventHandlerMixin class."""
    
    def test_on_off_emit(self):
        """Test event registration, removal, and emission."""
        handler = EventHandlerMixin()
        
        # Create a mock event handler
        mock_handler = mock.Mock()
        
        # Register the handler
        handler.on("test_event", mock_handler)
        
        # Emit the event
        handler.emit("test_event", {"test": "data"})
        
        # Check if handler was called
        mock_handler.assert_called_once()
        
        # Remove the handler
        handler.off("test_event", mock_handler)
        
        # Emit again
        handler.emit("test_event", {"test": "data"})
        
        # Handler should not be called again
        mock_handler.assert_called_once()


class TestEngineExtension(unittest.TestCase):
    """Test the engine extension functionality."""
    
    def test_extend_engine_with_events(self):
        """Test extending an engine class with events."""
        EventEnabledEngine = extend_engine_with_events(MockEngine)
        
        engine = EventEnabledEngine({"test": "config"})
        
        # Engine should have both MockEngine and EventHandlerMixin methods
        self.assertTrue(hasattr(engine, "repair_file"))
        self.assertTrue(hasattr(engine, "on"))
        self.assertTrue(hasattr(engine, "emit"))
        
        # Context should be initialized
        self.assertIsInstance(engine.context, dict)
        
        # Event handlers should be initialized
        self.assertIsInstance(engine._event_handlers, dict)


if __name__ == "__main__":
    unittest.main()
