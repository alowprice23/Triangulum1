#!/usr/bin/env python3
"""
Enhanced Verification Agent Demo

This script demonstrates the enhanced Verification Agent's capabilities:
- Multi-stage verification with progressive validation
- Advanced test discovery and execution
- Runtime environment detection
- Detailed verification metrics and reporting
- Support for different verification environments
"""

import os
import sys
import json
import logging
import time
from typing import Dict, Any

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.agents.verification_agent import VerificationAgent
from triangulum_lx.agents.implementation_agent import ImplementationAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Sample implementation for demonstration
SAMPLE_IMPLEMENTATION = {
    "strategy_id": "strategy_null_pointer_12345",
    "bug_type": "null_pointer",
    "bug_location": "example_files/null_pointer_example.py",
    "description": "Add null check to prevent NoneType error",
    "patches": [
        {
            "file_path": "example_files/null_pointer_example.py",
            "changes": [
                {
                    "type": "replace_lines",
                    "start_line": 12,
                    "end_line": 12,
                    "content": "    # Add null check to prevent NoneType error\n    profile = user.get_profile()\n    if profile is not None:\n        result = profile.get_settings()\n    else:\n        result = None"
                }
            ]
        }
    ],
    "timestamp": "2025-07-03T21:00:00.000000"
}

def setup_example_files():
    """Create example files for the demonstration."""
    os.makedirs("example_files", exist_ok=True)
    
    # Null pointer example
    with open("example_files/null_pointer_example.py", "w") as f:
        f.write("""class User:
    def __init__(self, name):
        self.name = name
        self.profile = None
    
    def get_profile(self):
        return self.profile

def process_user_settings(user):
    # Bug: user.get_profile() might return None
    result = user.get_profile().get_settings()
    return result

user = User("Alice")
process_user_settings(user)  # This will cause a NoneType error
""")
    
    # Create a test file for the null pointer example
    os.makedirs("example_files/tests", exist_ok=True)
    with open("example_files/tests/test_null_pointer_example.py", "w") as f:
        f.write("""import unittest
from example_files.null_pointer_example import User, process_user_settings

class TestUserSettings(unittest.TestCase):
    def test_process_user_settings_with_profile(self):
        # Create a user with a profile
        class Profile:
            def get_settings(self):
                return {"theme": "dark"}
        
        user = User("Bob")
        user.profile = Profile()
        
        # Process settings should work
        result = process_user_settings(user)
        self.assertEqual(result, {"theme": "dark"})
    
    def test_process_user_settings_without_profile(self):
        # Create a user without a profile
        user = User("Charlie")
        
        # Process settings should handle None profile
        result = process_user_settings(user)
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
""")

def demonstrate_environment_detection():
    """Demonstrate environment detection capabilities."""
    logger.info("\n=== Demonstrating Environment Detection ===")
    
    agent = VerificationAgent()
    env_info = agent.environment_info
    
    logger.info(f"Detected OS: {env_info['os']} {env_info['os_version']}")
    logger.info(f"Python Version: {env_info['python_version']}")
    logger.info(f"Platform: {env_info['platform']}")
    
    logger.info("Available tools:")
    for tool, details in env_info["available_tools"].items():
        if details.get("available", False):
            logger.info(f"  - {tool}: {details.get('version', 'unknown version')}")
    
    logger.info(f"Python packages: {len(env_info['python_packages'])} installed")
    logger.info(f"Some key packages: " + 
                ", ".join(f"{k}={v}" for k, v in list(env_info['python_packages'].items())[:5]))

def demonstrate_staged_verification():
    """Demonstrate the staged verification process."""
    logger.info("\n=== Demonstrating Staged Verification ===")
    
    agent = VerificationAgent(config={
        "staged_verification": True,
        "verification_data_dir": "example_files/.verification"
    })
    
    # Verify the implementation with staged verification
    verification_result = agent.verify_implementation(
        implementation=SAMPLE_IMPLEMENTATION,
        staged=True
    )
    
    # Report on the verification stages
    logger.info(f"Verification ID: {verification_result['verification_id']}")
    logger.info(f"Overall success: {verification_result['overall_success']}")
    logger.info(f"Confidence: {verification_result['confidence']:.2f}")
    logger.info(f"Verification time: {verification_result['verification_time']:.2f} seconds")
    
    # Show details of each stage
    logger.info("\nStage Results:")
    for stage_name, stage_result in verification_result["stages"].items():
        logger.info(f"  - {stage_name}: {'✅' if stage_result['success'] else '❌'}")
        logger.info(f"    Duration: {stage_result['duration']:.2f} seconds")
        
        # Show checks for this stage
        for check_name, check_result in stage_result["checks"].items():
            check_status = "✅" if check_result["success"] else "❌"
            logger.info(f"    - {check_name}: {check_status}")
        
        # Show issues if any
        if stage_result["issues"]:
            logger.info(f"    Issues:")
            for issue in stage_result["issues"]:
                logger.info(f"      * {issue}")
    
    # Show overall metrics
    logger.info("\nVerification Metrics:")
    metrics = verification_result["metrics"]
    logger.info(f"  Total checks: {metrics['total_checks']}")
    logger.info(f"  Passed checks: {metrics['passed_checks']}")
    logger.info(f"  Failed checks: {metrics['failed_checks']}")
    
    return verification_result

