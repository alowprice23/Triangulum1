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
            self.engine = TriangulumEngine(config={})

    def test_engine_initialization(self):
        """Test that the engine and its components are initialized correctly."""
        self.assertIsInstance(self.engine, TriangulumEngine)
        self.assertFalse(self.engine.running)

if __name__ == '__main__':
    unittest.main()
