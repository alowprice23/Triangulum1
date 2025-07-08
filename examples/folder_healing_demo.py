#!/usr/bin/env python
"""
Folder Healing Demo

This example demonstrates the complete folder-level self-healing workflow using the
orchestration agent and priority analyzer agent to coordinate repairs across multiple files.

Key features demonstrated:
1. Large-scale relationship analysis
2. Priority-based scheduling 
3. Distributed processing capabilities
4. Multi-file repair coordination

The demo creates a simulated codebase with intentional bugs, then uses the
folder healing system to detect and fix them.
"""

import os
import sys
import logging
import time
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from triangulum_lx.agents.orchestrator_agent import OrchestratorAgent
from triangulum_lx.agents.bug_detector_agent import BugDetectorAgent
from triangulum_lx.agents.relationship_analyst_agent import RelationshipAnalystAgent
from triangulum_lx.agents.priority_analyzer_agent import PriorityAnalyzerAgent
from triangulum_lx.agents.strategy_agent import StrategyAgent
from triangulum_lx.agents.implementation_agent import ImplementationAgent
from triangulum_lx.agents.verification_agent import VerificationAgent
from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.message_bus import MessageBus

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FolderHealingDemo:
    """Demonstration of the folder-level self-healing workflow."""
    
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
        
        self.priority_analyzer = PriorityAnalyzerAgent(
            agent_id="priority_analyzer",
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
        
        self.orchestrator = OrchestratorAgent(
            agent_id="orchestrator",
            message_bus=self.message_bus,
            config={
                "max_retries": 3,
                "timeout": 60,
                "parallel_execution": True
            }
        )
        
        # Setup message handlers
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
        
        # Create example project with bugs
        self.project_dir = self.create_example_project()
    
    def handle_task_result(self, message: AgentMessage):
        """Handle task result messages from agents."""
        # Store the result by sender
        self.results[message.sender] = message.content
        logger.info(f"Received task result from {message.sender}")
    
    def handle_error(self, message: AgentMessage):
        """Handle error messages from agents."""
        logger.error(f"Error from {message.sender}: {message.content.get('error', 'Unknown error')}")
    
    def create_example_project(self) -> str:
        """
        Create an example project with multiple files and intentional bugs.
        
        Returns:
            Path to the created project directory
        """
        # Create a directory for the example project
        project_dir = Path("./folder_healing_example_project")
        
        # Remove if exists
        if project_dir.exists():
            shutil.rmtree(project_dir)
        
        # Create directories
        project_dir.mkdir(exist_ok=True)
        (project_dir / "core").mkdir(exist_ok=True)
        (project_dir / "api").mkdir(exist_ok=True)
        (project_dir / "utils").mkdir(exist_ok=True)
        (project_dir / "models").mkdir(exist_ok=True)
        (project_dir / "tests").mkdir(exist_ok=True)
        
        # Create files with various bugs
        
        # 1. Core module with null pointer bug
        with open(project_dir / "core" / "data_manager.py", "w") as f:
            f.write("""
# Core data manager module

class DataManager:
    def __init__(self, config=None):
        self.config = config
        self.connections = {}
        self.initialize()
    
    def initialize(self):
        # BUG: No null check before accessing config properties
        db_name = self.config.db_name
        host = self.config.host
        
        self.logger = self._create_logger()
        self.logger.info(f"Initialized connection to {db_name} on {host}")
    
    def _create_logger(self):
        class Logger:
            def info(self, msg):
                print(f"INFO: {msg}")
            def error(self, msg):
                print(f"ERROR: {msg}")
        return Logger()
    
    def get_connection(self, name):
        return self.connections.get(name)

# Usage
if __name__ == "__main__":
    # This will cause a null pointer exception
    manager = DataManager()  # No config provided
""")
        
        # 2. API module with resource leak
        with open(project_dir / "api" / "file_handler.py", "w") as f:
            f.write("""
# API file handler

import os
from ..core.data_manager import DataManager

class FileHandler:
    def __init__(self, data_manager):
        self.data_manager = data_manager
    
    def read_data(self, file_path):
        # BUG: Resource leak - file not closed
        file = open(file_path, 'r')
        data = file.read()
        # Missing file.close()
        return data
    
    def write_data(self, file_path, content):
        # This is done correctly
        with open(file_path, 'w') as file:
            file.write(content)
        return True
    
    def process_file(self, input_path, output_path):
        data = self.read_data(input_path)
        processed = data.upper()  # Just a simple transformation
        return self.write_data(output_path, processed)

# Usage
if __name__ == "__main__":
    # Create a test file
    with open("test.txt", "w") as f:
        f.write("test data")
    
    manager = DataManager(config=type('obj', (object,), {
        'db_name': 'test_db',
        'host': 'localhost'
    }))
    handler = FileHandler(manager)
    
    # This will leak a file resource
    handler.read_data("test.txt")
    
    # Clean up
    if os.path.exists("test.txt"):
        os.remove("test.txt")
""")
        
        # 3. Utils module with exception swallowing
        with open(project_dir / "utils" / "validator.py", "w") as f:
            f.write("""
# Utility validator

class DataValidator:
    def __init__(self):
        self.validation_rules = {}
    
    def add_rule(self, field, rule_func):
        self.validation_rules[field] = rule_func
    
    def validate(self, data):
        # BUG: Exception swallowing without logging
        try:
            for field, rule in self.validation_rules.items():
                if field in data:
                    rule(data[field])
                else:
                    raise ValueError(f"Required field {field} missing")
            return True
        except Exception:
            # Silently swallowing the exception
            pass
        return False
    
    def validate_with_details(self, data):
        results = {}
        for field, rule in self.validation_rules.items():
            try:
                if field in data:
                    rule(data[field])
                    results[field] = "valid"
                else:
                    results[field] = "missing"
            except Exception as e:
                results[field] = str(e)
        return results

# Example usage
if __name__ == "__main__":
    validator = DataValidator()
    
    # Add validation rules
    validator.add_rule("email", lambda x: x.count("@") == 1)
    validator.add_rule("age", lambda x: 18 <= x <= 100)
    
    # This validation will silently fail
    data = {"name": "John"}  # Missing required fields
    result = validator.validate(data)
    print(f"Validation result: {result}")
""")
        
        # 4. Models with interdependent bugs
        with open(project_dir / "models" / "user.py", "w") as f:
            f.write("""
# User model

from ..utils.validator import DataValidator

class User:
    def __init__(self, data=None):
        self.data = data or {}
        self.validator = self._create_validator()
        
        # BUG: No validation check before using data
        self.id = data['id']
        self.name = data['name']
        self.email = data['email']
        self.age = data['age']
    
    def _create_validator(self):
        validator = DataValidator()
        validator.add_rule("id", lambda x: isinstance(x, int) and x > 0)
        validator.add_rule("name", lambda x: isinstance(x, str) and len(x) > 0)
        validator.add_rule("email", lambda x: isinstance(x, str) and "@" in x)
        validator.add_rule("age", lambda x: isinstance(x, int) and 18 <= x <= 100)
        return validator
    
    def is_valid(self):
        return self.validator.validate(self.data)
    
    def validate_with_details(self):
        return self.validator.validate_with_details(self.data)
    
    def __str__(self):
        return f"User(id={self.id}, name={self.name}, email={self.email}, age={self.age})"

# Example usage
if __name__ == "__main__":
    # This will cause KeyError
    try:
        user = User()  # No data provided
    except KeyError as e:
        print(f"Error: {e}")
""")
        
        # 5. Models with dependency on API
        with open(project_dir / "models" / "user_storage.py", "w") as f:
            f.write("""
# User storage model

from ..api.file_handler import FileHandler
from ..core.data_manager import DataManager
from .user import User
import json

class UserStorage:
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.file_handler = FileHandler(data_manager)
    
    def save_user(self, user, file_path):
        # Convert user to JSON
        user_data = {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'age': user.age
        }
        
        # Save to file
        json_data = json.dumps(user_data)
        return self.file_handler.write_data(file_path, json_data)
    
    def load_user(self, file_path):
        # BUG: No error handling if file doesn't exist
        json_data = self.file_handler.read_data(file_path)
        user_data = json.loads(json_data)
        return User(user_data)

# Example usage
if __name__ == "__main__":
    manager = DataManager(config=type('obj', (object,), {
        'db_name': 'test_db',
        'host': 'localhost'
    }))
    
    storage = UserStorage(manager)
    
    # Create a user
    user_data = {
        'id': 1,
        'name': 'John Doe',
        'email': 'john@example.com',
        'age': 30
    }
    user = User(user_data)
    
    # Save user
    storage.save_user(user, "user1.json")
    
    # Load user (will cause error if file doesn't exist)
    try:
        loaded_user = storage.load_user("non_existent_user.json")
    except Exception as e:
        print(f"Error: {e}")
""")
        
        # 6. A test file
        with open(project_dir / "tests" / "test_user.py", "w") as f:
            f.write("""
# Test for user model
import unittest
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from folder_healing_example_project.models.user import User
from folder_healing_example_project.models.user_storage import UserStorage
from folder_healing_example_project.core.data_manager import DataManager

class TestUser(unittest.TestCase):
    def setUp(self):
        self.user_data = {
            'id': 1,
            'name': 'Test User',
            'email': 'test@example.com',
            'age': 25
        }
        
        self.config = type('obj', (object,), {
            'db_name': 'test_db',
            'host': 'localhost'
        })
        
        self.data_manager = DataManager(config=self.config)
    
    def test_user_creation(self):
        user = User(self.user_data)
        self.assertEqual(user.id, 1)
        self.assertEqual(user.name, 'Test User')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.age, 25)
    
    def test_user_validation(self):
        user = User(self.user_data)
        self.assertTrue(user.is_valid())
    
    def test_user_storage(self):
        user = User(self.user_data)
        storage = UserStorage(self.data_manager)
        
        # Save user
        test_file = "test_user.json"
        self.assertTrue(storage.save_user(user, test_file))
        
        # Verify file exists and content is correct
        self.assertTrue(os.path.exists(test_file))
        with open(test_file, 'r') as f:
            content = f.read()
            data = json.loads(content)
            self.assertEqual(data['id'], 1)
        
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == '__main__':
    unittest.main()
""")
        
        # 7. Main application file that uses all modules
        with open(project_dir / "app.py", "w") as f:
            f.write("""
# Main application

from core.data_manager import DataManager
from api.file_handler import FileHandler
from utils.validator import DataValidator
from models.user import User
from models.user_storage import UserStorage
import os
import json

def main():
    # Initialize components
    config = type('obj', (object,), {
        'db_name': 'production_db',
        'host': 'db.example.com'
    })
    
    data_manager = DataManager(config=config)
    file_handler = FileHandler(data_manager)
    validator = DataValidator()
    
    # Add validation rules
    validator.add_rule("id", lambda x: isinstance(x, int) and x > 0)
    validator.add_rule("name", lambda x: isinstance(x, str) and len(x) > 0)
    validator.add_rule("email", lambda x: isinstance(x, str) and "@" in x)
    validator.add_rule("age", lambda x: isinstance(x, int) and 18 <= x <= 100)
    
    # Initialize storage
    user_storage = UserStorage(data_manager)
    
    # Create and save users
    users_data = [
        {
            'id': 1,
            'name': 'John Doe',
            'email': 'john@example.com',
            'age': 30
        },
        {
            'id': 2,
            'name': 'Jane Smith',
            'email': 'jane@example.com',
            'age': 25
        }
    ]
    
    for user_data in users_data:
        # Validate data
        if validator.validate(user_data):
            # Create user
            user = User(user_data)
            
            # Save user
            file_path = f"user_{user.id}.json"
            if user_storage.save_user(user, file_path):
                print(f"Saved user: {user}")
            else:
                print(f"Failed to save user: {user}")
        else:
            print(f"Invalid user data: {user_data}")
    
    # Load and display users
    for i in range(1, 3):
        try:
            file_path = f"user_{i}.json"
            if os.path.exists(file_path):
                user = user_storage.load_user(file_path)
                print(f"Loaded user: {user}")
            else:
                print(f"User file not found: {file_path}")
        except Exception as e:
            print(f"Error loading user {i}: {str(e)}")
    
    # Clean up
    for i in range(1, 3):
        file_path = f"user_{i}.json"
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    main()
""")
        
        # 8. Create an __init__.py file in each directory
        for dir_path in [
            project_dir,
            project_dir / "core",
            project_dir / "api",
            project_dir / "utils",
            project_dir / "models",
            project_dir / "tests"
        ]:
            with open(dir_path / "__init__.py", "w") as f:
                f.write("# Initialize package\n")
        
        logger.info(f"Created example project at: {project_dir}")
        return str(project_dir)
    
    def run_folder_healing(self, dry_run: bool = True):
        """
        Run the folder-level self-healing process on the example project.
        
        Args:
            dry_run: If True, don't apply fixes
        """
        logger.info(f"Starting folder-level self-healing for: {self.project_dir}")
        
        # Configure options for the orchestrator
        options = {
            "dry_run": dry_run,
            "max_files": 10,
            "analysis_depth": 3,
            "workers": 2
        }
        
        # Send the orchestration request
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "orchestrate_folder_healing",
                "folder_path": self.project_dir,
                "options": options
            },
            sender="demo_app",
            recipient="orchestrator"
        )
        
        # Process the message
        self.orchestrator.handle_message(message)
        
        # Wait for the result (with timeout)
        start_time = time.time()
        timeout = 300  # 5 minutes timeout
        
        while time.time() - start_time < timeout:
            if "orchestrator" in self.results:
                result = self.results["orchestrator"]
                
                if result.get("status") == "success":
                    logger.info("Folder healing completed successfully!")
                    return result.get("result", {})
                elif result.get("status") == "error":
                    logger.error(f"Folder healing failed: {result.get('error', 'Unknown error')}")
                    return {}
            
            # Sleep a bit to avoid busy waiting
            time.sleep(1)
            
            # Print a progress indicator
            if int(time.time()) % 5 == 0:
                logger.info("Healing in progress...")
        
        # Timeout
        logger.error("Folder healing timed out")
        return {}
    
    def display_results(self, result: Dict[str, Any], dry_run: bool):
        """
        Display the results of the healing process.
        
        Args:
            result: Results of the healing process
            dry_run: Whether this was a dry run
        """
        print("\n" + "=" * 80)
        print(f"{'FOLDER HEALING RESULTS (DRY RUN)' if dry_run else 'FOLDER HEALING RESULTS'}")
        print("=" * 80)
        
        # Display summary information
        print(f"\nTarget folder: {result.get('target', 'unknown')}")
        print(f"Status: {result.get('status', 'unknown')}")
        
        # Display metrics
        metrics = result.get("metrics", {})
        if metrics:
            print("\nMetrics:")
            print(f"  Files analyzed: {metrics.get('files_analyzed', 0)}")
            print(f"  Files with bugs: {metrics.get('files_with_bugs', 0)}")
            print(f"  Files processed: {metrics.get('files_processed', 0)}")
            print(f"  Files healed: {metrics.get('files_healed', 0)}")
            print(f"  Files failed: {metrics.get('files_failed', 0)}")
            print(f"  Total bugs detected: {metrics.get('bugs_detected', 0)}")
            print(f"  Bugs fixed: {metrics.get('bugs_fixed', 0)}")
            
            if metrics.get('files_processed', 0) > 0:
                success_rate = (metrics.get('files_healed', 0) / metrics.get('files_processed', 0)) * 100
                print(f"  Success rate: {success_rate:.1f}%")
        
        # Display files that were healed
        files_healed = result.get("files_healed", [])
        if files_healed:
            print("\nFiles healed:")
            for i, file_path in enumerate(files_healed, 1):
                print(f"  {i}. {file_path}")
        
        # Display files that failed
        files_failed = result.get("files_failed", [])
        if files_failed:
            print("\nFiles that could not be healed:")
            for i, file_path in enumerate(files_failed, 1):
                print(f"  {i}. {file_path}")
        
        # Display prioritization info
        results = result.get("results", {})
        priority_result = results.get("priority_analyzer", {})
        
        if priority_result:
            print("\nFile Prioritization:")
            file_priorities = priority_result.get("file_priorities", {})
            ranked_files = priority_result.get("ranked_files", [])
            
            for i, file_path in enumerate(ranked_files[:5], 1):
                priority = file_priorities.get(file_path, {}).get("priority", 0)
                bug_count = file_priorities.get(file_path, {}).get("bug_count", 0)
                print(f"  {i}. {file_path}")
                print(f"     Priority: {priority:.2f}, Bugs: {bug_count}")
        
        # If it was a dry run, remind the user
        if dry_run:
            print("\nThis was a dry run. No files were modified.")
        
        print("\n" + "=" * 80)
    
    def cleanup(self):
        """Clean up the example project."""
        project_dir = Path(self.project_dir)
        if project_dir.exists():
            logger.info(f"Cleaning up: {project_dir}")
            shutil.rmtree(project_dir)


def main():
    """Run the folder healing demo."""
    # Create and run the demo
    demo = FolderHealingDemo()
    
    try:
        # First do a dry run
        print("\nRunning folder healing (DRY RUN)...")
        dry_run_result = demo.run_folder_healing(dry_run=True)
        demo.display_results(dry_run_result, dry_run=True)
        
        # Ask if we should apply the fixes
        apply_fixes = input("\nApply the fixes? (y/n): ").lower() == 'y'
        
        if apply_fixes:
            print("\nApplying fixes...")
            result = demo.run_folder_healing(dry_run=False)
            demo.display_results(result, dry_run=False)
        
        # Ask if we should clean up
        clean_up = input("\nClean up the example project? (y/n): ").lower() == 'y'
        
        if clean_up:
            demo.cleanup()
            print("Example project cleaned up.")
        else:
            print(f"Example project remains at: {demo.project_dir}")
            print("You can explore the files and see the fixes applied.")
    
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    except Exception as e:
        logger.error(f"Error in demo: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
    
    print("\nFolder Healing Demo completed.")


if __name__ == "__main__":
    main()
