#!/usr/bin/env python3
"""
Triangulum Exception Hierarchy

This module defines the exception hierarchy for the Triangulum system,
providing specialized exceptions for different types of failures and errors.
"""

from typing import Optional, Dict, Any, List


class TriangulumException(Exception):
    """Base exception class for all Triangulum exceptions."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)
    
    def __str__(self) -> str:
        """String representation of the exception."""
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class StartupError(TriangulumException):
    """Exception raised for errors during system startup."""
    
    def __init__(self, message: str, component: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialize the startup error.
        
        Args:
            message: Error message
            component: Component that failed to start
            details: Additional error details
        """
        self.component = component
        if component:
            details = details or {}
            details["component"] = component
        super().__init__(message, details)


class ShutdownError(TriangulumException):
    """Exception raised for errors during system shutdown."""
    
    def __init__(self, message: str, component: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialize the shutdown error.
        
        Args:
            message: Error message
            component: Component that failed to shut down
            details: Additional error details
        """
        self.component = component
        if component:
            details = details or {}
            details["component"] = component
        super().__init__(message, details)


class ComponentInitError(StartupError):
    """Exception raised for errors during component initialization."""
    
    def __init__(self, message: str, component: str, 
                 details: Optional[Dict[str, Any]] = None,
                 cause: Optional[Exception] = None):
        """
        Initialize the component initialization error.
        
        Args:
            message: Error message
            component: Component that failed to initialize
            details: Additional error details
            cause: Original exception that caused this error
        """
        self.cause = cause
        if cause:
            details = details or {}
            details["cause"] = str(cause)
        super().__init__(message, component, details)


class ProviderInitError(ComponentInitError):
    """Exception raised for errors during provider initialization."""
    
    def __init__(self, message: str, provider: str, 
                 details: Optional[Dict[str, Any]] = None,
                 cause: Optional[Exception] = None):
        """
        Initialize the provider initialization error.
        
        Args:
            message: Error message
            provider: Provider that failed to initialize
            details: Additional error details
            cause: Original exception that caused this error
        """
        self.provider = provider
        component = f"provider:{provider}"
        super().__init__(message, component, details, cause)


class AgentInitError(ComponentInitError):
    """Exception raised for errors during agent initialization."""
    
    def __init__(self, message: str, agent_type: str, 
                 details: Optional[Dict[str, Any]] = None,
                 cause: Optional[Exception] = None):
        """
        Initialize the agent initialization error.
        
        Args:
            message: Error message
            agent_type: Agent type that failed to initialize
            details: Additional error details
            cause: Original exception that caused this error
        """
        self.agent_type = agent_type
        component = f"agent:{agent_type}"
        super().__init__(message, component, details, cause)


class ConfigurationError(StartupError):
    """Exception raised for errors in system configuration."""
    
    def __init__(self, message: str, 
                 invalid_sections: Optional[List[str]] = None,
                 missing_sections: Optional[List[str]] = None,
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialize the configuration error.
        
        Args:
            message: Error message
            invalid_sections: List of invalid configuration sections
            missing_sections: List of missing configuration sections
            details: Additional error details
        """
        self.invalid_sections = invalid_sections or []
        self.missing_sections = missing_sections or []
        
        details = details or {}
        if invalid_sections:
            details["invalid_sections"] = invalid_sections
        if missing_sections:
            details["missing_sections"] = missing_sections
        
        super().__init__(message, "configuration", details)


class DependencyError(StartupError):
    """Exception raised for errors in component dependencies."""
    
    def __init__(self, message: str, component: str, 
                 dependencies: Optional[List[str]] = None,
                 circular: Optional[List[str]] = None,
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialize the dependency error.
        
        Args:
            message: Error message
            component: Component with dependency issues
            dependencies: List of missing dependencies
            circular: List of components in a circular dependency
            details: Additional error details
        """
        self.dependencies = dependencies or []
        self.circular = circular or []
        
        details = details or {}
        if dependencies:
            details["dependencies"] = dependencies
        if circular:
            details["circular"] = circular
        
        super().__init__(message, component, details)


class ComponentNotFoundError(StartupError):
    """Exception raised when a required component is not found."""
    
    def __init__(self, message: str, component: str, 
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialize the component not found error.
        
        Args:
            message: Error message
            component: Component that was not found
            details: Additional error details
        """
        super().__init__(message, component, details)


class SystemHealthError(TriangulumException):
    """Exception raised for errors in system health checks."""
    
    def __init__(self, message: str, 
                 failed_components: Optional[List[str]] = None,
                 health_status: Optional[Dict[str, Any]] = None,
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialize the system health error.
        
        Args:
            message: Error message
            failed_components: List of failed components
            health_status: Health status of the system
            details: Additional error details
        """
        self.failed_components = failed_components or []
        self.health_status = health_status or {}
        
        details = details or {}
        if failed_components:
            details["failed_components"] = failed_components
        if health_status:
            details["health_status"] = health_status
        
        super().__init__(message, details)


class TriangulumValidationError(TriangulumException):
    """Exception raised for validation errors in Triangulum."""
    
    def __init__(self, message: str, 
                 field: Optional[str] = None,
                 schema_path: Optional[str] = None,
                 value: Optional[Any] = None,
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialize the validation error.
        
        Args:
            message: Error message
            field: Field that failed validation
            schema_path: Path in the schema where validation failed
            value: Value that failed validation
            details: Additional error details
        """
        self.field = field
        self.schema_path = schema_path
        self.value = value
        
        details = details or {}
        if field:
            details["field"] = field
        if schema_path:
            details["schema_path"] = schema_path
        if value is not None:
            details["value"] = value
        
        super().__init__(message, details)


# Alias for backward compatibility
TriangulumError = TriangulumException


class VerificationError(TriangulumException):
    """Exception raised for errors during verification process."""
    
    def __init__(self, message: str, 
                 implementation_id: Optional[str] = None,
                 verification_stage: Optional[str] = None,
                 issues: Optional[List[str]] = None,
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialize the verification error.
        
        Args:
            message: Error message
            implementation_id: ID of the implementation being verified
            verification_stage: Stage where verification failed
            issues: List of verification issues
            details: Additional error details
        """
        self.implementation_id = implementation_id
        self.verification_stage = verification_stage
        self.issues = issues or []
        
        details = details or {}
        if implementation_id:
            details["implementation_id"] = implementation_id
        if verification_stage:
            details["verification_stage"] = verification_stage
        if issues:
            details["issues"] = issues
        
        super().__init__(message, details)


class ImplementationError(TriangulumException):
    """Exception raised for errors during implementation process."""
    
    def __init__(self, message: str, 
                 strategy_id: Optional[str] = None,
                 bug_type: Optional[str] = None,
                 implementation_stage: Optional[str] = None,
                 issues: Optional[List[str]] = None,
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialize the implementation error.
        
        Args:
            message: Error message
            strategy_id: ID of the strategy being implemented
            bug_type: Type of bug being fixed
            implementation_stage: Stage where implementation failed
            issues: List of implementation issues
            details: Additional error details
        """
        self.strategy_id = strategy_id
        self.bug_type = bug_type
        self.implementation_stage = implementation_stage
        self.issues = issues or []
        
        details = details or {}
        if strategy_id:
            details["strategy_id"] = strategy_id
        if bug_type:
            details["bug_type"] = bug_type
        if implementation_stage:
            details["implementation_stage"] = implementation_stage
        if issues:
            details["issues"] = issues
        
        super().__init__(message, details)
