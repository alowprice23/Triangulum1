#!/usr/bin/env python3
"""
Learning Manager

This module coordinates learning activities across the Triangulum system, managing
the integration of learning components with the core engine. It provides a centralized
interface for learning operations, data collection, model management, and improvement
tracking.
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
logger = logging.getLogger("triangulum.learning_manager")

# Try to import learning components
try:
    from triangulum_lx.learning.repair_pattern_extractor import RepairPatternExtractor
    from triangulum_lx.learning.feedback_processor import FeedbackProcessor
    from triangulum_lx.learning.continuous_improvement import ContinuousImprovement
    HAVE_LEARNING_COMPONENTS = True
except ImportError:
    logger.warning("Learning components not available. Some functionality will be limited.")
    HAVE_LEARNING_COMPONENTS = False


class LearningManager:
    """
    Manages learning activities and coordinates learning components.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the learning manager.
        
        Args:
            config_path: Path to the learning configuration file
        """
        self.config_path = config_path or "triangulum_lx/config/learning_config.json"
        self.config = self._load_config()
        
        # Initialize learning components if available
        self.repair_pattern_extractor = None
        self.feedback_processor = None
        self.continuous_improvement = None
        
        if HAVE_LEARNING_COMPONENTS and self.config.get("enable_learning", True):
            self._initialize_learning_components()
        
        # Initialize learning data collection
        self.learning_data = defaultdict(list)
        self.learning_events = []
        self.learning_sessions = {}
        
        # Initialize model registry
        self.models = {}
        self.model_versions = defaultdict(list)
        
        # Initialize learning metrics
        self.metrics = defaultdict(list)
        
        # Start background thread for learning coordination
        self.stop_event = threading.Event()
        self.learning_thread = None
        
        if self.config.get("auto_learning", False):
            self.start_learning_thread()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load learning configuration from file.
        
        Returns:
            Configuration dictionary
        """
        default_config = {
            "enable_learning": True,
            "auto_learning": False,
            "learning_interval_hours": 24,
            "data_collection": {
                "max_events": 10000,
                "max_age_days": 30,
                "collection_enabled": True
            },
            "components": {
                "repair_pattern_extractor": True,
                "feedback_processor": True,
                "continuous_improvement": True
            },
            "model_management": {
                "max_versions_per_model": 5,
                "auto_cleanup": True
            }
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # Merge with default config
                config = default_config.copy()
                self._deep_update(config, user_config)
                
                logger.info(f"Loaded learning configuration from {self.config_path}")
                return config
            except Exception as e:
                logger.error(f"Error loading learning configuration: {e}")
        
        logger.info("Using default learning configuration")
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
        """Save learning configuration to file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Save to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            
            logger.info(f"Saved learning configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving learning configuration: {e}")
    
    def _initialize_learning_components(self):
        """Initialize learning components."""
        try:
            # Initialize repair pattern extractor
            if self.config["components"]["repair_pattern_extractor"]:
                self.repair_pattern_extractor = RepairPatternExtractor()
                logger.info("Initialized repair pattern extractor")
            
            # Initialize feedback processor
            if self.config["components"]["feedback_processor"]:
                self.feedback_processor = FeedbackProcessor()
                logger.info("Initialized feedback processor")
            
            # Initialize continuous improvement
            if self.config["components"]["continuous_improvement"]:
                self.continuous_improvement = ContinuousImprovement()
                logger.info("Initialized continuous improvement")
                
        except Exception as e:
            logger.error(f"Error initializing learning components: {e}")
    
    def start_learning_thread(self):
        """Start background learning thread."""
        if self.learning_thread and self.learning_thread.is_alive():
            logger.warning("Learning thread is already running")
            return
        
        logger.info("Starting learning thread")
        self.stop_event.clear()
        self.learning_thread = threading.Thread(target=self._learning_loop, daemon=True)
        self.learning_thread.start()
    
    def stop_learning_thread(self):
        """Stop background learning thread."""
        if not self.learning_thread or not self.learning_thread.is_alive():
            logger.warning("Learning thread is not running")
            return
        
        logger.info("Stopping learning thread")
        self.stop_event.set()
        self.learning_thread.join(timeout=5)
        
        if self.learning_thread.is_alive():
            logger.warning("Learning thread did not terminate cleanly")
        else:
            logger.info("Learning thread stopped")
    
    def _learning_loop(self):
        """Background thread for learning coordination."""
        while not self.stop_event.is_set():
            try:
                # Run learning cycle
                self._run_learning_cycle()
                
                # Sleep until next learning cycle
                sleep_hours = self.config.get("learning_interval_hours", 24)
                sleep_seconds = sleep_hours * 3600
                
                # Sleep in smaller increments to allow for clean shutdown
                for _ in range(sleep_seconds // 60):
                    if self.stop_event.is_set():
                        break
                    time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in learning loop: {e}")
                time.sleep(3600)  # Sleep for an hour on error
    
    def _run_learning_cycle(self):
        """Run a learning cycle."""
        logger.info("Running learning cycle")
        
        # Process collected data
        self._process_learning_data()
        
        # Update models
        self._update_models()
        
        # Clean up old data
        self._cleanup_old_data()
        
        logger.info("Learning cycle completed")
    
    def _process_learning_data(self):
        """Process collected learning data."""
        if not self.learning_data:
            logger.info("No learning data to process")
            return
        
        logger.info(f"Processing {sum(len(data) for data in self.learning_data.values())} learning data items")
        
        # Process repair patterns
        if self.repair_pattern_extractor and "repair" in self.learning_data:
            for repair_data in self.learning_data["repair"]:
                try:
                    self.repair_pattern_extractor.extract_pattern(
                        bug_type=repair_data.get("bug_type", "unknown"),
                        before_code=repair_data.get("before_code", ""),
                        after_code=repair_data.get("after_code", ""),
                        file_path=repair_data.get("file_path", "unknown"),
                        bug_description=repair_data.get("bug_description"),
                        fix_description=repair_data.get("fix_description")
                    )
                except Exception as e:
                    logger.error(f"Error extracting repair pattern: {e}")
        
        # Process feedback
        if self.feedback_processor and "feedback" in self.learning_data:
            for feedback_data in self.learning_data["feedback"]:
                try:
                    self.feedback_processor.add_feedback(
                        source_type=feedback_data.get("source_type", "system"),
                        content=feedback_data.get("content", ""),
                        context=feedback_data.get("context", {}),
                        metadata=feedback_data.get("metadata", {})
                    )
                except Exception as e:
                    logger.error(f"Error processing feedback: {e}")
        
        # Process performance metrics
        if self.continuous_improvement and "performance" in self.learning_data:
            for metric_data in self.learning_data["performance"]:
                try:
                    self.continuous_improvement.track_performance(
                        metric_name=metric_data.get("metric_name", "unknown"),
                        value=metric_data.get("value", 0.0)
                    )
                except Exception as e:
                    logger.error(f"Error tracking performance: {e}")
        
        # Clear processed data
        self.learning_data.clear()
    
    def _update_models(self):
        """Update models based on learning."""
        if not self.continuous_improvement:
            return
        
        logger.info("Updating models based on learning")
        
        # This is a placeholder for model updating logic
        # In a real implementation, this would use the continuous improvement
        # system to update models based on collected data and feedback
        pass
    
    def _cleanup_old_data(self):
        """Clean up old learning data."""
        # Get data collection config
        data_config = self.config.get("data_collection", {})
        max_events = data_config.get("max_events", 10000)
        max_age_days = data_config.get("max_age_days", 30)
        
        # Clean up old events
        if len(self.learning_events) > max_events:
            self.learning_events = self.learning_events[-max_events:]
        
        # Clean up old events by age
        if max_age_days > 0:
            cutoff = datetime.now() - timedelta(days=max_age_days)
            self.learning_events = [
                event for event in self.learning_events
                if event.get("timestamp", datetime.now()) >= cutoff
            ]
        
        # Clean up old sessions
        active_sessions = {}
        for session_id, session in self.learning_sessions.items():
            if session.get("end_time") is None or \
               datetime.fromisoformat(session.get("end_time", datetime.now().isoformat())) >= cutoff:
                active_sessions[session_id] = session
        
        self.learning_sessions = active_sessions
        
        # Clean up old model versions
        max_versions = self.config.get("model_management", {}).get("max_versions_per_model", 5)
        for model_id, versions in self.model_versions.items():
            if len(versions) > max_versions:
                # Keep only the most recent versions
                versions.sort(key=lambda v: v.get("created_at", ""))
                self.model_versions[model_id] = versions[-max_versions:]
    
    def collect_repair_data(self, 
                           bug_type: str,
                           before_code: str,
                           after_code: str,
                           file_path: str,
                           bug_description: Optional[str] = None,
                           fix_description: Optional[str] = None) -> str:
        """
        Collect data about a code repair for learning.
        
        Args:
            bug_type: Type of bug that was fixed
            before_code: Code before the fix
            after_code: Code after the fix
            file_path: Path to the file that was fixed
            bug_description: Description of the bug
            fix_description: Description of the fix
            
        Returns:
            ID of the collected data
        """
        if not self.config.get("data_collection", {}).get("collection_enabled", True):
            return "collection_disabled"
        
        data_id = f"repair_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        repair_data = {
            "data_id": data_id,
            "timestamp": datetime.now().isoformat(),
            "bug_type": bug_type,
            "before_code": before_code,
            "after_code": after_code,
            "file_path": file_path,
            "bug_description": bug_description,
            "fix_description": fix_description
        }
        
        self.learning_data["repair"].append(repair_data)
        
        # Record learning event
        self._record_learning_event("repair_data_collected", {
            "data_id": data_id,
            "bug_type": bug_type,
            "file_path": file_path
        })
        
        logger.info(f"Collected repair data {data_id} for bug type {bug_type}")
        return data_id
    
    def collect_feedback(self, 
                        source_type: str,
                        content: str,
                        context: Dict[str, Any],
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Collect feedback for learning.
        
        Args:
            source_type: Type of feedback source (user, test, system)
            content: Feedback content text
            context: Contextual information about the feedback
            metadata: Additional metadata about the feedback
            
        Returns:
            ID of the collected feedback
        """
        if not self.config.get("data_collection", {}).get("collection_enabled", True):
            return "collection_disabled"
        
        feedback_id = f"feedback_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        feedback_data = {
            "feedback_id": feedback_id,
            "timestamp": datetime.now().isoformat(),
            "source_type": source_type,
            "content": content,
            "context": context,
            "metadata": metadata or {}
        }
        
        self.learning_data["feedback"].append(feedback_data)
        
        # Record learning event
        self._record_learning_event("feedback_collected", {
            "feedback_id": feedback_id,
            "source_type": source_type
        })
        
        logger.info(f"Collected feedback {feedback_id} from {source_type}")
        return feedback_id
    
    def track_metric(self, metric_name: str, value: float):
        """
        Track a performance metric for learning.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
        """
        if not self.config.get("data_collection", {}).get("collection_enabled", True):
            return
        
        metric_data = {
            "timestamp": datetime.now().isoformat(),
            "metric_name": metric_name,
            "value": value
        }
        
        self.learning_data["performance"].append(metric_data)
        self.metrics[metric_name].append((datetime.now(), value))
        
        # Limit metrics history
        if len(self.metrics[metric_name]) > 1000:
            self.metrics[metric_name] = self.metrics[metric_name][-1000:]
        
        # Record learning event
        self._record_learning_event("metric_tracked", {
            "metric_name": metric_name,
            "value": value
        })
    
    def _record_learning_event(self, event_type: str, event_data: Dict[str, Any]):
        """
        Record a learning event.
        
        Args:
            event_type: Type of event
            event_data: Event data
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "event_data": event_data
        }
        
        self.learning_events.append(event)
        
        # Limit events history
        max_events = self.config.get("data_collection", {}).get("max_events", 10000)
        if len(self.learning_events) > max_events:
            self.learning_events = self.learning_events[-max_events:]
    
    def start_learning_session(self, session_type: str, context: Dict[str, Any]) -> str:
        """
        Start a learning session.
        
        Args:
            session_type: Type of learning session
            context: Session context information
            
        Returns:
            Session ID
        """
        session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        session = {
            "session_id": session_id,
            "session_type": session_type,
            "context": context,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "events": [],
            "metrics": {}
        }
        
        self.learning_sessions[session_id] = session
        
        # Record learning event
        self._record_learning_event("session_started", {
            "session_id": session_id,
            "session_type": session_type
        })
        
        logger.info(f"Started learning session {session_id} of type {session_type}")
        return session_id
    
    def end_learning_session(self, session_id: str, results: Dict[str, Any]):
        """
        End a learning session.
        
        Args:
            session_id: Session ID
            results: Session results
        """
        if session_id not in self.learning_sessions:
            logger.warning(f"Learning session {session_id} not found")
            return
        
        session = self.learning_sessions[session_id]
        session["end_time"] = datetime.now().isoformat()
        session["results"] = results
        
        # Record learning event
        self._record_learning_event("session_ended", {
            "session_id": session_id,
            "session_type": session["session_type"],
            "duration_seconds": (datetime.now() - datetime.fromisoformat(session["start_time"])).total_seconds()
        })
        
        logger.info(f"Ended learning session {session_id}")
    
    def record_session_event(self, session_id: str, event_type: str, event_data: Dict[str, Any]):
        """
        Record an event in a learning session.
        
        Args:
            session_id: Session ID
            event_type: Type of event
            event_data: Event data
        """
        if session_id not in self.learning_sessions:
            logger.warning(f"Learning session {session_id} not found")
            return
        
        session = self.learning_sessions[session_id]
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "event_data": event_data
        }
        
        session["events"].append(event)
    
    def record_session_metric(self, session_id: str, metric_name: str, value: float):
        """
        Record a metric in a learning session.
        
        Args:
            session_id: Session ID
            metric_name: Name of the metric
            value: Metric value
        """
        if session_id not in self.learning_sessions:
            logger.warning(f"Learning session {session_id} not found")
            return
        
        session = self.learning_sessions[session_id]
        
        if metric_name not in session["metrics"]:
            session["metrics"][metric_name] = []
        
        session["metrics"][metric_name].append({
            "timestamp": datetime.now().isoformat(),
            "value": value
        })
    
    def register_model(self, 
                      model_id: str,
                      model_type: str,
                      description: str,
                      parameters: Dict[str, Any],
                      metrics: Dict[str, float],
                      file_path: Optional[str] = None) -> bool:
        """
        Register a model in the model registry.
        
        Args:
            model_id: Unique identifier for the model
            model_type: Type of model
            description: Model description
            parameters: Model parameters
            metrics: Model performance metrics
            file_path: Path to the model file
            
        Returns:
            True if model was registered successfully, False otherwise
        """
        if model_id in self.models:
            logger.warning(f"Model {model_id} already exists")
            return False
        
        # Create model entry
        model = {
            "model_id": model_id,
            "model_type": model_type,
            "description": description,
            "parameters": parameters,
            "metrics": metrics,
            "file_path": file_path,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": 1
        }
        
        self.models[model_id] = model
        
        # Add to version history
        if model_id not in self.model_versions:
            self.model_versions[model_id] = []
        
        self.model_versions[model_id].append(model.copy())
        
        # Record learning event
        self._record_learning_event("model_registered", {
            "model_id": model_id,
            "model_type": model_type
        })
        
        logger.info(f"Registered model {model_id} of type {model_type}")
        return True
    
    def update_model(self, 
                    model_id: str,
                    parameters: Optional[Dict[str, Any]] = None,
                    metrics: Optional[Dict[str, float]] = None,
                    file_path: Optional[str] = None) -> bool:
        """
        Update a model in the registry.
        
        Args:
            model_id: Model ID
            parameters: Updated model parameters
            metrics: Updated model performance metrics
            file_path: Updated path to the model file
            
        Returns:
            True if model was updated successfully, False otherwise
        """
        if model_id not in self.models:
            logger.warning(f"Model {model_id} not found")
            return False
        
        model = self.models[model_id]
        
        # Update model entry
        if parameters is not None:
            model["parameters"] = parameters
        
        if metrics is not None:
            model["metrics"] = metrics
        
        if file_path is not None:
            model["file_path"] = file_path
        
        model["updated_at"] = datetime.now().isoformat()
        model["version"] += 1
        
        # Add to version history
        self.model_versions[model_id].append(model.copy())
        
        # Limit version history
        max_versions = self.config.get("model_management", {}).get("max_versions_per_model", 5)
        if len(self.model_versions[model_id]) > max_versions:
            self.model_versions[model_id] = self.model_versions[model_id][-max_versions:]
        
        # Record learning event
        self._record_learning_event("model_updated", {
            "model_id": model_id,
            "version": model["version"]
        })
        
        logger.info(f"Updated model {model_id} to version {model['version']}")
        return True
    
    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a model from the registry.
        
        Args:
            model_id: Model ID
            
        Returns:
            Model entry or None if model doesn't exist
        """
        if model_id not in self.models:
            logger.warning(f"Model {model_id} not found")
            return None
        
        return self.models[model_id]
    
    def get_model_version(self, model_id: str, version: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific version of a model.
        
        Args:
            model_id: Model ID
            version: Model version
            
        Returns:
            Model version entry or None if not found
        """
        if model_id not in self.model_versions:
            logger.warning(f"Model {model_id} not found")
            return None
        
        for model_version in self.model_versions[model_id]:
            if model_version["version"] == version:
                return model_version
        
        logger.warning(f"Model {model_id} version {version} not found")
        return None
    
    def get_models_by_type(self, model_type: str) -> List[Dict[str, Any]]:
        """
        Get all models of a specific type.
        
        Args:
            model_type: Model type
            
        Returns:
            List of model entries
        """
        return [
            model for model in self.models.values()
            if model["model_type"] == model_type
        ]
    
    def get_learning_events(self, 
                           event_type: Optional[str] = None,
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get learning events.
        
        Args:
            event_type: Filter by event type
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of events to return
            
        Returns:
            List of learning events
        """
        filtered_events = []
        
        for event in reversed(self.learning_events):  # Most recent first
            # Apply filters
            if event_type and event["event_type"] != event_type:
                continue
            
            event_time = datetime.fromisoformat(event["timestamp"])
            
            if start_time and event_time < start_time:
                continue
            
            if end_time and event_time > end_time:
                continue
            
            filtered_events.append(event)
            
            if len(filtered_events) >= limit:
                break
        
        return filtered_events
    
    def get_learning_sessions(self, 
                             session_type: Optional[str] = None,
                             active_only: bool = False,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get learning sessions.
        
        Args:
            session_type: Filter by session type
            active_only: Only return active sessions
            limit: Maximum number of sessions to return
            
        Returns:
            List of learning sessions
        """
        filtered_sessions = []
        
        # Sort sessions by start time (most recent first)
        sorted_sessions = sorted(
            self.learning_sessions.values(),
            key=lambda s: s["start_time"],
            reverse=True
        )
        
        for session in sorted_sessions:
            # Apply filters
            if session_type and session["session_type"] != session_type:
                continue
            
            if active_only and session["end_time"] is not None:
                continue
            
            filtered_sessions.append(session)
            
            if len(filtered_sessions) >= limit:
                break
        
        return filtered_sessions
    
    def get_metric_history(self, 
                          metric_name: str,
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> List[Tuple[datetime, float]]:
        """
        Get history for a specific metric.
        
        Args:
            metric_name: Name of the metric
            start_time: Filter by start time
            end_time: Filter by end time
            
        Returns:
            List of (timestamp, value) tuples
        """
        if metric_name not in self.metrics:
            return []
        
        filtered_metrics = []
        
        for timestamp, value in self.metrics[metric_name]:
            # Apply filters
            if start_time and timestamp < start_time:
                continue
            
            if end_time and timestamp > end_time:
                continue
            
            filtered_metrics.append((timestamp, value))
        
        return filtered_metrics
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """
        Get a summary of learning activities.
        
        Returns:
            Dictionary with learning summary
        """
        # Count events by type
        event_counts = defaultdict(int)
        for event in self.learning_events:
            event_counts[event["event_type"]] += 1
        
        # Count sessions by type
        session_counts = defaultdict(int)
        active_sessions = 0
        for session in self.learning_sessions.values():
            session_counts[session["session_type"]] += 1
            if session["end_time"] is None:
                active_sessions += 1
        
        # Count models by type
        model_counts = defaultdict(int)
        for model in self.models.values():
            model_counts[model["model_type"]] += 1
        
        # Get recent metrics
        recent_metrics = {}
        for metric_name, values in self.metrics.items():
            if values:
                recent_metrics[metric_name] = values[-1][1]  # Most recent value
        
        return {
            "total_events": len(self.learning_events),
            "event_counts": dict(event_counts),
            "total_sessions": len(self.learning_sessions),
            "active_sessions": active_sessions,
            "session_counts": dict(session_counts),
            "total_models": len(self.models),
            "model_counts": dict(model_counts),
            "recent_metrics": recent_metrics,
            "learning_enabled": self.config.get("enable_learning", True),
            "auto_learning": self.config.get("auto_learning", False),
            "components_available": {
                "repair_pattern_extractor": self.repair_pattern_extractor is not None,
                "feedback_processor": self.feedback_processor is not None,
                "continuous_improvement": self.continuous_improvement is not None
            }
        }


def main():
    """Main entry point for the learning manager."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Triangulum Learning Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the learning manager")
    start_parser.add_argument("--config", help="Path to configuration file")
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop the learning manager")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get learning manager status")
    
    # Collect repair data command
    collect_repair_parser = subparsers.add_parser("collect-repair", help="Collect repair data")
    collect_repair_parser.add_argument("--bug-type", required=True, help="Type of bug that was fixed")
    collect_repair_parser.add_argument("--before-file", required=True, help="File with code before the fix")
    collect_repair_parser.add_argument("--after-file", required=True, help="File with code after the fix")
    collect_repair_parser.add_argument("--file-path", required=True, help="Path to the file that was fixed")
    collect_repair_parser.add_argument("--bug-description", help="Description of the bug")
    collect_repair_parser.add_argument("--fix-description", help="Description of the fix")
    
    # Collect feedback command
    collect_feedback_parser = subparsers.add_parser("collect-feedback", help="Collect feedback")
    collect_feedback_parser.add_argument("--source", required=True, choices=["user", "test", "system"], help="Feedback source type")
    collect_feedback_parser.add_argument("--content", required=True, help="Feedback content text")
    collect_feedback_parser.add_argument("--context", help="JSON string with context information")
    collect_feedback_parser.add_argument("--metadata", help="JSON string with metadata")
    
    # Track metric command
    track_metric_parser = subparsers.add_parser("track-metric", help="Track a performance metric")
    track_metric_parser.add_argument("--name", required=True, help="Metric name")
    track_metric_parser.add_argument("--value", required=True, type=float, help="Metric value")
    
    # Model commands
    model_parser = subparsers.add_parser("model", help="Model management")
    model_subparsers = model_parser.add_subparsers(dest="model_command", help="Model command")
    
    # Register model
    register_model_parser = model_subparsers.add_parser("register", help="Register a model")
    register_model_parser.add_argument("--id", required=True, help="Model ID")
    register_model_parser.add_argument("--type", required=True, help="Model type")
    register_model_parser.add_argument("--description", required=True, help="Model description")
    register_model_parser.add_argument("--parameters", required=True, help="JSON string with model parameters")
    register_model_parser.add_argument("--metrics", required=True, help="JSON string with model metrics")
    register_model_parser.add_argument("--file-path", help="Path to the model file")
    
    # Get model
    get_model_parser = model_subparsers.add_parser("get", help="Get a model")
    get_model_parser.add_argument("--id", required=True, help="Model ID")
    
    # List models
    list_models_parser = model_subparsers.add_parser("list", help="List models")
    list_models_parser.add_argument("--type", help="Filter by model type")
    
    args = parser.parse_args()
    
    # Create learning manager
    manager = LearningManager(args.config if hasattr(args, "config") else None)
    
    if args.command == "start":
        # Start learning manager
        manager.start_learning_thread()
        print("Learning manager started")
        
    elif args.command == "stop":
        # Stop learning manager
        manager.stop_learning_thread()
        print("Learning manager stopped")
        
    elif args.command == "status":
        # Get learning manager status
        summary = manager.get_learning_summary()
        
        print(f"Learning Manager Status:")
        print(f"Learning enabled: {summary['learning_enabled']}")
        print(f"Auto learning: {summary['auto_learning']}")
        print(f"Total events: {summary['total_events']}")
        print(f"Total sessions: {summary['total_sessions']} (active: {summary['active_sessions']})")
        print(f"Total models: {summary['total_models']}")
        
        print("\nComponents available:")
        for component, available in summary["components_available"].items():
            print(f"  {component}: {'Yes' if available else 'No'}")
        
        print("\nRecent metrics:")
        for metric, value in summary.get("recent_metrics", {}).items():
            print(f"  {metric}: {value}")
        
    elif args.command == "collect-repair":
        # Read files
        with open(args.before_file, 'r', encoding='utf-8') as f:
            before_code = f.read()
        
        with open(args.after_file, 'r', encoding='utf-8') as f:
            after_code = f.read()
        
        # Collect repair data
        data_id = manager.collect_repair_data(
            bug_type=args.bug_type,
            before_code=before_code,
            after_code=after_code,
            file_path=args.file_path,
            bug_description=args.bug_description,
            fix_description=args.fix_description
        )
        
        print(f"Collected repair data with ID: {data_id}")
        
    elif args.command == "collect-feedback":
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
        feedback_id = manager.collect_feedback(
            source_type=args.source,
            content=args.content,
            context=context,
            metadata=metadata
        )
        
        print(f"Collected feedback with ID: {feedback_id}")
        
    elif args.command == "track-metric":
        # Track metric
        manager.track_metric(args.name, args.value)
        print(f"Tracked metric {args.name} with value {args.value}")
        
    elif args.command == "model":
        if args.model_command == "register":
            # Parse parameters and metrics
            try:
                parameters = json.loads(args.parameters)
            except json.JSONDecodeError:
                print(f"Error parsing parameters JSON: {args.parameters}")
                return 1
            
            try:
                metrics = json.loads(args.metrics)
            except json.JSONDecodeError:
                print(f"Error parsing metrics JSON: {args.metrics}")
                return 1
            
            # Register model
            success = manager.register_model(
                model_id=args.id,
                model_type=args.type,
                description=args.description,
                parameters=parameters,
                metrics=metrics,
                file_path=args.file_path
            )
            
            if success:
                print(f"Registered model {args.id}")
            else:
                print(f"Failed to register model {args.id}")
                return 1
                
        elif args.model_command == "get":
            # Get model
            model = manager.get_model(args.id)
            
            if model:
                print(f"Model {args.id}:")
                print(f"  Type: {model['model_type']}")
                print(f"  Description: {model['description']}")
                print(f"  Version: {model['version']}")
                print(f"  Created: {model['created_at']}")
                print(f"  Updated: {model['updated_at']}")
                print(f"  File path: {model.get('file_path', 'N/A')}")
                
                print("\n  Parameters:")
                for key, value in model["parameters"].items():
                    print(f"    {key}: {value}")
                
                print("\n  Metrics:")
                for key, value in model["metrics"].items():
                    print(f"    {key}: {value}")
            else:
                print(f"Model {args.id} not found")
                return 1
                
        elif args.model_command == "list":
            # List models
            if args.type:
                models = manager.get_models_by_type(args.type)
                print(f"Models of type {args.type}:")
            else:
                models = list(manager.models.values())
                print(f"All models:")
            
            for model in models:
                print(f"  {model['model_id']} (type: {model['model_type']}, version: {model['version']})")
            
            print(f"\nTotal: {len(models)} models")
            
        else:
            parser.print_help()
            return 1
            
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
