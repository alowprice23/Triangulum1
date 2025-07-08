"""
Unit tests for the CodeRelationshipAnalyzer class.
"""

import os
import tempfile
import unittest
import json
from unittest.mock import patch, mock_open, MagicMock

from triangulum_lx.tooling.code_relationship_analyzer import CodeRelationshipAnalyzer

class TestCodeRelationshipAnalyzer(unittest.TestCase):
    """Tests for the CodeRelationshipAnalyzer class."""

    def setUp(self):
        """Set up test environment."""
        self.analyzer = CodeRelationshipAnalyzer()
        
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create some test Python files
        self.create_test_files()

    def tearDown(self):
        """Clean up test environment."""
        # Clean up the temporary directory
        import shutil
        shutil.rmtree(self.temp_dir)

    def create_test_files(self):
        """Create test Python files for analysis."""
        # Create a module directory
        module_dir = os.path.join(self.temp_dir, "test_module")
        os.makedirs(module_dir)
        
        # Create __init__.py in the module directory
        with open(os.path.join(module_dir, "__init__.py"), "w") as f:
            f.write("# Module initialization\n")
        
        # Create a file with some imports and functions
        with open(os.path.join(module_dir, "file1.py"), "w") as f:
            f.write("""
import os
import sys
from datetime import datetime

def function1():
    \"\"\"A test function.\"\"\"
    return "Function 1"

def function2(param):
    \"\"\"Another test function.\"\"\"
    return f"Function 2 with {param}"

class TestClass:
    \"\"\"A test class.\"\"\"
    
    def method1(self):
        \"\"\"A test method.\"\"\"
        return "Method 1"
    
    def method2(self, param):
        \"\"\"Another test method.\"\"\"
        return f"Method 2 with {param}"
""")
        
        # Create a file that imports the first file
        with open(os.path.join(module_dir, "file2.py"), "w") as f:
            f.write("""
from test_module.file1 import function1, TestClass

def use_function1():
    \"\"\"Use function1 from file1.\"\"\"
    return function1()

def create_test_class():
    \"\"\"Create a TestClass instance.\"\"\"
    return TestClass()
""")

    def test_initialization(self):
        """Test initialization of the analyzer."""
        self.assertIsInstance(self.analyzer, CodeRelationshipAnalyzer)
        self.assertEqual(self.analyzer.relationships, {})
        self.assertEqual(self.analyzer.import_map, {})
        self.assertEqual(self.analyzer.function_map, {})

    def test_collect_python_files(self):
        """Test collecting Python files from a directory."""
        files = self.analyzer._collect_python_files(self.temp_dir)
        
        # Check that we found the expected number of files
        self.assertEqual(len(files), 3)
        
        # Check that all files have the .py extension
        for file in files:
            self.assertTrue(file.endswith(".py"))

    def test_build_module_map(self):
        """Test building the module map."""
        files = self.analyzer._collect_python_files(self.temp_dir)
        self.analyzer._build_module_map(files, self.temp_dir)
        
        # Check that the module map contains the expected modules
        self.assertIn("test_module", self.analyzer.import_map)
        self.assertIn("test_module.file1", self.analyzer.import_map)
        self.assertIn("test_module.file2", self.analyzer.import_map)

    def test_analyze_file(self):
        """Test analyzing a single file."""
        files = self.analyzer._collect_python_files(self.temp_dir)
        self.analyzer._build_module_map(files, self.temp_dir)
        
        # Find the file1.py path
        file1_path = None
        for file in files:
            if file.endswith("file1.py"):
                file1_path = file
                break
        
        self.assertIsNotNone(file1_path, "Could not find file1.py")
        
        # Analyze the file
        self.analyzer._analyze_file(file1_path)
        
        # Check that the file was analyzed
        self.assertIn(file1_path, self.analyzer.relationships)
        
        # Check that the functions were found
        self.assertIn("function1", self.analyzer.relationships[file1_path]["functions"])
        self.assertIn("function2", self.analyzer.relationships[file1_path]["functions"])
        
        # Check that the classes were found
        self.assertIn("TestClass", self.analyzer.relationships[file1_path]["classes"])

    def test_analyze_directory(self):
        """Test analyzing a directory."""
        relationships = self.analyzer.analyze_directory(self.temp_dir)
        
        # Check that all files were analyzed
        self.assertEqual(len(relationships), 3)
        
        # Check that the relationships between files were detected
        file1_path = None
        file2_path = None
        for file in relationships:
            if file.endswith("file1.py"):
                file1_path = file
            elif file.endswith("file2.py"):
                file2_path = file
        
        self.assertIsNotNone(file1_path, "Could not find file1.py")
        self.assertIsNotNone(file2_path, "Could not find file2.py")
        
        # Check that file2 imports file1
        self.assertIn(file1_path, relationships[file2_path]["imports"])
        
        # Check that file1 is imported by file2
        self.assertIn(file2_path, relationships[file1_path]["imported_by"])

    def test_save_and_load_relationships(self):
        """Test saving and loading relationships."""
        # Analyze the directory
        self.analyzer.analyze_directory(self.temp_dir)
        
        # Create a temporary file to save the relationships
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Save the relationships
            self.analyzer.save_relationships(temp_path)
            
            # Create a new analyzer
            new_analyzer = CodeRelationshipAnalyzer()
            
            # Load the relationships
            loaded_relationships = new_analyzer.load_relationships(temp_path)
            
            # Check that the loaded relationships match the original
            self.assertEqual(loaded_relationships, self.analyzer.relationships)
        finally:
            # Clean up the temporary file
            os.unlink(temp_path)

    @patch("builtins.open", new_callable=mock_open, read_data="import os\nimport sys\n")
    def test_analyze_file_with_mock(self, mock_file):
        """Test analyzing a file with a mock file."""
        # Mock ast.parse to return a simple AST
        with patch("ast.parse") as mock_parse:
            # Create a mock AST
            mock_ast = MagicMock()
            mock_parse.return_value = mock_ast
            
            # Mock ast.walk to return a list of mock nodes
            mock_import = MagicMock()
            mock_import.names = [MagicMock(name="os"), MagicMock(name="sys")]
            mock_ast.walk.return_value = [mock_import]
            
            # Analyze a mock file
            self.analyzer._analyze_file("mock_file.py")
            
            # Check that open was called
            mock_file.assert_called_once_with("mock_file.py", "r", encoding="utf-8")
            
            # Check that ast.parse was called
            mock_parse.assert_called_once()

if __name__ == "__main__":
    unittest.main()
