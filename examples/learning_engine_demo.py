#!/usr/bin/env python3
"""
Learning Engine Demo

This script demonstrates the capabilities of the learning-enabled engine.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("triangulum.learning_engine_demo")

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import learning components
from triangulum_lx.core.learning_enabled_engine import LearningEnabledEngine


def run_demo():
    """Run the learning engine demo."""
    logger.info("Starting learning engine demo")
    
    # Create learning engine
    engine = LearningEnabledEngine()
    
    # Register agents
    engine.register_agent(
        agent_id="bug_detector",
        agent_type="detector",
        agent_info={
            "description": "Detects bugs in code",
            "capabilities": ["static_analysis", "pattern_matching", "context_aware_detection"]
        }
    )
    
    engine.register_agent(
        agent_id="verification",
        agent_type="verifier",
        agent_info={
            "description": "Verifies code changes",
            "capabilities": ["test_running", "static_analysis", "regression_detection"]
        }
    )
    
    # Register tasks
    engine.register_task(
        task_id="fix_bug_1",
        task_type="bug_fix",
        task_info={
            "description": "Fix null pointer bug in user authentication",
            "priority": "high",
            "file_path": "auth/user_auth.py"
        }
    )
    
    # Track metrics
    engine.track_metric("bug_detection_accuracy", 0.95)
    engine.track_metric("verification_time_seconds", 3.2)
    engine.track_metric("fix_success_rate", 0.87)
    
    # Update task status
    engine.update_task_status(
        task_id="fix_bug_1",
        status="in_progress",
        result=None
    )
    
    # Simulate some work
    time.sleep(2)
    
    # Collect repair data
    engine.collect_repair_data(
        bug_type="null_pointer",
        before_code="user = get_user(user_id)\nreturn user.name",
        after_code="user = get_user(user_id)\nif user:\n    return user.name\nreturn None",
        file_path="auth/user_auth.py",
        bug_description="Null pointer when user doesn't exist",
        fix_description="Added null check before accessing user.name"
    )
    
    # Update task status
    engine.update_task_status(
        task_id="fix_bug_1",
        status="completed",
        result={
            "success": True,
            "fix_description": "Added null check before accessing user.name",
            "verification_result": "passed"
        }
    )
    
    # Collect feedback
    engine.collect_feedback(
        source_type="user",
        content="The fix works correctly and handles all edge cases",
        context={
            "task_id": "fix_bug_1",
            "user_id": "user123"
        },
        metadata={
            "rating": 5,
            "time_spent_minutes": 10
        }
    )
    
    # Track more metrics
    engine.track_metric("user_satisfaction", 4.8)
    engine.track_metric("system_response_time", 0.8)
    
    # Wait for events to be processed
    time.sleep(2)
    
    # Shut down engine
    engine.shutdown()
    
    logger.info("Learning engine demo completed")


if __name__ == "__main__":
    run_demo()
