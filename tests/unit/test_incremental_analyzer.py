import os
import unittest
from unittest.mock import MagicMock, patch
from triangulum_lx.tooling.incremental_analyzer import IncrementalAnalyzer
from triangulum_lx.tooling.graph_models import DependencyGraph, FileNode, LanguageType

class TestIncrementalAnalyzer(unittest.TestCase):
    def setUp(self):
        self.graph = DependencyGraph()
        self.analyzer = IncrementalAnalyzer(self.graph)

    def test_analyze_changes_new_file(self):
        updated_files = {"new_file.py": "import os"}
        affected_files = self.analyzer.analyze_changes(updated_files)
        self.assertEqual(affected_files, {"new_file.py"})

    def test_analyze_changes_modified_file(self):
        # Create a mock node with a file hash
        node = FileNode(path="file1.py", language=LanguageType.PYTHON)
        node.file_hash = "old_hash"
        self.graph.add_node(node)
        
        # Mock the update_hash method to return a different hash
        original_update_hash = FileNode.update_hash
        
        def mock_update_hash(self):
            self.file_hash = "new_hash"
            return self.file_hash
            
        # Apply the mock
        FileNode.update_hash = mock_update_hash
        
        try:
            # Test with a modified file
            updated_files = {"file1.py": "import sys"}
            affected_files = self.analyzer.analyze_changes(updated_files)
            
            # Verify the file was marked as affected
            self.assertEqual(affected_files, {"file1.py"})
            # Verify the node was removed from the graph
            self.assertNotIn("file1.py", self.graph)
        finally:
            # Restore the original method
            FileNode.update_hash = original_update_hash

if __name__ == "__main__":
    unittest.main()
