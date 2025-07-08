#!/usr/bin/env python3
"""
Run Final Triangulum Agentic Dashboard

This script provides a comprehensive, all-in-one solution for running the
Triangulum agentic dashboard. It generates all necessary data and visualization
files, then launches a stable web server to host the dashboard.
"""

import os
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

# --- Data Generation Functions ---

def create_progress_data(output_dir):
    """Create and save progress data files."""
    progress_dir = os.path.join(output_dir, "progress")
    ensure_directory_exists(progress_dir)
    
    agents = ["orchestrator", "bug_detector", "relationship_analyst", "verification_agent", "priority_analyzer", "code_fixer"]
    agent_progress = {}
    for agent in agents:
        agent_progress[agent] = {
            "agent_id": agent, "percent_complete": random.uniform(50, 95),
            "status": "Active" if random.random() > 0.25 else "Idle",
            "current_activity": random.choice(["Analyzing dependencies", "Detecting bugs", "Verifying changes", "Planning repairs"]),
            "tasks_completed": random.randint(8, 18), "total_tasks": 20,
            "thought_count": random.randint(30, 70), "last_updated": datetime.datetime.now().isoformat()
        }
    with open(os.path.join(progress_dir, "agent_progress.json"), 'w') as f:
        json.dump(agent_progress, f, indent=2)
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
            
        events.append({"id": str(uuid.uuid4()), "type": event_type, "timestamp": timestamp.isoformat(), "agent_id": agent, "content": content, "metadata": metadata})
        
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    with open(os.path.join(timeline_dir, "timeline_events.json"), 'w') as f:
        json.dump(events, f, indent=2)
    logger.info(f"Timeline data created in {timeline_dir}")

def create_decision_tree_data(output_dir):
    """Create and save decision tree data."""
    trees_dir = os.path.join(output_dir, "decision_trees")
    ensure_directory_exists(trees_dir)
    
    agents = ["orchestrator", "bug_detector", "relationship_analyst"]
    decision_trees = {}
    
    for agent in agents:
        tree_id = str(uuid.uuid4())
        root_node = {"id": str(uuid.uuid4()), "name": "Root", "type": "root", "content": "Start of process", "children": []}
        
        for i in range(random.randint(2, 4)):
            child = {"id": str(uuid.uuid4()), "name": f"Analysis Step {i+1}", "type": "analysis", "content": f"Analyzing condition {i+1}", "confidence": random.randint(70, 95), "children": []}
            if i == 0:
                for j in range(random.randint(1, 3)):
                    grandchild = {"id": str(uuid.uuid4()), "name": f"Action {j+1}", "type": "action", "content": f"Take action {j+1}", "confidence": random.randint(80, 99), "children": []}
                    child["children"].append(grandchild)
            root_node["children"].append(child)
            
        decision_trees[tree_id] = {"tree_id": tree_id, "agent_id": agent, "name": f"{agent.capitalize()} Process", "root": root_node}

    with open(os.path.join(trees_dir, "decision_trees.json"), 'w') as f:
        json.dump(decision_trees, f, indent=2)
    logger.info(f"Decision tree data created in {trees_dir}")

def create_agent_network_data(output_dir):
    """Create and save agent network data."""
    network_dir = os.path.join(output_dir, "agent_network")
    ensure_directory_exists(network_dir)
    messages = []
    agents = ["orchestrator", "bug_detector", "relationship_analyst", "verification_agent", "priority_analyzer", "code_fixer"]
    for i in range(30):
        source = random.choice(agents)
        target = random.choice([a for a in agents if a != source])
        messages.append({
            "id": str(uuid.uuid4()),
            "source": source,
            "target": target,
            "type": random.choice(["request", "response", "info"]),
            "timestamp": (datetime.datetime.now() - datetime.timedelta(seconds=i*15)).isoformat()
        })
    with open(os.path.join(network_dir, "messages.json"), 'w') as f:
        json.dump(messages, f, indent=2)
    logger.info(f"Agent network data created in {network_dir}")

def create_thought_chains_data(output_dir):
    """Create and save thought chains data."""
    chains_dir = os.path.join(output_dir, "thought_chains")
    ensure_directory_exists(chains_dir)
    thought_chains = {}
    agents = ["bug_detector", "priority_analyzer", "code_fixer"]
    for agent in agents:
        chain_id = f"chain_{agent}_{random.randint(1,10)}"
        thoughts = []
        for i in range(random.randint(3, 7)):
            thoughts.append({
                "id": str(uuid.uuid4()),
                "content": f"Step {i+1}: {random.choice(['Analyzing...', 'Considering...', 'Deciding...', 'Concluding...'])}",
                "type": random.choice(["analysis", "decision", "planning"]),
                "timestamp": (datetime.datetime.now() - datetime.timedelta(minutes=i)).isoformat()
            })
        thought_chains[chain_id] = {"chain_id": chain_id, "agent_id": agent, "thoughts": thoughts}
    with open(os.path.join(chains_dir, "thought_chains.json"), 'w') as f:
        json.dump(thought_chains, f, indent=2)
    logger.info(f"Thought chains data created in {chains_dir}")


