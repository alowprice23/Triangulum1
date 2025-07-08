"""
Strategy Agent Demo

This example demonstrates how to use the Strategy Agent to formulate repair
strategies for bugs identified by the Bug Detector Agent.
"""

import os
import sys
import logging
from pathlib import Path
import json

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from triangulum_lx.agents.bug_detector_agent import BugDetectorAgent
from triangulum_lx.agents.strategy_agent import StrategyAgent
from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.message_bus import MessageBus

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_example_files():
    """Create example files with bugs for demonstration."""
    # Create a directory for example files
    example_dir = Path("./strategy_example_files")
    example_dir.mkdir(exist_ok=True)
    
    # Example 1: File with null pointer bug
    null_pointer_file = example_dir / "null_pointer_example.py"
    with open(null_pointer_file, "w") as f:
        f.write("""
def get_user_profile(user_id):
    # Get user from database
    user = get_user_from_database(user_id)
    
    # Bug: No check if user is None before accessing properties
    name = user.name
    email = user.email
    
    return {
        "name": name,
        "email": email
    }

def get_user_from_database(user_id):
    # This is a mock function that might return None
    if user_id <= 0:
        return None
    
    # For demo purposes, create a user object
    class User:
        def __init__(self, user_id):
            self.id = user_id
            self.name = f"User {user_id}"
            self.email = f"user{user_id}@example.com"
    
    return User(user_id)
""")
    
    # Example 2: File with resource leak
    resource_leak_file = example_dir / "resource_leak_example.py"
    with open(resource_leak_file, "w") as f:
        f.write("""
def save_log_entry(log_entry):
    # Bug: File is opened but not properly closed
    log_file = open("application.log", "a")
    log_file.write(log_entry + "\\n")
    
    # Missing log_file.close()
    
    return True

def read_configuration():
    # Bug: Another resource leak
    config_file = open("config.ini", "r")
    config_data = config_file.read()
    
    # What if an exception occurs?
    
    config_file.close()
    return config_data
""")
    
    # Example 3: File with SQL injection
    sql_injection_file = example_dir / "sql_injection_example.py"
    with open(sql_injection_file, "w") as f:
        f.write("""
def search_users(search_term):
    # Bug: SQL injection vulnerability
    query = "SELECT * FROM users WHERE name LIKE '%" + search_term + "%'"
    
    # Execute query (not actual implementation)
    results = db_execute(query)
    
    return results

def get_user_by_id(user_id):
    # Bug: Another SQL injection vulnerability
    query = "SELECT * FROM users WHERE id = " + user_id
    
    # Execute query (not actual implementation)
    result = db_execute(query)
    
    return result

def db_execute(query):
    # Mock function for demonstration
    return [{"id": 1, "name": "User 1"}, {"id": 2, "name": "User 2"}]
""")
    
    # Example 4: File with exception swallowing
    exception_file = example_dir / "exception_swallowing_example.py"
    with open(exception_file, "w") as f:
        f.write("""
def process_data(data):
    try:
        # Process the data
        result = transform_data(data)
        return result
    except Exception:
        # Bug: Exception is swallowed without logging or handling
        pass
    
    # Default return value with no indication of failure
    return None

def transform_data(data):
    # This might raise various exceptions
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary")
    
    if "value" not in data:
        raise ValueError("Data must contain a 'value' key")
    
    return data["value"] * 2
""")
    
    return {
        "null_pointer": str(null_pointer_file),
        "resource_leak": str(resource_leak_file),
        "sql_injection": str(sql_injection_file),
        "exception_swallowing": str(exception_file)
    }


def detect_bugs(agent, files):
    """Use the Bug Detector Agent to find bugs in the example files."""
    logger.info("===== DETECTING BUGS =====")
    
    bugs = {}
    
    for bug_type, file_path in files.items():
        logger.info(f"\nAnalyzing file for {bug_type} bugs: {file_path}")
        file_bugs = agent.detect_bugs_in_file(file_path)
        
        if file_bugs:
            logger.info(f"Found {len(file_bugs)} potential bugs:")
            bugs[file_path] = file_bugs
            
            for i, bug in enumerate(file_bugs, 1):
                logger.info(f"  Bug #{i}:")
                logger.info(f"    Pattern: {bug['pattern_id']}")
                logger.info(f"    Severity: {bug['severity']}")
                logger.info(f"    Line {bug['line']}: {bug['code']}")
                logger.info(f"    Remediation: {bug['remediation']}")
        else:
            logger.info("No bugs detected (or no matching patterns).")
    
    return bugs


