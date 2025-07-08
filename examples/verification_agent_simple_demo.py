#!/usr/bin/env python3
"""
Simplified Verification Agent Demo

This script demonstrates the basic functionality of the enhanced Verification Agent
without requiring the full system implementation. It helps verify that our changes
work properly.
"""

import os
import sys
import logging
from typing import Dict, Any

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.agents.message import MessageType
from triangulum_lx.core.exceptions import TriangulumException, VerificationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class SimpleVerificationAgent:
    """A simplified version of the Verification Agent for testing."""
    
    def __init__(self):
        """Initialize the agent."""
        self.environment_info = self._detect_environment()
        logger.info("Initialized Simple Verification Agent")
    
    def _detect_environment(self) -> Dict[str, Any]:
        """Detect the execution environment."""
        import platform
        
        environment_info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "available_tools": {},
            "python_packages": {}
        }
        
        # Detect some Python packages
        try:
            import pkg_resources
            for pkg in list(pkg_resources.working_set)[:10]:  # Get first 10 packages
                environment_info["python_packages"][pkg.key] = pkg.version
        except ImportError:
            pass
        
        return environment_info
    
    def verify_implementation(self, implementation: Dict[str, Any]) -> Dict[str, Any]:
        """Verify an implementation."""
        logger.info(f"Verifying implementation: {implementation.get('strategy_id', 'unknown')}")
        
        # Sample verification result
        result = {
            "implementation_id": implementation.get("strategy_id", "unknown"),
            "verification_id": "ver_" + implementation.get("strategy_id", "unknown"),
            "overall_success": True,
            "confidence": 0.85,
            "checks": {
                "syntax": {"success": True},
                "tests": {"success": True},
                "standards": {"success": True}
            },
            "issues": [],
            "recommendations": []
        }
        
        return result
    
    def generate_verification_id(self, implementation_id: str) -> str:
        """Generate a verification ID."""
        import hashlib
        import time
        
        # Create a verification ID based on the implementation ID and timestamp
        timestamp = str(int(time.time()))
        data = f"{implementation_id}:{timestamp}".encode('utf-8')
        hash_value = hashlib.sha256(data).hexdigest()[:12]
        
        return f"ver_{hash_value}"

def demonstrate_exception_handling():
    """Demonstrate exception handling with the new exception classes."""
    logger.info("\n=== Demonstrating Exception Handling ===")
    
    # Test TriangulumException
    try:
        raise TriangulumException("General Triangulum error")
    except TriangulumException as e:
        logger.info(f"Caught TriangulumException: {e}")
    
    # Test VerificationError
    try:
        raise VerificationError(
            message="Verification failed", 
            implementation_id="impl_12345",
            verification_stage="syntax_check",
            issues=["Syntax error on line 42"]
        )
    except VerificationError as e:
        logger.info(f"Caught VerificationError: {e}")
        logger.info(f"Implementation ID: {e.implementation_id}")
        logger.info(f"Verification Stage: {e.verification_stage}")
        logger.info(f"Issues: {e.issues}")

def demonstrate_message_types():
    """Demonstrate the available message types."""
    logger.info("\n=== Demonstrating Message Types ===")
    
    # Print all available message types
    logger.info("Available Message Types:")
    for msg_type in MessageType:
        logger.info(f"  - {msg_type.name}: {msg_type.value}")
    
    # Specifically check for STATUS_UPDATE
    try:
        status_update = MessageType.STATUS_UPDATE
        logger.info(f"SUCCESS: STATUS_UPDATE message type exists: {status_update.value}")
    except AttributeError:
        logger.error("FAILED: STATUS_UPDATE message type does not exist")

def main():
    """Main function to run the demonstration."""
    logger.info("Starting Simple Verification Agent Demo")
    
    # Demonstrate exception handling
    demonstrate_exception_handling()
    
    # Demonstrate message types
    demonstrate_message_types()
    
    # Create a simple verification agent
    agent = SimpleVerificationAgent()
    
    # Display environment information
    logger.info("\n=== Environment Information ===")
    logger.info(f"OS: {agent.environment_info['os']} {agent.environment_info['os_version']}")
    logger.info(f"Python Version: {agent.environment_info['python_version']}")
    logger.info(f"Platform: {agent.environment_info['platform']}")
    
    # Verify a sample implementation
    sample_implementation = {
        "strategy_id": "strategy_sample_12345",
        "bug_type": "null_pointer",
        "description": "Sample implementation for testing"
    }
    
    verification_result = agent.verify_implementation(sample_implementation)
    
    logger.info("\n=== Verification Result ===")
    logger.info(f"Implementation ID: {verification_result['implementation_id']}")
    logger.info(f"Verification ID: {verification_result['verification_id']}")
    logger.info(f"Overall Success: {verification_result['overall_success']}")
    logger.info(f"Confidence: {verification_result['confidence']}")
    
    # Show checks
    logger.info("\nChecks:")
    for check_name, check_result in verification_result['checks'].items():
        status = "✅" if check_result["success"] else "❌"
        logger.info(f"  - {check_name}: {status}")
    
    logger.info("\nSimple Verification Agent Demo completed successfully")

if __name__ == "__main__":
    main()
