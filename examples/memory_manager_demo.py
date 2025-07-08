"""
Memory Manager Demo

This script demonstrates the token-efficient context retrieval capabilities of the
MemoryManager class, showing various strategies for retrieving relevant context
from conversation history while optimizing token usage.
"""

import logging
import time
import json
from typing import List

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the path for importing
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from triangulum_lx.agents.message import AgentMessage, MessageType, ConversationMemory
from triangulum_lx.agents.memory_manager import MemoryManager, RetrievalStrategy, TokenCounter


def create_sample_conversation() -> ConversationMemory:
    """Create a sample conversation with various message types for demonstration."""
    conversation = ConversationMemory(conversation_id="demo_conversation")
    
    # Add a series of messages to simulate a debugging conversation
    
    # Message 1: Initial task request
    msg1 = AgentMessage(
        message_type=MessageType.TASK_REQUEST,
        content={"task": "Analyze the file.py module for bugs"},
        sender="coordinator_agent",
        message_id="msg1",
        conversation_id="demo_conversation",
        timestamp=time.time() - 600  # 10 minutes ago
    )
    conversation.add_message(msg1)
    
    # Message 2: Code analysis response
    msg2 = AgentMessage(
        message_type=MessageType.CODE_ANALYSIS,
        content={"analysis": "Found potential type error in file.py"},
        sender="bug_detector_agent",
        receiver="coordinator_agent",
        parent_id="msg1",
        conversation_id="demo_conversation",
        message_id="msg2",
        timestamp=time.time() - 540,  # 9 minutes ago
        problem_context={
            "file_path": "file.py",
            "line_number": 42,
            "code_snippet": "result = 'Total: ' + count"
        },
        analysis_results={
            "error_type": "TypeError",
            "error_cause": "String concatenation with integer",
            "severity": "medium"
        }
    )
    conversation.add_message(msg2)
    
    # Message 3: Query for more information
    msg3 = AgentMessage(
        message_type=MessageType.QUERY,
        content={"query": "What data type is 'count' variable?"},
        sender="coordinator_agent",
        receiver="bug_detector_agent",
        parent_id="msg2",
        conversation_id="demo_conversation",
        message_id="msg3",
        timestamp=time.time() - 480,  # 8 minutes ago
    )
    conversation.add_message(msg3)
    
    # Message 4: Query response
    msg4 = AgentMessage(
        message_type=MessageType.QUERY_RESPONSE,
        content={"response": "'count' is an integer returned from len(items)"},
        sender="bug_detector_agent",
        receiver="coordinator_agent",
        parent_id="msg3",
        conversation_id="demo_conversation",
        message_id="msg4",
        timestamp=time.time() - 420,  # 7 minutes ago
        problem_context={
            "file_path": "file.py",
            "line_number": 40,
            "code_snippet": "count = len(items)"
        }
    )
    conversation.add_message(msg4)
    
    # Message 5: Problem analysis
    msg5 = AgentMessage(
        message_type=MessageType.PROBLEM_ANALYSIS,
        content={"analysis": "The issue is a type mismatch: trying to concatenate string with integer"},
        sender="analyzer_agent",
        receiver="coordinator_agent",
        parent_id="msg4",
        conversation_id="demo_conversation",
        message_id="msg5",
        timestamp=time.time() - 360,  # 6 minutes ago
        analysis_results={
            "error_type": "TypeError",
            "error_cause": "Type mismatch in string concatenation",
            "impact": "Runtime error when function is called"
        }
    )
    conversation.add_message(msg5)
    
    # Message 6: Repair suggestion
    msg6 = AgentMessage(
        message_type=MessageType.REPAIR_SUGGESTION,
        content={"suggestion": "Convert the integer to string before concatenation"},
        sender="repair_agent",
        receiver="coordinator_agent",
        parent_id="msg5",
        conversation_id="demo_conversation",
        message_id="msg6",
        timestamp=time.time() - 300,  # 5 minutes ago
        suggested_actions=[{
            "action_type": "code_change",
            "file": "file.py",
            "line": 42,
            "original": "result = 'Total: ' + count",
            "replacement": "result = 'Total: ' + str(count)",
            "description": "Convert integer to string before concatenation",
            "confidence": 0.95
        }]
    )
    conversation.add_message(msg6)
    
    # Message 7: Status update - applying fix
    msg7 = AgentMessage(
        message_type=MessageType.STATUS,
        content={"status": "Applying suggested fix"},
        sender="coordinator_agent",
        conversation_id="demo_conversation",
        message_id="msg7",
        timestamp=time.time() - 240  # 4 minutes ago
    )
    conversation.add_message(msg7)
    
    # Message 8: Verification request
    msg8 = AgentMessage(
        message_type=MessageType.TASK_REQUEST,
        content={"task": "Verify the fix works correctly"},
        sender="coordinator_agent",
        receiver="verification_agent",
        conversation_id="demo_conversation",
        message_id="msg8",
        timestamp=time.time() - 180  # 3 minutes ago
    )
    conversation.add_message(msg8)
    
    # Message 9: Verification result
    msg9 = AgentMessage(
        message_type=MessageType.VERIFICATION_RESULT,
        content={"verification": "Fix resolves the TypeError. All tests passing."},
        sender="verification_agent",
        receiver="coordinator_agent",
        parent_id="msg8",
        conversation_id="demo_conversation",
        message_id="msg9",
        timestamp=time.time() - 120,  # 2 minutes ago
        analysis_results={
            "tests_run": 12,
            "tests_passed": 12,
            "runtime_errors": 0
        }
    )
    conversation.add_message(msg9)
    
    # Message 10: Final status
    msg10 = AgentMessage(
        message_type=MessageType.STATUS,
        content={"status": "Bug fixed successfully"},
        sender="coordinator_agent",
        conversation_id="demo_conversation",
        message_id="msg10",
        timestamp=time.time() - 60  # 1 minute ago
    )
    conversation.add_message(msg10)
    
    logger.info(f"Created sample conversation with {len(conversation.messages)} messages")
    return conversation


