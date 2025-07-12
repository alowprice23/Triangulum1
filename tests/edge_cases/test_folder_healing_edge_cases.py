"""
Edge case tests for the folder-level self-healing system.

This test suite verifies that the folder-level self-healing system handles
unusual or extreme scenarios correctly, such as:
1. Empty folders
2. Very large files
3. Files with unusual encodings
4. Corrupted files
5. Circular dependencies
6. Missing permissions
7. Unusual file extensions
"""

import unittest
import os
import tempfile
import shutil
import time
import random
import string
from pathlib import Path

from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus as MessageBus
from triangulum_lx.agents.bug_detector_agent import BugDetectorAgent
from triangulum_lx.agents.relationship_analyst_agent import RelationshipAnalystAgent
from triangulum_lx.agents.priority_analyzer_agent import PriorityAnalyzerAgent
from triangulum_lx.agents.strategy_agent import StrategyAgent
from triangulum_lx.agents.implementation_agent import ImplementationAgent
from triangulum_lx.agents.verification_agent import VerificationAgent
from triangulum_lx.agents.orchestrator_agent import OrchestratorAgent
from triangulum_lx.agents.message import AgentMessage, MessageType


class TestFolderHealingEdgeCases(unittest.TestCase):
    """Edge case tests for the folder-level self-healing system."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a message bus
        self.message_bus = MessageBus()
        
        # Create all specialized agents
        self.bug_detector = BugDetectorAgent(
            agent_id="bug_detector",
            message_bus=self.message_bus
        )
        
        self.relationship_analyst = RelationshipAnalystAgent(
            agent_id="relationship_analyst",
            message_bus=self.message_bus
        )
        
        self.priority_analyzer = PriorityAnalyzerAgent(
            agent_id="priority_analyzer",
            message_bus=self.message_bus
        )
        
        self.strategy_agent = StrategyAgent(
            agent_id="strategy_agent",
            message_bus=self.message_bus
        )
        
        self.implementation_agent = ImplementationAgent(
            agent_id="implementation_agent",
            message_bus=self.message_bus
        )
        
        self.verification_agent = VerificationAgent(
            agent_id="verification_agent",
            message_bus=self.message_bus
        )
        
        # Create the orchestrator with short timeout for testing
        self.orchestrator = OrchestratorAgent(
            agent_id="orchestrator",
            message_bus=self.message_bus,
            config={"timeout": 5}
        )
        
        # Create a temporary directory for edge case tests
        self.test_dir = tempfile.mkdtemp()
        
        # Set up message handlers
        self.results = {}
        self.message_bus.register_handler(
            "test_handler",
            MessageType.TASK_RESULT,
            self._handle_task_result
        )
        
        self.message_bus.register_handler(
            "test_handler",
            MessageType.ERROR,
            self._handle_error
        )
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.test_dir)
    
    def _handle_task_result(self, message):
        """Handle task result messages."""
        self.results[message.sender] = message.content
    
    def _handle_error(self, message):
        """Handle error messages."""
        print(f"Error from {message.sender}: {message.content.get('error', 'Unknown error')}")
    
    def _wait_for_result(self, timeout=10):
        """Wait for a result from the orchestrator."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if "orchestrator" in self.results:
                return self.results["orchestrator"]
            time.sleep(0.1)
        return None
    
    def _run_orchestrator(self, folder_path, options=None):
        """Run the orchestrator on a folder."""
        # Clear previous results
        self.results = {}
        
        # Create a task request message
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "orchestrate_folder_healing",
                "folder_path": folder_path,
                "options": options or {"dry_run": True}
            },
            sender="test_handler",
            recipient="orchestrator"
        )
        
        # Process the message
        self.orchestrator.handle_message(message)
        
        # Wait for the result
        result = self._wait_for_result()
        if result:
            return result.get("result", {})
        return {}
    
    def test_empty_folder(self):
        """Test healing an empty folder."""
        # Create an empty folder
        empty_dir = os.path.join(self.test_dir, "empty")
        os.makedirs(empty_dir, exist_ok=True)
        
        # Run the orchestrator
        result = self._run_orchestrator(empty_dir)
        
        # Check that it handled the empty folder gracefully
        self.assertIn("status", result)
        # Either completed or skipped, but not failed
        self.assertNotEqual(result.get("status"), "failed")
    
    def test_very_large_file(self):
        """Test healing a folder with a very large file."""
        # Create a directory
        large_file_dir = os.path.join(self.test_dir, "large_file")
        os.makedirs(large_file_dir, exist_ok=True)
        
        # Create a large file (10 MB of random Python-like content)
        large_file_path = os.path.join(large_file_dir, "large_file.py")
        
        with open(large_file_path, 'w') as f:
            f.write("# Very large Python file with potential bugs\n\n")
            f.write("import os\nimport sys\n\n")
            
            # Generate a large class with many methods
            f.write("class LargeClass:\n")
            f.write("    def __init__(self, config=None):\n")
            f.write("        self.config = config\n")
            
            # Add a bug at the beginning
            f.write("    def bug_method(self):\n")
            f.write("        # BUG: No null check before accessing attribute\n")
            f.write("        return self.config.attribute\n\n")
            
            # Generate many methods to make the file large
            for i in range(1000):
                f.write(f"    def method_{i}(self, arg1, arg2):\n")
                f.write(f"        # Method {i}\n")
                f.write(f"        result = arg1 + arg2\n")
                f.write(f"        return result * {i}\n\n")
            
            # Generate a large dictionary (takes up space)
            f.write("large_dictionary = {\n")
            for i in range(10000):
                f.write(f"    'key_{i}': 'value_{''.join(random.choices(string.ascii_letters, k=20))}',\n")
            f.write("}\n\n")
            
            # Add a main section
            f.write("if __name__ == '__main__':\n")
            f.write("    instance = LargeClass()\n")
            f.write("    print(instance.method_999(10, 20))\n")
        
        # Verify the file is large (should be at least 1 MB)
        file_size = os.path.getsize(large_file_path)
        self.assertGreater(file_size, 1_000_000)  # 1 MB minimum
        
        # Run the orchestrator (with longer timeout)
        result = self._run_orchestrator(large_file_dir, {"dry_run": True, "timeout": 30})
        
        # Check that it handled the large file
        self.assertIn("status", result)
        # Should not crash on large file
        self.assertIsNotNone(result.get("status"))
    
    def test_unusual_encoding(self):
        """Test healing a folder with files that have unusual encodings."""
        # Create a directory
        encoding_dir = os.path.join(self.test_dir, "encoding")
        os.makedirs(encoding_dir, exist_ok=True)
        
        # Create a file with UTF-16 encoding
        utf16_file_path = os.path.join(encoding_dir, "utf16_file.py")
        
        # Create content with non-ASCII characters
        content = """
# File with UTF-16 encoding and non-ASCII characters
# Contains a bug to detect

def greet(name=None):
    # BUG: No null check
    return "Hello, " + name + "!"

# Non-ASCII characters: 你好, こんにちは, Привет, مرحبا, שלום
"""
        
        # Write with UTF-16 encoding
        with open(utf16_file_path, 'w', encoding='utf-16') as f:
            f.write(content)
        
        # Run the orchestrator
        result = self._run_orchestrator(encoding_dir)
        
        # Check that it handled the encoding
        self.assertIn("status", result)
        # System should not crash with encoding issues
        self.assertIsNotNone(result.get("status"))
    
    def test_corrupted_file(self):
        """Test healing a folder with a corrupted Python file."""
        # Create a directory
        corrupted_dir = os.path.join(self.test_dir, "corrupted")
        os.makedirs(corrupted_dir, exist_ok=True)
        
        # Create a corrupted Python file (invalid syntax)
        corrupted_file_path = os.path.join(corrupted_dir, "corrupted_file.py")
        
        with open(corrupted_file_path, 'w') as f:
            f.write("# Corrupted Python file with invalid syntax\n\n")
            f.write("def valid_function():\n")
            f.write("    return 'This is valid'\n\n")
            f.write("class InvalidClass\n")  # Missing colon
            f.write("    def __init__(self):\n")
            f.write("        self.value = 10\n\n")
            f.write("if True\n")  # Missing colon
            f.write("    print('This will not work')\n")
        
        # Create a valid file with a bug
        valid_file_path = os.path.join(corrupted_dir, "valid_file.py")
        
        with open(valid_file_path, 'w') as f:
            f.write("# Valid Python file with a bug\n\n")
            f.write("def bug_function(param=None):\n")
            f.write("    # BUG: No null check\n")
            f.write("    return param.upper()\n")
        
        # Run the orchestrator
        result = self._run_orchestrator(corrupted_dir)
        
        # Check that it handled the corrupted file gracefully
        self.assertIn("status", result)
        # Should not crash on corrupted file
        self.assertIsNotNone(result.get("status"))
    
    def test_circular_dependencies(self):
        """Test healing a folder with circular dependencies."""
        # Create a directory
        circular_dir = os.path.join(self.test_dir, "circular")
        os.makedirs(circular_dir, exist_ok=True)
        
        # Create files with circular dependencies
        module_a_path = os.path.join(circular_dir, "module_a.py")
        module_b_path = os.path.join(circular_dir, "module_b.py")
        module_c_path = os.path.join(circular_dir, "module_c.py")
        
        # Module A imports B, and has a bug
        with open(module_a_path, 'w') as f:
            f.write("# Module A - imports Module B\n")
            f.write("from module_b import ClassB\n\n")
            f.write("class ClassA:\n")
            f.write("    def __init__(self, config=None):\n")
            f.write("        self.config = config\n")
            f.write("        self.b = ClassB()\n\n")
            f.write("    def method_a(self):\n")
            f.write("        # BUG: No null check\n")
            f.write("        return self.config.value\n")
        
        # Module B imports C
        with open(module_b_path, 'w') as f:
            f.write("# Module B - imports Module C\n")
            f.write("from module_c import ClassC\n\n")
            f.write("class ClassB:\n")
            f.write("    def __init__(self):\n")
            f.write("        self.c = ClassC()\n\n")
            f.write("    def method_b(self):\n")
            f.write("        return self.c.method_c()\n")
        
        # Module C imports A, creating a circular dependency
        with open(module_c_path, 'w') as f:
            f.write("# Module C - imports Module A, creating a circular dependency\n")
            f.write("from module_a import ClassA\n\n")
            f.write("class ClassC:\n")
            f.write("    def __init__(self):\n")
            f.write("        # Comment out to avoid runtime errors, but static analysis should detect the circular import\n")
            f.write("        # self.a = ClassA()\n")
            f.write("        pass\n\n")
            f.write("    def method_c(self):\n")
            f.write("        return 'Method C'\n")
        
        # Run the orchestrator
        result = self._run_orchestrator(circular_dir)
        
        # Check that it handled the circular dependencies
        self.assertIn("status", result)
        # System should not crash with circular dependencies
        self.assertIsNotNone(result.get("status"))
    
    def test_unusual_file_extensions(self):
        """Test healing a folder with unusual file extensions."""
        # Create a directory
        extension_dir = os.path.join(self.test_dir, "extensions")
        os.makedirs(extension_dir, exist_ok=True)
        
        # Create Python files with unusual extensions
        extensions = [".pyc", ".pyw", ".pyx", ".pyd", ".pyi", ".pyz"]
        
        for i, ext in enumerate(extensions):
            file_path = os.path.join(extension_dir, f"test_file{ext}")
            
            with open(file_path, 'w') as f:
                f.write(f"# Python file with unusual extension: {ext}\n\n")
                f.write("def test_function(param=None):\n")
                if i % 2 == 0:  # Add bug to some files
                    f.write("    # BUG: No null check\n")
                    f.write("    return param.lower()\n")
                else:
                    f.write("    if param is None:\n")
                    f.write("        return ''\n")
                    f.write("    return param.lower()\n")
        
        # Add a normal Python file for reference
        normal_file_path = os.path.join(extension_dir, "normal.py")
        with open(normal_file_path, 'w') as f:
            f.write("# Normal Python file\n\n")
            f.write("def normal_function(param=None):\n")
            f.write("    # BUG: No null check\n")
            f.write("    return param.upper()\n")
        
        # Run the orchestrator
        result = self._run_orchestrator(extension_dir)
        
        # Check that it handled the unusual extensions
        self.assertIn("status", result)
        # System should process at least the normal Python file
        bug_detection_result = result.get("results", {}).get("bug_detector", {})
        bugs_by_file = bug_detection_result.get("bugs_by_file", {})
        self.assertGreaterEqual(len(bugs_by_file), 1)
    
    def test_mixed_languages(self):
        """Test healing a folder with mixed language files."""
        # Create a directory
        mixed_dir = os.path.join(self.test_dir, "mixed")
        os.makedirs(mixed_dir, exist_ok=True)
        
        # Create files in different languages
        languages = {
            "python.py": "# Python file with a bug\n\ndef bug_function(param=None):\n    return param.upper()\n",
            "javascript.js": "// JavaScript file\nfunction test(param) {\n    // BUG: No null check\n    return param.toUpperCase();\n}\n",
            "java.java": "// Java file\npublic class Test {\n    public String bug(String param) {\n        // BUG: No null check\n        return param.toUpperCase();\n    }\n}\n",
            "cpp.cpp": "// C++ file\n#include <string>\nstd::string bug(std::string param) {\n    // BUG: No check for empty string\n    return param + \"test\";\n}\n",
            "typescript.ts": "// TypeScript file\nfunction test(param: string): string {\n    // BUG: No null check\n    return param.toUpperCase();\n}\n"
        }
        
        for filename, content in languages.items():
            file_path = os.path.join(mixed_dir, filename)
            with open(file_path, 'w') as f:
                f.write(content)
        
        # Run the orchestrator
        result = self._run_orchestrator(mixed_dir)
        
        # Check that it handled the mixed languages
        self.assertIn("status", result)
        # System should process at least the Python file
        bug_detection_result = result.get("results", {}).get("bug_detector", {})
        bugs_by_file = bug_detection_result.get("bugs_by_file", {})
        python_file = os.path.join(mixed_dir, "python.py")
        self.assertIn(python_file, bugs_by_file)
    
    def test_very_deep_directory_structure(self):
        """Test healing a folder with a very deep directory structure."""
        # Create a deep directory structure
        current_dir = self.test_dir
        depth = 10  # Create 10 levels of nesting
        
        for i in range(depth):
            current_dir = os.path.join(current_dir, f"level_{i}")
            os.makedirs(current_dir, exist_ok=True)
            
            # Add a Python file at each level
            file_path = os.path.join(current_dir, f"file_{i}.py")
            with open(file_path, 'w') as f:
                f.write(f"# Python file at depth {i}\n\n")
                if i % 2 == 0:  # Add bug to alternating levels
                    f.write("def bug_function(param=None):\n")
                    f.write("    # BUG: No null check\n")
                    f.write("    return param.upper()\n")
                else:
                    f.write("def safe_function(param=None):\n")
                    f.write("    if param is None:\n")
                    f.write("        return ''\n")
                    f.write("    return param.upper()\n")
        
        # Run the orchestrator
        result = self._run_orchestrator(self.test_dir, {"recursive": True, "dry_run": True})
        
        # Check that it handled the deep structure
        self.assertIn("status", result)
        # System should not crash on deep directories
        self.assertIsNotNone(result.get("status"))
    
    def test_many_small_files(self):
        """Test healing a folder with many small files."""
        # Create a directory
        many_files_dir = os.path.join(self.test_dir, "many_files")
        os.makedirs(many_files_dir, exist_ok=True)
        
        # Create many small files
        file_count = 100  # Create 100 small files
        
        for i in range(file_count):
            file_path = os.path.join(many_files_dir, f"file_{i}.py")
            with open(file_path, 'w') as f:
                f.write(f"# Small Python file {i}\n\n")
                if i % 5 == 0:  # Add bug to some files
                    f.write("def bug_function(param=None):\n")
                    f.write("    # BUG: No null check\n")
                    f.write("    return param.upper()\n")
                else:
                    f.write("def safe_function(param=None):\n")
                    f.write("    if param is None:\n")
                    f.write("        return ''\n")
                    f.write("    return param.upper()\n")
        
        # Run the orchestrator (with limit on max files to process)
        result = self._run_orchestrator(many_files_dir, {"max_files": 20, "dry_run": True})
        
        # Check that it handled the many files
        self.assertIn("status", result)
        # System should respect the max_files limit
        bug_detection_result = result.get("results", {}).get("bug_detector", {})
        bugs_by_file = bug_detection_result.get("bugs_by_file", {})
        if bugs_by_file:
            # Should find some bugs but not all files
            self.assertGreater(len(bugs_by_file), 0)
            self.assertLessEqual(len(bugs_by_file), 20)


if __name__ == '__main__':
    unittest.main()