def demonstrate_traditional_verification():
    """Demonstrate the traditional (non-staged) verification process."""
    logger.info("\n=== Demonstrating Traditional Verification ===")
    
    agent = VerificationAgent()
    
    # Verify the implementation without staged verification
    verification_result = agent.verify_implementation(
        implementation=SAMPLE_IMPLEMENTATION,
        staged=False
    )
    
    logger.info(f"Verification ID: {verification_result['verification_id']}")
    logger.info(f"Overall success: {verification_result['overall_success']}")
    logger.info(f"Confidence: {verification_result['confidence']:.2f}")
    
    # Show individual checks
    logger.info("\nCheck Results:")
    for check_name, check_result in verification_result["checks"].items():
        check_status = "✅" if check_result["success"] else "❌"
        logger.info(f"  - {check_name}: {check_status}")
    
    # Show issues if any
    if verification_result["issues"]:
        logger.info("\nIssues:")
        for issue in verification_result["issues"]:
            logger.info(f"  * {issue}")
    
    # Show recommendations if any
    if verification_result["recommendations"]:
        logger.info("\nRecommendations:")
        for recommendation in verification_result["recommendations"]:
            logger.info(f"  * {recommendation}")
    
    return verification_result

def demonstrate_verification_metrics():
    """Demonstrate verification metrics collection."""
    logger.info("\n=== Demonstrating Verification Metrics ===")
    
    agent = VerificationAgent()
    
    # Run multiple verifications to collect metrics
    implementations = [
        SAMPLE_IMPLEMENTATION,
        # Create a flawed implementation that will fail verification
        {
            "strategy_id": "strategy_null_pointer_flawed",
            "bug_type": "null_pointer",
            "bug_location": "example_files/null_pointer_example.py",
            "description": "Incorrect fix for null pointer",
            "patches": [
                {
                    "file_path": "example_files/null_pointer_example.py",
                    "changes": [
                        {
                            "type": "replace_lines",
                            "start_line": 12,
                            "end_line": 12,
                            "content": "    # This fix is flawed - it will cause a syntax error\n    if user.get_profile() is None\n        result = None\n    else:\n        result = user.get_profile().get_settings()"
                        }
                    ]
                }
            ],
            "timestamp": "2025-07-03T21:30:00.000000"
        }
    ]
    
    # Verify each implementation
    for impl in implementations:
        try:
            agent.verify_implementation(implementation=impl)
        except Exception as e:
            logger.warning(f"Verification failed for {impl['strategy_id']}: {str(e)}")
    
    # Get metrics summary
    metrics = agent.metrics.get_summary()
    
    logger.info("Verification Metrics Summary:")
    logger.info(f"Total verifications: {metrics['total_verifications']}")
    logger.info(f"Success rate: {metrics['success_rate']:.2f}")
    logger.info(f"Average verification time: {metrics['avg_verification_time']:.2f} seconds")
    logger.info(f"False positive rate: {metrics['false_positive_rate']:.2f}")
    logger.info(f"False negative rate: {metrics['false_negative_rate']:.2f}")
    
    logger.info("\nBug Type Success Rates:")
    for bug_type, rate in metrics['bug_type_success_rates'].items():
        logger.info(f"  - {bug_type}: {rate:.2f}")
    
    logger.info("\nCheck Success Rates:")
    for check_name, rate in metrics['check_success_rates'].items():
        logger.info(f"  - {check_name}: {rate:.2f}")

