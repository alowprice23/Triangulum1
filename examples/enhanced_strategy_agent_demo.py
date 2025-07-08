#!/usr/bin/env python3
"""
Enhanced Strategy Agent Demo

This script demonstrates the enhanced Strategy Agent's capabilities:
- Advanced bug pattern recognition
- Learning from historical strategies
- Context-aware strategy optimization
- Dynamic strategy template generation
- Confidence calculation with historical performance data
"""

import os
import sys
import json
import logging
import time
from typing import Dict, Any

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.agents.strategy_agent import StrategyAgent
from triangulum_lx.tooling.code_relationship_analyzer import CodeRelationshipAnalyzer
from triangulum_lx.tooling.relationship_context_provider import RelationshipContextProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Sample bug reports for demonstration
SAMPLE_BUGS = {
    "null_pointer": {
        "id": "bug-001",
        "file": "example_files/null_pointer_example.py",
        "line": 12,
        "code": "result = user.get_profile().get_settings()",
        "description": "NoneType error when accessing profile settings",
        "error_type": "AttributeError",
        "severity": "high"
    },
    "resource_leak": {
        "id": "bug-002",
        "file": "example_files/resource_leak_example.py",
        "line": 8,
        "code": "file = open('data.txt', 'r')\ndata = file.read()",
        "description": "File resource not properly closed",
        "error_type": "ResourceWarning",
        "severity": "medium"
    },
    "exception_swallowing": {
        "id": "bug-003",
        "file": "example_files/exception_swallowing_example.py",
        "line": 15,
        "code": "try:\n    process_data()\nexcept Exception:\n    pass",
        "description": "Exception being swallowed without logging",
        "error_type": "SilentError",
        "severity": "medium"
    }
}

def create_code_context(bug_report: Dict[str, Any]) -> Dict[str, Any]:
    """Create a simple code context for a bug report."""
    return {
        "file": bug_report["file"],
        "line": bug_report["line"],
        "language": "python",
        "function_name": "unknown_function",
        "class_name": None,
        "imports": [],
        "code_snippet": bug_report["code"]
    }

def demonstrate_enhanced_pattern_recognition():
    """Demonstrate the enhanced bug pattern recognition capabilities."""
    logger.info("=== Demonstrating Enhanced Bug Pattern Recognition ===")
    
    # Initialize the Strategy Agent
    agent = StrategyAgent(config={"enable_learning": True})
    
    # Create additional bug report variants with less explicit information
    variant_bugs = {
        "ambiguous_null": {
            "id": "bug-v001",
            "file": "example_files/variant_example.py",
            "line": 25,
            "code": "data = response.body.data",
            "description": "Error when accessing data from API response",
            "error_type": "Error",
            "severity": "medium"
        },
        "implicit_resource": {
            "id": "bug-v002",
            "file": "example_files/variant_example.py",
            "line": 42,
            "code": "conn = db.connect()\nresults = conn.query('SELECT * FROM users')",
            "description": "Database connection issues in the application",
            "error_type": "Warning",
            "severity": "low"
        }
    }
    
    # Demonstrate pattern recognition on standard cases
    for bug_type, bug_report in SAMPLE_BUGS.items():
        detected_type = agent._determine_bug_type(bug_report)
        logger.info(f"Original bug type: {bug_type}, Detected type: {detected_type}")
    
    # Demonstrate pattern recognition on ambiguous variants
    for variant_name, bug_report in variant_bugs.items():
        detected_type = agent._determine_bug_type(bug_report)
        logger.info(f"Variant: {variant_name}, Detected type: {detected_type}")
    
    # Test the pattern recognizers directly
    for pattern_id, recognizer in agent.pattern_recognizers.items():
        for bug_type, bug_report in SAMPLE_BUGS.items():
            result = recognizer(bug_report)
            logger.info(f"Pattern '{pattern_id}' recognizer on '{bug_type}' bug: {result}")

