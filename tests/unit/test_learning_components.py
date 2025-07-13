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
    FeedbackProcessor
)
from triangulum_lx.learning.continuous_improvement import ContinuousImprovement
from triangulum_lx.core.learning_manager import LearningManager
from triangulum_lx.core.engine_event_extension import EventHandler


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
        self.extractor = RepairPatternExtractor(database_path=self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    




class TestContinuousImprovement(unittest.TestCase):
    """Test the ContinuousImprovement class."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cis = ContinuousImprovement(
            database_path=os.path.join(self.temp_dir, "parameters.json")
        )
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_get_parameter(self):
        """Test getting a parameter."""
        # Get a default parameter
        param_value = self.cis.get_parameter("bug_detection_confidence_threshold")
        self.assertEqual(param_value, 0.7)
        
        # Get a non-existent parameter
        param_value = self.cis.get_parameter("non_existent_param")
        self.assertIsNone(param_value)


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
        self.config_path = os.path.join(self.temp_dir, "learning_config.json")
        with open(self.config_path, "w") as f:
            json.dump(self.config, f)
        self.manager = LearningManager(config_path=self.config_path)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    




if __name__ == "__main__":
    unittest.main()
