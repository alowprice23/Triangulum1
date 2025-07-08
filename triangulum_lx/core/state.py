import time
from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, Any

class Phase(Enum):
    WAIT = auto()
    REPRO = auto()
    PATCH = auto()
    VERIFY = auto()
    DONE = auto()
    ESCALATE = auto()          # unreachable in happy path

@dataclass(frozen=True, slots=True)
class BugState:
    phase: Phase      # current phase in triangle
    timer: int        # 0‥3
    attempts: int     # 0 or 1
    code_snippet: str = ""


class TriangulumState:
    """Represents the state of the Triangulum debugging system."""
    
    def __init__(self):
        """Initialize the Triangulum state."""
        self.current_phase = Phase.WAIT
        self.active_bugs = []
        self.completed_bugs = []
        self.system_metrics = {}
        self.start_time = time.time()
    
    def update_phase(self, new_phase: Phase) -> None:
        """Update the current phase.
        
        Args:
            new_phase: New phase to transition to
        """
        self.current_phase = new_phase
    
    def add_bug(self, bug_id: str) -> None:
        """Add a bug to the active list.
        
        Args:
            bug_id: Bug identifier
        """
        if bug_id not in self.active_bugs:
            self.active_bugs.append(bug_id)
    
    def complete_bug(self, bug_id: str) -> None:
        """Mark a bug as completed.
        
        Args:
            bug_id: Bug identifier
        """
        if bug_id in self.active_bugs:
            self.active_bugs.remove(bug_id)
            self.completed_bugs.append(bug_id)
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current system status.
        
        Returns:
            Status dictionary
        """
        return {
            'current_phase': self.current_phase.name,
            'active_bugs': len(self.active_bugs),
            'completed_bugs': len(self.completed_bugs),
            'uptime': time.time() - self.start_time
        }
