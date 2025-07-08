"""
Message Schema Validator - Validates and enforces the agent message schema.

This module provides functionality to validate agent messages against the
standardized JSON schema, ensuring compliance with the communication protocol.
It implements comprehensive validation for all message types, with detailed error
messages and support for schema versioning.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional, List, Tuple, Union, Set
import jsonschema
from jsonschema import validators, Draft7Validator

from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.core.exceptions import TriangulumValidationError

logger = logging.getLogger(__name__)

class MessageSchemaValidator:
    """
    Validator for agent messages based on the standardized JSON schema.
    
    This class loads the schema from the message_schema.json file and provides
    methods to validate messages against the schema, ensuring they follow the
    standardized communication protocol. It includes comprehensive validation for
    all message types, with detailed error messages and support for schema versioning.
    
    Features:
    - Full validation against JSON schema
    - Additional validation for specific message types
    - Detailed error messages with context
    - Support for schema versioning
    - Performance optimized validation
    - Template generation for all message types
    """
    
    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize the message schema validator.
        
        Args:
            schema_path: Optional custom path to the schema file. If not provided,
                         the default schema path will be used.
        """
        self._schema = self._load_schema(schema_path)
        self._validator = self._create_validator()
        self._cached_validators: Dict[str, Draft7Validator] = {}
        self._message_type_validators: Dict[MessageType, Dict[str, Any]] = self._create_message_type_validators()
        
    def _load_schema(self, custom_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load the message schema from the JSON file.
        
        Args:
            custom_path: Optional custom path to the schema file
            
        Returns:
            Dict[str, Any]: The loaded schema
            
        Raises:
            TriangulumValidationError: If the schema file is not found or cannot be parsed
        """
        schema_path = custom_path or os.path.join(os.path.dirname(__file__), "message_schema.json")
        try:
            with open(schema_path, "r") as f:
                schema = json.load(f)
                logger.debug(f"Loaded message schema from {schema_path}")
                
                # Validate the schema itself is a valid JSON Schema
                try:
                    validators.validator_for(schema)
                    logger.debug("Schema is a valid JSON Schema")
                except Exception as schema_e:
                    logger.warning(f"Schema validation warning: {schema_e}")
                
                return schema
        except FileNotFoundError as e:
            error_msg = f"Failed to load message schema - file not found: {schema_path}"
            logger.error(error_msg)
            # Fall back to a minimal schema to avoid breaking everything
            fallback_schema = {
                "type": "object",
                "required": ["message_type", "content", "sender", "message_id", "timestamp"],
                "properties": {
                    "message_type": {"type": "string"},
                    "content": {"type": "object"},
                    "sender": {"type": "string"},
                    "message_id": {"type": "string"},
                    "timestamp": {"type": "number"}
                }
            }
            logger.warning("Using fallback minimal schema")
            return fallback_schema
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse message schema - invalid JSON: {e}"
            logger.error(error_msg)
            raise TriangulumValidationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error loading message schema: {e}"
            logger.error(error_msg)
            raise TriangulumValidationError(error_msg) from e
    
    def _create_validator(self) -> Draft7Validator:
        """
        Create a JSON Schema validator for the loaded schema.
        
        Returns:
            Draft7Validator: The schema validator
        """
        return Draft7Validator(self._schema)
    
    def _create_message_type_validators(self) -> Dict[MessageType, Dict[str, Any]]:
        """
        Create validators specific to each message type.
        
        Returns:
            Dict[MessageType, Dict[str, Any]]: Mapping of message types to their validation rules
        """
        # Define specific validation rules for each message type
        validators = {}
        
        # TASK_REQUEST validation
        validators[MessageType.TASK_REQUEST] = {
            "required_content_fields": ["task"],
            "optional_content_fields": ["parameters", "context", "priority", "timeout"],
            "common_errors": {
                "missing_task": "TASK_REQUEST messages must include a 'task' field in content",
                "invalid_priority": "Priority must be one of: low, medium, high, critical"
            }
        }
        
        # TASK_RESULT validation
        validators[MessageType.TASK_RESULT] = {
            "required_content_fields": ["result"],
            "optional_content_fields": ["execution_time", "status", "errors"],
            "common_errors": {
                "missing_result": "TASK_RESULT messages must include a 'result' field in content",
                "invalid_status": "Status must be one of: success, failure, partial_success"
            }
        }
        
        # QUERY validation
        validators[MessageType.QUERY] = {
            "required_content_fields": ["query"],
            "optional_content_fields": ["query_type", "parameters", "context"],
            "common_errors": {
                "missing_query": "QUERY messages must include a 'query' field in content"
            }
        }
        
        # QUERY_RESPONSE validation
        validators[MessageType.QUERY_RESPONSE] = {
            "required_content_fields": ["response"],
            "optional_content_fields": ["query_id", "status", "data"],
            "common_errors": {
                "missing_response": "QUERY_RESPONSE messages must include a 'response' field in content"
            }
        }
        
        # CODE_ANALYSIS validation
        validators[MessageType.CODE_ANALYSIS] = {
            "required_content_fields": ["analysis"],
            "optional_content_fields": ["file_path", "issues", "metrics", "summary"],
            "common_errors": {
                "missing_analysis": "CODE_ANALYSIS messages must include an 'analysis' field in content"
            }
        }
        
        # PROBLEM_ANALYSIS validation
        validators[MessageType.PROBLEM_ANALYSIS] = {
            "required_content_fields": ["problem", "analysis"],
            "optional_content_fields": ["causes", "impact", "severity"],
            "common_errors": {
                "missing_problem": "PROBLEM_ANALYSIS messages must include a 'problem' field in content",
                "missing_analysis": "PROBLEM_ANALYSIS messages must include an 'analysis' field in content"
            }
        }
        
        # RELATIONSHIP_ANALYSIS validation
        validators[MessageType.RELATIONSHIP_ANALYSIS] = {
            "required_content_fields": ["relationships"],
            "optional_content_fields": ["entity_type", "strength", "direction", "context"],
            "common_errors": {
                "missing_relationships": "RELATIONSHIP_ANALYSIS messages must include a 'relationships' field in content"
            }
        }
        
        # REPAIR_SUGGESTION validation
        validators[MessageType.REPAIR_SUGGESTION] = {
            "required_content_fields": ["suggestion"],
            "required_top_level_fields": ["suggested_actions"],
            "common_errors": {
                "missing_suggestion": "REPAIR_SUGGESTION messages must include a 'suggestion' field in content",
                "missing_suggested_actions": "REPAIR_SUGGESTION messages must include a 'suggested_actions' field at the top level"
            }
        }
        
        # VERIFICATION_RESULT validation
        validators[MessageType.VERIFICATION_RESULT] = {
            "required_content_fields": ["verified", "result"],
            "optional_content_fields": ["tests_passed", "tests_failed", "coverage"],
            "common_errors": {
                "missing_verified": "VERIFICATION_RESULT messages must include a 'verified' field in content",
                "missing_result": "VERIFICATION_RESULT messages must include a 'result' field in content"
            }
        }
        
        # ERROR validation
        validators[MessageType.ERROR] = {
            "required_content_fields": ["error"],
            "optional_content_fields": ["error_type", "details", "recoverable", "source"],
            "common_errors": {
                "missing_error": "ERROR messages must include an 'error' field in content"
            }
        }
        
        # STATUS validation
        validators[MessageType.STATUS] = {
            "required_content_fields": ["status"],
            "optional_content_fields": ["details", "progress", "timestamp"],
            "common_errors": {
                "missing_status": "STATUS messages must include a 'status' field in content"
            }
        }
        
        # LOG validation
        validators[MessageType.LOG] = {
            "required_content_fields": ["message"],
            "optional_content_fields": ["level", "source", "timestamp", "data"],
            "common_errors": {
                "missing_message": "LOG messages must include a 'message' field in content"
            }
        }
        
        return validators
    
    def validate_message(self, message: AgentMessage) -> Tuple[bool, Optional[str]]:
        """
        Validate a message against the schema.
        
        Args:
            message: The message to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
            
        Notes:
            This method provides a convenient boolean return value to check
            if a message is valid, along with any error message. For more 
            detailed validation with full error context, use validate_message_detailed.
        """
        try:
            result = self.validate_message_detailed(message)
            return result["valid"], result.get("error")
        except Exception as e:
            error_message = f"Unexpected error during message validation: {str(e)}"
            logger.error(error_message)
            return False, error_message
    
    def validate_message_detailed(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Validate a message against the schema with detailed error information.
        
        Args:
            message: The message to validate
            
        Returns:
            Dict[str, Any]: Validation results with the following structure:
                {
                    "valid": bool,  # Whether the message is valid
                    "message_id": str,  # ID of the validated message
                    "message_type": str,  # Type of the validated message
                    "schema_version": str,  # Schema version used for validation
                    "errors": List[Dict],  # List of validation errors (if any)
                    "error": str,  # Summary error message (if any)
                    "warnings": List[str],  # List of validation warnings (if any)
                    "validation_time_ms": float  # Time taken for validation in milliseconds
                }
        """
        start_time = time.time()
        
        # Initialize the result
        result = {
            "valid": True,
            "message_id": getattr(message, "message_id", "unknown"),
            "message_type": message.message_type.value if hasattr(message, "message_type") else "unknown",
            "schema_version": self.get_schema_version(),
            "errors": [],
            "warnings": [],
            "validation_time_ms": 0
        }
        
        try:
            # Convert message to dictionary for validation
            message_dict = message.to_dict()
            
            # Step 1: Validate required fields
            missing_required = self._validate_required_fields(message_dict)
            if missing_required:
                result["valid"] = False
                result["errors"].append({
                    "type": "missing_required_fields",
                    "fields": missing_required,
                    "message": f"Missing required fields: {', '.join(missing_required)}"
                })
            
            # Step 2: Validate against JSON schema
            schema_errors = list(self._validator.iter_errors(message_dict))
            if schema_errors:
                result["valid"] = False
                for error in schema_errors:
                    result["errors"].append({
                        "type": "schema_validation",
                        "path": ".".join(str(p) for p in error.path) if error.path else None,
                        "message": error.message,
                        "context": [c.message for c in error.context] if hasattr(error, "context") else None,
                        "schema_path": ".".join(str(p) for p in error.schema_path) if hasattr(error, "schema_path") else None
                    })
            
            # Step 3: Validate message type specific requirements
            content_validation_errors = self._validate_message_content_detailed(message)
            if content_validation_errors:
                result["valid"] = False
                result["errors"].extend(content_validation_errors)
            
            # Step 4: Validate nested properties based on message type
            nested_errors = self._validate_nested_properties(message)
            if nested_errors:
                result["valid"] = False
                result["errors"].extend(nested_errors)
            
            # Add summary error message if there are errors
            if result["errors"]:
                result["error"] = f"Message validation failed with {len(result['errors'])} errors"
            
            # Performance check - add warning if validation took too long
            validation_time = (time.time() - start_time) * 1000  # in milliseconds
            if validation_time > 100:  # warn if validation takes more than 100ms
                result["warnings"].append(f"Validation performance warning: took {validation_time:.2f}ms")
            
            result["validation_time_ms"] = validation_time
            return result
            
        except jsonschema.exceptions.SchemaError as e:
            # This happens when the schema itself is invalid
            logger.error(f"Invalid schema: {e}")
            result["valid"] = False
            result["errors"].append({
                "type": "schema_error",
                "message": f"Schema validation error: {e.message}",
                "path": ".".join(str(p) for p in e.path) if hasattr(e, "path") else None
            })
            result["error"] = "Schema definition error"
        except Exception as e:
            # Handle any other unexpected errors
            logger.error(f"Unexpected validation error: {e}")
            result["valid"] = False
            result["errors"].append({
                "type": "validation_error",
                "message": f"Unexpected error during validation: {str(e)}"
            })
            result["error"] = "Unexpected validation error"
        
        # Calculate validation time if we hit an exception
        result["validation_time_ms"] = (time.time() - start_time) * 1000
        return result
    
    def _validate_required_fields(self, message_dict: Dict[str, Any]) -> List[str]:
        """
        Validate that all required fields are present in the message.
        
        Args:
            message_dict: Dictionary representation of the message
            
        Returns:
            List[str]: List of missing required fields, empty if all required fields are present
        """
        missing = []
        
        # Check top-level required fields from schema
        for field in self._schema.get("required", []):
            if field not in message_dict:
                missing.append(field)
        
        # Check message type specific required fields
        if "message_type" in message_dict:
            message_type_str = message_dict["message_type"]
            try:
                message_type = MessageType(message_type_str)
                if message_type in self._message_type_validators:
                    validator = self._message_type_validators[message_type]
                    
                    # Check required content fields
                    if "content" in message_dict and "required_content_fields" in validator:
                        content = message_dict["content"]
                        for field in validator["required_content_fields"]:
                            if field not in content:
                                missing.append(f"content.{field}")
                    
                    # Check required top-level fields specific to this message type
                    if "required_top_level_fields" in validator:
                        for field in validator["required_top_level_fields"]:
                            if field not in message_dict:
                                missing.append(field)
            except ValueError:
                # Invalid message type
                missing.append("valid_message_type")
        
        return missing
    
    def _validate_message_content_detailed(self, message: AgentMessage) -> List[Dict[str, Any]]:
        """
        Perform detailed validation on message content based on message type.
        
        Args:
            message: The message to validate
            
        Returns:
            List[Dict[str, Any]]: List of validation errors, empty if content is valid
        """
        errors = []
        
        if not hasattr(message, "message_type") or not hasattr(message, "content"):
            errors.append({
                "type": "structural_error",
                "message": "Message missing required attributes 'message_type' or 'content'"
            })
            return errors
        
        # Get the message type
        message_type = message.message_type
        
        # Skip validation if we don't have specific validation rules for this message type
        if message_type not in self._message_type_validators:
            return []
        
        # Get the validator for this message type
        validator = self._message_type_validators[message_type]
        
        # Check required content fields
        for field in validator.get("required_content_fields", []):
            if field not in message.content:
                error_key = f"missing_{field}"
                error_msg = validator.get("common_errors", {}).get(
                    error_key,
                    f"Messages of type {message_type.value} must include a '{field}' field in content"
                )
                errors.append({
                    "type": "content_validation",
                    "field": field,
                    "message": error_msg
                })
        
        # Check field value constraints (where applicable)
        if message_type == MessageType.TASK_REQUEST and "priority" in message.content:
            priority = message.content["priority"]
            if priority not in ["low", "medium", "high", "critical"]:
                errors.append({
                    "type": "content_validation",
                    "field": "priority",
                    "message": validator["common_errors"]["invalid_priority"],
                    "value": priority
                })
        
        if message_type == MessageType.TASK_RESULT and "status" in message.content:
            status = message.content["status"]
            if status not in ["success", "failure", "partial_success"]:
                errors.append({
                    "type": "content_validation",
                    "field": "status",
                    "message": validator["common_errors"]["invalid_status"],
                    "value": status
                })
        
        return errors
    
    def _validate_nested_properties(self, message: AgentMessage) -> List[Dict[str, Any]]:
        """
        Validate nested properties in the message based on message type.
        
        Args:
            message: The message to validate
            
        Returns:
            List[Dict[str, Any]]: List of validation errors, empty if all nested properties are valid
        """
        errors = []
        
        # For REPAIR_SUGGESTION messages, validate suggested_actions
        if message.message_type == MessageType.REPAIR_SUGGESTION:
            if hasattr(message, "suggested_actions"):
                actions = message.suggested_actions
                
                # Check if it's a list
                if not isinstance(actions, list):
                    errors.append({
                        "type": "nested_validation",
                        "field": "suggested_actions",
                        "message": "suggested_actions must be a list"
                    })
                else:
                    # Validate each action
                    for i, action in enumerate(actions):
                        if not isinstance(action, dict):
                            errors.append({
                                "type": "nested_validation",
                                "field": f"suggested_actions[{i}]",
                                "message": "Each action must be a dictionary"
                            })
                        else:
                            # Check required fields in each action
                            for field in ["action_type", "description"]:
                                if field not in action:
                                    errors.append({
                                        "type": "nested_validation",
                                        "field": f"suggested_actions[{i}].{field}",
                                        "message": f"Each action must include a '{field}' field"
                                    })
                            
                            # Validate action_type values
                            if "action_type" in action and action["action_type"] not in [
                                "code_change", "test_addition", "refactor", 
                                "dependency_update", "configuration_change", "further_analysis"
                            ]:
                                errors.append({
                                    "type": "nested_validation",
                                    "field": f"suggested_actions[{i}].action_type",
                                    "message": "action_type must be one of: code_change, test_addition, refactor, dependency_update, configuration_change, further_analysis",
                                    "value": action["action_type"]
                                })
            else:
                errors.append({
                    "type": "nested_validation",
                    "field": "suggested_actions",
                    "message": "REPAIR_SUGGESTION messages must include a suggested_actions field"
                })
        
        # For PROBLEM_ANALYSIS or CODE_ANALYSIS messages, validate analysis_results if present
        if message.message_type in [MessageType.PROBLEM_ANALYSIS, MessageType.CODE_ANALYSIS]:
            if hasattr(message, "analysis_results") and message.analysis_results:
                analysis = message.analysis_results
                
                # Check if it's a dict
                if not isinstance(analysis, dict):
                    errors.append({
                        "type": "nested_validation",
                        "field": "analysis_results",
                        "message": "analysis_results must be a dictionary"
                    })
                else:
                    # Validate severity if present
                    if "severity" in analysis and analysis["severity"] not in [
                        "low", "medium", "high", "critical", None
                    ]:
                        errors.append({
                            "type": "nested_validation",
                            "field": "analysis_results.severity",
                            "message": "severity must be one of: low, medium, high, critical, or null",
                            "value": analysis["severity"]
                        })
        
        return errors
    
    def generate_message_template(self, message_type: MessageType) -> Dict[str, Any]:
        """
        Generate a template for a message of the specified type.
        
        Args:
            message_type: The type of message to generate a template for
            
        Returns:
            Dict[str, Any]: A template with the required fields for the message type
        """
        # Base template that all messages share
        template = {
            "message_type": message_type.value,
            "content": {},
            "sender": "",
            "receiver": None,
            "message_id": "00000000-0000-0000-0000-000000000000",  # Placeholder for UUID
            "timestamp": int(time.time()),
            "conversation_id": "00000000-0000-0000-0000-000000000000",  # Placeholder for UUID
            "parent_id": None,
            "schema_version": self.get_schema_version(),
            "metadata": {},
            "problem_context": {},
            "analysis_results": {},
            "suggested_actions": []
        }
        
        # Add message type specific content fields
        if message_type == MessageType.TASK_REQUEST:
            template["content"] = {
                "task": "",
                "parameters": {},
                "context": {},
                "priority": "medium",
                "timeout": None
            }
            
        elif message_type == MessageType.TASK_RESULT:
            template["content"] = {
                "result": "",
                "execution_time": 0,
                "status": "success",
                "errors": []
            }
            
        elif message_type == MessageType.QUERY:
            template["content"] = {
                "query": "",
                "query_type": "",
                "parameters": {},
                "context": {}
            }
            
        elif message_type == MessageType.QUERY_RESPONSE:
            template["content"] = {
                "response": "",
                "query_id": None,
                "status": "success",
                "data": {}
            }
            
        elif message_type == MessageType.CODE_ANALYSIS:
            template["content"] = {
                "analysis": "",
                "file_path": None,
                "issues": [],
                "metrics": {},
                "summary": ""
            }
            template["analysis_results"] = {
                "error_type": None,
                "error_cause": None,
                "affected_code": None,
                "severity": None,
                "impact": None
            }
            
        elif message_type == MessageType.PROBLEM_ANALYSIS:
            template["content"] = {
                "problem": "",
                "analysis": "",
                "causes": [],
                "impact": "",
                "severity": "medium"
            }
            
        elif message_type == MessageType.RELATIONSHIP_ANALYSIS:
            template["content"] = {
                "relationships": [],
                "entity_type": "",
                "strength": 0.5,
                "direction": "bidirectional",
                "context": {}
            }
            
        elif message_type == MessageType.REPAIR_SUGGESTION:
            template["content"] = {
                "suggestion": "",
                "confidence": 0.8
            }
            template["suggested_actions"] = [{
                "action_type": "code_change",
                "description": "",
                "file": None,
                "line": None,
                "original": None,
                "replacement": None,
                "rationale": ""
            }]
            
        elif message_type == MessageType.VERIFICATION_RESULT:
            template["content"] = {
                "verified": False,
                "result": "",
                "tests_passed": 0,
                "tests_failed": 0,
                "coverage": 0.0
            }
            
        elif message_type == MessageType.ERROR:
            template["content"] = {
                "error": "",
                "error_type": "",
                "details": {},
                "recoverable": True,
                "source": ""
            }
            
        elif message_type == MessageType.STATUS:
            template["content"] = {
                "status": "",
                "details": {},
                "progress": 0.0,
                "timestamp": int(time.time())
            }
            
        elif message_type == MessageType.LOG:
            template["content"] = {
                "message": "",
                "level": "info",
                "source": "",
                "timestamp": int(time.time()),
                "data": {}
            }
        
        return template
    
    def get_schema_version(self) -> str:
        """
        Get the current schema version.
        
        Returns:
            str: The current schema version
        """
        return self._schema.get("properties", {}).get("schema_version", {}).get("enum", ["1.0"])[-1]
    
    def get_required_fields(self, message_type: Optional[MessageType] = None) -> List[str]:
        """
        Get the required fields for a message type.
        
        Args:
            message_type: The type of message to get required fields for,
                          or None to get the fields required for all messages
            
        Returns:
            List[str]: The required fields
        """
        # Fields required for all messages
        required_fields = self._schema.get("required", [])
        
        # Additional fields required for specific message types
        if message_type:
            if message_type == MessageType.TASK_REQUEST:
                required_fields.append("content.task")
                
            elif message_type == MessageType.TASK_RESULT:
                required_fields.append("content.result")
                
            elif message_type == MessageType.QUERY:
                required_fields.append("content.query")
                
            elif message_type == MessageType.QUERY_RESPONSE:
                required_fields.append("content.response")
                
            elif message_type == MessageType.CODE_ANALYSIS:
                required_fields.append("content.analysis")
                
            elif message_type == MessageType.REPAIR_SUGGESTION:
                required_fields.append("content.suggestion")
                required_fields.append("suggested_actions")
        
        return required_fields


# Singleton instance for global use
message_schema_validator = MessageSchemaValidator()
