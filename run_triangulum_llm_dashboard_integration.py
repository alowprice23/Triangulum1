#!/usr/bin/env python3
"""
Triangulum LLM-Dashboard Integration

This script combines the LLM-powered Triangulum agents with the dashboard to demonstrate
how they work together. The LLM agents generate thoughts and communicate with each other,
and the dashboard shows their activity in real-time.
"""

import os
import sys
import time
import json
import logging
import argparse
import threading
import subprocess
import datetime
import tempfile
import random
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Triangulum LLM-Dashboard Integration')
    
    parser.add_argument(
        '--duration',
        type=int,
        default=300,  # 5 minutes by default
        help='Duration to run the integration demo in seconds'
    )
    
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not automatically open browser for dashboard'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    return parser.parse_args()

def run_command(command, name, log_file=None):
    """Run a command in a subprocess and capture its output."""
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

def run_llm_integration(duration, log_file):
    """Run the LLM integration script."""
    command = f"{sys.executable} triangulum_llm_integration.py --duration {duration}"
    return run_command(command, "LLM Integration", log_file)

def run_dashboard(no_browser, log_file):
    """Run the dashboard."""
    command = f"{sys.executable} run_fixed_triangulum_dashboard.py"
    
    if no_browser:
        command += " --no-browser"
    
    return run_command(command, "Dashboard", log_file)

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("\n" + "=" * 80)
    print("TRIANGULUM LLM-DASHBOARD INTEGRATION".center(80))
    print("=" * 80 + "\n")
    
    print("This script demonstrates the full integration between LLM-powered")
    print("Triangulum agents and the dashboard. The agents will generate")
    print("thoughts and communicate with each other, and the dashboard will")
    print("show their activity in real-time.\n")
    
    # Create log directory
    log_dir = os.path.join(tempfile.gettempdir(), f"triangulum_integration_{int(time.time())}")
    os.makedirs(log_dir, exist_ok=True)
    
    llm_log = os.path.join(log_dir, "llm_integration.log")
    dashboard_log = os.path.join(log_dir, "dashboard.log")
    
    print(f"Log files will be written to: {log_dir}\n")
    
    # Start the dashboard first
    print("Starting Triangulum Dashboard...")
    dashboard_process = run_dashboard(args.no_browser, dashboard_log)
    
    if not dashboard_process:
        logger.error("Failed to start dashboard")
        return 1
    
    # Give the dashboard time to initialize
    time.sleep(5)
    
    # Start the LLM integration
    print("Starting LLM-powered agents...")
    llm_process = run_llm_integration(args.duration, llm_log)
    
    if not llm_process:
        logger.error("Failed to start LLM integration")
        dashboard_process.terminate()
        return 1
    
    try:
        print("\nTriangulum LLM-Dashboard integration is running")
        print("You should now see real-time agent activity in the dashboard")
        print(f"The demo will run for {args.duration} seconds")
        print("Press Ctrl+C to stop early\n")
        
        # Wait for the LLM integration to complete
        llm_process.wait()
        
        print("\nLLM integration completed")
        
        # Give some time for final updates to appear in the dashboard
        print("Waiting for final dashboard updates...")
        time.sleep(5)
        
    except KeyboardInterrupt:
        print("\nStopping integration demo...")
    
    finally:
        # Clean up processes
        if llm_process and llm_process.poll() is None:
            llm_process.terminate()
            llm_process.wait(timeout=5)
        
        if dashboard_process and dashboard_process.poll() is None:
            dashboard_process.terminate()
            dashboard_process.wait(timeout=5)
    
    print("\nIntegration demo completed")
    print(f"Log files are available in: {log_dir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
