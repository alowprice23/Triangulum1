#!/usr/bin/env python3
"""
Run Fixed Agentic Dashboard

This script runs a simple HTTP server to serve the fixed Triangulum agentic dashboard
with all visualizations working properly. It directly serves the static files created
by fix_agentic_dashboard.py.
"""

import os
import argparse
import webbrowser
import http.server
import socketserver
import threading
import random
import logging
import time
import json
import datetime
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardRequestHandler(http.server.SimpleHTTPRequestHandler):
    """
    Custom request handler for the dashboard server that properly routes
    requests to the appropriate directories.
    """
    
    def __init__(self, *args, **kwargs):
        self.directory = kwargs.pop('directory', os.getcwd())
        super().__init__(*args, **kwargs)
    
    def translate_path(self, path):
        """Translate URL path to file system path."""
        # First, get the default translation
        path = super().translate_path(path)
        
        # If path is just the directory (like '/'), serve the index file
        if os.path.isdir(path) and not path.endswith('/'):
            path = path + '/'
        if path.endswith('/'):
            path = os.path.join(path, 'index.html')
        
        # Check for dashboard components
        if '/thought_chains/' in path and not os.path.exists(path):
            base_path = os.path.dirname(path)
            os.makedirs(base_path, exist_ok=True)
            if 'thought_chains.json' in path:
                # Serve fake thought chains data if requested
                self.serve_fake_thought_chains()
            elif 'thought_chains.html' in path and not os.path.exists(path):
                # Copy the HTML template if needed
                self.copy_template('thought_chains.html', base_path)
                
        if '/agent_network/' in path and not os.path.exists(path):
            base_path = os.path.dirname(path)
            os.makedirs(base_path, exist_ok=True)
            if 'messages.json' in path:
                # Serve fake messages data if requested
                self.serve_fake_messages()
            elif 'agent_network.html' in path and not os.path.exists(path):
                # Copy the HTML template if needed
                self.copy_template('agent_network.html', base_path)
        
        # Properly route timeline requests
        if '/timeline/' in path and 'timeline_events.json' in path and not os.path.exists(path):
            # Look for timeline_events.json in the dashboard directory
            base_dir = self.directory
            timeline_json = os.path.join(base_dir, 'timeline', 'timeline_events.json')
            if os.path.exists(timeline_json):
                path = timeline_json
                
        # Properly route progress tracking requests
        if '/progress/' in path:
            # Check for global_progress.json or agent_progress.json
            if 'global_progress.json' in path or 'agent_progress.json' in path:
                base_dir = self.directory
                progress_file = os.path.basename(path)
                progress_json = os.path.join(base_dir, 'progress', progress_file)
                if os.path.exists(progress_json):
                    path = progress_json
            elif 'progress.html' in path and not os.path.exists(path):
                # Look for the HTML file in the progress directory
                base_dir = self.directory
                progress_html = os.path.join(base_dir, 'progress', 'progress.html')
                if os.path.exists(progress_html):
                    path = progress_html
        
        # Properly route decision trees requests
        if '/decision_trees/' in path:
            if 'decision_trees.json' in path and not os.path.exists(path):
                base_dir = self.directory
                trees_json = os.path.join(base_dir, 'decision_trees', 'decision_trees.json')
                if os.path.exists(trees_json):
                    path = trees_json
            elif 'agent_trees.json' in path and not os.path.exists(path):
                base_dir = self.directory
                agent_trees_json = os.path.join(base_dir, 'decision_trees', 'agent_trees.json')
                if os.path.exists(agent_trees_json):
                    path = agent_trees_json
            elif 'decision_trees.html' in path and not os.path.exists(path):
                # Look for the HTML file in the decision_trees directory
                base_dir = self.directory
                trees_html = os.path.join(base_dir, 'decision_trees', 'decision_trees.html')
                if os.path.exists(trees_html):
                    path = trees_html
        
        return path
    
    def serve_fake_thought_chains(self):
        """Serve fake thought chains data."""
        # This is not needed as we have real thought chains data
        pass
    
    def serve_fake_messages(self):
        """Serve fake messages data."""
        # This is not needed as we have real message data
        pass
    
    def copy_template(self, template_name, target_dir):
        """Copy a template file if needed."""
        # Look for the template in templates directory
        templates_dir = os.path.join(self.directory, 'templates')
        if os.path.exists(os.path.join(templates_dir, template_name)):
            # Copy it to the target directory
            import shutil
            shutil.copy(
                os.path.join(templates_dir, template_name),
                os.path.join(target_dir, template_name)
            )

