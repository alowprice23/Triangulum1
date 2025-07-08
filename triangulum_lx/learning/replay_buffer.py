"""
Replay buffer for Triangulum system.

Stores a history of bug-fixing episodes for learning and optimization.
"""

from collections import deque
import random
import json
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Deque
from pathlib import Path
import logging

# Setup logging
logger = logging.getLogger("triangulum.replay_buffer")


@dataclass
class Episode:
    """
    Represents a single bug-fixing episode for learning.
    
    An episode captures all relevant information about one bug-fixing attempt,
    including the steps taken, timing information, and outcome.
    """
    bug_id: str
    cycles: int  # Number of fix-verify cycles required
    total_wall: float  # Wall-clock seconds
    success: bool  # Whether the bug was fixed successfully
    timer_val: int  # Final timer value used
    entropy_gain: float  # Information gained during debugging
    fix_attempt: int  # Which fix attempt (0 or 1)
    agent_tokens: Dict[str, int]  # Token usage per agent role
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Episode':
        """Create from dictionary."""
        return cls(**data)


class ReplayBuffer:
    """
    Stores bug-fixing episodes for learning and optimization.
    
    This is a circular buffer that keeps the most recent episodes
    for use in reinforcement learning and parameter optimization.
    """
    
    def __init__(self, capacity: int = 500, storage_path: Optional[str] = None):
        """
        Initialize the replay buffer.
        
        Args:
            capacity: Maximum number of episodes to store
            storage_path: Path to save episodes (if provided)
        """
        self.buffer: Deque[Episode] = deque(maxlen=capacity)
        self.capacity = capacity
        self.storage_path = Path(storage_path) if storage_path else None
        
        # Create storage directory if needed
        if self.storage_path:
            self.storage_path.mkdir(exist_ok=True, parents=True)
            self._load_from_storage()
    
    def add(self, episode: Episode) -> None:
        """
        Add an episode to the buffer.
        
        Args:
            episode: The Episode to add
        """
        self.buffer.append(episode)
        
        # Save to storage if configured
        if self.storage_path:
            self._save_episode(episode)
    
    def sample(self, batch_size: int = 32) -> List[Episode]:
        """
        Sample a random batch of episodes.
        
        Args:
            batch_size: Number of episodes to sample
        
        Returns:
            List of sampled episodes
        """
        if len(self.buffer) <= batch_size:
            return list(self.buffer)
        return random.sample(list(self.buffer), batch_size)
    
    def recent(self, n: int = 10) -> List[Episode]:
        """
        Get the most recent episodes.
        
        Args:
            n: Number of recent episodes to return
            
        Returns:
            List of recent episodes
        """
        return list(self.buffer)[-n:]
    
    def stats(self) -> Dict[str, Any]:
        """
        Calculate statistics from all episodes.
        
        Returns:
            Dictionary of statistics
        """
        if not self.buffer:
            return {
                "count": 0,
                "success_rate": 0.0,
                "avg_cycles": 0.0,
                "avg_wall_time": 0.0,
                "avg_entropy_gain": 0.0,
            }
        
        count = len(self.buffer)
        success_count = sum(1 for ep in self.buffer if ep.success)
        
        return {
            "count": count,
            "success_rate": success_count / count if count > 0 else 0.0,
            "avg_cycles": sum(ep.cycles for ep in self.buffer) / count,
            "avg_wall_time": sum(ep.total_wall for ep in self.buffer) / count,
            "avg_entropy_gain": sum(ep.entropy_gain for ep in self.buffer) / count,
            "total_tokens": sum(sum(ep.agent_tokens.values()) for ep in self.buffer),
        }
    
    def clear(self) -> None:
        """Clear the buffer."""
        self.buffer.clear()
    
    def _save_episode(self, episode: Episode) -> None:
        """
        Save an episode to disk.
        
        Args:
            episode: Episode to save
        """
        if not self.storage_path:
            return
        
        try:
            # Create a filename based on bug_id and timestamp
            timestamp = int(time.time())
            filename = f"episode_{episode.bug_id}_{timestamp}.json"
            file_path = self.storage_path / filename
            
            # Save as JSON
            with open(file_path, 'w') as f:
                json.dump(episode.to_dict(), f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving episode: {e}")
    
    def _load_from_storage(self) -> None:
        """Load episodes from disk storage."""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        try:
            # Load all JSON files in the directory
            episode_files = list(self.storage_path.glob("episode_*.json"))
            
            # Sort by modification time (newest first)
            episode_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            # Load up to capacity
            loaded_count = 0
            for file_path in episode_files[:self.capacity]:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        episode = Episode.from_dict(data)
                        self.buffer.append(episode)
                        loaded_count += 1
                except Exception as e:
                    logger.warning(f"Error loading episode from {file_path}: {e}")
            
            logger.info(f"Loaded {loaded_count} episodes from storage")
            
        except Exception as e:
            logger.error(f"Error loading episodes from storage: {e}")
    
    def save_all(self, path: Optional[str] = None) -> bool:
        """
        Save all episodes to a single JSON file.
        
        Args:
            path: Path to save the file (defaults to storage_path/all_episodes.json)
            
        Returns:
            bool: True if saved successfully
        """
        save_path = Path(path) if path else (self.storage_path / "all_episodes.json")
        
        try:
            # Convert all episodes to dictionaries
            episodes_data = [ep.to_dict() for ep in self.buffer]
            
            # Save as JSON
            with open(save_path, 'w') as f:
                json.dump({
                    "episodes": episodes_data,
                    "stats": self.stats(),
                    "timestamp": time.time()
                }, f, indent=2)
                
            logger.info(f"Saved {len(episodes_data)} episodes to {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving all episodes: {e}")
            return False