def demonstrate_retrieval_strategies(memory_manager: MemoryManager, conversation: ConversationMemory):
    """Demonstrate different retrieval strategies."""
    logger.info("\n=== DEMONSTRATING RETRIEVAL STRATEGIES ===")
    
    # 1. Recency strategy (default)
    logger.info("\n--- Recency Strategy (most recent first) ---")
    recency_messages = memory_manager.get_context(
        conversation,
        strategy=RetrievalStrategy.RECENCY,
        message_limit=3  # Get only 3 most recent messages
    )
    print_messages(recency_messages, "Most recent messages")
    
    # 2. Thread strategy (follow conversation thread)
    logger.info("\n--- Thread Strategy (following a specific thread) ---")
    thread_messages = memory_manager.get_context(
        conversation,
        strategy=RetrievalStrategy.THREAD,
        reference_content={"message_id": "msg3"}  # Start from the query message
    )
    print_messages(thread_messages, "Thread starting from query about 'count' variable")
    
    # 3. Relevance strategy (based on content similarity)
    logger.info("\n--- Relevance Strategy (most relevant to reference content) ---")
    relevance_messages = memory_manager.get_context(
        conversation,
        strategy=RetrievalStrategy.RELEVANCE,
        reference_content={"query": "type error string concatenation"},
        message_limit=3
    )
    print_messages(relevance_messages, "Messages relevant to 'type error string concatenation'")
    
    # 4. Filter by message type
    logger.info("\n--- Type Filtering (only specific message types) ---")
    filtered_messages = memory_manager.get_context(
        conversation,
        strategy=RetrievalStrategy.RECENCY,
        filter_types=[MessageType.REPAIR_SUGGESTION, MessageType.VERIFICATION_RESULT]
    )
    print_messages(filtered_messages, "Only repair suggestions and verification results")
    
    # 5. Round-robin strategy (one from each agent)
    logger.info("\n--- Round-Robin Strategy (one from each agent) ---")
    round_robin_messages = memory_manager.get_context(
        conversation,
        strategy=RetrievalStrategy.ROUND_ROBIN
    )
    print_messages(round_robin_messages, "One message from each agent")
    
    # 6. Type prioritized strategy
    logger.info("\n--- Type Prioritized Strategy (prioritize specific message types) ---")
    priority_types = [
        MessageType.REPAIR_SUGGESTION,  # First priority
        MessageType.PROBLEM_ANALYSIS,   # Second priority
        MessageType.CODE_ANALYSIS       # Third priority
    ]
    prioritized_messages = memory_manager.get_context(
        conversation,
        strategy=RetrievalStrategy.TYPE_PRIORITIZED,
        reference_content={"priority_types": priority_types}
    )
    print_messages(prioritized_messages, "Prioritized by message type")


