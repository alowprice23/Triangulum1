#!/usr/bin/env python3
"""
Adaptive Timeout Manager for Triangulum

Implements adaptive timeouts based on file size and complexity,
and provides checkpoint recovery capabilities.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("triangulum.timeout")

class TimeoutManager:
    """Manages timeouts and checkpoints for long-running operations."""
    
    def __init__(self, base_timeout: int = 300, max_timeout: int = 1200):
        """Initialize the timeout manager.
        
        Args:
            base_timeout: Base timeout in seconds (default: 5 minutes)
            max_timeout: Maximum timeout in seconds (default: 20 minutes)
        """
        self.base_timeout = base_timeout
        self.max_timeout = max_timeout
        self.checkpoint_path = None
        self.checkpointing_enabled = False
        
    def calculate_timeout(self, file_path: str) -> int:
        """Calculate adaptive timeout based on file size and complexity.
        
        Args:
            file_path: Path to the file to calculate timeout for
            
        Returns:
            timeout: Timeout in seconds
        """
        if not os.path.exists(file_path):
            return self.base_timeout
            
        # Get file size in KB
        file_size = os.path.getsize(file_path) / 1024
        
        # Count lines of code as a complexity measure
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
        except Exception as e:
            logger.warning(f"Error counting lines in {file_path}: {e}")
            line_count = 100  # Default assumption
        
        # Calculate timeout: base + additional time for large/complex files
        # File size factor: 0.5 seconds per KB
        # Line count factor: 0.2 seconds per line
        timeout = self.base_timeout + min(
            self.max_timeout - self.base_timeout,  # Cap the additional time
            int(file_size * 0.5) + int(line_count * 0.2)
        )
        
        logger.info(f"Adaptive timeout for {file_path}: {timeout}s (size: {file_size:.1f}KB, lines: {line_count})")
        return timeout
    
    def enable_checkpointing(self, checkpoint_path: Path):
        """Enable checkpointing for recovery from timeouts.
        
        Args:
            checkpoint_path: Path to the checkpoint file
        """
        self.checkpoint_path = checkpoint_path
        self.checkpointing_enabled = True
        
        # Create directory if it doesn't exist
        os.makedirs(checkpoint_path.parent, exist_ok=True)
        
        logger.info(f"Checkpointing enabled at {checkpoint_path}")
    
    def save_checkpoint(self, state: Dict[str, Any]):
        """Save a checkpoint of the current state.
        
        Args:
            state: Dictionary with state to save
        """
        if not self.checkpointing_enabled or not self.checkpoint_path:
            return
            
        try:
            # Add timestamp
            state['timestamp'] = time.time()
            
            with open(self.checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, default=str)
            
            logger.debug(f"Checkpoint saved to {self.checkpoint_path}")
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
    
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load the latest checkpoint.
        
        Returns:
            state: Dictionary with loaded state, or None if no checkpoint exists
        """
        if not self.checkpointing_enabled or not self.checkpoint_path:
            return None
            
        if not self.checkpoint_path.exists():
            return None
            
        try:
            with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            logger.info(f"Checkpoint loaded from {self.checkpoint_path}")
            return state
        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}")
            return None
