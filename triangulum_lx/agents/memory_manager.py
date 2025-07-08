"""
Memory Manager - Implements token-efficient context retrieval for agent communication.

This module provides the MemoryManager class which enhances the ConversationMemory
with sophisticated retrieval capabilities, optimizing token usage while preserving
critical contextual information for effective agent communication.
"""

import enum
import logging
import time
from typing import Dict, List, Any, Optional, Union, Callable, Set, Tuple
import re

from triangulum_lx.agents.message import AgentMessage, MessageType, ConversationMemory

logger = logging.getLogger(__name__)


class RetrievalStrategy(enum.Enum):
    """Defines strategies for retrieving messages from conversation memory."""
    
    RECENCY = "recency"                 # Most recent messages first
    RELEVANCE = "relevance"             # Most relevant messages first (based on content similarity)
    THREAD = "thread"                   # Messages in a specific thread
    HYBRID = "hybrid"                   # Combination of recency and relevance
    ROUND_ROBIN = "round_robin"         # One message from each agent in conversation
    TYPE_PRIORITIZED = "type_prioritized"  # Prioritize specific message types


class TokenCounter:
    """Utility class for counting tokens in text."""
    
    @staticmethod
    def count_tokens(text: str) -> int:
        """
        Count the approximate number of tokens in a text.
        This is a simple approximation - for production use, 
        this should be replaced with a proper tokenizer.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            int: Approximate token count
        """
        # Simple approximation: split on whitespace and punctuation
        # In production, use the actual tokenizer from the LLM provider
        tokens = re.findall(r'\w+|[^\w\s]', text)
        return len(tokens)
    
    @staticmethod
    def count_message_tokens(message: AgentMessage) -> int:
        """
        Count the approximate number of tokens in a message.
        
        Args:
            message: The message to count tokens for
            
        Returns:
            int: Approximate token count
        """
        # Convert message to JSON for token counting
        message_json = message.to_json()
        return TokenCounter.count_tokens(message_json)