# --- HTML Generation ---

def create_html_files(output_dir):
    """Create the main index.html and all component HTML files."""
    # Main index.html
    index_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Triangulum Agentic Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif; margin: 0; background-color: #f0f2f5; }
        .header { background-color: #001529; color: white; padding: 16px 24px; font-size: 24px; font-weight: 600; }
        .tab-bar { display: flex; background-color: white; border-bottom: 1px solid #d9d9d9; padding: 0 24px; }
        .tab { padding: 14px 16px; cursor: pointer; color: #595959; border-bottom: 3px solid transparent; margin-bottom: -1px; }
        .tab.active { color: #1890ff; border-bottom-color: #1890ff; }
        .content { padding: 24px; display: none; }
        .content.active { display: block; }
        iframe { border: none; width: 100%; height: 85vh; background-color: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="header">Triangulum Agentic Dashboard</div>
    <div class="tab-bar">
        <div class="tab active" onclick="switchTab('overview')">Overview</div>
        <div class="tab" onclick="switchTab('timeline')">Timeline</div>
        <div class="tab" onclick="switchTab('decision_trees')">Decision Trees</div>
        <div class="tab" onclick="switchTab('agent_network')">Agent Network</div>
        <div class="tab" onclick="switchTab('thought_chains')">Thought Chains</div>
    </div>
    <div id="overview-content" class="content active"><iframe src="progress/progress.html"></iframe></div>
    <div id="timeline-content" class="content"><iframe src="timeline/timeline.html"></iframe></div>
    <div id="decision_trees-content" class="content"><iframe src="decision_trees/decision_trees.html"></iframe></div>
    <div id="agent_network-content" class="content"><iframe src="agent_network/agent_network.html"></iframe></div>
    <div id="thought_chains-content" class="content"><iframe src="thought_chains/thought_chains.html"></iframe></div>
    <script>
        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
            document.querySelector(`.tab[onclick="switchTab('${tabName}')"]`).classList.add('active');
            document.getElementById(`${tabName}-content`).classList.add('active');
        }
    </script>
</body>
</html>"""
    with open(os.path.join(output_dir, "index.html"), 'w') as f:
        f.write(index_html)

    # Generic component HTML template
    component_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: sans-serif; padding: 20px; }}
        pre {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word; }}
    </style>
</head>
<body>
    <h2>{title}</h2>
    <div id="data-container"><p>Loading data...</p></div>
    <script>
        // Determine the correct JSON file to fetch
        let jsonFile = '{json_file}';
        
        function fetchData() {{
            fetch(jsonFile)
                .then(res => res.ok ? res.json() : Promise.reject(`File not found: {json_file}`))
                .then(data => {{
                    document.getElementById('data-container').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                }})
                .catch(error => {{
                    document.getElementById('data-container').innerHTML = '<p style="color: red;">Error loading data: ' + error + '</p>';
                }});
        }}
        setInterval(fetchData, 5000);
        fetchData();
    </script>
</body>
</html>"""

    # Create HTML files for each component
    components = {
        "progress": "agent_progress.json",
        "timeline": "timeline_events.json",
        "decision_trees": "decision_trees.json",
        "agent_network": "messages.json",
        "thought_chains": "thought_chains.json"
    }
    for name, json_file in components.items():
        component_dir = os.path.join(output_dir, name)
        ensure_directory_exists(component_dir)
        title = name.replace('_', ' ').title()
        with open(os.path.join(component_dir, f"{name}.html"), 'w') as f:
            f.write(component_template.format(title=title, json_file=json_file))
    
    logger.info("All HTML files created successfully.")


# --- Main Execution ---

def main():
    """Run the comprehensive dashboard script."""
    parser = argparse.ArgumentParser(description='Run the Triangulum agentic dashboard')
    parser.add_argument('--directory', type=str, default='./triangulum_dashboard_final', help='Directory for dashboard files')
    parser.add_argument('--port', type=int, default=None, help='Port for the server (default: random)')
    parser.add_argument('--no-browser', action='store_true', help='Do not open the browser automatically')
    
    args = parser.parse_args()
    
    # Create all necessary files
    ensure_directory_exists(args.directory)
    create_progress_data(args.directory)
    create_timeline_data(args.directory)
    create_decision_tree_data(args.directory)
    create_agent_network_data(args.directory)
    create_thought_chains_data(args.directory)
    create_html_files(args.directory)
    
    # Use functools.partial to pass the directory to the handler
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=args.directory)
    
    port = args.port or random.randint(8000, 9000)
    
    print("=" * 80)
    print("TRIANGULUM AGENTIC DASHBOARD".center(80))
    print("=" * 80)
    
    try:
        # The handler needs to serve from the correct directory.
        # SimpleHTTPRequestHandler serves from the current working directory by default.
        # By using functools.partial, we are setting the directory for all instances of the handler.
        # We no longer need to os.chdir.
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"\nDashboard server started at http://localhost:{port}/")
            print("Serving files from:", os.path.abspath(args.directory))
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
