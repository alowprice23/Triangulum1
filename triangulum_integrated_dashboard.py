#!/usr/bin/env python3
"""
Triangulum Integrated Dashboard

A comprehensive solution that:
1. Fixes all dashboard components (thoughts, overview, feedback, etc.)
2. Connects to the actual Triangulum backend system for live data
3. Falls back to simulation mode if backend is unavailable
4. Provides consistent data structures across all visualizations
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
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DASHBOARD_DIR = './triangulum_dashboard_integrated'
DASHBOARD_PORT = random.randint(8000, 9000)  # Random port to avoid conflicts

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
                    for subdir in ["thought_chains", "agent_network", "decision_trees", "timeline"]
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

def prepare_thought_chains(dashboard_dir):
    """Create or update thought chains with proper structure for active visualization."""
    thought_chains_dir = os.path.join(dashboard_dir, "thought_chains")
    ensure_directory_exists(thought_chains_dir)
    
    # Prepare the JSON file for thought chains
    json_file = os.path.join(thought_chains_dir, "thought_chains.json")
    
    # Define the agents
    agents = ["orchestrator", "bug_detector", "relationship_analyst", 
              "verification_agent", "priority_analyzer", "code_fixer"]
    
    # Create a thought chain for each agent
    thought_chains = {}
    now = datetime.datetime.now()
    
    for agent in agents:
        chain_id = f"chain_{agent}"
        
        thought_chains[chain_id] = {
            "chain_id": chain_id,
            "agent_id": agent,
            "created_at": (now - datetime.timedelta(hours=1)).isoformat(),
            "last_updated": now.isoformat(),
            "thoughts": []
        }
        
        # Add 3-5 thoughts for each agent
        num_thoughts = random.randint(3, 5)
        for i in range(num_thoughts):
            thought_type = random.choice(["analysis", "decision", "discovery"])
            thought_content = get_realistic_thought_content(agent, i, thought_type)
            
            # Ensure timestamps are recent but sequential
            timestamp = now - datetime.timedelta(minutes=(num_thoughts-i)*3)
            
            thought_chains[chain_id]["thoughts"].append({
                "id": f"thought_{agent}_{i}",
                "agent_id": agent,
                "chain_id": chain_id,
                "type": thought_type,
                "thought_type": thought_type,  # Redundant for compatibility
                "content": thought_content,
                "timestamp": timestamp.isoformat(),
                "metadata": {
                    "confidence": random.randint(70, 95)
                }
            })
    
    # Save the thought chains
    with open(json_file, 'w') as f:
        json.dump(thought_chains, f, indent=2)
    
    logger.info(f"Prepared thought chains data in {json_file}")
    
    # Check if thought_chains.html exists, if not, create it
    html_file = os.path.join(thought_chains_dir, "thought_chains.html")
    if not os.path.exists(html_file):
        with open(html_file, 'w') as f:
            f.write(get_thought_chains_html_template())
        
        logger.info(f"Created thought chains HTML template in {html_file}")

def get_realistic_thought_content(agent, index, thought_type):
    """Generate realistic thought content based on agent and thought type."""
    thoughts = {
        "orchestrator": [
            "Analyzing system components to determine optimal repair strategy",
            "Prioritizing bug fixes based on dependency graph analysis",
            "Coordinating repair sequence to minimize regression risks",
            "Deploying verification agents to test proposed fixes",
            "Final validation of integrated fix solution"
        ],
        "bug_detector": [
            "Scanning module imports for circular dependencies",
            "Identified potential null reference in error handling path",
            "Found race condition in asynchronous operation sequence",
            "Type mismatch detected in data transformation layer",
            "Memory leak detected in resource cleanup path"
        ],
        "relationship_analyst": [
            "Mapping dependencies between core system components",
            "Analyzing impact of changes to message bus on dependent modules",
            "Detected high coupling between visualization and data processing layers",
            "Recommending refactoring to reduce coupling in feedback system",
            "Structural analysis of monitoring subsystem complete"
        ],
        "verification_agent": [
            "Executing test suite against proposed changes",
            "Validating fix against historical failure cases",
            "Stress testing system under peak load conditions",
            "Verifying compatibility with existing API contracts",
            "All validation checks passed, changes approved"
        ],
        "priority_analyzer": [
            "Calculating critical path for repair operations",
            "Identified highest impact issues based on user workflows",
            "Recommending fix order based on dependency constraints",
            "Updated priority matrix with latest system health metrics",
            "Finalized repair strategy with optimal resource allocation"
        ],
        "code_fixer": [
            "Implementing patch for message routing logic",
            "Refactoring visualization renderer to fix memory leak",
            "Adding proper error handling to dashboard data fetcher",
            "Resolving merge conflicts in monitoring integration",
            "Optimizing dashboard rendering for large datasets"
        ]
    }
    
    # Return a realistic thought based on agent type, or fallback if not found
    if agent in thoughts and index < len(thoughts[agent]):
        return thoughts[agent][index]
    else:
        return f"{thought_type.capitalize()} step {index+1} for system improvement"

def prepare_agent_network(dashboard_dir):
    """Create or update agent network visualization with proper structure."""
    agent_network_dir = os.path.join(dashboard_dir, "agent_network")
    ensure_directory_exists(agent_network_dir)
    
    # Prepare the JSON file for agent network messages
    json_file = os.path.join(agent_network_dir, "messages.json")
    
    # Define the agents
    agents = ["orchestrator", "bug_detector", "relationship_analyst", 
              "verification_agent", "priority_analyzer", "code_fixer"]
    
    # Create messages between agents
    messages = []
    now = datetime.datetime.now()
    
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
            "id": f"msg_{i}",
            "source": source,
            "target": target,
            "type": message_type,
            "content": content,
            "timestamp": (now - datetime.timedelta(minutes=i*2)).isoformat()
        })
    
    # Save the messages
    with open(json_file, 'w') as f:
        json.dump(messages, f, indent=2)
    
    logger.info(f"Prepared agent network data in {json_file}")
    
    # Check if agent_network.html exists, if not, create it
    html_file = os.path.join(agent_network_dir, "agent_network.html")
    if not os.path.exists(html_file):
        # Implementing a simple placeholder - you'd implement a proper template
        with open(html_file, 'w') as f:
            f.write("<html><body><h1>Agent Network Visualization</h1><div id='network'></div></body></html>")
        
        logger.info(f"Created agent network HTML template in {html_file}")

def prepare_timeline(dashboard_dir):
    """Create or update timeline visualization with proper structure."""
    timeline_dir = os.path.join(dashboard_dir, "timeline")
    ensure_directory_exists(timeline_dir)
    
    # Prepare the JSON file for timeline events
    json_file = os.path.join(timeline_dir, "timeline_events.json")
    
    # Define the agents
    agents = ["orchestrator", "bug_detector", "relationship_analyst", "verification_agent"]
    
    # Create timeline events
    events = []
    now = datetime.datetime.now()
    
    for i in range(60):
        event_type = "thought" if i % 2 == 0 else "message"
        agent = random.choice(agents)
        timestamp = now - datetime.timedelta(minutes=i * 3)
        
        if event_type == "thought":
            content = random.choice([f"Analyzing module {i}", f"Discovered potential issue in function X", f"Planning next steps for bug #{i}"])
            metadata = {"thought_type": random.choice(["analysis", "discovery", "planning"]), "confidence": random.randint(60, 99)}
        else:
            target_agent = random.choice([a for a in agents if a != agent])
            content = random.choice([f"Requesting analysis of file Y", f"Sending bug report #{i}", f"Verification of fix for #{i-1} complete"])
            metadata = {"message_type": "request", "target_agent": target_agent}
            
        events.append({
            "id": f"event_{i}", 
            "type": event_type, 
            "timestamp": timestamp.isoformat(), 
            "agent_id": agent, 
            "content": content, 
            "metadata": metadata
        })
        
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    with open(json_file, 'w') as f:
        json.dump(events, f, indent=2)
    
    logger.info(f"Prepared timeline data in {json_file}")
    
    # Check if timeline.html exists, if not, create it
    html_file = os.path.join(timeline_dir, "timeline.html")
    if not os.path.exists(html_file):
        # Implementing a simple placeholder - you'd implement a proper template
        with open(html_file, 'w') as f:
            f.write("<html><body><h1>Timeline Visualization</h1><div id='timeline'></div></body></html>")
        
        logger.info(f"Created timeline HTML template in {html_file}")

def prepare_decision_trees(dashboard_dir):
    """Create or update decision trees visualization with proper structure."""
    decision_trees_dir = os.path.join(dashboard_dir, "decision_trees")
    ensure_directory_exists(decision_trees_dir)
    
    # Prepare the JSON file for decision trees
    json_file = os.path.join(decision_trees_dir, "decision_trees.json")
    
    # Define the agents
    agents = ["orchestrator", "bug_detector", "relationship_analyst"]
    
    # Create decision trees
    trees = {}
    now = datetime.datetime.now()
    
    for agent in agents:
        tree_id = f"tree_{agent}"
        
        # Create the root node
        root_node = {
            "id": f"node_root_{agent}",
            "name": "Root", 
            "type": "root", 
            "content": "Start of decision process",
            "children": []
        }
        
        # Add decisions with children
        for i in range(random.randint(2, 4)):
            decision_id = f"node_decision_{agent}_{i}"
            decision = {
                "id": decision_id,
                "name": f"Decision {i+1}", 
                "type": "decision",
                "content": f"This is decision {i+1}", 
                "confidence": random.randint(70, 95),
                "children": []
            }
            
            # Add actions for each decision
            for j in range(random.randint(1, 3)):
                action_id = f"node_action_{agent}_{i}_{j}"
                action = {
                    "id": action_id,
                    "name": f"Action {j+1}", 
                    "type": "action",
                    "content": f"Perform action {j+1}", 
                    "confidence": random.randint(80, 99),
                    "children": []
                }
                decision["children"].append(action)
            
            root_node["children"].append(decision)
        
        # Add the tree
        trees[tree_id] = {
            "tree_id": tree_id,
            "agent_id": agent,
            "name": f"{agent.capitalize()} Decision Process",
            "root": root_node,
            "created_at": (now - datetime.timedelta(hours=1)).isoformat(),
            "last_updated": now.isoformat(),
            "status": "Active"
        }
    
    # Save the trees
    with open(json_file, 'w') as f:
        json.dump(trees, f, indent=2)
    
    logger.info(f"Prepared decision trees data in {json_file}")
    
    # Check if decision_trees.html exists, if not, create it
    html_file = os.path.join(decision_trees_dir, "decision_trees.html")
    if not os.path.exists(html_file):
        # Implementing a simple placeholder - you'd implement a proper template
        with open(html_file, 'w') as f:
            f.write("<html><body><h1>Decision Trees Visualization</h1><div id='trees'></div></body></html>")
        
        logger.info(f"Created decision trees HTML template in {html_file}")

def prepare_overview(dashboard_dir):
    """Create or update overview (progress) visualization with proper structure and feedback form."""
    progress_dir = os.path.join(dashboard_dir, "progress")
    ensure_directory_exists(progress_dir)
    
    # Prepare agent progress data
    agent_progress_file = os.path.join(progress_dir, "agent_progress.json")
    
    # Define the agents
    agents = ["orchestrator", "bug_detector", "relationship_analyst", 
              "verification_agent", "priority_analyzer", "code_fixer"]
    
    # Create agent progress data
    agent_progress = {}
    for agent in agents:
        agent_progress[agent] = {
            "agent_id": agent,
            "percent_complete": random.uniform(60, 95),
            "status": "Active" if random.random() > 0.2 else "Idle",
            "current_activity": random.choice([
                "Analyzing dependencies", "Detecting bugs", "Verifying changes",
                "Planning repairs", "Fixing issues", "Awaiting instructions"
            ]),
            "tasks_completed": random.randint(10, 18),
            "total_tasks": 20,
            "thought_count": random.randint(30, 70),
            "last_updated": datetime.datetime.now().isoformat()
        }
    
    # Save agent progress data
    with open(agent_progress_file, 'w') as f:
        json.dump(agent_progress, f, indent=2)
    
    logger.info(f"Prepared agent progress data in {agent_progress_file}")
    
    # Prepare global progress data
    global_progress_file = os.path.join(progress_dir, "global_progress.json")
    
    global_progress = {
        "percent_complete": 80.0,
        "status": "Analyzing",
        "steps_completed": 80,
        "total_steps": 100,
        "estimated_completion": (datetime.datetime.now() + datetime.timedelta(minutes=15)).isoformat(),
        "last_updated": datetime.datetime.now().isoformat()
    }
    
    # Save global progress data
    with open(global_progress_file, 'w') as f:
        json.dump(global_progress, f, indent=2)
    
    logger.info(f"Prepared global progress data in {global_progress_file}")
    
    # Create progress.html with feedback form
    html_file = os.path.join(progress_dir, "progress.html")
    with open(html_file, 'w') as f:
        f.write(get_overview_html_template())
    
    logger.info(f"Created progress HTML with feedback form in {html_file}")

def prepare_main_index(dashboard_dir):
    """Create or update the main index.html file."""
    index_file = os.path.join(dashboard_dir, "index.html")
    
    with open(index_file, 'w') as f:
        f.write(get_main_index_html_template())
    
    logger.info(f"Prepared main index.html in {index_file}")

def create_backend_connector(dashboard_dir):
    """Create backend connector script to integrate with Triangulum system."""
    data_dir = os.path.join(dashboard_dir, "data")
    ensure_directory_exists(data_dir)
    
    # Create backend connector script
    connector_file = os.path.join(data_dir, "backend_connector.js")
    
    with open(connector_file, 'w') as f:
        f.write(get_backend_connector_js())
    
    logger.info(f"Created backend connector in {connector_file}")

def start_dashboard_server(dashboard_dir, port):
    """Start HTTP server to serve the dashboard."""
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=dashboard_dir)
    
    print("\n" + "=" * 80)
    print("TRIANGULUM INTEGRATED DASHBOARD".center(80))
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
        "chain_bug_detector": [
            {"content": "Starting bug detection process", "type": "analysis"},
            {"content": "Reviewing file dependencies", "type": "analysis"}
        ],
        "chain_priority_analyzer": [
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

def get_thought_chains_html_template():
    """Get HTML template for thought chains visualization."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Triangulum Thought Chains</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }
        h1, h2, h3 { margin-top: 0; color: #333; }
        .thought-chain { margin-bottom: 30px; }
        .thought-chain-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .thought-chain-title { font-weight: bold; font-size: 18px; }
        .thought-chain-status { font-size: 12px; padding: 3px 8px; border-radius: 12px; }
        .status-active { background-color: #e8f5e9; color: #2e7d32; }
        .status-idle { background-color: #f5f5f5; color: #757575; }
        .thought { padding: 15px; border-left: 3px solid #1e88e5; background-color: #f9f9f9; margin-bottom: 10px; }
        .thought-header { display: flex; justify-content: space-between; font-size: 12px; color: #757575; margin-bottom: 5px; }
        .thought-content { color: #333; }
        .thought-type-analysis { border-left-color: #1e88e5; }
        .thought-type-decision { border-left-color: #43a047; }
        .thought-type-discovery { border-left-color: #ffb300; }
        .thought-type-planning { border-left-color: #8e24aa; }
        .empty-state { text-align: center; padding: 40px; color: #757575; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Thought Chains</h1>
        
        <div id="thought-chains-container">
            <!-- Thought chains will be populated here -->
            <div class="empty-state">Loading thought chains...</div>
        </div>
    </div>
    
    <script>
        // Function to format date
        function formatDate(dateString) {
            try {
                const date = new Date(dateString);
                return date.toLocaleString();
            } catch (e) {
                return "Unknown";
            }
        }
        
        // Function to determine chain status based on last thought timestamp
        function getChainStatus(thoughts) {
            if (!thoughts || thoughts.length === 0) return "idle";
            
            const now = new Date();
            const lastThoughtTime = new Date(thoughts[0].timestamp);
            const diffMinutes = (now - lastThoughtTime) / (1000 * 60);
            
            if (diffMinutes < 10) return "active";
            if (diffMinutes < 30) return "recent";
            return "idle";
        }
        
        // Function to update thought chains
        function updateThoughtChains() {
            fetch('thought_chains.json')
                .then
