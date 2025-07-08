"""
O3Provider Demonstration

This script demonstrates the enhanced features of the O3Provider:
- API Abstraction Layer with rate limiting and error handling
- Context Management for token optimization
- Model Configuration Profiles for different agent roles
"""

import os
import time
import logging
import argparse
from typing import Dict, List, Any

from triangulum_lx.providers.o3_provider import O3Provider, AgentRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def demonstrate_role_based_configuration():
    """Demonstrate different agent role configurations."""
    logger.info("\n=== DEMONSTRATING ROLE-BASED CONFIGURATIONS ===")
    
    # Create providers with different roles
    providers = {
        "analyst": O3Provider(role=AgentRole.ANALYST),
        "detective": O3Provider(role=AgentRole.DETECTIVE),
        "strategist": O3Provider(role=AgentRole.STRATEGIST),
        "implementer": O3Provider(role=AgentRole.IMPLEMENTER),
        "verifier": O3Provider(role=AgentRole.VERIFIER),
        "default": O3Provider(role=AgentRole.DEFAULT),
    }
    
    # Print configuration details for each role
    for role_name, provider in providers.items():
        config = provider.get_model_config()
        logger.info(f"\nRole: {role_name.upper()}")
        logger.info(f"  Temperature: {config.temperature}")
        logger.info(f"  Top-p: {config.top_p}")
        logger.info(f"  Max tokens: {config.max_tokens}")
        logger.info(f"  System prompt: {provider.prepare_system_prompt()[:60]}...")
        
    # Return the provider map for later use
    return providers

def demonstrate_context_management(provider: O3Provider):
    """Demonstrate context management capabilities."""
    logger.info("\n=== DEMONSTRATING CONTEXT MANAGEMENT ===")
    
    # Original message list (simulates a long conversation)
    long_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "I'm working on a project and need help with code."},
        {"role": "assistant", "content": "I'd be happy to help with your coding project. What language are you working with?"},
        {"role": "user", "content": "I'm using Python for a data analysis project."},
        {"role": "assistant", "content": "Great choice! Python is excellent for data analysis. Are you using libraries like pandas or numpy?"},
        {"role": "user", "content": "Yes, I'm using pandas but having trouble with groupby operations."},
        {"role": "assistant", "content": "I can help with pandas groupby operations. Could you share a specific example of what you're trying to do?"},
        {"role": "user", "content": "I'm trying to group data by date and calculate statistics."},
        {"role": "assistant", "content": "To group by date and calculate statistics in pandas, you can use code like: df.groupby(df['date']).agg({'value': ['mean', 'sum', 'count']})"},
        {"role": "user", "content": "How would I filter the groups after aggregation?"}
    ]
    
    # Show the original message count
    logger.info(f"Original conversation has {len(long_messages)} messages")
    
    # Optimize messages for different token limits
    for token_limit in [2000, 1000, 500]:
        optimized = provider.optimize_messages(long_messages.copy(), token_limit)
        logger.info(f"Optimized for {token_limit} tokens: {len(optimized)} messages remain")
        
        # Show the structure of the optimized messages
        roles = [msg["role"] for msg in optimized]
        logger.info(f"Message roles after optimization: {roles}")
        
    # Demonstrate context storage
    logger.info("\nStoring and retrieving context:")
    
    # Save conversation context
    provider.save_context("conversation_1", {
        "messages": long_messages,
        "topic": "pandas groupby",
        "language": "python",
        "last_update": time.time()
    })
    
    # Retrieve context
    context = provider.get_context("conversation_1")
    logger.info(f"Retrieved context topic: {context['topic']}")
    logger.info(f"Message count in stored context: {len(context['messages'])}")

def demonstrate_api_features(provider: O3Provider):
    """Demonstrate API abstraction features."""
    logger.info("\n=== DEMONSTRATING API ABSTRACTION FEATURES ===")
    
    # Only run API calls if we have an API key
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("No OpenAI API key found. Skipping API call demonstrations.")
        logger.info("To run with API calls, set the OPENAI_API_KEY environment variable.")
        return
    
    # Send a simple request
    logger.info("\nSending test request...")
    response = provider.generate(
        "What is the Triangulum project?",
        temperature=0.2,
        max_tokens=100
    )
    
    logger.info(f"Response received: {response.content[:100]}...")
    logger.info(f"Tokens used: {response.tokens_used}")
    logger.info(f"Latency: {response.latency:.2f}s")
    
    # Show statistics
    stats = provider.get_statistics()
    logger.info(f"\nProvider statistics: {stats}")
    
    # Demonstrate error handling with an invalid request
    logger.info("\nDemonstrating error handling with invalid parameters...")
    try:
        # This will cause an error because temperature is out of range
        response = provider.generate(
            "This will cause an error",
            temperature=2.5  # Valid range is 0-2
        )
        logger.info(f"Response: {response.content}")
    except Exception as e:
        logger.info(f"Caught error as expected: {str(e)}")

def main():
    """Run the O3Provider demonstration."""
    parser = argparse.ArgumentParser(description="Demonstrate O3Provider features")
    parser.add_argument("--api-key", help="OpenAI API key (optional, will use env var if not provided)")
    parser.add_argument("--skip-api-calls", action="store_true", help="Skip demonstrations that make actual API calls")
    args = parser.parse_args()
    
    # Set API key if provided
    if args.api_key:
        os.environ["OPENAI_API_KEY"] = args.api_key
    
    try:
        logger.info("Starting O3Provider Demonstration")
        
        # Create a default provider for demonstrations
        default_provider = O3Provider(
            model="o3",
            additional_context="This is a demonstration of the enhanced o3 provider."
        )
        
        # Run demonstrations
        providers = demonstrate_role_based_configuration()
        demonstrate_context_management(default_provider)
        
        # Only run API demonstrations if not skipped
        if not args.skip_api_calls:
            demonstrate_api_features(default_provider)
        
        logger.info("\nO3Provider Demonstration completed successfully")
        
    except Exception as e:
        logger.exception(f"Error in demonstration: {e}")
    
if __name__ == "__main__":
    main()
