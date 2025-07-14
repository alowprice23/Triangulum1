"""
Unit tests for timeout handling functionality in the Triangulum system.

These tests verify that the timeout handling works correctly with the
new progress tracking enhancements.
"""

import unittest
import time
import threading
from unittest.mock import MagicMock, patch
import logging

from triangulum_lx.core.monitor import OperationProgress, ProgressStatus, OperationTracker
from triangulum_lx.core.monitor import EngineMonitor
from triangulum_lx.agents.base_agent import BaseAgent
from triangulum_lx.agents.orchestrator_agent import OrchestratorAgent, TaskPriority
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus # Added

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestOperationProgress(unittest.TestCase):
    """Test the OperationProgress data class functionality."""
    
    def test_progress_lifecycle(self):
        """Test the full lifecycle of an operation progress object."""
        # Create a new operation progress
        progress = OperationProgress(
            operation_id="test_op_1",
            operation_type="test_operation",
            total_steps=5,
            timeout_seconds=10
        )
        
        # Verify initial state
        self.assertEqual(progress.operation_id, "test_op_1")
        self.assertEqual(progress.status, ProgressStatus.NOT_STARTED)
        self.assertEqual(progress.percentage, 0.0)
        
        # Start the operation
        progress.start()
        self.assertEqual(progress.status, ProgressStatus.IN_PROGRESS)
        self.assertIsNotNone(progress.start_time)
        
        # Update progress
        progress.update(current_step=2, total_steps=5, details={"stage": "processing"})
        self.assertEqual(progress.current_step, 2)
        self.assertEqual(progress.percentage, 40.0)  # 2/5 * 100
        self.assertEqual(progress.details["stage"], "processing")
        
        # Complete the operation
        progress.complete(details={"result": "success"})
        self.assertEqual(progress.status, ProgressStatus.COMPLETED)
        self.assertEqual(progress.percentage, 100.0)
        self.assertEqual(progress.current_step, 5)  # Should be set to total_steps
        self.assertEqual(progress.details["result"], "success")
        self.assertIsNotNone(progress.end_time)
        
    def test_operation_timeout(self):
        """Test that operation timeout detection works correctly."""
        # Create operation with a 0.1 second timeout
        progress = OperationProgress(
            operation_id="test_op_timeout",
            operation_type="test_operation",
            timeout_seconds=0.1
        )
        
        # Not timed out before starting
        self.assertFalse(progress.has_timed_out())
        
        # Start the operation
        progress.start()
        self.assertFalse(progress.has_timed_out())
        
        # Wait for timeout
        time.sleep(0.2)
        self.assertTrue(progress.has_timed_out())
        
        # Mark as timed out
        cancel_callback_called = False
        def cancel_callback():
            nonlocal cancel_callback_called
            cancel_callback_called = True
        
        progress.cancel_callback = cancel_callback
        progress.timeout()
        
        # Verify timeout status
        self.assertEqual(progress.status, ProgressStatus.TIMED_OUT)
        self.assertTrue(cancel_callback_called)
        self.assertIsNotNone(progress.end_time)
    
    def test_operation_cancellation(self):
        """Test operation cancellation."""
        progress = OperationProgress(
            operation_id="test_op_cancel",
            operation_type="test_operation"
        )
        
        # Start the operation
        progress.start()
        
        # Set up cancel callback
        cancel_callback_called = False
        def cancel_callback():
            nonlocal cancel_callback_called
            cancel_callback_called = True
        
        progress.cancel_callback = cancel_callback
        
        # Cancel the operation
        progress.cancel(details={"reason": "user requested"})
        
        # Verify cancellation
        self.assertEqual(progress.status, ProgressStatus.CANCELLED)
        self.assertTrue(cancel_callback_called)
        self.assertEqual(progress.details["reason"], "user requested")
        self.assertIsNotNone(progress.end_time)


