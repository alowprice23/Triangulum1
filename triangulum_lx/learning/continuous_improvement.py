#!/usr/bin/env python3
"""
Continuous Improvement System

This module automatically adjusts system parameters and models based on operational
experience and feedback. It implements automated parameter adjustment, performance
metric tracking, A/B testing, model fine-tuning, and knowledge distillation.
"""

import os
import json
import time
import logging
import random
import threading
import copy
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("triangulum.continuous_improvement")

# Try to import optional dependencies
try:
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    HAVE_ML_DEPS = True
except ImportError:
    logger.warning("Machine learning dependencies not available. Using basic improvement mechanisms only.")
    HAVE_ML_DEPS = False


class Parameter:
    """
    Represents a system parameter that can be adjusted.
    """
    
    def __init__(self, 
                 name: str,
                 value: Any,
                 min_value: Optional[Any] = None,
                 max_value: Optional[Any] = None,
                 step_size: Optional[Any] = None,
                 description: str = "",
                 category: str = "general"):
        """
        Initialize a parameter.
        
        Args:
            name: Name of the parameter
            value: Current value of the parameter
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            step_size: Step size for adjustments
            description: Description of the parameter
            category: Category of the parameter
        """
        self.name = name
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        self.step_size = step_size
        self.description = description
        self.category = category
        self.history = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parameter to dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "step_size": self.step_size,
            "description": self.description,
            "category": self.category,
            "history": self.history,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Parameter':
        """Create parameter from dictionary."""
        param = cls(
            name=data["name"],
            value=data["value"],
            min_value=data["min_value"],
            max_value=data["max_value"],
            step_size=data["step_size"],
            description=data["description"],
            category=data["category"]
        )
        
        # Restore state
        param.history = data["history"]
        param.created_at = data["created_at"]
        param.updated_at = data["updated_at"]
        
        return param
    
    def update(self, value: Any, reason: str = "manual"):
        """
        Update the parameter value.
        
        Args:
            value: New value
            reason: Reason for the update
        """
        # Validate value
        if self.min_value is not None and value < self.min_value:
            value = self.min_value
        
        if self.max_value is not None and value > self.max_value:
            value = self.max_value
        
        # Record history
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "old_value": self.value,
            "new_value": value,
            "reason": reason
        })
        
        # Update value
        self.value = value
        self.updated_at = datetime.now().isoformat()


