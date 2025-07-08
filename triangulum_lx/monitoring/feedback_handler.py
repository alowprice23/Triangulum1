#!/usr/bin/env python3
"""
Feedback Handler for Agentic System

This module provides a mechanism for receiving and processing real-time
user feedback to adjust agent reasoning and behavior.
"""

import logging
from typing import Dict, Any, Callable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FeedbackHandler:
    """
    Handles real-time feedback from users to adjust agent reasoning.
    """
    
    def __init__(self, agent_manager: Any):
        """
        Initialize the feedback handler.
        
        Args:
            agent_manager: The agent manager to which feedback will be sent.
        """
        self.agent_manager = agent_manager
        self.feedback_callbacks = {}  # agent_id -> callback
        
        logger.info("Feedback Handler initialized.")
    
    def register_feedback_callback(self, agent_id: str, callback: Callable):
        """
        Register a callback function for an agent to receive feedback.
        
        Args:
            agent_id: The ID of the agent.
            callback: The function to call when feedback is received.
        """
        self.feedback_callbacks[agent_id] = callback
        logger.info(f"Registered feedback callback for agent {agent_id}")
    
    def submit_feedback(self, agent_id: str, feedback: Dict[str, Any]):
        """
        Submit feedback for a specific agent.
        
        Args:
            agent_id: The ID of the agent to receive feedback.
            feedback: A dictionary containing feedback data.
        """
        if agent_id in self.feedback_callbacks:
            try:
                self.feedback_callbacks[agent_id](feedback)
                logger.info(f"Submitted feedback to agent {agent_id}: {feedback}")
            except Exception as e:
                logger.error(f"Error processing feedback for agent {agent_id}: {e}")
        else:
            logger.warning(f"No feedback callback registered for agent {agent_id}")