def formulate_strategies(agent, bugs):
    """Use the Strategy Agent to formulate repair strategies for the bugs."""
    logger.info("\n\n===== FORMULATING STRATEGIES =====")
    
    strategies = {}
    
    for file_path, file_bugs in bugs.items():
        logger.info(f"\nFormulating strategies for bugs in: {file_path}")
        
        file_strategies = []
        
        # Read the file content to provide code context
        with open(file_path, 'r') as f:
            file_content = f.read()
        
        for bug in file_bugs:
            # Prepare code context
            code_context = {
                "language": "python",  # Assume Python for this demo
                "file_content": file_content,
                "file_path": file_path
            }
            
            # Formulate a strategy for the bug
            strategy = agent.formulate_strategy(bug, code_context)
            file_strategies.append(strategy)
            
            # Log the strategy details
            logger.info(f"\nStrategy for {bug['pattern_id']} bug on line {bug['line']}:")
            logger.info(f"  Name: {strategy['name']}")
            logger.info(f"  Description: {strategy['description']}")
            logger.info(f"  Estimated Complexity: {strategy['estimated_complexity']}/10")
            logger.info(f"  Confidence: {strategy['confidence']:.2f}")
            
            logger.info("\n  Repair Steps:")
            for i, step in enumerate(strategy['repair_steps'], 1):
                logger.info(f"    {i}. {step['description']}")
            
            if strategy['code_examples']:
                logger.info("\n  Code Examples:")
                for i, example in enumerate(strategy['code_examples'], 1):
                    logger.info(f"    Example #{i}:\n{example}")
        
        strategies[file_path] = file_strategies
    
    return strategies


def evaluate_strategies(agent, strategies):
    """Evaluate the strategies against constraints."""
    logger.info("\n\n===== EVALUATING STRATEGIES =====")
    
    evaluations = {}
    
    # Define different constraint sets
    constraint_sets = {
        "default": {
            "max_complexity": 5,
            "max_changes": 10,
            "max_files": 3,
            "restricted_areas": []
        },
        "strict": {
            "max_complexity": 3,
            "max_changes": 5,
            "max_files": 1,
            "restricted_areas": ["database", "authentication"]
        },
        "lenient": {
            "max_complexity": 8,
            "max_changes": 20,
            "max_files": 5,
            "restricted_areas": []
        }
    }
    
    for file_path, file_strategies in strategies.items():
        logger.info(f"\nEvaluating strategies for: {file_path}")
        
        file_evaluations = []
        
        for strategy in file_strategies:
            logger.info(f"\nEvaluating strategy: {strategy['name']}")
            
            for constraint_name, constraints in constraint_sets.items():
                evaluation = agent.evaluate_strategy(strategy, constraints)
                
                logger.info(f"\n  Evaluation against {constraint_name} constraints:")
                logger.info(f"    Score: {evaluation['score']}/100")
                logger.info(f"    Acceptable: {'Yes' if evaluation['acceptable'] else 'No'}")
                logger.info(f"    Complexity: {evaluation['complexity']}/10")
                logger.info(f"    Changes: {evaluation['changes']}")
                logger.info(f"    Affected Files: {evaluation['affected_files']}")
                
                if evaluation['issues']:
                    logger.info(f"    Issues: {', '.join(evaluation['issues'])}")
                
                file_evaluations.append({
                    "strategy_id": strategy['id'],
                    "constraint_set": constraint_name,
                    "evaluation": evaluation
                })
        
        evaluations[file_path] = file_evaluations
    
    return evaluations


