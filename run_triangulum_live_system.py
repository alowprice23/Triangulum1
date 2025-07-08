#!/usr/bin/env python3
"""
Triangulum Live System with Dashboard

This script launches the full Triangulum Agentic System and connects it
to the working dashboard for real-time monitoring and visualization.
"""

import os
import sys
import time
import json
import logging
import threading
import subprocess
import datetime
import argparse
import random
import signal
import webbrowser
from functools import partial
import http.server
import socketserver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DASHBOARD_DIR = './triangulum_dashboard_live'
DASHBOARD_PORT = random.randint(8000, 9000)  # Random port to avoid conflicts

def ensure_directory_exists(directory):
    """Ensure a directory exists, creating it if necessary."""
    os.makedirs(directory, exist_ok=True)
    return directory

def clone_dashboard(src_dir, dest_dir):
    """Clone the dashboard structure from source to destination."""
    import shutil
    
    # First ensure the destination directory exists
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    
    # If source doesn't exist, log an error and return
    if not os.path.exists(src_dir):
        logger.error(f"Source directory {src_dir} does not exist!")
        return False
    
    # Clone everything - structure and files
    for item in os.listdir(src_dir):
        src_item = os.path.join(src_dir, item)
        dest_item = os.path.join(dest_dir, item)
        
        if os.path.isdir(src_item):
            if os.path.exists(dest_item):
                shutil.rmtree(dest_item)
            shutil.copytree(src_item, dest_item)
            logger.info(f"Copied directory: {item}")
        else:
            shutil.copy2(src_item, dest_item)
            logger.info(f"Copied file: {item}")
    
    logger.info(f"Successfully cloned dashboard from {src_dir} to {dest_dir}")
    return True

def start_dashboard_server(dashboard_dir, port):
    """Start HTTP server to serve the dashboard."""
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=dashboard_dir)
    
    print("\n" + "=" * 80)
    print("TRIANGULUM LIVE DASHBOARD".center(80))
    print("=" * 80 + "\n")
    
    try:
        httpd = socketserver.TCPServer(("", port), handler)
        print(f"Dashboard server started at http://localhost:{port}/")
        print(f"Serving files from: {os.path.abspath(dashboard_dir)}")
        
        # Open browser
        webbrowser.open(f"http://localhost:{port}/")
        
        # Start server in a thread
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        return httpd
    except Exception as e:
        logger.error(f"Failed to start dashboard server: {e}")
        return None

def update_dashboard_data(dashboard_dir, data_dict):
    """Update dashboard data files with new system status."""
    try:
        # Update agent progress
        progress_file = os.path.join(dashboard_dir, "progress", "agent_progress.json")
        if os.path.exists(progress_file):
            with open(progress_file, 'w') as f:
                json.dump(data_dict['agent_progress'], f, indent=2)
        
        # Add new timeline events
        timeline_file = os.path.join(dashboard_dir, "timeline", "timeline_events.json")
        if os.path.exists(timeline_file):
            with open(timeline_file, 'r') as f:
                timeline_events = json.load(f)
            
            # Prepend new events
            for event in data_dict['new_events']:
                event['timestamp'] = datetime.datetime.now().isoformat()
                event['id'] = f"event_{int(time.time())}_{random.randint(1000, 9999)}"
                timeline_events.insert(0, event)
            
            with open(timeline_file, 'w') as f:
                json.dump(timeline_events[:100], f, indent=2)  # Keep only last 100 events
        
        # Update thought chains
        thoughts_file = os.path.join(dashboard_dir, "thought_chains", "thought_chains.json") 
        if os.path.exists(thoughts_file):
            with open(thoughts_file, 'r') as f:
                thought_chains = json.load(f)
            
            # Add new thoughts to each chain
            for chain_id, new_thoughts in data_dict['new_thoughts'].items():
                if chain_id in thought_chains:
                    for thought in new_thoughts:
                        thought['timestamp'] = datetime.datetime.now().isoformat()
                        thought['id'] = f"thought_{int(time.time())}_{random.randint(1000, 9999)}"
                        thought_chains[chain_id]['thoughts'].insert(0, thought)
            
            with open(thoughts_file, 'w') as f:
                json.dump(thought_chains, f, indent=2)
        
        logger.info(f"Updated dashboard data files in {dashboard_dir}")
        return True
    except Exception as e:
        logger.error(f"Error updating dashboard data: {e}")
        return False

