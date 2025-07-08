#!/usr/bin/env python3
"""
Message Schema Demo

This demo showcases the message schema validation and parameter handling capabilities:
1. Schema validation for message fields
2. Type conversion for message parameters
3. Default value handling
4. Error reporting for invalid messages
5. Schema versioning and backward compatibility
"""

import os
import sys
import json
import time
import logging
from typing import Dict, List, Any, Optional

# Add the parent directory to the path so we can import triangulum_lx
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.agents.message import AgentMessage, MessageType, ConfidenceLevel
from triangulum_lx.agents.message_schema import (
    validate_message, get_default_values, convert_field_type,
    export_schema_to_json, import_schema_from_json,
    MESSAGE_SCHEMA_V1_1
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("message_schema_demo")


def demo_schema_validation():
    """Demonstrate schema validation for messages."""
    print("\n=== Schema Validation Demo ===")
    
    # Create a valid message
    valid_message = {
        "message_type": "task_request",
        "content": {"task": "analyze_code", "file_path": "example.py"},
        "sender": "demo_agent",
        "receiver": "analysis_agent",
        "confidence": 0.8,
        "metadata": {"priority": "high"}
    }
    
    # Validate the message
    print("\nValidating a valid message:")
    is_valid, errors = validate_message(valid_message)
    print(f"  Valid: {is_valid}")
    if not is_valid:
        print(f"  Errors: {errors}")
    
    # Create an invalid message (missing required field)
    invalid_message1 = {
        "message_type": "task_request",
        "sender": "demo_agent",  # Missing 'content' field
        "receiver": "analysis_agent"
    }
    
    # Validate the invalid message
    print("\nValidating a message with missing required field:")
    is_valid, errors = validate_message(invalid_message1)
    print(f"  Valid: {is_valid}")
    if not is_valid:
        print(f"  Errors: {errors}")
    
    # Create an invalid message (wrong type)
    invalid_message2 = {
        "message_type": "task_request",
        "content": "This should be a dictionary, not a string",
        "sender": "demo_agent",
        "receiver": "analysis_agent"
    }
    
    # Validate the invalid message
    print("\nValidating a message with wrong field type:")
    is_valid, errors = validate_message(invalid_message2)
    print(f"  Valid: {is_valid}")
    if not is_valid:
        print(f"  Errors: {errors}")
    
    # Create an invalid message (invalid enum value)
    invalid_message3 = {
        "message_type": "invalid_type",  # Not a valid MessageType
        "content": {"task": "analyze_code"},
        "sender": "demo_agent",
        "receiver": "analysis_agent"
    }
    
    # Validate the invalid message
    print("\nValidating a message with invalid enum value:")
    is_valid, errors = validate_message(invalid_message3)
    print(f"  Valid: {is_valid}")
    if not is_valid:
        print(f"  Errors: {errors}")
    
    # Create an invalid message (value out of range)
    invalid_message4 = {
        "message_type": "task_request",
        "content": {"task": "analyze_code"},
        "sender": "demo_agent",
        "receiver": "analysis_agent",
        "confidence": 1.5  # Should be between 0.0 and 1.0
    }
    
    # Validate the invalid message
    print("\nValidating a message with value out of range:")
    is_valid, errors = validate_message(invalid_message4)
    print(f"  Valid: {is_valid}")
    if not is_valid:
        print(f"  Errors: {errors}")


def demo_type_conversion():
    """Demonstrate type conversion for message parameters."""
    print("\n=== Type Conversion Demo ===")
    
    # String to MessageType enum
    print("\nConverting string to MessageType enum:")
    message_type_str = "task_request"
    message_type_enum = convert_field_type("message_type", message_type_str)
    print(f"  Original: {message_type_str} ({type(message_type_str).__name__})")
    print(f"  Converted: {message_type_enum} ({type(message_type_enum).__name__})")
    
    # String to integer
    print("\nConverting string to integer:")
    int_str = "42"
    int_val = convert_field_type("total_chunks", int_str)
    print(f"  Original: {int_str} ({type(int_str).__name__})")
    print(f"  Converted: {int_val} ({type(int_val).__name__})")
    
    # String to float
    print("\nConverting string to float:")
    float_str = "0.75"
    float_val = convert_field_type("confidence", float_str)
    print(f"  Original: {float_str} ({type(float_str).__name__})")
    print(f"  Converted: {float_val} ({type(float_val).__name__})")
    
    # String to boolean
    print("\nConverting string to boolean:")
    bool_str = "true"
    bool_val = convert_field_type("is_chunked", bool_str)
    print(f"  Original: {bool_str} ({type(bool_str).__name__})")
    print(f"  Converted: {bool_val} ({type(bool_val).__name__})")
    
    # Integer to float
    print("\nConverting integer to float:")
    int_val = 42
    float_val = convert_field_type("confidence", int_val)
    print(f"  Original: {int_val} ({type(int_val).__name__})")
    print(f"  Converted: {float_val} ({type(float_val).__name__})")


def demo_default_values():
    """Demonstrate default value handling for messages."""
    print("\n=== Default Value Handling Demo ===")
    
    # Get default values from schema
    defaults = get_default_values()
    print("\nDefault values from schema:")
    for field, value in defaults.items():
        print(f"  {field}: {value}")
    
    # Create a message with minimal fields
    minimal_message = {
        "message_type": "status",
        "content": {"status": "ready"},
        "sender": "demo_agent"
    }
    
    # Create an AgentMessage instance (which will apply defaults)
    print("\nCreating a message with minimal fields:")
    message = AgentMessage.from_dict(minimal_message)
    
    # Show the complete message with defaults applied
    print("\nComplete message with defaults applied:")
    message_dict = message.to_dict()
    for field, value in message_dict.items():
        if field in minimal_message:
            print(f"  {field}: {value} (provided)")
        else:
            print(f"  {field}: {value} (default)")


def demo_error_reporting():
    """Demonstrate error reporting for invalid messages."""
    print("\n=== Error Reporting Demo ===")
    
    # Try to create an invalid message
    print("\nTrying to create an invalid message:")
    try:
        message = AgentMessage(
            message_type="not_an_enum",  # Should be a MessageType enum
            content={"task": "analyze_code"},
            sender="demo_agent"
        )
        print("  Message created successfully (unexpected)")
    except ValueError as e:
        print(f"  Error: {e}")
    
    # Try to create a message with invalid confidence
    print("\nTrying to create a message with invalid confidence:")
    try:
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "analyze_code"},
            sender="demo_agent",
            confidence=2.0  # Should be between 0.0 and 1.0
        )
        print("  Message created successfully (unexpected)")
    except ValueError as e:
        print(f"  Error: {e}")
    
    # Try to create a message with wrong content type
    print("\nTrying to create a message with wrong content type:")
    try:
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content="This should be a dictionary",  # Should be a dictionary
            sender="demo_agent"
        )
        print("  Message created successfully (unexpected)")
    except ValueError as e:
        print(f"  Error: {e}")


