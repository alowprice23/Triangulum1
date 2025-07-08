#!/usr/bin/env python3
"""
Unit tests for the Message Schema validation system.

This module contains comprehensive tests for the Message Schema validation system,
verifying schema validation, type conversion, default value handling, and error reporting.
"""

import unittest
import json
import os
import sys
import tempfile
from typing import Dict, List, Any, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from triangulum_lx.agents.message import AgentMessage, MessageType, ConfidenceLevel
from triangulum_lx.agents.message_schema import (
    SchemaType, SchemaField, MessageSchema, validate_message,
    get_default_values, convert_field_type, export_schema_to_json,
    import_schema_from_json, MESSAGE_SCHEMA_V1_1
)


class TestSchemaField(unittest.TestCase):
    """Test cases for the SchemaField class."""
    
    def test_string_validation(self):
        """Test validation of string fields."""
        # Create a string field
        field = SchemaField(
            name="test_string",
            type=SchemaType.STRING,
            required=True,
            min_length=3,
            max_length=10,
            pattern=r"^[a-z]+$"
        )
        
        # Test valid string
        is_valid, error = field.validate("abcdef")
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test string too short
        is_valid, error = field.validate("ab")
        self.assertFalse(is_valid)
        self.assertIn("at least 3 characters", error)
        
        # Test string too long
        is_valid, error = field.validate("abcdefghijk")
        self.assertFalse(is_valid)
        self.assertIn("at most 10 characters", error)
        
        # Test string not matching pattern
        is_valid, error = field.validate("abc123")
        self.assertFalse(is_valid)
        self.assertIn("match pattern", error)
        
        # Test non-string value
        is_valid, error = field.validate(123)
        self.assertFalse(is_valid)
        self.assertIn("must be a string", error)
        
        # Test None for required field
        is_valid, error = field.validate(None)
        self.assertFalse(is_valid)
        self.assertIn("is required", error)
        
        # Test None for non-required field
        optional_field = SchemaField(
            name="optional_string",
            type=SchemaType.STRING,
            required=False
        )
        is_valid, error = optional_field.validate(None)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_integer_validation(self):
        """Test validation of integer fields."""
        # Create an integer field
        field = SchemaField(
            name="test_integer",
            type=SchemaType.INTEGER,
            required=True,
            min_value=1,
            max_value=100
        )
        
        # Test valid integer
        is_valid, error = field.validate(42)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test integer too small
        is_valid, error = field.validate(0)
        self.assertFalse(is_valid)
        self.assertIn("at least 1", error)
        
        # Test integer too large
        is_valid, error = field.validate(101)
        self.assertFalse(is_valid)
        self.assertIn("at most 100", error)
        
        # Test non-integer value
        is_valid, error = field.validate("42")
        self.assertFalse(is_valid)
        self.assertIn("must be an integer", error)
        
        # Test boolean (should not be accepted as integer)
        is_valid, error = field.validate(True)
        self.assertFalse(is_valid)
        self.assertIn("must be an integer", error)
    
    def test_float_validation(self):
        """Test validation of float fields."""
        # Create a float field
        field = SchemaField(
            name="test_float",
            type=SchemaType.FLOAT,
            required=True,
            min_value=0.0,
            max_value=1.0
        )
        
        # Test valid float
        is_valid, error = field.validate(0.5)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test float too small
        is_valid, error = field.validate(-0.1)
        self.assertFalse(is_valid)
        self.assertIn("at least 0.0", error)
        
        # Test float too large
        is_valid, error = field.validate(1.1)
        self.assertFalse(is_valid)
        self.assertIn("at most 1.0", error)
        
        # Test integer (should be accepted as float)
        is_valid, error = field.validate(0)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test non-numeric value
        is_valid, error = field.validate("0.5")
        self.assertFalse(is_valid)
        self.assertIn("must be a number", error)
    
    def test_boolean_validation(self):
        """Test validation of boolean fields."""
        # Create a boolean field
        field = SchemaField(
            name="test_boolean",
            type=SchemaType.BOOLEAN,
            required=True
        )
        
        # Test valid boolean
        is_valid, error = field.validate(True)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        is_valid, error = field.validate(False)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test non-boolean value
        is_valid, error = field.validate("true")
        self.assertFalse(is_valid)
        self.assertIn("must be a boolean", error)
        
        is_valid, error = field.validate(1)
        self.assertFalse(is_valid)
        self.assertIn("must be a boolean", error)
    
    def test_enum_validation(self):
        """Test validation of enum fields."""
        # Create an enum field
        field = SchemaField(
            name="test_enum",
            type=SchemaType.ENUM,
            required=True,
            enum_values=["option1", "option2", "option3"]
        )
        
        # Test valid enum value
        is_valid, error = field.validate("option1")
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test invalid enum value
        is_valid, error = field.validate("option4")
        self.assertFalse(is_valid)
        self.assertIn("must be one of", error)
        
        # Test non-string value (but in enum values)
        field_with_mixed_types = SchemaField(
            name="mixed_enum",
            type=SchemaType.ENUM,
            required=True,
            enum_values=["option1", 2, True]
        )
        
        is_valid, error = field_with_mixed_types.validate(2)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test enum field with no values
        field_no_values = SchemaField(
            name="empty_enum",
            type=SchemaType.ENUM,
            required=True
        )
        
        is_valid, error = field_no_values.validate("anything")
        self.assertFalse(is_valid)
        self.assertIn("no enum values defined", error)
    
    def test_array_validation(self):
        """Test validation of array fields."""
        # Create an array field with item type
        item_type = SchemaField(
            name="item",
            type=SchemaType.STRING,
            required=True,
            min_length=2
        )
        
        field = SchemaField(
            name="test_array",
            type=SchemaType.ARRAY,
            required=True,
            min_length=1,
            max_length=3,
            item_type=item_type
        )
        
        # Test valid array
        is_valid, error = field.validate(["ab", "cde", "fghi"])
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test array too short
        is_valid, error = field.validate([])
        self.assertFalse(is_valid)
        self.assertIn("at least 1 items", error)
        
        # Test array too long
        is_valid, error = field.validate(["a", "b", "c", "d"])
        self.assertFalse(is_valid)
        self.assertIn("at most 3 items", error)
        
        # Test invalid item in array
        is_valid, error = field.validate(["abc", "d", "efg"])
        self.assertFalse(is_valid)
        self.assertIn("Item 1 in field", error)
        self.assertIn("at least 2 characters", error)
        
        # Test non-array value
        is_valid, error = field.validate("not an array")
        self.assertFalse(is_valid)
        self.assertIn("must be an array", error)
    
    def test_object_validation(self):
        """Test validation of object fields."""
        # Create an object field with properties
        properties = {
            "name": SchemaField(
                name="name",
                type=SchemaType.STRING,
                required=True
            ),
            "age": SchemaField(
                name="age",
                type=SchemaType.INTEGER,
                required=False,
                min_value=0
            )
        }
        
        field = SchemaField(
            name="test_object",
            type=SchemaType.OBJECT,
            required=True,
            properties=properties
        )
        
        # Test valid object
        is_valid, error = field.validate({"name": "John", "age": 30})
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test object with missing required property
        is_valid, error = field.validate({"age": 30})
        self.assertFalse(is_valid)
        self.assertIn("Required property 'name' missing", error)
        
        # Test object with invalid property
        is_valid, error = field.validate({"name": "John", "age": -5})
        self.assertFalse(is_valid)
        self.assertIn("Property 'age' in field", error)
        self.assertIn("at least 0", error)
        
        # Test non-object value
        is_valid, error = field.validate("not an object")
        self.assertFalse(is_valid)
        self.assertIn("must be an object", error)
    
    def test_custom_validator(self):
        """Test custom validation function."""
        # Create a field with custom validator
        def validate_even(value):
            return isinstance(value, int) and value % 2 == 0
        
        field = SchemaField(
            name="even_number",
            type=SchemaType.INTEGER,
            required=True,
            custom_validator=validate_even
        )
        
        # Test valid even number
        is_valid, error = field.validate(42)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test invalid odd number
        is_valid, error = field.validate(43)
        self.assertFalse(is_valid)
        self.assertIn("failed custom validation", error)
        
        # Test custom validator that raises exception
        def validator_with_exception(value):
            raise ValueError("Custom validation error")
        
        field_with_exception = SchemaField(
            name="exception_field",
            type=SchemaType.STRING,
            required=True,
            custom_validator=validator_with_exception
        )
        
        is_valid, error = field_with_exception.validate("test")
        self.assertFalse(is_valid)
        self.assertIn("custom validation error", error)


