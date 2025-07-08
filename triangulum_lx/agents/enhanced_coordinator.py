#!/usr/bin/env python3
"""
Enhanced Agent Coordinator for Triangulum

Implements smarter agent coordination to prevent loops and improve debugging effectiveness.
"""

import logging
import random
from typing import Dict, List, Any, Optional, Set, Tuple

logger = logging.getLogger("triangulum.coordinator")

class AgentCoordinator:
    """Coordinates agent selection to prevent loops and improve effectiveness."""
    
    def __init__(self, agent_roles: List[str]):
        """Initialize the coordinator.
        
        Args:
            agent_roles: List of available agent roles
        """
        self.agent_roles = agent_roles
        self.effectiveness_scores = {role: 1.0 for role in agent_roles}
        self.selection_history = []
        self.state_transition_counts = {}  # Tracks state transitions by agent
        self.stuck_detection_threshold = 3
        
    def select_next_agent(self, current_state: str, coordinator_suggestion: Optional[str] = None) -> str:
        """Select the next agent to execute based on current state and history.
        
        Args:
            current_state: Current bug state
            coordinator_suggestion: Suggested agent from the coordinator
            
        Returns:
            next_agent: Selected agent role
        """
        # If the coordinator made a strong suggestion, consider it heavily
        if coordinator_suggestion and coordinator_suggestion in self.agent_roles:
            # Still check if we're in a loop with this agent
            if self._is_agent_in_loop(coordinator_suggestion):
                logger.info(f"Coordinator suggested {coordinator_suggestion} but it appears to be in a loop")
            else:
                # 80% chance to follow coordinator's suggestion if not in a loop
                if random.random() < 0.8:
                    logger.info(f"Following coordinator suggestion: {coordinator_suggestion}")
                    self._update_history(coordinator_suggestion)
                    return coordinator_suggestion
        
        # Calculate scores for each agent based on state, history, and effectiveness
        scores = {}
        for role in self.agent_roles:
            scores[role] = self._calculate_score(role, current_state)
        
        # Select the agent with the highest score
        next_agent = max(scores.items(), key=lambda x: x[1])[0]
        
        # If we're getting stuck in a pattern, occasionally introduce randomness
        if len(self.selection_history) >= 4:
            recent_agents = self.selection_history[-4:]
            if len(set(recent_agents)) <= 2:  # Only 1 or 2 agents in recent history
                # 20% chance to pick a completely different agent
                if random.random() < 0.2:
                    alternative_agents = [r for r in self.agent_roles if r not in recent_agents]
                    if alternative_agents:
                        next_agent = random.choice(alternative_agents)
                        logger.info(f"Breaking potential loop by selecting alternative agent: {next_agent}")
        
        self._update_history(next_agent)
        return next_agent
    
    def record_state_transition(self, agent: str, old_state: str, new_state: str):
        """Record a successful state transition by an agent.
        
        Args:
            agent: Agent that performed the transition
            old_state: Previous state
            new_state: New state
        """
        if agent not in self.effectiveness_scores:
            return
            
        # Reward the agent for making progress
        if old_state != new_state:
            self.effectiveness_scores[agent] = min(2.0, self.effectiveness_scores[agent] * 1.2)
            
            # Track transition
            transition = (old_state, new_state)
            if agent not in self.state_transition_counts:
                self.state_transition_counts[agent] = {}
            
            if transition not in self.state_transition_counts[agent]:
                self.state_transition_counts[agent][transition] = 0
            
            self.state_transition_counts[agent][transition] += 1
            
            logger.debug(f"Agent {agent} successfully transitioned from {old_state} to {new_state}")
    
    def _calculate_score(self, role: str, current_state: str) -> float:
        """Calculate score for an agent based on history and state.
        
        Args:
            role: Agent role
            current_state: Current bug state
            
        Returns:
            score: Agent's score
        """
        # Start with the agent's effectiveness score
        score = self.effectiveness_scores.get(role, 1.0)
        
        # Adjust based on agent history
        if self.selection_history:
            # Penalize if this agent was used recently
            recent_count = self.selection_history[-5:].count(role)
            if recent_count > 0:
                score *= (0.8 ** recent_count)
            
            # Heavily penalize if the agent appears to be in a loop
            if self._is_agent_in_loop(role):
                score *= 0.3
        
        # Adjust based on current state - each agent is best suited to certain states
        state_preferences = {
            "WAIT": {"observer": 1.5, "analyst": 0.8},
            "REPRO": {"analyst": 1.5, "observer": 1.2},
            "PATCH": {"patcher": 1.8, "analyst": 0.9},
            "VERIFY": {"verifier": 1.8, "patcher": 0.7}
        }
        
        if current_state in state_preferences and role in state_preferences[current_state]:
            score *= state_preferences[current_state][role]
        
        # Add a small random factor to break ties (0.9-1.1)
        score *= (0.9 + 0.2 * random.random())
        
        return score
    
    def _is_agent_in_loop(self, role: str) -> bool:
        """Check if an agent appears to be in a loop.
        
        Args:
            role: Agent role
            
        Returns:
            in_loop: True if the agent appears to be in a loop
        """
        if len(self.selection_history) < self.stuck_detection_threshold:
            return False
            
        # Check if this agent has been selected repeatedly
        return (
            self.selection_history[-self.stuck_detection_threshold:].count(role) 
            >= self.stuck_detection_threshold - 1
        )
    
    def _update_history(self, agent: str):
        """Update the selection history.
        
        Args:
            agent: Selected agent
        """
        self.selection_history.append(agent)
        # Keep history at a manageable size
        if len(self.selection_history) > 20:
            self.selection_history = self.selection_history[-20:]
