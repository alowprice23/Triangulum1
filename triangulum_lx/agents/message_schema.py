"""
Message Schema - Defines the schema for agent messages.

This module provides schema definitions and validation for agent messages,
ensuring consistent message structure and proper type handling across the system.
"""

import json
import re
from typing import Dict, List, Any, Optional, Union, Type, Callable
from enum import Enum
from dataclasses import dataclass, field

from triangulum_lx.agents.message import MessageType, ConfidenceLevel


class SchemaType(Enum):
    """Types of schema fields."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    ENUM = "enum"
    ANY = "any"
    NULL = "null"


@dataclass
class SchemaField:
    """Definition of a schema field."""
    name: str
    type: SchemaType
    required: bool = False
    default: Any = None
    enum_values: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    item_type: Optional['SchemaField'] = None
    properties: Optional[Dict[str, 'SchemaField']] = None
    description: Optional[str] = None
    custom_validator: Optional[Callable[[Any], bool]] = None
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate a value against this schema field.
        
        Args:
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Handle None values for non-required fields
        if value is None:
            if self.required:
                return False, f"Field '{self.name}' is required"
            return True, None
        
        # Type validation
        if self.type == SchemaType.STRING:
            if not isinstance(value, str):
                return False, f"Field '{self.name}' must be a string"
            
            # Length validation
            if self.min_length is not None and len(value) < self.min_length:
                return False, f"Field '{self.name}' must be at least {self.min_length} characters"
            if self.max_length is not None and len(value) > self.max_length:
                return False, f"Field '{self.name}' must be at most {self.max_length} characters"
            
            # Pattern validation
            if self.pattern is not None and not re.match(self.pattern, value):
                return False, f"Field '{self.name}' must match pattern '{self.pattern}'"
        
        elif self.type == SchemaType.INTEGER:
            if not isinstance(value, int) or isinstance(value, bool):
                return False, f"Field '{self.name}' must be an integer"
            
            # Range validation
            if self.min_value is not None and value < self.min_value:
                return False, f"Field '{self.name}' must be at least {self.min_value}"
            if self.max_value is not None and value > self.max_value:
                return False, f"Field '{self.name}' must be at most {self.max_value}"
        
        elif self.type == SchemaType.FLOAT:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return False, f"Field '{self.name}' must be a number"
            
            # Range validation
            if self.min_value is not None and value < self.min_value:
                return False, f"Field '{self.name}' must be at least {self.min_value}"
            if self.max_value is not None and value > self.max_value:
                return False, f"Field '{self.name}' must be at most {self.max_value}"
        
        elif self.type == SchemaType.BOOLEAN:
            if not isinstance(value, bool):
                return False, f"Field '{self.name}' must be a boolean"
        
        elif self.type == SchemaType.ENUM:
            if self.enum_values is None:
                return False, f"Field '{self.name}' has no enum values defined"
            
            if value not in self.enum_values:
                valid_values = ", ".join(str(v) for v in self.enum_values)
                return False, f"Field '{self.name}' must be one of: {valid_values}"
        
        elif self.type == SchemaType.ARRAY:
            if not isinstance(value, list):
                return False, f"Field '{self.name}' must be an array"
            
            # Length validation
            if self.min_length is not None and len(value) < self.min_length:
                return False, f"Field '{self.name}' must have at least {self.min_length} items"
            if self.max_length is not None and len(value) > self.max_length:
                return False, f"Field '{self.name}' must have at most {self.max_length} items"
            
            # Item type validation
            if self.item_type is not None:
                for i, item in enumerate(value):
                    is_valid, error = self.item_type.validate(item)
                    if not is_valid:
                        return False, f"Item {i} in field '{self.name}': {error}"
        
        elif self.type == SchemaType.OBJECT:
            if not isinstance(value, dict):
                return False, f"Field '{self.name}' must be an object"
            
            # Property validation
            if self.properties is not None:
                for prop_name, prop_schema in self.properties.items():
                    if prop_schema.required and prop_name not in value:
                        return False, f"Required property '{prop_name}' missing from field '{self.name}'"
                    
                    if prop_name in value:
                        is_valid, error = prop_schema.validate(value[prop_name])
                        if not is_valid:
                            return False, f"Property '{prop_name}' in field '{self.name}': {error}"
        
        # Custom validation
        if self.custom_validator is not None:
            try:
                if not self.custom_validator(value):
                    return False, f"Field '{self.name}' failed custom validation"
            except Exception as e:
                return False, f"Field '{self.name}' custom validation error: {str(e)}"
        
        return True, None


@dataclass
class MessageSchema:
    """Schema for validating agent messages."""
    version: str
    fields: Dict[str, SchemaField]
    
    def validate(self, message_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate a message against this schema.
        
        Args:
            message_data: Message data to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check required fields
        for field_name, field_schema in self.fields.items():
            if field_schema.required and field_name not in message_data:
                errors.append(f"Required field '{field_name}' is missing")
        
        # Validate each field
        for field_name, field_value in message_data.items():
            if field_name in self.fields:
                is_valid, error = self.fields[field_name].validate(field_value)
                if not is_valid:
                    errors.append(error)
        
        return len(errors) == 0, errors


# Define the message schema
MESSAGE_SCHEMA_V1_1 = MessageSchema(
    version="1.1",
    fields={
        "message_type": SchemaField(
            name="message_type",
            type=SchemaType.ENUM,
            required=True,
            enum_values=[mt.value for mt in MessageType],
            description="Type of the message"
        ),
        "content": SchemaField(
            name="content",
            type=SchemaType.OBJECT,
            required=True,
            description="Content of the message"
        ),
        "sender": SchemaField(
            name="sender",
            type=SchemaType.STRING,
            required=True,
            min_length=1,
            description="ID of the sender agent"
        ),
        "message_id": SchemaField(
            name="message_id",
            type=SchemaType.STRING,
            required=False,
            description="Unique ID of the message"
        ),
        "timestamp": SchemaField(
            name="timestamp",
            type=SchemaType.FLOAT,
            required=False,
            description="Timestamp when the message was created"
        ),
        "receiver": SchemaField(
            name="receiver",
            type=SchemaType.STRING,
            required=False,
            description="ID of the receiver agent (None for broadcast)"
        ),
        "parent_id": SchemaField(
            name="parent_id",
            type=SchemaType.STRING,
            required=False,
            description="ID of the parent message"
        ),
        "conversation_id": SchemaField(
            name="conversation_id",
            type=SchemaType.STRING,
            required=False,
            description="ID of the conversation this message belongs to"
        ),
        "confidence": SchemaField(
            name="confidence",
            type=SchemaType.FLOAT,
            required=False,
            min_value=0.0,
            max_value=1.0,
            description="Confidence level of the message (0.0-1.0)"
        ),
        "metadata": SchemaField(
            name="metadata",
            type=SchemaType.OBJECT,
            required=False,
            description="Additional metadata for the message"
        ),
        "schema_version": SchemaField(
            name="schema_version",
            type=SchemaType.STRING,
            required=False,
            default="1.1",
            description="Version of the message schema"
        ),
        "is_chunked": SchemaField(
            name="is_chunked",
            type=SchemaType.BOOLEAN,
            required=False,
            default=False,
            description="Whether this message is part of a chunked response"
        ),
        "chunk_id": SchemaField(
            name="chunk_id",
            type=SchemaType.STRING,
            required=False,
            description="ID of this chunk"
        ),
        "total_chunks": SchemaField(
            name="total_chunks",
            type=SchemaType.INTEGER,
            required=False,
            min_value=1,
            description="Total number of chunks in the complete response"
        ),
        "chunk_sequence": SchemaField(
            name="chunk_sequence",
            type=SchemaType.INTEGER,
            required=False,
            min_value=0,
            description="Position of this chunk in the sequence"
        ),
        "response_id": SchemaField(
            name="response_id",
            type=SchemaType.STRING,
            required=False,
            description="ID of the complete response this chunk belongs to"
        ),
        "compressed": SchemaField(
            name="compressed",
            type=SchemaType.BOOLEAN,
            required=False,
            default=False,
            description="Whether the message content is compressed"
        ),
        "problem_context": SchemaField(
            name="problem_context",
            type=SchemaType.OBJECT,
            required=False,
            default={},
            description="Context information about the problem being addressed"
        ),
        "analysis_results": SchemaField(
            name="analysis_results",
            type=SchemaType.OBJECT,
            required=False,
            default={},
            description="Results of analysis performed by agents"
        ),
        "suggested_actions": SchemaField(
            name="suggested_actions",
            type=SchemaType.ARRAY,
            required=False,
            default=[],
            item_type=SchemaField(
                name="action",
                type=SchemaType.OBJECT,
                required=True
            ),
            description="Actions suggested by agents"
        )
    }
)


def validate_message(message_data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate a message against the appropriate schema.
    
    Args:
        message_data: Message data to validate
        
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    # Determine schema version
    schema_version = message_data.get("schema_version", "1.1")
    
    # Select the appropriate schema
    if schema_version == "1.1":
        schema = MESSAGE_SCHEMA_V1_1
    else:
        return False, [f"Unsupported schema version: {schema_version}"]
    
    # Validate against the schema
    return schema.validate(message_data)


def get_default_values(schema_version: str = "1.1") -> Dict[str, Any]:
    """
    Get default values for message fields.
    
    Args:
        schema_version: Version of the schema to get defaults for
        
    Returns:
        Dictionary of default values
    """
    # Select the appropriate schema
    if schema_version == "1.1":
        schema = MESSAGE_SCHEMA_V1_1
    else:
        raise ValueError(f"Unsupported schema version: {schema_version}")
    
    # Extract default values
    defaults = {}
    for field_name, field_schema in schema.fields.items():
        if field_schema.default is not None:
            defaults[field_name] = field_schema.default
    
    return defaults


def convert_field_type(field_name: str, value: Any, schema_version: str = "1.1") -> Any:
    """
    Convert a field value to the correct type according to the schema.
    
    Args:
        field_name: Name of the field
        value: Value to convert
        schema_version: Version of the schema to use
        
    Returns:
        Converted value
    """
    # Select the appropriate schema
    if schema_version == "1.1":
        schema = MESSAGE_SCHEMA_V1_1
    else:
        raise ValueError(f"Unsupported schema version: {schema_version}")
    
    # Get the field schema
    field_schema = schema.fields.get(field_name)
    if field_schema is None:
        return value  # No schema for this field, return as is
    
    # Convert based on the field type
    try:
        if field_schema.type == SchemaType.STRING and not isinstance(value, str):
            return str(value)
        
        elif field_schema.type == SchemaType.INTEGER and not isinstance(value, int):
            if isinstance(value, float):
                return int(value)
            elif isinstance(value, str) and value.isdigit():
                return int(value)
        
        elif field_schema.type == SchemaType.FLOAT and not isinstance(value, float):
            if isinstance(value, int):
                return float(value)
            elif isinstance(value, str) and value.replace('.', '', 1).isdigit():
                return float(value)
        
        elif field_schema.type == SchemaType.BOOLEAN and not isinstance(value, bool):
            if isinstance(value, str):
                return value.lower() in ('true', 'yes', '1', 'y')
            elif isinstance(value, int):
                return value != 0
        
        elif field_schema.type == SchemaType.ENUM:
            # For MessageType enum
            if field_name == "message_type" and isinstance(value, str):
                return MessageType(value)
    
    except (ValueError, TypeError):
        # If conversion fails, return the original value
        pass
    
    return value


def export_schema_to_json(schema: MessageSchema, file_path: str) -> None:
    """
    Export a schema to a JSON file.
    
    Args:
        schema: Schema to export
        file_path: Path to the output file
    """
    # Convert schema to a JSON-serializable dictionary
    schema_dict = {
        "version": schema.version,
        "fields": {}
    }
    
    for field_name, field_schema in schema.fields.items():
        field_dict = {
            "type": field_schema.type.value,
            "required": field_schema.required,
            "description": field_schema.description
        }
        
        if field_schema.default is not None:
            field_dict["default"] = field_schema.default
        
        if field_schema.enum_values is not None:
            field_dict["enum_values"] = field_schema.enum_values
        
        if field_schema.min_value is not None:
            field_dict["min_value"] = field_schema.min_value
        
        if field_schema.max_value is not None:
            field_dict["max_value"] = field_schema.max_value
        
        if field_schema.min_length is not None:
            field_dict["min_length"] = field_schema.min_length
        
        if field_schema.max_length is not None:
            field_dict["max_length"] = field_schema.max_length
        
        if field_schema.pattern is not None:
            field_dict["pattern"] = field_schema.pattern
        
        if field_schema.item_type is not None:
            field_dict["item_type"] = {
                "type": field_schema.item_type.type.value,
                "required": field_schema.item_type.required
            }
        
        if field_schema.properties is not None:
            field_dict["properties"] = {}
            for prop_name, prop_schema in field_schema.properties.items():
                field_dict["properties"][prop_name] = {
                    "type": prop_schema.type.value,
                    "required": prop_schema.required
                }
        
        schema_dict["fields"][field_name] = field_dict
    
    # Write to file
    with open(file_path, 'w') as f:
        json.dump(schema_dict, f, indent=2)


def import_schema_from_json(file_path: str) -> MessageSchema:
    """
    Import a schema from a JSON file.
    
    Args:
        file_path: Path to the input file
        
    Returns:
        Imported schema
    """
    # Read from file
    with open(file_path, 'r') as f:
        schema_dict = json.load(f)
    
    # Convert to schema
    fields = {}
    
    for field_name, field_dict in schema_dict["fields"].items():
        # Create item type if present
        item_type = None
        if "item_type" in field_dict:
            item_type_dict = field_dict["item_type"]
            item_type = SchemaField(
                name=f"{field_name}_item",
                type=SchemaType(item_type_dict["type"]),
                required=item_type_dict["required"]
            )
        
        # Create properties if present
        properties = None
        if "properties" in field_dict:
            properties = {}
            for prop_name, prop_dict in field_dict["properties"].items():
                properties[prop_name] = SchemaField(
                    name=prop_name,
                    type=SchemaType(prop_dict["type"]),
                    required=prop_dict["required"]
                )
        
        # Create the field schema
        fields[field_name] = SchemaField(
            name=field_name,
            type=SchemaType(field_dict["type"]),
            required=field_dict["required"],
            default=field_dict.get("default"),
            enum_values=field_dict.get("enum_values"),
            min_value=field_dict.get("min_value"),
            max_value=field_dict.get("max_value"),
            min_length=field_dict.get("min_length"),
            max_length=field_dict.get("max_length"),
            pattern=field_dict.get("pattern"),
            item_type=item_type,
            properties=properties,
            description=field_dict.get("description")
        )
    
    return MessageSchema(
        version=schema_dict["version"],
        fields=fields
    )
