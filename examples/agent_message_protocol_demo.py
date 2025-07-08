"""
Agent Message Protocol Demo

This script demonstrates the standardized agent message protocol defined in
Triangulum's Agent Communication Framework. It shows how to create, validate,
and work with messages that follow the protocol.
"""

import logging
import json
import sys
from typing import Dict, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the path so we can import the modules
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.message_schema_validator import MessageSchemaValidator


def create_example_messages() -> List[AgentMessage]:
    """Create a series of example messages demonstrating the protocol."""
    messages = []
    
    # 1. Simple task request
    task_request = AgentMessage(
        message_type=MessageType.TASK_REQUEST,
        content={"task": "Analyze file for bugs"},
        sender="coordinator_agent"
    )
    messages.append(task_request)
    
    # 2. Code analysis message with enhanced fields
    code_analysis = AgentMessage(
        message_type=MessageType.CODE_ANALYSIS,
        content={"analysis": "Found potential type error in file"},
        sender="bug_detector_agent",
        receiver="coordinator_agent",
        parent_id=task_request.message_id,
        conversation_id=task_request.conversation_id,
        confidence=0.85,
        problem_context={
            "file_path": "src/example.py",
            "error_message": "TypeError: cannot concatenate 'str' and 'int' objects",
            "line_number": 42,
            "code_snippet": "result = 'Total: ' + count"
        },
        analysis_results={
            "error_type": "TypeError",
            "error_cause": "String concatenation with integer",
            "affected_code": "result = 'Total: ' + count",
            "severity": "medium"
        },
        suggested_actions=[
            {
                "action_type": "code_change",
                "file": "src/example.py",
                "line": 42,
                "original": "result = 'Total: ' + count",
                "replacement": "result = 'Total: ' + str(count)",
                "description": "Convert integer to string before concatenation",
                "confidence": 0.95,
                "priority": "high"
            }
        ]
    )
    messages.append(code_analysis)
    
    # 3. Create a response using the create_response method
    repair_suggestion = code_analysis.create_response(
        message_type=MessageType.REPAIR_SUGGESTION,
        content={"suggestion": "Fix type error by converting integer to string"},
        confidence=0.9,
        problem_context=code_analysis.problem_context,
        analysis_results=code_analysis.analysis_results,
        suggested_actions=code_analysis.suggested_actions
    )
    messages.append(repair_suggestion)
    
    # 4. Message with relationship metadata
    relationship_analysis = AgentMessage(
        message_type=MessageType.RELATIONSHIP_ANALYSIS,
        content={"analysis": "Found dependencies between files"},
        sender="relationship_analyst_agent",
        receiver="coordinator_agent",
        conversation_id=task_request.conversation_id,
        problem_context={
            "file_path": "src/example.py",
            "related_files": ["src/utils.py", "src/types.py"]
        },
        analysis_results={
            "relationships": {
                "imports": ["src/utils.py", "src/types.py"],
                "imported_by": ["src/main.py"]
            },
            "impact": "Changes to this file may affect src/main.py"
        }
    )
    messages.append(relationship_analysis)
    
    return messages


def validate_messages(messages: List[AgentMessage], validator: MessageSchemaValidator) -> None:
    """Validate messages against the schema."""
    logger.info("Validating messages against the schema...")
    
    for i, message in enumerate(messages):
        is_valid, error = validator.validate_message(message)
        if is_valid:
            logger.info(f"Message {i+1} ({message.message_type.value}) is valid")
        else:
            logger.error(f"Message {i+1} ({message.message_type.value}) is invalid: {error}")


def demonstrate_serialization(message: AgentMessage) -> None:
    """Demonstrate serialization and deserialization of messages."""
    logger.info("Demonstrating message serialization...")
    
    # Convert message to JSON
    json_str = message.to_json()
    logger.info(f"JSON representation:\n{json.dumps(json.loads(json_str), indent=2)}")
    
    # Deserialize back to a message
    recreated = AgentMessage.from_json(json_str)
    logger.info(f"Deserialized message has type: {recreated.message_type.value}")
    logger.info(f"Contains {len(recreated.suggested_actions)} suggested actions")
    
    # Verify fields match
    assert recreated.message_id == message.message_id
    assert recreated.content == message.content
    assert recreated.problem_context == message.problem_context
    assert recreated.analysis_results == message.analysis_results
    logger.info("Verified original and deserialized messages match")


def demonstrate_schema_templates(validator: MessageSchemaValidator) -> None:
    """Demonstrate schema template generation."""
    logger.info("Generating message templates from schema...")
    
    # Generate templates for different message types
    for message_type in [MessageType.TASK_REQUEST, MessageType.CODE_ANALYSIS, 
                         MessageType.REPAIR_SUGGESTION]:
        template = validator.generate_message_template(message_type)
        logger.info(f"Template for {message_type.value}:\n{json.dumps(template, indent=2)}")


def main():
    """Main function to run the demo."""
    logger.info("Starting Agent Message Protocol Demo")
    
    # Create example messages
    messages = create_example_messages()
    logger.info(f"Created {len(messages)} example messages")
    
    # Initialize the schema validator
    validator = MessageSchemaValidator()
    
    # Validate messages
    validate_messages(messages, validator)
    
    # Demonstrate serialization with a message that has all enhanced fields
    demonstrate_serialization(messages[1])
    
    # Demonstrate schema templates
    demonstrate_schema_templates(validator)
    
    logger.info("Agent Message Protocol Demo completed")


if __name__ == "__main__":
    main()