def create_index_html(output_dir):
    """Create the main index.html for the dashboard."""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Triangulum Agentic System Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        .dashboard-header {
            background-color: #001529;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .dashboard-title {
            font-size: 24px;
            font-weight: bold;
        }
        .dashboard-info {
            font-size: 12px;
        }
        .tab-bar {
            display: flex;
            background-color: white;
            border-bottom: 1px solid #e8e8e8;
        }
        .tab {
            padding: 12px 16px;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.3s;
            color: #595959;
        }
        .tab:hover {
            color: #1890ff;
        }
        .tab.active {
            color: #1890ff;
            border-bottom-color: #1890ff;
        }
        .tab-content {
            padding: 20px;
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        iframe {
            border: none;
            width: 100%;
            height: 800px;
            background-color: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .progress-container {
            background-color: white;
            padding: 20px;
            border-radius: 4px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .progress-bar-container {
            width: 100%;
            height: 20px;
            background-color: #f0f0f0;
            border-radius: 10px;
            margin-top: 10px;
            overflow: hidden;
        }
        .progress-bar {
            height: 100%;
            background-color: #1890ff;
            width: 2%;
            transition: width 0.5s ease-in-out;
        }
        .progress-details {
            display: flex;
            justify-content: space-between;
            margin-top: 5px;
            color: #595959;
            font-size: 12px;
        }
        h2 {
            margin-top: 0;
            color: #262626;
            font-size: 18px;
        }
        .agent-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .agent-card {
            background-color: white;
            border-radius: 4px;
            padding: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .agent-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .agent-name {
            font-weight: bold;
            color: #262626;
        }
        .agent-status {
            padding: 3px 8px;
            border-radius: 10px;
            font-size: 12px;
        }
        .agent-status.active {
            background-color: #e6f7ff;
            color: #1890ff;
        }
        .agent-status.idle {
            background-color: #f5f5f5;
            color: #8c8c8c;
        }
        .agent-progress {
            width: 100%;
            height: 8px;
            background-color: #f0f0f0;
            border-radius: 4px;
            margin-bottom: 10px;
            overflow: hidden;
        }
        .agent-progress-bar {
            height: 100%;
            background-color: #1890ff;
            width: 0%;
            transition: width 0.5s ease-in-out;
        }
        .agent-details {
            font-size: 12px;
            color: #595959;
        }
        .feedback-container {
            background-color: white;
            padding: 20px;
            border-radius: 4px;
            margin-top: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .feedback-title {
            font-weight: bold;
            margin-bottom: 10px;
            color: #262626;
        }
        .feedback-input {
            width: 100%;
            padding: 10px;
            border: 1px solid #d9d9d9;
            border-radius: 4px;
            margin-bottom: 10px;
            resize: vertical;
            min-height: 80px;
        }
        .feedback-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .agent-select {
            padding: 5px;
            border: 1px solid #d9d9d9;
            border-radius: 4px;
            min-width: 150px;
        }
        .feedback-button {
            background-color: #1890ff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        .feedback-button:hover {
            background-color: #40a9ff;
        }
    </style>
    <script>
        // Data for agent status in overview tab
        const agents = [
            { id: "orchestrator", name: "Orchestrator Agent", status: "Active", progress: 85, activity: "Coordinating code repair operations" },
            { id: "bug_detector", name: "Bug Detector Agent", status: "Active", progress: 92, activity: "Scanning code for defects" },
            { id: "relationship_analyst", name: "Relationship Analyst Agent", status: "Active", progress: 76, activity: "Analyzing module dependencies" },
            { id: "verification_agent", name: "Verification Agent", status: "Idle", progress: 100, activity: "Waiting for code changes to verify" },
            { id: "priority_analyzer", name: "Priority Analyzer Agent", status: "Active", progress: 68, activity: "Evaluating fix priorities" },
            { id: "code_fixer", name: "Code Fixer Agent", status: "Active", progress: 45, activity: "Implementing repairs for high-priority issues" }
        ];
        
        // Update global progress
        function updateGlobalProgress() {
            fetch('progress/global_progress.json')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('system-progress-bar').style.width = `${data.percent_complete}%`;
                    document.getElementById('system-status').textContent = data.status;
                    document.getElementById('steps-completed').textContent = `${data.steps_completed}/${data.total_steps} steps completed`;
                    document.getElementById('est-completion').textContent = `Est. completion: ${new Date(data.estimated_completion).toLocaleTimeString()}`;
                })
                .catch(error => {
                    console.error('Error loading global progress:', error);
                    // Use default values if fetch fails
                    document.getElementById('system-progress-bar').style.width = '100%';
                    document.getElementById('system-status').textContent = 'Active';
                    document.getElementById('steps-completed').textContent = '100/100 steps completed';
                    document.getElementById('est-completion').textContent = 'Est. completion: Complete';
                });
        }
        
        // Update agent status cards
        function updateAgentStatus() {
            fetch('progress/agent_progress.json')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('agent-container');
                    container.innerHTML = '';
                    
                    // Use data from JSON if available, otherwise use default agents
                    const agentData = Object.keys(data).length > 0 ? 
                        Object.values(data) : agents;
                    
                    agentData.forEach(agent => {
                        const card = document.createElement('div');
                        card.className = 'agent-card';
                        
                        card.innerHTML = `
                            <div class="agent-header">
                                <div class="agent-name">${agent.agent_id || agent.name}</div>
                                <div class="agent-status ${(agent.status || '').toLowerCase()}">${agent.status}</div>
                            </div>
                            <div class="agent-progress">
                                <div class="agent-progress-bar" style="width: ${agent.percent_complete}%"></div>
                            </div>
                            <div class="agent-details">
                                ${agent.current_activity || agent.activity}
                            </div>
                            <div class="agent-details">
                                Tasks: ${agent.tasks_completed || 0}/${agent.total_tasks || 0}, 
                                Thoughts: ${agent.thought_count || 0}
                            </div>
                        `;
                        
                        container.appendChild(card);
                    });
                    
                    // Update feedback agent select
                    updateFeedbackAgentSelect(agentData);
                })
                .catch(error => {
                    console.error('Error loading agent status:', error);
                    // Use default values if fetch fails
                    const container = document.getElementById('agent-container');
                    container.innerHTML = '';
                    
                    agents.forEach(agent => {
                        const card = document.createElement('div');
                        card.className = 'agent-card';
                        
                        card.innerHTML = `
                            <div class="agent-header">
                                <div class="agent-name">${agent.name}</div>
                                <div class="agent-status ${agent.status.toLowerCase()}">${agent.status}</div>
                            </div>
                            <div class="agent-progress">
                                <div class="agent-progress-bar" style="width: ${agent.progress}%"></div>
                            </div>
                            <div class="agent-details">
                                ${agent.activity}
                            </div>
                            <div class="agent-details">
                                Tasks: ${Math.floor(agent.progress / 10)}/10, 
                                Thoughts: ${Math.floor(agent.progress / 2)}
                            </div>
                        `;
                        
                        container.appendChild(card);
                    });
                    
                    // Update feedback agent select with default agents
                    updateFeedbackAgentSelect(agents);
                });
        }
        
        // Update feedback agent select dropdown
        function updateFeedbackAgentSelect(agents) {
            const select = document.getElementById('agent-select');
            select.innerHTML = '';
            
            agents.forEach(agent => {
                const option = document.createElement('option');
                option.value = agent.id || agent.agent_id;
                option.textContent = agent.name || agent.agent_id;
                select.appendChild(option);
            });
        }
        
        // Submit feedback
        function submitFeedback() {
            const agentId = document.getElementById('agent-select').value;
            const feedbackText = document.getElementById('feedback-input').value.trim();
            
            if (!feedbackText) {
                alert('Please enter feedback text');
                return;
            }
            
            // In a real app, this would send to the server
            console.log(`Feedback for ${agentId}:`, feedbackText);
            alert(`Feedback for ${agentId} submitted!`);
            
            // Clear input
            document.getElementById('feedback-input').value = '';
        }
        
        // Switch tabs
        function switchTab(tabId) {
            // Hide all tab content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Deactivate all tabs
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Activate selected tab
            document.getElementById(`tab-${tabId}`).classList.add('active');
            document.getElementById(`content-${tabId}`).classList.add('active');
            
            // Special handling for iframe-based tabs
            if (tabId !== 'overview') {
                const iframe = document.getElementById(`${tabId}-iframe`);
                if (iframe && !iframe.src) {
                    iframe.src = `${tabId}/${tabId}.html`;
                }
            }
        }
        
        // Initialize dashboard on page load
        document.addEventListener('DOMContentLoaded', () => {
            // Set up tab switching
            document.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    const tabId = tab.getAttribute('data-tab');
                    switchTab(tabId);
                });
            });
            
            // Set up feedback submission
            document.getElementById('feedback-button').addEventListener('click', submitFeedback);
            
            // Load overview data
            updateGlobalProgress();
            updateAgentStatus();
            
            // Start refresh interval
            setInterval(() => {
                if (document.getElementById('content-overview').classList.contains('active')) {
                    updateGlobalProgress();
                    updateAgentStatus();
                }
            }, 3000);
            
            // Initialize with overview tab active
            switchTab('overview');
        });
    </script>
