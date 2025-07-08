#!/usr/bin/env python3
"""
Learning Enabled Engine

This module extends the core Triangulum engine with learning capabilities,
integrating the learning components with the engine's operation. It provides
a learning-enabled version of the engine that can improve over time based on
operational experience and feedback.
"""

import os
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
logger = logging.getLogger("triangulum.learning_enabled_engine")

# Try to import required components
try:
    from triangulum_lx.core.learning_manager import LearningManager
    from triangulum_lx.core.engine_event_extension import EngineEventExtension, EngineEvent
    HAVE_LEARNING_COMPONENTS = True
except ImportError:
    logger.warning("Learning components not available. Learning capabilities will be limited.")
    HAVE_LEARNING_COMPONENTS = False


class LearningEnabledEngine:
    """
    Extends the core engine with learning capabilities.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the learning-enabled engine.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path or "triangulum_lx/config/learning_enabled_engine.json"
        self.config = self._load_config()
        
        # Initialize learning components
        self.learning_manager = None
        self.event_extension = None
        
        if HAVE_LEARNING_COMPONENTS and self.config.get("enable_learning", True):
            self._initialize_learning_components()
        
        # Initialize engine state
        self.engine_state = {
            "status": "initialized",
            "start_time": datetime.now().isoformat(),
            "agents": {},
            "tasks": {},
            "metrics": {},
            "parameters": {}
        }
        
        # Initialize learning session
        self.learning_session_id = None
        if self.learning_manager and self.config.get("auto_start_learning_session", True):
            self._start_learning_session()
        
        # Initialize improvement thread
        self.stop_event = threading.Event()
        self.improvement_thread = None
        
        if self.config.get("auto_improvement", False):
            self.start_improvement_thread()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Configuration dictionary
        """
        default_config = {
            "enable_learning": True,
            "auto_start_learning_session": True,
            "auto_improvement": False,
            "improvement_interval_hours": 24,
            "learning_components": {
                "learning_manager": True,
                "event_extension": True
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
            },
            "improvement_strategies": {
                "parameter_tuning": True,
                "model_updating": True,
                "pattern_refinement": True
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
    
    def _initialize_learning_components(self):
        """Initialize learning components."""
        try:
            # Initialize learning manager
            if self.config["learning_components"]["learning_manager"]:
                self.learning_manager = LearningManager()
                logger.info("Initialized learning manager")
            
            # Initialize event extension
            if self.config["learning_components"]["event_extension"]:
                self.event_extension = EngineEventExtension()
                logger.info("Initialized event extension")
                
        except Exception as e:
            logger.error(f"Error initializing learning components: {e}")
    
    def _start_learning_session(self):
        """Start a learning session."""
        if not self.learning_manager:
            logger.warning("Learning manager not available. Cannot start learning session.")
            return
        
        try:
            # Start learning session
            self.learning_session_id = self.learning_manager.start_learning_session(
                session_type="engine_session",
                context={
                    "engine_state": self.engine_state,
                    "config": self.config
                }
            )
            
            logger.info(f"Started learning session {self.learning_session_id}")
        except Exception as e:
            logger.error(f"Error starting learning session: {e}")
    
    def _end_learning_session(self):
        """End the current learning session."""
        if not self.learning_manager or not self.learning_session_id:
            return
        
        try:
            # End learning session
            self.learning_manager.end_learning_session(
                session_id=self.learning_session_id,
                results={
                    "engine_state": self.engine_state,
                    "end_time": datetime.now().isoformat(),
                    "duration_seconds": (datetime.now() - datetime.fromisoformat(self.engine_state["start_time"])).total_seconds()
                }
            )
            
            logger.info(f"Ended learning session {self.learning_session_id}")
            self.learning_session_id = None
        except Exception as e:
            logger.error(f"Error ending learning session: {e}")
    
    def start_improvement_thread(self):
        """Start improvement thread."""
        if self.improvement_thread and self.improvement_thread.is_alive():
            logger.warning("Improvement thread is already running")
            return
        
        logger.info("Starting improvement thread")
        self.stop_event.clear()
        self.improvement_thread = threading.Thread(target=self._improvement_loop, daemon=True)
        self.improvement_thread.start()
    
    def stop_improvement_thread(self):
        """Stop improvement thread."""
        if not self.improvement_thread or not self.improvement_thread.is_alive():
            logger.warning("Improvement thread is not running")
            return
        
        logger.info("Stopping improvement thread")
        self.stop_event.set()
        self.improvement_thread.join(timeout=5)
        
        if self.improvement_thread.is_alive():
            logger.warning("Improvement thread did not terminate cleanly")
        else:
            logger.info("Improvement thread stopped")
    
    def _improvement_loop(self):
        """Improvement loop."""
        while not self.stop_event.is_set():
            try:
                # Run improvement cycle
                self._run_improvement_cycle()
                
                # Sleep until next improvement cycle
                sleep_hours = self.config.get("improvement_interval_hours", 24)
                sleep_seconds = sleep_hours * 3600
                
                # Sleep in smaller increments to allow for clean shutdown
                for _ in range(sleep_seconds // 60):
                    if self.stop_event.is_set():
                        break
                    time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in improvement loop: {e}")
                time.sleep(3600)  # Sleep for an hour on error
    
    def _run_improvement_cycle(self):
        """Run an improvement cycle."""
        logger.info("Running improvement cycle")
        
        # Check which strategies to use
        strategies = [
            strategy for strategy, enabled in self.config.get("improvement_strategies", {}).items()
            if enabled
        ]
        
        # Run improvement strategies
        for strategy in strategies:
            try:
                if strategy == "parameter_tuning":
                    self._run_parameter_tuning()
                elif strategy == "model_updating":
                    self._run_model_updating()
                elif strategy == "pattern_refinement":
                    self._run_pattern_refinement()
            except Exception as e:
                logger.error(f"Error running improvement strategy {strategy}: {e}")
        
        logger.info("Improvement cycle completed")
    
    def _run_parameter_tuning(self):
        """Run parameter tuning."""
        logger.info("Running parameter tuning")
        
        # This is a placeholder for parameter tuning logic
        # In a real implementation, this would use the learning components
        # to tune engine parameters based on collected data and feedback
        pass
    
    def _run_model_updating(self):
        """Run model updating."""
        logger.info("Running model updating")
        
        # This is a placeholder for model updating logic
        # In a real implementation, this would use the learning components
        # to update models based on collected data and feedback
        pass
    
    def _run_pattern_refinement(self):
        """Run pattern refinement."""
        logger.info("Running pattern refinement")
        
        # This is a placeholder for pattern refinement logic
        # In a real implementation, this would use the learning components
        # to refine repair patterns based on collected data and feedback
        pass
    
    def emit_event(self, 
                  event_type: str,
                  source: str,
                  data: Dict[str, Any],
                  immediate: bool = False) -> str:
        """
        Emit an event.
        
        Args:
            event_type: Type of event
            source: Source of the event
            data: Event data
            immediate: Whether to process the event immediately
            
        Returns:
            Event ID
        """
        if not self.event_extension:
            logger.warning("Event extension not available. Cannot emit event.")
            return "event_extension_not_available"
        
        # Check if event type is enabled
        if not self.config.get("event_types", {}).get(event_type, True):
            return "event_type_disabled"
        
        # Emit event
        return self.event_extension.emit_event(
            event_type=event_type,
            source=source,
            data=data,
            immediate=immediate
        )
    
    def register_agent(self, agent_id: str, agent_type: str, agent_info: Dict[str, Any]):
        """
        Register an agent with the engine.
        
        Args:
            agent_id: Agent ID
            agent_type: Agent type
            agent_info: Agent information
        """
        # Update engine state
        self.engine_state["agents"][agent_id] = {
            "agent_type": agent_type,
            "registered_at": datetime.now().isoformat(),
            "status": "registered",
            "info": agent_info
        }
        
        # Emit event
        self.emit_event(
            event_type="agent_registered",
            source="engine",
            data={
                "agent_data": {
                    "agent_id": agent_id,
                    "agent_type": agent_type,
                    "info": agent_info
                }
            }
        )
        
        logger.info(f"Registered agent {agent_id} of type {agent_type}")
    
    def unregister_agent(self, agent_id: str):
        """
        Unregister an agent from the engine.
        
        Args:
            agent_id: Agent ID
        """
        if agent_id not in self.engine_state["agents"]:
            logger.warning(f"Agent {agent_id} not registered")
            return
        
        # Update agent status
        self.engine_state["agents"][agent_id]["status"] = "unregistered"
        self.engine_state["agents"][agent_id]["unregistered_at"] = datetime.now().isoformat()
        
        # Emit event
        self.emit_event(
            event_type="agent_unregistered",
            source="engine",
            data={
                "agent_data": {
                    "agent_id": agent_id,
                    "agent_type": self.engine_state["agents"][agent_id]["agent_type"]
                }
            }
        )
        
        logger.info(f"Unregistered agent {agent_id}")
    
    def register_task(self, task_id: str, task_type: str, task_info: Dict[str, Any]):
        """
        Register a task with the engine.
        
        Args:
            task_id: Task ID
            task_type: Task type
            task_info: Task information
        """
        # Update engine state
        self.engine_state["tasks"][task_id] = {
            "task_type": task_type,
            "registered_at": datetime.now().isoformat(),
            "status": "registered",
            "info": task_info
        }
        
        # Emit event
        self.emit_event(
            event_type="task_registered",
            source="engine",
            data={
                "task_data": {
                    "task_id": task_id,
                    "task_type": task_type,
                    "info": task_info
                }
            }
        )
        
        logger.info(f"Registered task {task_id} of type {task_type}")
    
    def update_task_status(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None):
        """
        Update the status of a task.
        
        Args:
            task_id: Task ID
            status: New task status
            result: Task result
        """
        if task_id not in self.engine_state["tasks"]:
            logger.warning(f"Task {task_id} not registered")
            return
        
        # Update task status
        self.engine_state["tasks"][task_id]["status"] = status
        self.engine_state["tasks"][task_id]["updated_at"] = datetime.now().isoformat()
        
        if result:
            self.engine_state["tasks"][task_id]["result"] = result
        
        # Emit event
        self.emit_event(
            event_type="task_status_updated",
            source="engine",
            data={
                "task_data": {
                    "task_id": task_id,
                    "task_type": self.engine_state["tasks"][task_id]["task_type"],
                    "status": status,
                    "result": result
                }
            }
        )
        
        logger.info(f"Updated task {task_id} status to {status}")
    
    def track_metric(self, metric_name: str, value: float):
        """
        Track a metric.
        
        Args:
            metric_name: Metric name
            value: Metric value
        """
        # Update engine state
        if metric_name not in self.engine_state["metrics"]:
            self.engine_state["metrics"][metric_name] = []
        
        self.engine_state["metrics"][metric_name].append({
            "timestamp": datetime.now().isoformat(),
            "value": value
        })
        
        # Limit metrics history
        if len(self.engine_state["metrics"][metric_name]) > 1000:
            self.engine_state["metrics"][metric_name] = self.engine_state["metrics"][metric_name][-1000:]
        
        # Emit event
        self.emit_event(
            event_type="performance_metric",
            source="engine",
            data={
                "metric_data": {
                    metric_name: value
                }
            }
        )
        
        # Track metric in learning manager
        if self.learning_manager:
            self.learning_manager.track_metric(metric_name, value)
    
    def get_parameter(self, name: str, default: Optional[Any] = None) -> Any:
        """
        Get a parameter value.
        
        Args:
            name: Parameter name
            default: Default value if parameter doesn't exist
            
        Returns:
            Parameter value or default
        """
        # Check engine parameters
        if name in self.engine_state["parameters"]:
            return self.engine_state["parameters"][name]
        
        # Check learning manager parameters
        if self.learning_manager:
            return self.learning_manager.get_parameter(name, default)
        
        return default
    
    def set_parameter(self, name: str, value: Any) -> bool:
        """
        Set a parameter value.
        
        Args:
            name: Parameter name
            value: Parameter value
            
        Returns:
            True if parameter was set successfully, False otherwise
        """
        # Update engine state
        self.engine_state["parameters"][name] = value
        
        # Emit event
        self.emit_event(
            event_type="parameter_updated",
            source="engine",
            data={
                "parameter_data": {
                    "name": name,
                    "value": value
                }
            }
        )
        
        # Set parameter in learning manager
        if self.learning_manager:
            return self.learning_manager.set_parameter(name, value)
        
        return True
    
    def collect_feedback(self, 
                        source_type: str,
                        content: str,
                        context: Dict[str, Any],
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Collect feedback.
        
        Args:
            source_type: Type of feedback source (user, test, system)
            content: Feedback content text
            context: Contextual information about the feedback
            metadata: Additional metadata about the feedback
            
        Returns:
            Feedback ID
        """
        # Emit event
        self.emit_event(
            event_type="user_feedback",
            source="engine",
            data={
                "feedback_data": {
                    "source_type": source_type,
                    "content": content,
                    "context": context,
                    "metadata": metadata or {}
                }
            }
        )
        
        # Collect feedback in learning manager
        if self.learning_manager:
            return self.learning_manager.collect_feedback(
                source_type=source_type,
                content=content,
                context=context,
                metadata=metadata
            )
        
        return "learning_manager_not_available"
    
    def collect_repair_data(self, 
                           bug_type: str,
                           before_code: str,
                           after_code: str,
                           file_path: str,
                           bug_description: Optional[str] = None,
                           fix_description: Optional[str] = None) -> str:
        """
        Collect repair data.
        
        Args:
            bug_type: Type of bug that was fixed
            before_code: Code before the fix
            after_code: Code after the fix
            file_path: Path to the file that was fixed
            bug_description: Description of the bug
            fix_description: Description of the fix
            
        Returns:
            Data ID
        """
        # Emit event
        self.emit_event(
            event_type="repair_action",
            source="engine",
            data={
                "repair_data": {
                    "bug_type": bug_type,
                    "before_code": before_code,
                    "after_code": after_code,
                    "file_path": file_path,
                    "bug_description": bug_description,
                    "fix_description": fix_description
                }
            }
        )
        
        # Collect repair data in learning manager
        if self.learning_manager:
            return self.learning_manager.collect_repair_data(
                bug_type=bug_type,
                before_code=before_code,
                after_code=after_code,
                file_path=file_path,
                bug_description=bug_description,
                fix_description=fix_description
            )
        
        return "learning_manager_not_available"
    
    def shutdown(self):
        """Shut down the engine."""
        logger.info("Shutting down learning-enabled engine")
        
        # Stop improvement thread
        self.stop_improvement_thread()
        
        # End learning session
        self._end_learning_session()
        
        # Update engine state
        self.engine_state["status"] = "shutdown"
        self.engine_state["shutdown_time"] = datetime.now().isoformat()
        
        # Emit event
        if self.event_extension:
            self.emit_event(
                event_type="engine_shutdown",
                source="engine",
                data={
                    "engine_state": self.engine_state
                },
                immediate=True
            )
            
            # Stop event processing
            self.event_extension.stop_event_processing()
        
        logger.info("Learning-enabled engine shutdown complete")


def main():
    """Main entry point for the learning-enabled engine."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Triangulum Learning-Enabled Engine")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the learning-enabled engine")
    start_parser.add_argument("--config", help="Path to configuration file")
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop the learning-enabled engine")
    
    # Emit event command
    emit_parser = subparsers.add_parser("emit", help="Emit an event")
    emit_parser.add_argument("--type", required=True, help="Event type")
    emit_parser.add_argument("--source", required=True, help="Event source")
    emit_parser.add_argument("--data", required=True, help="JSON string with event data")
    
    # Track metric command
    track_parser = subparsers.add_parser("track", help="Track a metric")
    track_parser.add_argument("--name", required=True, help="Metric name")
    track_parser.add_argument("--value", required=True, type=float, help="Metric value")
    
    # Collect feedback command
    feedback_parser = subparsers.add_parser("feedback", help="Collect feedback")
    feedback_parser.add_argument("--source", required=True, choices=["user", "test", "system"], help="Feedback source type")
    feedback_parser.add_argument("--content", required=True, help="Feedback content text")
    feedback_parser.add_argument("--context", help="JSON string with context information")
    feedback_parser.add_argument("--metadata", help="JSON string with metadata")
    
    args = parser.parse_args()
    
    # Create learning-enabled engine
    engine = LearningEnabledEngine(args.config if hasattr(args, "config") else None)
    
    if args.command == "start":
        # Engine is already started by initialization
        print("Learning-enabled engine started")
        
        # Keep running until interrupted
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down...")
            engine.shutdown()
        
    elif args.command == "stop":
        # Shut down engine
        engine.shutdown()
        print("Learning-enabled engine stopped")
        
    elif args.command == "emit":
        # Parse event data
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError:
            print(f"Error parsing event data JSON: {args.data}")
            return 1
        
        # Emit event
        event_id = engine.emit_event(
            event_type=args.type,
            source=args.source,
            data=data
        )
        
        print(f"Emitted event with ID: {event_id}")
        
    elif args.command == "track":
        # Track metric
        engine.track_metric(args.name, args.value)
        print(f"Tracked metric {args.name} with value {args.value}")
        
    elif args.command == "feedback":
        # Parse context and metadata
        context = {}
        if args.context:
            try:
                context = json.loads(args.context)
            except json.JSONDecodeError:
                print(f"Error parsing context JSON: {args.context}")
                return 1
        
        metadata = {}
        if args.metadata:
            try:
                metadata = json.loads(args.metadata)
            except json.JSONDecodeError:
                print(f"Error parsing metadata JSON: {args.metadata}")
                return 1
        
        # Collect feedback
        feedback_id = engine.collect_feedback(
            source_type=args.source,
            content=args.content,
            context=context,
            metadata=metadata
        )
        
        print(f"Collected feedback with ID: {feedback_id}")
        
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