def demo_schema_versioning():
    """Demonstrate schema versioning and backward compatibility."""
    print("\n=== Schema Versioning Demo ===")
    
    # Create a message with old schema version
    old_message = {
        "message_type": "task_request",
        "content": {"task": "analyze_code"},
        "sender": "demo_agent",
        "schema_version": "1.0"  # Old schema version
    }
    
    # Convert to AgentMessage (which will upgrade the schema)
    print("\nConverting a message with old schema version:")
    message = AgentMessage.from_dict(old_message)
    
    # Show the upgraded message
    print("\nUpgraded message:")
    message_dict = message.to_dict()
    print(f"  Schema version: {message_dict['schema_version']}")
    print(f"  Has problem_context: {'problem_context' in message_dict}")
    print(f"  Has analysis_results: {'analysis_results' in message_dict}")
    print(f"  Has suggested_actions: {'suggested_actions' in message_dict}")


def demo_schema_export_import():
    """Demonstrate schema export and import."""
    print("\n=== Schema Export/Import Demo ===")
    
    # Export schema to JSON
    schema_file = "message_schema_demo.json"
    print(f"\nExporting schema to {schema_file}:")
    export_schema_to_json(MESSAGE_SCHEMA_V1_1, schema_file)
    print("  Schema exported successfully")
    
    # Read the exported schema
    with open(schema_file, 'r') as f:
        schema_json = json.load(f)
    
    print("\nExported schema summary:")
    print(f"  Version: {schema_json['version']}")
    print(f"  Number of fields: {len(schema_json['fields'])}")
    
    # Import schema from JSON
    print(f"\nImporting schema from {schema_file}:")
    imported_schema = import_schema_from_json(schema_file)
    print("  Schema imported successfully")
    
    print("\nImported schema summary:")
    print(f"  Version: {imported_schema.version}")
    print(f"  Number of fields: {len(imported_schema.fields)}")
    
    # Clean up
    os.remove(schema_file)
    print(f"\nRemoved temporary file: {schema_file}")