def demonstrate_learning_capabilities():
    """Demonstrate the agent's ability to learn from historical strategies."""
    logger.info("\n=== Demonstrating Learning Capabilities ===")
    
    # Initialize the Strategy Agent with learning enabled
    agent = StrategyAgent(config={"enable_learning": True})
    
    # Use the null pointer bug for demonstration
    bug_report = SAMPLE_BUGS["null_pointer"]
    code_context = create_code_context(bug_report)
    
    # Formulate an initial strategy
    logger.info("Formulating initial strategy...")
    strategy = agent.formulate_strategy(bug_report, code_context)
    
    # Record some simulated historical performance
    logger.info("Recording historical performance data...")
    
    # Simulate a successful strategy
    agent.update_strategy_performance(
        strategy_id=strategy["id"],
        success=True,
        confidence=strategy["confidence"],
        bug_type=strategy["bug_type"],
        verification_score=0.85,
        implementation_time=120,  # seconds
        code_context=f"{bug_report['file']}:{bug_report['line']}"
    )
    
    # Simulate another successful strategy with different parameters
    variant_strategy_id = f"{strategy['id']}_variant"
    agent.update_strategy_performance(
        strategy_id=variant_strategy_id,
        success=True,
        confidence=0.8,
        bug_type=strategy["bug_type"],
        verification_score=0.9,
        implementation_time=90,  # seconds
        code_context=f"{bug_report['file']}:{bug_report['line'] + 10}"
    )
    
    # Simulate a failed strategy
    failed_strategy_id = f"{strategy['id']}_failed"
    agent.update_strategy_performance(
        strategy_id=failed_strategy_id,
        success=False,
        confidence=0.6,
        bug_type=strategy["bug_type"],
        verification_score=0.3,
        implementation_time=180,  # seconds
        code_context=f"{bug_report['file']}:{bug_report['line'] + 20}"
    )
    
    # Display the performance records
    logger.info("Strategy performance records:")
    for strategy_id, record in agent.strategy_performance.items():
        logger.info(f"  Strategy {strategy_id}:")
        logger.info(f"    Success rate: {record.success_rate:.2f}")
        logger.info(f"    Total uses: {record.total_uses}")
        logger.info(f"    Average confidence: {record.avg_confidence:.2f}")
    
    # Formulate a new strategy for the same bug type to demonstrate learning
    similar_bug = {
        "id": "bug-001-similar",
        "file": bug_report["file"],
        "line": bug_report["line"] + 5,
        "code": "settings = user.profile.settings",
        "description": "Null reference when accessing user profile settings",
        "error_type": "AttributeError",
        "severity": "high"
    }
    
    logger.info("Formulating new strategy with historical learning...")
    new_strategy = agent.formulate_strategy(similar_bug, create_code_context(similar_bug))
    
    logger.info(f"Original strategy confidence: {strategy['confidence']:.2f}")
    logger.info(f"New strategy confidence: {new_strategy['confidence']:.2f}")

def demonstrate_context_aware_optimization():
    """Demonstrate context-aware strategy optimization."""
    logger.info("\n=== Demonstrating Context-Aware Strategy Optimization ===")
    
    # Initialize the Strategy Agent
    agent = StrategyAgent(config={"enable_learning": True})
    
    # Create a code relationship context
    relationship_context = {
        "file_relationships": {
            "example_files/null_pointer_example.py": [
                "example_files/utils.py",
                "example_files/models.py"
            ]
        },
        "function_calls": {
            "example_files/null_pointer_example.py": {
                "get_profile": ["example_files/models.py:User.get_profile"]
            }
        },
        "class_hierarchies": {
            "example_files/models.py": {
                "User": ["BaseModel"],
                "Profile": ["BaseModel"]
            }
        }
    }
    
    # Use the null pointer bug
    bug_report = SAMPLE_BUGS["null_pointer"]
    code_context = create_code_context(bug_report)
    
    # Formulate a strategy without relationship context
    logger.info("Formulating strategy without relationship context...")
    basic_strategy = agent.formulate_strategy(bug_report, code_context)
    
    # Formulate a strategy with relationship context
    logger.info("Formulating strategy with relationship context...")
    enhanced_strategy = agent.formulate_strategy(
        bug_report, code_context, relationship_context
    )
    
    # Compare the results
    logger.info(f"Basic strategy affected files: {len(basic_strategy['affected_files'])}")
    logger.info(f"Enhanced strategy affected files: {len(enhanced_strategy['affected_files'])}")
    
    logger.info(f"Basic strategy: {basic_strategy['affected_files']}")
    logger.info(f"Enhanced strategy: {enhanced_strategy['affected_files']}")

def main():
    """Run the demonstration."""
    logger.info("Starting Enhanced Strategy Agent Demo")
    
    # Ensure the examples directory exists for the demo
    os.makedirs("data/strategy_learning", exist_ok=True)
    os.makedirs("example_files", exist_ok=True)
    
    # Create example files if they don't exist
    example_files = {
        "example_files/null_pointer_example.py": 
'''class User:
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
''',

        "example_files/resource_leak_example.py":
'''def read_data_file():
    # Bug: file is not closed
    file = open('data.txt', 'r')
    data = file.read()
    return data

def write_data_file(data):
    # Also missing file close
    file = open('data.txt', 'w')
    file.write(data)
    # Missing file.close()

read_data_file()
''',

        "example_files/exception_swallowing_example.py":
'''def process_data():
    # Some processing that might fail
    data = [1, 2, 3]
    result = data[10]  # This will raise an IndexError
    return result

def safe_process():
    # Bug: Exception is swallowed without logging or handling
    try:
        return process_data()
    except Exception:
        pass  # Exception is silently swallowed
    
    return None

safe_process()
'''
    }
    
    # Write example files
    for file_path, content in example_files.items():
        with open(file_path, 'w') as f:
            f.write(content)
    
    # Run demonstrations
    demonstrate_enhanced_pattern_recognition()
    demonstrate_learning_capabilities()
    demonstrate_context_aware_optimization()
    
    logger.info("Enhanced Strategy Agent Demo completed successfully")

if __name__ == "__main__":
    main()
