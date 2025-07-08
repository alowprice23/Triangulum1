#!/usr/bin/env python3
"""
Engine Event Extension

This module extends the core engine with event handling capabilities to support
learning and continuous improvement. It provides mechanisms for capturing engine
events, routing them to learning components, and applying learned improvements
back to the engine.
"""

import os
import json
import time
import logging
import threading
import uuid
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("triangulum.engine_event_extension")

# Try to import learning components
try:
    from triangulum_lx.core.learning_manager import LearningManager
    HAVE_LEARNING_MANAGER = True
except ImportError:
    logger.warning("Learning manager not available. Learning capabilities will be limited.")
    HAVE_LEARNING_MANAGER = False


class EngineEvent:
    """
    Represents an event in the engine that can be used for learning.
    """
    
    def __init__(self, 
                 event_type: str,
                 source: str,
                 data: Dict[str, Any],
                 timestamp: Optional[datetime] = None):
        """
        Initialize an engine event.
        
        Args:
            event_type: Type of event
            source: Source of the event
            data: Event data
            timestamp: Event timestamp
        """
        self.event_type = event_type
        self.source = source
        self.data = data
        self.timestamp = timestamp or datetime.now()
        self.event_id = f"event_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EngineEvent':
        """Create event from dictionary."""
        event = cls(
            event_type=data["event_type"],
            source=data["source"],
            data=data["data"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"]
        )
        event.event_id = data["event_id"]
        return event


class EventHandler:
    """
    Base class for event handlers.
    """
    
    def __init__(self, event_types: List[str]):
        """
        Initialize an event handler.
        
        Args:
            event_types: Types of events this handler can process
        """
        self.event_types = event_types
    
    def can_handle(self, event: EngineEvent) -> bool:
        """
        Check if this handler can handle the given event.
        
        Args:
            event: Event to check
            
        Returns:
            True if this handler can handle the event, False otherwise
        """
        return event.event_type in self.event_types
    
    def handle_event(self, event: EngineEvent) -> bool:
        """
        Handle an event.
        
        Args:
            event: Event to handle
            
        Returns:
            True if the event was handled successfully, False otherwise
        """
        raise NotImplementedError("Subclasses must implement handle_event")


class LearningEventHandler(EventHandler):
    """
    Event handler that routes events to the learning manager.
    """
    
    def __init__(self, learning_manager: LearningManager, event_types: Optional[List[str]] = None):
        """
        Initialize a learning event handler.
        
        Args:
            learning_manager: Learning manager to route events to
            event_types: Types of events this handler can process (None for all)
        """
        super().__init__(event_types or [
            "agent_action", "agent_error", "repair_action", "verification_result",
            "system_metric", "user_feedback", "test_result", "performance_metric"
        ])
        self.learning_manager = learning_manager
    
    def handle_event(self, event: EngineEvent) -> bool:
        """
        Handle an event by routing it to the learning manager.
        
        Args:
            event: Event to handle
            
        Returns:
            True if the event was handled successfully, False otherwise
        """
        try:
            # Route event to appropriate learning component based on type
            if event.event_type == "repair_action":
                self._handle_repair_action(event)
            elif event.event_type == "verification_result":
                self._handle_verification_result(event)
            elif event.event_type == "user_feedback":
                self._handle_user_feedback(event)
            elif event.event_type == "test_result":
                self._handle_test_result(event)
            elif event.event_type == "performance_metric":
                self._handle_performance_metric(event)
            elif event.event_type in ["agent_action", "agent_error"]:
                self._handle_agent_event(event)
            elif event.event_type == "system_metric":
                self._handle_system_metric(event)
            else:
                # Generic handling for other event types
                self._handle_generic_event(event)
            
            return True
        except Exception as e:
            logger.error(f"Error handling event {event.event_id}: {e}")
            return False
    
    def _handle_repair_action(self, event: EngineEvent):
        """
        Handle a repair action event.
        
        Args:
            event: Repair action event
        """
        # Extract repair data
        repair_data = event.data.get("repair_data", {})
        
        # Collect repair data for learning
        if "before_code" in repair_data and "after_code" in repair_data:
            self.learning_manager.collect_repair_data(
                bug_type=repair_data.get("bug_type", "unknown"),
                before_code=repair_data.get("before_code", ""),
                after_code=repair_data.get("after_code", ""),
                file_path=repair_data.get("file_path", "unknown"),
                bug_description=repair_data.get("bug_description"),
                fix_description=repair_data.get("fix_description")
            )
    
    def _handle_verification_result(self, event: EngineEvent):
        """
        Handle a verification result event.
        
        Args:
            event: Verification result event
        """
        # Extract verification data
        verification_data = event.data.get("verification_data", {})
        
        # Collect feedback for learning
        self.learning_manager.collect_feedback(
            source_type="test",
            content=f"Verification result: {verification_data.get('result', 'unknown')}. "
                    f"{verification_data.get('message', '')}",
            context={
                "verification_type": verification_data.get("verification_type", "unknown"),
                "file_path": verification_data.get("file_path", "unknown"),
                "success": verification_data.get("success", False)
            },
            metadata={
                "metrics": verification_data.get("metrics", {}),
                "details": verification_data.get("details", {})
            }
        )
        
        # Track verification metrics
        if "metrics" in verification_data:
            for metric_name, value in verification_data["metrics"].items():
                if isinstance(value, (int, float)):
                    self.learning_manager.track_metric(f"verification_{metric_name}", value)
    
    def _handle_user_feedback(self, event: EngineEvent):
        """
        Handle a user feedback event.
        
        Args:
            event: User feedback event
        """
        # Extract feedback data
        feedback_data = event.data.get("feedback_data", {})
        
        # Collect feedback for learning
        self.learning_manager.collect_feedback(
            source_type="user",
            content=feedback_data.get("content", ""),
            context=feedback_data.get("context", {}),
            metadata=feedback_data.get("metadata", {})
        )
    
    def _handle_test_result(self, event: EngineEvent):
        """
        Handle a test result event.
        
        Args:
            event: Test result event
        """
        # Extract test data
        test_data = event.data.get("test_data", {})
        
        # Collect feedback for learning
        self.learning_manager.collect_feedback(
            source_type="test",
            content=f"Test result: {test_data.get('result', 'unknown')}. "
                    f"{test_data.get('message', '')}",
            context={
                "test_name": test_data.get("test_name", "unknown"),
                "test_type": test_data.get("test_type", "unknown"),
                "success": test_data.get("success", False)
            },
            metadata={
                "metrics": test_data.get("metrics", {}),
                "details": test_data.get("details", {})
            }
        )
        
        # Track test metrics
        if "metrics" in test_data:
            for metric_name, value in test_data["metrics"].items():
                if isinstance(value, (int, float)):
                    self.learning_manager.track_metric(f"test_{metric_name}", value)
    
    def _handle_performance_metric(self, event: EngineEvent):
        """
        Handle a performance metric event.
        
        Args:
            event: Performance metric event
        """
        # Extract metric data
        metric_data = event.data.get("metric_data", {})
        
        # Track performance metrics
        for metric_name, value in metric_data.items():
            if isinstance(value, (int, float)):
                self.learning_manager.track_metric(metric_name, value)
    
    def _handle_agent_event(self, event: EngineEvent):
        """
        Handle an agent event.
        
        Args:
            event: Agent event
        """
        # Extract agent data
        agent_data = event.data.get("agent_data", {})
        
        # Collect feedback for learning
        if event.event_type == "agent_error":
            self.learning_manager.collect_feedback(
                source_type="system",
                content=f"Agent error: {agent_data.get('error', 'unknown')}. "
                        f"{agent_data.get('message', '')}",
                context={
                    "agent_type": agent_data.get("agent_type", "unknown"),
                    "agent_id": agent_data.get("agent_id", "unknown"),
                    "action": agent_data.get("action", "unknown")
                },
                metadata={
                    "stack_trace": agent_data.get("stack_trace", ""),
                    "details": agent_data.get("details", {})
                }
            )
        else:
            # Track agent metrics
            if "metrics" in agent_data:
                for metric_name, value in agent_data["metrics"].items():
                    if isinstance(value, (int, float)):
                        self.learning_manager.track_metric(f"agent_{metric_name}", value)
    
    def _handle_system_metric(self, event: EngineEvent):
        """
        Handle a system metric event.
        
        Args:
            event: System metric event
        """
        # Extract metric data
        metric_data = event.data.get("metric_data", {})
        
        # Track system metrics
        for metric_name, value in metric_data.items():
            if isinstance(value, (int, float)):
                self.learning_manager.track_metric(f"system_{metric_name}", value)
    
    def _handle_generic_event(self, event: EngineEvent):
        """
        Handle a generic event.
        
        Args:
            event: Generic event
        """
        # Log the event
        logger.info(f"Received generic event: {event.event_type} from {event.source}")
        
        # Track event count
        self.learning_manager.track_metric(f"event_count_{event.event_type}", 1.0)


class EngineEventExtension:
    """
    Extends the core engine with event handling capabilities.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the engine event extension.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path or "triangulum_lx/config/engine_event_extension.json"
        self.config = self._load_config()
        
        # Initialize event handlers
        self.event_handlers: List[EventHandler] = []
        
        # Initialize learning manager if available
        self.learning_manager = None
        if HAVE_LEARNING_MANAGER and self.config.get("enable_learning", True):
            self.learning_manager = LearningManager()
            self.event_handlers.append(LearningEventHandler(self.learning_manager))
        
        # Initialize event queue
        self.event_queue = deque()
        self.queue_lock = threading.Lock()
        
        # Initialize event processing thread
        self.stop_event = threading.Event()
        self.processing_thread = None
        
        if self.config.get("auto_process_events", True):
            self.start_event_processing()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Configuration dictionary
        """
        default_config = {
            "enable_learning": True,
            "auto_process_events": True,
            "max_queue_size": 1000,
            "processing_interval_ms": 100,
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
    
    def register_event_handler(self, handler: EventHandler):
        """
        Register an event handler.
        
        Args:
            handler: Event handler to register
        """
        self.event_handlers.append(handler)
        logger.info(f"Registered event handler for event types: {handler.event_types}")
    
    def unregister_event_handler(self, handler: EventHandler):
        """
        Unregister an event handler.
        
        Args:
            handler: Event handler to unregister
        """
        if handler in self.event_handlers:
            self.event_handlers.remove(handler)
            logger.info(f"Unregistered event handler for event types: {handler.event_types}")
    
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
        # Check if event type is enabled
        if not self.config.get("event_types", {}).get(event_type, True):
            return "event_type_disabled"
        
        # Create event
        event = EngineEvent(event_type, source, data)
        
        # Process event
        if immediate:
            self._process_event(event)
        else:
            with self.queue_lock:
                # Check queue size
                max_queue_size = self.config.get("max_queue_size", 1000)
                if len(self.event_queue) >= max_queue_size:
                    # Remove oldest event
                    self.event_queue.popleft()
                
                # Add event to queue
                self.event_queue.append(event)
        
        return event.event_id
    
    def start_event_processing(self):
        """Start event processing thread."""
        if self.processing_thread and self.processing_thread.is_alive():
            logger.warning("Event processing thread is already running")
            return
        
        logger.info("Starting event processing thread")
        self.stop_event.clear()
        self.processing_thread = threading.Thread(target=self._event_processing_loop, daemon=True)
        self.processing_thread.start()
    
    def stop_event_processing(self):
        """Stop event processing thread."""
        if not self.processing_thread or not self.processing_thread.is_alive():
            logger.warning("Event processing thread is not running")
            return
        
        logger.info("Stopping event processing thread")
        self.stop_event.set()
        self.processing_thread.join(timeout=5)
        
        if self.processing_thread.is_alive():
            logger.warning("Event processing thread did not terminate cleanly")
        else:
            logger.info("Event processing thread stopped")
    
    def _event_processing_loop(self):
        """Event processing loop."""
        while not self.stop_event.is_set():
            try:
                # Process events in queue
                events_to_process = []
                
                with self.queue_lock:
                    # Get all events from queue
                    while self.event_queue and len(events_to_process) < 100:  # Process up to 100 events at a time
                        events_to_process.append(self.event_queue.popleft())
                
                # Process events
                for event in events_to_process:
                    self._process_event(event)
                
                # Sleep for a short time
                processing_interval = self.config.get("processing_interval_ms", 100) / 1000.0
                time.sleep(processing_interval)
                
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
                time.sleep(1.0)  # Sleep for a second on error
    
    def _process_event(self, event: EngineEvent):
        """
        Process an event.
        
        Args:
            event: Event to process
        """
        # Find handlers for this event
        handlers = [h for h in self.event_handlers if h.can_handle(event)]
        
        if not handlers:
            logger.debug(f"No handlers found for event {event.event_id} of type {event.event_type}")
            return
        
        # Process event with each handler
        for handler in handlers:
            try:
                handler.handle_event(event)
            except Exception as e:
                logger.error(f"Error handling event {event.event_id} with handler {handler.__class__.__name__}: {e}")
    
    def get_learning_manager(self) -> Optional[LearningManager]:
        """
        Get the learning manager.
        
        Returns:
            Learning manager or None if not available
        """
        return self.learning_manager


class CustomEventHandler(EventHandler):
    """
    Custom event handler for specific event processing.
    """
    
    def __init__(self, event_types: List[str], handler_func: Callable[[EngineEvent], bool]):
        """
        Initialize a custom event handler.
        
        Args:
            event_types: Types of events this handler can process
            handler_func: Function to handle events
        """
        super().__init__(event_types)
        self.handler_func = handler_func
    
    def handle_event(self, event: EngineEvent) -> bool:
        """
        Handle an event using the provided handler function.
        
        Args:
            event: Event to handle
            
        Returns:
            True if the event was handled successfully, False otherwise
        """
        return self.handler_func(event)


def main():
    """Main entry point for the engine event extension."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Triangulum Engine Event Extension")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the engine event extension")
    start_parser.add_argument("--config", help="Path to configuration file")
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop the engine event extension")
    
    # Emit command
    emit_parser = subparsers.add_parser("emit", help="Emit an event")
    emit_parser.add_argument("--type", required=True, help="Event type")
    emit_parser.add_argument("--source", required=True, help="Event source")
    emit_parser.add_argument("--data", required=True, help="JSON string with event data")
    emit_parser.add_argument("--immediate", action="store_true", help="Process event immediately")
    
    args = parser.parse_args()
    
    # Create engine event extension
    extension = EngineEventExtension(args.config if hasattr(args, "config") else None)
    
    if args.command == "start":
        # Start event processing
        extension.start_event_processing()
        print("Engine event extension started")
        
    elif args.command == "stop":
        # Stop event processing
        extension.stop_event_processing()
        print("Engine event extension stopped")
        
    elif args.command == "emit":
        # Parse event data
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError:
            print(f"Error parsing event data JSON: {args.data}")
            return 1
        
        # Emit event
        event_id = extension.emit_event(
            event_type=args.type,
            source=args.source,
            data=data,
            immediate=args.immediate
        )
        
        print(f"Emitted event with ID: {event_id}")
        
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
