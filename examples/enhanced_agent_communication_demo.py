"""
Enhanced Agent Communication Protocol Demo

This script demonstrates the advanced agent communication protocol features including:
- Topic-based messaging
- Message filtering
- Delivery guarantees
- Integration with thought chains
- Memory-efficient context management

It showcases how specialized agents can communicate efficiently using the
standardized message protocol defined in Triangulum's Agent Communication Framework.
"""

import logging
import sys
import os
import time
import json
import threading
import uuid
from typing import Dict, List, Any, Optional, Set

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from triangulum_lx.agents.message import AgentMessage, MessageType, ConversationMemory
from triangulum_lx.agents.message_schema_validator import MessageSchemaValidator
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus, DeliveryStatus
from triangulum_lx.agents.chain_node import ChainNode, ThoughtType, RelationshipType
from triangulum_lx.agents.thought_chain import ThoughtChain
from triangulum_lx.agents.thought_chain_manager import ThoughtChainManager
from triangulum_lx.agents.memory_manager import MemoryManager, RetrievalStrategy


class SimulatedAgent:
    """Base class for simulated agents in the demo."""
    
    def __init__(self, agent_id: str, message_bus: EnhancedMessageBus):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.received_messages: List[AgentMessage] = []
        self.memory_manager = MemoryManager(max_tokens=2000)
        self.schema_validator = MessageSchemaValidator()
        
        # Subscribe to messages
        self.subscribe_to_messages()
        
        logger.info(f"Agent {agent_id} initialized")

    def subscribe_to_messages(self):
        """Subscribe to relevant messages for this agent."""
        self.message_bus.subscribe(
            agent_id=self.agent_id,
            callback=self.handle_message,
            message_types=None  # Subscribe to all message types by default
        )
    
    def handle_message(self, message: AgentMessage):
        """Handle received messages."""
        logger.info(f"Agent {self.agent_id} received message of type {message.message_type.value}")
        self.received_messages.append(message)
    
    def send_message(self, 
                    message_type: MessageType, 
                    content: Dict[str, Any],
                    receiver: Optional[str] = None,
                    topic: Optional[str] = None,
                    **kwargs) -> AgentMessage:
        """Send a message to another agent or topic."""
        message = AgentMessage(
            message_type=message_type,
            content=content,
            sender=self.agent_id,
            receiver=receiver,
            **kwargs
        )
        
        # Validate the message
        is_valid, error = self.schema_validator.validate_message(message)
        if not is_valid:
            logger.error(f"Invalid message: {error}")
            return message
        
        # Publish the message
        if topic:
            logger.info(f"Agent {self.agent_id} publishing message to topic '{topic}'")
            self.message_bus.publish_to_topic(topic, message)
        else:
            logger.info(f"Agent {self.agent_id} sending message to {receiver or 'all'}")
            self.message_bus.publish(message)
        
        return message


class CoordinatorAgent(SimulatedAgent):
    """Simulates a coordinator agent that delegates tasks to other agents."""
    
    def __init__(self, agent_id: str, message_bus: EnhancedMessageBus, thought_chain_manager: ThoughtChainManager):
        super().__init__(agent_id, message_bus)
        self.thought_chain_manager = thought_chain_manager
        
        # Create a thought chain for this task
        self.chain_id = self.thought_chain_manager.create_chain(
            name="BugFixCoordination",
            description="Coordinates bug detection and fixing",
            creator_agent_id=self.agent_id
        )
        
        # Subscribe to specific topics
        self.message_bus.subscribe_to_topic(
            agent_id=self.agent_id,
            topic="bug_reports",
            callback=self.handle_bug_report,
            message_types=[MessageType.PROBLEM_ANALYSIS]
        )
        
        self.message_bus.subscribe_to_topic(
            agent_id=self.agent_id,
            topic="repair_results",
            callback=self.handle_repair_result,
            message_types=[MessageType.VERIFICATION_RESULT]
        )
    
    def handle_bug_report(self, message: AgentMessage):
        """Handle bug reports from the bug detector."""
        logger.info(f"Coordinator received bug report: {message.content}")
        
        # Add a thought to the chain
        self.thought_chain_manager.add_thought(
            chain_id=self.chain_id,
            thought_type=ThoughtType.OBSERVATION,
            content={"observation": f"Bug detected: {message.content.get('analysis')}", 
                     "source": message.message_id},
            author_agent_id=self.agent_id
        )
        
        # Request a repair suggestion
        self.send_message(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Generate repair suggestion", 
                     "bug_details": message.content},
            receiver="repair_agent",
            parent_id=message.message_id,
            conversation_id=message.conversation_id,
            problem_context=message.problem_context
        )

    def handle_repair_result(self, message: AgentMessage):
        """Handle repair verification results."""
        logger.info(f"Coordinator received repair verification: {message.content}")
        
        # Add a thought to the chain
        self.thought_chain_manager.add_thought(
            chain_id=self.chain_id,
            thought_type=ThoughtType.CONCLUSION,
            content={"conclusion": f"Repair verified: {message.content.get('status')}", 
                     "source": message.message_id},
            author_agent_id=self.agent_id
        )
        
        # Notify all agents of the repair status
        self.send_message(
            message_type=MessageType.STATUS,
            content={"status": "Repair completed", 
                     "result": message.content},
            topic="system_status",  # Broadcast to all agents subscribed to this topic
            parent_id=message.message_id,
            conversation_id=message.conversation_id
        )

    def start_bug_detection_task(self, file_path: str):
        """Start a bug detection task for a specific file."""
        logger.info(f"Coordinator starting bug detection task for {file_path}")
        
        # Add a thought to the chain
        thought_id = self.thought_chain_manager.add_thought(
            chain_id=self.chain_id,
            thought_type=ThoughtType.ACTION,
            content={"action": f"Start bug detection for {file_path}"},
            author_agent_id=self.agent_id
        )
        
        # Request bug detection
        self.send_message(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Detect bugs", "file_path": file_path},
            receiver="bug_detector_agent",
            problem_context={"file_path": file_path}
        )