def run_triangulum_system():
    """Run the Triangulum system with all agents."""
    try:
        # First look for the specific triangulum agentic demo script
        script_path = 'run_triangulum_agentic_demo.py'
        if not os.path.exists(script_path):
            # Fall back to run_triangulum_demo.py if the agentic version doesn't exist
            script_path = 'run_triangulum_demo.py'
            if not os.path.exists(script_path):
                logger.error("Could not find Triangulum system script to run")
                return None
        
        logger.info(f"Starting Triangulum system using {script_path}...")
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        logger.info(f"Triangulum system started (PID: {process.pid})")
        return process
    except Exception as e:
        logger.error(f"Failed to start Triangulum system: {e}")
        return None

def simulate_system_activity():
    """Simulate system activity for dashboard updates."""
    agents = ["orchestrator", "bug_detector", "relationship_analyst", 
              "verification_agent", "priority_analyzer", "code_fixer"]
    
    # Initial state - agents with different progress levels
    agent_progress = {}
    for agent in agents:
        agent_progress[agent] = {
            "agent_id": agent,
            "percent_complete": random.uniform(10, 30),
            "status": "Active",
            "current_activity": "Initializing...",
            "tasks_completed": 0,
            "total_tasks": 20,
            "thought_count": 0,
            "last_updated": datetime.datetime.now().isoformat()
        }
    
    # Prepare initial event and thought data structure
    event_templates = [
        {"type": "message", "agent_id": "orchestrator", "content": "Starting system analysis", 
         "metadata": {"message_type": "notification", "priority": "high"}},
        {"type": "thought", "agent_id": "bug_detector", "content": "Scanning codebase for issues", 
         "metadata": {"thought_type": "analysis", "confidence": 85}}
    ]
    
    thought_templates = {
        "chain_bug_detector_1": [
            {"content": "Starting bug detection process", "type": "analysis"},
            {"content": "Reviewing file dependencies", "type": "analysis"}
        ],
        "chain_priority_analyzer_1": [
            {"content": "Initializing priority analysis", "type": "planning"},
            {"content": "Setting up analysis parameters", "type": "decision"}
        ]
    }
    
    # Initial data package
    data = {
        'agent_progress': agent_progress,
        'new_events': event_templates,
        'new_thoughts': thought_templates
    }
    
    return data

