"""
Unit tests for the message schema validator.

This module contains tests for the MessageSchemaValidator class, verifying that
the JSON schema validation for agent messages works as expected.
"""

import unittest
import json
import os
import time
import jsonschema
from unittest.mock import patch, mock_open, MagicMock

from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.message_schema_validator import MessageSchemaValidator, Draft7Validator
from triangulum_lx.core.exceptions import TriangulumValidationError


class TestMessageSchemaValidator(unittest.TestCase):
    """Test case for the MessageSchemaValidator class."""
    
    def setUp(self):
        """Set up a message schema validator for testing."""
        self.validator = MessageSchemaValidator()
    
    def test_load_schema(self):
        """Test loading the schema from the JSON file."""
        # Verify the schema was loaded
        self.assertIsNotNone(self.validator._schema)
        self.assertIsInstance(self.validator._schema, dict)
        
        # Verify key schema components are present
        self.assertIn("type", self.validator._schema)
        self.assertIn("properties", self.validator._schema)
        self.assertIn("required", self.validator._schema)
    
    def test_validate_valid_message(self):
        """Test validating a valid message."""
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Analyze code"},
            sender="test_agent"
        )
        
        is_valid, error = self.validator.validate_message(message)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_validate_message_with_enhanced_fields(self):
        """Test validating a message with enhanced fields."""
        message = AgentMessage(
            message_type=MessageType.CODE_ANALYSIS,
            content={"analysis": "Code has a type error"},
            sender="analyzer_agent",
            problem_context={"file_path": "example.py"},
            analysis_results={"error_type": "TypeError"},
            suggested_actions=[{"action_type": "code_change", "description": "Convert to string"}]
        )
        
        is_valid, error = self.validator.validate_message(message)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_validate_invalid_message_type(self):
        """Test validating a message with an invalid message type."""
        # Create an invalid message by directly manipulating the dictionary
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Analyze code"},
            sender="test_agent"
        )
        
        # Set an invalid message type
        message_dict = message.to_dict()
        message_dict["message_type"] = "invalid_type"
        
        # Mock the message.to_dict() method to return our modified dictionary
        with patch.object(AgentMessage, 'to_dict', return_value=message_dict):
            is_valid, error = self.validator.validate_message(message)
            self.assertFalse(is_valid)
            self.assertIsNotNone(error)
            # With our enhanced validator, the error message format has changed
            self.assertIn("Message validation failed", error)
    
    def test_validate_missing_required_content(self):
        """Test validating a message with missing required content."""
        # Create messages with missing required content fields
        task_request = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={},  # Missing 'task' field
            sender="test_agent"
        )
        
        # This should raise an error in _validate_message_content
        is_valid, error = self.validator.validate_message(task_request)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        
        # Get detailed validation to check specific errors
        detailed_result = self.validator.validate_message_detailed(task_request)
        self.assertFalse(detailed_result["valid"])
        
        # Check that the missing task field is reported in the errors
        has_task_error = False
        for error_item in detailed_result["errors"]:
            if error_item.get("type") == "content_validation" and error_item.get("field") == "task":
                has_task_error = True
                break
        self.assertTrue(has_task_error, "Missing task field error not found")
        
        # Test with TASK_RESULT missing 'result' field
        task_result = AgentMessage(
            message_type=MessageType.TASK_RESULT,
            content={},  # Missing 'result' field
            sender="test_agent"
        )
        
        detailed_result = self.validator.validate_message_detailed(task_result)
        self.assertFalse(detailed_result["valid"])
        
        # Check that the missing result field is reported in the errors
        has_result_error = False
        for error_item in detailed_result["errors"]:
            if error_item.get("type") == "content_validation" and error_item.get("field") == "result":
                has_result_error = True
                break
        self.assertTrue(has_result_error, "Missing result field error not found")
    
    def test_generate_message_template(self):
        """Test generating message templates."""
        # Test templates for different message types
        task_request_template = self.validator.generate_message_template(MessageType.TASK_REQUEST)
        self.assertEqual(task_request_template["message_type"], "task_request")
        self.assertIn("task", task_request_template["content"])
        
        code_analysis_template = self.validator.generate_message_template(MessageType.CODE_ANALYSIS)
        self.assertEqual(code_analysis_template["message_type"], "code_analysis")
        self.assertIn("analysis", code_analysis_template["content"])
        self.assertIn("error_type", code_analysis_template["analysis_results"])
        
        repair_suggestion_template = self.validator.generate_message_template(MessageType.REPAIR_SUGGESTION)
        self.assertEqual(repair_suggestion_template["message_type"], "repair_suggestion")
        self.assertEqual(len(repair_suggestion_template["suggested_actions"]), 1)
        self.assertIn("action_type", repair_suggestion_template["suggested_actions"][0])
        
        # Test templates for all other message types
        problem_analysis_template = self.validator.generate_message_template(MessageType.PROBLEM_ANALYSIS)
        self.assertEqual(problem_analysis_template["message_type"], "problem_analysis")
        self.assertIn("problem", problem_analysis_template["content"])
        self.assertIn("analysis", problem_analysis_template["content"])
        
        relationship_analysis_template = self.validator.generate_message_template(MessageType.RELATIONSHIP_ANALYSIS)
        self.assertEqual(relationship_analysis_template["message_type"], "relationship_analysis")
        self.assertIn("relationships", relationship_analysis_template["content"])
        
        verification_result_template = self.validator.generate_message_template(MessageType.VERIFICATION_RESULT)
        self.assertEqual(verification_result_template["message_type"], "verification_result")
        self.assertIn("verified", verification_result_template["content"])
        self.assertIn("result", verification_result_template["content"])
        
        error_template = self.validator.generate_message_template(MessageType.ERROR)
        self.assertEqual(error_template["message_type"], "error")
        self.assertIn("error", error_template["content"])
        
        status_template = self.validator.generate_message_template(MessageType.STATUS)
        self.assertEqual(status_template["message_type"], "status")
        self.assertIn("status", status_template["content"])
        
        log_template = self.validator.generate_message_template(MessageType.LOG)
        self.assertEqual(log_template["message_type"], "log")
        self.assertIn("message", log_template["content"])
    
    def test_get_schema_version(self):
        """Test getting the schema version."""
        version = self.validator.get_schema_version()
        self.assertIsInstance(version, str)
        self.assertTrue(version in ["1.0", "1.1"])  # Should be one of our defined versions
    
    def test_get_required_fields(self):
        """Test getting required fields for messages."""
        # Get fields required for all messages
        all_required = self.validator.get_required_fields()
        self.assertIsInstance(all_required, list)
        self.assertIn("message_type", all_required)
        self.assertIn("content", all_required)
        self.assertIn("sender", all_required)
        
        # Get fields required for specific message types
        task_request_required = self.validator.get_required_fields(MessageType.TASK_REQUEST)
        self.assertIn("content.task", task_request_required)
        
        repair_suggestion_required = self.validator.get_required_fields(MessageType.REPAIR_SUGGESTION)
        self.assertIn("content.suggestion", repair_suggestion_required)
        self.assertIn("suggested_actions", repair_suggestion_required)
    
    def test_fallback_schema_on_load_failure(self):
        """Test fallback to minimal schema when loading fails."""
        # Mock a file not found error
        with patch('builtins.open', side_effect=FileNotFoundError):
            validator = MessageSchemaValidator()
            self.assertIsNotNone(validator._schema)
            self.assertIn("required", validator._schema)
            self.assertIn("type", validator._schema)
        
        # Mock a JSON decode error
        with patch('builtins.open', mock_open(read_data="invalid json")):
            with patch('json.load', side_effect=json.JSONDecodeError("Invalid JSON", "", 0)):
                with self.assertRaises(TriangulumValidationError):
                    validator = MessageSchemaValidator()
    
    def test_validate_message_detailed(self):
        """Test detailed message validation."""
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Analyze code"},
            sender="test_agent"
        )
        
        result = self.validator.validate_message_detailed(message)
        self.assertTrue(result["valid"])
        self.assertEqual(result["message_type"], "task_request")
        self.assertEqual(len(result["errors"]), 0)
        self.assertIn("validation_time_ms", result)
        
        # Test with invalid message
        invalid_message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={},  # Missing required task field
            sender="test_agent"
        )
        
        result = self.validator.validate_message_detailed(invalid_message)
        self.assertFalse(result["valid"])
        self.assertGreater(len(result["errors"]), 0)
        self.assertIn("error", result)
        self.assertIn("validation_time_ms", result)
    
    def test_validate_required_fields(self):
        """Test validation of required fields."""
        # Create valid message dict with all required fields based on current schema
        message_dict = {
            "message_type": "task_request",
            "content": {"task": "Analyze code"},
            "sender": "test_agent",
            "message_id": "1234",
            "timestamp": 123456789,
            "conversation_id": "conv123",
            "schema_version": "1.1"  # This field is now required
        }
        
        # Should be no missing fields
        missing = self.validator._validate_required_fields(message_dict)
        self.assertEqual(len(missing), 0)
        
        # Remove required field
        del message_dict["sender"]
        missing = self.validator._validate_required_fields(message_dict)
        self.assertIn("sender", missing)
        
        # Test message type specific required fields
        message_dict["sender"] = "test_agent"  # Restore sender
        del message_dict["content"]["task"]
        missing = self.validator._validate_required_fields(message_dict)
        self.assertIn("content.task", missing)
    
    def test_validate_message_content_detailed(self):
        """Test detailed validation of message content."""
        # Valid message
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Analyze code", "priority": "medium"},
            sender="test_agent"
        )
        
        errors = self.validator._validate_message_content_detailed(message)
        self.assertEqual(len(errors), 0)
        
        # Invalid priority value
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Analyze code", "priority": "invalid_priority"},
            sender="test_agent"
        )
        
        errors = self.validator._validate_message_content_detailed(message)
        self.assertGreater(len(errors), 0)
        self.assertEqual(errors[0]["field"], "priority")
        self.assertIn("Priority must be one of", errors[0]["message"])
        
        # Missing required content field
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={},  # Missing task
            sender="test_agent"
        )
        
        errors = self.validator._validate_message_content_detailed(message)
        self.assertGreater(len(errors), 0)
        self.assertEqual(errors[0]["field"], "task")
        self.assertIn("must include a 'task' field", errors[0]["message"])
    
    def test_validate_nested_properties(self):
        """Test validation of nested properties."""
        # Valid repair suggestion with suggested actions
        message = AgentMessage(
            message_type=MessageType.REPAIR_SUGGESTION,
            content={"suggestion": "Fix null pointer"},
            sender="test_agent",
            suggested_actions=[{
                "action_type": "code_change",
                "description": "Add null check"
            }]
        )
        
        errors = self.validator._validate_nested_properties(message)
        self.assertEqual(len(errors), 0)
        
        # Invalid action_type value
        message.suggested_actions[0]["action_type"] = "invalid_type"
        errors = self.validator._validate_nested_properties(message)
        self.assertGreater(len(errors), 0)
        self.assertIn("action_type must be one of", errors[0]["message"])
        
        # Missing required field in action
        message.suggested_actions = [{"action_type": "code_change"}]  # Missing description
        errors = self.validator._validate_nested_properties(message)
        self.assertGreater(len(errors), 0)
        self.assertIn("must include a 'description' field", errors[0]["message"])
        
        # Suggested actions not a list
        message.suggested_actions = "not a list"
        errors = self.validator._validate_nested_properties(message)
        self.assertGreater(len(errors), 0)
        self.assertEqual(errors[0]["field"], "suggested_actions")
        self.assertIn("must be a list", errors[0]["message"])
        
        # Test analysis_results validation
        message = AgentMessage(
            message_type=MessageType.CODE_ANALYSIS,
            content={"analysis": "Found error"},
            sender="test_agent",
            analysis_results={
                "severity": "invalid_severity"  # Invalid severity value
            }
        )
        
        errors = self.validator._validate_nested_properties(message)
        self.assertGreater(len(errors), 0)
        self.assertEqual(errors[0]["field"], "analysis_results.severity")
        self.assertIn("must be one of", errors[0]["message"])
    
    def test_performance_monitoring(self):
        """Test performance monitoring for validation."""
        # Create a very complex message that would take time to validate
        message = AgentMessage(
            message_type=MessageType.REPAIR_SUGGESTION,
            content={"suggestion": "Complex fix"},
            sender="test_agent",
            suggested_actions=[{
                "action_type": "code_change",
                "description": "Complex change",
                "file": "file.py",
                "line": 100,
                "original": "old code",
                "replacement": "new code",
                "rationale": "This is better"
            } for _ in range(100)]  # Create many actions to slow validation
        )
        
        # Patch time.time to simulate slow validation
        original_time = time.time
        time_values = [1000.0, 1000.2]  # 200ms difference
        
        with patch('time.time', side_effect=time_values):
            result = self.validator.validate_message_detailed(message)
            self.assertGreater(result["validation_time_ms"], 100)
            self.assertTrue(len(result["warnings"]) > 0)
            self.assertIn("performance warning", result["warnings"][0])
    
    def test_schema_error_handling(self):
        """Test handling of schema errors."""
        # Mock a schema error
        mock_validator = MagicMock()
        mock_validator.iter_errors.side_effect = jsonschema.exceptions.SchemaError("Bad schema")
        
        with patch.object(self.validator, '_validator', mock_validator):
            result = self.validator.validate_message_detailed(AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                content={"task": "Test"},
                sender="test"
            ))
            
            self.assertFalse(result["valid"])
            self.assertEqual(len(result["errors"]), 1)
            self.assertEqual(result["errors"][0]["type"], "schema_error")
            self.assertIn("Schema validation error", result["errors"][0]["message"])
    
    def test_custom_schema_path(self):
        """Test using a custom schema path."""
        # Create a mock schema file
        mock_schema = {
            "type": "object",
            "required": ["test_field"],
            "properties": {
                "test_field": {"type": "string"}
            }
        }
        
        # Mock open to return our custom schema
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_schema))):
            validator = MessageSchemaValidator(schema_path="custom/path.json")
            self.assertEqual(validator._schema, mock_schema)


if __name__ == "__main__":
    unittest.main()
