#!/usr/bin/env python3
"""
Run Triangulum with Live Dashboard

This script runs the Triangulum system with LLM-powered agents and connects the dashboard
to show real-time activity. It demonstrates the full integration between the agent system
and the dashboard.
"""

import os
import sys
import time
import logging
import argparse
import threading
import subprocess
import signal
import tempfile
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run Triangulum with Live Dashboard')
    
    parser.add_argument(
        '--no-dashboard',
        action='store_true',
        help='Run Triangulum without the dashboard'
    )
    
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not automatically open browser for dashboard'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Run in debug mode with additional logging'
    )
    
    return parser.parse_args()

def run_command(command, name, log_file=None):
    """Run a command in a subprocess and log its output."""
    logger.info(f"Starting {name}: {command}")
    
    if log_file:
        with open(log_file, 'w') as f:
            process = subprocess.Popen(
                command,
                stdout=f,
                stderr=subprocess.STDOUT,
                shell=True
            )
    else:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            universal_newlines=True
        )
        
        # Log output in real-time
        for line in iter(process.stdout.readline, ''):
            logger.info(f"{name}: {line.strip()}")
    
    return process

def run_triangulum_system(log_file):
    """Run the Triangulum system."""
    # Find the best Triangulum runner script
    runner_options = [
        'run_triangulum_agentic_demo.py',
        'run_triangulum_demo.py',
        'run_triangulum_live_system.py'
    ]
    
    runner_script = None
    for option in runner_options:
        if os.path.exists(option):
            runner_script = option
            break
    
    if not runner_script:
        logger.error("Could not find a Triangulum runner script!")
        return None
    
    # Run the Triangulum system
    command = f"{sys.executable} {runner_script}"
    return run_command(command, "Triangulum System", log_file)

def run_dashboard(log_file, no_browser=False):
    """Run the Triangulum dashboard."""
    # Run the dashboard
    command = f"{sys.executable} run_fixed_triangulum_dashboard.py"
    
    if no_browser:
        command += " --no-browser"
    
    return run_command(command, "Triangulum Dashboard", log_file)

def main():
    """Run Triangulum with the live dashboard."""
    args = parse_arguments()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("\n" + "=" * 80)
    print("TRIANGULUM WITH LIVE DASHBOARD".center(80))
    print("=" * 80 + "\n")
    
    print("Starting Triangulum system with LLM-powered agents and connecting the dashboard")
    print("to show real-time activity. This demonstrates how the agent system integrates")
    print("with the dashboard to provide visibility into the system's operations.\n")
    
    # Create log directory
    log_dir = os.path.join(tempfile.gettempdir(), f"triangulum_logs_{int(time.time())}")
    os.makedirs(log_dir, exist_ok=True)
    
    system_log = os.path.join(log_dir, "triangulum_system.log")
    dashboard_log = os.path.join(log_dir, "triangulum_dashboard.log")
    
    # Start Triangulum system
    system_process = run_triangulum_system(system_log)
    
    if not system_process:
        logger.error("Failed to start Triangulum system")
        return 1
    
    # Give the system time to initialize
    print("Waiting for Triangulum system to initialize...")
    time.sleep(5)
    
    # Start dashboard if requested
    dashboard_process = None
    if not args.no_dashboard:
        dashboard_process = run_dashboard(dashboard_log, args.no_browser)
        
        if not dashboard_process:
            logger.error("Failed to start Triangulum dashboard")
            system_process.terminate()
            return 1
    
    # Wait for processes to complete or for user to interrupt
    try:
        print("\nTriangulum system is running with the live dashboard")
        print("Press Ctrl+C to stop\n")
        
        while True:
            # Check if processes are still running
            if system_process.poll() is not None:
                logger.error("Triangulum system process terminated unexpectedly")
                break
            
            if dashboard_process and dashboard_process.poll() is not None:
                logger.error("Dashboard process terminated unexpectedly")
                break
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nStopping Triangulum system and dashboard...")
    
    finally:
        # Terminate processes
        if system_process and system_process.poll() is None:
            system_process.terminate()
            system_process.wait(timeout=5)
        
        if dashboard_process and dashboard_process.poll() is None:
            dashboard_process.terminate()
            dashboard_process.wait(timeout=5)
    
    print(f"\nLog files are available in: {log_dir}")
    print("\nTriangulum system and dashboard have been stopped")
    return 0

if __name__ == "__main__":
    sys.exit(main())
