#!/usr/bin/env python3
"""
Checkpoint Manager

This module provides functionality for saving and loading the state of
the agentic system, allowing for recovery from failures.
"""

import os
import json
import logging
import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CheckpointManager:
    """
    Manages the saving and loading of system state checkpoints.
    """
    
    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        """
        Initialize the checkpoint manager.
        
        Args:
            checkpoint_dir: The directory to store checkpoint files.
        """
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        logger.info(f"Checkpoint Manager initialized with directory: {checkpoint_dir}")
    
    def save_checkpoint(self, state: Dict[str, Any], name: Optional[str] = None) -> str:
        """
        Save the current system state to a checkpoint file.
        
        Args:
            state: A dictionary representing the system state to save.
            name: An optional name for the checkpoint.
        
        Returns:
            The path to the saved checkpoint file.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_name = name or f"checkpoint_{timestamp}"
        checkpoint_path = os.path.join(self.checkpoint_dir, f"{checkpoint_name}.json")
        
        try:
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"Checkpoint saved to: {checkpoint_path}")
            return checkpoint_path
        except Exception as e:
            logger.error(f"Error saving checkpoint to {checkpoint_path}: {e}")
            return None
    
    def load_checkpoint(self, checkpoint_path: str) -> Optional[Dict[str, Any]]:
        """
        Load a system state from a checkpoint file.
        
        Args:
            checkpoint_path: The path to the checkpoint file to load.
        
        Returns:
            A dictionary representing the loaded system state, or None if loading fails.
        """
        if not os.path.exists(checkpoint_path):
            logger.error(f"Checkpoint file not found: {checkpoint_path}")
            return None
        
        try:
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            logger.info(f"Checkpoint loaded from: {checkpoint_path}")
            return state
        except Exception as e:
            logger.error(f"Error loading checkpoint from {checkpoint_path}: {e}")
            return None
    
    def get_latest_checkpoint(self) -> Optional[str]:
        """
        Get the path to the most recent checkpoint file.
        
        Returns:
            The path to the latest checkpoint file, or None if no checkpoints are found.
        """
        checkpoints = [os.path.join(self.checkpoint_dir, f) for f in os.listdir(self.checkpoint_dir) if f.endswith(".json")]
        
        if not checkpoints:
            return None
        
        latest_checkpoint = max(checkpoints, key=os.path.getctime)
        return latest_checkpoint