class BugDetectorAgent(SimulatedAgent):
    """Simulates a bug detector agent that analyzes code for bugs."""
    
    def __init__(self, agent_id: str, message_bus: EnhancedMessageBus, thought_chain_manager: ThoughtChainManager):
        super().__init__(agent_id, message_bus)
        self.thought_chain_manager = thought_chain_manager
        
        # Only handle task requests
        self.message_bus.subscribe(
            agent_id=self.agent_id,
            callback=self.handle_message,
            message_types=[MessageType.TASK_REQUEST]
        )
    
    def handle_message(self, message: AgentMessage):
        """Handle received messages."""
        super().handle_message(message)
        
        if message.message_type == MessageType.TASK_REQUEST:
            task = message.content.get("task")
            if task == "Detect bugs":
                self.detect_bugs(message)
    
    def detect_bugs(self, message: AgentMessage):
        """Simulate bug detection for a file."""
        file_path = message.content.get("file_path")
        logger.info(f"Bug detector analyzing file {file_path}")
        
        # Simulate some processing time
        time.sleep(0.5)
        
        # Get the chain ID from the coordinator
        chains = self.thought_chain_manager.list_chains()
        chain_id = None
        for chain_info in chains:
            if chain_info["name"] == "BugFixCoordination":
                chain_id = chain_info["chain_id"]
                break
        
        if chain_id:
            # Add a thought to the chain
            self.thought_chain_manager.add_thought(
                chain_id=chain_id,
                thought_type=ThoughtType.HYPOTHESIS,
                content={"hypothesis": f"File {file_path} might contain type errors"},
                author_agent_id=self.agent_id
            )
        
        # Simulate finding a bug
        bug_analysis = {
            "analysis": f"Found type error in {file_path}",
            "error_type": "TypeError",
            "line_number": 42,
            "code_snippet": "result = 'Total: ' + count",
            "severity": "medium"
        }
        
        # Report the bug
        self.send_message(
            message_type=MessageType.PROBLEM_ANALYSIS,
            content=bug_analysis,
            topic="bug_reports",  # Send to the bug_reports topic
            parent_id=message.message_id,
            conversation_id=message.conversation_id,
            problem_context={
                "file_path": file_path,
                "line_number": 42,
                "code_snippet": "result = 'Total: ' + count",
                "error_message": "TypeError: cannot concatenate 'str' and 'int' objects"
            },
            analysis_results={
                "error_type": "TypeError",
                "error_cause": "String concatenation with integer",
                "affected_code": "result = 'Total: ' + count",
                "severity": "medium"
            }
        )


