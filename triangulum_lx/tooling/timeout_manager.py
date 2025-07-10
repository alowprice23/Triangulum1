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

from triangulum_lx.tooling.fs_ops import atomic_write
from triangulum_lx.core.fs_state import FileSystemStateCache

logger = logging.getLogger("triangulum.timeout")

class TimeoutManager:
    """Manages timeouts and checkpoints for long-running operations."""
    
    def __init__(self, base_timeout: int = 300, max_timeout: int = 1200, fs_cache: Optional[FileSystemStateCache] = None):
        """Initialize the timeout manager.
        
        Args:
            base_timeout: Base timeout in seconds (default: 5 minutes)
            max_timeout: Maximum timeout in seconds (default: 20 minutes)
            fs_cache: Optional FileSystemStateCache instance.
        """
        self.base_timeout = base_timeout
        self.max_timeout = max_timeout
        self.checkpoint_path = None
        self.checkpointing_enabled = False
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()
        
    def calculate_timeout(self, file_path: str) -> int:
        """Calculate adaptive timeout based on file size and complexity.
        
        Args:
            file_path: Path to the file to calculate timeout for
            
        Returns:
            timeout: Timeout in seconds
        """
        if not self.fs_cache.exists(file_path): # Use cache
            # If cache says no, double check FS before returning base_timeout
            if not Path(file_path).exists():
                logger.debug(f"File {file_path} not found for timeout calculation (cache and FS). Returning base timeout.")
                return self.base_timeout
            else: # Cache was stale
                logger.warning(f"Cache miss for existing file {file_path} in calculate_timeout. Invalidating.")
                self.fs_cache.invalidate(file_path)
            
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
        chkpt_parent_dir = checkpoint_path.parent
        if not self.fs_cache.exists(str(chkpt_parent_dir)): # Use cache
            chkpt_parent_dir.mkdir(parents=True, exist_ok=True) # Direct mkdir for setup
            self.fs_cache.invalidate(str(chkpt_parent_dir)) # Invalidate as it might have been created
        elif not self.fs_cache.is_dir(str(chkpt_parent_dir)):
            logger.warning(f"Checkpoint parent path {chkpt_parent_dir} exists but is not a directory. Attempting mkdir.")
            chkpt_parent_dir.mkdir(parents=True, exist_ok=True)
            self.fs_cache.invalidate(str(chkpt_parent_dir))

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
            
            content_str = json.dumps(state, indent=2, default=str)
            atomic_write(str(self.checkpoint_path), content_str.encode('utf-8'))
            self.fs_cache.invalidate(str(self.checkpoint_path))
            
            logger.debug(f"Checkpoint saved to {self.checkpoint_path} using atomic_write")
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
    
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load the latest checkpoint.
        
        Returns:
            state: Dictionary with loaded state, or None if no checkpoint exists
        """
        if not self.checkpointing_enabled or not self.checkpoint_path:
            return None
            
        if not self.fs_cache.exists(str(self.checkpoint_path)): # Use cache
            if not self.checkpoint_path.exists(): # Double check FS
                logger.debug(f"Checkpoint file {self.checkpoint_path} not found (cache and FS).")
                return None
            else: # Cache stale
                logger.warning(f"Cache miss for existing checkpoint {self.checkpoint_path}. Invalidating.")
                self.fs_cache.invalidate(str(self.checkpoint_path))

        # Direct read for content
        try:
            with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            logger.info(f"Checkpoint loaded from {self.checkpoint_path}")
            return state
        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}")
            return None