def demonstrate_message_based_communication(bug_detector, strategy_agent, bugs):
    """Demonstrate message-based communication between agents."""
    logger.info("\n\n===== DEMONSTRATING MESSAGE-BASED COMMUNICATION =====")
    
    # Get the first bug for demonstration
    file_path = list(bugs.keys())[0]
    bug = bugs[file_path][0]
    
    # Read the file content to provide code context
    with open(file_path, 'r') as f:
        file_content = f.read()
    
    # Create a message bus for agent communication
    message_bus = MessageBus()
    
    # Create a simple message handler to capture responses
    class MessageHandler:
        def __init__(self):
            self.responses = []
        
        def handle_message(self, message):
            self.responses.append(message)
    
    # Create a message handler
    handler = MessageHandler()
    
    # Setup the message bus to capture responses
    original_publish = message_bus.publish
    
    def custom_publish(message):
        original_publish(message)
        handler.handle_message(message)
    
    message_bus.publish = custom_publish
    
    # Connect agents to the message bus
    bug_detector.message_bus = message_bus
    strategy_agent.message_bus = message_bus
    
    # Register agents with the message bus
    bug_detector._register_with_message_bus()
    strategy_agent._register_with_message_bus()
    
    # Step 1: Send a task request to the Bug Detector Agent
    logger.info("\nStep 1: Sending task request to Bug Detector Agent")
    bug_detect_message = AgentMessage(
        message_type=MessageType.TASK_REQUEST,
        content={
            "action": "detect_bugs_in_file",
            "file_path": file_path
        },
        sender="demo_app"
    )
    
    # Process the message
    bug_detector.handle_message(bug_detect_message)
    
    # Wait for the response (in a real system, this would be asynchronous)
    import time
    time.sleep(0.5)
    
    # Find the Bug Detector's response
    bug_detector_response = None
    for response in handler.responses:
        if response.message_type == MessageType.TASK_RESULT:
            bug_detector_response = response
            break
    
    if not bug_detector_response:
        logger.warning("No response received from Bug Detector Agent")
        return
    
    # Display the Bug Detector's response
    logger.info(f"Received response from Bug Detector Agent: {bug_detector_response.message_type}")
    logger.info(f"Status: {bug_detector_response.content['status']}")
    logger.info(f"Found {bug_detector_response.content['bug_count']} bugs")
    
    # Step 2: Send a task request to the Strategy Agent with the bug report
    if bug_detector_response.content['bugs']:
        bug_report = bug_detector_response.content['bugs'][0]
        
        # Prepare code context
        code_context = {
            "language": "python",
            "file_content": file_content,
            "file_path": file_path
        }
        
        logger.info("\nStep 2: Sending task request to Strategy Agent")
        strategy_message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "formulate_strategy",
                "bug_report": bug_report,
                "code_context": code_context
            },
            sender="demo_app"
        )
        
        # Clear previous responses
        handler.responses.clear()
        
        # Process the message
        strategy_agent.handle_message(strategy_message)
        
        # Wait for the response
        time.sleep(0.5)
        
        # Find the Strategy Agent's response
        strategy_agent_response = None
        for response in handler.responses:
            if response.message_type == MessageType.TASK_RESULT:
                strategy_agent_response = response
                break
        
        if not strategy_agent_response:
            logger.warning("No response received from Strategy Agent")
            return
        
        # Display the Strategy Agent's response
        logger.info(f"Received response from Strategy Agent: {strategy_agent_response.message_type}")
        logger.info(f"Status: {strategy_agent_response.content['status']}")
        
        # Display the strategy
        strategy = strategy_agent_response.content['strategy']
        logger.info(f"\nStrategy for {strategy['bug_type']} bug:")
        logger.info(f"  Name: {strategy['name']}")
        logger.info(f"  Description: {strategy['description']}")
        logger.info(f"  Estimated Complexity: {strategy['estimated_complexity']}/10")
        logger.info(f"  Confidence: {strategy['confidence']:.2f}")
        
        logger.info("\n  Repair Steps:")
        for i, step in enumerate(strategy['repair_steps'], 1):
            logger.info(f"    {i}. {step['description']}")
        
        if strategy['code_examples']:
            logger.info("\n  Code Examples:")
            for i, example in enumerate(strategy['code_examples'], 1):
                logger.info(f"    Example #{i}:\n{example}")
    else:
        logger.warning("No bugs found to formulate strategy")


def main():
    """Main function to run the demo."""
    logger.info("Starting Strategy Agent Demo")
    
    # Create example files
    files = create_example_files()
    
    # Create the Bug Detector Agent
    bug_detector = BugDetectorAgent(
        agent_id="demo_bug_detector"
    )
    
    # Create the Strategy Agent
    strategy_agent = StrategyAgent(
        agent_id="demo_strategy_agent"
    )
    
    # Use the Bug Detector Agent to find bugs
    bugs = detect_bugs(bug_detector, files)
    
    # Use the Strategy Agent to formulate repair strategies
    strategies = formulate_strategies(strategy_agent, bugs)
    
    # Evaluate the strategies
    evaluations = evaluate_strategies(strategy_agent, strategies)
    
    # Demonstrate message-based communication
    demonstrate_message_based_communication(bug_detector, strategy_agent, bugs)
    
    logger.info("\nDemo completed successfully!")


if __name__ == "__main__":
    main()
