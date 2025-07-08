#!/usr/bin/env python3
"""
Run Complete Triangulum Agentic Dashboard

This script launches the full Triangulum agentic dashboard by:
1. Using existing visualizations from agentic_dashboard_full_demo for working sections
2. Only generating new data for sections that need it
3. Launching a web server with all components properly integrated
"""

import os
import shutil
import http.server
import socketserver
import webbrowser
import random
import logging
import argparse
import threading
import json
import datetime
import uuid
import sys
from functools import partial

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_directory_exists(directory):
    """Ensure a directory exists, creating it if necessary."""
    os.makedirs(directory, exist_ok=True)
    return directory

def copy_existing_dashboard_files(src_dir, dest_dir):
    """Copy existing dashboard files while preserving structure."""
    if os.path.exists(src_dir):
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        
        # Copy index.html if it exists
        src_index = os.path.join(src_dir, 'index.html')
        if os.path.exists(src_index):
            shutil.copy2(src_index, os.path.join(dest_dir, 'index.html'))
            logger.info(f"Copied existing index.html from {src_dir}")
        
        # Copy existing directories that have good visualizations
        for subdir in ['progress', 'timeline', 'decision_trees', 'agent_network', 'thought_chains']:
            src_subdir = os.path.join(src_dir, subdir)
            if os.path.exists(src_subdir):
                dest_subdir = os.path.join(dest_dir, subdir)
                if os.path.exists(dest_subdir):
                    shutil.rmtree(dest_subdir)
                shutil.copytree(src_subdir, dest_subdir)
                logger.info(f"Copied existing {subdir} directory")
    else:
        logger.warning(f"Source directory {src_dir} does not exist. Will generate all files from scratch.")
        return False
    return True