class TestMessageSchema(unittest.TestCase):
    """Test cases for the MessageSchema class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a simple schema for testing
        self.schema = MessageSchema(
            version="test",
            fields={
                "id": SchemaField(
                    name="id",
                    type=SchemaType.STRING,
                    required=True
                ),
                "name": SchemaField(
                    name="name",
                    type=SchemaType.STRING,
                    required=True
                ),
                "age": SchemaField(
                    name="age",
                    type=SchemaType.INTEGER,
                    required=False,
                    min_value=0
                ),
                "tags": SchemaField(
                    name="tags",
                    type=SchemaType.ARRAY,
                    required=False,
                    item_type=SchemaField(
                        name="tag",
                        type=SchemaType.STRING,
                        required=True
                    )
                )
            }
        )
    
    def test_validate_valid_message(self):
        """Test validation of a valid message."""
        # Create a valid message
        message = {
            "id": "123",
            "name": "John Doe",
            "age": 30,
            "tags": ["developer", "python"]
        }
        
        # Validate the message
        is_valid, errors = self.schema.validate(message)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_missing_required_field(self):
        """Test validation of a message with missing required field."""
        # Create a message with missing required field
        message = {
            "id": "123",
            # Missing "name" field
            "age": 30
        }
        
        # Validate the message
        is_valid, errors = self.schema.validate(message)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("Required field 'name' is missing", errors[0])
    
    def test_validate_invalid_field(self):
        """Test validation of a message with an invalid field."""
        # Create a message with an invalid field
        message = {
            "id": "123",
            "name": "John Doe",
            "age": -5  # Invalid age
        }
        
        # Validate the message
        is_valid, errors = self.schema.validate(message)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("at least 0", errors[0])
    
    def test_validate_multiple_errors(self):
        """Test validation of a message with multiple errors."""
        # Create a message with multiple errors
        message = {
            "id": "123",
            # Missing "name" field
            "age": -5,  # Invalid age
            "tags": ["developer", 123]  # Invalid tag
        }
        
        # Validate the message
        is_valid, errors = self.schema.validate(message)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 3)
    
    def test_validate_unknown_field(self):
        """Test validation of a message with an unknown field."""
        # Create a message with an unknown field
        message = {
            "id": "123",
            "name": "John Doe",
            "unknown_field": "value"
        }
        
        # Validate the message
        is_valid, errors = self.schema.validate(message)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)


class TestMessageSchemaValidation(unittest.TestCase):
    """Test cases for the message schema validation functions."""
    
    def test_validate_message(self):
        """Test the validate_message function."""
        # Create a valid message
        valid_message = {
            "message_type": "status",
            "content": {"status": "ok"},
            "sender": "test_agent",
            "schema_version": "1.1"
        }
        
        # Validate the message
        is_valid, errors = validate_message(valid_message)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Create an invalid message
        invalid_message = {
            "message_type": "invalid_type",  # Invalid message type
            "content": {"status": "ok"},
            "sender": "test_agent",
            "schema_version": "1.1"
        }
        
        # Validate the message
        is_valid, errors = validate_message(invalid_message)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        
        # Create a message with unsupported schema version
        unsupported_version = {
            "message_type": "status",
            "content": {"status": "ok"},
            "sender": "test_agent",
            "schema_version": "999.999"  # Unsupported version
        }
        
        # Validate the message
        is_valid, errors = validate_message(unsupported_version)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("Unsupported schema version", errors[0])
    
    def test_get_default_values(self):
        """Test the get_default_values function."""
        # Get default values
        defaults = get_default_values()
        
        # Check that defaults include expected fields
        self.assertIn("schema_version", defaults)
        self.assertEqual(defaults["schema_version"], "1.1")
        
        self.assertIn("is_chunked", defaults)
        self.assertEqual(defaults["is_chunked"], False)
        
        self.assertIn("compressed", defaults)
        self.assertEqual(defaults["compressed"], False)
        
        # Test with unsupported version
        with self.assertRaises(ValueError):
            get_default_values("999.999")
    
    def test_convert_field_type(self):
        """Test the convert_field_type function."""
        # Test string to MessageType conversion
        converted = convert_field_type("message_type", "status")
        self.assertEqual(converted, MessageType.STATUS)
        
        # Test string to integer conversion
        converted = convert_field_type("total_chunks", "42")
        self.assertEqual(converted, 42)
        
        # Test string to float conversion
        converted = convert_field_type("confidence", "0.75")
        self.assertEqual(converted, 0.75)
        
        # Test string to boolean conversion
        converted = convert_field_type("is_chunked", "true")
        self.assertEqual(converted, True)
        
        converted = convert_field_type("is_chunked", "false")
        self.assertEqual(converted, False)
        
        # Test integer to float conversion
        converted = convert_field_type("confidence", 1)
        self.assertEqual(converted, 1.0)
        
        # Test field with no schema
        converted = convert_field_type("unknown_field", "value")
        self.assertEqual(converted, "value")
        
        # Test with unsupported version
        with self.assertRaises(ValueError):
            convert_field_type("message_type", "status", "999.999")


class TestSchemaExportImport(unittest.TestCase):
    """Test cases for schema export and import functions."""
    
    def test_export_import_schema(self):
        """Test exporting and importing a schema."""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Export the schema
            export_schema_to_json(MESSAGE_SCHEMA_V1_1, temp_path)
            
            # Check that the file exists
            self.assertTrue(os.path.exists(temp_path))
            
            # Import the schema
            imported_schema = import_schema_from_json(temp_path)
            
            # Check that the imported schema matches the original
            self.assertEqual(imported_schema.version, MESSAGE_SCHEMA_V1_1.version)
            self.assertEqual(len(imported_schema.fields), len(MESSAGE_SCHEMA_V1_1.fields))
            
            # Check a few specific fields
            self.assertIn("message_type", imported_schema.fields)
            self.assertEqual(imported_schema.fields["message_type"].type, SchemaType.ENUM)
            self.assertTrue(imported_schema.fields["message_type"].required)
            
            self.assertIn("content", imported_schema.fields)
            self.assertEqual(imported_schema.fields["content"].type, SchemaType.OBJECT)
            self.assertTrue(imported_schema.fields["content"].required)
        
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestAgentMessageWithSchema(unittest.TestCase):
    """Test cases for AgentMessage with schema validation."""
    
    def test_create_valid_message(self):
        """Test creating a valid message."""
        # Create a valid message
        message = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "ok"},
            sender="test_agent"
        )
        
        # Check that the message was created successfully
        self.assertEqual(message.message_type, MessageType.STATUS)
        self.assertEqual(message.content, {"status": "ok"})
        self.assertEqual(message.sender, "test_agent")
    
    def test_create_invalid_message(self):
        """Test creating an invalid message."""
        # Try to create a message with invalid message_type
        with self.assertRaises(ValueError):
            AgentMessage(
                message_type="invalid_type",  # Should be a MessageType enum
                content={"status": "ok"},
                sender="test_agent"
            )
        
        # Try to create a message with invalid content
        with self.assertRaises(ValueError):
            AgentMessage(
                message_type=MessageType.STATUS,
                content="not a dictionary",  # Should be a dictionary
                sender="test_agent"
            )
        
        # Try to create a message with missing sender
        with self.assertRaises(ValueError):
            AgentMessage(
                message_type=MessageType.STATUS,
                content={"status": "ok"},
                sender=""  # Empty sender
            )
        
        # Try to create a message with invalid confidence
        with self.assertRaises(ValueError):
            AgentMessage(
                message_type=MessageType.STATUS,
                content={"status": "ok"},
                sender="test_agent",
                confidence=1.5  # Should be between 0.0 and 1.0
            )
    
    def test_from_dict_valid(self):
        """Test creating a message from a valid dictionary."""
        # Create a valid dictionary
        message_dict = {
            "message_type": "status",
            "content": {"status": "ok"},
            "sender": "test_agent"
        }
        
        # Create a message from the dictionary
        message = AgentMessage.from_dict(message_dict)
        
        # Check that the message was created successfully
        self.assertEqual(message.message_type, MessageType.STATUS)
        self.assertEqual(message.content, {"status": "ok"})
        self.assertEqual(message.sender, "test_agent")
    
    def test_from_dict_with_defaults(self):
        """Test creating a message from a dictionary with default values."""
        # Create a dictionary with minimal fields
        message_dict = {
            "message_type": "status",
            "content": {"status": "ok"},
            "sender": "test_agent"
        }
        
        # Create a message from the dictionary
        message = AgentMessage.from_dict(message_dict)
        
        # Check that default values were applied
        self.assertEqual(message.schema_version, "1.1")
        self.assertEqual(message.is_chunked, False)
        self.assertEqual(message.compressed, False)
        self.assertEqual(message.problem_context, {})
        self.assertEqual(message.analysis_results, {})
        self.assertEqual(message.suggested_actions, [])
    
    def test_from_dict_with_type_conversion(self):
        """Test creating a message from a dictionary with type conversion."""
        # Create a dictionary with fields that need conversion
        message_dict = {
            "message_type": "status",  # String instead of enum
            "content": {"status": "ok"},
            "sender": "test_agent",
            "confidence": "0.75",  # String instead of float
            "is_chunked": "true"  # String instead of boolean
        }
        
        # Create a message from the dictionary
        message = AgentMessage.from_dict(message_dict)
        
        # Check that types were converted correctly
        self.assertEqual(message.message_type, MessageType.STATUS)
        self.assertEqual(message.confidence, 0.75)
        self.assertEqual(message.is_chunked, True)
    
    def test_to_dict_and_json(self):
        """Test converting a message to dictionary and JSON."""
        # Create a message
        message = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "ok"},
            sender="test_agent",
            confidence=0.75
        )
        
        # Convert to dictionary
        message_dict = message.to_dict()
        
        # Check dictionary fields
        self.assertEqual(message_dict["message_type"], "status")
        self.assertEqual(message_dict["content"], {"status": "ok"})
        self.assertEqual(message_dict["sender"], "test_agent")
        self.assertEqual(message_dict["confidence"], 0.75)
        
        # Convert to JSON
        message_json = message.to_json()
        
        # Parse JSON and check fields
        parsed_json = json.loads(message_json)
        self.assertEqual(parsed_json["message_type"], "status")
        self.assertEqual(parsed_json["content"], {"status": "ok"})
        self.assertEqual(parsed_json["sender"], "test_agent")
        self.assertEqual(parsed_json["confidence"], 0.75)
    
    def test_create_response(self):
        """Test creating a response message."""
        # Create an original message
        original = AgentMessage(
            message_type=MessageType.QUERY,
            content={"query": "status?"},
            sender="agent1",
            receiver="agent2"
        )
        
        # Create a response
        response = original.create_response(
            message_type=MessageType.QUERY_RESPONSE,
            content={"response": "ok"},
            confidence=0.9
        )
        
        # Check response fields
        self.assertEqual(response.message_type, MessageType.QUERY_RESPONSE)
        self.assertEqual(response.content, {"response": "ok"})
        self.assertEqual(response.sender, "agent2")
        self.assertEqual(response.receiver, "agent1")
        self.assertEqual(response.parent_id, original.message_id)
        self.assertEqual(response.conversation_id, original.conversation_id)
        self.assertEqual(response.confidence, 0.9)


if __name__ == "__main__":
    unittest.main()