class TestOperationTracker(unittest.TestCase):
    """Test the OperationTracker class functionality."""
    
    def setUp(self):
        self.tracker = OperationTracker()
    
    def tearDown(self):
        self.tracker.stop_timeout_checker()
    
    def test_create_and_track_operation(self):
        """Test creating and tracking an operation."""
        # Create an operation
        op_id = self.tracker.create_operation(
            operation_type="test_operation",
            total_steps=10,
            timeout_seconds=30
        )
        
        # Verify operation was created
        operation = self.tracker.get_operation(op_id)
        self.assertIsNotNone(operation)
        self.assertEqual(operation.operation_type, "test_operation")
        self.assertEqual(operation.total_steps, 10)
        self.assertEqual(operation.status, ProgressStatus.NOT_STARTED)
        
        # Start the operation
        self.tracker.start_operation(op_id)
        operation = self.tracker.get_operation(op_id)
        self.assertEqual(operation.status, ProgressStatus.IN_PROGRESS)
        
        # Update progress
        self.tracker.update_operation(op_id, current_step=5, details={"stage": "halfway"})
        operation = self.tracker.get_operation(op_id)
        self.assertEqual(operation.current_step, 5)
        self.assertEqual(operation.percentage, 50.0)
        self.assertEqual(operation.details["stage"], "halfway")
        
        # Complete the operation
        self.tracker.complete_operation(op_id, details={"result": "success"})
        operation = self.tracker.get_operation(op_id)
        self.assertEqual(operation.status, ProgressStatus.COMPLETED)
        self.assertEqual(operation.percentage, 100.0)
        self.assertEqual(operation.details["result"], "success")
    
    def test_operation_timeout_detection(self):
        """Test that operation timeouts are detected and handled."""
        # Mock the _emit_event method to avoid threading issues in tests
        original_emit = self.tracker._emit_event
        self.tracker._emit_event = MagicMock()
        
        # Start the timeout checker
        self.tracker.start_timeout_checker(check_interval=0.1)
        
        # Create an operation with a short timeout
        op_id = self.tracker.create_operation(
            operation_type="timeout_test",
            timeout_seconds=0.2
        )
        
        # Start the operation
        self.tracker.start_operation(op_id)
        
        # Wait for timeout to occur and be detected
        time.sleep(0.5)
        
        # Verify the operation was timed out
        operation = self.tracker.get_operation(op_id)
        self.assertEqual(operation.status, ProgressStatus.TIMED_OUT)
        
        # Verify event was emitted
        self.tracker._emit_event.assert_called_with("operation_timeout", operation)
        
        # Restore original method
        self.tracker._emit_event = original_emit
    
    def test_event_subscription(self):
        """Test subscribing to operation events."""
        events_received = []
        
        def event_handler(event_name, progress):
            events_received.append((event_name, progress.operation_id))
        
        # Subscribe to events
        self.tracker.subscribe_to_events(event_handler)
        
        # Create and update an operation
        op_id = self.tracker.create_operation("test_events")
        self.tracker.start_operation(op_id)
        self.tracker.update_operation(op_id, 1, 2)
        self.tracker.complete_operation(op_id)
        
        # Verify events were received
        self.assertEqual(len(events_received), 4)  # created, started, updated, completed
        self.assertEqual(events_received[0][0], "operation_created")
        self.assertEqual(events_received[1][0], "operation_started")
        self.assertEqual(events_received[2][0], "operation_updated")
        self.assertEqual(events_received[3][0], "operation_completed")
        
        # Unsubscribe
        self.tracker.unsubscribe_from_events(event_handler)
        
        # Create another operation
        op_id2 = self.tracker.create_operation("test_events2")
        
        # No new events should be received
        self.assertEqual(len(events_received), 4)


class TestEngineMonitorOperations(unittest.TestCase):
    """Test the operation tracking features of EngineMonitor."""
    
    def setUp(self):
        self.engine_mock = MagicMock()
        self.engine_mock.bugs = []
        self.monitor = EngineMonitor(self.engine_mock)
    
    def tearDown(self):
        self.monitor.cleanup()
    
    def test_engine_monitor_operations(self):
        """Test that EngineMonitor correctly delegates to OperationTracker."""
        # Create an operation
        op_id = self.monitor.create_operation(
            operation_type="engine_test",
            total_steps=5,
            timeout_seconds=30
        )
        
        # Verify operation was created
        operation = self.monitor.get_operation(op_id)
        self.assertIsNotNone(operation)
        self.assertEqual(operation.operation_type, "engine_test")
        
        # Start the operation
        self.monitor.start_operation(op_id)
        operation = self.monitor.get_operation(op_id)
        self.assertEqual(operation.status, ProgressStatus.IN_PROGRESS)
        
        # Update progress
        self.monitor.update_operation(op_id, current_step=3, total_steps=5)
        operation = self.monitor.get_operation(op_id)
        self.assertEqual(operation.current_step, 3)
        self.assertEqual(operation.percentage, 60.0)
        
        # Complete the operation
        self.monitor.complete_operation(op_id)
        operation = self.monitor.get_operation(op_id)
        self.assertEqual(operation.status, ProgressStatus.COMPLETED)
    
    def test_metrics_include_operations(self):
        """Test that metrics include operation statistics."""
        # Create and complete an operation
        op_id1 = self.monitor.create_operation("metrics_test_1")
        self.monitor.start_operation(op_id1)
        self.monitor.complete_operation(op_id1)
        
        # Create and fail an operation
        op_id2 = self.monitor.create_operation("metrics_test_2")
        self.monitor.start_operation(op_id2)
        self.monitor.fail_operation(op_id2, "test failure")
        
        # Create an in-progress operation
        op_id3 = self.monitor.create_operation("metrics_test_3")
        self.monitor.start_operation(op_id3)
        
        # Get metrics
        metrics = self.monitor.get_metrics()
        
        # Verify operation metrics
        self.assertEqual(metrics["active_operations"], 1)
        self.assertEqual(metrics["completed_operations"], 1)
        self.assertEqual(metrics["failed_operations"], 1)
        self.assertEqual(metrics["total_operations"], 3)


