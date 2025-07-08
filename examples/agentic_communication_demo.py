#!/usr/bin/env python3
"""
Agentic Communication Demo

This script demonstrates the enhanced agentic communication capabilities of Triangulum,
showing how the new components work together to provide advanced communication,
conflict resolution, and context preservation across agent interactions.
"""

import os
import sys
import logging
import json
import time
import datetime
from typing import Dict, List, Any, Optional

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Triangulum components
from triangulum_lx.agents.message_prioritizer import MessagePrioritizer, PriorityLevel
from triangulum_lx.agents.conflict_resolver import ConflictResolver, ResolutionStrategy, ConflictStatus
from triangulum_lx.agents.context_preserver import ContextPreserver, ContextRelevance
from triangulum_lx.monitoring.token_processing_visualizer import TokenProcessingVisualizer
from triangulum_lx.monitoring.progress_tracker import ProgressTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("agentic_communication_demo")

class AgentSimulator:
    """
    Simulates multiple agents interacting with each other to demonstrate
    the enhanced communication capabilities of Triangulum.
    """
    
    def __init__(self, output_dir: str = "./demo_output"):
        """
        Initialize the agent simulator.
        
        Args:
            output_dir: Directory to store output files
        """
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir = output_dir
        
        # Initialize communication components
        self.message_prioritizers = {}  # agent_id -> prioritizer
        self.context_preserver = ContextPreserver(
            max_context_size=10000,
            enable_semantic_chunking=True,
            enable_context_summarization=True
        )
        self.conflict_resolver = ConflictResolver(
            orchestrator_id="orchestrator_agent",
            default_strategy=ResolutionStrategy.HYBRID,
            confidence_threshold=0.6
        )
        
        # Initialize visualization components
        self.token_visualizer = TokenProcessingVisualizer(
            output_dir=os.path.join(output_dir, "token_visualizations")
        )
        
        # Initialize progress tracking
        self.progress_tracker = ProgressTracker(
            output_dir=os.path.join(output_dir, "progress_tracking")
        )
        
        # Register agent expertise for conflict resolution
        self._register_agent_expertise()
        
        # Track conversation contexts
        self.conversation_contexts = {}
        
        logger.info("Initialized agent simulator")
    
    def _register_agent_expertise(self):
        """Register expertise levels for different agents."""
        self.conflict_resolver.update_agent_expertise("bug_detector_agent", {
            "code_repair": 0.9,
            "bug_detection": 0.95,
            "test_generation": 0.7,
            "dependency_analysis": 0.6
        })
        
        self.conflict_resolver.update_agent_expertise("verification_agent", {
            "code_repair": 0.8,
            "bug_detection": 0.7,
            "test_generation": 0.9,
            "code_quality": 0.85
        })
        
        self.conflict_resolver.update_agent_expertise("relationship_analyst_agent", {
            "code_repair": 0.6,
            "dependency_analysis": 0.95,
            "code_structure": 0.9,
            "impact_analysis": 0.85
        })
        
        self.conflict_resolver.update_agent_expertise("orchestrator_agent", {
            "code_repair": 0.75,
            "bug_detection": 0.75,
            "test_generation": 0.75,
            "dependency_analysis": 0.75,
            "coordination": 0.95,
            "prioritization": 0.9
        })
    
    def setup_agents(self, agent_ids: List[str]):
        """
        Set up message prioritizers for each agent.
        
        Args:
            agent_ids: List of agent IDs to set up
        """
        for agent_id in agent_ids:
            if agent_id not in self.message_prioritizers:
                # Create message prioritizer for agent
                self.message_prioritizers[agent_id] = MessagePrioritizer(
                    agent_id=agent_id,
                    priority_threshold=PriorityLevel.MEDIUM,
                    enable_adaptive_prioritization=True
                )
                
                logger.info(f"Set up message prioritizer for agent {agent_id}")
    
    def start_conversation(self, 
                         initiating_agent: str, 
                         participating_agents: List[str],
                         domain: str,
                         initial_context: Optional[Dict] = None) -> str:
        """
        Start a new conversation between agents.
        
        Args:
            initiating_agent: Agent initiating the conversation
            participating_agents: Agents participating in the conversation
            domain: Domain/topic of the conversation
            initial_context: Initial context for the conversation
            
        Returns:
            conversation_id: ID of the created conversation
        """
        # Ensure all agents are set up
        all_agents = [initiating_agent] + [a for a in participating_agents if a != initiating_agent]
        self.setup_agents(all_agents)
        
        # Create conversation context
        conversation_id = self.context_preserver.create_conversation_context(
            initiating_agent=initiating_agent,
            participating_agents=all_agents,
            domain=domain,
            initial_context=initial_context
        )
        
        # Store conversation ID
        self.conversation_contexts[conversation_id] = {
            "domain": domain,
            "initiating_agent": initiating_agent,
            "participating_agents": all_agents,
            "message_count": 0,
            "conflict_count": 0,
            "started_at": datetime.datetime.now().isoformat()
        }
        
        # Initialize progress tracking for this conversation
        self.progress_tracker.start_task(
            task_id=f"conversation_{conversation_id}",
            task_name=f"Conversation: {domain}",
            total_steps=100,  # Will be updated as the conversation progresses
            estimated_duration_seconds=300
        )
        
        logger.info(f"Started conversation {conversation_id} in domain '{domain}' with {len(all_agents)} agents")
        return conversation_id
    
    def send_agent_message(self,
                         conversation_id: str,
                         source_agent: str,
                         target_agent: str,
                         message_type: str,
                         content: Any,
                         urgency: float = 0.5,
                         context_relevance: float = 0.5) -> str:
        """
        Send a message from one agent to another.
        
        Args:
            conversation_id: ID of the conversation
            source_agent: ID of the sending agent
            target_agent: ID of the receiving agent
            message_type: Type of message (command, query, response, etc.)
            content: Message content
            urgency: Urgency level of the message (0-1)
            context_relevance: Relevance to current context (0-1)
            
        Returns:
            message_id: ID of the sent message
        """
        if conversation_id not in self.conversation_contexts:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Check if agents are participants in the conversation
        conv_data = self.conversation_contexts[conversation_id]
        if source_agent not in conv_data["participating_agents"]:
            raise ValueError(f"Agent {source_agent} is not a participant in conversation {conversation_id}")
        if target_agent not in conv_data["participating_agents"]:
            raise ValueError(f"Agent {target_agent} is not a participant in conversation {conversation_id}")
        
        # Create message
        message = {
            "type": message_type,
            "content": content,
            "conversation_id": conversation_id,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Add to context
        element_id = self.context_preserver.add_context_element(
            conversation_id=conversation_id,
            source_agent=source_agent,
            element_type="message",
            element_key=f"message_{int(time.time())}",
            element_value=message,
            relevance=ContextRelevance.MEDIUM
        )
        
        # Queue in target agent's prioritizer
        if target_agent in self.message_prioritizers:
            message_id = self.message_prioritizers[target_agent].enqueue_message(
                message=message,
                source_agent=source_agent,
                message_type=message_type,
                content=content,
                urgency=urgency,
                context_relevance=context_relevance
            )
        else:
            message_id = f"{int(time.time())}_{source_agent}_{target_agent}"
        
        # Update metrics
        conv_data["message_count"] += 1
        
        # Update progress
        self.progress_tracker.update_progress(
            task_id=f"conversation_{conversation_id}",
            current_step=conv_data["message_count"],
            status_message=f"Message from {source_agent} to {target_agent}: {message_type}"
        )
        
        logger.info(f"Agent {source_agent} sent {message_type} message to {target_agent} in conversation {conversation_id}")
        return message_id
    
    def process_agent_queue(self, agent_id: str, max_messages: int = 5) -> List[Dict]:
        """
        Process messages in an agent's queue.
        
        Args:
            agent_id: ID of the agent to process messages for
            max_messages: Maximum number of messages to process
            
        Returns:
            processed_messages: List of processed messages
        """
        if agent_id not in self.message_prioritizers:
            return []
        
        prioritizer = self.message_prioritizers[agent_id]
        processed_messages = []
        
        for i in range(max_messages):
            # Get highest priority message
            message = prioritizer.dequeue_message()
            if not message:
                break
            
            # Simulate processing
            logger.info(f"Agent {agent_id} processing message: {message['message_type']} from {message['source_agent']}")
            
            # Track token processing (simulating LLM token generation)
            session_id = self.token_visualizer.start_processing_session(
                agent_id=agent_id,
                description=f"Processing {message['message_type']} from {message['source_agent']}"
            )
            
            # Simulate token processing
            response_tokens = self._simulate_token_processing(
                agent_id=agent_id,
                message=message,
                session_id=session_id
            )
            
            # Mark message as processed
            prioritizer.complete_message_processing(
                message_id=message["message_id"],
                success=True,
                response_time_ms=200  # Simulated processing time
            )
            
            # Add to processed messages
            processed_messages.append({
                "message": message,
                "response_tokens": response_tokens
            })
        
        return processed_messages
    
    def _simulate_token_processing(self, agent_id: str, message: Dict, session_id: str) -> List[str]:
        """
        Simulate token-by-token processing for an agent.
        
        Args:
            agent_id: ID of the agent processing the message
            message: Message being processed
            session_id: Token processing session ID
            
        Returns:
            tokens: List of generated tokens
        """
        # Simulate a simple response based on message type
        message_type = message["message_type"]
        source_agent = message["source_agent"]
        content = message.get("content", "")
        
        if message_type == "command":
            response_text = f"Executing command: {content}"
        elif message_type == "query":
            response_text = f"Query result for '{content}': This is a simulated response"
        elif message_type == "update":
            response_text = f"Acknowledged update: {content}"
        else:
            response_text = f"Processing {message_type} from {source_agent}"
        
        # Break into tokens (simulate word-by-word)
        tokens = response_text.split()
        
        # Add tokens with visualization
        for i, token in enumerate(tokens):
            # Simulate varying confidence and processing time
            confidence = 0.5 + (i / len(tokens)) * 0.5  # Increases as we progress
            processing_time = 50 + (i % 5) * 10  # Varies between 50-90ms
            
            # Add token to visualizer
            self.token_visualizer.add_token(
                session_id=session_id,
                token=token,
                confidence=confidence * 100,  # Convert to percentage
                processing_time_ms=processing_time
            )
            
            # Simulate processing time
            time.sleep(0.05)
        
        # End processing session
        self.token_visualizer.end_processing_session(session_id)
        
        return tokens
    
    def register_agent_conflict(self,
                              conversation_id: str,
                              domain: str,
                              competing_decisions: List[Dict]) -> str:
        """
        Register a conflict between agent decisions.
        
        Args:
            conversation_id: ID of the conversation
            domain: Domain of the conflict (e.g., "code_repair")
            competing_decisions: List of competing decisions with metadata
            
        Returns:
            conflict_id: ID of the registered conflict
        """
        if conversation_id not in self.conversation_contexts:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Extract affected agents
        affected_agents = [d["agent_id"] for d in competing_decisions]
        
        # Register conflict
        conflict_id = self.conflict_resolver.register_conflict(
            domain=domain,
            competing_decisions=competing_decisions,
            affected_agents=affected_agents,
            context={"conversation_id": conversation_id}
        )
        
        # Update metrics
        conv_data = self.conversation_contexts[conversation_id]
        conv_data["conflict_count"] += 1
        
        # Update progress
        self.progress_tracker.update_progress(
            task_id=f"conversation_{conversation_id}",
            current_step=conv_data["message_count"] + conv_data["conflict_count"],
            status_message=f"Resolving conflict between {', '.join(affected_agents)}"
        )
        
        logger.info(f"Registered conflict {conflict_id} between {len(competing_decisions)} decisions in domain '{domain}'")
        return conflict_id
    
    def resolve_agent_conflict(self, conflict_id: str) -> Dict:
        """
        Resolve a conflict between agent decisions.
        
        Args:
            conflict_id: ID of the conflict to resolve
            
        Returns:
            resolution: Resolution result
        """
        # Resolve conflict
        resolution = self.conflict_resolver.resolve_conflict(conflict_id)
        
        # Get conversation ID from conflict
        conflict = self.conflict_resolver.active_conflicts.get(conflict_id)
        if conflict and "context" in conflict and "conversation_id" in conflict["context"]:
            conversation_id = conflict["context"]["conversation_id"]
            
            # Update progress
            if conversation_id in self.conversation_contexts:
                self.progress_tracker.update_progress(
                    task_id=f"conversation_{conversation_id}",
                    status_message=f"Conflict resolved: {resolution['explanation']}"
                )
        
        logger.info(f"Resolved conflict {conflict_id} with strategy {resolution['resolution_strategy']}")
        return resolution
    
    def run_demo_scenario(self):
        """Run a demonstration scenario showcasing the enhanced communication capabilities."""
        logger.info("Starting demo scenario...")
        
        # Create agents
        agents = ["orchestrator_agent", "bug_detector_agent", "verification_agent", "relationship_analyst_agent"]
        self.setup_agents(agents)
        
        # Start a conversation
        conversation_id = self.start_conversation(
            initiating_agent="orchestrator_agent",
            participating_agents=agents[1:],
            domain="code_repair",
            initial_context={
                "project": "example_project",
                "task": "Fix null pointer exception in login.py",
                "priority": "high"
            }
        )
        
        # Simulate message exchange
        self.send_agent_message(
            conversation_id=conversation_id,
            source_agent="orchestrator_agent",
            target_agent="bug_detector_agent",
            message_type="command",
            content="Analyze login.py for null pointer issues",
            urgency=0.8
        )
        
        # Process bug detector's messages
        self.process_agent_queue("bug_detector_agent")
        
        # Bug detector sends results back
        self.send_agent_message(
            conversation_id=conversation_id,
            source_agent="bug_detector_agent",
            target_agent="orchestrator_agent",
            message_type="response",
            content={
                "file": "login.py",
                "line": 42,
                "issue": "Null pointer when user object is None",
                "severity": "high"
            },
            urgency=0.7
        )
        
        # Orchestrator assigns verification
        self.send_agent_message(
            conversation_id=conversation_id,
            source_agent="orchestrator_agent",
            target_agent="verification_agent",
            message_type="command",
            content="Verify bug in login.py:42",
            urgency=0.6
        )
        
        # Orchestrator asks for dependency analysis
        self.send_agent_message(
            conversation_id=conversation_id,
            source_agent="orchestrator_agent",
            target_agent="relationship_analyst_agent",
            message_type="command",
            content="Analyze dependencies for login.py",
            urgency=0.5
        )
        
        # Process verification agent's messages
        self.process_agent_queue("verification_agent")
        
        # Process relationship analyst's messages
        self.process_agent_queue("relationship_analyst_agent")
        
        # Both agents report back
        self.send_agent_message(
            conversation_id=conversation_id,
            source_agent="verification_agent",
            target_agent="orchestrator_agent",
            message_type="response",
            content={
                "verified": True,
                "reproduction_steps": ["Login with null user ID", "Check error log"],
                "recommended_fix": "Add null check before accessing user properties"
            }
        )
        
        self.send_agent_message(
            conversation_id=conversation_id,
            source_agent="relationship_analyst_agent",
            target_agent="orchestrator_agent",
            message_type="response",
            content={
                "dependencies": ["user.py", "session.py", "auth.py"],
                "impact": "Medium - affects login flow only",
                "affected_functions": ["validate_user", "create_session"]
            }
        )
        
        # Process orchestrator's messages
        self.process_agent_queue("orchestrator_agent")
        
        # Simulate a conflict in fix approach
        competing_decisions = [
            {
                "agent_id": "bug_detector_agent",
                "decision": {"fix_type": "add_null_check", "priority": "high"},
                "confidence": 0.85
            },
            {
                "agent_id": "verification_agent",
                "decision": {"fix_type": "add_type_check", "priority": "medium"},
                "confidence": 0.75
            },
            {
                "agent_id": "relationship_analyst_agent",
                "decision": {"fix_type": "refactor_login_flow", "priority": "medium"},
                "confidence": 0.65
            }
        ]
        
        conflict_id = self.register_agent_conflict(
            conversation_id=conversation_id,
            domain="code_repair",
            competing_decisions=competing_decisions
        )
        
        # Resolve the conflict
        resolution = self.resolve_agent_conflict(conflict_id)
        
        # Orchestrator communicates the decision
        for agent_id in [a["agent_id"] for a in competing_decisions]:
            if agent_id != "orchestrator_agent":
                self.send_agent_message(
                    conversation_id=conversation_id,
                    source_agent="orchestrator_agent",
                    target_agent=agent_id,
                    message_type="decision",
                    content={
                        "selected_fix": resolution["resolution_result"],
                        "explanation": resolution["explanation"],
                        "confidence": resolution["confidence"]
                    }
                )
        
        # Process all agents' messages
        for agent_id in agents:
            self.process_agent_queue(agent_id)
        
        # Complete the task
        self.progress_tracker.complete_task(
            task_id=f"conversation_{conversation_id}",
            final_status="Completed with fix decision: " + str(resolution["resolution_result"])
        )
        
        # Generate outputs
        self._generate_demo_outputs(conversation_id)
        
        logger.info("Demo scenario completed")
    
    def _generate_demo_outputs(self, conversation_id: str):
        """
        Generate demo outputs summarizing the scenario.
        
        Args:
            conversation_id: ID of the conversation to summarize
        """
        # Create output file
        output_file = os.path.join(self.output_dir, f"demo_scenario_{conversation_id}.json")
        
        # Get conversation context
        context = self.context_preserver.get_conversation_context(
            conversation_id=conversation_id,
            agent_id=self.conversation_contexts[conversation_id]["initiating_agent"]
        )
        
        # Get agent queue statuses
        queue_statuses = {}
        for agent_id, prioritizer in self.message_prioritizers.items():
            queue_statuses[agent_id] = prioritizer.get_queue_status()
        
        # Get context usage metrics
        context_metrics = self.context_preserver.get_context_usage_metrics()
        
        # Compile output data
        output_data = {
            "conversation_id": conversation_id,
            "conversation_details": self.conversation_contexts[conversation_id],
            "context_summary": context.get("summary"),
            "message_count": context["total_elements"],
            "queue_statuses": queue_statuses,
            "context_metrics": context_metrics,
            "token_visualization_dir": os.path.join(self.output_dir, "token_visualizations"),
            "progress_tracking_dir": os.path.join(self.output_dir, "progress_tracking")
        }
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"Demo outputs saved to {output_file}")


def main():
    """Run the agentic communication demo."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Run the Triangulum agentic communication demo")
    parser.add_argument("--output-dir", default="./demo_output", help="Directory for demo outputs")
    args = parser.parse_args()
    
    # Run demo
    simulator = AgentSimulator(output_dir=args.output_dir)
    simulator.run_demo_scenario()
    
    print(f"\nDemo completed! Outputs saved to {args.output_dir}")
    print(f"Token visualizations are in {os.path.join(args.output_dir, 'token_visualizations')}")
    print(f"Progress tracking data is in {os.path.join(args.output_dir, 'progress_tracking')}")


if __name__ == "__main__":
    main()