class Experiment:
    """
    Represents an A/B testing experiment.
    """
    
    def __init__(self, 
                 experiment_id: str,
                 name: str,
                 description: str,
                 variants: Dict[str, Dict[str, Any]],
                 metrics: List[str],
                 start_time: Optional[str] = None,
                 end_time: Optional[str] = None,
                 status: str = "created"):
        """
        Initialize an experiment.
        
        Args:
            experiment_id: Unique identifier for the experiment
            name: Name of the experiment
            description: Description of the experiment
            variants: Dictionary of variant configurations
            metrics: List of metrics to track
            start_time: Start time of the experiment
            end_time: End time of the experiment
            status: Status of the experiment
        """
        self.experiment_id = experiment_id
        self.name = name
        self.description = description
        self.variants = variants
        self.metrics = metrics
        self.start_time = start_time or datetime.now().isoformat()
        self.end_time = end_time
        self.status = status
        self.results = {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert experiment to dictionary for serialization."""
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "variants": self.variants,
            "metrics": self.metrics,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "results": self.results,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Experiment':
        """Create experiment from dictionary."""
        experiment = cls(
            experiment_id=data["experiment_id"],
            name=data["name"],
            description=data["description"],
            variants=data["variants"],
            metrics=data["metrics"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            status=data["status"]
        )
        
        # Restore state
        experiment.results = data["results"]
        experiment.created_at = data["created_at"]
        experiment.updated_at = data["updated_at"]
        
        return experiment
    
    def start(self):
        """Start the experiment."""
        self.status = "running"
        self.start_time = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def stop(self):
        """Stop the experiment."""
        self.status = "stopped"
        self.end_time = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def complete(self):
        """Complete the experiment."""
        self.status = "completed"
        self.end_time = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def add_result(self, variant: str, metric: str, value: float):
        """
        Add a result for a variant and metric.
        
        Args:
            variant: Variant name
            metric: Metric name
            value: Metric value
        """
        if variant not in self.variants:
            logger.warning(f"Variant {variant} not found in experiment {self.experiment_id}")
            return
        
        if metric not in self.metrics:
            logger.warning(f"Metric {metric} not found in experiment {self.experiment_id}")
            return
        
        if variant not in self.results:
            self.results[variant] = {}
        
        if metric not in self.results[variant]:
            self.results[variant][metric] = []
        
        self.results[variant][metric].append({
            "timestamp": datetime.now().isoformat(),
            "value": value
        })
        
        self.updated_at = datetime.now().isoformat()
    
    def get_winner(self) -> Optional[str]:
        """
        Get the winning variant based on metrics.
        
        Returns:
            Winning variant or None if no clear winner
        """
        if not self.results or self.status != "completed":
            return None
        
        # Calculate average metric values for each variant
        variant_scores = {}
        
        for variant, metrics in self.results.items():
            variant_scores[variant] = 0.0
            
            for metric, values in metrics.items():
                if not values:
                    continue
                
                # Calculate average value
                avg_value = sum(v["value"] for v in values) / len(values)
                
                # Add to variant score
                variant_scores[variant] += avg_value
        
        # Find variant with highest score
        if not variant_scores:
            return None
        
        return max(variant_scores.items(), key=lambda x: x[1])[0]


class Model:
    """
    Represents a machine learning model.
    """
    
    def __init__(self, 
                 model_id: str,
                 name: str,
                 model_type: str,
                 description: str,
                 parameters: Dict[str, Any],
                 metrics: Dict[str, float],
                 version: str = "1.0.0"):
        """
        Initialize a model.
        
        Args:
            model_id: Unique identifier for the model
            name: Name of the model
            model_type: Type of model
            description: Description of the model
            parameters: Model parameters
            metrics: Model metrics
            version: Model version
        """
        self.model_id = model_id
        self.name = name
        self.model_type = model_type
        self.description = description
        self.parameters = parameters
        self.metrics = metrics
        self.version = version
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.trained_at = None
        self.model_instance = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for serialization."""
        return {
            "model_id": self.model_id,
            "name": self.name,
            "model_type": self.model_type,
            "description": self.description,
            "parameters": self.parameters,
            "metrics": self.metrics,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "trained_at": self.trained_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Model':
        """Create model from dictionary."""
        model = cls(
            model_id=data["model_id"],
            name=data["name"],
            model_type=data["model_type"],
            description=data["description"],
            parameters=data["parameters"],
            metrics=data["metrics"],
            version=data["version"]
        )
        
        # Restore state
        model.created_at = data["created_at"]
        model.updated_at = data["updated_at"]
        model.trained_at = data["trained_at"]
        
        return model
    
    def update_metrics(self, metrics: Dict[str, float]):
        """
        Update model metrics.
        
        Args:
            metrics: New metrics
        """
        self.metrics.update(metrics)
        self.updated_at = datetime.now().isoformat()
    
    def update_parameters(self, parameters: Dict[str, Any]):
        """
        Update model parameters.
        
        Args:
            parameters: New parameters
        """
        self.parameters.update(parameters)
        self.updated_at = datetime.now().isoformat()
    
    def set_trained(self):
        """Mark the model as trained."""
        self.trained_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()


class ContinuousImprovement:
    """
    Automatically adjusts system parameters and models based on operational experience and feedback.
    """
    
    def __init__(self, database_path: Optional[str] = None):
        """
        Initialize the continuous improvement system.
        
        Args:
            database_path: Path to the database file
        """
        self.database_path = database_path or "triangulum_lx/config/parameters.json"
        self.parameters: Dict[str, Parameter] = {}
        self.experiments: Dict[str, Experiment] = {}
        self.models: Dict[str, Model] = {}
        self.metrics: Dict[str, List[Dict[str, Any]]] = {}
        
        # Initialize improvement thread
        self.stop_event = threading.Event()
        self.improvement_thread = None
        self.improvement_interval = 3600  # 1 hour
        
        # Load parameters if available
        self._load_parameters()
        
        # Initialize default parameters if none exist
        if not self.parameters:
            self._initialize_default_parameters()
    
    def _load_parameters(self):
        """Load parameters from the database file."""
        if os.path.exists(self.database_path):
            try:
                with open(self.database_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load parameters
                for param_data in data.get("parameters", []):
                    param = Parameter.from_dict(param_data)
                    self.parameters[param.name] = param
                
                # Load experiments
                for exp_data in data.get("experiments", []):
                    experiment = Experiment.from_dict(exp_data)
                    self.experiments[experiment.experiment_id] = experiment
                
                # Load models
                for model_data in data.get("models", []):
                    model = Model.from_dict(model_data)
                    self.models[model.model_id] = model
                
                # Load metrics
                self.metrics = data.get("metrics", {})
                
                logger.info(f"Loaded {len(self.parameters)} parameters from {self.database_path}")
            except Exception as e:
                logger.error(f"Error loading parameters: {e}")
                self.parameters = {}
                self.experiments = {}
                self.models = {}
                self.metrics = {}
        else:
            logger.info("No parameter database found. Starting with default parameters.")
    
    def _save_parameters(self):
        """Save parameters to the database file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
            
            # Prepare data for serialization
            data = {
                "parameters": [param.to_dict() for param in self.parameters.values()],
                "experiments": [exp.to_dict() for exp in self.experiments.values()],
                "models": [model.to_dict() for model in self.models.values()],
                "metrics": self.metrics,
                "last_updated": datetime.now().isoformat()
            }
            
            # Save to file
            with open(self.database_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Saved {len(self.parameters)} parameters to {self.database_path}")
        except Exception as e:
            logger.error(f"Error saving parameters: {e}")
    
    def _initialize_default_parameters(self):
        """Initialize default parameters."""
        default_parameters = [
            {
                "name": "bug_detection_confidence_threshold",
                "value": 0.7,
                "min_value": 0.5,
                "max_value": 0.95,
                "step_size": 0.05,
                "description": "Confidence threshold for bug detection",
                "category": "bug_detection"
            },
            {
                "name": "repair_confidence_threshold",
                "value": 0.8,
                "min_value": 0.6,
                "max_value": 0.95,
                "step_size": 0.05,
                "description": "Confidence threshold for repair application",
                "category": "repair"
            },
            {
                "name": "max_repair_attempts",
                "value": 3,
                "min_value": 1,
                "max_value": 10,
                "step_size": 1,
                "description": "Maximum number of repair attempts",
                "category": "repair"
            },
            {
                "name": "verification_strictness",
                "value": 0.8,
                "min_value": 0.5,
                "max_value": 1.0,
                "step_size": 0.1,
                "description": "Strictness of verification checks",
                "category": "verification"
            },
            {
                "name": "parallel_execution_workers",
                "value": 4,
                "min_value": 1,
                "max_value": 16,
                "step_size": 1,
                "description": "Number of parallel execution workers",
                "category": "performance"
            },
            {
                "name": "timeout_multiplier",
                "value": 1.5,
                "min_value": 1.0,
                "max_value": 5.0,
                "step_size": 0.5,
                "description": "Multiplier for operation timeouts",
                "category": "performance"
            },
            {
                "name": "learning_rate",
                "value": 0.01,
                "min_value": 0.001,
                "max_value": 0.1,
                "step_size": 0.005,
                "description": "Learning rate for model updates",
                "category": "learning"
            },
            {
                "name": "feedback_weight",
                "value": 0.7,
                "min_value": 0.1,
                "max_value": 1.0,
                "step_size": 0.1,
                "description": "Weight given to user feedback",
                "category": "learning"
            }
        ]
        
        for param_data in default_parameters:
            param = Parameter(**param_data)
            self.parameters[param.name] = param
        
        # Save parameters
        self._save_parameters()
    
    def get_parameter(self, name: str) -> Optional[Any]:
        """
        Get a parameter value.
        
        Args:
            name: Parameter name
            
        Returns:
            Parameter value or None if not found
        """
        if name in self.parameters:
            return self.parameters[name].value
        
        return None
    
    def set_parameter(self, name: str, value: Any, reason: str = "manual") -> bool:
        """
        Set a parameter value.
        
        Args:
            name: Parameter name
            value: New value
            reason: Reason for the update
            
        Returns:
            True if successful, False otherwise
        """
        if name not in self.parameters:
            logger.warning(f"Parameter {name} not found")
            return False
        
        self.parameters[name].update(value, reason)
        
        # Save parameters
        self._save_parameters()
        
        return True
    
    def track_metric(self, name: str, value: float):
        """
        Track a metric.
        
        Args:
            name: Metric name
            value: Metric value
        """
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append({
            "timestamp": datetime.now().isoformat(),
            "value": value
        })
        
        # Limit metric history
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]
        
        # Save parameters
        self._save_parameters()
    
    def create_experiment(self, 
                         name: str,
                         description: str,
                         variants: Dict[str, Dict[str, Any]],
                         metrics: List[str]) -> str:
        """
        Create an A/B testing experiment.
        
        Args:
            name: Experiment name
            description: Experiment description
            variants: Dictionary of variant configurations
            metrics: List of metrics to track
            
        Returns:
            Experiment ID
        """
        # Generate experiment ID
        timestamp = int(time.time())
        experiment_id = f"experiment_{timestamp}_{name.lower().replace(' ', '_')}"
        
        # Create experiment
        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            variants=variants,
            metrics=metrics
        )
        
        # Add experiment
        self.experiments[experiment_id] = experiment
        
        # Save parameters
        self._save_parameters()
        
        logger.info(f"Created experiment {experiment_id}")
        return experiment_id
    
    def start_experiment(self, experiment_id: str) -> bool:
        """
        Start an experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            True if successful, False otherwise
        """
        if experiment_id not in self.experiments:
            logger.warning(f"Experiment {experiment_id} not found")
            return False
        
        self.experiments[experiment_id].start()
        
        # Save parameters
        self._save_parameters()
        
        logger.info(f"Started experiment {experiment_id}")
        return True
    
    def stop_experiment(self, experiment_id: str) -> bool:
        """
        Stop an experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            True if successful, False otherwise
        """
        if experiment_id not in self.experiments:
            logger.warning(f"Experiment {experiment_id} not found")
            return False
        
        self.experiments[experiment_id].stop()
        
        # Save parameters
        self._save_parameters()
        
        logger.info(f"Stopped experiment {experiment_id}")
        return True
    
    def complete_experiment(self, experiment_id: str) -> bool:
        """
        Complete an experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            True if successful, False otherwise
        """
        if experiment_id not in self.experiments:
            logger.warning(f"Experiment {experiment_id} not found")
            return False
        
        self.experiments[experiment_id].complete()
        
        # Apply winning variant if available
        winner = self.experiments[experiment_id].get_winner()
        if winner:
            logger.info(f"Experiment {experiment_id} winner: {winner}")
            
            # Apply winning variant parameters
            variant_config = self.experiments[experiment_id].variants[winner]
            for param_name, param_value in variant_config.items():
                if param_name in self.parameters:
                    self.parameters[param_name].update(param_value, f"experiment_{experiment_id}")
        
        # Save parameters
        self._save_parameters()
        
        logger.info(f"Completed experiment {experiment_id}")
        return True
    
    def add_experiment_result(self, experiment_id: str, variant: str, metric: str, value: float) -> bool:
        """
        Add a result to an experiment.
        
        Args:
            experiment_id: Experiment ID
            variant: Variant name
            metric: Metric name
            value: Metric value
            
        Returns:
            True if successful, False otherwise
        """
        if experiment_id not in self.experiments:
            logger.warning(f"Experiment {experiment_id} not found")
            return False
        
        self.experiments[experiment_id].add_result(variant, metric, value)
        
        # Save parameters
        self._save_parameters()
        
        return True
    
    def register_model(self, 
                      name: str,
                      model_type: str,
                      description: str,
                      parameters: Dict[str, Any],
                      metrics: Dict[str, float],
                      version: str = "1.0.0") -> str:
        """
        Register a model.
        
        Args:
            name: Model name
            model_type: Model type
            description: Model description
            parameters: Model parameters
            metrics: Model metrics
            version: Model version
            
        Returns:
            Model ID
        """
        # Generate model ID
        timestamp = int(time.time())
        model_id = f"model_{timestamp}_{name.lower().replace(' ', '_')}"
        
        # Create model
        model = Model(
            model_id=model_id,
            name=name,
            model_type=model_type,
            description=description,
            parameters=parameters,
            metrics=metrics,
            version=version
        )
        
        # Add model
        self.models[model_id] = model
        
        # Save parameters
        self._save_parameters()
        
        logger.info(f"Registered model {model_id}")
        return model_id
    
    def update_model_metrics(self, model_id: str, metrics: Dict[str, float]) -> bool:
        """
        Update model metrics.
        
        Args:
            model_id: Model ID
            metrics: New metrics
            
        Returns:
            True if successful, False otherwise
        """
        if model_id not in self.models:
            logger.warning(f"Model {model_id} not found")
            return False
        
        self.models[model_id].update_metrics(metrics)
        
        # Save parameters
        self._save_parameters()
        
        return True
    
    def update_model_parameters(self, model_id: str, parameters: Dict[str, Any]) -> bool:
        """
        Update model parameters.
        
        Args:
            model_id: Model ID
            parameters: New parameters
            
        Returns:
            True if successful, False otherwise
        """
        if model_id not in self.models:
            logger.warning(f"Model {model_id} not found")
            return False
        
        self.models[model_id].update_parameters(parameters)
        
        # Save parameters
        self._save_parameters()
        
        return True
    
    def set_model_trained(self, model_id: str) -> bool:
        """
        Mark a model as trained.
        
        Args:
            model_id: Model ID
            
        Returns:
            True if successful, False otherwise
        """
        if model_id not in self.models:
            logger.warning(f"Model {model_id} not found")
            return False
        
        self.models[model_id].set_trained()
        
        # Save parameters
        self._save_parameters()
        
        return True
    
    def start_improvement_thread(self):
        """Start the improvement thread."""
        if self.improvement_thread and self.improvement_thread.is_alive():
            logger.warning("Improvement thread is already running")
            return
        
        logger.info("Starting improvement thread")
        self.stop_event.clear()
        self.improvement_thread = threading.Thread(target=self._improvement_loop, daemon=True)
        self.improvement_thread.start()
    
    def stop_improvement_thread(self):
        """Stop the improvement thread."""
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
                sleep_seconds = self.improvement_interval
                
                # Sleep in smaller increments to allow for clean shutdown
                for _ in range(sleep_seconds // 5):
                    if self.stop_event.is_set():
                        break
                    time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in improvement loop: {e}")
                time.sleep(60)  # Sleep for a minute on error
    
    def _run_improvement_cycle(self):
        """Run an improvement cycle."""
        logger.info("Running improvement cycle")
        
        # Analyze metrics
        self._analyze_metrics()
        
        # Adjust parameters
        self._adjust_parameters()
        
        # Fine-tune models
        self._fine_tune_models()
        
        # Save parameters
        self._save_parameters()
    
    def _analyze_metrics(self):
        """Analyze metrics to identify improvement opportunities."""
        # Skip if no metrics
        if not self.metrics:
            return
        
        # Calculate metric trends
        metric_trends = {}
        
        for metric_name, metric_values in self.metrics.items():
            if len(metric_values) < 2:
                continue
            
            # Get recent values
            recent_values = [v["value"] for v in metric_values[-10:]]
            
            # Calculate trend
            if len(recent_values) >= 2:
                trend = (recent_values[-1] - recent_values[0]) / len(recent_values)
                metric_trends[metric_name] = trend
        
        # Log metric trends
        for metric_name, trend in metric_trends.items():
            logger.info(f"Metric {metric_name} trend: {trend:.4f}")
    
    def _adjust_parameters(self):
        """Adjust parameters based on metrics and experiments."""
        # Skip if no metrics
        if not self.metrics:
            return
        
        # Get parameters by category
        params_by_category = defaultdict(list)
        for param_name, param in self.parameters.items():
            params_by_category[param.category].append(param_name)
        
        # Adjust parameters based on metrics
        for category, param_names in params_by_category.items():
            # Find relevant metrics for this category
            relevant_metrics = [
                m for m in self.metrics.keys()
                if category in m or any(p.replace("_", "") in m for p in param_names)
            ]
            
            if not relevant_metrics:
                continue
            
            # Calculate metric scores
            metric_scores = {}
            for metric_name in relevant_metrics:
                if not self.metrics[metric_name]:
                    continue
                
                # Get recent values
                recent_values = [v["value"] for v in self.metrics[metric_name][-5:]]
                
                # Calculate score (average of recent values)
                if recent_values:
                    metric_scores[metric_name] = sum(recent_values) / len(recent_values)
            
            if not metric_scores:
                continue
            
            # Adjust parameters based on metric scores
            for param_name in param_names:
                param = self.parameters[param_name]
                
                # Skip parameters without step size
                if param.step_size is None:
                    continue
                
                # Find most relevant metric
                most_relevant_metric = max(
                    metric_scores.keys(),
                    key=lambda m: sum(1 for p in param_name.split("_") if p in m)
                )
                
                # Get metric score
                metric_score = metric_scores[most_relevant_metric]
                
                # Determine adjustment direction
                # For most metrics, higher is better
                is_higher_better = True
                
                # For some metrics, lower is better
                if any(term in most_relevant_metric for term in ["error", "latency", "time", "memory", "cpu", "resource"]):
                    is_higher_better = False
                
                # Calculate current performance
                if (is_higher_better and metric_score > 0.7) or (not is_higher_better and metric_score < 0.3):
                    # Good performance, make small adjustments
                    adjustment_factor = 0.5
                else:
                    # Poor performance, make larger adjustments
                    adjustment_factor = 1.0
                
                # Determine adjustment direction
                if (is_higher_better and metric_score < 0.5) or (not is_higher_better and metric_score > 0.5):
                    # Need improvement, adjust parameter
                    if isinstance(param.value, (int, float)):
                        # Try increasing the parameter
                        new_value = param.value + (param.step_size * adjustment_factor)
                        self.set_parameter(param_name, new_value, f"auto_adjust_based_on_{most_relevant_metric}")
                        logger.info(f"Adjusted parameter {param_name} from {param.value} to {new_value}")
                
                # Occasionally try decreasing the parameter to explore parameter space
                elif random.random() < 0.2:  # 20% chance
                    if isinstance(param.value, (int, float)):
                        # Try decreasing the parameter
                        new_value = param.value - (param.step_size * adjustment_factor)
                        self.set_parameter(param_name, new_value, f"auto_explore_based_on_{most_relevant_metric}")
                        logger.info(f"Explored parameter {param_name} from {param.value} to {new_value}")
    
    def _fine_tune_models(self):
        """Fine-tune models based on operational data."""
        # Skip if no ML dependencies or no models
        if not HAVE_ML_DEPS or not self.models:
            return
        
        # Skip if no metrics
        if not self.metrics:
            return
        
        # Get models that need fine-tuning
        models_to_tune = [
            model for model in self.models.values()
            if model.model_type in ["classifier", "regressor"]
        ]
        
        if not models_to_tune:
            return
        
        # Fine-tune each model
        for model in models_to_tune:
            try:
                # Get relevant metrics for this model
                relevant_metrics = [
                    m for m in self.metrics.keys()
                    if model.name.lower() in m.lower() or any(p in m.lower() for p in model.parameters.keys())
                ]
                
                if not relevant_metrics:
                    continue
                
                # Prepare training data
                X = []
                y = []
                
                # Use metrics as features and target
                for metric_name in relevant_metrics:
                    if not self.metrics[metric_name]:
                        continue
                    
                    # Get metric values
                    metric_values = [v["value"] for v in self.metrics[metric_name]]
                    
                    if len(metric_values) < 10:
                        continue
                    
                    # Use recent values as target
                    y = metric_values[-10:]
                    
                    # Use previous values as features
                    for i in range(len(metric_values) - 20, len(metric_values) - 10):
                        if i >= 0:
                            X.append([metric_values[i]])
                
                if not X or not y:
                    continue
                
                # Convert to numpy arrays
                X = np.array(X)
                y = np.array(y)
                
                # Split data
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                
                # Create and train model
                if model.model_type == "regressor":
                    model_instance = RandomForestRegressor(
                        n_estimators=model.parameters.get("n_estimators", 100),
                        max_depth=model.parameters.get("max_depth", 10),
                        random_state=42
                    )
                    
                    # Train model
                    model_instance.fit(X_train, y_train)
                    
                    # Evaluate model
                    score = model_instance.score(X_test, y_test)
                    
                    # Update model metrics
                    self.update_model_metrics(model.model_id, {"r2_score": score})
                    
                    # Update model instance
                    model.model_instance = model_instance
                    
                    # Mark model as trained
                    self.set_model_trained(model.model_id)
                    
                    logger.info(f"Fine-tuned model {model.model_id} with R² score: {score:.4f}")
                
            except Exception as e:
                logger.error(f"Error fine-tuning model {model.model_id}: {e}")