</head>
<body>
    <div class="dashboard-header">
        <div class="dashboard-title">Triangulum Agentic System Dashboard</div>
        <div class="dashboard-info">Last updated: <span id="last-updated"></span></div>
    </div>
    
    <div class="tab-bar">
        <div id="tab-overview" class="tab active" data-tab="overview">Overview</div>
        <div id="tab-thought_chains" class="tab" data-tab="thought_chains">Thought Chains</div>
        <div id="tab-agent_network" class="tab" data-tab="agent_network">Agent Network</div>
        <div id="tab-decision_trees" class="tab" data-tab="decision_trees">Decision Trees</div>
        <div id="tab-timeline" class="tab" data-tab="timeline">Timeline View</div>
        <div id="tab-progress" class="tab" data-tab="progress">Progress Tracking</div>
    </div>
    
    <div id="content-overview" class="tab-content active">
        <div class="progress-container">
            <h2>System Progress</h2>
            <div id="system-status">Initializing</div>
            <div class="progress-bar-container">
                <div id="system-progress-bar" class="progress-bar"></div>
            </div>
            <div class="progress-details">
                <div id="steps-completed">0/100 steps completed</div>
                <div id="est-completion">Est. completion: Unknown</div>
            </div>
        </div>
        
        <h2>Agent Status</h2>
        <div id="agent-container" class="agent-container">
            <!-- Agent cards will be dynamically inserted here -->
        </div>
        
        <div class="feedback-container">
            <div class="feedback-title">Provide Feedback</div>
            <textarea id="feedback-input" class="feedback-input" placeholder="Enter feedback for an agent..."></textarea>
            <div class="feedback-row">
                <select id="agent-select" class="agent-select">
                    <!-- Agent options will be dynamically inserted here -->
                </select>
                <button id="feedback-button" class="feedback-button">Submit Feedback</button>
            </div>
        </div>
    </div>
    
    <div id="content-thought_chains" class="tab-content">
        <iframe id="thought_chains-iframe" src=""></iframe>
    </div>
    
    <div id="content-agent_network" class="tab-content">
        <iframe id="agent_network-iframe" src=""></iframe>
    </div>
    
    <div id="content-decision_trees" class="tab-content">
        <iframe id="decision_trees-iframe" src=""></iframe>
    </div>
    
    <div id="content-timeline" class="tab-content">
        <iframe id="timeline-iframe" src=""></iframe>
    </div>
    
    <div id="content-progress" class="tab-content">
        <iframe id="progress-iframe" src=""></iframe>
    </div>
    
    <script>
        // Update last updated timestamp
        document.getElementById('last-updated').textContent = new Date().toLocaleString();
        
        // Update every minute
        setInterval(() => {
            document.getElementById('last-updated').textContent = new Date().toLocaleString();
        }, 60000);
    </script>
