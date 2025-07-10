import unittest
from unittest.mock import MagicMock, patch, mock_open
import json
from triangulum_lx.tooling.relationship_context_provider import RelationshipContextProvider
from triangulum_lx.core.fs_state import FileSystemStateCache # Added import

class TestRelationshipContextProvider(unittest.TestCase):

    def setUp(self):
        """Set up a new RelationshipContextProvider instance for each test."""
        self.mock_fs_cache = MagicMock(spec=FileSystemStateCache)
        # Default behavior for cache: relationship file doesn't exist unless specified by a test
        self.mock_fs_cache.exists.return_value = False
        self.relationship_context_provider = RelationshipContextProvider(
            relationships_path="dummy_default_path.json", # Provide a path for init
            fs_cache=self.mock_fs_cache
        )

    def test_provider_initialization(self):
        """Test that the provider is initialized correctly."""
        self.assertIsInstance(self.relationship_context_provider, RelationshipContextProvider)
        # self.assertEqual(self.relationship_context_provider.engine, self.mock_engine) # Removed, no engine attribute
        self.assertIsNotNone(self.relationship_context_provider.relationships)
        self.assertEqual(self.relationship_context_provider.relationships, {})

    @patch('builtins.open', new_callable=mock_open, read_data='{"file1.py": {"imports": ["file2.py"]}}')
    def test_load_relationships(self, mock_open_file): # Renamed mock_file to mock_open_file for clarity
        """Test loading relationships from a file."""
        fake_path = "fake_path.json"
        # Ensure fs_cache.exists returns True for this path so load_relationships_from_file attempts to open it
        self.relationship_context_provider.fs_cache.exists.return_value = True

        self.relationship_context_provider.load_relationships_from_file(fake_path)
        
        # Verify the file was opened
        mock_open_file.assert_called_once_with(fake_path, 'r', encoding='utf-8')
        
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
        self.relationship_context_provider._build_dependency_graphs() # Call manually after setting relationships
        
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
        self.relationship_context_provider._build_dependency_graphs() # Call manually
        
        context = self.relationship_context_provider.get_context_for_repair("file1.py") # Corrected method name
        
        # Verify the context contains the expected information
        self.assertIn("file_path", context)
        self.assertEqual(context["file_path"], "file1.py")

        self.assertIn("imports", context)
        self.assertIsInstance(context["imports"], list)
        self.assertIn("file2.py", context["imports"])
        self.assertIn("file3.py", context["imports"])

        self.assertIn("imported_by", context)
        self.assertIsInstance(context["imported_by"], list)
        self.assertIn("file4.py", context["imported_by"])

        self.assertIn("functions", context)
        self.assertIsInstance(context["functions"], list)
        self.assertIn("func1", context["functions"])
        self.assertIn("func2", context["functions"])

if __name__ == '__main__':
    unittest.main()
