"""
O3Provider API Test

This script tests the O3Provider with actual API calls to demonstrate its capabilities.
"""

import os
import sys
import logging
import time
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to import Triangulum modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the O3Provider
from triangulum_lx.providers.o3_provider import O3Provider, AgentRole
from triangulum_lx.providers.base import Tool

# Use the API key provided
API_KEY = "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"

def test_basic_generation():
    """Test basic text generation with different agent roles."""
    logger.info("=== TESTING BASIC TEXT GENERATION ===")
    
    # Create a provider with the default settings
    # O3 model only supports default temperature
    provider = O3Provider(api_key=API_KEY, role=AgentRole.DEFAULT)
    
    # Test prompt
    prompt = "Suggest three approaches to optimize a large Python codebase."
    
    # Generate response
    logger.info(f"\n=== Testing Basic Generation ===")
    start_time = time.time()
    response = provider.generate(prompt)
    end_time = time.time()
    
    logger.info(f"Generation time: {end_time - start_time:.2f} seconds")
    logger.info(f"Tokens used: {response.tokens_used}")
    logger.info(f"Response snippet: {response.content[:150]}...\n")

def test_context_management():
    """Test context management capabilities."""
    logger.info("\n=== TESTING CONTEXT MANAGEMENT ===")
    
    provider = O3Provider(api_key=API_KEY, role=AgentRole.DEFAULT)
    
    # Create a conversation with multiple turns
    conversation = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What are microservices?"},
        {"role": "assistant", "content": "Microservices are an architectural style that structures an application as a collection of small, loosely coupled services. Each service is focused on a specific business capability and can be developed, deployed, and scaled independently."},
        {"role": "user", "content": "What are their advantages?"}
    ]
    
    # Generate response with conversation context
    logger.info("Generating response with conversation context...")
    response = provider.generate(conversation)
    logger.info(f"Tokens used: {response.tokens_used}")
    logger.info(f"Response snippet: {response.content[:150]}...\n")
    
    # Test context storage
    provider.save_context("microservices_convo", conversation)
    
    # Create a new message in a different conversation
    logger.info("Retrieving context and continuing conversation...")
    saved_convo = provider.get_context("microservices_convo")
    
    # Add a new message to the saved conversation
    saved_convo.append({"role": "assistant", "content": response.content})
    saved_convo.append({"role": "user", "content": "What are some disadvantages?"})
    
    # Generate a response with the saved and updated context
    response = provider.generate(saved_convo)
    logger.info(f"Tokens used: {response.tokens_used}")
    logger.info(f"Response snippet: {response.content[:150]}...\n")

def test_tool_usage():
    """Test tool-based generation."""
    logger.info("\n=== TESTING TOOL USAGE ===")
    
    provider = O3Provider(api_key=API_KEY, role=AgentRole.DEFAULT)
    
    # Define some tools
    weather_tool = Tool(
        name="get_weather",
        description="Get the current weather in a location",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "The unit of temperature to use"
                }
            },
            "required": ["location"]
        }
    )
    
    search_tool = Tool(
        name="search",
        description="Search for information on the internet",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    )
    
    # List of tools
    tools = [weather_tool, search_tool]
    
    # Test prompt that should trigger tool use
    prompt = "What's the weather like in New York? I'm planning a trip there."
    
    logger.info(f"Generating response with tools available...")
    response = provider.generate_with_tools_enhanced(prompt, tools)
    
    if isinstance(response, list):
        logger.info(f"Tool call detected! Tool: {response[0].tool_name}")
        logger.info(f"Arguments: {response[0].arguments}")
    else:
        logger.info(f"Response without tool use: {response.content[:150]}...")

if __name__ == "__main__":
    logger.info("Starting O3Provider API Test")
    
    try:
        test_basic_generation()
        test_context_management()
        test_tool_usage()
        logger.info("All tests completed successfully!")
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
