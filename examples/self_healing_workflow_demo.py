"""
Self-Healing Workflow Demo

This example demonstrates the complete self-healing workflow using all specialized agents:
1. Bug Detector Agent - identifies bugs in code
2. Relationship Analyst Agent - determines code relationships
3. Strategy Agent - formulates repair strategies
4. Implementation Agent - implements the fixes
5. Verification Agent - verifies the fixes

This demonstrates a complete end-to-end self-healing cycle.
"""

import os
import sys
import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from triangulum_lx.agents.bug_detector_agent import BugDetectorAgent
from triangulum_lx.agents.relationship_analyst_agent import RelationshipAnalystAgent
from triangulum_lx.agents.strategy_agent import StrategyAgent
from triangulum_lx.agents.implementation_agent import ImplementationAgent
from triangulum_lx.agents.verification_agent import VerificationAgent
from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.message_bus import MessageBus

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SelfHealingDemo:
    """Demonstration of the complete self-healing workflow using specialized agents."""
    
    def __init__(self):
        """Initialize the demo."""
        # Create the message bus for agent communication
        self.message_bus = MessageBus()
        
        # Create all agents
        self.bug_detector = BugDetectorAgent(
            agent_id="bug_detector",
            message_bus=self.message_bus
        )
        
        self.relationship_analyst = RelationshipAnalystAgent(
            agent_id="relationship_analyst",
            message_bus=self.message_bus
        )
        
        self.strategy_agent = StrategyAgent(
            agent_id="strategy_agent",
            message_bus=self.message_bus
        )
        
        self.implementation_agent = ImplementationAgent(
            agent_id="implementation_agent",
            message_bus=self.message_bus
        )
        
        self.verification_agent = VerificationAgent(
            agent_id="verification_agent",
            message_bus=self.message_bus
        )
        
        # Setup message handlers
        self.setup_message_handlers()
        
        # Create example files with bugs
        self.example_files = self.create_example_files()
    
    def setup_message_handlers(self):
        """Set up message handlers for the demo."""
        # Register message handlers
        self.message_bus.register_handler(
            "demo_app",
            MessageType.TASK_RESULT,
            self.handle_task_result
        )
        
        self.message_bus.register_handler(
            "demo_app",
            MessageType.ERROR,
            self.handle_error
        )
        
        # List to store results from agents
        self.results = {}
    
    def handle_task_result(self, message: AgentMessage):
        """
        Handle task result messages from agents.
        
        Args:
            message: The task result message
        """
        # Store the result by sender
        self.results[message.sender] = message.content
        logger.info(f"Received task result from {message.sender}")
    
    def handle_error(self, message: AgentMessage):
        """
        Handle error messages from agents.
        
        Args:
            message: The error message
        """
        logger.error(f"Error from {message.sender}: {message.content.get('error', 'Unknown error')}")
    
    def create_example_files(self) -> Dict[str, str]:
        """
        Create example files with bugs for demonstration.
        
        Returns:
            Dictionary mapping bug types to file paths
        """
        # Create a directory for example files
        example_dir = Path("./self_healing_example_files")
        example_dir.mkdir(exist_ok=True)
        
        # Example file with a null pointer bug
        null_pointer_file = example_dir / "null_pointer_example.py"
        with open(null_pointer_file, "w") as f:
            f.write("""
# This file demonstrates a null pointer bug

def get_user_data(user_id):
    '''Retrieve data for a user.'''
    # Simulate fetching user from database
    user = fetch_user(user_id)
    
    # BUG: No null check before accessing properties
    name = user.name
    email = user.email
    
    return {
        "name": name,
        "email": email
    }

def fetch_user(user_id):
    '''Fetch a user from the database.'''
    # This function might return None for some user IDs
    if user_id <= 0:
        return None
    
    # Mock user class
    class User:
        def __init__(self, user_id):
            self.id = user_id
            self.name = f"User {user_id}"
            self.email = f"user{user_id}@example.com"
    
    return User(user_id)

def main():
    # This works fine
    good_result = get_user_data(1)
    print(f"Good result: {good_result}")
    
    try:
        # This will cause a null pointer exception
        bad_result = get_user_data(0)
        print(f"Bad result: {bad_result}")
    except AttributeError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
""")
        
        # Example file with a resource leak bug
        resource_leak_file = example_dir / "resource_leak_example.py"
        with open(resource_leak_file, "w") as f:
            f.write("""
# This file demonstrates a resource leak bug

def read_data_from_file(filename):
    '''Reads data from a file.'''
    # BUG: File is opened but not properly closed
    file = open(filename, 'r')
    data = file.read()
    
    # Missing file.close() or 'with' statement
    
    return data

def write_data_to_file(filename, data):
    '''Writes data to a file.'''
    # This function correctly uses the 'with' statement
    with open(filename, 'w') as file:
        file.write(data)

def main():
    # Create a test file
    test_file = "test_resource.txt"
    write_data_to_file(test_file, "This is test data.")
    
    # Read the test file (leaking the file resource)
    data = read_data_from_file(test_file)
    print(f"Read data: {data}")
    
    # Clean up
    import os
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    main()
""")
        
        # Example file with an exception swallowing bug
        exception_file = example_dir / "exception_swallowing_example.py"
        with open(exception_file, "w") as f:
            f.write("""
# This file demonstrates an exception swallowing bug

def process_data(data):
    '''Processes data and handles exceptions.'''
    try:
        # Process the data
        result = transform_data(data)
        return result
    except Exception:
        # BUG: Exception is swallowed without any logging or handling
        pass
    
    # Default return with no indication of failure
    return None

def transform_data(data):
    '''Transforms the input data.'''
    # This can raise different exceptions
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary")
    
    if "value" not in data:
        raise ValueError("Data must contain a 'value' key")
    
    return data["value"] * 2

def main():
    # This works fine
    good_data = {"value": 5}
    good_result = process_data(good_data)
    print(f"Good result: {good_result}")
    
    # This will silently fail due to exception swallowing
    bad_data = "not a dictionary"
    bad_result = process_data(bad_data)
    print(f"Bad result: {bad_result}")  # Will print None without indicating the error

if __name__ == "__main__":
    main()
""")
        
        return {
            "null_pointer": str(null_pointer_file),
            "resource_leak": str(resource_leak_file),
            "exception_swallowing": str(exception_file)
        }
    
    def run_demo(self):
        """Run the self-healing demo."""
        logger.info("Starting Self-Healing Workflow Demo")
        
        # Select a bug to fix
        bug_type = "null_pointer"
        file_path = self.example_files[bug_type]
        
        logger.info(f"Demonstrating self-healing for {bug_type} bug in {file_path}")
        
        # Step 1: Detect Bugs
        self.detect_bugs(file_path)
        
        # Step 2: Analyze Relationships
        self.analyze_relationships(file_path)
        
        # Step 3: Formulate Strategy
        self.formulate_strategy(file_path)
        
        # Step 4: Implement Fix
        self.implement_fix(file_path)
        
        # Step 5: Verify Fix
        self.verify_fix(file_path)
        
        # Show summary
        self.show_summary()
    
    def detect_bugs(self, file_path: str):
        """
        Step 1: Detect bugs in the file.
        
        Args:
            file_path: Path to the file to analyze
        """
        logger.info("\n\n===== STEP 1: DETECTING BUGS =====")
        
        # Send a task request to the Bug Detector Agent
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "detect_bugs_in_file",
                "file_path": file_path
            },
            sender="demo_app"
        )
        
        # Process the message
        self.bug_detector.handle_message(message)
        
        # Wait for the response
        time.sleep(1)
        
        # Check the results
        if "bug_detector" in self.results:
            result = self.results["bug_detector"]
            bugs = result.get("bugs", [])
            
            logger.info(f"Found {len(bugs)} bugs:")
            for i, bug in enumerate(bugs, 1):
                logger.info(f"  Bug #{i}:")
                logger.info(f"    Pattern: {bug.get('pattern_id', 'unknown')}")
                logger.info(f"    Severity: {bug.get('severity', 'unknown')}")
                logger.info(f"    Line {bug.get('line', '?')}: {bug.get('code', '')}")
                logger.info(f"    Remediation: {bug.get('remediation', 'unknown')}")
        else:
            logger.warning("No response received from Bug Detector Agent")
    
    def analyze_relationships(self, file_path: str):
        """
        Step 2: Analyze code relationships.
        
        Args:
            file_path: Path to the file to analyze
        """
        logger.info("\n\n===== STEP 2: ANALYZING CODE RELATIONSHIPS =====")
        
        # Send a task request to the Relationship Analyst Agent
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "analyze_file_relationships",
                "file_path": file_path,
                "max_depth": 2  # Only analyze immediate relationships
            },
            sender="demo_app"
        )
        
        # Process the message
        self.relationship_analyst.handle_message(message)
        
        # Wait for the response
        time.sleep(1)
        
        # Check the results
        if "relationship_analyst" in self.results:
            result = self.results["relationship_analyst"]
            relationships = result.get("relationships", {})
            
            logger.info(f"Code relationships for {file_path}:")
            for related_file, details in relationships.items():
                logger.info(f"  Related to: {related_file}")
                logger.info(f"    Relationship type: {details.get('relationship_type', 'unknown')}")
                logger.info(f"    Strength: {details.get('strength', 0)}")
        else:
            logger.warning("No response received from Relationship Analyst Agent")
    
    def formulate_strategy(self, file_path: str):
        """
        Step 3: Formulate a repair strategy.
        
        Args:
            file_path: Path to the file to fix
        """
        logger.info("\n\n===== STEP 3: FORMULATING REPAIR STRATEGY =====")
        
        # Get the bug report from the Bug Detector Agent
        if "bug_detector" not in self.results:
            logger.error("No bug detection results available")
            return
        
        bug_result = self.results["bug_detector"]
        bugs = bug_result.get("bugs", [])
        
        if not bugs:
            logger.error("No bugs found to fix")
            return
        
        # Take the first bug for demonstration
        bug = bugs[0]
        
        # Get the relationship context
        relationship_context = {}
        if "relationship_analyst" in self.results:
            relationship_result = self.results["relationship_analyst"]
            relationship_context = {
                "file_relationships": relationship_result.get("relationships", {})
            }
        
        # Prepare the code context
        with open(file_path, 'r') as f:
            code_content = f.read()
        
        code_context = {
            "language": "python",  # Assuming Python for this demo
            "file_content": code_content,
            "file_path": file_path
        }
        
        # Send a task request to the Strategy Agent
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "formulate_strategy",
                "bug_report": bug,
                "code_context": code_context,
                "relationship_context": relationship_context
            },
            sender="demo_app"
        )
        
        # Process the message
        self.strategy_agent.handle_message(message)
        
        # Wait for the response
        time.sleep(1)
        
        # Check the results
        if "strategy_agent" in self.results:
            result = self.results["strategy_agent"]
            strategy = result.get("strategy", {})
            
            logger.info(f"Repair strategy for {bug.get('pattern_id', 'unknown')} bug:")
            logger.info(f"  Name: {strategy.get('name', 'unknown')}")
            logger.info(f"  Description: {strategy.get('description', 'unknown')}")
            logger.info(f"  Estimated Complexity: {strategy.get('estimated_complexity', '?')}/10")
            logger.info(f"  Confidence: {strategy.get('confidence', '?')}")
            
            logger.info("\n  Repair Steps:")
            for i, step in enumerate(strategy.get('repair_steps', []), 1):
                logger.info(f"    {i}. {step.get('description', '')}")
            
            if strategy.get('code_examples', []):
                logger.info("\n  Code Examples:")
                for i, example in enumerate(strategy.get('code_examples', []), 1):
                    logger.info(f"    Example #{i}:\n{example}")
        else:
            logger.warning("No response received from Strategy Agent")
    
    def implement_fix(self, file_path: str):
        """
        Step 4: Implement the fix.
        
        Args:
            file_path: Path to the file to fix
        """
        logger.info("\n\n===== STEP 4: IMPLEMENTING FIX =====")
        
        # Get the strategy from the Strategy Agent
        if "strategy_agent" not in self.results:
            logger.error("No strategy results available")
            return
        
        strategy_result = self.results["strategy_agent"]
        strategy = strategy_result.get("strategy", {})
        
        if not strategy:
            logger.error("No strategy available to implement")
            return
        
        # Send a task request to the Implementation Agent
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "implement_strategy",
                "strategy": strategy,
                "additional_context": {}
            },
            sender="demo_app"
        )
        
        # Process the message
        self.implementation_agent.handle_message(message)
        
        # Wait for the response
        time.sleep(1)
        
        # Check the results
        if "implementation_agent" in self.results:
            result = self.results["implementation_agent"]
            implementation = result.get("implementation", {})
            
            logger.info(f"Implementation for {strategy.get('bug_type', 'unknown')} bug:")
            logger.info(f"  Description: {implementation.get('description', 'unknown')}")
            logger.info(f"  Approach: {implementation.get('approach', 'unknown')}")
            logger.info(f"  Risk Level: {implementation.get('risk_level', 'unknown')}")
            
            logger.info("\n  Patches:")
            for i, patch in enumerate(implementation.get('patches', []), 1):
                logger.info(f"    Patch #{i} for file: {patch.get('file_path', '')}")
                logger.info(f"      Function: {patch.get('function', '')}")
                
                changes = patch.get('changes', [])
                for j, change in enumerate(changes, 1):
                    logger.info(f"      Change #{j} - Type: {change.get('type', '')}")
                    logger.info(f"        Affects lines: {change.get('start_line', '?')}-{change.get('end_line', '?')}")
                    
                    # For brevity, only show the first few lines of content
                    content = change.get('content', '')
                    content_preview = '\n'.join(content.split('\n')[:5])
                    if len(content.split('\n')) > 5:
                        content_preview += "\n        ..."
                    logger.info(f"        Content: \n{content_preview}")
            
            # Apply the implementation in dry run mode (just for demo)
            apply_message = AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                content={
                    "action": "apply_implementation",
                    "implementation": implementation,
                    "dry_run": True  # Dry run to avoid modifying files in demo
                },
                sender="demo_app"
            )
            
            # Save the implementation for later verification
            self.results["implementation"] = implementation
            
            # Process the message
            self.implementation_agent.handle_message(apply_message)
            
            # Wait for the response
            time.sleep(1)
            
            # Check the apply results
            if "implementation_agent" in self.results:
                apply_result = self.results["implementation_agent"]
                
                logger.info("\n  Apply Result:")
                logger.info(f"    Status: {apply_result.get('status', 'unknown')}")
                logger.info(f"    Message: {apply_result.get('message', '')}")
                logger.info(f"    Dry Run: {apply_result.get('dry_run', True)}")
                
                modified_files = apply_result.get("result", {}).get("files_modified", [])
                logger.info(f"    Files Modified: {len(modified_files)}")
                for file_info in modified_files:
                    logger.info(f"      {file_info.get('file_path', '')}: {file_info.get('changes_applied', 0)} changes")
        else:
            logger.warning("No response received from Implementation Agent")
    
    def verify_fix(self, file_path: str):
        """
        Step 5: Verify the fix.
        
        Args:
            file_path: Path to the file to verify
        """
        logger.info("\n\n===== STEP 5: VERIFYING FIX =====")
        
        # Get the implementation from the previous step
        if "implementation" not in self.results:
            logger.error("No implementation results available")
            return
        
        implementation = self.results["implementation"]
        
        # Get the strategy for context
        strategy = {}
        if "strategy_agent" in self.results and "strategy" in self.results["strategy_agent"]:
            strategy = self.results["strategy_agent"]["strategy"]
        
        # Get the bug report for context
        bug_report = {}
        if "bug_detector" in self.results and "bugs" in self.results["bug_detector"]:
            bugs = self.results["bug_detector"]["bugs"]
            if bugs:
                bug_report = bugs[0]
        
        # Send a task request to the Verification Agent
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "verify_implementation",
                "implementation": implementation,
                "strategy": strategy,
                "bug_report": bug_report
            },
            sender="demo_app"
        )
        
        # Process the message
        self.verification_agent.handle_message(message)
        
        # Wait for the response
        time.sleep(1)
        
        # Check the results
        if "verification_agent" in self.results:
            result = self.results["verification_agent"]
            verification_result = result.get("verification_result", {})
            
            logger.info(f"Verification Result:")
            logger.info(f"  Overall Success: {verification_result.get('overall_success', False)}")
            logger.info(f"  Confidence: {verification_result.get('confidence', 0)}")
            
            # Show check results
            checks = verification_result.get("checks", {})
            logger.info("\n  Checks:")
            for check_name, check_result in checks.items():
                success = "✅" if check_result.get("success", False) else "❌"
                logger.info(f"    {check_name}: {success}")
                
                # Show issues
                issues = check_result.get("issues", [])
                if issues:
                    logger.info(f"      Issues:")
                    for issue in issues[:3]:  # Show first 3 issues
                        logger.info(f"        - {issue}")
                    if len(issues) > 3:
                        logger.info(f"        - ({len(issues) - 3} more issues...)")
            
            # Show recommendations
            recommendations = verification_result.get("recommendations", [])
            if recommendations:
                logger.info("\n  Recommendations:")
                for i, rec in enumerate(recommendations, 1):
                    logger.info(f"    {i}. {rec}")
        else:
            logger.warning("No response received from Verification Agent")
    
    def show_summary(self):
        """Show a summary of the self-healing process."""
        logger.info("\n\n===== SELF-HEALING SUMMARY =====")
        
        # Check if we have all the necessary results
        if all(key in self.results for key in ["bug_detector", "strategy_agent", "implementation_agent", "verification_agent"]):
            # Get bug info
            bug_report = {}
            if "bugs" in self.results["bug_detector"] and self.results["bug_detector"]["bugs"]:
                bug_report = self.results["bug_detector"]["bugs"][0]
            
            bug_type = bug_report.get("pattern_id", "unknown")
            bug_file = bug_report.get("file", "unknown")
            bug_line = bug_report.get("line", "?")
            
            # Get verification result
            verification = self.results["verification_agent"].get("verification_result", {})
            success = verification.get("overall_success", False)
            confidence = verification.get("confidence", 0)
            
            # Show summary
            logger.info(f"Bug Type: {bug_type}")
            logger.info(f"Location: {bug_file}, line {bug_line}")
            logger.info(f"Fix Success: {success}")
            logger.info(f"Confidence: {confidence:.2f}")
            
            if success:
                logger.info("\nThe self-healing workflow successfully fixed the bug!")
            else:
                logger.info("\nThe self-healing workflow was unable to fully fix the bug.")
                logger.info("Review the verification results for details on what went wrong.")
        else:
            logger.warning("Incomplete results, unable to generate summary.")
        
        logger.info("\nSelf-Healing Workflow Demo completed!")


def main():
    """Main function to run the demo."""
    # Create and run the demo
    demo = SelfHealingDemo()
    demo.run_demo()


if __name__ == "__main__":
    main()