def create_progress_data(output_dir):
    """Create and save progress data files."""
    progress_dir = os.path.join(output_dir, "progress")
    ensure_directory_exists(progress_dir)
    
    agents = ["orchestrator", "bug_detector", "relationship_analyst", "verification_agent", "priority_analyzer", "code_fixer"]
    agent_progress = {}
    for agent in agents:
        agent_progress[agent] = {
            "agent_id": agent, 
            "percent_complete": random.uniform(50, 95),
            "status": "Active" if random.random() > 0.25 else "Idle",
            "current_activity": random.choice(["Analyzing dependencies", "Detecting bugs", "Verifying changes", "Planning repairs"]),
            "tasks_completed": random.randint(8, 18), 
            "total_tasks": 20,
            "thought_count": random.randint(30, 70), 
            "last_updated": datetime.datetime.now().isoformat()
        }
    with open(os.path.join(progress_dir, "agent_progress.json"), 'w') as f:
        json.dump(agent_progress, f, indent=2)
    
    # Also create global progress data if needed
    global_progress = {
        "percent_complete": 80.0, 
        "status": "Running Analysis",
        "steps_completed": 80, 
        "total_steps": 100,
        "estimated_completion": (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat(),
        "last_updated": datetime.datetime.now().isoformat()
    }
    with open(os.path.join(progress_dir, "global_progress.json"), 'w') as f:
        json.dump(global_progress, f, indent=2)
    
    logger.info(f"Progress data created in {progress_dir}")

def create_timeline_data(output_dir):
    """Create and save timeline data file."""
    timeline_dir = os.path.join(output_dir, "timeline")
    ensure_directory_exists(timeline_dir)
    
    events = []
    agents = ["orchestrator", "bug_detector", "relationship_analyst", "verification_agent"]
    for i in range(60):
        event_type = "thought" if i % 2 == 0 else "message"
        agent = random.choice(agents)
        timestamp = datetime.datetime.now() - datetime.timedelta(minutes=i * 3)
        
        if event_type == "thought":
            content = random.choice([f"Analyzing module {i}", f"Discovered potential issue in function X", f"Planning next steps for bug #{i}"])
            metadata = {"thought_type": random.choice(["analysis", "discovery", "planning"]), "confidence": random.randint(60, 99)}
        else:
            target_agent = random.choice([a for a in agents if a != agent])
            content = random.choice([f"Requesting analysis of file Y", f"Sending bug report #{i}", f"Verification of fix for #{i-1} complete"])
            metadata = {"message_type": "request", "target_agent": target_agent}
            
        events.append({
            "id": str(uuid.uuid4()), 
            "type": event_type, 
            "timestamp": timestamp.isoformat(), 
            "agent_id": agent, 
            "content": content, 
            "metadata": metadata
        })
        
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    with open(os.path.join(timeline_dir, "timeline_events.json"), 'w') as f:
        json.dump(events, f, indent=2)
    logger.info(f"Timeline data created in {timeline_dir}")

def create_decision_trees_data(output_dir):
    """Create and save decision tree data."""
    trees_dir = os.path.join(output_dir, "decision_trees")
    ensure_directory_exists(trees_dir)
    
    agents = ["orchestrator", "bug_detector", "relationship_analyst"]
    decision_trees = {}
    
    for agent in agents:
        tree_id = str(uuid.uuid4())
        root_node = {
            "id": str(uuid.uuid4()),
            "name": "Root", 
            "type": "root", 
            "content": "Start of decision process",
            "children": []
        }
        
        # Add a few decisions with children
        for i in range(random.randint(2, 4)):
            decision = {
                "id": str(uuid.uuid4()),
                "name": f"Decision {i+1}", 
                "type": "decision",
                "content": f"This is decision {i+1}", 
                "confidence": random.randint(70, 95),
                "children": []
            }
            
            # Add actions for each decision
            for j in range(random.randint(1, 3)):
                action = {
                    "id": str(uuid.uuid4()),
                    "name": f"Action {j+1}", 
                    "type": "action",
                    "content": f"Perform action {j+1}", 
                    "confidence": random.randint(80, 99),
                    "children": []
                }
                decision["children"].append(action)
            
            root_node["children"].append(decision)
            
        decision_trees[tree_id] = {
            "tree_id": tree_id,
            "agent_id": agent,
            "name": f"{agent.capitalize()} Decision Process",
            "root": root_node,
            "created_at": (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat(),
            "last_updated": datetime.datetime.now().isoformat(),
            "status": "Active"
        }
    
    with open(os.path.join(trees_dir, "decision_trees.json"), 'w') as f:
        json.dump(decision_trees, f, indent=2)
    logger.info(f"Decision tree data created in {trees_dir}")

def create_agent_network_data(output_dir):
    """Create and save agent network data."""
    network_dir = os.path.join(output_dir, "agent_network")
    ensure_directory_exists(network_dir)
    
    agents = ["orchestrator", "bug_detector", "relationship_analyst", "verification_agent", "priority_analyzer", "code_fixer"]
    messages = []
    
    for i in range(30):
        source = random.choice(agents)
        target = random.choice([a for a in agents if a != source])
        
        message_type = random.choice(["request", "response", "notification"])
        content = random.choice([
            f"Analyzing module {random.randint(1, 5)}",
            f"Found {random.randint(1, 5)} issues in file X",
            f"Verifying fix for issue #{random.randint(100, 999)}",
            "Please analyze these dependencies",
            "Update on progress: 75% complete"
        ])
        
        messages.append({
            "id": str(uuid.uuid4()),
            "source": source,
            "target": target,
            "type": message_type,
            "content": content,
            "timestamp": (datetime.datetime.now() - datetime.timedelta(minutes=i*2)).isoformat()
        })
    
    with open(os.path.join(network_dir, "messages.json"), 'w') as f:
        json.dump(messages, f, indent=2)
    logger.info(f"Agent network data created in {network_dir}")

def create_thought_chains_data(output_dir):
    """Create and save thought chains data."""
    chains_dir = os.path.join(output_dir, "thought_chains")
    ensure_directory_exists(chains_dir)
    
    agents = ["bug_detector", "priority_analyzer", "code_fixer"]
    thought_chains = {}
    
    for agent in agents:
        chain_id = f"chain_{agent}_{random.randint(1, 10)}"
        thoughts = []
        
        for i in range(random.randint(4, 8)):
            step_type = random.choice(["analysis", "decision", "planning"])
            content = f"Step {i+1}: {random.choice(['Analyzing...', 'Considering...', 'Deciding...', 'Concluding...'])}"
            
            thoughts.append({
                "id": str(uuid.uuid4()),
                "content": content,
                "type": step_type,
                "timestamp": (datetime.datetime.now() - datetime.timedelta(minutes=i*5)).isoformat()
            })
        
        thought_chains[chain_id] = {
            "chain_id": chain_id,
            "agent_id": agent,
            "thoughts": thoughts
        }
    
    with open(os.path.join(chains_dir, "thought_chains.json"), 'w') as f:
        json.dump(thought_chains, f, indent=2)
    logger.info(f"Thought chains data created in {chains_dir}")

def main():
    """Run the dashboard script."""
    parser = argparse.ArgumentParser(description='Run the Triangulum Agentic Dashboard')
    parser.add_argument('--output-dir', type=str, default='./triangulum_dashboard_complete', help='Directory for dashboard files')
    parser.add_argument('--source-dir', type=str, default='./agentic_dashboard_full_demo', help='Source directory for existing dashboard files')
    parser.add_argument('--port', type=int, default=None, help='Port for the server (default: random)')
    parser.add_argument('--no-browser', action='store_true', help='Do not open the browser automatically')
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    ensure_directory_exists(args.output_dir)
    
    # Try to copy existing dashboard files first
    copied_existing = copy_existing_dashboard_files(args.source_dir, args.output_dir)
    
    # Update the data for each component
    create_progress_data(args.output_dir)
    create_timeline_data(args.output_dir)
    create_decision_trees_data(args.output_dir)
    create_agent_network_data(args.output_dir)
    create_thought_chains_data(args.output_dir)
    
    # Use functools.partial to pass the directory to the handler
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=args.output_dir)
    
    # Use a random port if none specified to avoid conflicts
    port = args.port or random.randint(8000, 9000)
    
    print("=" * 80)
    print("TRIANGULUM AGENTIC DASHBOARD".center(80))
    print("=" * 80)
    print()
    
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"Dashboard server started at http://localhost:{port}/")
            print(f"Serving files from: {os.path.abspath(args.output_dir)}")
            print("Press Ctrl+C to stop the server")
            
            if not args.no_browser:
                webbrowser.open(f"http://localhost:{port}/")
            
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
