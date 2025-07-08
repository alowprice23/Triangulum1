#!/usr/bin/env python3
"""
Conflict Resolver for Agent Decision Making

This module provides conflict resolution mechanisms for competing agent decisions
in the Triangulum agentic system. It ensures that when multiple agents propose
conflicting courses of action, the system can intelligently resolve these conflicts
based on agent expertise, confidence levels, and contextual factors.
"""

import logging
import datetime
import json
import os
import time
from typing import Dict, List, Any, Optional, Tuple, Callable
import uuid
import heapq
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResolutionStrategy(Enum):
    """Resolution strategies for agent conflicts."""
    CONSENSUS = 0      # Require consensus among majority of agents
    CONFIDENCE = 1     # Choose decision with highest confidence score
    EXPERTISE = 2      # Prioritize based on agent domain expertise
    WEIGHTED_VOTE = 3  # Weight votes by agent reliability and expertise
    HIERARCHICAL = 4   # Use predefined agent hierarchy
    HYBRID = 5         # Combine multiple strategies

class ConflictStatus(Enum):
    """Status of a conflict resolution process."""
    PENDING = 0        # Conflict identified but not yet resolved
    RESOLVING = 1      # Resolution in progress
    RESOLVED = 2       # Conflict successfully resolved
    ESCALATED = 3      # Conflict escalated to higher authority
    DEADLOCKED = 4     # Unable to resolve with current information

