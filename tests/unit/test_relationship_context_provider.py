import unittest
from unittest.mock import MagicMock, patch, mock_open
import json
from triangulum_lx.tooling.relationship_context_provider import RelationshipContextProvider

class TestRelationshipContextProvider(unittest.TestCase):

    def setUp(self):
        """Set up a new RelationshipContextProvider instance for each test."""
        self.mock_engine = MagicMock()
        self.relationship_context_provider = RelationshipContextProvider(self.mock_engine)

    def test_provider_initialization(self):
        """Test that the provider is initialized correctly."""
        self.assertIsInstance(self.relationship_context_provider, RelationshipContextProvider)
        self.assertEqual(self.relationship_context_provider.engine, self.mock_engine)
        self.assertIsNotNone(self.relationship_context_provider.relationships)
        self.assertEqual(self.relationship_context_provider.relationships, {})

    @patch('builtins.open', new_callable=mock_open, read_data='{"file1.py": {"imports": ["file2.py"]}}')
    def test_load_relationships(self, mock_file):
        """Test loading relationships from a file."""
        self.relationship_context_provider.load_relationships("fake_path.json")
        
        # Verify the file was opened
        mock_file.assert_called_once_with("fake_path.json", "r")
        
        # Verify the relationships were loaded
        expected_relationships = {"file1.py": {"imports": ["file2.py"]}}
        self.assertEqual(self.relationship_context_provider.relationships, expected_relationships)

    def test_get_related_files(self):
        """Test getting related files."""
        # Set up test relationships
        self.relationship_context_provider.relationships = {
            "file1.py": {
                "imports": ["file2.py", "file3.py"],
                "imported_by": ["file4.py"]
            },
            "file2.py": {
                "imports": ["file3.py"],
                "imported_by": ["file1.py", "file4.py"]
            }
        }
        
        related_files = self.relationship_context_provider.get_related_files("file1.py")
        
        # Verify the related files are correct
        expected_related_files = ["file2.py", "file3.py", "file4.py"]
        self.assertEqual(sorted(related_files), sorted(expected_related_files))

    def test_get_relationship_context(self):
        """Test getting relationship context."""
        # Set up test relationships
        self.relationship_context_provider.relationships = {
            "file1.py": {
                "imports": ["file2.py", "file3.py"],
                "imported_by": ["file4.py"],
                "functions": ["func1", "func2"]
            }
        }
        
        context = self.relationship_context_provider.get_relationship_context("file1.py")
        
        # Verify the context contains the expected information
        self.assertIn("file1.py", context)
        self.assertIn("imports", context)
        self.assertIn("file2.py", context)
        self.assertIn("file3.py", context)
        self.assertIn("imported_by", context)
        self.assertIn("file4.py", context)
        self.assertIn("functions", context)
        self.assertIn("func1", context)
        self.assertIn("func2", context)

if __name__ == '__main__':
    unittest.main()
