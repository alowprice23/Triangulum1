#!/usr/bin/env python3
"""
Triangulum LLM Integration

This script demonstrates how LLM-powered agents can integrate with the Triangulum 
message bus to communicate with each other and have their activity displayed 
in real-time on the dashboard.
"""

import os
import sys
import time
import json
import random
import logging
import threading
import datetime
import argparse

from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus
from triangulum_lx.agents.message import Message, MessageType
from triangulum_lx.agents.message_schema import MessageSchema

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global message bus instance
message_bus = None

class LLMAgent:
    """Simulates an LLM-powered agent that can generate thoughts and communicate with other agents."""
    
    def __init__(self, agent_id, llm_model="gpt-4-turbo"):
        self.agent_id = agent_id
        self.llm_model = llm_model
        self.bus = message_bus
        self.running = False
        self.thread = None
        self.knowledge_base = {}
        self.message_counter = 0
        
    def start(self):
        """Start the agent's processing thread."""
        if self.thread and self.thread.is_alive():
            logger.warning(f"Agent {self.agent_id} is already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._process_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Agent {self.agent_id} started")
        
    def stop(self):
        """Stop the agent's processing thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info(f"Agent {self.agent_id} stopped")
        
    def _process_loop(self):
        """Main processing loop for the agent."""
        while self.running:
            # Generate a thought or message occasionally
            if random.random() < 0.3:  # 30% chance each iteration
                self._generate_activity()
                
            # Sleep for a random interval (1-5 seconds)
            time.sleep(random.uniform(1, 5))
    
    def _generate_activity(self):
        """Generate a random thought or message."""
        activity_type = random.choice(["thought", "message"])
        
        if activity_type == "thought":
            self._generate_thought()
        else:
            self._generate_message()
    
    def _generate_thought(self):
        """Generate and publish a thought from this agent."""
        thought_types = {
            "analysis": [
                "Examining code structure in module {}",
                "Analyzing error pattern in {} function",
                "Reviewing dependency structure for {}",
                "Evaluating performance bottleneck in {}"
            ],
            "decision": [
                "Determining best approach for fixing {}",
                "Selecting optimal repair strategy for {}",
                "Choosing between alternative implementations for {}",
                "Deciding on refactoring method for {}"
            ],
            "discovery": [
                "Found unexpected behavior in {}",
                "Discovered potential root cause in {}",
                "Identified critical issue in {} module",
                "Detected unusual pattern in {}"
            ]
        }
        
        thought_type = random.choice(list(thought_types.keys()))
        components = ["authentication", "database", "API", "frontend", "backend", 
                     "caching", "logging", "error handling", "concurrency"]
        component = random.choice(components)
        
        templates = thought_types[thought_type]
        content = random.choice(templates).format(component)
        
        # Add some randomness to content
        if random.random() < 0.3:
            content += f" (confidence: {random.randint(70, 99)}%)"
        
        # Create message to represent the thought
        self.message_counter += 1
        message = Message(
            sender=self.agent_id,
            message_type=MessageType.THOUGHT,
            content=content,
            metadata={
                "thought_type": thought_type,
                "component": component,
                "confidence": random.randint(70, 99),
                "thought_id": f"{self.agent_id}_thought_{self.message_counter}"
            }
        )
        
        # Publish the thought
        self.bus.publish(message)
        logger.info(f"Agent {self.agent_id} thought: {content}")
    
    def _generate_message(self):
        """Generate and send a message to another agent."""
        # Get a list of all other agents
        all_agents = [
            "orchestrator", "bug_detector", "relationship_analyst",
            "verification_agent", "priority_analyzer", "code_fixer"
        ]
        
        # Don't send a message to self
        other_agents = [agent for agent in all_agents if agent != self.agent_id]
        if not other_agents:
            return
            
        # Choose a random recipient
        receiver = random.choice(other_agents)
        
        # Generate message content
        message_templates = [
            "Request analysis of {} issue",
            "Need help with {} module",
            "Please verify fix for {}",
            "Update on {} status",
            "Information about {} dependency"
        ]
        
        components = ["authentication", "database", "API", "frontend", "backend", 
                     "caching", "logging", "error handling", "concurrency"]
        component = random.choice(components)
        
        content = random.choice(message_templates).format(component)
        
        # Create the message
        self.message_counter += 1
        message = Message(
            sender=self.agent_id,
            receiver=receiver,
            message_type=MessageType.REQUEST if random.random() < 0.7 else MessageType.RESPONSE,
            content=content,
            metadata={
                "priority": random.choice(["high", "medium", "low"]),
                "component": component,
                "message_id": f"{self.agent_id}_msg_{self.message_counter}"
            }
        )
        
        # Send the message
        self.bus.publish(message)
        logger.info(f"Agent {self.agent_id} sent message to {receiver}: {content}")


def initialize_agents():
    """Initialize and return a dictionary of agents."""
    agents = {}
    
    agent_configs = [
        {"id": "orchestrator", "role": "Manages and coordinates all other agents"},
        {"id": "bug_detector", "role": "Identifies bugs and issues in code"},
        {"id": "relationship_analyst", "role": "Analyzes code relationships and dependencies"},
        {"id": "verification_agent", "role": "Verifies fixes and changes"},
        {"id": "priority_analyzer", "role": "Determines priority of issues"},
        {"id": "code_fixer", "role": "Implements fixes and repairs"}
    ]
    
    for config in agent_configs:
        agent = LLMAgent(config["id"])
        agents[config["id"]] = agent
        
    return agents

def announce_system_status(message_bus, event_type, content):
    """Announce a system status update on the message bus."""
    message = Message(
        sender="system",
        message_type=MessageType.NOTIFICATION,
        content=content,
        metadata={
            "event_type": event_type,
            "timestamp": datetime.datetime.now().isoformat()
        }
    )
    
    message_bus.publish(message)
    logger.info(f"System announcement: {content}")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Triangulum LLM Integration')
    
    parser.add_argument(
        '--duration',
        type=int,
        default=300,  # 5 minutes by default
        help='Duration to run the simulation in seconds'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    global message_bus
    message_bus = EnhancedMessageBus()
    
    print("\n" + "=" * 80)
    print("TRIANGULUM LLM INTEGRATION".center(80))
    print("=" * 80 + "\n")
    
    print("Starting LLM-powered agents that will communicate through the message bus")
    print("and generate activity that will be displayed on the dashboard.\n")
    
    # Initialize agents
    agents = initialize_agents()
    
    try:
        # Announce system startup
        announce_system_status(
            message_bus, 
            "system_startup",
            "Triangulum system starting with LLM-powered agents"
        )
        
        # Start all agents
        for agent_id, agent in agents.items():
            agent.start()
            time.sleep(0.5)  # Stagger agent startup
        
        # Announce system ready
        announce_system_status(
            message_bus, 
            "system_ready",
            "All agents initialized and ready"
        )
        
        # Run for the specified duration
        end_time = time.time() + args.duration
        
        while time.time() < end_time:
            # Every 30 seconds, announce system status
            if int(time.time()) % 30 == 0:
                announce_system_status(
                    message_bus,
                    "system_status",
                    f"System running with {len(agents)} active agents"
                )
                time.sleep(1)  # Avoid multiple announcements in the same second
            
            time.sleep(1)
            
        # Announce system shutdown
        announce_system_status(
            message_bus, 
            "system_shutdown",
            "System shutting down normally"
        )
    
    except KeyboardInterrupt:
        print("\nShutting down agents...")
        
        # Announce emergency shutdown
        announce_system_status(
            message_bus, 
            "system_shutdown",
            "System shutting down due to user interrupt"
        )
    
    finally:
        # Stop all agents
        for agent_id, agent in agents.items():
            agent.stop()
        
        print("\nAll agents stopped")
    
    print("\nLLM integration demo completed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