class RepairAgent(SimulatedAgent):
    """Simulates a repair agent that generates fixes for detected bugs."""
    
    def __init__(self, agent_id: str, message_bus: EnhancedMessageBus, thought_chain_manager: ThoughtChainManager):
        super().__init__(agent_id, message_bus)
        self.thought_chain_manager = thought_chain_manager
        
        # Only handle task requests
        self.message_bus.subscribe(
            agent_id=self.agent_id,
            callback=self.handle_message,
            message_types=[MessageType.TASK_REQUEST]
        )
    
    def handle_message(self, message: AgentMessage):
        """Handle received messages."""
        super().handle_message(message)
        
        if message.message_type == MessageType.TASK_REQUEST:
            task = message.content.get("task")
            if task == "Generate repair suggestion":
                self.generate_repair(message)
    
    def generate_repair(self, message: AgentMessage):
        """Simulate generating a repair for a bug."""
        bug_details = message.content.get("bug_details", {})
        logger.info(f"Repair agent generating fix for {bug_details.get('error_type')}")
        
        # Simulate some processing time
        time.sleep(0.5)
        
        # Get the chain ID
        chains = self.thought_chain_manager.list_chains()
        chain_id = None
        for chain_info in chains:
            if chain_info["name"] == "BugFixCoordination":
                chain_id = chain_info["chain_id"]
                break
        
        if chain_id:
            # Add thoughts to the chain showing reasoning
            evidence_id = self.thought_chain_manager.add_thought(
                chain_id=chain_id,
                thought_type=ThoughtType.EVIDENCE,
                content={"evidence": "Type error caused by concatenating string and integer"},
                author_agent_id=self.agent_id
            )
            
            inference_id = self.thought_chain_manager.add_thought(
                chain_id=chain_id,
                thought_type=ThoughtType.INFERENCE,
                content={"inference": "Need to convert integer to string before concatenation"},
                author_agent_id=self.agent_id,
                parent_id=evidence_id,
                relationship=RelationshipType.DERIVES_FROM
            )
            
            action_id = self.thought_chain_manager.add_thought(
                chain_id=chain_id,
                thought_type=ThoughtType.ACTION,
                content={"action": "Replace 'result = 'Total: ' + count' with 'result = 'Total: ' + str(count)'"},
                author_agent_id=self.agent_id,
                parent_id=inference_id,
                relationship=RelationshipType.DERIVES_FROM
            )
        
        # Generate a repair suggestion
        repair_suggestion = {
            "suggestion": "Convert integer to string before concatenation",
            "file_path": message.problem_context.get("file_path"),
            "line_number": message.problem_context.get("line_number"),
            "original_code": message.problem_context.get("code_snippet"),
            "fixed_code": "result = 'Total: ' + str(count)"
        }
        
        repair_message = self.send_message(
            message_type=MessageType.REPAIR_SUGGESTION,
            content=repair_suggestion,
            receiver="verification_agent",
            parent_id=message.message_id,
            conversation_id=message.conversation_id,
            problem_context=message.problem_context,
            analysis_results=message.analysis_results,
            suggested_actions=[{
                "action_type": "code_change",
                "file": message.problem_context.get("file_path"),
                "line": message.problem_context.get("line_number"),
                "original": message.problem_context.get("code_snippet"),
                "replacement": "result = 'Total: ' + str(count)",
                "description": "Convert integer to string before concatenation",
                "confidence": 0.95,
                "priority": "high"
            }]
        )


class VerificationAgent(SimulatedAgent):
    """Simulates a verification agent that tests fixes."""
    
    def __init__(self, agent_id: str, message_bus: EnhancedMessageBus, thought_chain_manager: ThoughtChainManager):
        super().__init__(agent_id, message_bus)
        self.thought_chain_manager = thought_chain_manager
        
        # Subscribe to repair suggestions
        self.message_bus.subscribe(
            agent_id=self.agent_id,
            callback=self.handle_message,
            message_types=[MessageType.REPAIR_SUGGESTION]
        )
    
    def handle_message(self, message: AgentMessage):
        """Handle received messages."""
        super().handle_message(message)
        
        if message.message_type == MessageType.REPAIR_SUGGESTION:
            self.verify_repair(message)
    
    def verify_repair(self, message: AgentMessage):
        """Simulate verifying a repair."""
        suggestion = message.content.get("suggestion")
        logger.info(f"Verification agent testing repair: {suggestion}")
        
        # Simulate some processing time
        time.sleep(0.7)
        
        # Get the chain ID
        chains = self.thought_chain_manager.list_chains()
        chain_id = None
        for chain_info in chains:
            if chain_info["name"] == "BugFixCoordination":
                chain_id = chain_info["chain_id"]
                break
        
        if chain_id:
            # Add a thought to the chain
            self.thought_chain_manager.add_thought(
                chain_id=chain_id,
                thought_type=ThoughtType.VERIFICATION,
                content={"verification": f"Tested fix: {message.content.get('fixed_code')}. Tests pass."},
                author_agent_id=self.agent_id
            )
        
        # Send verification result
        self.send_message(
            message_type=MessageType.VERIFICATION_RESULT,
            content={
                "status": "success",
                "message": "All tests pass",
                "execution_time": 0.7,
                "file_path": message.content.get("file_path"),
                "line_number": message.content.get("line_number")
            },
            topic="repair_results",  # Send to the repair_results topic
            parent_id=message.message_id,
            conversation_id=message.conversation_id
        )


