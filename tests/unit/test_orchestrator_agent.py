"""
Unit tests for the OrchestratorAgent.

This test suite verifies that the OrchestratorAgent correctly coordinates
the workflow between specialized agents in the Triangulum self-healing system.
"""

import unittest
import os
import tempfile
import time
from unittest import mock
from pathlib import Path
from datetime import datetime, timedelta

from triangulum_lx.agents.orchestrator_agent import OrchestratorAgent, TaskPriority, Task
from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.message_bus import MessageBus


class MockMessageBus:
    """Mock message bus for testing."""
    
    def __init__(self):
        self.messages = []
        self.handlers = {}
        self.subscriptions = {}
    
    def publish(self, message):
        """Record published messages."""
        self.messages.append(message)
    
    def register_handler(self, agent_id, message_type, handler):
        """Register a message handler."""
        key = (agent_id, message_type)
        self.handlers[key] = handler
    
    def subscribe(self, agent_id, message_types, handler):
        """Subscribe agent to message types."""
        for message_type in message_types:
            key = (agent_id, message_type)
            self.subscriptions[key] = handler
    
    def unsubscribe(self, agent_id, message_types=None):
        """Unsubscribe agent from message types."""
        if message_types is None:
            # Remove all subscriptions for this agent
            self.subscriptions = {k: v for k, v in self.subscriptions.items() if k[0] != agent_id}
        else:
            for message_type in message_types:
                key = (agent_id, message_type)
                if key in self.subscriptions:
                    del self.subscriptions[key]
    
    def simulate_response(self, sender, message_type, content):
        """Simulate a response from an agent."""
        message = AgentMessage(
            message_type=message_type,
            content=content,
            sender=sender,
            receiver="orchestrator"
        )
        # Find the handler
        key = ("orchestrator", message_type)
        if key in self.handlers:
            self.handlers[key](message)
        elif key in self.subscriptions:
            self.subscriptions[key](message)


