#!/usr/bin/env python3
"""
Simple demonstration of the Triangulum LX system.

This script shows how to initialize and run the core components
of the Triangulum debugging system.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from triangulum_lx.core import TriangulumEngine, EngineMonitor
from triangulum_lx.agents import AutoGenCoordinator
from triangulum_lx.monitoring import MetricsCollector
from triangulum_lx.core.state import BugState, Phase


async def main():
    """Run a simple demonstration of Triangulum LX."""
    print("=== Triangulum LX Demonstration ===\n")
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. LLM agents will not function.")
        print("Please set this environment variable to use the full system.\n")
    
    # Initialize the core engine and monitor
    print("Initializing core components...")
    engine = TriangulumEngine()
    monitor = EngineMonitor(engine)
    engine.monitor = monitor
    
    # Initialize metrics collection
    metrics = MetricsCollector()
    
    # Initialize the agent coordinator
    print("Setting up agent coordination...")
    coordinator = AutoGenCoordinator(engine)
    engine.coordinator = coordinator
    
    # Add our test bug to the system
    test_bug_path = Path("test_bug.py")
    if test_bug_path.exists():
        print(f"Loading test bug from {test_bug_path}...")
        with open(test_bug_path, 'r') as f:
            code_content = f.read()
        
        # Create a bug state for our division by zero error
        bug = BugState(
            phase=Phase.REPRO,  # Start in REPRO phase
            timer=5,
            attempts=0,
            code_snippet=code_content,  # Contains the code with division by zero error
        )
        
        # The BugState class doesn't have error_message or file_path fields
        # but we can print them for informational purposes
        print(f"Bug source file: {test_bug_path}")
        print(f"Expected error: division by zero")
        
        # Add the bug to the engine
        engine.bugs.append(bug)
        print(f"Added bug to the engine")
    
    # Print initial system state
    print(f"\nInitial state:")
    print(f"- Free agents: {engine.free_agents}")
    print(f"- Entropy budget: {monitor.H0_bits:.2f} bits")
    print(f"- Maximum bugs: {engine.MAX_BUGS}")
    print(f"- Maximum ticks: {engine.MAX_TICKS}")
    
    # Run for a few ticks to show the system in action
    print("\nRunning simulation...")
    for i in range(30):  # Run for 30 ticks to give agents time to work
        print(f"\nTick {i+1}:")
        await engine.tick()  # Use await here to properly handle the coroutine
        
        # Record metrics
        metrics.record_tick(engine)
        
        # Print current state
        bug_counts = {}
        for bug in engine.bugs:
            phase_name = bug.phase.name
            bug_counts[phase_name] = bug_counts.get(phase_name, 0) + 1
        
        print(f"- Free agents: {engine.free_agents}")
        print(f"- Bug states: {bug_counts}")
        print(f"- Entropy: {monitor.g_bits:.2f}/{monitor.H0_bits:.2f} bits")
        
        # Check if done
        if monitor.done():
            print("\n✅ All bugs resolved successfully!")
            break
        
        # Small delay to let the dashboard update
        await asyncio.sleep(0.5)
    
    # Generate a summary
    summary = metrics.finalize_run()
    
    print("\n=== Run Summary ===")
    print(f"Total ticks: {summary['total_ticks']}")
    print(f"Success rate: {summary['success_rate']:.2f}")
    print(f"Total bugs: {summary['bugs_total']}")
    print(f"Bugs resolved: {summary['bugs_resolved']}")
    
    print("\nDemonstration complete!")


if __name__ == "__main__":
    asyncio.run(main())
