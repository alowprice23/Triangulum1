#!/usr/bin/env python3
"""
Run Fixed Triangulum Dashboard

This script launches the fixed Triangulum dashboard that properly connects to the backend.
It uses the triangulum_integrated_dashboard_compact.py implementation which:
1. Connects to real Triangulum system via the message bus
2. Uses the proper AgenticDashboard class
3. Shows real-time activity from the agents instead of simulated data
4. Only falls back to simulation mode if backend is unavailable
"""

import os
import sys
import argparse
import logging
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run Fixed Triangulum Dashboard')
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./triangulum_dashboard_integrated',
        help='Directory for dashboard output files'
    )
    
    parser.add_argument(
        '--simulation',
        action='store_true',
        help='Force simulation mode even if backend is available'
    )
    
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not automatically open browser'
    )
    
    return parser.parse_args()

def main():
    """Run the fixed Triangulum dashboard."""
    args = parse_arguments()
    
    # Check if required files exist
    required_files = [
        'triangulum_integrated_dashboard_compact.py',
        'triangulum_dashboard_backend_connector.py'
    ]
    
    for file in required_files:
        if not os.path.exists(file):
            logger.error(f"Required file '{file}' not found!")
            return 1
    
    # Construct command
    cmd = [sys.executable, 'triangulum_integrated_dashboard_compact.py']
    
    if args.output_dir:
        cmd.extend(['--output-dir', args.output_dir])
    
    if args.simulation:
        cmd.append('--simulation')
    
    if args.no_browser:
        cmd.append('--no-browser')
    
    # Print status
    print("\n" + "=" * 80)
    print("FIXED TRIANGULUM DASHBOARD".center(80))
    print("=" * 80 + "\n")
    
    print("Starting the fixed Triangulum dashboard with proper backend connections...")
    print(f"Dashboard files will be saved to: {args.output_dir}")
    
    if args.simulation:
        print("Running in SIMULATION MODE (forced)")
    else:
        print("Attempting to connect to real backend (will fall back to simulation if unavailable)")
    
    print("\nPress Ctrl+C to stop the dashboard\n")
    
    # Run the dashboard
    try:
        subprocess.run(cmd)
        return 0
    except KeyboardInterrupt:
        print("\nDashboard stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Error running dashboard: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
