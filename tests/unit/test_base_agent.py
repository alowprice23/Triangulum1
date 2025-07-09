"""
Unit tests for the base agent functionality.

This module contains tests for the BaseAgent abstract class and agent factory,
verifying the core agent functionality and interfaces.
"""

import unittest
from unittest.mock import MagicMock, patch, call

from triangulum_lx.agents.message import AgentMessage, MessageType, ConfidenceLevel
# from triangulum_lx.agents.message_bus import MessageBus # Old
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus # New
from triangulum_lx.agents.base_agent import BaseAgent
from triangulum_lx.agents.agent_factory import AgentFactory
from triangulum_lx.monitoring.metrics import MetricsCollector # For mocking
# from triangulum_lx.core.monitor import OperationProgress # For mocking engine_monitor if needed


# Concrete implementation of BaseAgent for testing
class TestAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""
    
    def __init__(self, **kwargs):
        # Make sure to set agent_type to test_agent
        kwargs["agent_type"] = "test_agent"
        super().__init__(**kwargs)
        self.task_requests_handled = []
        self.queries_handled = []
    
    def _handle_task_request(self, message: AgentMessage) -> None:
        self.task_requests_handled.append(message)
        self.send_response(
            original_message=message,
            message_type=MessageType.TASK_RESULT,
            content={"result": f"Handled task: {message.content.get('task', 'unknown')}"}
        )
    
    def _handle_query(self, message: AgentMessage) -> None:
        self.queries_handled.append(message)
        self.send_response(
            original_message=message,
            message_type=MessageType.QUERY_RESPONSE,
            content={"answer": f"Answered query: {message.content.get('query', 'unknown')}"}
        )