class ConflictResolver:
    """
    Resolves conflicts between competing agent decisions to ensure
    consistent and optimal system behavior.
    """
    
    def __init__(self, 
                orchestrator_id: str,
                default_strategy: ResolutionStrategy = ResolutionStrategy.HYBRID,
                decision_timeout: float = 30.0,
                confidence_threshold: float = 0.7,
                escalation_policy: Optional[Dict] = None,
                agent_expertise: Optional[Dict[str, Dict[str, float]]] = None):
        """
        Initialize the conflict resolver.
        
        Args:
            orchestrator_id: ID of the orchestrator agent that manages resolution
            default_strategy: Default strategy for conflict resolution
            decision_timeout: Timeout in seconds for resolution decisions
            confidence_threshold: Minimum confidence required for auto-resolution
            escalation_policy: Policy for escalating unresolvable conflicts
            agent_expertise: Dictionary mapping agent IDs to their expertise areas with scores
        """
        self.orchestrator_id = orchestrator_id
        self.default_strategy = default_strategy
        self.decision_timeout = decision_timeout
        self.confidence_threshold = confidence_threshold
        self.escalation_policy = escalation_policy or {
            "max_attempts": 3,
            "escalation_path": ["orchestrator", "human_supervisor"],
            "auto_resolve_threshold": 0.9
        }
        self.agent_expertise = agent_expertise or {}
        
        # Initialize conflict tracking
        self.active_conflicts = {}  # conflict_id -> conflict_data
        self.resolution_history = {}  # conflict_id -> resolution_data
        self.agent_performance = {}  # agent_id -> performance_metrics
        
        # Strategy implementations
        self.resolution_strategies = {
            ResolutionStrategy.CONSENSUS: self._resolve_by_consensus,
            ResolutionStrategy.CONFIDENCE: self._resolve_by_confidence,
            ResolutionStrategy.EXPERTISE: self._resolve_by_expertise,
            ResolutionStrategy.WEIGHTED_VOTE: self._resolve_by_weighted_vote,
            ResolutionStrategy.HIERARCHICAL: self._resolve_by_hierarchy,
            ResolutionStrategy.HYBRID: self._resolve_by_hybrid
        }
        
        logger.info(f"Conflict Resolver initialized with {default_strategy.name} strategy")
    
    def register_conflict(self, 
                         domain: str,
                         competing_decisions: List[Dict],
                         affected_agents: List[str],
                         context: Optional[Dict] = None,
                         urgency: float = 0.5,
                         strategy: Optional[ResolutionStrategy] = None) -> str:
        """
        Register a new conflict for resolution.
        
        Args:
            domain: Domain/topic of the conflict (e.g., "code_repair", "prioritization")
            competing_decisions: List of competing decisions with metadata
            affected_agents: List of agent IDs affected by this conflict
            context: Additional context information relevant to the conflict
            urgency: Urgency level of resolution (0-1, higher is more urgent)
            strategy: Specific strategy to use, or None for default
            
        Returns:
            conflict_id: ID of the registered conflict
        """
        conflict_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        # Validate competing decisions format
        for decision in competing_decisions:
            if not isinstance(decision, dict) or 'agent_id' not in decision or 'decision' not in decision:
                raise ValueError("Each competing decision must be a dict with at least 'agent_id' and 'decision' keys")
            
            # Add confidence if not provided
            if 'confidence' not in decision:
                decision['confidence'] = 0.5  # Default medium confidence
        
        # Create conflict record
        conflict_data = {
            "conflict_id": conflict_id,
            "domain": domain,
            "competing_decisions": competing_decisions,
            "affected_agents": affected_agents,
            "context": context or {},
            "urgency": urgency,
            "strategy": strategy.name if strategy else self.default_strategy.name,
            "status": ConflictStatus.PENDING.name,
            "created_at": timestamp,
            "updated_at": timestamp,
            "resolution_attempts": 0,
            "resolution_deadline": (datetime.datetime.now() + 
                                  datetime.timedelta(seconds=self.decision_timeout * (1 + urgency))).isoformat(),
            "resolution_progress": 0.0,
            "resolution_result": None,
            "resolution_explanation": None
        }
        
        # Store conflict
        self.active_conflicts[conflict_id] = conflict_data
        
        logger.info(f"Registered conflict {conflict_id} in domain '{domain}' with {len(competing_decisions)} competing decisions")
        return conflict_id
    
    def resolve_conflict(self, 
                        conflict_id: str,
                        additional_context: Optional[Dict] = None,
                        force_strategy: Optional[ResolutionStrategy] = None) -> Dict:
        """
        Attempt to resolve a registered conflict.
        
        Args:
            conflict_id: ID of the conflict to resolve
            additional_context: Additional context that may help resolution
            force_strategy: Override the conflict's strategy with this one
            
        Returns:
            resolution: Resolution result with metadata
        """
        if conflict_id not in self.active_conflicts:
            raise ValueError(f"Conflict {conflict_id} not found")
        
        conflict = self.active_conflicts[conflict_id]
        
        # Update conflict with additional context
        if additional_context:
            conflict["context"].update(additional_context)
            conflict["updated_at"] = datetime.datetime.now().isoformat()
        
        # Determine resolution strategy
        strategy = force_strategy or ResolutionStrategy[conflict["strategy"]]
        
        # Increment resolution attempts
        conflict["resolution_attempts"] += 1
        
        # Check if we need to escalate based on max attempts
        if conflict["resolution_attempts"] > self.escalation_policy["max_attempts"]:
            return self._escalate_conflict(conflict_id, "Exceeded maximum resolution attempts")
        
        # Update status to resolving
        conflict["status"] = ConflictStatus.RESOLVING.name
        conflict["resolution_progress"] = 0.25
        
        # Apply resolution strategy
        try:
            resolution_func = self.resolution_strategies[strategy]
            result, confidence, explanation = resolution_func(conflict)
            
            # Update progress
            conflict["resolution_progress"] = 0.75
            
            # Check confidence threshold
            if confidence < self.confidence_threshold:
                # Try hybrid approach if confidence is too low
                if strategy != ResolutionStrategy.HYBRID:
                    logger.info(f"Confidence {confidence} below threshold, trying hybrid strategy")
                    result, confidence, explanation = self._resolve_by_hybrid(conflict)
                
                # If still below threshold, escalate
                if confidence < self.confidence_threshold:
                    return self._escalate_conflict(conflict_id, 
                                                "Confidence below threshold: " + 
                                                f"{confidence} < {self.confidence_threshold}")
            
            # Record successful resolution
            resolution = {
                "conflict_id": conflict_id,
                "resolved_at": datetime.datetime.now().isoformat(),
                "resolution_strategy": strategy.name,
                "resolution_result": result,
                "confidence": confidence,
                "explanation": explanation,
                "resolution_attempts": conflict["resolution_attempts"]
            }
            
            # Update conflict status
            conflict["status"] = ConflictStatus.RESOLVED.name
            conflict["resolution_result"] = result
            conflict["resolution_explanation"] = explanation
            conflict["resolution_progress"] = 1.0
            conflict["updated_at"] = datetime.datetime.now().isoformat()
            
            # Add to history and update agent performance
            self.resolution_history[conflict_id] = resolution
            self._update_agent_performance(conflict, result)
            
            # Move from active conflicts to history if needed
            # Here we keep it in active_conflicts for the caller to access
            
            logger.info(f"Resolved conflict {conflict_id} with strategy {strategy.name}, confidence {confidence:.2f}")
            return resolution
            
        except Exception as e:
            logger.error(f"Error resolving conflict {conflict_id}: {e}")
            return self._escalate_conflict(conflict_id, f"Error during resolution: {str(e)}")
    
    def get_conflict_status(self, conflict_id: str) -> Dict:
        """
        Get the current status of a conflict.
        
        Args:
            conflict_id: ID of the conflict to check
            
        Returns:
            status: Current status information for the conflict
        """
        if conflict_id not in self.active_conflicts and conflict_id not in self.resolution_history:
            raise ValueError(f"Conflict {conflict_id} not found")
        
        # Check if conflict is active or historical
        if conflict_id in self.active_conflicts:
            conflict = self.active_conflicts[conflict_id]
            is_active = True
        else:
            conflict = self.resolution_history[conflict_id]
            is_active = False
        
        # Calculate time remaining if active and not resolved
        time_remaining = None
        if is_active and conflict["status"] != ConflictStatus.RESOLVED.name:
            try:
                deadline = datetime.datetime.fromisoformat(conflict["resolution_deadline"])
                now = datetime.datetime.now()
                time_remaining = max(0, (deadline - now).total_seconds())
            except (ValueError, KeyError):
                time_remaining = 0
        
        # Prepare status response
        status = {
            "conflict_id": conflict_id,
            "status": conflict["status"],
            "domain": conflict["domain"],
            "resolution_progress": conflict["resolution_progress"],
            "resolution_attempts": conflict["resolution_attempts"],
            "time_remaining": time_remaining,
            "is_active": is_active,
            "created_at": conflict.get("created_at"),
            "updated_at": conflict.get("updated_at"),
            "resolution_result": conflict.get("resolution_result"),
            "resolution_explanation": conflict.get("resolution_explanation")
        }
        
        return status
    
    def list_active_conflicts(self, domain: Optional[str] = None, agent_id: Optional[str] = None) -> List[Dict]:
        """
        List all active conflicts, optionally filtered by domain or agent.
        
        Args:
            domain: Optional domain to filter conflicts
            agent_id: Optional agent ID to filter conflicts
            
        Returns:
            conflicts: List of conflict status summaries
        """
        active_conflicts = []
        
        for conflict_id, conflict in self.active_conflicts.items():
            # Apply domain filter if provided
            if domain and conflict["domain"] != domain:
                continue
            
            # Apply agent filter if provided
            if agent_id:
                # Check if agent is in affected_agents or is the source of any competing decision
                agent_involved = (agent_id in conflict["affected_agents"] or
                                any(d["agent_id"] == agent_id for d in conflict["competing_decisions"]))
                if not agent_involved:
                    continue
            
            # Add conflict summary
            active_conflicts.append({
                "conflict_id": conflict_id,
                "domain": conflict["domain"],
                "status": conflict["status"],
                "affected_agents": conflict["affected_agents"],
                "created_at": conflict["created_at"],
                "resolution_progress": conflict["resolution_progress"],
                "urgency": conflict["urgency"]
            })
        
        return active_conflicts
    
    def get_resolution_history(self, 
                             domain: Optional[str] = None, 
                             agent_id: Optional[str] = None,
                             limit: int = 100) -> List[Dict]:
        """
        Get resolution history, optionally filtered by domain or agent.
        
        Args:
            domain: Optional domain to filter history
            agent_id: Optional agent ID to filter history
            limit: Maximum number of history items to return
            
        Returns:
            history: List of resolution history items
        """
        history_items = []
        
        # Sort history by resolved_at timestamp (newest first)
        sorted_history = sorted(
            self.resolution_history.values(),
            key=lambda x: x.get("resolved_at", ""),
            reverse=True
        )
        
        for resolution in sorted_history:
            # Skip if no conflict data (shouldn't happen but being defensive)
            conflict_id = resolution.get("conflict_id")
            if not conflict_id:
                continue
                
            # Try to get original conflict data
            conflict = None
            if conflict_id in self.active_conflicts:
                conflict = self.active_conflicts[conflict_id]
            
            # If we don't have the conflict data anymore, we can't filter by domain/agent
            if not conflict:
                # We can only add the resolution data we have
                history_items.append(resolution)
                continue
                
            # Apply domain filter if provided
            if domain and conflict["domain"] != domain:
                continue
                
            # Apply agent filter if provided
            if agent_id:
                # Check if agent is in affected_agents or is the source of any competing decision
                agent_involved = (agent_id in conflict["affected_agents"] or
                                any(d["agent_id"] == agent_id for d in conflict["competing_decisions"]))
                if not agent_involved:
                    continue
            
            # Add combined conflict and resolution data
            history_items.append({
                "conflict_id": conflict_id,
                "domain": conflict["domain"],
                "resolved_at": resolution["resolved_at"],
                "resolution_strategy": resolution["resolution_strategy"],
                "resolution_result": resolution["resolution_result"],
                "confidence": resolution["confidence"],
                "resolution_attempts": resolution["resolution_attempts"]
            })
            
            # Check limit
            if len(history_items) >= limit:
                break
        
        return history_items
    
    def update_agent_expertise(self, agent_id: str, expertise: Dict[str, float]):
        """
        Update the expertise levels for an agent.
        
        Args:
            agent_id: ID of the agent to update
            expertise: Dictionary mapping expertise domains to scores (0-1)
        """
        # Initialize agent expertise if not present
        if agent_id not in self.agent_expertise:
            self.agent_expertise[agent_id] = {}
        
        # Update expertise
        self.agent_expertise[agent_id].update(expertise)
        
        logger.info(f"Updated expertise for agent {agent_id}: {expertise}")
    
    def _resolve_by_consensus(self, conflict: Dict) -> Tuple[Any, float, str]:
        """
        Resolve conflict by consensus (majority vote).
        
        Returns:
            result: The winning decision
            confidence: Confidence level in the resolution (0-1)
            explanation: Explanation of the resolution
        """
        # Group decisions by their content
        decision_counts = {}
        
        for decision in conflict["competing_decisions"]:
            # Convert decision to a hashable form if needed
            decision_key = str(decision["decision"])
            
            if decision_key not in decision_counts:
                decision_counts[decision_key] = {
                    "count": 0,
                    "confidence_sum": 0,
                    "agents": [],
                    "original_decision": decision["decision"]
                }
            
            # Increment count and sum confidence
            decision_counts[decision_key]["count"] += 1
            decision_counts[decision_key]["confidence_sum"] += decision.get("confidence", 0.5)
            decision_counts[decision_key]["agents"].append(decision["agent_id"])
        
        # Find decision with highest count
        max_count = 0
        max_confidence_sum = 0
        winning_decision = None
        
        for decision_key, data in decision_counts.items():
            if data["count"] > max_count:
                max_count = data["count"]
                max_confidence_sum = data["confidence_sum"]
                winning_decision = data
            elif data["count"] == max_count:
                # Tiebreaker: highest confidence sum
                if data["confidence_sum"] > max_confidence_sum:
                    max_confidence_sum = data["confidence_sum"]
                    winning_decision = data
        
        if not winning_decision:
            return None, 0.0, "No decisions provided"
        
        # Calculate confidence based on proportion of votes and average confidence
        total_decisions = len(conflict["competing_decisions"])
        vote_proportion = max_count / total_decisions
        avg_confidence = max_confidence_sum / max_count
        
        # Overall confidence is a blend of vote proportion and average confidence
        confidence = (vote_proportion * 0.7) + (avg_confidence * 0.3)
        
        explanation = (
            f"Decision selected by consensus with {max_count}/{total_decisions} votes "
            f"({vote_proportion:.1%}) and average confidence {avg_confidence:.1%}. "
            f"Supporting agents: {', '.join(winning_decision['agents'])}"
        )
        
        return winning_decision["original_decision"], confidence, explanation
    
    def _resolve_by_confidence(self, conflict: Dict) -> Tuple[Any, float, str]:
        """
        Resolve conflict by selecting the decision with highest confidence.
        
        Returns:
            result: The winning decision
            confidence: Confidence level in the resolution (0-1)
            explanation: Explanation of the resolution
        """
        if not conflict["competing_decisions"]:
            return None, 0.0, "No decisions provided"
        
        # Find decision with highest confidence
        max_confidence = -1
        winning_decision = None
        
        for decision in conflict["competing_decisions"]:
            confidence = decision.get("confidence", 0.5)
            
            if confidence > max_confidence:
                max_confidence = confidence
                winning_decision = decision
        
        if not winning_decision:
            return None, 0.0, "Could not identify winning decision"
        
        # If multiple decisions with same confidence, note that in explanation
        tied_agents = []
        for decision in conflict["competing_decisions"]:
            if decision.get("confidence", 0.5) == max_confidence and decision["agent_id"] != winning_decision["agent_id"]:
                tied_agents.append(decision["agent_id"])
        
        if tied_agents:
            tied_note = f" (tied with agents: {', '.join(tied_agents)})"
        else:
            tied_note = ""
            
        explanation = (
            f"Decision selected based on highest confidence ({max_confidence:.1%}) "
            f"from agent {winning_decision['agent_id']}{tied_note}"
        )
        
        return winning_decision["decision"], max_confidence, explanation
    
    def _resolve_by_expertise(self, conflict: Dict) -> Tuple[Any, float, str]:
        """
        Resolve conflict by prioritizing agents with highest domain expertise.
        
        Returns:
            result: The winning decision
            confidence: Confidence level in the resolution (0-1)
            explanation: Explanation of the resolution
        """
        if not conflict["competing_decisions"]:
            return None, 0.0, "No decisions provided"
        
        domain = conflict["domain"]
        
        # Calculate expertise scores for each decision
        decision_scores = []
        
        for decision in conflict["competing_decisions"]:
            agent_id = decision["agent_id"]
            base_confidence = decision.get("confidence", 0.5)
            
            # Get agent's expertise in this domain
            expertise = 0.5  # Default medium expertise
            if agent_id in self.agent_expertise and domain in self.agent_expertise[agent_id]:
                expertise = self.agent_expertise[agent_id][domain]
            
            # Combined score: blend of expertise and confidence
            score = (expertise * 0.7) + (base_confidence * 0.3)
            
            decision_scores.append({
                "decision": decision["decision"],
                "agent_id": agent_id,
                "expertise": expertise,
                "base_confidence": base_confidence,
                "score": score
            })
        
        # Sort by score (descending)
        decision_scores.sort(key=lambda x: x["score"], reverse=True)
        
        if not decision_scores:
            return None, 0.0, "Could not score decisions"
        
        # Select highest scoring decision
        winning_score = decision_scores[0]
        
        explanation = (
            f"Decision selected based on agent expertise. Agent {winning_score['agent_id']} "
            f"has {winning_score['expertise']:.1%} expertise in domain '{domain}' with "
            f"base confidence {winning_score['base_confidence']:.1%}, resulting in "
            f"overall score {winning_score['score']:.1%}"
        )
        
        return winning_score["decision"], winning_score["score"], explanation
    
    def _resolve_by_weighted_vote(self, conflict: Dict) -> Tuple[Any, float, str]:
        """
        Resolve conflict by weighted voting based on agent reliability and expertise.
        
        Returns:
            result: The winning decision
            confidence: Confidence level in the resolution (0-1)
            explanation: Explanation of the resolution
        """
        if not conflict["competing_decisions"]:
            return None, 0.0, "No decisions provided"
        
        domain = conflict["domain"]
        
        # Group decisions by their content
        decision_votes = {}
        
        for decision in conflict["competing_decisions"]:
            agent_id = decision["agent_id"]
            decision_key = str(decision["decision"])
            
            # Calculate agent's vote weight
            base_weight = 1.0
            
            # Add expertise factor
            expertise = 0.5  # Default medium expertise
            if agent_id in self.agent_expertise and domain in self.agent_expertise[agent_id]:
                expertise = self.agent_expertise[agent_id][domain]
            
            # Add reliability factor based on past performance
            reliability = 0.5  # Default medium reliability
            if agent_id in self.agent_performance:
                perf = self.agent_performance[agent_id]
                if perf["total_conflicts"] > 0:
                    reliability = perf["successful_resolutions"] / perf["total_conflicts"]
            
            # Add confidence factor
            confidence = decision.get("confidence", 0.5)
            
            # Calculate total weight (expertise has highest weight)
            weight = base_weight * (expertise * 0.5 + reliability * 0.3 + confidence * 0.2)
            
            if decision_key not in decision_votes:
                decision_votes[decision_key] = {
                    "total_weight": 0,
                    "agents": [],
                    "original_decision": decision["decision"],
                    "weights": {}
                }
            
            decision_votes[decision_key]["total_weight"] += weight
            decision_votes[decision_key]["agents"].append(agent_id)
            decision_votes[decision_key]["weights"][agent_id] = weight
        
        # Find decision with highest weight
        max_weight = 0
        winning_decision = None
        
        for decision_key, data in decision_votes.items():
            if data["total_weight"] > max_weight:
                max_weight = data["total_weight"]
                winning_decision = data
        
        if not winning_decision:
            return None, 0.0, "Could not identify winning decision"
        
        # Calculate total weight across all decisions
        total_weight = sum(d["total_weight"] for d in decision_votes.values())
        
        # Calculate confidence as proportion of total weight
        confidence = max_weight / total_weight if total_weight > 0 else 0
        
        # Prepare detailed weight explanation
        weight_details = []
        for agent_id, weight in winning_decision["weights"].items():
            weight_details.append(f"{agent_id}: {weight:.2f}")
        
        explanation = (
            f"Decision selected by weighted voting with {max_weight:.2f}/{total_weight:.2f} "
            f"total weight ({confidence:.1%}). Contributing agents with weights: "
            f"{', '.join(weight_details)}"
        )
        
        return winning_decision["original_decision"], confidence, explanation
    
    def _resolve_by_hierarchy(self, conflict: Dict) -> Tuple[Any, float, str]:
        """
        Resolve conflict using a predefined agent hierarchy.
        
        Returns:
            result: The winning decision
            confidence: Confidence level in the resolution (0-1)
            explanation: Explanation of the resolution
        """
        if not conflict["competing_decisions"]:
            return None, 0.0, "No decisions provided"
        
        # Agent hierarchy (lower rank = higher priority)
        # This could be configured as part of the resolver initialization
        agent_hierarchy = {
            self.orchestrator_id: 0,  # Orchestrator has highest priority
            "priority_analyzer": 1,
            "verification_agent": 2,
            "bug_detector": 3,
            "relationship_analyst": 4,
            # Default rank for unlisted agents
            "default": 10
        }
        
        # Rank decisions by agent hierarchy
        ranked_decisions = []
        
        for decision in conflict["competing_decisions"]:
            agent_id = decision["agent_id"]
            
            # Get agent's rank (lower = higher priority)
            rank = agent_hierarchy.get(agent_id, agent_hierarchy["default"])
            
            ranked_decisions.append({
                "decision": decision["decision"],
                "agent_id": agent_id,
                "rank": rank,
                "confidence": decision.get("confidence", 0.5)
            })
        
        # Sort by rank (ascending)
        ranked_decisions.sort(key=lambda x: x["rank"])
        
        if not ranked_decisions:
            return None, 0.0, "Could not rank decisions"
        
        # Select highest ranking decision
        winning_decision = ranked_decisions[0]
        
        # If multiple decisions with same rank, note that in explanation
        tied_agents = []
        for decision in ranked_decisions[1:]:
            if decision["rank"] == winning_decision["rank"]:
                tied_agents.append(decision["agent_id"])
            else:
                # We've moved beyond tied ranks
                break
        
        if tied_agents:
            tied_note = f" (tied with agents: {', '.join(tied_agents)})"
        else:
            tied_note = ""
        
        explanation = (
            f"Decision selected based on agent hierarchy. Agent {winning_decision['agent_id']} "
            f"has priority rank {winning_decision['rank']}{tied_note}"
        )
        
        # Confidence is based on the agent's own confidence and a rank factor
        # Higher ranks (lower numeric values) get a confidence boost
        rank_factor = max(0.0, 1.0 - (winning_decision["rank"] * 0.1))
        confidence = (winning_decision["confidence"] * 0.7) + (rank_factor * 0.3)
        
        return winning_decision["decision"], confidence, explanation
    
    def _resolve_by_hybrid(self, conflict: Dict) -> Tuple[Any, float, str]:
        """
        Resolve conflict using a hybrid approach combining multiple strategies.
        
        Returns:
            result: The winning decision
            confidence: Confidence level in the resolution (0-1)
            explanation: Explanation of the resolution
        """
        if not conflict["competing_decisions"]:
            return None, 0.0, "No decisions provided"
        
        # Apply each strategy and collect results
        strategy_results = []
        
        for strategy_enum, strategy_func in self.resolution_strategies.items():
            # Skip hybrid strategy to avoid recursion
            if strategy_enum == ResolutionStrategy.HYBRID:
                continue
                
            try:
                result, confidence, explanation = strategy_func(conflict)
                strategy_results.append({
                    "strategy": strategy_enum.name,
                    "result": result,
                    "confidence": confidence,
                    "explanation": explanation
                })
            except Exception as e:
                logger.warning(f"Strategy {strategy_enum.name} failed: {e}")
        
        if not strategy_results:
            return None, 0.0, "All resolution strategies failed"
        
        # Group results by decision
        decision_scores = {}
        
        for result in strategy_results:
            decision_key = str(result["result"])
            
            if decision_key not in decision_scores:
                decision_scores[decision_key] = {
                    "score": 0,
                    "confidence_sum": 0,
                    "strategies": [],
                    "original_decision": result["result"]
                }
            
            # Add this strategy's confidence to the score
            decision_scores[decision_key]["score"] += result["confidence"]
            decision_scores[decision_key]["confidence_sum"] += result["confidence"]
            decision_scores[decision_key]["strategies"].append(result["strategy"])
        
        # Find decision with highest score
        max_score = 0
        winning_decision = None
        
        for decision_key, data in decision_scores.items():
            if data["score"] > max_score:
                max_score = data["score"]
                winning_decision = data
        
        if not winning_decision:
            return None, 0.0, "Could not identify winning decision"
        
        # Calculate confidence as average of contributing strategies
        num_strategies = len(winning_decision["strategies"])
        avg_confidence = winning_decision["confidence_sum"] / num_strategies if num_strategies > 0 else 0
        
        # Boost confidence based on strategy agreement
        strategy_agreement = num_strategies / len(self.resolution_strategies)
        boosted_confidence = avg_confidence * (0.7 + 0.3 * strategy_agreement)
        
        explanation = (
            f"Decision selected by hybrid approach with {num_strategies} supporting strategies "
            f"({', '.join(winning_decision['strategies'])}). Average confidence: {avg_confidence:.1%}, "
            f"boosted by {strategy_agreement:.1%} strategy agreement to {boosted_confidence:.1%}"
        )
        
        return winning_decision["original_decision"], boosted_confidence, explanation
    
    def _escalate_conflict(self, conflict_id: str, reason: str) -> Dict:
        """
        Escalate a conflict that cannot be resolved automatically.
        
        Args:
            conflict_id: ID of the conflict to escalate
            reason: Reason for escalation
            
        Returns:
            escalation: Escalation details
        """
        if conflict_id not in self.active_conflicts:
            raise ValueError(f"Conflict {conflict_id} not found")
        
        conflict = self.active_conflicts[conflict_id]
        
        # Update conflict status
        conflict["status"] = ConflictStatus.ESCALATED.name
        conflict["resolution_explanation"] = f"Escalated: {reason}"
        conflict["updated_at"] = datetime.datetime.now().isoformat()
        
        # Create escalation record
        escalation = {
            "conflict_id": conflict_id,
            "escalated_at": datetime.datetime.now().isoformat(),
            "reason": reason,
            "escalation_level": 0,  # Start at first level
            "escalation_path": self.escalation_policy["escalation_path"],
            "current_escalation_target": self.escalation_policy["escalation_path"][0],
            "resolution_attempts": conflict["resolution_attempts"],
            "resolution_required_by": conflict["resolution_deadline"]
        }
        
        logger.info(f"Escalated conflict {conflict_id}: {reason}")
        return escalation
    
    def _update_agent_performance(self, conflict: Dict, result: Any):
        """
        Update agent performance metrics based on conflict resolution.
        
        Args:
            conflict: The conflict data
            result: The resolution result
        """
        # Identify agents that had the correct decision
        correct_agents = []
        incorrect_agents = []
        
        for decision in conflict["competing_decisions"]:
            agent_id = decision["agent_id"]
            
            # Compare decision with result (this may need more sophisticated comparison)
            if str(decision["decision"]) == str(result):
                correct_agents.append(agent_id)
            else:
                incorrect_agents.append(agent_id)
        
        # Update performance metrics for all involved agents
        for agent_id in set(correct_agents + incorrect_agents):
            if agent_id not in self.agent_performance:
                self.agent_performance[agent_id] = {
                    "total_conflicts": 0,
                    "successful_resolutions": 0,
                    "domains": {}
                }
            
            self.agent_performance[agent_id]["total_conflicts"] += 1
            
            if agent_id in correct_agents:
                self.agent_performance[agent_id]["successful_resolutions"] += 1
            
            # Update domain-specific performance
            domain = conflict["domain"]
            if domain not in self.agent_performance[agent_id]["domains"]:
                self.agent_performance[agent_id]["domains"][domain] = {
                    "total": 0,
                    "successful": 0
                }
            
            self.agent_performance[agent_id]["domains"][domain]["total"] += 1
            
            if agent_id in correct_agents:
                self.agent_performance[agent_id]["domains"][domain]["successful"] += 1


