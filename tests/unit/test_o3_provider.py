"""
Unit tests for the O3Provider class.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import json

from triangulum_lx.providers.o3_provider import O3Provider, AgentRole, ModelConfig
from triangulum_lx.providers.base import LLMResponse, Tool, ToolCall

class TestO3Provider(unittest.TestCase):
    """Test case for the O3Provider class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use a mock API key for testing
        self.api_key = "test_api_key"
        # Create provider instance
        self.provider = O3Provider(api_key=self.api_key)
        
    def test_initialization(self):
        """Test that the provider initializes correctly."""
        self.assertEqual(self.provider.api_key, self.api_key)
        self.assertEqual(self.provider.model, "o3")
        self.assertEqual(self.provider.role, AgentRole.DEFAULT)
        
        # Test initialization with different role
        analyst_provider = O3Provider(api_key=self.api_key, role=AgentRole.ANALYST)
        self.assertEqual(analyst_provider.role, AgentRole.ANALYST)
        
        # Test initialization with string role
        detective_provider = O3Provider(api_key=self.api_key, role="detective")
        self.assertEqual(detective_provider.role, AgentRole.DETECTIVE)
        
    def test_model_configs(self):
        """Test that model configurations are set up correctly for different roles."""
        # Test each role has a configuration
        for role in AgentRole:
            self.assertIn(role, self.provider.MODEL_CONFIGS)
            config = self.provider.MODEL_CONFIGS[role]
            self.assertIsInstance(config, ModelConfig)
            
        # Test specific role configurations
        analyst_config = self.provider.MODEL_CONFIGS[AgentRole.ANALYST]
        self.assertLess(analyst_config.temperature, 0.5)  # Analysts need precision
        
        strategist_config = self.provider.MODEL_CONFIGS[AgentRole.STRATEGIST]
        self.assertGreater(strategist_config.temperature, 0.5)  # Strategists need creativity
        
    def test_get_model_config(self):
        """Test getting configuration for a specific role."""
        # Test getting config for the default role
        config = self.provider.get_model_config()
        self.assertEqual(config, self.provider.MODEL_CONFIGS[AgentRole.DEFAULT])
        
        # Test getting config for a specific role
        config = self.provider.get_model_config(AgentRole.ANALYST)
        self.assertEqual(config, self.provider.MODEL_CONFIGS[AgentRole.ANALYST])
        
    def test_prepare_system_prompt(self):
        """Test system prompt preparation."""
        # Test default prompt
        prompt = self.provider.prepare_system_prompt()
        self.assertIn("AI assistant", prompt)
        
        # Test role-specific prompt
        prompt = self.provider.prepare_system_prompt(AgentRole.IMPLEMENTER)
        self.assertIn("expert software engineer", prompt)
        
        # Test with custom context
        prompt = self.provider.prepare_system_prompt(custom_context="Test specific context.")
        self.assertIn("Test specific context", prompt)
        
    def test_optimize_messages(self):
        """Test message optimization for token limits."""
        # Create a list of test messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you for asking!"},
            {"role": "user", "content": "Can you help me with a Python question?"},
            {"role": "assistant", "content": "Of course! I'd be happy to help with Python."},
            {"role": "user", "content": "How do I read a file in Python?"}
        ]
        
        # Test with high token limit (should keep all messages)
        high_limit = 10000
        optimized = self.provider.optimize_messages(messages.copy(), high_limit)
        self.assertEqual(len(optimized), len(messages))
        
        # Test with low token limit (should reduce messages)
        low_limit = 100
        optimized = self.provider.optimize_messages(messages.copy(), low_limit)
        self.assertLess(len(optimized), len(messages))
        
        # Verify essential messages are kept
        roles = [msg["role"] for msg in optimized]
        self.assertIn("system", roles)  # System message should always be kept
        self.assertIn("user", roles)    # At least one user message should be kept
        
    def test_context_storage(self):
        """Test context storage and retrieval."""
        # Save context
        test_context = {"key": "value", "nested": {"data": 123}}
        self.provider.save_context("test_key", test_context)
        
        # Retrieve context
        retrieved = self.provider.get_context("test_key")
        self.assertEqual(retrieved, test_context)
        
        # Test non-existent key
        self.assertIsNone(self.provider.get_context("nonexistent"))
        
    @patch('triangulum_lx.providers.o3_provider.OpenAI')
    def test_is_available(self, mock_openai):
        """Test availability check with mocked OpenAI client."""
        # Set up mock for successful availability
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        self.provider.client = mock_client
        
        # Test successful availability
        mock_client.models.list.return_value = ["model1", "model2"]
        self.assertTrue(self.provider.is_available())
        
        # Test failed availability
        mock_client.models.list.side_effect = Exception("API Error")
        self.assertFalse(self.provider.is_available())
        
    @patch('triangulum_lx.providers.o3_provider.O3Provider._api_request_with_backoff')
    def test_generate(self, mock_api_request):
        """Test generate method with mocked API response."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a test response."
        mock_response.model = "o3"
        mock_response.usage.total_tokens = 50
        mock_api_request.return_value = mock_response
        
        # Test generation with string prompt
        response = self.provider.generate("Test prompt")
        self.assertEqual(response.content, "This is a test response.")
        self.assertEqual(response.model, "o3")
        self.assertEqual(response.tokens_used, 50)
        
        # Test generation with message list
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Test prompt"}
        ]
        response = self.provider.generate(messages)
        self.assertEqual(response.content, "This is a test response.")
        
        # Test with different role
        response = self.provider.generate("Test prompt", role=AgentRole.ANALYST)
        self.assertEqual(response.content, "This is a test response.")
        
        # Verify the mock was called appropriately
        self.assertTrue(mock_api_request.called)
        self.assertEqual(mock_api_request.call_count, 3)  # Called for all 3 test cases
        
    @patch('triangulum_lx.providers.o3_provider.O3Provider._api_request_with_backoff')
    def test_generate_with_tools_enhanced(self, mock_api_request):
        """Test tool-enabled generation with mocked API response."""
        # Set up mock response for content generation
        mock_content_response = MagicMock()
        mock_content_response.choices = [MagicMock()]
        mock_content_response.choices[0].message.content = "This is a content response."
        mock_content_response.choices[0].message.tool_calls = None
        mock_content_response.model = "o3"
        mock_content_response.usage.total_tokens = 30
        
        # Set up mock response for tool call
        mock_tool_response = MagicMock()
        mock_tool_response.choices = [MagicMock()]
        mock_tool_response.choices[0].message.content = None
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call123"
        mock_tool_call.function.name = "test_function"
        mock_tool_call.function.arguments = '{"arg1": "value1", "arg2": 42}'
        mock_tool_response.choices[0].message.tool_calls = [mock_tool_call]
        mock_tool_response.model = "o3"
        mock_tool_response.usage.total_tokens = 40
        
        # Create test tools
        tools = [
            Tool(name="test_function", description="A test function", parameters={"type": "object"})
        ]
        
        # Test content generation (no tool calls)
        mock_api_request.return_value = mock_content_response
        
        response = self.provider.generate_with_tools_enhanced("Test prompt", tools)
        self.assertIsInstance(response, LLMResponse)
        self.assertEqual(response.content, "This is a content response.")
        
        # Test tool call generation
        mock_api_request.return_value = mock_tool_response
        response = self.provider.generate_with_tools_enhanced("Test prompt", tools)
        self.assertIsInstance(response, list)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0].tool_name, "test_function")
        
        # Test error handling
        mock_api_request.side_effect = Exception("Test error")
        response = self.provider.generate_with_tools_enhanced("Test prompt", tools)
        self.assertIsInstance(response, LLMResponse)
        self.assertIn("Error", response.content)
        
    def test_get_statistics(self):
        """Test statistics collection."""
        # Initial statistics should all be zero
        stats = self.provider.get_statistics()
        self.assertEqual(stats["requests"], 0)
        self.assertEqual(stats["tokens_used"], 0)
        self.assertEqual(stats["errors"], 0)
        
        # Modify stats and verify they're updated
        self.provider.stats["requests"] = 10
        self.provider.stats["tokens_used"] = 500
        stats = self.provider.get_statistics()
        self.assertEqual(stats["requests"], 10)
        self.assertEqual(stats["tokens_used"], 500)
        
        # Verify stats returned is a copy
        stats["requests"] = 999
        self.assertEqual(self.provider.stats["requests"], 10)  # Original unchanged

if __name__ == '__main__':
    unittest.main()
