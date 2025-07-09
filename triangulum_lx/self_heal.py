"""
Self-Healing Module - Import redirection for SystemStartupManager.

This module re-exports SystemStartupManager from its canonical location
in triangulum_lx.core.startup_manager.
"""
from triangulum_lx.core.startup_manager import SystemStartupManager

__all__ = ['SystemStartupManager']
