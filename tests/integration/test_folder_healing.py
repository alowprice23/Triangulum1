"""
Integration tests for the folder-level self-healing system.

This test suite verifies that the entire folder-level self-healing workflow
functions correctly, with all agents working together to detect, analyze,
prioritize, fix, and verify bugs across multiple files.
"""

import unittest
import os
import tempfile
import shutil
import time
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


class TestFolderHealing(unittest.TestCase):
    """Integration tests for the folder-level self-healing system."""
    
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
        
        # Create the orchestrator
        self.orchestrator = OrchestratorAgent(
            agent_id="orchestrator",
            message_bus=self.message_bus,
            config={
                "timeout": 5,  # Short timeout for testing
                "parallel_execution": False
            }
        )
        
        # Create a temporary directory for test project
        self.test_dir = tempfile.mkdtemp()
        
        # Create a simple project with bugs
        self._create_test_project()
        
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
    
    def _create_test_project(self):
        """Create a simple test project with intentional bugs."""
        # Create directories
        os.makedirs(os.path.join(self.test_dir, "core"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "utils"), exist_ok=True)
        
        # Create a core module with a null pointer bug
        with open(os.path.join(self.test_dir, "core", "data.py"), "w") as f:
            f.write("""
# Core data module with null pointer bug

class DataManager:
    def __init__(self, config=None):
        self.config = config
    
    def get_connection_string(self):
        # BUG: No null check before accessing config
        return self.config.connection_string
    
    def get_timeout(self):
        # BUG: No null check before accessing config
        return self.config.timeout
""")
        
        # Create a utility module with a resource leak
        with open(os.path.join(self.test_dir, "utils", "file_helper.py"), "w") as f:
            f.write("""
# Utility module with resource leak

def read_file(file_path):
    # BUG: Resource leak - file not closed
    file = open(file_path, 'r')
    data = file.read()
    # Missing file.close()
    return data

def write_file(file_path, content):
    # This is done correctly
    with open(file_path, 'w') as file:
        file.write(content)
    return True
""")
        
        # Create a main file that uses both modules
        with open(os.path.join(self.test_dir, "main.py"), "w") as f:
            f.write("""
# Main module

from core.data import DataManager
from utils.file_helper import read_file, write_file

def main():
    # Create a configuration
    config = type('obj', (object,), {
        'connection_string': 'db://localhost',
        'timeout': 30
    })
    
    # Create a data manager
    manager = DataManager(config)
    connection = manager.get_connection_string()
    timeout = manager.get_timeout()
    
    print(f"Connection: {connection}, Timeout: {timeout}")
    
    # Write and read a file
    write_file("test.txt", "Hello, world!")
    content = read_file("test.txt")
    print(f"File content: {content}")

if __name__ == "__main__":
    main()
""")
        
        # Create an __init__.py file in each directory
        for dir_path in [
            os.path.join(self.test_dir),
            os.path.join(self.test_dir, "core"),
            os.path.join(self.test_dir, "utils")
        ]:
            with open(os.path.join(dir_path, "__init__.py"), "w") as f:
                f.write("# Initialize package\n")
    
    def test_folder_healing_dry_run(self):
        """Test the entire folder-level healing workflow in dry run mode."""
        # Create a task request message
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "orchestrate_folder_healing",
                "folder_path": self.test_dir,
                "options": {
                    "dry_run": True,
                    "max_files": 10,
                    "analysis_depth": 2
                }
            },
            sender="test_handler",
            recipient="orchestrator"
        )
        
        # Process the message
        self.orchestrator.handle_message(message)
        
        # Wait for the result (with timeout)
        start_time = time.time()
        timeout = 30  # 30 seconds timeout for integration test
        
        while time.time() - start_time < timeout:
            if "orchestrator" in self.results:
                result = self.results["orchestrator"]
                
                if result.get("status") == "success":
                    break
            
            # Sleep a bit to avoid busy waiting
            time.sleep(0.1)
        
        # Check that we got a result
        self.assertIn("orchestrator", self.results)
        result = self.results["orchestrator"].get("result", {})
        
        # Check the overall structure
        self.assertEqual(result.get("target"), self.test_dir)
        self.assertIn("status", result)
        self.assertIn("files_processed", result)
        self.assertIn("files_healed", result)
        self.assertIn("files_failed", result)
        self.assertIn("bugs_detected", result)
        self.assertIn("bugs_fixed", result)
        
        # In dry run mode, bugs should be detected but not fixed
        self.assertGreater(result.get("bugs_detected", 0), 0)
        self.assertEqual(result.get("bugs_fixed", 0), 0)  # No fixes in dry run
        
        # Check that the bug detector identified both files with bugs
        bug_detection_result = result.get("results", {}).get("bug_detector", {})
        bugs_by_file = bug_detection_result.get("bugs_by_file", {})
        
        self.assertGreaterEqual(len(bugs_by_file), 2)  # At least 2 files with bugs
        
        # Verify the specific files were identified
        core_data_path = os.path.join(self.test_dir, "core", "data.py")
        utils_file_helper_path = os.path.join(self.test_dir, "utils", "file_helper.py")
        
        self.assertIn(core_data_path, bugs_by_file)
        self.assertIn(utils_file_helper_path, bugs_by_file)
        
        # Verify that bug types were correctly identified
        core_bugs = bugs_by_file.get(core_data_path, [])
        utils_bugs = bugs_by_file.get(utils_file_helper_path, [])
        
        core_bug_types = [bug.get("pattern_id") for bug in core_bugs]
        utils_bug_types = [bug.get("pattern_id") for bug in utils_bugs]
        
        self.assertIn("null_pointer", core_bug_types)
        self.assertIn("resource_leak", utils_bug_types)
        
        # Check that priorities were assigned
        priority_result = result.get("results", {}).get("priority_analyzer", {})
        file_priorities = priority_result.get("file_priorities", {})
        ranked_files = priority_result.get("ranked_files", [])
        
        self.assertGreaterEqual(len(file_priorities), 2)  # At least 2 files prioritized
        self.assertGreaterEqual(len(ranked_files), 2)  # At least 2 files ranked
        
        # Verify that the original files weren't modified (dry run)
        with open(os.path.join(self.test_dir, "core", "data.py"), "r") as f:
            core_content = f.read()
        with open(os.path.join(self.test_dir, "utils", "file_helper.py"), "r") as f:
            utils_content = f.read()
        
        # Check that the bug patterns are still present
        self.assertIn("return self.config.connection_string", core_content)
        self.assertIn("# Missing file.close()", utils_content)
    
    def test_orchestrator_real_healing_simulation(self):
        """
        Test that the orchestrator correctly simulates a real healing process.
        
        Instead of actually modifying files, this test mocks the key methods
        to simulate the healing process without modifying real files.
        """
        # Create a copy of our test directory
        sim_dir = tempfile.mkdtemp()
        try:
            # Copy test project to simulation directory
            shutil.copytree(self.test_dir, sim_dir, dirs_exist_ok=True)
            
            # Create a simulated message
            message = AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                content={
                    "action": "orchestrate_folder_healing",
                    "folder_path": sim_dir,
                    "options": {"dry_run": False}
                },
                sender="test_handler",
                recipient="orchestrator"
            )
            
            # Replace the orchestrator's _heal_single_file_in_folder method
            # with a version that pretends to fix bugs
            original_heal = self.orchestrator._heal_single_file_in_folder
            
            def mock_heal_file(*args, **kwargs):
                # Pretend the file was healed successfully
                return {"status": "success", "bugs_fixed": 1}
            
            self.orchestrator._heal_single_file_in_folder = mock_heal_file
            
            # Replace the _run_integration_tests method
            original_tests = self.orchestrator._run_integration_tests
            
            def mock_run_tests(*args, **kwargs):
                # Pretend the integration tests passed
                return {"status": "success", "tests_passed": 1, "tests_failed": 0}
            
            self.orchestrator._run_integration_tests = mock_run_tests
            
            try:
                # Process the message
                self.orchestrator.handle_message(message)
                
                # Wait for the result
                start_time = time.time()
                timeout = 30
                
                while time.time() - start_time < timeout:
                    if "orchestrator" in self.results:
                        result = self.results["orchestrator"]
                        
                        if result.get("status") == "success":
                            break
                    
                    # Sleep a bit
                    time.sleep(0.1)
                
                # Check the result
                self.assertIn("orchestrator", self.results)
                result = self.results["orchestrator"].get("result", {})
                
                # In a real healing scenario, bugs should be fixed
                self.assertGreater(result.get("bugs_detected", 0), 0)
                self.assertGreater(result.get("bugs_fixed", 0), 0)
                
                # Check that files were marked as healed
                self.assertGreater(len(result.get("files_healed", [])), 0)
                
            finally:
                # Restore original methods
                self.orchestrator._heal_single_file_in_folder = original_heal
                self.orchestrator._run_integration_tests = original_tests
        
        finally:
            # Clean up the simulation directory
            shutil.rmtree(sim_dir)


if __name__ == '__main__':
    unittest.main()