class TestBaseAgentTimeoutHandling(unittest.TestCase):
    """Test timeout handling in BaseAgent."""
    
    def test_agent_operation_tracking(self):
        """Test that agents can track operations with timeouts."""
        # Create a mock engine monitor
        engine_monitor = MagicMock()
        
        # Create a concrete implementation of BaseAgent for testing
        class TestAgent(BaseAgent):
            def _handle_task_request(self, message):
                pass
                
            def _handle_query(self, message):
                pass
        
        # Create an agent instance
        agent = TestAgent(
            agent_id="test_agent",
            agent_type="test",
            engine_monitor=engine_monitor
        )
        
        # Create an operation
        op_id = agent.create_operation(
            operation_type="test_operation",
            total_steps=3,
            timeout_seconds=10
        )
        
        # Verify the operation was registered with the engine monitor
        engine_monitor.create_operation.assert_called_once()
        
        # Start and update the operation
        agent.start_operation(op_id)
        agent.update_operation_progress(op_id, current_step=2, details={"status": "processing"})
        
        # Verify engine monitor was called
        engine_monitor.start_operation.assert_called_once_with(op_id)
        engine_monitor.update_operation.assert_called_once()
        
        # Complete the operation
        agent.complete_operation(op_id, details={"result": "success"})
        engine_monitor.complete_operation.assert_called_once()
    
    def test_timeout_checking(self):
        """Test that agent can detect timeouts."""
        class TestAgent(BaseAgent):
            def _handle_task_request(self, message):
                pass
                
            def _handle_query(self, message):
                pass
                
            def _handle_operation_timeout(self, operation_id):
                self.timeout_handled = True
                super()._handle_operation_timeout(operation_id)
        
        # Create an agent instance
        agent = TestAgent(agent_id="timeout_test_agent")
        agent.timeout_handled = False
        
        # Create an operation with a short timeout
        op_id = agent.create_operation(
            operation_type="timeout_test",
            timeout_seconds=0.1
        )
        
        # Start the operation
        agent.start_operation(op_id)
        
        # Wait for the timeout
        time.sleep(0.2)
        
        # Check for timeouts
        timed_out = agent.check_operation_timeouts()
        
        # Verify timeout was detected and handled
        self.assertTrue(op_id in timed_out)
        self.assertTrue(agent.timeout_handled)


class TestOrchestratorTimeoutHandling(unittest.TestCase):
    """Test timeout handling in OrchestratorAgent."""
    
    async def test_orchestrator_timeout_handling(self): # Removed mock_message_bus from signature
        """Test that OrchestratorAgent properly handles timeouts."""
        # Create a mock engine monitor
        engine_monitor = MagicMock()
        mock_enhanced_message_bus = MagicMock(spec=EnhancedMessageBus)

        # Create an orchestrator instance with the mock monitor and faster internal timing
        orchestrator_config = {
            "timeout": 0.2,  # Task processing timeout
            "task_check_interval": 0.01, # How often main loop checks queue
            "progress_update_interval": 0.01, # How often progress/timeout thread runs
            "default_task_timeout": 0.2, # Default for tasks if not specified
            "timeout_grace_period": 0.05 # Grace before hard fail
        }
        orchestrator = OrchestratorAgent(
            agent_id="test_orchestrator",
            message_bus=mock_enhanced_message_bus, # Pass mock EnhancedMessageBus
            engine_monitor=engine_monitor,
            config=orchestrator_config
        )
        
        # Mock the _assign_task_to_agent method to avoid agent registry dependency
        orchestrator._assign_task_to_agent = MagicMock(return_value="test_agent")
        
        # Patch the _process_file_healing_task method to simulate a long-running task
        original_process = orchestrator._handle_folder_healing
        
        async def slow_process(*args, **kwargs):
            await asyncio.sleep(1.0)  # Sleep longer than the timeout
            return await original_process(*args, **kwargs)
            
        orchestrator._process_file_healing_task = slow_process
        
        # Create a task that will timeout
        message = MagicMock()
        message.message_type = "TASK_REQUEST"
        message.content = {
            "action": "orchestrate_folder_healing",
            "folder_path": "test_folder",
            "options": {
                "dry_run": False,
                "max_files": 1,
                "analysis_depth": 1,
                "timeout_seconds": 0.5,
            },
        }
        message.sender = "test_sender"

        await orchestrator.handle_message(message)
        
        # Verify the operation was registered with the engine monitor
        engine_monitor.create_operation.assert_called_once()
        
        # Wait for the task to be processed and timeout
        await asyncio.sleep(2.0)
        
        # Check that the task was marked as failed due to timeout
        # In the new design, we can't easily access the task status directly.
        # Instead, we check if the engine_monitor.fail_operation was called.
        
        # Verify that the monitor was notified
        engine_monitor.fail_operation.assert_called_once()


if __name__ == '__main__':
    unittest.main()