class TestOrchestratorAgent(unittest.TestCase):
    """Test case for the OrchestratorAgent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.message_bus = MockMessageBus()
        
        # Patch the _register_with_message_bus method to prevent it from trying to use MessageBus.subscribe
        with mock.patch('triangulum_lx.agents.base_agent.BaseAgent._register_with_message_bus'):
            self.orchestrator = OrchestratorAgent(
                agent_id="orchestrator",
                message_bus=self.message_bus,
                config={"timeout": 0.1}  # Short timeout for testing
            )
        
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".py")
        self.temp_file.write(b"# Test file\n\ndef test_func():\n    return None\n")
        self.temp_file.close()
    
    def tearDown(self):
        """Tear down test fixtures."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_initialization(self):
        """Test that the agent initializes correctly."""
        self.assertEqual(self.orchestrator.agent_id, "orchestrator")
        self.assertEqual(self.orchestrator.agent_type, "orchestrator")
        self.assertIsNotNone(self.orchestrator.message_bus)
        self.assertEqual(len(self.orchestrator.file_workflow), 5)
        self.assertEqual(len(self.orchestrator.folder_workflow), 7)
        
        # Check that task distribution system is initialized
        self.assertIsNotNone(self.orchestrator.task_queue)
        self.assertIsNotNone(self.orchestrator.agent_registry)
        self.assertIsNotNone(self.orchestrator.task_distribution_thread)
        self.assertTrue(len(self.orchestrator.worker_threads) > 0)
    
    def test_handle_task_request_file_healing(self):
        """Test handling a file healing task request."""
        # Create a task request message
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "orchestrate_file_healing",
                "file_path": self.temp_file.name
            },
            sender="test_sender",
            receiver="orchestrator"
        )
        
        # Mock the orchestrate_file_healing method
        with mock.patch.object(self.orchestrator, 'orchestrate_file_healing') as mock_orchestrate:
            mock_orchestrate.return_value = {"status": "completed"}
            
            # Handle the message
            self.orchestrator.handle_message(message)
            
            # Check that orchestrate_file_healing was called with the right arguments
            mock_orchestrate.assert_called_once_with(self.temp_file.name, {})
            
            # Check that a response was sent
            self.assertEqual(len(self.message_bus.messages), 1)
            response = self.message_bus.messages[0]
            self.assertEqual(response.message_type, MessageType.TASK_RESULT)
            self.assertEqual(response.sender, "orchestrator")
            self.assertEqual(response.receiver, "test_sender")
            self.assertEqual(response.content["status"], "success")
    
    def test_handle_task_request_folder_healing(self):
        """Test handling a folder healing task request."""
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Create a task request message
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "orchestrate_folder_healing",
                "folder_path": temp_dir
            },
            sender="test_sender",
            receiver="orchestrator"
        )
        
        # Mock the orchestrate_folder_healing method
        with mock.patch.object(self.orchestrator, 'orchestrate_folder_healing') as mock_orchestrate:
            mock_orchestrate.return_value = {"status": "completed"}
            
            # Handle the message
            self.orchestrator.handle_message(message)
            
            # Check that orchestrate_folder_healing was called with the right arguments
            mock_orchestrate.assert_called_once_with(temp_dir, {})
            
            # Check that a response was sent
            self.assertEqual(len(self.message_bus.messages), 1)
            response = self.message_bus.messages[0]
            self.assertEqual(response.message_type, MessageType.TASK_RESULT)
            self.assertEqual(response.sender, "orchestrator")
            self.assertEqual(response.receiver, "test_sender")
            self.assertEqual(response.content["status"], "success")
        
        # Clean up
        os.rmdir(temp_dir)
    
    def test_execute_workflow_step(self):
        """Test executing a workflow step."""
        workflow_id = "test_workflow"
        agent_type = "bug_detector"
        workflow_state = {
            "target": self.temp_file.name,
            "results": {}
        }
        
        # Mock the _prepare_bug_detector_message method
        with mock.patch.object(self.orchestrator, '_prepare_bug_detector_message') as mock_prepare:
            mock_prepare.return_value = AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                content={"workflow_id": workflow_id},
                sender="orchestrator",
                receiver="bug_detector"
            )
            
            # Mock the _wait_for_result method
            with mock.patch.object(self.orchestrator, '_wait_for_result') as mock_wait:
                mock_wait.return_value = {"status": "success", "bugs": []}
                
                # Execute the workflow step
                result = self.orchestrator._execute_workflow_step(workflow_id, agent_type, workflow_state)
                
                # Check that the methods were called with the right arguments
                mock_prepare.assert_called_once_with(workflow_id, self.temp_file.name)
                mock_wait.assert_called_once_with(workflow_id, agent_type, self.orchestrator.timeout)
                
                # Check the result
                self.assertEqual(result["status"], "success")
                self.assertEqual(result["bugs"], [])
    
    def test_orchestrate_file_healing_with_bug(self):
        """Test orchestrating file healing with a bug."""
        # Set up mock responses
        bug_detection_result = {
            "status": "success",
            "bugs": [{"pattern_id": "null_pointer", "line": 2, "severity": "high"}]
        }
        relationship_result = {
            "status": "success",
            "relationships": {}
        }
        strategy_result = {
            "status": "success",
            "strategy": {"name": "add_null_check", "approach": "defensive"}
        }
        implementation_result = {
            "status": "success",
            "implementation": {"patches": [{"file_path": self.temp_file.name}]}
        }
        verification_result = {
            "status": "success",
            "verification_result": {"overall_success": True}
        }
        
        # Mock the _execute_workflow_step method to return different results based on agent_type
        def mock_execute_workflow_step(workflow_id, agent_type, workflow_state):
            if agent_type == "bug_detector":
                return bug_detection_result
            elif agent_type == "relationship_analyst":
                return relationship_result
            elif agent_type == "strategy":
                return strategy_result
            elif agent_type == "implementation":
                return implementation_result
            elif agent_type == "verification":
                return verification_result
            return {"status": "failed"}
        
        # Replace the _execute_workflow_step method
        self.orchestrator._execute_workflow_step = mock_execute_workflow_step
        
        # Orchestrate file healing
        result = self.orchestrator.orchestrate_file_healing(self.temp_file.name)
        
        # Check the result
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["target"], self.temp_file.name)
        self.assertEqual(len(result["steps_completed"]), 5)
        self.assertEqual(len(result["steps_failed"]), 0)
        
        # Check that the results were stored
        self.assertEqual(result["results"]["bug_detector"], bug_detection_result)
        self.assertEqual(result["results"]["strategy"], strategy_result)
    
    def test_orchestrate_folder_healing(self):
        """Test orchestrating folder healing."""
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Set up mock responses
        bug_detection_result = {
            "status": "success",
            "bugs_by_file": {
                self.temp_file.name: [{"pattern_id": "null_pointer", "line": 2, "severity": "high"}]
            }
        }
        relationship_result = {
            "status": "success",
            "relationships": {}
        }
        priority_result = {
            "status": "success",
            "file_priorities": {
                self.temp_file.name: {"priority": 0.8, "bug_count": 1}
            },
            "ranked_files": [self.temp_file.name]
        }
        
        # Mock the _execute_folder_analysis_step method
        def mock_execute_folder_analysis_step(workflow_id, agent_type, folder_path, workflow_state):
            if agent_type == "bug_detector":
                return bug_detection_result
            elif agent_type == "relationship_analyst":
                return relationship_result
            elif agent_type == "priority_analyzer":
                return priority_result
            return {"status": "failed"}
        
        # Replace the _execute_folder_analysis_step method
        self.orchestrator._execute_folder_analysis_step = mock_execute_folder_analysis_step
        
        # Mock the _heal_single_file_in_folder method
        with mock.patch.object(self.orchestrator, '_heal_single_file_in_folder') as mock_heal:
            mock_heal.return_value = {"status": "success", "bugs_fixed": 1}
            
            # Mock the _run_integration_tests method
            with mock.patch.object(self.orchestrator, '_run_integration_tests') as mock_tests:
                mock_tests.return_value = {"status": "success", "tests_passed": 1}
                
                # Mock the _get_prioritized_files method
                with mock.patch.object(self.orchestrator, '_get_prioritized_files') as mock_prioritize:
                    mock_prioritize.return_value = [
                        {"file_path": self.temp_file.name, "bugs": bug_detection_result["bugs_by_file"][self.temp_file.name]}
                    ]
                    
                    # Orchestrate folder healing
                    result = self.orchestrator.orchestrate_folder_healing(temp_dir)
                    
                    # Check the result
                    self.assertEqual(result["status"], "completed")
                    self.assertEqual(result["target"], temp_dir)
                    self.assertEqual(len(result["steps_completed"]), 4)  # 3 analysis steps + integration_tester
                    self.assertEqual(len(result["files_healed"]), 1)
                    self.assertEqual(result["bugs_fixed"], 1)
        
        # Clean up
        os.rmdir(temp_dir)


    def test_task_queue(self):
        """Test task queue functionality."""
        # Create a task
        task = Task(
            id="test_task_1",
            type="file_healing",
            priority=TaskPriority.HIGH,
            content={"file_path": self.temp_file.name},
            workflow_id="workflow_1",
            created_at=datetime.now()
        )
        
        # Add task to queue
        self.orchestrator.task_queue.add_task(task)
        
        # Check task was added
        retrieved_task = self.orchestrator.task_queue.get_task("test_task_1")
        self.assertIsNotNone(retrieved_task)
        self.assertEqual(retrieved_task.id, "test_task_1")
        self.assertEqual(retrieved_task.priority, TaskPriority.HIGH)
        
        # Test get_tasks_by_status
        pending_tasks = self.orchestrator.task_queue.get_tasks_by_status("pending")
        self.assertEqual(len(pending_tasks), 1)
        self.assertEqual(pending_tasks[0].id, "test_task_1")
        
        # Test priority-based retrieval
        next_task = self.orchestrator.task_queue.get_next_task()
        self.assertIsNotNone(next_task)
        self.assertEqual(next_task.id, "test_task_1")
        
        # Test task removal
        self.orchestrator.task_queue.remove_task("test_task_1")
        self.assertIsNone(self.orchestrator.task_queue.get_task("test_task_1"))
    
    def test_agent_registry(self):
        """Test agent registry functionality."""
        # Register an agent
        self.orchestrator.agent_registry.register_agent(
            agent_id="test_agent",
            agent_type="bug_detector",
            capabilities=["detect_bugs", "analyze_code"]
        )
        
        # Check agent retrieval by capability
        agent_id = self.orchestrator.agent_registry.get_agent_for_capability("detect_bugs")
        self.assertEqual(agent_id, "test_agent")
        
        # Check agent availability
        is_available = self.orchestrator.agent_registry.is_agent_available("test_agent")
        self.assertTrue(is_available)
        
        # Update agent health (failure)
        self.orchestrator.agent_registry.update_agent_health(
            agent_id="test_agent",
            success=False,
            error_message="Test error"
        )
        
        # Agent should still be available after one failure
        is_available = self.orchestrator.agent_registry.is_agent_available("test_agent")
        self.assertTrue(is_available)
        
        # Multiple failures should mark agent as unavailable
        for _ in range(3):
            self.orchestrator.agent_registry.update_agent_health(
                agent_id="test_agent",
                success=False,
                error_message="Test error"
            )
        
        # Agent should now be unavailable
        is_available = self.orchestrator.agent_registry.is_agent_available("test_agent")
        self.assertFalse(is_available)
        
        # Unregister the agent
        self.orchestrator.agent_registry.unregister_agent("test_agent")
        
        # Check agent is no longer available
        agent_id = self.orchestrator.agent_registry.get_agent_for_capability("detect_bugs")
        self.assertIsNone(agent_id)
    
    def test_enqueue_task(self):
        """Test enqueuing a task."""
        # Mock the task_event.set method
        with mock.patch.object(self.orchestrator.task_event, 'set') as mock_set:
            # Enqueue a task with basic parameters
            task_id = self.orchestrator.enqueue_task(
                task_type="file_healing",
                content={"file_path": self.temp_file.name},
                priority=TaskPriority.CRITICAL,
                sender="test_sender"
            )
            
            # Check task was added to queue
            task = self.orchestrator.task_queue.get_task(task_id)
            self.assertIsNotNone(task)
            self.assertEqual(task.type, "file_healing")
            self.assertEqual(task.priority, TaskPriority.CRITICAL)
            self.assertEqual(task.content["file_path"], self.temp_file.name)
            self.assertEqual(task.required_capabilities, [])
            self.assertIsNone(task.target_agent_type)
            
            # Check metadata was added
            self.assertIn("_metadata", task.content)
            self.assertEqual(task.content["_metadata"]["task_id"], task_id)
            
            # Check task_event was set
            mock_set.assert_called_once()
            
            # Reset the mock
            mock_set.reset_mock()
            
            # Enqueue a task with capabilities and target agent
            task_id2 = self.orchestrator.enqueue_task(
                task_type="bug_detection",
                content={"file_path": self.temp_file.name},
                priority=TaskPriority.HIGH,
                sender="test_sender",
                required_capabilities=["detect_bugs", "analyze_code"],
                target_agent_type="bug_detector"
            )
            
            # Check task was added to queue with proper parameters
            task2 = self.orchestrator.task_queue.get_task(task_id2)
            self.assertIsNotNone(task2)
            self.assertEqual(task2.type, "bug_detection")
            self.assertEqual(task2.priority, TaskPriority.HIGH)
            self.assertEqual(task2.required_capabilities, ["detect_bugs", "analyze_code"])
            self.assertEqual(task2.target_agent_type, "bug_detector")
            
            # Check task_event was set again
            mock_set.assert_called_once()
    
    def test_task_assignment_with_capabilities(self):
        """Test task assignment based on agent capabilities."""
        # Register agents with different capabilities
        self.orchestrator.agent_registry.register_agent(
            agent_id="agent1",
            agent_type="bug_detector",
            capabilities=["detect_bugs"]
        )
        self.orchestrator.agent_registry.register_agent(
            agent_id="agent2",
            agent_type="analyzer",
            capabilities=["analyze_code", "detect_bugs"]
        )
        self.orchestrator.agent_registry.register_agent(
            agent_id="agent3",
            agent_type="implementation",
            capabilities=["implement_fixes"]
        )
        
        # Test agent assignment with single capability
        task1 = Task(
            id="task1",
            type="bug_detection",
            priority=TaskPriority.HIGH,
            content={},
            workflow_id="workflow1",
            created_at=datetime.now(),
            required_capabilities=["detect_bugs"]
        )
        assigned_agent = self.orchestrator._assign_task_to_agent(task1)
        self.assertIn(assigned_agent, ["agent1", "agent2"])  # Either agent with the capability
        
        # Test agent assignment with multiple capabilities
        task2 = Task(
            id="task2",
            type="code_analysis",
            priority=TaskPriority.MEDIUM,
            content={},
            workflow_id="workflow2",
            created_at=datetime.now(),
            required_capabilities=["analyze_code", "detect_bugs"]
        )
        assigned_agent = self.orchestrator._assign_task_to_agent(task2)
        self.assertEqual(assigned_agent, "agent2")  # Only agent2 has both capabilities
        
        # Test assignment with non-existent capability
        task3 = Task(
            id="task3",
            type="optimization",
            priority=TaskPriority.LOW,
            content={},
            workflow_id="workflow3",
            created_at=datetime.now(),
            required_capabilities=["optimize_code"]
        )
        assigned_agent = self.orchestrator._assign_task_to_agent(task3)
        self.assertIsNone(assigned_agent)  # No agent has this capability
        
        # Test assignment with target agent type
        task4 = Task(
            id="task4",
            type="implementation",
            priority=TaskPriority.CRITICAL,
            content={},
            workflow_id="workflow4",
            created_at=datetime.now(),
            target_agent_type="implementation"
        )
        assigned_agent = self.orchestrator._assign_task_to_agent(task4)
        self.assertEqual(assigned_agent, "agent3")  # Direct match by agent type
    
    def test_unavailable_agent_handling(self):
        """Test handling when agents are unavailable."""
        # Register an agent
        self.orchestrator.agent_registry.register_agent(
            agent_id="agent1",
            agent_type="bug_detector",
            capabilities=["detect_bugs"]
        )
        
        # Mark the agent as unavailable after multiple failures
        for _ in range(3):
            self.orchestrator.agent_registry.update_agent_health(
                agent_id="agent1",
                success=False,
                error_message="Test error"
            )
        
        # Confirm agent is unavailable
        self.assertFalse(self.orchestrator.agent_registry.is_agent_available("agent1"))
        
        # Create a task that requires the unavailable agent
        task = Task(
            id="task1",
            type="bug_detection",
            priority=TaskPriority.HIGH,
            content={},
            workflow_id="workflow1",
            created_at=datetime.now(),
            required_capabilities=["detect_bugs"]
        )
        
        # Attempt to assign the task
        assigned_agent = self.orchestrator._assign_task_to_agent(task)
        self.assertIsNone(assigned_agent)  # No available agent
        
        # Mark the agent as successful again to make it available
        self.orchestrator.agent_registry.update_agent_health(
            agent_id="agent1",
            success=True
        )
        
        # Confirm agent is now available
        self.assertTrue(self.orchestrator.agent_registry.is_agent_available("agent1"))
        
        # Try assigning the task again
        assigned_agent = self.orchestrator._assign_task_to_agent(task)
        self.assertEqual(assigned_agent, "agent1")  # Now agent is available


if __name__ == '__main__':
    unittest.main()
