#!/usr/bin/env python3
"""
Learning System Demo

This script demonstrates the capabilities of the complete learning system,
including the learning manager, event extension, and learning-enabled engine.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("triangulum.learning_system_demo")

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import learning components
from triangulum_lx.core.learning_manager import LearningManager
from triangulum_lx.core.engine_event_extension import EngineEventExtension
from triangulum_lx.core.learning_enabled_engine import LearningEnabledEngine
from triangulum_lx.core.engine_learning_integration import EngineLearningIntegration


def run_demo():
    """Run the learning system demo."""
    logger.info("Starting learning system demo")
    
    # Create integration
    integration = EngineLearningIntegration()
    
    # Get components
    learning_manager = integration.get_learning_manager()
    event_extension = integration.get_event_extension()
    learning_engine = integration.get_learning_engine()
    
    if not learning_manager or not event_extension or not learning_engine:
        logger.error("Failed to initialize learning components")
        return
    
    # Start learning session
    session_id = learning_manager.start_learning_session(
        session_type="demo_session",
        context={
            "description": "Learning system demo session",
            "start_time": datetime.now().isoformat()
        }
    )
    
    logger.info(f"Started learning session {session_id}")
    
    # Register model
    learning_manager.register_model(
        model_id="bug_detection_model",
        model_type="classifier",
        description="Model for detecting bugs in code",
        parameters={
            "algorithm": "random_forest",
            "feature_count": 128,
            "max_depth": 10
        },
        metrics={
            "accuracy": 0.92,
            "precision": 0.89,
            "recall": 0.94,
            "f1_score": 0.91
        }
    )
    
    # Register agents
    learning_engine.register_agent(
        agent_id="bug_detector",
        agent_type="detector",
        agent_info={
            "description": "Detects bugs in code",
            "capabilities": ["static_analysis", "pattern_matching", "context_aware_detection"]
        }
    )
    
    learning_engine.register_agent(
        agent_id="verification",
        agent_type="verifier",
        agent_info={
            "description": "Verifies code changes",
            "capabilities": ["test_running", "static_analysis", "regression_detection"]
        }
    )
    
    # Register tasks
    learning_engine.register_task(
        task_id="fix_bug_1",
        task_type="bug_fix",
        task_info={
            "description": "Fix null pointer bug in user authentication",
            "priority": "high",
            "file_path": "auth/user_auth.py"
        }
    )
    
    # Track metrics
    learning_engine.track_metric("bug_detection_accuracy", 0.95)
    learning_engine.track_metric("verification_time_seconds", 3.2)
    learning_engine.track_metric("fix_success_rate", 0.87)
    
    # Update task status
    learning_engine.update_task_status(
        task_id="fix_bug_1",
        status="in_progress",
        result=None
    )
    
    # Simulate some work
    time.sleep(2)
    
    # Collect repair data
    learning_engine.collect_repair_data(
        bug_type="null_pointer",
        before_code="user = get_user(user_id)\nreturn user.name",
        after_code="user = get_user(user_id)\nif user:\n    return user.name\nreturn None",
        file_path="auth/user_auth.py",
        bug_description="Null pointer when user doesn't exist",
        fix_description="Added null check before accessing user.name"
    )
    
    # Update task status
    learning_engine.update_task_status(
        task_id="fix_bug_1",
        status="completed",
        result={
            "success": True,
            "fix_description": "Added null check before accessing user.name",
            "verification_result": "passed"
        }
    )
    
    # Collect feedback
    learning_engine.collect_feedback(
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
    learning_engine.track_metric("user_satisfaction", 4.8)
    learning_engine.track_metric("system_response_time", 0.8)
    
    # Record session event
    learning_manager.record_session_event(
        session_id=session_id,
        event_type="demo_completed",
        event_data={
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
    )
    
    # Record session metric
    learning_manager.record_session_metric(
        session_id=session_id,
        metric_name="demo_duration_seconds",
        value=time.time() - datetime.fromisoformat(
            learning_manager.learning_sessions[session_id]["start_time"]
        ).timestamp()
    )
    
    # End learning session
    learning_manager.end_learning_session(
        session_id=session_id,
        results={
            "status": "completed",
            "end_time": datetime.now().isoformat(),
            "metrics": {
                "bug_detection_accuracy": 0.95,
                "verification_time_seconds": 3.2,
                "fix_success_rate": 0.87,
                "user_satisfaction": 4.8,
                "system_response_time": 0.8
            }
        }
    )
    
    logger.info(f"Ended learning session {session_id}")
    
    # Wait for events to be processed
    time.sleep(2)
    
    # Shut down integration
    integration.shutdown()
    
    logger.info("Learning system demo completed")


if __name__ == "__main__":
    run_demo()
