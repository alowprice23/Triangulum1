#!/usr/bin/env python3

import argparse
import logging
import sys
import asyncio
from pathlib import Path

# Add the parent directory to sys.path to enable imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from triangulum_lx.core.engine import TriangulumEngine
from triangulum_lx.core.monitor import Monitor
from triangulum_lx.agents.coordinator import AgentCoordinator
from triangulum_lx.monitoring.metrics import MetricsCollector
from triangulum_lx.human.interactive_mode import launch_interactive_mode
from triangulum_lx.core.state import BugState, Phase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("triangulum.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("triangulum.cli")


async def run_triangulum(args):
    """Run the Triangulum system with the given arguments."""
    logger.info(f"Starting Triangulum LX with mode: {args.mode}")
    
    # Initialize system with correct classes
    engine = TriangulumEngine()
    coordinator = AgentCoordinator(["observer", "analyst", "patcher", "verifier"])
    monitor = Monitor(engine)
    
    # Initialize metrics collection
    metrics = MetricsCollector()
    
    if args.mode == 'auto':
        # Fully automatic mode
        logger.info("Running in automatic mode")
        await run_automatic_mode(engine, monitor, coordinator, metrics, args)
    elif args.mode == 'batch':
        # Batch mode
        logger.info(f"Running in batch mode with config: {args.config}")
        await run_batch_mode(engine, monitor, coordinator, metrics, args)
    else:
        logger.error(f"Unknown mode: {args.mode}")
        sys.exit(1)
    
    # Finalize run and save metrics
    summary = metrics.finalize_run()
    logger.info(f"Run completed. Success rate: {summary['success_rate']:.2f}")
    
    return summary


async def run_automatic_mode(engine, monitor, coordinator, metrics, args):
    """Run the system in fully automatic mode."""
    max_ticks = args.max_ticks
    
    # Load source from args.source if specified
    if args.source:
        logger.info(f"Loading source from: {args.source}")
        source_path = Path(args.source)
        if source_path.is_dir():
            python_files = list(source_path.rglob("*.py"))
            logger.info(f"Found {len(python_files)} Python files to analyze.")
            for file_path in python_files:
                # Create a BugState for each file
                # This is a simplified representation. In a real scenario,
                # you would have a more sophisticated way of identifying and representing bugs.
                bug = BugState(phase=Phase.REPRO, timer=5, attempts=0, code_snippet=str(file_path))
                engine.bugs.append(bug)
        elif source_path.is_file():
            logger.info(f"Analyzing single file: {source_path}")
            bug = BugState(phase=Phase.REPRO, timer=5, attempts=0, code_snippet=str(source_path))
            engine.bugs.append(bug)
    
    # Run until completion or max ticks
    tick = 0
    while tick < max_ticks and not monitor.done():
        await engine.tick()
        metrics.record_tick(engine)
        
        if tick % 10 == 0:
            logger.info(f"Tick {tick}: {engine.free_agents} free agents, "
                       f"completed {sum(b.phase.name == 'DONE' for b in engine.bugs)} bugs")
        
        tick += 1
    
    logger.info(f"Automatic mode completed after {tick} ticks")


async def run_batch_mode(engine, monitor, coordinator, metrics, args):
    """Run the system in batch mode using a configuration file."""
    import json
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = json.load(f)
    
    # Process each job in the configuration
    for job_config in config.get('jobs', []):
        logger.info(f"Starting job: {job_config.get('name', 'unnamed')}")
        
        # Reset engine state for each job
        engine = TriangulumEngine()
        monitor = Monitor(engine)
        engine.monitor = monitor
        
        # Configure job-specific settings
        if 'agents' in job_config:
            engine.AGENTS = job_config['agents']
        
        if 'max_bugs' in job_config:
            engine.MAX_BUGS = job_config['max_bugs']
        
        # Run the job
        max_ticks = job_config.get('max_ticks', args.max_ticks)
        
        tick = 0
        while tick < max_ticks and not monitor.done():
            engine.tick()
            metrics.record_tick(engine)
            tick += 1
        
        # Log job results
        bugs_done = sum(b.phase.name == 'DONE' for b in engine.bugs)
        logger.info(f"Job completed after {tick} ticks. Resolved {bugs_done} bugs.")


def main():
    """Main entry point for the Triangulum CLI."""
    parser = argparse.ArgumentParser(
        description="Triangulum LX - Agentic Debugging System",
        epilog="For more information, see the documentation."
    )
    
    parser.add_argument(
        '-m', '--mode',
        choices=['interactive', 'auto', 'batch'],
        default='interactive',
        help='Execution mode (default: interactive)'
    )
    
    parser.add_argument(
        '-c', '--config',
        help='Path to configuration file for batch mode'
    )
    
    parser.add_argument(
        '-s', '--source',
        help='Path to source directory or file to analyze'
    )
    
    parser.add_argument(
        '-t', '--max-ticks',
        type=int, 
        default=60,
        help='Maximum number of ticks to run (default: 60)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--no-visualization',
        action='store_true',
        help='Disable visualization output'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='Triangulum LX 1.0.0'
    )
    
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check for required arguments
    if args.mode == 'batch' and not args.config:
        parser.error("Batch mode requires a configuration file (--config)")
    
    # Run in appropriate mode
    if args.mode == 'interactive':
        # Interactive mode uses its own main loop
        launch_interactive_mode()
    else:
        # For automatic and batch modes, run the async process
        asyncio.run(run_triangulum(args))


if __name__ == "__main__":
    main()