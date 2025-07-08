#!/usr/bin/env python3
"""
Context Preserver

This module provides enhanced context preservation mechanisms for agent conversations,
ensuring that relevant context is maintained across long-running, multi-step interactions
between agents in the Triangulum agentic system.
"""

import logging
import datetime
import json
import os
import time
from typing import Dict, List, Any, Optional, Union, Tuple, Set
import uuid
import heapq
from enum import Enum
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContextRelevance(Enum):
    """Relevance levels for context elements."""
    CRITICAL = 0     # Essential context that must be preserved
    HIGH = 1         # Important context with high relevance
    MEDIUM = 2       # Moderately relevant context
    LOW = 3          # Context with limited relevance
    BACKGROUND = 4   # Background context with minimal immediate relevance

class ContextPreserver:
    """
    Preserves and manages context across long-running agent conversations,
    ensuring that critical information is maintained while less relevant
    context is pruned to prevent context overflow.
    """
    
    def __init__(self, 
                max_context_size: int = 8192,
                relevance_threshold: ContextRelevance = ContextRelevance.MEDIUM,
                context_window_hours: float = 24.0,
                enable_semantic_chunking: bool = True,
                enable_context_summarization: bool = True,
                max_agents_per_context: int = 10):
        """
        Initialize the context preserver.
        
        Args:
            max_context_size: Maximum token size for preserved context
            relevance_threshold: Minimum relevance level to retain context
            context_window_hours: Time window for context relevance in hours
            enable_semantic_chunking: Whether to use semantic chunking for context
            enable_context_summarization: Whether to summarize context when it exceeds limits
            max_agents_per_context: Maximum number of agents in a shared context
        """
        self.max_context_size = max_context_size
        self.relevance_threshold = relevance_threshold
        self.context_window_hours = context_window_hours
        self.enable_semantic_chunking = enable_semantic_chunking
        self.enable_context_summarization = enable_context_summarization
        self.max_agents_per_context = max_agents_per_context
        
        # Initialize context storage
        self.conversation_contexts = {}  # conversation_id -> context_data
        self.agent_contexts = {}  # agent_id -> {conversation_id -> context_relevance}
        self.shared_contexts = {}  # shared_context_id -> context_data
        
        # Context usage metrics
        self.context_usage_stats = {
            "total_contexts": 0,
            "active_contexts": 0,
            "total_tokens_preserved": 0,
            "pruned_contexts": 0,
            "summarized_contexts": 0,
            "context_retrievals": 0
        }
        
        logger.info(f"Context Preserver initialized with max_context_size={max_context_size}")
    
    def create_conversation_context(self, 
                                  initiating_agent: str,
                                  participating_agents: List[str],
                                  domain: str,
                                  initial_context: Optional[Dict] = None,
                                  context_lifespan_hours: Optional[float] = None) -> str:
        """
        Create a new conversation context.
        
        Args:
            initiating_agent: ID of the agent initiating the conversation
            participating_agents: List of agent IDs participating in the conversation
            domain: Domain/topic of the conversation
            initial_context: Initial context data to include
            context_lifespan_hours: Override the default context lifespan
            
        Returns:
            conversation_id: ID of the created conversation context
        """
        conversation_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        # Ensure list of participating agents includes the initiating agent
        if initiating_agent not in participating_agents:
            participating_agents = [initiating_agent] + participating_agents
        
        # Limit number of agents if it exceeds maximum
        if len(participating_agents) > self.max_agents_per_context:
            logger.warning(f"Number of participating agents ({len(participating_agents)}) exceeds maximum ({self.max_agents_per_context}). Limiting to most relevant agents.")
            participating_agents = participating_agents[:self.max_agents_per_context]
        
        # Create context data structure
        context_data = {
            "conversation_id": conversation_id,
            "initiating_agent": initiating_agent,
            "participating_agents": participating_agents,
            "domain": domain,
            "created_at": timestamp,
            "updated_at": timestamp,
            "expires_at": (datetime.datetime.now() + datetime.timedelta(hours=context_lifespan_hours or self.context_window_hours)).isoformat(),
            "context_elements": [],
            "token_count": 0,
            "summary": None,
            "semantic_chunks": {},
            "references": {},
            "status": "active"
        }
        
        # Add initial context if provided
        if initial_context:
            for key, value in initial_context.items():
                self.add_context_element(
                    conversation_id=conversation_id,
                    source_agent=initiating_agent,
                    element_type="initial",
                    element_key=key,
                    element_value=value,
                    relevance=ContextRelevance.HIGH
                )
        
        # Store the context
        self.conversation_contexts[conversation_id] = context_data
        
        # Update agent contexts
        for agent_id in participating_agents:
            if agent_id not in self.agent_contexts:
                self.agent_contexts[agent_id] = {}
            
            self.agent_contexts[agent_id][conversation_id] = ContextRelevance.HIGH
        
        # Update metrics
        self.context_usage_stats["total_contexts"] += 1
        self.context_usage_stats["active_contexts"] += 1
        
        logger.info(f"Created conversation context {conversation_id} for {domain} domain with {len(participating_agents)} agents")
        return conversation_id
    
    def add_context_element(self,
                          conversation_id: str,
                          source_agent: str,
                          element_type: str,
                          element_key: str,
                          element_value: Any,
                          relevance: ContextRelevance = ContextRelevance.MEDIUM,
                          lifespan_hours: Optional[float] = None,
                          metadata: Optional[Dict] = None) -> str:
        """
        Add a new element to a conversation context.
        
        Args:
            conversation_id: ID of the conversation context
            source_agent: ID of the agent adding the element
            element_type: Type of context element (message, fact, decision, etc.)
            element_key: Key/identifier for the element
            element_value: Value of the context element
            relevance: Relevance level of the element
            lifespan_hours: Override the default element lifespan
            metadata: Additional metadata for the element
            
        Returns:
            element_id: ID of the added context element
        """
        if conversation_id not in self.conversation_contexts:
            raise ValueError(f"Conversation context {conversation_id} not found")
        
        context = self.conversation_contexts[conversation_id]
        
        # Check if agent is a participant
        if source_agent not in context["participating_agents"]:
            raise ValueError(f"Agent {source_agent} is not a participant in conversation {conversation_id}")
        
        # Generate element ID
        element_id = f"{conversation_id}_{int(time.time())}_{source_agent}_{element_key}"
        timestamp = datetime.datetime.now().isoformat()
        
        # Calculate expiration time
        lifespan = lifespan_hours or self.context_window_hours
        expires_at = (datetime.datetime.now() + datetime.timedelta(hours=lifespan)).isoformat()
        
        # Estimate token count
        value_str = str(element_value)
        token_count = self._estimate_token_count(value_str)
        
        # Create element data
        element = {
            "element_id": element_id,
            "source_agent": source_agent,
            "element_type": element_type,
            "element_key": element_key,
            "element_value": element_value,
            "relevance": relevance.name,
            "created_at": timestamp,
            "expires_at": expires_at,
            "token_count": token_count,
            "metadata": metadata or {}
        }
        
        # Add element to context
        context["context_elements"].append(element)
        context["token_count"] += token_count
        context["updated_at"] = timestamp
        
        # Update context metrics
        self.context_usage_stats["total_tokens_preserved"] += token_count
        
        # Check if we need to prune the context
        if context["token_count"] > self.max_context_size:
            self._prune_context(conversation_id)
        
        # Update semantic chunks if enabled
        if self.enable_semantic_chunking:
            self._update_semantic_chunks(conversation_id, element)
        
        logger.debug(f"Added {element_type} context element {element_id} to conversation {conversation_id} (relevance: {relevance.name})")
        return element_id
    
    def get_conversation_context(self, 
                               conversation_id: str,
                               agent_id: str,
                               element_types: Optional[List[str]] = None,
                               min_relevance: ContextRelevance = None,
                               max_elements: Optional[int] = None) -> Dict:
        """
        Get context elements for a conversation.
        
        Args:
            conversation_id: ID of the conversation context
            agent_id: ID of the agent requesting the context
            element_types: Optional filter for specific element types
            min_relevance: Minimum relevance level to include
            max_elements: Maximum number of elements to return
            
        Returns:
            context: Context data including relevant elements
        """
        if conversation_id not in self.conversation_contexts:
            raise ValueError(f"Conversation context {conversation_id} not found")
        
        context = self.conversation_contexts[conversation_id]
        
        # Check if agent is a participant
        if agent_id not in context["participating_agents"]:
            raise ValueError(f"Agent {agent_id} is not a participant in conversation {conversation_id}")
        
        # Apply minimum relevance filter if provided
        min_relevance = min_relevance or self.relevance_threshold
        
        # Filter elements by relevance, type, and recency
        now = datetime.datetime.now()
        filtered_elements = []
        
        for element in context["context_elements"]:
            # Check expiration
            try:
                expires_at = datetime.datetime.fromisoformat(element["expires_at"])
                if now > expires_at:
                    continue
            except (ValueError, TypeError):
                # If expiration can't be parsed, include the element
                pass
            
            # Check relevance
            elem_relevance = ContextRelevance[element["relevance"]]
            if elem_relevance.value > min_relevance.value:
                continue
            
            # Check element type
            if element_types and element["element_type"] not in element_types:
                continue
            
            # Element passed all filters
            filtered_elements.append(element)
        
        # Sort by relevance (most relevant first), then by recency (newest first)
        filtered_elements.sort(
            key=lambda e: (
                ContextRelevance[e["relevance"]].value, 
                -time.mktime(datetime.datetime.fromisoformat(e["created_at"]).timetuple())
            )
        )
        
        # Limit number of elements if specified
        if max_elements is not None and len(filtered_elements) > max_elements:
            filtered_elements = filtered_elements[:max_elements]
        
        # Prepare context response
        context_response = {
            "conversation_id": conversation_id,
            "domain": context["domain"],
            "elements": filtered_elements,
            "summary": context.get("summary"),
            "token_count": sum(e["token_count"] for e in filtered_elements),
            "total_elements": len(filtered_elements),
            "created_at": context["created_at"],
            "updated_at": context["updated_at"]
        }
        
        # Update usage statistics
        self.context_usage_stats["context_retrievals"] += 1
        
        return context_response
    
    def get_agent_context(self, agent_id: str, max_conversations: int = 5) -> Dict:
        """
        Get aggregated context for an agent across all its active conversations.
        
        Args:
            agent_id: ID of the agent
            max_conversations: Maximum number of conversations to include
            
        Returns:
            agent_context: Aggregated context data for the agent
        """
        if agent_id not in self.agent_contexts:
            return {"agent_id": agent_id, "conversations": [], "total_conversations": 0}
        
        # Get all conversations for this agent
        agent_conversations = self.agent_contexts[agent_id]
        
        # Sort conversations by relevance to the agent
        sorted_conversations = sorted(
            [(conv_id, relevance) for conv_id, relevance in agent_conversations.items()],
            key=lambda x: ContextRelevance[x[1]].value if isinstance(x[1], str) else x[1].value
        )
        
        # Limit to max conversations
        selected_conversations = sorted_conversations[:max_conversations]
        
        # Get context for each selected conversation
        conversation_contexts = []
        
        for conv_id, _ in selected_conversations:
            if conv_id in self.conversation_contexts:
                try:
                    # Get a simplified version of the context
                    context = self.get_conversation_context(
                        conversation_id=conv_id,
                        agent_id=agent_id,
                        min_relevance=ContextRelevance.HIGH,
                        max_elements=10
                    )
                    
                    conversation_contexts.append({
                        "conversation_id": conv_id,
                        "domain": context["domain"],
                        "summary": context.get("summary"),
                        "elements": context["elements"],
                        "total_elements": context["total_elements"]
                    })
                except Exception as e:
                    logger.warning(f"Error retrieving context for conversation {conv_id}: {e}")
        
        # Prepare agent context response
        agent_context = {
            "agent_id": agent_id,
            "conversations": conversation_contexts,
            "total_conversations": len(agent_conversations)
        }
        
        return agent_context
    
    def create_shared_context(self,
                            agent_ids: List[str],
                            domain: str,
                            context_data: Dict,
                            relevance: ContextRelevance = ContextRelevance.HIGH) -> str:
        """
        Create a shared context accessible by multiple agents.
        
        Args:
            agent_ids: IDs of agents that can access this context
            domain: Domain/topic of the shared context
            context_data: Data to include in the shared context
            relevance: Relevance level of the shared context
            
        Returns:
            shared_context_id: ID of the created shared context
        """
        shared_context_id = f"shared_{str(uuid.uuid4())}"
        timestamp = datetime.datetime.now().isoformat()
        
        # Limit number of agents if it exceeds maximum
        if len(agent_ids) > self.max_agents_per_context:
            logger.warning(f"Number of agents for shared context ({len(agent_ids)}) exceeds maximum ({self.max_agents_per_context}). Limiting.")
            agent_ids = agent_ids[:self.max_agents_per_context]
        
        # Estimate token count
        token_count = self._estimate_token_count(json.dumps(context_data))
        
        # Create shared context data
        shared_context = {
            "shared_context_id": shared_context_id,
            "domain": domain,
            "agent_ids": agent_ids,
            "created_at": timestamp,
            "updated_at": timestamp,
            "expires_at": (datetime.datetime.now() + datetime.timedelta(hours=self.context_window_hours)).isoformat(),
            "relevance": relevance.name,
            "context_data": context_data,
            "token_count": token_count,
            "status": "active",
            "access_count": 0
        }
        
        # Store the shared context
        self.shared_contexts[shared_context_id] = shared_context
        
        # Update agent contexts to reference this shared context
        for agent_id in agent_ids:
            if agent_id not in self.agent_contexts:
                self.agent_contexts[agent_id] = {}
            
            # Create a special entry for shared contexts
            if "shared_contexts" not in self.agent_contexts[agent_id]:
                self.agent_contexts[agent_id]["shared_contexts"] = {}
            
            self.agent_contexts[agent_id]["shared_contexts"][shared_context_id] = relevance
        
        # Update metrics
        self.context_usage_stats["total_contexts"] += 1
        self.context_usage_stats["active_contexts"] += 1
        self.context_usage_stats["total_tokens_preserved"] += token_count
        
        logger.info(f"Created shared context {shared_context_id} for {domain} domain with {len(agent_ids)} agents")
        return shared_context_id
    
    def get_shared_context(self, shared_context_id: str, agent_id: str) -> Dict:
        """
        Get a shared context.
        
        Args:
            shared_context_id: ID of the shared context
            agent_id: ID of the agent requesting the context
            
        Returns:
            shared_context: The shared context data
        """
        if shared_context_id not in self.shared_contexts:
            raise ValueError(f"Shared context {shared_context_id} not found")
        
        shared_context = self.shared_contexts[shared_context_id]
        
        # Check if agent is authorized to access this context
        if agent_id not in shared_context["agent_ids"]:
            raise ValueError(f"Agent {agent_id} is not authorized to access shared context {shared_context_id}")
        
        # Check if context has expired
        now = datetime.datetime.now()
        try:
            expires_at = datetime.datetime.fromisoformat(shared_context["expires_at"])
            if now > expires_at:
                raise ValueError(f"Shared context {shared_context_id} has expired")
        except (ValueError, TypeError):
            # If expiration can't be parsed, allow access
            pass
        
        # Update access count
        shared_context["access_count"] += 1
        
        # Update usage statistics
        self.context_usage_stats["context_retrievals"] += 1
        
        return shared_context
    
    def update_context_relevance(self,
                               conversation_id: str,
                               agent_id: str,
                               new_relevance: ContextRelevance) -> bool:
        """
        Update the relevance of a conversation context for an agent.
        
        Args:
            conversation_id: ID of the conversation context
            agent_id: ID of the agent
            new_relevance: New relevance level
            
        Returns:
            success: Whether the update was successful
        """
        if agent_id not in self.agent_contexts:
            return False
        
        if conversation_id not in self.agent_contexts[agent_id]:
            return False
        
        # Update relevance
        self.agent_contexts[agent_id][conversation_id] = new_relevance
        logger.debug(f"Updated relevance of conversation {conversation_id} to {new_relevance.name} for agent {agent_id}")
        return True
    
    def merge_contexts(self,
                     source_context_ids: List[str],
                     agent_id: str,
                     domain: str,
                     merge_strategy: str = "combine") -> str:
        """
        Merge multiple conversation contexts into a new context.
        
        Args:
            source_context_ids: IDs of contexts to merge
            agent_id: ID of the agent performing the merge
            domain: Domain for the merged context
            merge_strategy: Strategy for merging ('combine', 'summarize', etc.)
            
        Returns:
            merged_context_id: ID of the merged context
        """
        # Validate source contexts
        valid_contexts = []
        participating_agents = set()
        
        for context_id in source_context_ids:
            if context_id in self.conversation_contexts:
                context = self.conversation_contexts[context_id]
                
                # Ensure agent has access to this context
                if agent_id in context["participating_agents"]:
                    valid_contexts.append(context)
                    participating_agents.update(context["participating_agents"])
        
        if not valid_contexts:
            raise ValueError("No valid source contexts found for merging")
        
        # Create new context for the merged result
        merged_context_id = self.create_conversation_context(
            initiating_agent=agent_id,
            participating_agents=list(participating_agents),
            domain=domain
        )
        
        # Apply merge strategy
        if merge_strategy == "combine":
            # Combine elements from all contexts, preserving the most relevant ones
            all_elements = []
            
            for context in valid_contexts:
                all_elements.extend(context["context_elements"])
            
            # Sort by relevance and recency
            all_elements.sort(
                key=lambda e: (
                    ContextRelevance[e["relevance"]].value, 
                    -time.mktime(datetime.datetime.fromisoformat(e["created_at"]).timetuple())
                )
            )
            
            # Add elements to merged context
            for element in all_elements:
                try:
                    self.add_context_element(
                        conversation_id=merged_context_id,
                        source_agent=element["source_agent"],
                        element_type=element["element_type"],
                        element_key=element["element_key"],
                        element_value=element["element_value"],
                        relevance=ContextRelevance[element["relevance"]],
                        metadata={"merged_from": element["element_id"]}
                    )
                except Exception as e:
                    logger.warning(f"Error adding element to merged context: {e}")
        
        elif merge_strategy == "summarize":
            # Create a summary of each context and add as elements
            for i, context in enumerate(valid_contexts):
                # Get existing summary or create one
                summary = context.get("summary") or self._generate_context_summary(context)
                
                self.add_context_element(
                    conversation_id=merged_context_id,
                    source_agent=agent_id,
                    element_type="summary",
                    element_key=f"summary_{i}",
                    element_value=summary,
                    relevance=ContextRelevance.HIGH,
                    metadata={"merged_from": context["conversation_id"]}
                )
        
        else:
            raise ValueError(f"Unknown merge strategy: {merge_strategy}")
        
        logger.info(f"Merged {len(valid_contexts)} contexts into new context {merged_context_id}")
        return merged_context_id
    
    def prune_expired_contexts(self) -> int:
        """
        Prune expired contexts to free up resources.
        
        Returns:
            pruned_count: Number of contexts pruned
        """
        now = datetime.datetime.now()
        pruned_count = 0
        
        # Prune conversation contexts
        contexts_to_prune = []
        
        for context_id, context in self.conversation_contexts.items():
            try:
                expires_at = datetime.datetime.fromisoformat(context["expires_at"])
                if now > expires_at:
                    contexts_to_prune.append(context_id)
            except (ValueError, TypeError):
                # If expiration can't be parsed, keep the context
                pass
        
        # Remove pruned contexts
        for context_id in contexts_to_prune:
            if context_id in self.conversation_contexts:
                # Get token count for metrics
                token_count = self.conversation_contexts[context_id].get("token_count", 0)
                
                # Remove from conversation contexts
                del self.conversation_contexts[context_id]
                
                # Remove from agent contexts
                for agent_contexts in self.agent_contexts.values():
                    if context_id in agent_contexts:
                        del agent_contexts[context_id]
                
                # Update metrics
                self.context_usage_stats["active_contexts"] -= 1
                self.context_usage_stats["pruned_contexts"] += 1
                self.context_usage_stats["total_tokens_preserved"] -= token_count
                
                pruned_count += 1
        
        # Prune shared contexts
        shared_to_prune = []
        
        for context_id, context in self.shared_contexts.items():
            try:
                expires_at = datetime.datetime.fromisoformat(context["expires_at"])
                if now > expires_at:
                    shared_to_prune.append(context_id)
            except (ValueError, TypeError):
                # If expiration can't be parsed, keep the context
                pass
        
        # Remove pruned shared contexts
        for context_id in shared_to_prune:
            if context_id in self.shared_contexts:
                # Get token count for metrics
                token_count = self.shared_contexts[context_id].get("token_count", 0)
                
                # Remove from shared contexts
                del self.shared_contexts[context_id]
                
                # Remove from agent contexts
                for agent_contexts in self.agent_contexts.values():
                    if "shared_contexts" in agent_contexts and context_id in agent_contexts["shared_contexts"]:
                        del agent_contexts["shared_contexts"][context_id]
                
                # Update metrics
                self.context_usage_stats["active_contexts"] -= 1
                self.context_usage_stats["pruned_contexts"] += 1
                self.context_usage_stats["total_tokens_preserved"] -= token_count
                
                pruned_count += 1
        
        logger.info(f"Pruned {pruned_count} expired contexts")
        return pruned_count
    
    def get_context_usage_metrics(self) -> Dict:
        """Get metrics on context usage."""
        return self.context_usage_stats
    
    def _prune_context(self, conversation_id: str) -> int:
        """
        Prune a context to keep it within size limits.
        
        Args:
            conversation_id: ID of the conversation context
            
        Returns:
            pruned_elements: Number of elements pruned
        """
        if conversation_id not in self.conversation_contexts:
            return 0
        
        context = self.conversation_contexts[conversation_id]
        
        # Check if we need to prune
        if context["token_count"] <= self.max_context_size:
            return 0
        
        # If summarization is enabled, try that first
        if self.enable_context_summarization:
            self._summarize_context(conversation_id)
            
            # Check if summarization was enough
            if context["token_count"] <= self.max_context_size:
                return 0
        
        # Sort elements by relevance and recency
        elements = context["context_elements"]
        elements.sort(
            key=lambda e: (
                ContextRelevance[e["relevance"]].value, 
                time.mktime(datetime.datetime.fromisoformat(e["created_at"]).timetuple())
            ),
            reverse=True  # Highest relevance and oldest first (to be pruned)
        )
        
        # Start pruning from the lowest relevance, oldest elements
        pruned_count = 0
        pruned_tokens = 0
        
        while context["token_count"] > self.max_context_size and elements:
            # Remove the last element (lowest relevance, oldest)
            element = elements.pop()
            element_tokens = element.get("token_count", 0)
            
            # Update token count
            context["token_count"] -= element_tokens
            pruned_tokens += element_tokens
            pruned_count += 1
        
        # Update the context elements
        context["context_elements"] = elements
        context["updated_at"] = datetime.datetime.now().isoformat()
        
        # Update metrics
        self.context_usage_stats["total_tokens_preserved"] -= pruned_tokens
        
        logger.info(f"Pruned {pruned_count} elements ({pruned_tokens} tokens) from context {conversation_id}")
        return pruned_count
    
    def _summarize_context(self, conversation_id: str) -> str:
        """
        Generate a summary of a context to reduce its size.
        
        Args:
            conversation_id: ID of the conversation context
            
        Returns:
            summary: Generated summary
        """
        if conversation_id not in self.conversation_contexts:
            raise ValueError(f"Context {conversation_id} not found")
        
        context = self.conversation_contexts[conversation_id]
        
        # Generate summary
        summary = self._generate_context_summary(context)
        
        # Store summary in context
        context["summary"] = summary
        context["updated_at"] = datetime.datetime.now().isoformat()
        
        # Update metrics
        self.context_usage_stats["summarized_contexts"] += 1
        
        logger.info(f"Generated summary for context {conversation_id}")
        return summary
    
    def _generate_context_summary(self, context: Dict) -> str:
        """
        Generate a summary of a context.
        
        Args:
            context: Context data to summarize
            
        Returns:
            summary: Generated summary
        """
        # In a real implementation, this would use more sophisticated summarization
        # For now, we'll create a simple summary based on context elements
        
        elements = context["context_elements"]
        
        # Filter to high relevance elements
        high_relevance_elements = [
            e for e in elements 
            if ContextRelevance[e["relevance"]].value <= ContextRelevance.HIGH.value
        ]
        
        # Sort by creation time (newest first)
        high_relevance_elements.sort(
            key=lambda e: datetime.datetime.fromisoformat(e["created_at"]),
            reverse=True
        )
        
        # Limit to a reasonable number of elements
        selected_elements = high_relevance_elements[:10]
        
        # Create summary
        summary_parts = [
            f"Conversation in domain '{context['domain']}' with {len(context['participating_agents'])} participants."
        ]
        
        # Add key elements to summary
        for element in selected_elements:
            element_type = element["element_type"]
            element_key = element["element_key"]
            element_value = element["element_value"]
            source_agent = element["source_agent"]
            
            # Format based on element type
            if element_type == "message":
                summary_parts.append(f"Message from {source_agent}: {str(element_value)[:100]}...")
            elif element_type == "decision":
                summary_parts.append(f"Decision by {source_agent}: {element_key} = {str(element_value)[:100]}...")
            elif element_type == "fact":
                summary_parts.append(f"Fact established: {element_key} = {str(element_value)[:100]}...")
            else:
                summary_parts.append(f"{element_type.capitalize()} ({element_key}): {str(element_value)[:100]}...")
        
        # Add concluding line if available
        if context.get("status"):
            summary_parts.append(f"Status: {context['status']}")
        
        # Join summary parts
        summary = "\n".join(summary_parts)
        
        return summary
    
    def _update_semantic_chunks(self, conversation_id: str, element: Dict):
        """
        Update semantic chunks for a context based on a new element.
        
        Args:
            conversation_id: ID of the conversation context
            element: New element to process for chunking
        """
        if not self.enable_semantic_chunking:
            return
            
        if conversation_id not in self.conversation_contexts:
            return
            
        context = self.conversation_contexts[conversation_id]
        
        # Extract key terms from element value
        value_str = str(element["element_value"])
        key_terms = self._extract_key_terms(value_str)
        
        # Update semantic chunks
        for term in key_terms:
            if term not in context["semantic_chunks"]:
                context["semantic_chunks"][term] = []
                
            context["semantic_chunks"][term].append(element["element_id"])
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """
        Extract key terms from text for semantic chunking.
        
        Args:
            text: Text to extract terms from
            
        Returns:
            key_terms: List of key terms
        """
        # In a real implementation, this would use more sophisticated NLP
        # For now, we'll use a simple approach with regex
        
        # Normalize text
        text = text.lower()
        
        # Extract words, excluding common stop words
        stop_words = {
            "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
            "at", "from", "by", "for", "with", "about", "against", "between",
            "into", "through", "during", "before", "after", "above", "below",
            "to", "of", "in", "on", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "having", "do", "does", "did", "doing",
            "this", "that", "these", "those", "it", "its", "it's", "they", "them"
        }
        
        # Extract words
        words = re.findall(r'\b\w+\b', text)
        
        # Filter out stop words and short words
        key_terms = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Limit to unique terms
        key_terms = list(set(key_terms))
        
        # Limit to a reasonable number
        if len(key_terms) > 20:
            key_terms = key_terms[:20]
            
        return key_terms
    
    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string.
        
        Args:
            text: Text to estimate token count for
            
        Returns:
            token_count: Estimated token count
        """
        # In a real implementation, this would use model-specific tokenization
        # For now, we'll use a simple approximation: ~1.3 tokens per word
        
        # Split into words
        words = re.findall(r'\b\w+\b', text)
        
        # Estimate token count (4 chars ~= 1 token is another approximation)
        char_count = len(text)
        
        # Blend word-based and char-based estimates
        word_estimate = len(words) * 1.3
        char_estimate = char_count / 4
        
        token_count = int((word_estimate + char_estimate) / 2)
        
        # Ensure minimum of 1 token
        return max(1, token_count)


# Example usage
if __name__ == "__main__":
    # Create a context preserver
    preserver = ContextPreserver()
    
    # Create a conversation context
    conversation_id = preserver.create_conversation_context(
        initiating_agent="orchestrator",
        participating_agents=["bug_detector", "verification_agent", "relationship_analyst"],
        domain="code_repair"
    )
    
    # Add context elements
    preserver.add_context_element(
        conversation_id=conversation_id,
        source_agent="orchestrator",
        element_type="message",
        element_key="task_description",
        element_value="We need to fix the null pointer issue in the login function",
        relevance=ContextRelevance.HIGH
    )
    
    preserver.add_context_element(
        conversation_id=conversation_id,
        source_agent="bug_detector",
        element_type="fact",
        element_key="bug_location",
        element_value={"file": "login.py", "line": 42, "function": "validate_user"},
        relevance=ContextRelevance.CRITICAL
    )
    
    preserver.add_context_element(
        conversation_id=conversation_id,
        source_agent="relationship_analyst",
        element_type="analysis",
        element_key="dependencies",
        element_value=["user.py", "session.py", "auth.py"],
        relevance=ContextRelevance.MEDIUM
    )
    
    # Get context for an agent
    context = preserver.get_conversation_context(
        conversation_id=conversation_id,
        agent_id="verification_agent"
    )
    
    print(f"Context for verification_agent has {len(context['elements'])} elements")
    
    # Create a shared context
    shared_context_id = preserver.create_shared_context(
        agent_ids=["orchestrator", "bug_detector", "verification_agent"],
        domain="system_configuration",
        context_data={
            "max_retry_count": 3,
            "timeout_seconds": 30,
            "verification_level": "high"
        }
    )
    
    print(f"Created shared context {shared_context_id}")
