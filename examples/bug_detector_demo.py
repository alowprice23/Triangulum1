"""
Bug Detector Agent Demo

This example demonstrates how to use the Bug Detector Agent to identify bugs in code
and analyze test failures. It shows both direct API usage and message-based interaction.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from triangulum_lx.agents.bug_detector_agent import BugDetectorAgent
from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.message_bus import MessageBus

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_example_files():
    """Create example files with bugs for demonstration."""
    # Create a directory for example files
    example_dir = Path("./example_files")
    example_dir.mkdir(exist_ok=True)
    
    # Example 1: File with null pointer bug
    null_pointer_file = example_dir / "null_pointer_example.py"
    with open(null_pointer_file, "w") as f:
        f.write("""
def get_user_name(user):
    # This will cause a null reference error if user is None
    return user.name

def process_request(request):
    user = get_user_from_request(request)
    # Forgot to check if user is None
    name = get_user_name(user)
    return f"Hello, {name}!"

def get_user_from_request(request):
    # This might return None
    if 'user_id' not in request:
        return None
    # Get user from database...
    return request.get('user')
""")
    
    # Example 2: File with SQL injection bug
    sql_injection_file = example_dir / "sql_injection_example.py"
    with open(sql_injection_file, "w") as f:
        f.write("""
def get_user_by_id(user_id):
    # This is vulnerable to SQL injection
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()

def search_users(search_term):
    # This is also vulnerable
    query = "SELECT * FROM users WHERE name LIKE '%" + search_term + "%'"
    cursor.execute(query)
    return cursor.fetchall()
""")
    
    # Example 3: File with exception swallowing
    exception_file = example_dir / "exception_swallowing_example.py"
    with open(exception_file, "w") as f:
        f.write("""
def process_data(data):
    try:
        result = complex_calculation(data)
        return result
    except Exception:
        # This silently swallows the exception
        pass
        
    # Default return value with no indication of failure
    return 0

def complex_calculation(data):
    # This might raise various exceptions
    return data['value1'] / data['value2']
""")
    
    # Example 4: File with resource leak
    resource_leak_file = example_dir / "resource_leak_example.py"
    with open(resource_leak_file, "w") as f:
        f.write("""
def read_data_from_file(filename):
    # This file is opened but never closed
    f = open(filename, 'r')
    data = f.read()
    # Missing f.close()
    return data

def write_data_to_file(filename, data):
    # This file is also not properly closed
    f = open(filename, 'w')
    f.write(data)
    # What if an exception occurs before we reach this point?
    f.close()
    return True
""")
    
    # Example 5: File with hardcoded credentials
    credentials_file = example_dir / "hardcoded_credentials_example.py"
    with open(credentials_file, "w") as f:
        f.write("""
def connect_to_database():
    # Hardcoded credentials are a security risk
    username = "admin"
    password = "super_secret_password"
    
    # Connect to the database
    connection = database.connect(
        host="db.example.com",
        user=username,
        password=password,
        database="production"
    )
    return connection
""")
    
    # Create a file for test failure analysis
    division_file = example_dir / "division.py"
    with open(division_file, "w") as f:
        f.write("""
def divide(a, b):
    # This will raise a ZeroDivisionError if b is 0
    return a / b

def calculate_ratio(numerator, denominator):
    # Missing check for denominator being zero
    return divide(numerator, denominator)

def safe_calculate_ratio(numerator, denominator):
    # Safe version with proper error handling
    if denominator == 0:
        return float('inf')  # Return infinity for division by zero
    return divide(numerator, denominator)
""")
    
    # Create a test file that will fail
    test_division_file = example_dir / "test_division.py"
    with open(test_division_file, "w") as f:
        f.write(f"""
import unittest
from pathlib import Path

# Add the current directory to path
import sys
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from division import calculate_ratio, safe_calculate_ratio

class TestDivision(unittest.TestCase):
    
    def test_calculate_ratio(self):
        # This test will fail with ZeroDivisionError
        result = calculate_ratio(10, 0)
        self.assertEqual(result, float('inf'))
    
    def test_safe_calculate_ratio(self):
        # This test will pass
        result = safe_calculate_ratio(10, 0)
        self.assertEqual(result, float('inf'))

if __name__ == "__main__":
    unittest.main()
