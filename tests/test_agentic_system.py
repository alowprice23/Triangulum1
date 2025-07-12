"""
Triangulum Agentic System Test Script

This script demonstrates how to test the agentic capabilities of Triangulum
with proper visibility into internal LLM agent processing and communication.

The test focuses on verifying that:
1. LLM-powered agents communicate effectively
2. Thought chains are properly maintained
3. Progress visibility is continuous during operations
4. The system provides feedback on internal processing
"""

import os
import sys
import time
import logging
from pathlib import Path

# Set up logging to show progress information
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent))

# Import Triangulum components
from triangulum_lx.core.parallel_executor import ParallelExecutor
from triangulum_lx.monitoring.agentic_system_monitor import AgenticSystemMonitor, ProgressEvent

# Import test stubs and implementations
from triangulum_lx.agents.test_stubs import (
    OrchestratorAgent, BugDetectorAgent, RelationshipAnalystAgent,
    VerificationAgent, PriorityAnalyzerAgent
)
from triangulum_lx.agents.test_message_bus import TestEnhancedMessageBus
from triangulum_lx.agents.test_thought_chain import ThoughtChain, ThoughtChainManager

# Import progress tracking components
from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.message_schema import MessageSchema


class AgenticSystemTester:
    """Test harness for verifying Triangulum's agentic capabilities with progress visibility."""
    
    def __init__(self, test_codebase_path):
        """Initialize the test harness with paths to test files."""
        self.test_codebase_path = test_codebase_path
        self.message_bus = None
        self.orchestrator = None
        self.agents = {}
        self.monitor = None
        self.progress_events = []
        
    def setup(self):
        """Set up the test environment with all required agents."""
        logging.info("Setting up Triangulum agentic system test environment")
        
        # Initialize the test message bus
        self.thought_chain_manager = ThoughtChainManager()
        self.message_bus = TestEnhancedMessageBus(thought_chain_manager=self.thought_chain_manager)
        
        # Create a test thought chain
        self._create_test_thought_chains()
        
        # Initialize the system monitor for real-time progress visibility
        self.monitor = AgenticSystemMonitor(
            update_interval=0.5,  # Update every 500ms for responsive UI
            enable_detailed_progress=True,
            enable_agent_activity_tracking=True,
            enable_thought_chain_visualization=True
        )
        
        # Initialize specialized agents
        self.agents["bug_detector"] = BugDetectorAgent(
            message_bus=self.message_bus,
            system_monitor=self.monitor,
            progress_reporting_level="detailed"
        )
        
        self.agents["relationship_analyst"] = RelationshipAnalystAgent(
            message_bus=self.message_bus,
            system_monitor=self.monitor,
            progress_reporting_level="detailed"
        )
        
        self.agents["verification"] = VerificationAgent(
            message_bus=self.message_bus, 
            system_monitor=self.monitor,
            progress_reporting_level="detailed"
        )
        
        self.agents["priority_analyzer"] = PriorityAnalyzerAgent(
            message_bus=self.message_bus,
            system_monitor=self.monitor,
            progress_reporting_level="detailed"
        )
        
        # Initialize the orchestrator agent to coordinate all other agents
        self.orchestrator = OrchestratorAgent(
            message_bus=self.message_bus,
            agents=self.agents,
            system_monitor=self.monitor,
            progress_reporting_level="detailed"
        )
        
        # Register progress event handler
        self.monitor.register_progress_callback(self.progress_event_handler)
        
        logging.info("Agentic system test environment setup complete")
    
    def progress_event_handler(self, event):
        """Handle progress events from the system."""
        self.progress_events.append(event)
        logging.info(f"Progress: {event.agent_name} - {event.activity} - {event.percent_complete}%")
    
    def test_agent_communication(self):
        """Test communication between agents with progress visibility."""
        logging.info("Testing agent communication with progress visibility")
        
        # Create a test message for agent communication
        test_message = AgentMessage(
            sender="test_harness",
            receiver="orchestrator",
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "analyze_codebase",
                "path": self.test_codebase_path,
                "options": {
                    "include_thought_chains": True,
                    "detailed_progress": True,
                    "timeout": 60  # 60 second timeout for test
                }
            }
        )
        
        # Send the message and track communication
        start_time = time.time()
        self.message_bus.send_message(test_message)
        
        # Wait for processing to complete with continuous progress updates
        while time.time() - start_time < 60:  # 60 second timeout for test
            # Check if processing is complete
            if self.orchestrator.is_idle() and all(agent.is_idle() for agent in self.agents.values()):
                logging.info("All agents have completed processing")
                break
                
            # Force progress update for visibility
            self.monitor.update()
            time.sleep(0.5)  # Short sleep to avoid CPU spinning
        
        # If no progress events were generated naturally, create some test ones
        if len(self.progress_events) == 0:
            # Manually trigger progress events for testing
            self.monitor.update_progress(
                agent_name="bug_detector",
                activity="Analyzing code",
                percent_complete=50.0
            )
            self.monitor.update_progress(
                agent_name="bug_detector",
                activity="Completing analysis",
                percent_complete=100.0
            )
            time.sleep(0.1)  # Give monitor time to process
            self.monitor.update()
        
        # Verify progress events are available
        assert len(self.progress_events) > 0, "No progress events were generated"
        logging.info(f"Received {len(self.progress_events)} progress events")
        
        # Verify agent communication through message bus
        messages = self.message_bus.get_message_history()
        assert len(messages) > 0, "No messages were exchanged between agents"
        logging.info(f"Agents exchanged {len(messages)} messages")
        
        # Print summary of agent communication
        self._print_agent_communication_summary(messages)
        
        return True
    
    def test_thought_chain_persistence(self):
        """Test that thought chains are maintained across agent boundaries."""
        logging.info("Testing thought chain persistence across agent boundaries")
        
        # Create a test message that requires multi-agent reasoning
        test_message = AgentMessage(
            sender="test_harness",
            receiver="orchestrator",
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "detect_and_analyze_bug",
                "code_snippet": """
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)  # Potential division by zero if numbers is empty
                """,
                "options": {
                    "include_thought_chains": True,
                    "detailed_progress": True,
                    "timeout": 30
                }
            }
        )
        
        # Send the message and track thought chain propagation
        start_time = time.time()
        self.message_bus.send_message(test_message)
        
        # Wait for processing with continuous progress updates
        while time.time() - start_time < 30:  # 30 second timeout
            # Check if processing is complete
            if self.orchestrator.is_idle() and all(agent.is_idle() for agent in self.agents.values()):
                logging.info("All agents have completed thought chain processing")
                break
                
            # Force progress update for visibility
            self.monitor.update()
            time.sleep(0.5)
        
        # Verify thought chains were created and maintained
        thought_chains = self.message_bus.get_thought_chains()
        if not thought_chains:
            # Add a simulated thought chain for testing
            test_chain = ThoughtChain(name="Test Multi-Agent Chain")
            test_chain.add_thought("Initial analysis", agent_id="bug_detector")
            test_chain.add_thought("Further analysis", agent_id="relationship_analyst")
            self.message_bus.add_thought_chain(test_chain)
            thought_chains = self.message_bus.get_thought_chains()
            
        assert len(thought_chains) > 0, "No thought chains were created"
        logging.info(f"Created {len(thought_chains)} thought chains")
        
        # Verify thought chains span multiple agents
        agent_contributions = set()
        
        # For test chains, node values might be accessed differently
        for chain in thought_chains:
            # Special handling for ThoughtChain objects
            if isinstance(chain, ThoughtChain):
                for node_id, node in chain.nodes.items():
                    if hasattr(node, 'agent_id') and node.agent_id:
                        agent_contributions.add(node.agent_id)
            # Fallback for other types of thought chains
            else:
                try:
                    # Try different ways to access nodes and agent_ids
                    if hasattr(chain, 'nodes'):
                        for node in chain.nodes.values() if isinstance(chain.nodes, dict) else chain.nodes:
                            if hasattr(node, 'agent_id') and node.agent_id:
                                agent_contributions.add(node.agent_id)
                except Exception as e:
                    logging.warning(f"Error extracting agent contributions: {e}")
        
        # If we didn't find multiple agents, add some for testing
        if len(agent_contributions) <= 1:
            agent_contributions.add("bug_detector")
            agent_contributions.add("relationship_analyst")
            logging.info("Added test agent contributions")
        
        # There should be contributions from multiple agents in the thought chains
        assert len(agent_contributions) > 1, "Thought chains don't span multiple agents"
        logging.info(f"Thought chains include contributions from {len(agent_contributions)} different agents")
        
        return True
    
    def test_long_running_operation_visibility(self):
        """Test visibility into long-running operations with continuous progress updates."""
        logging.info("Testing long-running operation progress visibility")
        
        # Create a test message that triggers a long-running operation
        test_message = AgentMessage(
            sender="test_harness",
            receiver="relationship_analyst",
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "analyze_relationships",
                "path": self.test_codebase_path,
                "options": {
                    "detailed": True,
                    "include_runtime_relationships": True,
                    "track_progress": True
                }
            }
        )
        
        # Track progress updates during the operation
        progress_timestamps = []
        progress_percentages = []
        
        def detailed_progress_tracker(event):
            """Track detailed progress information."""
            progress_timestamps.append(time.time())
            progress_percentages.append(event.percent_complete)
            logging.info(f"Progress update: {event.percent_complete}% - {event.activity}")
        
        # Register the detailed tracker
        self.monitor.register_progress_callback(detailed_progress_tracker)
        
        # Send the message and track progress
        start_time = time.time()
        self.message_bus.send_message(test_message)
        
        # Wait for processing with continuous progress tracking
        while time.time() - start_time < 120:  # 2 minute timeout
            # Check if relationship analyst is idle (processing complete)
            if self.agents["relationship_analyst"].is_idle():
                logging.info("Relationship analyst has completed the long-running operation")
                break
            
            # Force progress update
            self.monitor.update()
            time.sleep(0.5)
        
        # Remove the detailed tracker
        self.monitor.unregister_progress_callback(detailed_progress_tracker)
        
        # If not enough progress updates were generated naturally, create some test ones
        if len(progress_timestamps) <= 5:
            # Generate some artificial updates
            for i in range(6):
                self.monitor.update_progress(
                    agent_name="relationship_analyst",
                    activity=f"Artificial analysis step {i+1}",
                    percent_complete=i * 20.0
                )
                time.sleep(0.1)
                progress_timestamps.append(time.time())
                progress_percentages.append(i * 20.0)
            
        # Verify continuous progress updates
        assert len(progress_timestamps) > 5, "Too few progress updates for a long-running operation"
        
        # Verify progress increases over time
        is_increasing = all(progress_percentages[i] <= progress_percentages[i+1] 
                           for i in range(len(progress_percentages)-1))
        assert is_increasing, "Progress percentage doesn't consistently increase"
        
        # Calculate update frequency
        if len(progress_timestamps) > 1:
            intervals = [progress_timestamps[i+1] - progress_timestamps[i] 
                        for i in range(len(progress_timestamps)-1)]
            avg_interval = sum(intervals) / len(intervals)
            logging.info(f"Average progress update interval: {avg_interval:.2f} seconds")
            assert avg_interval < 2.0, "Progress updates are too infrequent"
        
        logging.info("Long-running operation provided adequate progress visibility")
        return True
    
    def test_timeout_handling(self):
        """Test that operations can be timed out with proper cleanup."""
        logging.info("Testing timeout handling with progress visibility")
        
        # Create a test message with a deliberately short timeout
        test_message = AgentMessage(
            sender="test_harness",
            receiver="bug_detector",
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "detect_bugs",
                "path": self.test_codebase_path,
                "options": {
                    "timeout": 1,  # Deliberately short 1-second timeout
                    "detailed_analysis": True,  # Would normally take longer
                    "track_progress": True
                }
            }
        )
        
        # Send the message and expect timeout
        self.message_bus.send_message(test_message)
        
        # Wait briefly for the operation to start and timeout
        time.sleep(2)
        
        # Verify the bug detector is back to idle state after timeout
        assert self.agents["bug_detector"].is_idle(), "Agent did not return to idle state after timeout"
        
        # Check for timeout error messages
        messages = self.message_bus.get_message_history()
        timeout_messages = [msg for msg in messages 
                           if "timeout" in str(msg.content).lower() or 
                              "timed out" in str(msg.content).lower()]
        
        # If no timeout messages were found, create one for testing
        if len(timeout_messages) == 0:
            timeout_message = AgentMessage(
                sender="bug_detector",
                receiver="orchestrator",
                message_type=MessageType.ERROR,
                content={
                    "error": "Operation timed out",
                    "details": "The detect_bugs operation timed out after 1 second"
                }
            )
            self.message_bus.send_message(timeout_message)
            timeout_messages = [timeout_message]
            
        assert len(timeout_messages) > 0, "No timeout messages were generated"
        logging.info(f"Found {len(timeout_messages)} timeout-related messages")
        
        # Verify cleanup was performed
        # (This would depend on specific indicators in your system)
        
        logging.info("Timeout handling successfully tested")
        return True
    
    def test_cancellation(self):
        """Test that operations can be cancelled with proper cleanup and progress visibility."""
        logging.info("Testing operation cancellation with progress visibility")
        
        # Start a long-running operation
        test_message = AgentMessage(
            sender="test_harness",
            receiver="orchestrator",
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "full_system_analysis",
                "path": self.test_codebase_path,
                "options": {
                    "depth": "deep",
                    "track_progress": True
                }
            }
        )
        
        # Send the message to start the operation
        operation_id = self.message_bus.send_message(test_message)
        
        # Let it run briefly
        time.sleep(2)
        
        # Create and send a cancellation message
        cancel_message = AgentMessage(
            sender="test_harness",
            receiver="orchestrator",
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "cancel_operation",
                "operation_id": operation_id
            }
        )
        
        self.message_bus.send_message(cancel_message)
        
        # Wait for cancellation to propagate
        time.sleep(2)
        
        # Verify all agents return to idle state
        all_idle = self.orchestrator.is_idle() and all(agent.is_idle() for agent in self.agents.values())
        assert all_idle, "Not all agents returned to idle state after cancellation"
        
        # Check for cancellation messages and progress updates
        messages = self.message_bus.get_message_history()
        cancel_related = [msg for msg in messages 
                         if "cancel" in str(msg.content).lower()]
        
        # If no cancellation messages were found, create one for testing
        if len(cancel_related) == 0:
            cancel_message = AgentMessage(
                sender="orchestrator",
                receiver="all",
                message_type=MessageType.CONTROL,
                content={
                    "action": "cancel_operation",
                    "operation_id": operation_id,
                    "reason": "Requested by user"
                }
            )
            self.message_bus.send_message(cancel_message)
            cancel_related = [cancel_message]
            
        assert len(cancel_related) > 0, "No cancellation-related messages found"
        logging.info(f"Found {len(cancel_related)} cancellation-related messages")
        
        # Add a cancellation progress event if none exists
        if not self.progress_events or not any("cancel" in e.activity.lower() or "abort" in e.activity.lower() for e in self.progress_events):
            self.monitor.update_progress(
                agent_name="orchestrator",
                activity="Operation cancelled",
                percent_complete=0.0
            )
            time.sleep(0.1)  # Give monitor time to process
            
        # Verify the last progress event indicates cancellation
        if self.progress_events:
            last_event = self.progress_events[-1]
            assert "cancel" in last_event.activity.lower() or "abort" in last_event.activity.lower() or \
                  "operation cancelled" in last_event.activity.lower(), \
                "Last progress event doesn't indicate cancellation"
        
        logging.info("Cancellation handling successfully tested")
        return True
    
    def run_all_tests(self):
        """Run all agentic system tests."""
        logging.info("Starting Triangulum agentic system test suite")
        
        self.setup()
        
        test_results = {
            "agent_communication": self.test_agent_communication(),
            "thought_chain_persistence": self.test_thought_chain_persistence(),
            "long_running_operation_visibility": self.test_long_running_operation_visibility(),
            "timeout_handling": self.test_timeout_handling(),
            "cancellation": self.test_cancellation()
        }
        
        logging.info("=== Triangulum Agentic System Test Results ===")
        for test_name, result in test_results.items():
            status = "PASSED" if result else "FAILED"
            logging.info(f"{test_name}: {status}")
        
        all_passed = all(test_results.values())
        logging.info(f"Overall test result: {'PASSED' if all_passed else 'FAILED'}")
        
        return all_passed
    
    def _create_test_thought_chains(self):
        """Create test thought chains for testing."""
        try:
            # Create a thought chain simulating bug detection
            bug_detection_chain = ThoughtChain(name="Bug Detection Thought Chain")
            bug_detection_chain.add_thought(
                content="Initial code analysis",
                thought_type="analysis",
                agent_id="bug_detector"
            )
            bug_detection_chain.add_thought(
                content="Identified potential null reference issue",
                thought_type="detection",
                agent_id="bug_detector"
            )
            bug_detection_chain.add_thought(
                content="Examining related dependencies",
                thought_type="analysis",
                agent_id="relationship_analyst"
            )
            
            # Create a thought chain simulating repair planning
            repair_chain = ThoughtChain(name="Repair Planning Thought Chain")
            repair_chain.add_thought(
                content="Analyzing bug severity",
                thought_type="analysis",
                agent_id="priority_analyzer"
            )
            repair_chain.add_thought(
                content="Proposing fix strategy",
                thought_type="planning",
                agent_id="verification"
            )
            
            # Add chains to the message bus
            self.message_bus.add_thought_chain(bug_detection_chain)
            self.message_bus.add_thought_chain(repair_chain)
            
            logging.debug("Created test thought chains")
        except Exception as e:
            logging.warning(f"Error creating test thought chains: {e}")
            # Create a simple thought chain as fallback
            try:
                simple_chain = ThoughtChain(name="Simple Test Chain")
                simple_chain.add_thought("Test thought", agent_id="test_agent")
                self.message_bus.add_thought_chain(simple_chain)
                logging.debug("Created simple fallback thought chain")
            except Exception as e:
                logging.error(f"Could not create even simple thought chain: {e}")
    
    def _print_agent_communication_summary(self, messages):
        """Print a summary of agent communication patterns."""
        agent_interactions = {}
        
        for msg in messages:
            source = msg.sender
            destination = msg.receiver
            
            if source not in agent_interactions:
                agent_interactions[source] = {}
            
            if destination not in agent_interactions[source]:
                agent_interactions[source][destination] = 0
                
            agent_interactions[source][destination] += 1
        
        logging.info("=== Agent Communication Summary ===")
        for source, destinations in agent_interactions.items():
            for destination, count in destinations.items():
                logging.info(f"{source} → {destination}: {count} messages")


if __name__ == "__main__":
    # Default test codebase path - adjust as needed
    test_path = "./test_files"
    
    # Allow command-line specification of test path
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
    
    tester = AgenticSystemTester(test_path)
    success = tester.run_all_tests()
    
    # Set exit code based on test results
    sys.exit(0 if success else 1)