def demonstrate_token_management(memory_manager: MemoryManager, conversation: ConversationMemory):
    """Demonstrate token management capabilities."""
    logger.info("\n=== DEMONSTRATING TOKEN MANAGEMENT ===")
    
    # Get total token count
    total_tokens = memory_manager.get_token_count(conversation)
    logger.info(f"Total conversation token count: {total_tokens}")
    
    # Limit tokens for context retrieval
    logger.info("\n--- Token-Limited Context Retrieval ---")
    # For demonstration, set a token limit that will include ~half the messages
    estimated_tokens_per_message = total_tokens // len(conversation.messages)
    token_limit = estimated_tokens_per_message * (len(conversation.messages) // 2)
    
    logger.info(f"Retrieving context with token limit: {token_limit}")
    limited_messages = memory_manager.get_context(
        conversation,
        strategy=RetrievalStrategy.RECENCY,
        token_limit=token_limit
    )
    logger.info(f"Retrieved {len(limited_messages)} messages within token limit")
    
    # Demonstrate conversation pruning
    logger.info("\n--- Conversation Pruning ---")
    pruned_conversation = memory_manager.prune_conversation(
        conversation,
        max_tokens=token_limit
    )
    logger.info(f"Pruned conversation from {len(conversation.messages)} to {len(pruned_conversation.messages)} messages")
    if "pruned_summary" in pruned_conversation.metadata:
        logger.info(f"Pruning summary: {pruned_conversation.metadata['pruned_summary']}")


def demonstrate_summarization(memory_manager: MemoryManager, conversation: ConversationMemory):
    """Demonstrate conversation summarization."""
    logger.info("\n=== DEMONSTRATING CONVERSATION SUMMARIZATION ===")
    
    # Generate a summary of the conversation
    summary = memory_manager.summarize_conversation(conversation)
    logger.info(f"Conversation summary:\n{summary}")


def print_messages(messages: List[AgentMessage], description: str):
    """Print messages in a readable format."""
    logger.info(f"{description} ({len(messages)} messages):")
    for i, message in enumerate(messages):
        content_str = str(message.content)
        if len(content_str) > 70:
            content_str = content_str[:67] + "..."
        logger.info(f"{i+1}. [{message.message_type.value}] {message.sender}: {content_str}")


def main():
    """Main function to run the demo."""
    logger.info("Starting Memory Manager Demo")
    
    # Create a memory manager with default settings
    memory_manager = MemoryManager(max_tokens=4000)
    logger.info(f"Created memory manager with {memory_manager.max_tokens} max tokens")
    
    # Create a sample conversation
    conversation = create_sample_conversation()
    
    # Demonstrate various retrieval strategies
    demonstrate_retrieval_strategies(memory_manager, conversation)
    
    # Demonstrate token management
    demonstrate_token_management(memory_manager, conversation)
    
    # Demonstrate summarization
    demonstrate_summarization(memory_manager, conversation)
    
    logger.info("\nMemory Manager Demo completed")


if __name__ == "__main__":
    main()