# Example usage
if __name__ == "__main__":
    # Create a conflict resolver
    resolver = ConflictResolver(orchestrator_id="orchestrator_agent")
    
    # Register agent expertise
    resolver.update_agent_expertise("bug_detector", {
        "code_repair": 0.9,
        "bug_detection": 0.95,
        "test_generation": 0.7
    })
    
    resolver.update_agent_expertise("verification_agent", {
        "code_repair": 0.8,
        "bug_detection": 0.7,
        "test_generation": 0.9
    })
    
    # Register a conflict
    competing_decisions = [
        {
            "agent_id": "bug_detector",
            "decision": {"fix_type": "add_null_check", "priority": "high"},
            "confidence": 0.85
        },
        {
            "agent_id": "verification_agent",
            "decision": {"fix_type": "add_type_check", "priority": "medium"},
            "confidence": 0.75
        },
        {
            "agent_id": "relationship_analyst",
            "decision": {"fix_type": "add_null_check", "priority": "medium"},
            "confidence": 0.6
        }
    ]
    
    conflict_id = resolver.register_conflict(
        domain="code_repair",
        competing_decisions=competing_decisions,
        affected_agents=["bug_detector", "verification_agent", "relationship_analyst"],
        context={"file": "main.py", "line": 42, "function": "process_data"}
    )
    
    # Resolve the conflict
    resolution = resolver.resolve_conflict(conflict_id)
    
    print(f"Resolution: {resolution['resolution_result']}")
    print(f"Confidence: {resolution['confidence']:.2f}")
    print(f"Explanation: {resolution['explanation']}")
    
    # Get conflict status
    status = resolver.get_conflict_status(conflict_id)
    print(f"Status: {status['status']}")
