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
from triangulum_lx.core.engine_learning_integration import EngineLearningIntegration
from triangulum_lx.core.engine_event_extension import EventHandler


class MockEngine(EventHandler):
    """Mock engine for testing."""
    
    def __init__(self, config=None):
        super().__init__(event_types=["test_event"])
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
        # Create integration
        integration = EngineLearningIntegration()
        
        # Get learning manager
        manager = integration.get_learning_manager()
        
        # Check that learning manager is initialized
        self.assertIsNotNone(manager)
    
    def test_get_integration_state(self):
        """Test getting the integration state."""
        # Create integration
        integration = EngineLearningIntegration()
        
        # Get integration state
        state = integration.get_integration_state()
        
        # Check that state is a dictionary
        self.assertIsInstance(state, dict)
        
        # Check for expected keys
        self.assertIn("status", state)
        self.assertIn("components", state)


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
        
        # Create a temporary config file
        self.config_path = os.path.join(self.temp_dir, "config.json")
        with open(self.config_path, "w") as f:
            json.dump(self.config, f)

        # Create engine
        self.engine = LearningEnabledEngine(self.config_path)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test engine initialization."""
        # Engine should have learning manager
        self.assertTrue(hasattr(self.engine, 'learning_manager'))
        
        # Engine should have event handling methods
        self.assertTrue(hasattr(self.engine, 'emit_event'))
    
    
    


if __name__ == "__main__":
    unittest.main()
