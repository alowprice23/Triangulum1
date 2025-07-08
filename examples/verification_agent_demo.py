"""
Verification Agent Demo

This demo showcases the enhanced verification agent with its integrated components:
- Test generation
- Code fixing
- Metrics tracking
- Multi-stage verification
"""

import os
import sys
import logging
import json
from pathlib import Path

# Add the parent directory to the path so we can import triangulum_lx
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.agents.verification_agent import VerificationAgent
from triangulum_lx.agents.message import MessageType

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_implementation():
    """Create a sample implementation for demonstration."""
    # Sample implementation with a bug fix for a null pointer issue
    return {
        "strategy_id": "demo_strategy_001",
        "bug_type": "null_pointer",
        "changes": [
            {
                "file_path": "example_files/null_pointer_example.py",
                "new_content": """
def process_data(data):
    \"\"\"Process the data and return a result.\"\"\"
    # Fixed version with null check
    if data is None:
        return None
        
    if 'key' in data:
        return data['key']
    return None
"""
            }
        ]
    }

def create_sample_bug_report():
    """Create a sample bug report for demonstration."""
    return {
        "bug_id": "BUG-001",
        "bug_type": "null_pointer",
        "file_path": "example_files/null_pointer_example.py",
        "description": "The function process_data crashes when given None as input",
        "severity": "high",
        "steps_to_reproduce": [
            "Call process_data(None)",
            "Observe that it raises an AttributeError"
        ]
    }

def create_sample_strategy():
    """Create a sample strategy for demonstration."""
    return {
        "strategy_id": "demo_strategy_001",
        "approach": "Add null check at the beginning of the function",
        "reasoning": "The function assumes data is a dictionary but doesn't check if it's None",
        "expected_outcome": "Function should return None when given None as input"
    }

def main():
    """Run the verification agent demo."""
    logger.info("Starting Verification Agent Demo")
    
    # Create a verification agent
    agent = VerificationAgent(
        agent_id="demo_verification_agent",
        config={
            "verification_metrics": [
                "syntax", "tests", "standards", "security", "regression"
            ],
            "auto_fix": True,
            "test_timeout": 10
        }
    )
    
    # Create sample data for verification
    implementation = create_sample_implementation()
    bug_report = create_sample_bug_report()
    strategy = create_sample_strategy()
    
    # Verify the implementation
    logger.info("Verifying implementation...")
    result = agent.verify_implementation(
        implementation=implementation,
        strategy=strategy,
        bug_report=bug_report
    )
    
    # Print the verification result
    logger.info(f"Verification result: {result['overall_success']}")
    logger.info(f"Confidence: {result['confidence']}")
    
    # Print the checks
    logger.info("Verification checks:")
    for check_name, check_result in result["checks"].items():
        success = "✓" if check_result.get("success", False) else "✗"
        logger.info(f"  {check_name}: {success}")
    
    # Print any issues
    if result["issues"]:
        logger.info("Issues found:")
        for issue in result["issues"]:
            if isinstance(issue, dict):
                logger.info(f"  {issue.get('type', 'Issue')}: {issue.get('message', str(issue))}")
            else:
                logger.info(f"  {issue}")
    
    # Print recommendations
    if result["recommendations"]:
        logger.info("Recommendations:")
        for recommendation in result["recommendations"]:
            logger.info(f"  {recommendation}")
    
    # Get metrics summary
    metrics_summary = agent.metrics.get_summary()
    logger.info(f"Verification metrics: {json.dumps(metrics_summary, indent=2)}")
    
    # Get global metrics summary
    global_metrics_summary = agent.global_metrics.get_summary()
    logger.info(f"Global verification metrics: {json.dumps(global_metrics_summary, indent=2)}")
    
    # Demonstrate code fixing
    logger.info("\nDemonstrating code fixing...")
    
    # Create a broken implementation
    broken_implementation = {
        "strategy_id": "demo_strategy_002",
        "bug_type": "resource_leak",
        "changes": [
            {
                "file_path": "example_files/resource_leak_example.py",
                "new_content": """
def read_file(filename):
    \"\"\"Read a file and return its contents.\"\"\"
    # This implementation has a resource leak - file is not closed
    file = open(filename, 'r')
    content = file.read()
    return content
"""
            }
        ]
    }
    
    # Verify the broken implementation
    logger.info("Verifying broken implementation...")
    broken_result = agent.verify_implementation(
        implementation=broken_implementation,
        bug_report={
            "bug_id": "BUG-002",
            "bug_type": "resource_leak",
            "file_path": "example_files/resource_leak_example.py",
            "description": "The function read_file doesn't close the file handle"
        }
    )
    
    # Print the verification result
    logger.info(f"Broken implementation verification result: {broken_result['overall_success']}")
    
    # Check if the implementation was fixed
    if broken_implementation != create_sample_implementation():
        logger.info("The implementation was automatically fixed!")
        logger.info("Fixed implementation:")
        for change in broken_implementation["changes"]:
            logger.info(f"File: {change['file_path']}")
            logger.info(f"Content:\n{change['new_content']}")
    
    logger.info("Verification Agent Demo completed")

if __name__ == "__main__":
    main()