def demo_agent_message_creation():
    """Demonstrate creating and validating AgentMessage instances."""
    print("\n=== AgentMessage Creation Demo ===")
    
    # Create a message directly
    print("\nCreating a message directly:")
    message1 = AgentMessage(
        message_type=MessageType.TASK_REQUEST,
        content={"task": "analyze_code", "file_path": "example.py"},
        sender="demo_agent",
        receiver="analysis_agent",
        confidence=0.8,
        metadata={"priority": "high"}
    )
    print(f"  Message ID: {message1.message_id}")
    print(f"  Message type: {message1.message_type}")
    print(f"  Sender: {message1.sender}")
    print(f"  Receiver: {message1.receiver}")
    
    # Create a message from dictionary
    print("\nCreating a message from dictionary:")
    message_dict = {
        "message_type": "query",
        "content": {"query": "What is the status?"},
        "sender": "demo_agent",
        "receiver": "status_agent",
        "metadata": {"urgent": True}
    }
    message2 = AgentMessage.from_dict(message_dict)
    print(f"  Message ID: {message2.message_id}")
    print(f"  Message type: {message2.message_type}")
    print(f"  Sender: {message2.sender}")
    print(f"  Receiver: {message2.receiver}")
    
    # Create a response message
    print("\nCreating a response message:")
    response = message2.create_response(
        message_type=MessageType.QUERY_RESPONSE,
        content={"response": "System is running normally"},
        confidence=ConfidenceLevel.HIGH.value,
        metadata={"response_time_ms": 42}
    )
    print(f"  Response ID: {response.message_id}")
    print(f"  Response type: {response.message_type}")
    print(f"  Sender: {response.sender}")
    print(f"  Receiver: {response.receiver}")
    print(f"  Parent ID: {response.parent_id}")
    print(f"  Conversation ID: {response.conversation_id}")
    
    # Convert to JSON and back
    print("\nConverting message to JSON and back:")
    json_str = message1.to_json()
    print(f"  JSON length: {len(json_str)} characters")
    message3 = AgentMessage.from_json(json_str)
    print(f"  Reconstructed message ID: {message3.message_id}")
    print(f"  Matches original: {message3.message_id == message1.message_id}")


def main():
    """Main function to run the demo."""
    print("Message Schema Demo")
    print("==================\n")
    
    # Run the demos
    demo_schema_validation()
    demo_type_conversion()
    demo_default_values()
    demo_error_reporting()
    demo_schema_versioning()
    demo_schema_export_import()
    demo_agent_message_creation()
    
    print("\nDemo completed successfully!")


if __name__ == "__main__":
    main()
