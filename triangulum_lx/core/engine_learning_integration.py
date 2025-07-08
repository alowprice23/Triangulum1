#!/usr/bin/env python3
"""
Engine Learning Integration

This module provides the integration layer between the core engine and learning components,
enabling seamless communication and coordination between them. It serves as the central
hub for connecting engine operations with learning capabilities.
"""

import os
import sys
import json
import time
import logging
import threading
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("triangulum.engine_learning_integration")

# Try to import required components
try:
    from triangulum_lx.core.learning_manager import LearningManager
    from triangulum_lx.core.engine_event_extension import EngineEventExtension, EngineEvent
    from triangulum_lx.core.learning_enabled_engine import LearningEnabledEngine
    HAVE_LEARNING_COMPONENTS = True
except ImportError:
    logger.warning("Learning components not available. Learning integration will be limited.")
    HAVE_LEARNING_COMPONENTS = False


class EngineLearningIntegration:
    """
    Integrates the core engine with learning components.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the engine learning integration.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path or "triangulum_lx/config/engine_learning_integration.json"
        self.config = self._load_config()
        
        # Initialize integration state
        self.integration_state = {
            "status": "initialized",
            "start_time": datetime.now().isoformat(),
            "components": {},
            "connections": {},
            "metrics": {}
        }
        
        # Initialize components
        self.learning_manager = None
        self.event_extension = None
        self.learning_engine = None
        
        if HAVE_LEARNING_COMPONENTS and self.config.get("enable_integration", True):
            self._initialize_components()
        
        # Initialize integration thread
        self.stop_event = threading.Event()
        self.integration_thread = None
        
        if self.config.get("auto_integration", True):
            self.start_integration_thread()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Configuration dictionary
        """
        default_config = {
            "enable_integration": True,
            "auto_integration": True,
            "integration_interval_seconds": 60,
            "components": {
                "learning_manager": True,
                "event_extension": True,
                "learning_engine": True
            },
            "integration_features": {
                "event_routing": True,
                "parameter_synchronization": True,
                "model_application": True,
                "feedback_collection": True,
                "metric_tracking": True
            },
            "event_types": {
                "agent_action": True,
                "agent_error": True,
                "repair_action": True,
                "verification_result": True,
                "system_metric": True,
                "user_feedback": True,
                "test_result": True,
                "performance_metric": True
            }
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # Merge with default config
                config = default_config.copy()
                self._deep_update(config, user_config)
                
                logger.info(f"Loaded configuration from {self.config_path}")
                return config
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
        
        logger.info("Using default configuration")
        return default_config
    
    def _deep_update(self, d: Dict, u: Dict) -> Dict:
        """
        Recursively update a dictionary.
        
        Args:
            d: Dictionary to update
            u: Dictionary with updates
            
        Returns:
            Updated dictionary
        """
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v
        return d
    
    def _save_config(self):
        """Save configuration to file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Save to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            
            logger.info(f"Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def _initialize_components(self):
        """Initialize components."""
        try:
            # Initialize learning manager
            if self.config["components"]["learning_manager"]:
                self.learning_manager = LearningManager()
                self.integration_state["components"]["learning_manager"] = {
                    "status": "initialized",
                    "initialized_at": datetime.now().isoformat()
                }
                logger.info("Initialized learning manager")
            
            # Initialize event extension
            if self.config["components"]["event_extension"]:
                self.event_extension = EngineEventExtension()
                self.integration_state["components"]["event_extension"] = {
                    "status": "initialized",
                    "initialized_at": datetime.now().isoformat()
                }
                logger.info("Initialized event extension")
            
            # Initialize learning engine
            if self.config["components"]["learning_engine"]:
                self.learning_engine = LearningEnabledEngine()
                self.integration_state["components"]["learning_engine"] = {
                    "status": "initialized",
                    "initialized_at": datetime.now().isoformat()
                }
                logger.info("Initialized learning engine")
                
            # Connect components
            self._connect_components()
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
    
    def _connect_components(self):
        """Connect components."""
        try:
            # Connect learning manager to event extension
            if self.learning_manager and self.event_extension:
                # Register learning manager as event handler
                # This is handled internally by the event extension
                
                self.integration_state["connections"]["learning_manager_to_event_extension"] = {
                    "status": "connected",
                    "connected_at": datetime.now().isoformat()
                }
                logger.info("Connected learning manager to event extension")
            
            # Connect learning engine to learning manager
            if self.learning_engine and self.learning_manager:
                # The learning engine already uses the learning manager internally
                
                self.integration_state["connections"]["learning_engine_to_learning_manager"] = {
                    "status": "connected",
                    "connected_at": datetime.now().isoformat()
                }
                logger.info("Connected learning engine to learning manager")
            
            # Connect learning engine to event extension
            if self.learning_engine and self.event_extension:
                # The learning engine already uses the event extension internally
                
                self.integration_state["connections"]["learning_engine_to_event_extension"] = {
                    "status": "connected",
                    "connected_at": datetime.now().isoformat()
                }
                logger.info("Connected learning engine to event extension")
            
        except Exception as e:
            logger.error(f"Error connecting components: {e}")
    
    def start_integration_thread(self):
        """Start integration thread."""
        if self.integration_thread and self.integration_thread.is_alive():
            logger.warning("Integration thread is already running")
            return
        
        logger.info("Starting integration thread")
        self.stop_event.clear()
        self.integration_thread = threading.Thread(target=self._integration_loop, daemon=True)
        self.integration_thread.start()
    
    def stop_integration_thread(self):
        """Stop integration thread."""
        if not self.integration_thread or not self.integration_thread.is_alive():
            logger.warning("Integration thread is not running")
            return
        
        logger.info("Stopping integration thread")
        self.stop_event.set()
        self.integration_thread.join(timeout=5)
        
        if self.integration_thread.is_alive():
            logger.warning("Integration thread did not terminate cleanly")
        else:
            logger.info("Integration thread stopped")
    
    def _integration_loop(self):
        """Integration loop."""
        while not self.stop_event.is_set():
            try:
                # Run integration cycle
                self._run_integration_cycle()
                
                # Sleep until next integration cycle
                sleep_seconds = self.config.get("integration_interval_seconds", 60)
                
                # Sleep in smaller increments to allow for clean shutdown
                for _ in range(sleep_seconds // 5):
                    if self.stop_event.is_set():
                        break
                    time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in integration loop: {e}")
                time.sleep(60)  # Sleep for a minute on error
    
    def _run_integration_cycle(self):
        """Run an integration cycle."""
        logger.debug("Running integration cycle")
        
        # Check which features to run
        features = [
            feature for feature, enabled in self.config.get("integration_features", {}).items()
            if enabled
        ]
        
        # Run integration features
        for feature in features:
            try:
                if feature == "event_routing":
                    self._run_event_routing()
                elif feature == "parameter_synchronization":
                    self._run_parameter_synchronization()
                elif feature == "model_application":
                    self._run_model_application()
                elif feature == "feedback_collection":
                    self._run_feedback_collection()
                elif feature == "metric_tracking":
                    self._run_metric_tracking()
            except Exception as e:
                logger.error(f"Error running integration feature {feature}: {e}")
    
    def _run_event_routing(self):
        """Run event routing."""
        # This is handled automatically by the event extension
        pass
    
    def _run_parameter_synchronization(self):
        """Run parameter synchronization."""
        if not self.learning_manager or not self.learning_engine:
            return
        
        try:
            # Synchronize parameters from learning manager to engine
            # This is handled automatically by the learning engine
            pass
            
        except Exception as e:
            logger.error(f"Error synchronizing parameters: {e}")
    
    def _run_model_application(self):
        """Run model application."""
        if not self.learning_manager or not self.learning_engine:
            return
        
        try:
            # Apply models from learning manager to engine
            # This is handled automatically by the learning engine
            pass
            
        except Exception as e:
            logger.error(f"Error applying models: {e}")
    
    def _run_feedback_collection(self):
        """Run feedback collection."""
        if not self.learning_manager or not self.learning_engine:
            return
        
        try:
            # Collect feedback from engine for learning manager
            # This is handled automatically by the learning engine
            pass
            
        except Exception as e:
            logger.error(f"Error collecting feedback: {e}")
    
    def _run_metric_tracking(self):
        """Run metric tracking."""
        if not self.learning_manager or not self.learning_engine:
            return
        
        try:
            # Track metrics from engine for learning manager
            # This is handled automatically by the learning engine
            
            # Track integration metrics
            self._track_integration_metrics()
            
        except Exception as e:
            logger.error(f"Error tracking metrics: {e}")
    
    def _track_integration_metrics(self):
        """Track integration metrics."""
        # Track component status
        for component_name, component_info in self.integration_state["components"].items():
            metric_name = f"integration_component_{component_name}_status"
            metric_value = 1.0 if component_info["status"] == "initialized" else 0.0
            
            if self.learning_manager:
                self.learning_manager.track_metric(metric_name, metric_value)
            
            # Update integration state
            if metric_name not in self.integration_state["metrics"]:
                self.integration_state["metrics"][metric_name] = []
            
            self.integration_state["metrics"][metric_name].append({
                "timestamp": datetime.now().isoformat(),
                "value": metric_value
            })
        
        # Track connection status
        for connection_name, connection_info in self.integration_state["connections"].items():
            metric_name = f"integration_connection_{connection_name}_status"
            metric_value = 1.0 if connection_info["status"] == "connected" else 0.0
            
            if self.learning_manager:
                self.learning_manager.track_metric(metric_name, metric_value)
            
            # Update integration state
            if metric_name not in self.integration_state["metrics"]:
                self.integration_state["metrics"][metric_name] = []
            
            self.integration_state["metrics"][metric_name].append({
                "timestamp": datetime.now().isoformat(),
                "value": metric_value
            })
    
    def get_learning_manager(self) -> Optional[LearningManager]:
        """
        Get the learning manager.
        
        Returns:
            Learning manager or None if not available
        """
        return self.learning_manager
    
    def get_event_extension(self) -> Optional[EngineEventExtension]:
        """
        Get the event extension.
        
        Returns:
            Event extension or None if not available
        """
        return self.event_extension
    
    def get_learning_engine(self) -> Optional[LearningEnabledEngine]:
        """
        Get the learning engine.
        
        Returns:
            Learning engine or None if not available
        """
        return self.learning_engine
    
    def get_integration_state(self) -> Dict[str, Any]:
        """
        Get the integration state.
        
        Returns:
            Integration state
        """
        return self.integration_state
    
    def shutdown(self):
        """Shut down the integration."""
        logger.info("Shutting down engine learning integration")
        
        # Stop integration thread
        self.stop_integration_thread()
        
        # Shut down learning engine
        if self.learning_engine:
            self.learning_engine.shutdown()
        
        # Update integration state
        self.integration_state["status"] = "shutdown"
        self.integration_state["shutdown_time"] = datetime.now().isoformat()
        
        logger.info("Engine learning integration shutdown complete")


def create_learning_demo(output_dir: str = "examples"):
    """
    Create learning demo files.
    
    Args:
        output_dir: Output directory for demo files
    """
    # Create learning engine demo
    learning_engine_demo = """#!/usr/bin/env python3
\"\"\"
Learning Engine Demo

This script demonstrates the capabilities of the learning-enabled engine.
\"\"\"

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
    \"\"\"Run the learning engine demo.\"\"\"
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
        before_code="user = get_user(user_id)\\nreturn user.name",
        after_code="user = get_user(user_id)\\nif user:\\n    return user.name\\nreturn None",
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
"""
    
    # Create learning system demo
    learning_system_demo = """#!/usr/bin/env python3
\"\"\"
Learning System Demo

This script demonstrates the capabilities of the complete learning system,
including the learning manager, event extension, and learning-enabled engine.
\"\"\"

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
    \"\"\"Run the learning system demo.\"\"\"
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
        before_code="user = get_user(user_id)\\nreturn user.name",
        after_code="user = get_user(user_id)\\nif user:\\n    return user.name\\nreturn None",
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
"""
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Write demo files
    with open(os.path.join(output_dir, "learning_engine_demo.py"), "w", encoding="utf-8") as f:
        f.write(learning_engine_demo)
    
    with open(os.path.join(output_dir, "learning_system_demo.py"), "w", encoding="utf-8") as f:
        f.write(learning_system_demo)
    
    logger.info(f"Created learning demo files in {output_dir}")


def main():
    """Main entry point for the engine learning integration."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Triangulum Engine Learning Integration")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the engine learning integration")
    start_parser.add_argument("--config", help="Path to configuration file")
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop the engine learning integration")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get integration status")
    
    # Create demos command
    demos_parser = subparsers.add_parser("create-demos", help="Create learning demo files")
    demos_parser.add_argument("--output-dir", default="examples", help="Output directory for demo files")
    
    args = parser.parse_args()
    
    if args.command == "create-demos":
        # Create learning demo files
        create_learning_demo(args.output_dir)
        return 0
    
    # Create integration
    integration = EngineLearningIntegration(args.config if hasattr(args, "config") else None)
    
    if args.command == "start":
        # Integration is already started by initialization
        print("Engine learning integration started")
        
        # Keep running until interrupted
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down...")
            integration.shutdown()
        
    elif args.command == "stop":
        # Shut down integration
        integration.shutdown()
        print("Engine learning integration stopped")
        
    elif args.command == "status":
        # Get integration status
        integration_state = integration.get_integration_state()
        
        print(f"Integration Status: {integration_state['status']}")
        print(f"Start Time: {integration_state['start_time']}")
        
        print("\nComponents:")
        for component_name, component_info in integration_state["components"].items():
            print(f"  {component_name}: {component_info['status']}")
        
        print("\nConnections:")
        for connection_name, connection_info in integration_state["connections"].items():
            print(f"  {connection_name}: {connection_info['status']}")
        
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