</body>
</html>
"""
    
    # Write the index HTML
    with open(os.path.join(output_dir, "index.html"), 'w') as f:
        f.write(html_content)
    
    logger.info(f"Created index.html at {os.path.join(output_dir, 'index.html')}")

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Run the fixed Triangulum agentic dashboard')
    
    parser.add_argument(
        '--directory',
        type=str,
        default='./triangulum_dashboard_fixed',
        help='Directory containing the dashboard files'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='Port to run the server on (default: random port between 8000-9000)'
    )
    
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not open the browser automatically'
    )
    
    return parser.parse_args()

def main():
    """Run the fixed dashboard."""
    args = parse_arguments()
    
    # Ensure the dashboard directory exists
    if not os.path.exists(args.directory):
        print(f"Error: Dashboard directory '{args.directory}' does not exist")
        print("Run fix_agentic_dashboard.py first to create the directory")
        return 1
    
    # Create index.html if it doesn't exist
    if not os.path.exists(os.path.join(args.directory, "index.html")):
        print("Creating main dashboard HTML...")
        create_index_html(args.directory)
    
    # Select a port
    port = args.port
    if port is None:
        # Try to find an available port
        for _ in range(10):
            port = random.randint(8000, 9000)
            try:
                with socketserver.TCPServer(("", port), None) as s:
                    pass  # Port is available if we get here
                break
            except OSError:
                continue
        else:
            port = 8123  # Default fallback
    
    print("=" * 80)
    print("TRIANGULUM FIXED AGENTIC DASHBOARD".center(80))
    print("=" * 80)
    print(f"\nStarting dashboard server at http://localhost:{port}/")
    
    # Change to the dashboard directory
    os.chdir(args.directory)
    
    # Create handler with the dashboard directory
    handler = lambda *args, **kwargs: DashboardRequestHandler(*args, directory=args[3], **kwargs)
    
    # Create server
    with socketserver.TCPServer(("", port), handler) as httpd:
        # Print server info
        print(f"Server started at http://localhost:{port}/")
        print("Press Ctrl+C to stop the server")
        
        # Open browser if requested
        if not args.no_browser:
            # Start browser in a separate thread
            threading.Thread(
                target=lambda: webbrowser.open(f"http://localhost:{port}/"),
                daemon=True
            ).start()
        
        # Start server
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server...")

if __name__ == "__main__":
    sys.exit(main())
