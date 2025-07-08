#!/usr/bin/env python3
"""
Run Triangulum Agentic Dashboard

This script provides a comprehensive solution for running the Triangulum
agentic dashboard. It generates all necessary data, including progress,
timeline, and decision trees, and then launches a web server to
visualize the data.
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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_directory_exists(directory):
    """Ensure a directory exists, creating it if necessary."""
    os.makedirs(directory, exist_ok=True)
    return directory

def create_progress_data(output_dir):
    """Create and save progress data."""
    progress_dir = ensure_directory_exists(os.path.join(output_dir, "progress"))
    
    # Create global progress data
    global_progress = {
        "percent_complete": 75.0,
        "status": "Analyzing",
        "steps_completed": 75,
        "total_steps": 100,
        "estimated_completion": (datetime.datetime.now() + datetime.timedelta(minutes=15)).isoformat(),
        "last_updated": datetime.datetime.now().isoformat()
    }
    
    with open(os.path.join(progress_dir, "global_progress.json"), 'w') as f:
        json.dump(global_progress, f, indent=2)
    
    # Create agent progress data
    agents = ["orchestrator", "bug_detector", "relationship_analyst", 
              "verification_agent", "priority_analyzer", "code_fixer"]
    
    agent_progress = {}
    for agent in agents:
        progress = random.uniform(40, 95)
        agent_progress[agent] = {
            "agent_id": agent,
            "percent_complete": progress,
            "status": "Active" if random.random() > 0.2 else "Idle",
            "current_activity": random.choice([
                "Analyzing dependencies", "Detecting bugs", "Verifying changes",
                "Planning repairs", "Fixing issues", "Awaiting instructions"
            ]),
            "tasks_completed": random.randint(5, 18),
            "total_tasks": 20,
            "thought_count": random.randint(20, 60),
            "last_updated": datetime.datetime.now().isoformat()
        }
    
    with open(os.path.join(progress_dir, "agent_progress.json"), 'w') as f:
        json.dump(agent_progress, f, indent=2)
    
    logger.info(f"Progress data created at {progress_dir}")

def create_timeline_data(output_dir):
    """Create and save timeline data."""
    timeline_dir = ensure_directory_exists(os.path.join(output_dir, "timeline"))
    
    events = []
    agents = ["orchestrator", "bug_detector", "relationship_analyst", 
              "verification_agent", "priority_analyzer", "code_fixer"]
    
    for i in range(50):
        event_type = "thought" if i % 2 == 0 else "message"
        agent = random.choice(agents)
        timestamp = datetime.datetime.now() - datetime.timedelta(minutes=i*5)
        
        if event_type == "thought":
            content = random.choice([
                f"Analyzing code structure in module {random.randint(1, 5)}",
                f"Found {random.randint(1, 10)} potential bugs",
                f"Determining optimal fix strategy for issue #{random.randint(100, 999)}",
            ])
            metadata = {"thought_type": random.choice(["analysis", "discovery", "decision"]), "confidence": random.randint(70, 99)}
        else:
            target_agent = random.choice([a for a in agents if a != agent])
            content = random.choice([
                f"Please analyze module {random.randint(1, 5)}",
                f"Found {random.randint(1, 10)} bugs, sending details",
                f"Verification complete, {random.randint(1, 5)} tests passing",
            ])
            metadata = {"message_type": random.choice(["request", "response", "notification"]), "priority": random.choice(["high", "medium", "low"]), "target_agent": target_agent}
        
        events.append({"id": str(uuid.uuid4()), "type": event_type, "timestamp": timestamp.isoformat(), "agent_id": agent, "content": content, "metadata": metadata})
    
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    
    with open(os.path.join(timeline_dir, "timeline_events.json"), 'w') as f:
        json.dump(events, f, indent=2)
    
    logger.info(f"Timeline data created at {timeline_dir}")

def create_decision_tree_data(output_dir):
    """Create and save decision tree data."""
    trees_dir = ensure_directory_exists(os.path.join(output_dir, "decision_trees"))
    
    agents = ["orchestrator", "bug_detector", "relationship_analyst"]
    decision_trees = {}
    agent_trees = {}
    
    for agent in agents:
        agent_trees[agent] = []
        tree_id = str(uuid.uuid4())
        agent_trees[agent].append(tree_id)
        
        root_node = {"id": str(uuid.uuid4()), "name": "Root", "type": "root", "content": "Decision tree root", "children": []}
        
        for i in range(random.randint(2, 4)):
            child = {"id": str(uuid.uuid4()), "name": f"Decision {i+1}", "type": "decision", "content": f"This is decision {i+1}", "confidence": random.randint(70, 95), "children": []}
            if child["type"] == "decision":
                child["alternatives"] = [{"name": f"Alternative for Decision {i+1}", "content": f"Alternative approach for decision {i+1}", "confidence": random.randint(50, 65)}]
            
            if i == 0:
                for j in range(random.randint(1, 3)):
                    grandchild = {"id": str(uuid.uuid4()), "name": f"Action {j+1}", "type": "action", "content": f"This is action {j+1}", "confidence": random.randint(80, 99), "children": []}
                    child["children"].append(grandchild)
            
            root_node["children"].append(child)
        
        decision_trees[tree_id] = {"tree_id": tree_id, "agent_id": agent, "name": f"{agent.capitalize()}'s Decision Process", "description": f"Decision process for {agent}", "created_at": (datetime.datetime.now() - datetime.timedelta(hours=2)).isoformat(), "last_updated": datetime.datetime.now().isoformat(), "status": "Active", "node_count": 10, "depth": 3, "root": root_node}
    
    with open(os.path.join(trees_dir, "decision_trees.json"), 'w') as f:
        json.dump(decision_trees, f, indent=2)
    
    with open(os.path.join(trees_dir, "agent_trees.json"), 'w') as f:
        json.dump(agent_trees, f, indent=2)
    
    logger.info(f"Decision tree data created at {trees_dir}")

def create_dashboard_files(output_dir):
    """Create all necessary data files for the dashboard."""
    logger.info(f"Creating dashboard files in {output_dir}...")
    create_progress_data(output_dir)
    create_timeline_data(output_dir)
    create_decision_tree_data(output_dir)
    create_index_html(output_dir)  # Add this line
    logger.info("Dashboard files created successfully.")

def create_index_html(output_dir):
    """Create the main index.html for the dashboard."""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Triangulum Agentic System Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f5f5f5; }
        .dashboard-header { background-color: #001529; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .dashboard-title { font-size: 24px; font-weight: bold; }
        .tab-bar { display: flex; background-color: white; border-bottom: 1px solid #e8e8e8; }
        .tab { padding: 12px 16px; cursor: pointer; border-bottom: 2px solid transparent; color: #595959; }
        .tab.active { color: #1890ff; border-bottom-color: #1890ff; }
        .tab-content { padding: 20px; display: none; }
        .tab-content.active { display: block; }
        iframe { border: none; width: 100%; height: 800px; }
    </style>
    <script>
        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(`tab-${tabId}`).classList.add('active');
            document.getElementById(`content-${tabId}`).classList.add('active');
            
            const iframe = document.getElementById(`${tabId}-iframe`);
            if (iframe && !iframe.src) {
                iframe.src = `${tabId}/${tabId}.html`; // Assumes html files are in subdirs
            }
        }
        
        document.addEventListener('DOMContentLoaded', () => {
            document.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', () => switchTab(tab.getAttribute('data-tab')));
            });
            switchTab('overview'); // Start with overview
        });
    </script>
</head>
<body>
    <div class="dashboard-header"><div class="dashboard-title">Triangulum Agentic System Dashboard</div></div>
    <div class="tab-bar">
        <div id="tab-overview" class="tab" data-tab="overview">Overview</div>
        <div id="tab-progress" class="tab" data-tab="progress">Progress</div>
        <div id="tab-timeline" class="tab" data-tab="timeline">Timeline</div>
        <div id="tab-decision_trees" class="tab" data-tab="decision_trees">Decision Trees</div>
    </div>
    
    <div id="content-overview" class="tab-content"><h2>Welcome to the Triangulum Dashboard</h2><p>Select a tab to view the system's status.</p></div>
    <div id="content-progress" class="tab-content"><iframe id="progress-iframe"></iframe></div>
    <div id="content-timeline" class="tab-content"><iframe id="timeline-iframe"></iframe></div>
    <div id="content-decision_trees" class="tab-content"><iframe id="decision_trees-iframe"></iframe></div>
</body>
</html>"""
    
    with open(os.path.join(output_dir, "index.html"), 'w') as f:
        f.write(html_content)
    
    # Also create dummy html files for the iframes
    for component in ["progress", "timeline", "decision_trees"]:
        ensure_directory_exists(os.path.join(output_dir, component))
        with open(os.path.join(output_dir, component, f"{component}.html"), 'w') as f:
            f.write(f"<html><body><p>Loading {component} data...</p><script>fetch('{component}.json').then(r=>r.json()).then(d=>document.body.innerHTML = `<pre>${JSON.stringify(d,null,2)}</pre>`);</script></body></html>")

    logger.info("Created index.html and component placeholder pages.")

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Simple HTTP request handler for serving dashboard files."""
    def __init__(self, *args, **kwargs):
        self.directory = DashboardHandler.dashboard_directory
        super().__init__(*args, directory=self.directory, **kwargs)
    
    def log_message(self, format, *args):
        pass

def main():
    """Run the comprehensive dashboard script."""
    parser = argparse.ArgumentParser(description='Run the Triangulum agentic dashboard')
    parser.add_argument('--directory', type=str, default='./triangulum_dashboard_final', help='Directory for dashboard files')
    parser.add_argument('--port', type=int, default=None, help='Port for the server (default: random)')
    parser.add_argument('--no-browser', action='store_true', help='Do not open the browser automatically')
    
    args = parser.parse_args()
    
    # Create dashboard files
    create_dashboard_files(args.directory)
    
    # Set the directory for the handler
    DashboardHandler.dashboard_directory = args.directory
    
    # Change to the dashboard directory
    os.chdir(args.directory)
    
    # Select a port
    port = args.port or random.randint(8000, 9000)
    
    print("=" * 80)
    print("TRIANGULUM AGENTIC DASHBOARD".center(80))
    print("=" * 80)
    print(f"\nStarting dashboard server at http://localhost:{port}/")
    
    try:
        with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
            print(f"Server started at http://localhost:{port}/")
            print("Press Ctrl+C to stop the server")
            
            if not args.no_browser:
                webbrowser.open(f"http://localhost:{port}/")
            
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