class TestBaseAgent(unittest.TestCase):
    """Test case for the BaseAgent class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.message_bus_mock = MagicMock(spec=EnhancedMessageBus)
        self.metrics_collector_mock = MagicMock(spec=MetricsCollector)
        self.engine_monitor_mock = MagicMock() # Generic mock for engine_monitor

        self.agent = TestAgent(
            agent_id="test_agent_1",
            message_bus=self.message_bus_mock,
            config={"test_config": "value"},
            metrics_collector=self.metrics_collector_mock,
            engine_monitor=self.engine_monitor_mock
        )
    
    def test_initialization(self):
        """Test agent initialization."""
        self.assertEqual(self.agent.agent_id, "test_agent_1")
        self.assertEqual(self.agent.agent_type, "test_agent")
        self.assertEqual(self.agent.config, {"test_config": "value"})
        self.assertFalse(self.agent._is_initialized)
        
        # Test auto-generated ID
        agent2 = TestAgent(agent_type="test_agent")
        self.assertTrue(agent2.agent_id.startswith("test_agent_"))
        self.assertNotEqual(agent2.agent_id, "test_agent_")
    
    def test_register_with_message_bus(self):
        """Test registration with message bus."""
        self.message_bus_mock.subscribe.assert_called_once()
        call_args = self.message_bus_mock.subscribe.call_args[1]
        self.assertEqual(call_args["agent_id"], "test_agent_1")
        self.assertEqual(call_args["callback"], self.agent.handle_message)
    
    def test_initialize(self):
        """Test agent initialization."""
        self.assertFalse(self.agent._is_initialized)
        result = self.agent.initialize()
        self.assertTrue(result)
        self.assertTrue(self.agent._is_initialized)
    
    def test_shutdown(self):
        """Test agent shutdown."""
        self.agent.shutdown()
        self.message_bus_mock.unsubscribe.assert_called_once_with(self.agent.agent_id)
    
    def test_handle_message_task_request(self):
        """Test handling task request messages."""
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "test task"},
            sender="sender_agent"
        )
        
        self.agent.handle_message(message)
        
        self.assertEqual(len(self.agent.task_requests_handled), 1)
        self.assertEqual(self.agent.task_requests_handled[0], message)
        self.message_bus_mock.publish.assert_called_once()
        
        # Check response message
        response = self.message_bus_mock.publish.call_args[0][0]
        self.assertEqual(response.message_type, MessageType.TASK_RESULT)
        self.assertEqual(response.sender, self.agent.agent_id)
        self.assertEqual(response.receiver, "sender_agent")
        self.assertEqual(response.content["result"], "Handled task: test task")
    
    def test_handle_message_query(self):
        """Test handling query messages."""
        message = AgentMessage(
            message_type=MessageType.QUERY,
            content={"query": "test query"},
            sender="sender_agent"
        )
        
        self.agent.handle_message(message)
        
        self.assertEqual(len(self.agent.queries_handled), 1)
        self.assertEqual(self.agent.queries_handled[0], message)
        self.message_bus_mock.publish.assert_called_once()
        
        # Check response message
        response = self.message_bus_mock.publish.call_args[0][0]
        self.assertEqual(response.message_type, MessageType.QUERY_RESPONSE)
        self.assertEqual(response.sender, self.agent.agent_id)
        self.assertEqual(response.receiver, "sender_agent")
        self.assertEqual(response.content["answer"], "Answered query: test query")
    
    def test_handle_message_error(self):
        """Test handling error messages."""
        message = AgentMessage(
            message_type=MessageType.ERROR,
            content={"error": "test error"},
            sender="sender_agent"
        )
        
        # Need to mock the logger to verify it's called
        with patch("triangulum_lx.agents.base_agent.logger") as mock_logger:
            self.agent.handle_message(message)
            mock_logger.warning.assert_called_once()
            self.assertIn("test error", mock_logger.warning.call_args[0][0])
    
    def test_handle_message_status(self):
        """Test handling status messages."""
        message = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "test status", "agent_type": "other_agent"},
            sender="sender_agent"
        )
        
        # Need to mock the logger to verify it's called
        with patch("triangulum_lx.agents.base_agent.logger") as mock_logger:
            self.agent.handle_message(message)
            # Check that debug was called at least once with the status message
            self.assertTrue(mock_logger.debug.called)
            # Check that one of the calls contains the status message
            status_call_found = False
            for call_args in mock_logger.debug.call_args_list:
                if "test status" in call_args[0][0]:
                    status_call_found = True
                    break
            self.assertTrue(status_call_found, "Status message not found in debug calls")
    
    def test_send_message(self):
        """Test sending messages."""
        message_id = self.agent.send_message(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "test task"},
            receiver="receiver_agent",
            confidence=0.8,
            metadata={"meta": "data"}
        )
        
        self.assertIsNotNone(message_id)
        self.message_bus_mock.publish.assert_called_once()
        
        # Check message details
        message = self.message_bus_mock.publish.call_args[0][0]
        self.assertEqual(message.message_type, MessageType.TASK_REQUEST)
        self.assertEqual(message.sender, self.agent.agent_id)
        self.assertEqual(message.receiver, "receiver_agent")
        self.assertEqual(message.content["task"], "test task")
        self.assertEqual(message.confidence, 0.8)
        self.assertEqual(message.metadata["meta"], "data")
    
    def test_send_response(self):
        """Test sending response messages."""
        original_message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "test task"},
            sender="sender_agent",
            message_id="original_id",
            conversation_id="convo_id"
        )
        
        message_id = self.agent.send_response(
            original_message=original_message,
            message_type=MessageType.TASK_RESULT,
            content={"result": "test result"},
            confidence=0.9,
            metadata={"meta": "data"}
        )
        
        self.assertIsNotNone(message_id)
        self.message_bus_mock.publish.assert_called_once()
        
        # Check response details
        response = self.message_bus_mock.publish.call_args[0][0]
        self.assertEqual(response.message_type, MessageType.TASK_RESULT)
        self.assertEqual(response.sender, self.agent.agent_id)
        self.assertEqual(response.receiver, "sender_agent")
        self.assertEqual(response.parent_id, "original_id")
        self.assertEqual(response.conversation_id, "convo_id")
        self.assertEqual(response.content["result"], "test result")
        self.assertEqual(response.confidence, 0.9)
        self.assertEqual(response.metadata["meta"], "data")
    
    def test_broadcast_status(self):
        """Test broadcasting status messages."""
        message_id = self.agent.broadcast_status(
            status="test status",
            metadata={"meta": "data"}
        )
        
        self.assertIsNotNone(message_id)
        self.message_bus_mock.publish.assert_called_once()
        
        # Check status message details
        message = self.message_bus_mock.publish.call_args[0][0]
        self.assertEqual(message.message_type, MessageType.STATUS)
        self.assertEqual(message.sender, self.agent.agent_id)
        self.assertIsNone(message.receiver)  # Broadcast has no specific receiver
        self.assertEqual(message.content["status"], "test status")
        self.assertEqual(message.content["agent_type"], "test_agent")
        self.assertEqual(message.metadata["meta"], "data")
    
    def test_no_message_bus(self):
        """Test agent behavior without a message bus."""
        agent = TestAgent(agent_id="no_bus_agent")
        
        # These operations should not raise exceptions even without a message bus
        agent.initialize()
        agent.shutdown()
        
        # Sending messages should return None but not raise exceptions
        self.assertIsNone(agent.send_message(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "test"}
        ))
        
        self.assertIsNone(agent.send_response(
            original_message=MagicMock(spec=AgentMessage),
            message_type=MessageType.TASK_RESULT,
            content={"result": "test"}
        ))
        
        self.assertIsNone(agent.broadcast_status("test status"))


class TestAgentFactory(unittest.TestCase):
    """Test case for the AgentFactory class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.message_bus_mock = MagicMock(spec=EnhancedMessageBus)
        self.metrics_collector_mock = MagicMock(spec=MetricsCollector)
        self.engine_monitor_mock = MagicMock()

        self.factory = AgentFactory(
            message_bus=self.message_bus_mock,
            metrics_collector=self.metrics_collector_mock,
            engine_monitor=self.engine_monitor_mock
        )
        
        # Register the test agent type
        self.factory.register_agent_type("test_agent", TestAgent)
    
    def test_register_agent_type(self):
        """Test registering agent types."""
        # Already registered in setUp
        self.assertIn("test_agent", self.factory._agent_registry)
        self.assertEqual(self.factory._agent_registry["test_agent"], TestAgent)
        
        # Test overwriting warning
        with patch("triangulum_lx.agents.agent_factory.logger") as mock_logger:
            self.factory.register_agent_type("test_agent", TestAgent)
            mock_logger.warning.assert_called_once()
    
    def test_create_agent(self):
        """Test creating agents."""
        agent = self.factory.create_agent(
            agent_type="test_agent",
            agent_id="test_agent_1",
            config={"test_config": "value"}
        )
        
        self.assertIsNotNone(agent)
        self.assertIsInstance(agent, TestAgent)
        self.assertEqual(agent.agent_id, "test_agent_1")
        self.assertEqual(agent.agent_type, "test_agent")
        self.assertEqual(agent.config, {"test_config": "value"})
        self.assertTrue(agent._is_initialized)
        
        # Agent should be stored in active agents
        self.assertIn("test_agent_1", self.factory._active_agents)
        self.assertEqual(self.factory._active_agents["test_agent_1"], agent)
    
    def test_create_agent_unregistered_type(self):
        """Test creating an agent with an unregistered type."""
        with patch("triangulum_lx.agents.agent_factory.logger") as mock_logger:
            agent = self.factory.create_agent("unknown_type")
            self.assertIsNone(agent)
            mock_logger.error.assert_called_once()
    
    def test_create_agent_initialization_failure(self):
        """Test handling initialization failure when creating an agent."""
        # Mock the initialize method to return False
        with patch.object(TestAgent, 'initialize', return_value=False):
            with patch("triangulum_lx.agents.agent_factory.logger") as mock_logger:
                agent = self.factory.create_agent("test_agent")
                self.assertIsNone(agent)
                mock_logger.error.assert_called_once()
    
    def test_get_agent(self):
        """Test retrieving an agent by ID."""
        agent = self.factory.create_agent("test_agent", "test_agent_1")
        retrieved = self.factory.get_agent("test_agent_1")
        self.assertEqual(retrieved, agent)
        
        # Test with non-existent ID
        self.assertIsNone(self.factory.get_agent("non_existent"))
    
    def test_get_agents_by_type(self):
        """Test retrieving agents by type."""
        agent1 = self.factory.create_agent("test_agent", "test_agent_1")
        agent2 = self.factory.create_agent("test_agent", "test_agent_2")
        
        agents = self.factory.get_agents_by_type("test_agent")
        self.assertEqual(len(agents), 2)
        self.assertIn(agent1, agents)
        self.assertIn(agent2, agents)
        
        # Test with non-existent type
        self.assertEqual(len(self.factory.get_agents_by_type("non_existent")), 0)
    
    def test_shutdown_agent(self):
        """Test shutting down an agent."""
        agent = self.factory.create_agent("test_agent", "test_agent_1")
        
        # Mock the agent's shutdown method
        agent.shutdown = MagicMock()
        
        # Test successful shutdown
        result = self.factory.shutdown_agent("test_agent_1")
        self.assertTrue(result)
        agent.shutdown.assert_called_once()
        self.assertNotIn("test_agent_1", self.factory._active_agents)
        
        # Test non-existent agent
        with patch("triangulum_lx.agents.agent_factory.logger") as mock_logger:
            result = self.factory.shutdown_agent("non_existent")
            self.assertFalse(result)
            mock_logger.warning.assert_called_once()
    
    def test_shutdown_all_agents(self):
        """Test shutting down all agents."""
        agent1 = self.factory.create_agent("test_agent", "test_agent_1")
        agent2 = self.factory.create_agent("test_agent", "test_agent_2")
        
        # Mock the agents' shutdown methods
        agent1.shutdown = MagicMock()
        agent2.shutdown = MagicMock()
        
        self.factory.shutdown_all_agents()
        
        agent1.shutdown.assert_called_once()
        agent2.shutdown.assert_called_once()
        self.assertEqual(len(self.factory._active_agents), 0)
    
    def test_shutdown_agent_exception(self):
        """Test handling exceptions during agent shutdown."""
        agent = self.factory.create_agent("test_agent", "test_agent_1")
        
        # Mock the agent's shutdown method to raise an exception
        agent.shutdown = MagicMock(side_effect=Exception("Test exception"))
        
        with patch("triangulum_lx.agents.agent_factory.logger") as mock_logger:
            result = self.factory.shutdown_agent("test_agent_1")
            self.assertFalse(result)
            mock_logger.error.assert_called_once()
            # Agent should still be in active agents
            self.assertIn("test_agent_1", self.factory._active_agents)


if __name__ == "__main__":
    unittest.main()