class ObserverAgent(SimulatedAgent):
    """An agent that just observes system status messages."""
    
    def __init__(self, agent_id: str, message_bus: EnhancedMessageBus):
        super().__init__(agent_id, message_bus)
        self.conversations = {}
        
        # Subscribe to the system_status topic
        self.message_bus.subscribe_to_topic(
            agent_id=self.agent_id,
            topic="system_status",
            callback=self.handle_status_message,
            message_types=[MessageType.STATUS]
        )
    
    def handle_status_message(self, message: AgentMessage):
        """Handle status messages."""
        logger.info(f"Observer {self.agent_id} received status: {message.content.get('status')}")
        
        # We'll use the conversation memory to store the context
        if message.conversation_id not in self.conversations:
            self.conversations[message.conversation_id] = ConversationMemory(conversation_id=message.conversation_id)
        
        # Add the message to the conversation
        self.conversations[message.conversation_id].add_message(message)
        
        # Use the memory manager to get a concise context
        context = self.memory_manager.get_context(
            self.conversations[message.conversation_id],
            strategy=RetrievalStrategy.HYBRID,
            token_limit=1000
        )
        
        logger.info(f"Observer has context of {len(context)} messages for this conversation")


def visualize_thought_chain(chain: ThoughtChain):
    """Visualize a thought chain for demonstration purposes."""
    logger.info("\n" + "="*50)
    logger.info(f"THOUGHT CHAIN: {chain.name}")
    logger.info("="*50)
    
    # Get all nodes in chronological order
    nodes = list(chain.traverse(order="chronological"))
    
    for i, node in enumerate(nodes):
        indent = ""
        if node.parent_ids:
            # Find the index of the parent in our list
            for parent_id in node.parent_ids:
                for j, potential_parent in enumerate(nodes):
                    if potential_parent.node_id == parent_id:
                        # Calculate indent based on parent's position
                        indent = "  " * (j + 1)
                        break
        
        relationship_str = ""
        if node.parent_ids:
            parent_id = list(node.parent_ids)[0]  # Just show the first parent for simplicity
            relationship = node.get_relationship_to(parent_id)
            if relationship:
                relationship_str = f" [{relationship.value}]"
        
        logger.info(f"{i}. {indent}{node.thought_type.value.upper()}{relationship_str}: {str(node.content)}")
    
    logger.info("="*50 + "\n")


def main():
    """Main function to run the demo."""
    logger.info("Starting Enhanced Agent Communication Protocol Demo")
    
    # Initialize components
    message_bus = EnhancedMessageBus(delivery_guarantee=True)
    thought_chain_manager = ThoughtChainManager()
    
    # Create agents
    coordinator = CoordinatorAgent("coordinator_agent", message_bus, thought_chain_manager)
    bug_detector = BugDetectorAgent("bug_detector_agent", message_bus, thought_chain_manager)
    repair_agent = RepairAgent("repair_agent", message_bus, thought_chain_manager)
    verification_agent = VerificationAgent("verification_agent", message_bus, thought_chain_manager)
    observer = ObserverAgent("observer_agent", message_bus)
    
    # Start a bug detection task
    coordinator.start_bug_detection_task("src/example.py")
    
    # Wait for the workflow to complete
    time.sleep(3)
    
    # Visualize the thought chain
    chain_id = None
    chains = thought_chain_manager.list_chains()
    for chain_info in chains:
        if chain_info["name"] == "BugFixCoordination":
            chain_id = chain_info["chain_id"]
            break
    
    if chain_id:
        chain = thought_chain_manager.get_chain(chain_id)
        if chain:
            visualize_thought_chain(chain)
    
    # Check delivery status
    logger.info("\nDelivery Status:")
    for agent in [coordinator, bug_detector, repair_agent, verification_agent, observer]:
        logger.info(f"{agent.agent_id}: {len(agent.received_messages)} messages received")
    
    # Shut down the message bus
    message_bus.shutdown()
    
    logger.info("Enhanced Agent Communication Protocol Demo completed")


if __name__ == "__main__":
    main()
