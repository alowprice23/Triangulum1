#!/usr/bin/env python3
"""
Checkpoint Manager Demo

This script demonstrates the checkpoint manager, which provides
functionality for saving and loading the state of the agentic system.
"""

import os
import json
import time
import argparse
from triangulum_lx.core.checkpoint_manager import CheckpointManager

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Run Checkpoint Manager Demo')
    
    parser.add_argument(
        '--checkpoint-dir',
        type=str,
        default='./checkpoints_demo',
        help='Directory for checkpoint files'
    )
    
    return parser.parse_args()

def run_demo(checkpoint_dir: str):
    """
    Run the checkpoint manager demo.
    
    Args:
        checkpoint_dir: Directory for checkpoint files
    """
    # Create the checkpoint manager
    checkpoint_manager = CheckpointManager(checkpoint_dir)
    
    # Simulate some system state
    system_state = {
        "timestamp": time.time(),
        "agents": {
            "orchestrator": {"status": "active", "task": "manage_workflow"},
            "bug_detector": {"status": "idle", "last_bug": "null_pointer"},
            "code_fixer": {"status": "active", "current_fix": "add_null_check"}
        },
        "global_progress": 75.0
    }
    
    # Save a checkpoint
    print("Saving checkpoint...")
    checkpoint_path = checkpoint_manager.save_checkpoint(system_state)
    
    if checkpoint_path:
        print(f"Checkpoint saved to: {checkpoint_path}")
        
        # Load the checkpoint
        print("\nLoading checkpoint...")
        loaded_state = checkpoint_manager.load_checkpoint(checkpoint_path)
        
        if loaded_state:
            print("Checkpoint loaded successfully:")
            print(json.dumps(loaded_state, indent=2))
            
            # Verify that the loaded state matches the original state
            if loaded_state == system_state:
                print("\nState verification successful: Loaded state matches original state.")
            else:
                print("\nState verification failed: Loaded state does not match original state.")
        else:
            print("Failed to load checkpoint.")
    else:
        print("Failed to save checkpoint.")
    
    # Get the latest checkpoint
    print("\nGetting latest checkpoint...")
    latest_checkpoint = checkpoint_manager.get_latest_checkpoint()
    
    if latest_checkpoint:
        print(f"Latest checkpoint found at: {latest_checkpoint}")
    else:
        print("No checkpoints found.")

def main():
    """Run the checkpoint manager demo."""
    args = parse_arguments()
    
    print("=" * 80)
    print("TRIANGULUM CHECKPOINT MANAGER DEMO".center(80))
    print("=" * 80)
    print("\nThis demo showcases the checkpoint manager, which provides")
    print("functionality for saving and loading the state of the agentic system.")
    
    run_demo(args.checkpoint_dir)

if __name__ == "__main__":
    main()
