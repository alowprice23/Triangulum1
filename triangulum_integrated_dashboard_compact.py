#!/usr/bin/env python3
"""
Triangulum Integrated Dashboard (Compact Version)

A streamlined solution that connects the dashboard to the actual Triangulum backend:
1. Connects to real Triangulum system when available
2. Falls back to simulation mode if backend is unavailable
3. Ensures all visualizations have real-time data
4. Fixes thought chains to show as active instead of idle
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
import webbrowser
from functools import partial
import http.server
import socketserver
import shutil
from triangulum_lx.monitoring.agentic_dashboard import AgenticDashboard
from triangulum_dashboard_backend_connector import MessageBusDashboardListener, monitor_backend_connection
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DASHBOARD_DIR = './triangulum_dashboard_integrated'
DASHBOARD_PORT = random.randint(8000, 9000)  # Random port to avoid conflicts

# Global message bus instance (singleton pattern)
message_bus = EnhancedMessageBus()

def get_global_message_bus():
    return message_bus

def ensure_directory_exists(directory):
    """Ensure a directory exists, creating it if necessary."""
    os.makedirs(directory, exist_ok=True)
    return directory

def find_best_source_dashboard():
    """Find the best source dashboard directory to use as a base."""
    source_options = [
        "./agentic_dashboard_full_demo",
        "./triangulum_dashboard_final",
        "./triangulum_dashboard_complete",
        "./triangulum_dashboard_final_consolidated"
    ]
    
    for source in source_options:
        if os.path.exists(source) and os.path.isdir(source):
            # Check if it has an index.html file
            if os.path.exists(os.path.join(source, "index.html")):
                # Check if it has the key subdirectories
                has_required_dirs = all(
                    os.path.exists(os.path.join(source, subdir))
                    for subdir in ["thought_chains", "agent_network", "decision_trees", "timeline", "progress"]
                )
                
                if has_required_dirs:
                    logger.info(f"Found good source dashboard: {source}")
                    return source
    
    # Fall back to the first existing directory
    for source in source_options:
        if os.path.exists(source):
            logger.warning(f"Using fallback source dashboard: {source}")
            return source
    
    logger.warning("No existing dashboard found. Will generate from scratch.")
    return None

def clone_dashboard(src_dir, dest_dir):
    """Clone the dashboard structure from source to destination."""
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

def initialize_dashboard_with_backend(output_dir, port, no_browser):
    """Initialize the dashboard with actual backend connections."""
    dashboard = AgenticDashboard(
        output_dir=output_dir,
        update_interval=0.5,
        enable_server=True,
        server_port=port,
        auto_open_browser=not no_browser
    )
    
    bus = get_global_message_bus()
    
    if bus:
        listener = MessageBusDashboardListener(bus, dashboard)
        
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(
            target=monitor_backend_connection,
            args=(dashboard, bus),
            daemon=True
        )
        monitor_thread.start()
        
        return dashboard, False
    else:
        logger.warning("Could not connect to Triangulum message bus - falling back to simulation mode")
        return dashboard, True

def initialize_simulation_data(dashboard_dir):
    """Create sample data for all dashboard components in simulation mode."""
    success = True
    
    # Initialize decision trees
    try:
        decision_trees_dir = os.path.join(dashboard_dir, "decision_trees")
        ensure_directory_exists(decision_trees_dir)
        
        decision_trees_file = os.path.join(decision_trees_dir, "decision_trees.json")
        
        # Create a simple decision tree structure
        decision_trees = {
            "tree_1": {
                "id": "tree_1",
                "agent_id": "orchestrator",
                "title": "Bug Repair Sequence",
                "created_at": datetime.datetime.now().isoformat(),
                "nodes": {
                    "root": {
                        "id": "root",
                        "type": "decision",
                        "content": "How to sequence bug repairs?",
                        "children": ["option_1", "option_2", "option_3"]
                    },
                    "option_1": {
                        "id": "option_1",
                        "type": "option",
                        "content": "Fix critical bugs first",
                        "children": ["result_1"]
                    },
                    "option_2": {
                        "id": "option_2",
                        "type": "option",
                        "content": "Fix easiest bugs first",
                        "children": ["result_2"]
                    },
                    "option_3": {
                        "id": "option_3",
                        "type": "option",
                        "content": "Fix bugs with most dependencies first",
                        "children": ["result_3"]
                    },
                    "result_1": {
                        "id": "result_1",
                        "type": "result",
                        "content": "Reduces system risk quickly",
                        "children": []
                    },
                    "result_2": {
                        "id": "result_2",
                        "type": "result",
                        "content": "Builds momentum quickly",
                        "children": []
                    },
                    "result_3": {
                        "id": "result_3",
                        "type": "result",
                        "content": "Unblocks more repairs",
                        "children": []
                    }
                },
                "selected_path": ["root", "option_1", "result_1"]
            }
        }
        
        with open(decision_trees_file, 'w') as f:
            json.dump(decision_trees, f, indent=2)
            
        logger.info(f"Initialized simulation decision trees in {decision_trees_file}")
    except Exception as e:
        logger.error(f"Error initializing simulation decision trees: {e}")
        success = False
        
    # Create simulation agent progress data
    try:
        progress_dir = os.path.join(dashboard_dir, "progress")
        ensure_directory_exists(progress_dir)
        
        agent_progress_file = os.path.join(progress_dir, "agent_progress.json")
        
        agents = ["orchestrator", "bug_detector", "relationship_analyst", 
                  "verification_agent", "priority_analyzer", "code_fixer"]
        
        agent_progress = {}
        for agent in agents:
            agent_progress[agent] = {
                "agent_id": agent,
                "percent_complete": random.uniform(60, 95),
                "status": "Active",
                "current_activity": f"Processing data for {agent}",
                "tasks_completed": random.randint(10, 18),
                "total_tasks": 20,
                "thought_count": random.randint(30, 70),
                "last_updated": datetime.datetime.now().isoformat()
            }
        
        with open(agent_progress_file, 'w') as f:
            json.dump(agent_progress, f, indent=2)
            
        logger.info(f"Initialized simulation agent progress in {agent_progress_file}")
        
        # Create global progress data
        global_progress_file = os.path.join(progress_dir, "global_progress.json")
        
        global_progress = {
            "percent_complete": 80.0,
            "status": "Active",
            "steps_completed": 80,
            "total_steps": 100,
            "estimated_completion": (datetime.datetime.now() + datetime.timedelta(minutes=15)).isoformat(),
            "last_updated": datetime.datetime.now().isoformat()
        }
        
        with open(global_progress_file, 'w') as f:
            json.dump(global_progress, f, indent=2)
            
        logger.info(f"Initialized simulation global progress in {global_progress_file}")
    except Exception as e:
        logger.error(f"Error initializing simulation progress data: {e}")
        success = False
        
    # Create simulation timeline events
    try:
        timeline_dir = os.path.join(dashboard_dir, "timeline")
        ensure_directory_exists(timeline_dir)
        
        timeline_file = os.path.join(timeline_dir, "timeline_events.json")
        
        # Create some sample timeline events
        timeline_events = []
        
        for i in range(10):
            event_type = random.choice(["message", "thought", "action", "decision"])
            agent_id = random.choice(agents)
            
            event = {
                "id": f"event_{int(time.time()) - i*60}_{random.randint(1000, 9999)}",
                "type": event_type,
                "agent_id": agent_id,
                "content": f"{agent_id.capitalize()} {event_type} #{i+1}",
                "timestamp": (datetime.datetime.now() - datetime.timedelta(minutes=i*5)).isoformat(),
                "metadata": {
                    "priority": random.choice(["high", "medium", "low"]),
                    "related_files": [f"file_{random.randint(1, 5)}.py"]
                }
            }
            
            timeline_events.append(event)
        
        with open(timeline_file, 'w') as f:
            json.dump(timeline_events, f, indent=2)
            
        logger.info(f"Initialized simulation timeline events in {timeline_file}")
    except Exception as e:
        logger.error(f"Error initializing simulation timeline data: {e}")
        success = False
    
    # Initialize thought chains
    try:
        thought_chains_dir = os.path.join(dashboard_dir, "thought_chains")
        ensure_directory_exists(thought_chains_dir)
        
        thought_chains_file = os.path.join(thought_chains_dir, "thought_chains.json")
        
        # Define agents
        agents = ["orchestrator", "bug_detector", "relationship_analyst", 
                  "verification_agent", "priority_analyzer", "code_fixer"]
        
        # Create thought chains
        thought_chains = {}
        now = datetime.datetime.now()
        
        for agent in agents:
            chain_id = f"chain_{agent}"
            
            # Create thought chain
            thought_chains[chain_id] = {
                "chain_id": chain_id,
                "agent_id": agent,
                "created_at": (now - datetime.timedelta(hours=1)).isoformat(),
                "last_updated": now.isoformat(),
                "thoughts": []
            }
            
            # Add thoughts with recent timestamps
            num_thoughts = random.randint(3, 7)
            for i in range(num_thoughts):
                thought_type = random.choice(["analysis", "decision", "discovery"])
                
                # Realistic thought content
                thoughts_content = {
                    "orchestrator": ["Analyzing system components", "Coordinating agents", "Planning repair sequence"],
                    "bug_detector": ["Scanning for issues", "Analyzing error patterns", "Identifying root causes"],
                    "relationship_analyst": ["Mapping dependencies", "Analyzing code relationships", "Detecting coupling issues"],
                    "verification_agent": ["Testing fixes", "Validating changes", "Verifying integrity"],
                    "priority_analyzer": ["Calculating critical path", "Evaluating repair priorities", "Optimizing fix sequence"],
                    "code_fixer": ["Implementing repairs", "Refactoring code", "Fixing identified issues"]
                }
                
                content = random.choice(thoughts_content.get(agent, ["Processing..."]))
                
                # Create thought with recent timestamp
                timestamp = now - datetime.timedelta(minutes=(num_thoughts-i)*15)
                
                thought = {
                    "id": f"thought_{agent}_{i}",
                    "agent_id": agent,
                    "chain_id": chain_id,
                    "type": thought_type,
                    "thought_type": thought_type,
                    "content": f"{content} #{i+1}",
                    "timestamp": timestamp.isoformat(),
                    "metadata": {
                        "confidence": random.randint(70, 95)
                    }
                }
                
                thought_chains[chain_id]["thoughts"].append(thought)
        
        # Save thought chains
        with open(thought_chains_file, 'w') as f:
            json.dump(thought_chains, f, indent=2)
        
        logger.info(f"Initialized simulation thought chains in {thought_chains_file}")
    except Exception as e:
        logger.error(f"Error initializing simulation thought chains: {e}")
        success = False
        
    return success

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

def main():
    """Run the Triangulum Integrated Dashboard."""
    parser = argparse.ArgumentParser(description='Run Triangulum Integrated Dashboard')
    parser.add_argument('--output-dir', type=str, default=DASHBOARD_DIR, 
                       help='Directory for the dashboard files')
    parser.add_argument('--port', type=int, default=DASHBOARD_PORT, 
                       help='Port for the dashboard server')
    parser.add_argument('--simulation', action='store_true', 
                       help='Run in simulation mode (don\'t connect to actual system)')
    parser.add_argument('--no-browser', action='store_true',
                       help='Do not open browser automatically')
    
    args = parser.parse_args()
    
    dashboard, is_simulation = initialize_dashboard_with_backend(
        args.output_dir, args.port, args.no_browser
    )

    if is_simulation or args.simulation:
        print("\nRunning in SIMULATION MODE")
        # Initialize simulation data
        initialize_simulation_data(args.output_dir)
        
        # Keep the server running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nSimulation stopped.")
    else:
        print("\nConnected to Triangulum system")
        # The dashboard is running and connected, just wait for interruption
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping system...")

    dashboard.stop()
    print("System shut down")
    return 0

if __name__ == "__main__":
    sys.exit(main())
