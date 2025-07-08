"""
Unit tests for the RelationshipAnalystAgent.

These tests ensure that the RelationshipAnalystAgent correctly analyzes
code relationships, identifies central files, detects cycles, and prioritizes
files for repair.
"""

import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from triangulum_lx.agents.relationship_analyst_agent import RelationshipAnalystAgent
from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.tooling.graph_models import DependencyGraph, FileNode, LanguageType, DependencyMetadata, DependencyType
from triangulum_lx.tooling.dependency_graph import DependencyAnalyzer


class TestRelationshipAnalystAgent(unittest.TestCase):
    """Test cases for the RelationshipAnalystAgent."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory for the test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create the agent with a mock message bus
        self.message_bus = MagicMock()
        self.agent = RelationshipAnalystAgent(
            agent_id="test_analyst",
            agent_type="relationship_analyst",
            message_bus=self.message_bus,
            max_workers=1,
            cache_dir=None
        )
        
        # Create a simple graph for testing
        self.create_test_graph()
    
    def tearDown(self):
        """Clean up after the tests."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def create_test_graph(self):
        """Create a test dependency graph."""
        # Create a graph with a specific structure:
        # file1 -> file2 -> file4
        #       -> file3 -> file5
        #          file5 -> file1 (creates a cycle)
        
        self.graph = DependencyGraph()
        
        # Add nodes
        for i in range(1, 6):
            node = FileNode(path=f"file{i}.py", language=LanguageType.PYTHON)
            self.graph.add_node(node)
        
        # Add edges
        metadata = DependencyMetadata(dependency_type=DependencyType.IMPORT)
        
        self.graph.add_edge("file1.py", "file2.py", metadata)
        self.graph.add_edge("file1.py", "file3.py", metadata)
        self.graph.add_edge("file2.py", "file4.py", metadata)
        self.graph.add_edge("file3.py", "file5.py", metadata)
        self.graph.add_edge("file5.py", "file1.py", metadata)
        
        # Create an analyzer for the graph
        self.analyzer = DependencyAnalyzer(self.graph)
        
        # Set the graph and analyzer on the agent
        self.agent.graph = self.graph
        self.agent.analyzer = self.analyzer
    
    def create_test_project(self):
        """Create a test project with a specific dependency structure."""
        # Project structure:
        # src/
        #   main.py         (imports util.py, models.py)
        #   util.py         (imports helpers.py)
        #   models.py       (imports db.py)
        #   helpers.py      (no imports)
        #   db.py           (no imports)
        
        src_dir = os.path.join(self.temp_dir, "src")
        os.makedirs(src_dir, exist_ok=True)
        
        # Create main.py
        with open(os.path.join(src_dir, "main.py"), "w") as f:
            f.write("""
from . import util
from . import models

def main():
    print("Main")
    util.helper_func()
    models.get_model()
""")
        
        # Create util.py
        with open(os.path.join(src_dir, "util.py"), "w") as f:
            f.write("""
from . import helpers

def helper_func():
    print("Helper function")
    helpers.internal_helper()
""")
        
        # Create models.py
        with open(os.path.join(src_dir, "models.py"), "w") as f:
            f.write("""
from . import db

def get_model():
    print("Get model")
    return db.get_data()
""")
        
        # Create helpers.py
        with open(os.path.join(src_dir, "helpers.py"), "w") as f:
            f.write("""
def internal_helper():
    print("Internal helper")
""")
        
        # Create db.py
        with open(os.path.join(src_dir, "db.py"), "w") as f:
            f.write("""
def get_data():
    print("Get data")
    return {"data": "value"}
""")
        
        # Create __init__.py to make it a package
        with open(os.path.join(src_dir, "__init__.py"), "w") as f:
            f.write("")
    
    def test_analyze_codebase(self):
        """Test analyzing a codebase."""
        # Create a test project
        self.create_test_project()
        
        # Mock the build_graph method to avoid actual file system operations
        with patch('triangulum_lx.tooling.dependency_graph.DependencyGraphBuilder.build_graph', return_value=self.graph):
            # Analyze the codebase
            summary = self.agent.analyze_codebase(self.temp_dir)
            
            # Verify the summary
            self.assertEqual(summary["files_analyzed"], 5)
            self.assertEqual(summary["dependencies_found"], 5)
            self.assertEqual(summary["cycles_detected"], 1)
            self.assertIn("PYTHON", summary["languages_detected"])
    
    def test_get_most_central_files(self):
        """Test getting the most central files."""
        # Get the most central files
        central_files = self.agent.get_most_central_files(n=2)
        
        # Verify the results
        self.assertEqual(len(central_files), 2)
        # file1.py and file5.py should be the most central due to the cycle
        central_file_paths = [file_path for file_path, _ in central_files]
        self.assertIn("file1.py", central_file_paths)
    
    def test_find_cycles(self):
        """Test finding cycles in the dependency graph."""
        # Find cycles
        cycles = self.agent.find_cycles()
        
        # Verify the results
        self.assertEqual(len(cycles), 1)
        cycle = cycles[0]
        self.assertEqual(len(cycle), 3)
        # The cycle should include file1, file3, and file5
        self.assertIn("file1.py", cycle)
        self.assertIn("file3.py", cycle)
        self.assertIn("file5.py", cycle)
    
    def test_get_file_dependents(self):
        """Test getting file dependents."""
        # Get direct dependents of file2.py
        dependents = self.agent.get_file_dependents("file2.py")
        self.assertEqual(len(dependents), 1)
        self.assertIn("file1.py", dependents)
        
        # Get transitive dependents of file2.py
        dependents = self.agent.get_file_dependents("file2.py", transitive=True)
        self.assertEqual(len(dependents), 3)  # file1.py, file3.py, file5.py
    
    def test_get_file_dependencies(self):
        """Test getting file dependencies."""
        # Get direct dependencies of file1.py
        dependencies = self.agent.get_file_dependencies("file1.py")
        self.assertEqual(len(dependencies), 2)
        self.assertIn("file2.py", dependencies)
        self.assertIn("file3.py", dependencies)
        
        # Get transitive dependencies of file1.py
        dependencies = self.agent.get_file_dependencies("file1.py", transitive=True)
        # Should include file2.py, file3.py, file4.py, file5.py, and possibly file1.py itself due to the cycle
        self.assertGreaterEqual(len(dependencies), 4)  
        self.assertIn("file2.py", dependencies)
        self.assertIn("file3.py", dependencies)
        self.assertIn("file4.py", dependencies)
        self.assertIn("file5.py", dependencies)
    
    def test_prioritize_files_for_repair(self):
        """Test prioritizing files for repair."""
        # Prioritize all files
        priorities = self.agent.prioritize_files_for_repair()
        
        # Verify the results
        self.assertEqual(len(priorities), 5)
        # Check that important files are in the priorities
        priority_files = [p[0] for p in priorities]
        self.assertIn("file1.py", priority_files)
        self.assertIn("file5.py", priority_files)  # Part of the cycle
    
    def test_get_impacted_files(self):
        """Test getting impacted files."""
        # Get files impacted by changes to file2.py
        impacted = self.agent.get_impacted_files(["file2.py"])
        
        # Verify the results
        self.assertEqual(len(impacted), 3)  # file1.py, file3.py, file5.py due to the cycle
    
    def test_handle_task_request_analyze_codebase(self):
        """Test handling a task request to analyze a codebase."""
        # Create a mock message
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "analyze_codebase",
                "root_dir": self.temp_dir
            },
            sender="test_sender"
        )
        
        # Mock the analyze_codebase method
        with patch.object(self.agent, 'analyze_codebase', return_value={"files_analyzed": 5}):
            # Handle the message
            self.agent._handle_task_request(message)
            
            # Verify that send_response was called with the correct arguments
            self.agent.message_bus.publish.assert_called_once()
            response_msg = self.agent.message_bus.publish.call_args[0][0]
            self.assertEqual(response_msg.message_type, MessageType.TASK_RESULT)
            self.assertEqual(response_msg.content["status"], "success")
            self.assertEqual(response_msg.content["summary"]["files_analyzed"], 5)
    
    def test_handle_query_central_files(self):
        """Test handling a query for central files."""
        # Create a mock message
        message = AgentMessage(
            message_type=MessageType.QUERY,
            content={
                "query_type": "central_files",
                "n": 2,
                "metric": "pagerank"
            },
            sender="test_sender"
        )
        
        # Mock the get_most_central_files method
        with patch.object(self.agent, 'get_most_central_files', return_value=[("file1.py", 0.5), ("file5.py", 0.3)]):
            # Handle the message
            self.agent._handle_query(message)
            
            # Verify that send_response was called with the correct arguments
            self.agent.message_bus.publish.assert_called_once()
            response_msg = self.agent.message_bus.publish.call_args[0][0]
            self.assertEqual(response_msg.message_type, MessageType.QUERY_RESPONSE)
            self.assertEqual(response_msg.content["status"], "success")
            self.assertEqual(len(response_msg.content["central_files"]), 2)
            self.assertEqual(response_msg.content["central_files"][0][0], "file1.py")
    
    def test_handle_query_file_dependencies(self):
        """Test handling a query for file dependencies."""
        # Create a mock message
        message = AgentMessage(
            message_type=MessageType.QUERY,
            content={
                "query_type": "file_dependencies",
                "file_path": "file1.py",
                "transitive": False
            },
            sender="test_sender"
        )
        
        # Mock the get_file_dependencies method
        with patch.object(self.agent, 'get_file_dependencies', return_value={"file2.py", "file3.py"}):
            # Handle the message
            self.agent._handle_query(message)
            
            # Verify that send_response was called with the correct arguments
            self.agent.message_bus.publish.assert_called_once()
            response_msg = self.agent.message_bus.publish.call_args[0][0]
            self.assertEqual(response_msg.message_type, MessageType.QUERY_RESPONSE)
            self.assertEqual(response_msg.content["status"], "success")
            self.assertEqual(len(response_msg.content["dependencies"]), 2)
            self.assertIn("file2.py", response_msg.content["dependencies"])
            self.assertIn("file3.py", response_msg.content["dependencies"])
    
    def test_error_handling(self):
        """Test error handling in message processing."""
        # Create a mock message with an invalid query type
        message = AgentMessage(
            message_type=MessageType.QUERY,
            content={
                "query_type": "invalid_query"
            },
            sender="test_sender"
        )
        
        # Handle the message
        self.agent._handle_query(message)
        
        # Verify that send_response was called with an error message
        self.agent.message_bus.publish.assert_called_once()
        response_msg = self.agent.message_bus.publish.call_args[0][0]
        self.assertEqual(response_msg.message_type, MessageType.ERROR)
        self.assertEqual(response_msg.content["status"], "error")
        self.assertIn("Unknown query type", response_msg.content["error"])
    
    def test_process_message(self):
        """Test the process_message method."""
        # Test with a valid action
        with patch.object(self.agent, 'analyze_codebase', return_value={"files_analyzed": 5}):
            result = self.agent.process_message({
                "action": "analyze_codebase",
                "root_dir": self.temp_dir
            })
            
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["summary"]["files_analyzed"], 5)
        
        # Test with an invalid action
        result = self.agent.process_message({
            "action": "invalid_action"
        })
        
        self.assertEqual(result["status"], "error")
        self.assertIn("Unknown action", result["message"])


if __name__ == "__main__":
    unittest.main()