""")
    
    return {
        "null_pointer": str(null_pointer_file),
        "sql_injection": str(sql_injection_file),
        "exception_swallowing": str(exception_file),
        "resource_leak": str(resource_leak_file),
        "hardcoded_credentials": str(credentials_file),
        "division": str(division_file),
        "test_division": str(test_division_file)
    }


def demo_direct_api_usage(agent, files):
    """Demonstrate direct API usage of the Bug Detector Agent."""
    logger.info("===== DEMO: DIRECT API USAGE =====")
    
    # 1. Detect bugs in each example file
    for bug_type, file_path in files.items():
        if bug_type == "test_division":
            continue  # Skip test file
        
        logger.info(f"\nAnalyzing file for {bug_type} bugs: {file_path}")
        bugs = agent.detect_bugs_in_file(file_path)
        
        if bugs:
            logger.info(f"Found {len(bugs)} potential bugs:")
            for i, bug in enumerate(bugs, 1):
                logger.info(f"  Bug #{i}:")
                logger.info(f"    Pattern: {bug['pattern_id']}")
                logger.info(f"    Severity: {bug['severity']}")
                logger.info(f"    Line {bug['line']}: {bug['code']}")
                logger.info(f"    Remediation: {bug['remediation']}")
        else:
            logger.info("No bugs detected (or no matching patterns).")
    
    # 2. Analyze a test failure
    try:
        # Try to run the test that will fail
        import unittest
        from example_files.test_division import TestDivision
        
        logger.info("\n===== Running test that will fail =====")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestDivision)
        result = unittest.TextTestRunner().run(suite)
        
        if not result.wasSuccessful():
            # Get the first error
            test_case, error = result.errors[0] if result.errors else result.failures[0]
            test_name = test_case.id().split('.')[-1]
            error_message = str(error[1])
            
            # The stack trace is already formatted in the error message
            formatted_trace = error[0]
            
            logger.info("\n===== Analyzing test failure =====")
            logger.info(f"Test: {test_name}")
            logger.info(f"Error: {error_message}")
            logger.info(f"Stack Trace:\n{formatted_trace}")
            
            # Analyze the test failure
            analysis = agent.analyze_test_failure(
                test_name=test_name,
                error_message=error_message,
                stack_trace=formatted_trace,
                source_files=[files["division"]]
            )
            
            logger.info("\n===== Analysis Results =====")
            logger.info(f"Error Type: {analysis['error_type']}")
            logger.info(f"Confidence: {analysis['confidence']:.2f}")
            
            if analysis["recommended_fixes"]:
                logger.info("\nRecommended Fixes:")
                for i, fix in enumerate(analysis["recommended_fixes"], 1):
                    logger.info(f"  Fix #{i} (Priority: {fix['priority']:.2f}):")
                    logger.info(f"    {fix['description']}")
                    logger.info(f"    Remediation: {fix['remediation']}")
                    logger.info(f"    Current Code: {fix['current_code']}")
            else:
                logger.info("No specific fixes recommended.")
    
    except Exception as e:
        logger.error(f"Error running test analysis: {e}")


def demo_message_based_usage(agent, files):
    """Demonstrate message-based usage of the Bug Detector Agent."""
    logger.info("\n\n===== DEMO: MESSAGE-BASED USAGE =====")
    
    # Create a simple message handler to capture responses
    class MessageHandler:
        def __init__(self):
            self.responses = []
        
        def handle_message(self, message):
            self.responses.append(message)
    
    # Create a message handler and hook it up to the message bus
    handler = MessageHandler()
    # Set up custom message handling
    # Since we can't directly subscribe the handler without an agent_id,
    # we'll capture messages in our custom publish method
    original_publish = agent.message_bus.publish
    
    def custom_publish(message):
        # Call the original publish method
        original_publish(message)
        # Also send to our handler
        if message.message_type in [MessageType.TASK_RESULT, MessageType.QUERY_RESPONSE, MessageType.ERROR]:
            handler.handle_message(message)
    
    # Replace the publish method with our custom one
    agent.message_bus.publish = custom_publish
    
    # 1. Send a task request to detect bugs in a file
    logger.info("\n===== Sending Task Request: detect_bugs_in_file =====")
    message = AgentMessage(
        message_type=MessageType.TASK_REQUEST,
        content={
            "action": "detect_bugs_in_file",
            "file_path": files["sql_injection"]
        },
        sender="demo_app"
    )
    
    # Process the message
    agent.handle_message(message)
    
    # Wait for the response (in a real system, this would be asynchronous)
    import time
    time.sleep(0.5)
    
    # Display the response
    if handler.responses:
        response = handler.responses[-1]
        logger.info(f"Received response: {response.message_type}")
        
        if response.message_type == MessageType.TASK_RESULT:
            logger.info(f"Status: {response.content['status']}")
            logger.info(f"Found {response.content['bug_count']} bugs")
            
            for i, bug in enumerate(response.content['bugs'], 1):
                logger.info(f"  Bug #{i}:")
                logger.info(f"    Pattern: {bug['pattern_id']}")
                logger.info(f"    Severity: {bug['severity']}")
                logger.info(f"    Line {bug['line']}: {bug['code']}")
    else:
        logger.warning("No response received")
    
    # Clear previous responses
    handler.responses.clear()
    
    # 2. Send a query to get bug patterns
    logger.info("\n===== Sending Query: get_bug_patterns =====")
    message = AgentMessage(
        message_type=MessageType.QUERY,
        content={
            "query_type": "get_bug_patterns",
            "language": "python"
        },
        sender="demo_app"
    )
    
    # Process the message
    agent.handle_message(message)
    
    # Wait for the response
    time.sleep(0.5)
    
    # Display the response
    if handler.responses:
        response = handler.responses[-1]
        logger.info(f"Received response: {response.message_type}")
        
        if response.message_type == MessageType.QUERY_RESPONSE:
            logger.info(f"Status: {response.content['status']}")
            logger.info(f"Found {response.content['pattern_count']} patterns for Python")
            
            # Display a summary of the patterns
            patterns = response.content['patterns']
            for pattern_id, pattern_info in patterns.items():
                logger.info(f"  Pattern: {pattern_id}")
                logger.info(f"    Description: {pattern_info['description']}")
                logger.info(f"    Severity: {pattern_info['severity']}")
    else:
        logger.warning("No response received")


def main():
    """Main function to run the demo."""
    logger.info("Starting Bug Detector Agent Demo")
    
    # Create example files
    files = create_example_files()
    
    # Create a message bus for agent communication
    message_bus = MessageBus()
    
    # Create the Bug Detector Agent
    agent = BugDetectorAgent(
        agent_id="demo_bug_detector",
        message_bus=message_bus,
        max_bug_patterns=100
    )
    
    # Demonstrate direct API usage
    demo_direct_api_usage(agent, files)
    
    # Demonstrate message-based usage
    demo_message_based_usage(agent, files)
    
    logger.info("\nDemo completed successfully!")


if __name__ == "__main__":
    main()