def main():
    """Run the Triangulum Live System with Dashboard."""
    parser = argparse.ArgumentParser(description='Run Triangulum Live System with Dashboard')
    parser.add_argument('--dashboard-dir', type=str, default=DASHBOARD_DIR, 
                       help='Directory for the dashboard files')
    parser.add_argument('--source-dir', type=str, default='./agentic_dashboard_full_demo', 
                       help='Source directory for the existing dashboard')
    parser.add_argument('--port', type=int, default=DASHBOARD_PORT, 
                       help='Port for the dashboard server')
    parser.add_argument('--simulation', action='store_true', 
                       help='Run in simulation mode (don\'t start actual system)')
    
    args = parser.parse_args()
    
    # Prepare the dashboard
    ensure_directory_exists(args.dashboard_dir)
    clone_success = clone_dashboard(args.source_dir, args.dashboard_dir)
    if not clone_success:
        logger.error("Failed to prepare dashboard. Aborting.")
        return 1
    
    # Start dashboard server
    httpd = start_dashboard_server(args.dashboard_dir, args.port)
    if not httpd:
        return 1
    
    # Initialize with simulated data
    initial_data = simulate_system_activity()
    update_dashboard_data(args.dashboard_dir, initial_data)
    
    if args.simulation:
        # Simulation mode - just update the dashboard with fake data
        try:
            print("\nRunning in SIMULATION MODE")
            print("Press Ctrl+C to stop\n")
            
            step = 1
            while True:
                time.sleep(5)  # Update every 5 seconds
                
                # Update agent progress
                for agent in initial_data['agent_progress']:
                    # Increase progress by 1-5%
                    progress_increase = random.uniform(1, 5)
                    current_progress = initial_data['agent_progress'][agent]['percent_complete']
                    new_progress = min(current_progress + progress_increase, 100)
                    initial_data['agent_progress'][agent]['percent_complete'] = new_progress
                    
                    # Update activity
                    if step % 3 == 0:
                        activities = [
                            f"Analyzing module {random.randint(1, 10)}",
                            f"Processing file {random.randint(1, 20)}",
                            "Optimizing code structure",
                            "Verifying changes",
                            "Running tests",
                            "Identifying potential issues"
                        ]
                        initial_data['agent_progress'][agent]['current_activity'] = random.choice(activities)
                    
                    # Update last_updated timestamp
                    initial_data['agent_progress'][agent]['last_updated'] = datetime.datetime.now().isoformat()
                
                # Generate new events
                initial_data['new_events'] = []
                if step % 2 == 0:  # Add new event every other step
                    agent = random.choice(list(initial_data['agent_progress'].keys()))
                    event_type = random.choice(["thought", "message"])
                    
                    if event_type == "thought":
                        content = f"Step {step}: {random.choice(['Analyzing...', 'Evaluating...', 'Processing...'])}"
                        metadata = {"thought_type": random.choice(["analysis", "discovery", "decision"]), "confidence": random.randint(60, 99)}
                    else:
                        target = random.choice([a for a in initial_data['agent_progress'] if a != agent])
                        content = f"Step {step}: Sending {random.choice(['request', 'data', 'results'])} to {target}"
                        metadata = {"message_type": "notification", "priority": random.choice(["high", "medium", "low"]), "target": target}
                    
                    initial_data['new_events'].append({
                        "type": event_type,
                        "agent_id": agent,
                        "content": content,
                        "metadata": metadata
                    })
                
                # Generate new thoughts
                initial_data['new_thoughts'] = {}
                if step % 3 == 0:  # Add new thoughts every third step
                    # Use the chains we started with
                    for chain_id in ["chain_bug_detector_1", "chain_priority_analyzer_1"]:
                        agent_id = chain_id.split('_')[1]  # Extract agent from chain ID
                        thought_type = random.choice(["analysis", "decision", "planning"])
                        content = f"Step {step}: {random.choice(['Analyzing code structure', 'Evaluating repair options', 'Planning next action'])}"
                        
                        if chain_id not in initial_data['new_thoughts']:
                            initial_data['new_thoughts'][chain_id] = []
                        
                        initial_data['new_thoughts'][chain_id].append({
                            "content": content,
                            "type": thought_type
                        })
                
                # Update the dashboard
                update_dashboard_data(args.dashboard_dir, initial_data)
                print(f"Step {step}: Updated dashboard with new data")
                step += 1
                
        except KeyboardInterrupt:
            print("\nSimulation stopped.")
    else:
        # Start the actual Triangulum system
        process = run_triangulum_system()
        if not process:
            httpd.shutdown()
            return 1
        
        # Main loop to monitor system and update dashboard
        try:
            print("\nSystem is running")
            print("Press Ctrl+C to stop\n")
            
            while True:
                # Read system output
                output = process.stdout.readline()
                if output:
                    print(output.strip())
                
                # Check if process is still alive
                if process.poll() is not None:
                    logger.warning("Triangulum system process has terminated")
                    break
                
                # Wait a bit before next iteration
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nStopping system...")
            # Terminate the process
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        finally:
            httpd.shutdown()
    
    print("System shut down")
    return 0

if __name__ == "__main__":
    sys.exit(main())