def demonstrate_verification_with_different_environments():
    """Demonstrate verification with different environment configurations."""
    logger.info("\n=== Demonstrating Verification with Different Environments ===")
    
    # Create a verification agent with multiple environment configurations
    agent = VerificationAgent(config={
        "environments": {
            "default": {
                "python_version": sys.version[:3],
                "test_framework": "unittest",
                "code_standards": ["flake8"],
                "use_virtualenv": False
            },
            "strict": {
                "python_version": sys.version[:3],
                "test_framework": "pytest",
                "code_standards": ["flake8", "black", "mypy"],
                "use_virtualenv": True,
                "additional_checks": ["security", "performance"]
            },
            "minimal": {
                "python_version": sys.version[:3],
                "test_framework": "unittest",
                "code_standards": [],
                "use_virtualenv": False,
                "skip_checks": ["standards", "regression"]
            }
        }
    })
    
    # Verify with the minimal environment
    logger.info("Verifying with 'minimal' environment...")
    minimal_result = agent.verify_implementation(
        implementation=SAMPLE_IMPLEMENTATION,
        environment="minimal"
    )
    
    logger.info(f"Minimal environment verification success: {minimal_result['overall_success']}")
    logger.info(f"Checks performed: {list(minimal_result['checks'].keys())}")
    
    # Verify with the default environment
    logger.info("\nVerifying with 'default' environment...")
    default_result = agent.verify_implementation(
        implementation=SAMPLE_IMPLEMENTATION,
        environment="default"
    )
    
    logger.info(f"Default environment verification success: {default_result['overall_success']}")
    logger.info(f"Checks performed: {list(default_result['checks'].keys())}")
    
    # Compare results
    logger.info("\nEnvironment Comparison:")
    logger.info(f"Minimal confidence: {minimal_result['confidence']:.2f}")
    logger.info(f"Default confidence: {default_result['confidence']:.2f}")
    
    return minimal_result, default_result

def end_to_end_demo():
    """Demonstrate an end-to-end implementation and verification workflow."""
    logger.info("\n=== Demonstrating End-to-End Implementation and Verification ===")
    
    # First, create an Implementation Agent to create the implementation
    impl_agent = ImplementationAgent()
    
    # Create a strategy for fixing the null pointer bug
    strategy = {
        "id": "strategy_null_pointer_e2e",
        "name": "Null Reference Prevention",
        "description": "Add null checks to prevent NoneType errors",
        "bug_type": "null_pointer",
        "bug_location": "example_files/null_pointer_example.py",
        "bug_line": 12,
        "bug_code": "result = user.get_profile().get_settings()",
        "bug_description": "NoneType error when accessing profile settings",
        "bug_severity": "high",
        "affected_files": ["example_files/null_pointer_example.py"],
        "repair_steps": [
            {"description": "Add null check before accessing properties", "completed": False},
            {"description": "Add appropriate error handling for null case", "completed": False}
        ],
        "confidence": 0.85
    }
    
    # Implement the strategy
    logger.info("Implementing the strategy...")
    implementation = impl_agent.implement_strategy(strategy)
    
    # Then, create a Verification Agent to verify the implementation
    verify_agent = VerificationAgent()
    
    # Verify the implementation
    logger.info("Verifying the implementation...")
    verification_result = verify_agent.verify_implementation(
        implementation=implementation,
        strategy=strategy
    )
    
    # Show the results
    logger.info(f"Implementation ID: {implementation.get('implementation_id', 'unknown')}")
    logger.info(f"Verification success: {verification_result['overall_success']}")
    logger.info(f"Confidence: {verification_result['confidence']:.2f}")
    
    # If verification was successful, apply the implementation
    if verification_result['overall_success']:
        logger.info("\nApplying the implementation...")
        apply_result = impl_agent.apply_implementation(
            implementation=implementation,
            dry_run=True  # Set to False to actually apply the changes
        )
        
        logger.info(f"Application status: {apply_result['status']}")
        logger.info(f"Message: {apply_result['message']}")
    else:
        logger.info("\nImplementation failed verification, not applying changes")
        logger.info(f"Issues: {verification_result['issues']}")
    
    return implementation, verification_result

def main():
    """Main function to run the demonstration."""
    logger.info("Starting Enhanced Verification Agent Demo")
    
    # Setup example files
    setup_example_files()
    
    # Run demonstrations
    demonstrate_environment_detection()
    demonstrate_staged_verification()
    demonstrate_traditional_verification()
    demonstrate_verification_metrics()
    demonstrate_verification_with_different_environments()
    end_to_end_demo()
    
    logger.info("Enhanced Verification Agent Demo completed successfully")

if __name__ == "__main__":
    main()