class MemoryManager:
    """
    Manages conversation memory with token-efficient retrieval strategies.
    
    This class provides enhanced capabilities for working with ConversationMemory,
    including token-efficient context retrieval, configurable retrieval strategies,
    and intelligent message selection to optimize context while staying within token limits.
    """
    
    def __init__(self, max_tokens: int = 4000):
        """
        Initialize the memory manager.
        
        Args:
            max_tokens: Maximum number of tokens to retrieve in context
        """
        self.max_tokens = max_tokens
        self._relevance_cache: Dict[str, Dict[str, float]] = {}  # Cache for relevance scores
    
    def get_context(self, 
                   conversation: ConversationMemory, 
                   strategy: RetrievalStrategy = RetrievalStrategy.RECENCY,
                   token_limit: Optional[int] = None,
                   message_limit: Optional[int] = None,
                   reference_content: Optional[Dict[str, Any]] = None,
                   filter_types: Optional[List[MessageType]] = None) -> List[AgentMessage]:
        """
        Get context from a conversation using the specified strategy.
        
        Args:
            conversation: The conversation memory to retrieve context from
            strategy: The strategy to use for retrieving messages
            token_limit: Maximum number of tokens to retrieve (overrides max_tokens if provided)
            message_limit: Maximum number of messages to retrieve
            reference_content: Reference content for relevance-based retrieval
            filter_types: Only include messages of these types
            
        Returns:
            List[AgentMessage]: Retrieved messages
        """
        limit = token_limit or self.max_tokens
        
        # Filter messages by type if specified
        messages = conversation.messages
        if filter_types:
            messages = [m for m in messages if m.message_type in filter_types]
        
        # Apply retrieval strategy
        if strategy == RetrievalStrategy.RECENCY:
            return self._get_by_recency(messages, limit, message_limit)
        elif strategy == RetrievalStrategy.RELEVANCE:
            if not reference_content:
                logger.warning("Reference content required for relevance-based retrieval, falling back to recency")
                return self._get_by_recency(messages, limit, message_limit)
            return self._get_by_relevance(messages, reference_content, limit, message_limit)
        elif strategy == RetrievalStrategy.THREAD:
            if not reference_content or "message_id" not in reference_content:
                logger.warning("Message ID required for thread-based retrieval, falling back to recency")
                return self._get_by_recency(messages, limit, message_limit)
            return self._get_by_thread(conversation, reference_content["message_id"], limit, message_limit)
        elif strategy == RetrievalStrategy.HYBRID:
            if not reference_content:
                logger.warning("Reference content required for hybrid retrieval, falling back to recency")
                return self._get_by_recency(messages, limit, message_limit)
            return self._get_by_hybrid(messages, reference_content, limit, message_limit)
        elif strategy == RetrievalStrategy.ROUND_ROBIN:
            return self._get_by_round_robin(messages, limit, message_limit)
        elif strategy == RetrievalStrategy.TYPE_PRIORITIZED:
            if not reference_content or "priority_types" not in reference_content:
                logger.warning("Priority types required for type-prioritized retrieval, falling back to recency")
                return self._get_by_recency(messages, limit, message_limit)
            return self._get_by_type_priority(
                messages, reference_content["priority_types"], limit, message_limit
            )
        
        # Default to recency if strategy not recognized
        logger.warning(f"Unrecognized retrieval strategy {strategy}, falling back to recency")
        return self._get_by_recency(messages, limit, message_limit)
    
    def _get_by_recency(self, 
                       messages: List[AgentMessage], 
                       token_limit: int,
                       message_limit: Optional[int] = None) -> List[AgentMessage]:
        """
        Get messages by recency (most recent first).
        
        Args:
            messages: List of messages to retrieve from
            token_limit: Maximum number of tokens to retrieve
            message_limit: Maximum number of messages to retrieve
            
        Returns:
            List[AgentMessage]: Retrieved messages, most recent first
        """
        # Sort messages by timestamp (newest first)
        sorted_messages = sorted(messages, key=lambda m: m.timestamp, reverse=True)
        
        # Apply message limit if specified
        if message_limit:
            sorted_messages = sorted_messages[:message_limit]
        
        # Apply token limit
        return self._apply_token_limit(sorted_messages, token_limit)
    
    def _get_by_relevance(self, 
                         messages: List[AgentMessage], 
                         reference_content: Dict[str, Any],
                         token_limit: int,
                         message_limit: Optional[int] = None) -> List[AgentMessage]:
        """
        Get messages by relevance to reference content.
        
        Args:
            messages: List of messages to retrieve from
            reference_content: Reference content to compare against
            token_limit: Maximum number of tokens to retrieve
            message_limit: Maximum number of messages to retrieve
            
        Returns:
            List[AgentMessage]: Retrieved messages, most relevant first
        """
        # Convert reference content to string for comparison
        ref_str = str(reference_content)
        
        # Calculate relevance scores
        scores = []
        for message in messages:
            # Check cache first
            cache_key = f"{message.message_id}:{hash(ref_str)}"
            if cache_key in self._relevance_cache:
                scores.append((message, self._relevance_cache[cache_key]))
                continue
            
            # Calculate relevance score (simple keyword matching for demonstration)
            # In production, use a proper semantic similarity metric
            message_str = str(message.content)
            
            # Count matching words (very simple relevance metric)
            ref_words = set(re.findall(r'\w+', ref_str.lower()))
            msg_words = set(re.findall(r'\w+', message_str.lower()))
            
            if not ref_words or not msg_words:
                score = 0.0
            else:
                intersection = ref_words.intersection(msg_words)
                score = len(intersection) / (len(ref_words) + len(msg_words) - len(intersection))
            
            # Cache the score
            self._relevance_cache[cache_key] = score
            scores.append((message, score))
        
        # Sort by relevance score (highest first)
        sorted_messages = [m for m, s in sorted(scores, key=lambda x: x[1], reverse=True)]
        
        # Apply message limit if specified
        if message_limit:
            sorted_messages = sorted_messages[:message_limit]
        
        # Apply token limit
        return self._apply_token_limit(sorted_messages, token_limit)
    
    def _get_by_thread(self, 
                      conversation: ConversationMemory,
                      message_id: str,
                      token_limit: int,
                      message_limit: Optional[int] = None) -> List[AgentMessage]:
        """
        Get messages in a thread starting from the specified message.
        
        Args:
            conversation: The conversation memory to retrieve from
            message_id: ID of the message to start the thread from
            token_limit: Maximum number of tokens to retrieve
            message_limit: Maximum number of messages to retrieve
            
        Returns:
            List[AgentMessage]: Retrieved messages in thread order
        """
        # Get the message chain
        chain = conversation.get_message_chain(message_id)
        
        # Apply message limit if specified
        if message_limit:
            chain = chain[:message_limit]
        
        # Apply token limit
        return self._apply_token_limit(chain, token_limit)
    
    def _get_by_hybrid(self, 
                      messages: List[AgentMessage], 
                      reference_content: Dict[str, Any],
                      token_limit: int,
                      message_limit: Optional[int] = None) -> List[AgentMessage]:
        """
        Get messages using a hybrid of recency and relevance.
        
        Args:
            messages: List of messages to retrieve from
            reference_content: Reference content to compare against
            token_limit: Maximum number of tokens to retrieve
            message_limit: Maximum number of messages to retrieve
            
        Returns:
            List[AgentMessage]: Retrieved messages
        """
        # Convert reference content to string for comparison
        ref_str = str(reference_content)
        
        # Calculate hybrid scores (combination of recency and relevance)
        scores = []
        newest_time = max(m.timestamp for m in messages) if messages else time.time()
        oldest_time = min(m.timestamp for m in messages) if messages else time.time()
        time_range = max(1.0, newest_time - oldest_time)  # Avoid division by zero
        
        for message in messages:
            # Calculate recency score (normalized 0-1)
            recency_score = (message.timestamp - oldest_time) / time_range
            
            # Calculate relevance score
            message_str = str(message.content)
            ref_words = set(re.findall(r'\w+', ref_str.lower()))
            msg_words = set(re.findall(r'\w+', message_str.lower()))
            
            if not ref_words or not msg_words:
                relevance_score = 0.0
            else:
                intersection = ref_words.intersection(msg_words)
                relevance_score = len(intersection) / (len(ref_words) + len(msg_words) - len(intersection))
            
            # Combine scores (equal weight to recency and relevance)
            hybrid_score = 0.5 * recency_score + 0.5 * relevance_score
            scores.append((message, hybrid_score))
        
        # Sort by hybrid score (highest first)
        sorted_messages = [m for m, s in sorted(scores, key=lambda x: x[1], reverse=True)]
        
        # Apply message limit if specified
        if message_limit:
            sorted_messages = sorted_messages[:message_limit]
        
        # Apply token limit
        return self._apply_token_limit(sorted_messages, token_limit)
    
    def _get_by_round_robin(self, 
                           messages: List[AgentMessage], 
                           token_limit: int,
                           message_limit: Optional[int] = None) -> List[AgentMessage]:
        """
        Get messages using a round-robin approach (one from each agent).
        
        Args:
            messages: List of messages to retrieve from
            token_limit: Maximum number of tokens to retrieve
            message_limit: Maximum number of messages to retrieve
            
        Returns:
            List[AgentMessage]: Retrieved messages
        """
        # Group messages by sender
        sender_groups: Dict[str, List[AgentMessage]] = {}
        for message in messages:
            if message.sender not in sender_groups:
                sender_groups[message.sender] = []
            sender_groups[message.sender].append(message)
        
        # Sort each group by timestamp (newest first)
        for sender in sender_groups:
            sender_groups[sender].sort(key=lambda m: m.timestamp, reverse=True)
        
        # Interleave messages from different senders
        result = []
        index = 0
        while True:
            added = False
            for sender, sender_messages in sender_groups.items():
                if index < len(sender_messages):
                    result.append(sender_messages[index])
                    added = True
            
            if not added:
                break
            
            index += 1
            
            # Check message limit
            if message_limit and len(result) >= message_limit:
                result = result[:message_limit]
                break
        
        # Apply token limit
        return self._apply_token_limit(result, token_limit)
    
    def _get_by_type_priority(self, 
                             messages: List[AgentMessage], 
                             priority_types: List[MessageType],
                             token_limit: int,
                             message_limit: Optional[int] = None) -> List[AgentMessage]:
        """
        Get messages prioritizing specific message types.
        
        Args:
            messages: List of messages to retrieve from
            priority_types: List of message types in priority order
            token_limit: Maximum number of tokens to retrieve
            message_limit: Maximum number of messages to retrieve
            
        Returns:
            List[AgentMessage]: Retrieved messages
        """
        # Group messages by type
        type_groups: Dict[MessageType, List[AgentMessage]] = {}
        for message in messages:
            if message.message_type not in type_groups:
                type_groups[message.message_type] = []
            type_groups[message.message_type].append(message)
        
        # Sort each group by timestamp (newest first)
        for msg_type in type_groups:
            type_groups[msg_type].sort(key=lambda m: m.timestamp, reverse=True)
        
        # Build result prioritizing specified types
        result = []
        
        # First add messages of priority types in order
        for msg_type in priority_types:
            if msg_type in type_groups:
                result.extend(type_groups[msg_type])
                # Remove added messages to avoid duplication
                del type_groups[msg_type]
        
        # Then add remaining messages
        for msg_type, msgs in type_groups.items():
            result.extend(msgs)
        
        # Apply message limit if specified
        if message_limit:
            result = result[:message_limit]
        
        # Apply token limit
        return self._apply_token_limit(result, token_limit)
    
    def _apply_token_limit(self, messages: List[AgentMessage], token_limit: int) -> List[AgentMessage]:
        """
        Apply token limit to a list of messages.
        
        Args:
            messages: List of messages to apply limit to
            token_limit: Maximum number of tokens to include
            
        Returns:
            List[AgentMessage]: Messages within token limit
        """
        result = []
        token_count = 0
        
        for message in messages:
            message_tokens = TokenCounter.count_message_tokens(message)
            
            # Skip if this single message exceeds the token limit
            if not result and message_tokens > token_limit:
                logger.warning(f"Message {message.message_id} exceeds token limit ({message_tokens} > {token_limit})")
                continue
            
            # Add message if it fits within the limit
            if token_count + message_tokens <= token_limit:
                result.append(message)
                token_count += message_tokens
            else:
                break
        
        return result
    
    def summarize_conversation(self, conversation: ConversationMemory, max_tokens: int = 200) -> str:
        """
        Generate a concise summary of the conversation.
        
        Args:
            conversation: The conversation to summarize
            max_tokens: Maximum number of tokens for the summary
            
        Returns:
            str: Summary of the conversation
        """
        # This is a placeholder implementation
        # In production, use a proper summarization approach with an LLM
        
        participants = set(m.sender for m in conversation.messages)
        msg_count = len(conversation.messages)
        types = {}
        for msg in conversation.messages:
            msg_type = msg.message_type.value
            types[msg_type] = types.get(msg_type, 0) + 1
        
        # Get most recent messages (up to 3)
        recent = sorted(conversation.messages, key=lambda m: m.timestamp, reverse=True)[:3]
        recent_summary = []
        for msg in recent:
            content_str = str(msg.content)
            if len(content_str) > 50:
                content_str = content_str[:47] + "..."
            recent_summary.append(f"{msg.sender}: {content_str}")
        
        summary = (
            f"Conversation with {len(participants)} participants ({', '.join(participants)}). "
            f"Contains {msg_count} messages: {', '.join(f'{count} {type}' for type, count in types.items())}. "
            f"Recent messages: {'; '.join(recent_summary)}"
        )
        
        # Ensure the summary is within the token limit
        summary_tokens = TokenCounter.count_tokens(summary)
        if summary_tokens > max_tokens:
            # Truncate the summary
            ratio = max_tokens / summary_tokens
            truncate_length = int(len(summary) * ratio)
            summary = summary[:truncate_length] + "..."
        
        return summary
    
    def prune_conversation(self, conversation: ConversationMemory, max_tokens: int = 8000) -> ConversationMemory:
        """
        Create a pruned copy of a conversation memory within token limits.
        
        Args:
            conversation: The conversation to prune
            max_tokens: Maximum number of tokens for the pruned conversation
            
        Returns:
            ConversationMemory: Pruned conversation memory
        """
        # Get most important messages within token limit
        # We use a hybrid strategy to preserve both recent and relevant messages
        messages = self._get_by_recency(conversation.messages, max_tokens)
        
        # Create a new conversation with the pruned messages
        pruned = ConversationMemory(
            conversation_id=conversation.conversation_id,
            metadata=conversation.metadata.copy()
        )
        
        # Add a summary of pruned messages
        if len(messages) < len(conversation.messages):
            pruned_count = len(conversation.messages) - len(messages)
            pruned.metadata["pruned_message_count"] = pruned_count
            pruned.metadata["pruned_summary"] = f"Pruned {pruned_count} older messages to stay within token limit."
        
        # Add the selected messages
        for message in messages:
            pruned.add_message(message)
        
        return pruned
    
    def get_token_count(self, conversation: ConversationMemory) -> int:
        """
        Get the total token count for a conversation.
        
        Args:
            conversation: The conversation to count tokens for
            
        Returns:
            int: Total token count
        """
        return sum(TokenCounter.count_message_tokens(msg) for msg in conversation.messages)
