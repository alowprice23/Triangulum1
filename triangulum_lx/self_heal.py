"""
Self-Healing Module - Import redirection for triangulum_self_heal.py

This module imports and re-exports the SystemStartupManager from the
root-level triangulum_self_heal.py to maintain package structure consistency.
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Import the SystemStartupManager from the root-level file
from triangulum_self_heal import SystemStartupManager

# Re-export the class
__all__ = ['SystemStartupManager']
