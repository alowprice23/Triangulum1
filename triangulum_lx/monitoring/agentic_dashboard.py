#!/usr/bin/env python3
"""
Agentic Dashboard

This module provides a unified dashboard for monitoring and visualizing
the Triangulum agentic system, including thought chains, agent communication,
progress indicators, and real-time activity tracking.
"""

import logging
import datetime
import json
import os
import time
import threading
import webbrowser
import random
from typing import Dict, List, Any, Optional, Union, Callable
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
import socket

# Import visualizers
from triangulum_lx.monitoring.thought_chain_visualizer import ThoughtChainVisualizer
from triangulum_lx.monitoring.agent_network_visualizer import AgentNetworkVisualizer
from triangulum_lx.monitoring.decision_tree_visualizer import DecisionTreeVisualizer
from triangulum_lx.monitoring.feedback_handler import FeedbackHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from triangulum_lx.tooling.fs_ops import atomic_write
from triangulum_lx.core.fs_state import FileSystemStateCache
from pathlib import Path # For easier path manipulation

class DashboardHandler(SimpleHTTPRequestHandler):
    """Custom handler for the dashboard HTTP server."""
    
    def __init__(self, *args, dashboard_root=None, **kwargs):
        self.dashboard_root = dashboard_root
        super().__init__(*args, **kwargs)
    
    def translate_path(self, path):
        """Translate URL paths to filesystem paths."""
        if self.dashboard_root:
            # Remove query parameters if any
            path = path.split('?', 1)[0]
            path = path.split('#', 1)[0]
            
            # Normalize path
            path = path.strip('/')
            
            # Serve from dashboard root
            if not path:
                return os.path.join(self.dashboard_root, "index.html")
            return os.path.join(self.dashboard_root, path)
        else:
            return super().translate_path(path)

class AgenticDashboard:
    """
    Unified dashboard for monitoring and visualizing the Triangulum agentic system.
    Integrates thought chain visualization, agent network visualization, progress
    tracking, and real-time activity monitoring.
    """
    
    def __init__(self, 
                 output_dir: str = "./agentic_dashboard",
                 update_interval: float = 0.5,
                 enable_server: bool = True,
                 server_port: int = 8080,
                 auto_open_browser: bool = True,
                 fs_cache: Optional[FileSystemStateCache] = None):
        """
        Initialize the agentic dashboard.
        
        Args:
            output_dir: Directory to store dashboard outputs
            update_interval: How frequently to update visualizations (seconds)
            enable_server: Whether to start an HTTP server for the dashboard
            server_port: Port to use for the HTTP server
            auto_open_browser: Whether to automatically open a browser window
            fs_cache: Optional FileSystemStateCache instance.
        """
        self.output_dir = output_dir
        self.update_interval = update_interval
        self.enable_server = enable_server
        self.server_port = server_port
        self.auto_open_browser = auto_open_browser
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()

        # Create visualization directories
        # Using Path().mkdir for consistency, direct ops for setup are okay.
        # Invalidate cache after ensuring directories exist.
        dirs_to_create = [
            Path(output_dir),
            Path(output_dir) / "thought_chains",
            Path(output_dir) / "agent_network",
            Path(output_dir) / "progress",
            Path(output_dir) / "data",
            Path(output_dir) / "decision_trees",
            Path(output_dir) / "timeline"
        ]
        for d in dirs_to_create:
            if not self.fs_cache.exists(str(d)): # Check before creating
                d.mkdir(parents=True, exist_ok=True)
                self.fs_cache.invalidate(str(d))
            elif not self.fs_cache.is_dir(str(d)): # Path exists but isn't a dir
                logger.warning(f"Path {d} for dashboard exists but is not a directory. Attempting to ensure it's a directory.")
                d.mkdir(parents=True, exist_ok=True) # This might fail if 'd' is a file
                self.fs_cache.invalidate(str(d))

        # Initialize visualizers, passing the cache
        self.thought_chain_visualizer = ThoughtChainVisualizer(
            output_dir=os.path.join(output_dir, "thought_chains"),
            update_interval=update_interval,
            enable_terminal_output=False,
            fs_cache=self.fs_cache
        )
        
        self.agent_network_visualizer = AgentNetworkVisualizer(
            output_dir=os.path.join(output_dir, "agent_network"),
            update_interval=update_interval,
            fs_cache=self.fs_cache
        )
        
        self.decision_tree_visualizer = DecisionTreeVisualizer(
            output_dir=os.path.join(output_dir, "decision_trees"),
            update_interval=update_interval,
            fs_cache=self.fs_cache
        )
        
        # Initialize feedback handler
        self.feedback_handler = FeedbackHandler(agent_manager=self)  # Pass self as agent_manager
        
        # Create decision trees directory
        os.makedirs(os.path.join(output_dir, "decision_trees"), exist_ok=True)
        
        # Initialize progress tracking
        self.agent_progress = {}  # agent_id -> progress info
        self.global_progress = {
            "percent_complete": 0.0,
            "status": "Initializing",
            "start_time": datetime.datetime.now().isoformat(),
            "estimated_completion": None,
            "steps_completed": 0,
            "total_steps": 0
        }
        
        # Initialize activity tracking
        self.agent_activity = {}  # agent_id -> activity info
        self.last_update = time.time()
        self.server = None
        self.server_thread = None
        
        # Use templates directory
        self.templates_dir = Path(os.path.dirname(__file__)) / "templates"
        if not self.fs_cache.exists(str(self.templates_dir)): # Check before creating
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            self.fs_cache.invalidate(str(self.templates_dir))
        elif not self.fs_cache.is_dir(str(self.templates_dir)):
            logger.warning(f"Templates dir {self.templates_dir} path exists but is not a directory. Attempting mkdir.")
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            self.fs_cache.invalidate(str(self.templates_dir))


        # Check if a pre-built dashboard exists in output_dir
        index_html_path_str = os.path.join(self.output_dir, "index.html")
        pre_built_dashboard_exists = self.fs_cache.exists(index_html_path_str)
        if not pre_built_dashboard_exists and Path(index_html_path_str).exists(): # Cache stale
            logger.warning(f"Cache miss for existing index.html {index_html_path_str}. Invalidating.")
            self.fs_cache.invalidate(index_html_path_str)
            pre_built_dashboard_exists = True


        if not pre_built_dashboard_exists:
            logger.info(f"No pre-built index.html found in {self.output_dir}. Generating from templates.")
            # Copy template files to output directories
            self._copy_template_files()
            # Create the main dashboard HTML
            self._create_main_dashboard()
        else:
            logger.info(f"Using existing index.html and structure in {self.output_dir}.")
            # Ensure necessary data subdirectories exist even if we don't copy templates
            # These were already handled by the loop at the start of __init__
            pass
        
        # Start HTTP server if enabled
        if self.enable_server:
            self._start_server()
        
        logger.info(f"Agentic Dashboard initialized with output_dir={self.output_dir}")
    
    def _copy_template_files(self):
        """Copy template files to output directories."""
        try:
            # Copy thought chains template
            thought_chains_src = os.path.join(self.templates_dir, "thought_chains.html")
            thought_chains_dest = os.path.join(self.output_dir, "thought_chains", "thought_chains.html")
            
            if self.fs_cache.exists(str(thought_chains_src)): # Use cache for source existence
                # Direct read for content
                with open(thought_chains_src, 'r', encoding='utf-8') as f:
                    content = f.read()
                atomic_write(str(thought_chains_dest), content.encode('utf-8'))
                self.fs_cache.invalidate(str(thought_chains_dest))
            elif Path(thought_chains_src).exists(): # Cache stale
                logger.warning(f"Cache miss for existing template {thought_chains_src}. Invalidating and copying.")
                self.fs_cache.invalidate(str(thought_chains_src))
                with open(thought_chains_src, 'r', encoding='utf-8') as f:
                    content = f.read()
                atomic_write(str(thought_chains_dest), content.encode('utf-8'))
                self.fs_cache.invalidate(str(thought_chains_dest))

            # Copy agent network template
            agent_network_src = Path(self.templates_dir) / "agent_network.html"
            agent_network_dest = Path(self.output_dir) / "agent_network" / "agent_network.html"
            
            if self.fs_cache.exists(str(agent_network_src)):
                with open(agent_network_src, 'r', encoding='utf-8') as f:
                    content = f.read()
                atomic_write(str(agent_network_dest), content.encode('utf-8'))
                self.fs_cache.invalidate(str(agent_network_dest))
            elif Path(agent_network_src).exists(): # Cache stale
                logger.warning(f"Cache miss for existing template {agent_network_src}. Invalidating and copying.")
                self.fs_cache.invalidate(str(agent_network_src))
                with open(agent_network_src, 'r', encoding='utf-8') as f:
                    content = f.read()
                atomic_write(str(agent_network_dest), content.encode('utf-8'))
                self.fs_cache.invalidate(str(agent_network_dest))

            # Copy decision trees template
            decision_trees_src = Path(self.templates_dir) / "decision_trees.html"
            decision_trees_dest = Path(self.output_dir) / "decision_trees" / "decision_trees.html"
            
            if self.fs_cache.exists(str(decision_trees_src)):
                with open(decision_trees_src, 'r', encoding='utf-8') as f:
                    content = f.read()
                atomic_write(str(decision_trees_dest), content.encode('utf-8'))
                self.fs_cache.invalidate(str(decision_trees_dest))
            elif Path(decision_trees_src).exists(): # Cache stale
                logger.warning(f"Cache miss for existing template {decision_trees_src}. Invalidating and copying.")
                self.fs_cache.invalidate(str(decision_trees_src))
                with open(decision_trees_src, 'r', encoding='utf-8') as f:
                    content = f.read()
                atomic_write(str(decision_trees_dest), content.encode('utf-8'))
                self.fs_cache.invalidate(str(decision_trees_dest))
            
            # Copy timeline template
            timeline_src = Path(self.templates_dir) / "timeline.html"
            timeline_dest = Path(self.output_dir) / "timeline" / "timeline.html"
            
            if self.fs_cache.exists(str(timeline_src)):
                with open(timeline_src, 'r', encoding='utf-8') as f:
                    content = f.read()
                atomic_write(str(timeline_dest), content.encode('utf-8'))
                self.fs_cache.invalidate(str(timeline_dest))
            elif Path(timeline_src).exists(): # Cache stale
                logger.warning(f"Cache miss for existing template {timeline_src}. Invalidating and copying.")
                self.fs_cache.invalidate(str(timeline_src))
                with open(timeline_src, 'r', encoding='utf-8') as f:
                    content = f.read()
                atomic_write(str(timeline_dest), content.encode('utf-8'))
                self.fs_cache.invalidate(str(timeline_dest))
            
            logger.info("Dashboard templates copied to output directories")
        
        except Exception as e:
            logger.error(f"Error copying template files: {e}")
    
    def _create_main_dashboard(self):
        """Create the main dashboard HTML file and its template."""
        template = """<!DOCTYPE html>
<html>
<head>
    <title>Triangulum Agentic System Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f0f2f5;
        }
        .dashboard-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            max-width: 1800px;
            margin: 0 auto;
            padding: 20px;
        }
        .dashboard-header {
            grid-column: 1 / -1;
        }
        .dashboard-nav {
            grid-column: 1 / -1;
        }
        .main-content {
            grid-column: 1 / -1;
        }
        .thought-chain-container {
            grid-column: 1 / 2;
        }
        .agent-network-container {
            grid-column: 2 / 3;
        }
        .dashboard-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            background-color: #001529;
            padding: 15px 20px;
            border-radius: 6px;
            color: white;
        }
        .dashboard-title {
            font-size: 24px;
            font-weight: bold;
        }
        .dashboard-timestamp {
            font-size: 14px;
            color: #d9d9d9;
        }
        .dashboard-nav {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            background-color: white;
            padding: 10px;
            border-radius: 6px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        .nav-item {
            padding: 8px 16px;
            cursor: pointer;
            border-radius: 4px;
            transition: background-color 0.3s;
        }
        .nav-item:hover, .nav-item.active {
            background-color: #e6f7ff;
            color: #1890ff;
        }
        .dashboard-section {
            margin-bottom: 20px;
            background-color: white;
            padding: 20px;
            border-radius: 6px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #f0f0f0;
        }
        .section-title {
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }
        .section-action {
            display: none;
        }
        .global-progress {
            margin-bottom: 20px;
        }
        .progress-bar-container {
            width: 100%;
            height: 10px;
            background-color: #f5f5f5;
            border-radius: 5px;
            overflow: hidden;
            margin-bottom: 10px;
        }
        .progress-bar {
            height: 100%;
            background-color: #1890ff;
            transition: width 0.3s ease;
        }
        .thought-chain {
            display: flex;
            flex-direction: column-reverse;
        }
        .progress-stats {
            display: flex;
            justify-content: space-between;
            font-size: 14px;
            color: #666;
        }
        .agent-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
        }
        .agent-card {
            background-color: white;
            border-radius: 6px;
            padding: 15px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            border: 1px solid #f0f0f0;
        }
        .agent-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .agent-name {
            font-size: 16px;
            font-weight: bold;
            color: #333;
        }
        .agent-status {
            font-size: 12px;
            padding: 2px 8px;
            border-radius: 10px;
            background-color: #e6f7ff;
            color: #1890ff;
        }
        .agent-status.active {
            background-color: #f6ffed;
            color: #52c41a;
        }
        .agent-status.idle {
            background-color: #f5f5f5;
            color: #8c8c8c;
        }
        .agent-status.error {
            background-color: #fff2f0;
            color: #f5222d;
        }
        .agent-progress {
            margin-top: 10px;
        }
        .agent-activity {
            margin-top: 10px;
            font-size: 14px;
            color: #666;
        }
        .agent-stats {
            display: flex;
            gap: 10px;
            margin-top: 10px;
            font-size: 12px;
            color: #8c8c8c;
        }
        .iframe-container {
            width: 100%;
            height: 800px;
            border: none;
            margin-top: 20px;
        }
        iframe {
            width: 100%;
            height: 100%;
            border: none;
        }
        .tab-container {
            display: none;
        }
        .tab-container.active {
            display: block;
        }
        .timeline-container {
            position: relative;
            padding: 20px 0;
        }
        .timeline-event {
            position: relative;
            padding: 10px 20px;
            margin-left: 30px;
            border-left: 2px solid #e8e8e8;
        }
        .timeline-event:before {
            content: '';
            position: absolute;
            left: -8px;
            top: 10px;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background-color: #1890ff;
            border: 2px solid white;
        }
        .timeline-event-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
        }
        .timeline-agent {
            font-weight: bold;
            color: #333;
        }
        .timeline-timestamp {
            font-size: 12px;
            color: #999;
        }
        .timeline-content {
            font-size: 14px;
            color: #666;
        }
        .feedback-form {
            margin-top: 20px;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 6px;
        }
        .feedback-form textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            resize: vertical;
        }
        .feedback-form button {
            margin-top: 10px;
            padding: 8px 16px;
            background-color: #1890ff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .feedback-form button:hover {
            background-color: #40a9ff;
        }
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="dashboard-header">
            <div class="dashboard-title">Triangulum Agentic System Dashboard</div>
            <div class="dashboard-timestamp">Last updated: <span id="update-time">{{last_updated}}</span></div>
        </div>
        
        <div class="dashboard-nav">
            <div class="nav-item active" data-tab="overview">Overview</div>
            <div class="nav-item" data-tab="thought-chains">Thought Chains</div>
            <div class="nav-item" data-tab="agent-network">Agent Network</div>
            <div class="nav-item" data-tab="decision-trees">Decision Trees</div>
            <div class="nav-item" data-tab="timeline">Timeline View</div>
            <div class="nav-item" data-tab="progress">Progress Tracking</div>
        </div>
        
        <div id="overview" class="tab-container active">
            <div class="dashboard-section global-progress">
                <div class="section-header">
                    <div class="section-title">System Progress</div>
                    <div class="section-action" id="refresh-progress">Refresh</div>
                </div>
                
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: {{global_progress_percent}}%"></div>
                </div>
                
                <div class="progress-stats">
                    <div>Status: {{global_status}}</div>
                    <div>{{steps_completed}} / {{total_steps}} steps completed</div>
                    <div>Est. completion: {{estimated_completion}}</div>
                </div>
            </div>
            
            <div class="dashboard-section">
                <div class="section-header">
                    <div class="section-title">Agent Status</div>
                    <div class="section-action" id="refresh-agents">Refresh</div>
                </div>
                
                <div class="agent-grid">
                    {{agent_cards}}
                </div>
                
                <div class="feedback-form">
                    <h3>Provide Feedback</h3>
                    <textarea id="feedback-text" rows="3" placeholder="Enter feedback for an agent..."></textarea>
                    <select id="feedback-agent-select">
                        {{agent_options}}
                    </select>
                    <button onclick="submitFeedback()">Submit Feedback</button>
                </div>
            </div>
        </div>
        
        <div id="thought-chains" class="tab-container">
            <div class="dashboard-section">
                <div class="section-header">
                    <div class="section-title">Thought Chain Visualization</div>
                    <div class="section-action" id="refresh-thoughts">Refresh</div>
                </div>
                
                <iframe src="thought_chains/thought_chains.html" class="iframe-container"></iframe>
            </div>
        </div>
        
        <div id="agent-network" class="tab-container">
            <div class="dashboard-section">
                <div class="section-header">
                    <div class="section-title">Agent Communication Network</div>
                    <div class="section-action" id="refresh-network">Refresh</div>
                </div>
                
                <iframe src="agent_network/agent_network.html" class="iframe-container"></iframe>
            </div>
        </div>
        
        <div id="decision-trees" class="tab-container">
            <div class="dashboard-section">
                <div class="section-header">
                    <div class="section-title">Agent Decision Trees</div>
                    <div class="section-action" id="refresh-trees">Refresh</div>
                </div>
                
                <iframe src="decision_trees/decision_trees.html" class="iframe-container"></iframe>
            </div>
        </div>
        
        <div id="progress" class="tab-container">
            <div class="dashboard-section">
                <div class="section-header">
                    <div class="section-title">Detailed Progress Tracking</div>
                    <div class="section-action" id="refresh-detailed">Refresh</div>
                </div>
                
                <div id="detailed-progress">
                    {{detailed_progress}}
                </div>
            </div>
        </div>
        
        <div id="timeline" class="tab-container">
            <div class="dashboard-section">
                <div class="section-header">
                    <div class="section-title">Agent Reasoning Timeline</div>
                    <div class="section-action" id="refresh-timeline">Refresh</div>
                </div>
                
                <div class="timeline-container">
                    {{timeline_events}}
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Tab switching
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                // Remove active class from all tabs and containers
                document.querySelectorAll('.nav-item').forEach(navItem => {
                    navItem.classList.remove('active');
                });
                document.querySelectorAll('.tab-container').forEach(container => {
                    container.classList.remove('active');
                });
                
                // Add active class to clicked tab and corresponding container
                item.classList.add('active');
                const tabId = item.getAttribute('data-tab');
                document.getElementById(tabId).classList.add('active');
            });
        });
        
        function submitFeedback() {
            const agentId = document.getElementById('feedback-agent-select').value;
            const feedbackText = document.getElementById('feedback-text').value;
            
            if (!agentId || !feedbackText) {
                alert("Please select an agent and enter feedback.");
                return;
            }
            
            // Send feedback to the backend (this part requires a proper API endpoint)
            // For now, we'll just log it to the console.
            console.log(`Submitting feedback for ${agentId}: ${feedbackText}`);
            
            // In a real application, you would use fetch() to send this to a server endpoint
            // that calls the feedback_handler.submit_feedback() method.
            
            alert("Feedback submitted (logged to console).");
            document.getElementById('feedback-text').value = '';
        }
    </script>
</body>
</html>
"""
        
        # Save the template file
        template_path = Path(self.templates_dir) / "dashboard.html"
        # Ensure parent dir for template_path (self.templates_dir) exists
        self.templates_dir.mkdir(parents=True, exist_ok=True) # Direct mkdir for setup
        self.fs_cache.invalidate(str(self.templates_dir))

        atomic_write(str(template_path), template.encode('utf-8'))
        self.fs_cache.invalidate(str(template_path))

        # Generate the initial dashboard with placeholder data
        html = self._generate_dashboard_html(template)
        
        # Write HTML file
        output_path = Path(self.output_dir) / "index.html"
        # Parent self.output_dir should exist from __init__
        atomic_write(str(output_path), html.encode('utf-8'))
        self.fs_cache.invalidate(str(output_path))
        
        logger.info(f"Main dashboard HTML created at {output_path} using atomic_write")
    
    def _generate_dashboard_html(self, template):
        """Generate the dashboard HTML with current data."""
        # Calculate global progress percent
        global_percent = self.global_progress["percent_complete"]
        global_status = self.global_progress["status"]
        steps_completed = self.global_progress["steps_completed"]
        total_steps = self.global_progress["total_steps"]
        
        # Format estimated completion time
        estimated_completion = "Unknown"
        if self.global_progress["estimated_completion"]:
            try:
                est_time = datetime.datetime.fromisoformat(self.global_progress["estimated_completion"])
                estimated_completion = est_time.strftime("%H:%M:%S")
            except (ValueError, TypeError):
                estimated_completion = "Unknown"
        
        # Generate agent cards and options for feedback form
        agent_cards = ""
        agent_options = ""
        for agent_id, progress in self.agent_progress.items():
            agent_options += f'<option value="{agent_id}">{agent_id}</option>'
            status_class = "idle"
            if progress.get("status", "").lower() == "active":
                status_class = "active"
            elif progress.get("status", "").lower() == "error":
                status_class = "error"
            
            percent = progress.get("percent_complete", 0)
            activity = progress.get("current_activity", "No activity")
            
            agent_cards += f"""
            <div class="agent-card">
                <div class="agent-header">
                    <div class="agent-name">{agent_id}</div>
                    <div class="agent-status {status_class}">{progress.get("status", "Unknown")}</div>
                </div>
                
                <div class="agent-progress">
                    <div class="progress-bar-container">
                        <div class="progress-bar" style="width: {percent}%"></div>
                    </div>
                </div>
                
                <div class="agent-activity">{activity}</div>
                
                <div class="agent-stats">
                    <div>Tasks: {progress.get("tasks_completed", 0)}/{progress.get("total_tasks", 0)}</div>
                    <div>Thoughts: {progress.get("thought_count", 0)}</div>
                </div>
            </div>
            """
        
        # Generate detailed progress HTML
        detailed_progress = "<ul>"
        if isinstance(self.agent_activity, dict):
            for agent_id, activity in self.agent_activity.items():
                detailed_progress += f"<li><strong>{agent_id}</strong>: {activity.get('description', 'No activity')}</li>"
        detailed_progress += "</ul>"
        
        # Generate timeline events HTML
        timeline_events = ""
        all_events = []
        
        # Collect all thoughts and messages
        try:
            if hasattr(self.thought_chain_visualizer, 'thought_chains'):
                for chain_id, chain in self.thought_chain_visualizer.thought_chains.items():
                    if isinstance(chain, dict) and "thoughts" in chain and isinstance(chain["thoughts"], list):
                        for thought in chain["thoughts"]:
                            if isinstance(thought, dict):
                                all_events.append({
                                    "type": "thought",
                                    "timestamp": thought.get("timestamp", "Unknown"),
                                    "agent_id": thought.get("agent_id", "Unknown"),
                                    "content": f"Thought ({thought.get('thought_type', 'Unknown')}): {thought.get('content', 'No content')}"
                                })
        except Exception as e:
            logger.error(f"Error processing thought chains: {e}")
        
        try:
            if hasattr(self.agent_network_visualizer, 'messages'):
                if isinstance(self.agent_network_visualizer.messages, list):
                    for message in self.agent_network_visualizer.messages:
                        if isinstance(message, dict):
                            all_events.append({
                                "type": "message",
                                "timestamp": message.get("timestamp", "Unknown"),
                                "agent_id": message.get("source_agent", "Unknown"),
                                "content": f"Message to {message.get('target_agent', 'Unknown')} ({message.get('message_type', 'Unknown')}): {message.get('content', '')}"
                            })
        except Exception as e:
            logger.error(f"Error processing messages: {e}")
        
        try:
            # Sort events by timestamp - with type checking
            all_events.sort(key=lambda x: x.get("timestamp", "") if isinstance(x, dict) else "")
            
            # Create timeline HTML
            for event in all_events:
                if not isinstance(event, dict):
                    continue
                
                try:
                    timestamp = datetime.datetime.fromisoformat(event.get("timestamp", "")).strftime("%H:%M:%S")
                except (ValueError, TypeError, AttributeError):
                    timestamp = "Unknown"
                
                timeline_events += f"""
                <div class="timeline-event">
                    <div class="timeline-event-header">
                        <div class="timeline-agent">{event.get('agent_id', 'Unknown')}</div>
                        <div class="timeline-timestamp">{timestamp}</div>
                    </div>
                    <div class="timeline-content">{event.get('content', 'No content')}</div>
                </div>
                """
        except Exception as e:
            logger.error(f"Error sorting timeline events: {e}")
        
        # Replace template placeholders
        html = template.replace("{{global_progress_percent}}", str(global_percent))
        html = html.replace("{{global_status}}", global_status)
        html = html.replace("{{steps_completed}}", str(steps_completed))
        html = html.replace("{{total_steps}}", str(total_steps))
        html = html.replace("{{estimated_completion}}", estimated_completion)
        html = html.replace("{{agent_cards}}", agent_cards)
        html = html.replace("{{agent_options}}", agent_options)
        html = html.replace("{{detailed_progress}}", detailed_progress)
        html = html.replace("{{timeline_events}}", timeline_events)
        html = html.replace("{{last_updated}}", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return html
    
    def _find_available_port(self, start_port=8080, max_attempts=100):
        """Find an available port starting from start_port."""
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('localhost', port))
                    return port
                except socket.error:
                    continue
        return None
    
    def _start_server(self):
        """Start the HTTP server for the dashboard."""
        try:
            # Find an available port
            port = self._find_available_port(self.server_port)
            if not port:
                logger.warning(f"Could not find an available port. Dashboard server not started.")
                return
            
            # Create handler class with dashboard root
            handler = lambda *args, **kwargs: DashboardHandler(*args, dashboard_root=self.output_dir, **kwargs)
            
            # Create server
            self.server = socketserver.TCPServer(("", port), handler)
            
            # Start server in a separate thread
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            logger.info(f"Dashboard server started at http://localhost:{port}/")
            
            # Open browser if enabled
            if self.auto_open_browser:
                webbrowser.open(f"http://localhost:{port}/")
        
        except Exception as e:
            logger.error(f"Error starting dashboard server: {e}")
    
    def update_agent_progress(self, 
                             agent_id: str, 
                             percent_complete: float,
                             status: str = "Active",
                             current_activity: Optional[str] = None,
                             tasks_completed: Optional[int] = None,
                             total_tasks: Optional[int] = None,
                             thought_count: Optional[int] = None):
        """
        Update progress information for an agent.
        
        Args:
            agent_id: ID of the agent to update
            percent_complete: Percentage of completion (0-100)
            status: Current status (Active, Idle, Error, etc.)
            current_activity: Description of current activity
            tasks_completed: Number of tasks completed
            total_tasks: Total number of tasks
            thought_count: Number of thoughts generated
        """
        # Initialize agent progress if needed
        if agent_id not in self.agent_progress:
            self.agent_progress[agent_id] = {
                "percent_complete": 0.0,
                "status": "Idle",
                "current_activity": None,
                "last_update": datetime.datetime.now().isoformat(),
                "tasks_completed": 0,
                "total_tasks": 0,
                "thought_count": 0
            }
        
        # Update progress
        progress = self.agent_progress[agent_id]
        progress["percent_complete"] = percent_complete
        progress["status"] = status
        progress["last_update"] = datetime.datetime.now().isoformat()
        
        if current_activity is not None:
            progress["current_activity"] = current_activity
        
        if tasks_completed is not None:
            progress["tasks_completed"] = tasks_completed
        
        if total_tasks is not None:
            progress["total_tasks"] = total_tasks
        
        if thought_count is not None:
            progress["thought_count"] = thought_count
        
        # Update activity tracking
        self.agent_activity[agent_id] = {
            "timestamp": datetime.datetime.now().isoformat(),
            "description": current_activity or progress["current_activity"] or "No activity",
            "percent_complete": percent_complete
        }
        
        # Update visualizations if needed
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.update_dashboard()
            self.last_update = current_time
    
    def update_global_progress(self,
                              percent_complete: float,
                              status: str = None,
                              steps_completed: Optional[int] = None,
                              total_steps: Optional[int] = None):
        """
        Update global progress information.
        
        Args:
            percent_complete: Overall percentage of completion (0-100)
            status: Current system status
            steps_completed: Number of steps completed
            total_steps: Total number of steps
        """
        self.global_progress["percent_complete"] = percent_complete
        
        if status is not None:
            self.global_progress["status"] = status
        
        if steps_completed is not None:
            self.global_progress["steps_completed"] = steps_completed
        
        if total_steps is not None:
            self.global_progress["total_steps"] = total_steps
        
        # Calculate estimated completion time
        if percent_complete > 0:
            start_time = datetime.datetime.fromisoformat(self.global_progress["start_time"])
            now = datetime.datetime.now()
            elapsed = (now - start_time).total_seconds()
            
            if percent_complete < 100:
                # Estimate completion time based on elapsed time and progress
                remaining = elapsed * (100 - percent_complete) / percent_complete
                est_completion = now + datetime.timedelta(seconds=remaining)
                self.global_progress["estimated_completion"] = est_completion.isoformat()
            else:
                self.global_progress["estimated_completion"] = now.isoformat()
        
        # Update visualizations if needed
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.update_dashboard()
            self.last_update = current_time
    
    def register_thought(self, 
                        agent_id: str, 
                        chain_id: str, 
                        content: str, 
                        thought_type: str = "analysis",
                        metadata: Optional[Dict] = None):
        """
        Register a thought to be visualized in the thought chain.
        
        Args:
            agent_id: ID of the agent that generated the thought
            chain_id: ID of the thought chain
            content: The thought content
            thought_type: Type of thought (analysis, decision, etc.)
            metadata: Additional metadata for the thought
        """
        # Register thought with the thought chain visualizer
        self.thought_chain_visualizer.register_thought(
            agent_id=agent_id,
            chain_id=chain_id,
            content=content,
            thought_type=thought_type,
            metadata=metadata
        )
        
        # Update agent progress - increment thought count
        if agent_id in self.agent_progress:
            thought_count = self.agent_progress[agent_id].get("thought_count", 0) + 1
            self.update_agent_progress(agent_id, 
                                      self.agent_progress[agent_id].get("percent_complete", 0),
                                      thought_count=thought_count)
        
        # Update visualizations if needed
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.update_dashboard()
            self.last_update = current_time
    
    def register_message(self, 
                        source_agent: str, 
                        target_agent: str, 
                        message_type: str, 
                        content: Optional[str] = None,
                        metadata: Optional[Dict] = None):
        """
        Register a message between agents to be visualized in the network.
        
        Args:
            source_agent: ID of the source agent
            target_agent: ID of the target agent
            message_type: Type of message (command, response, etc.)
            content: Optional message content
            metadata: Optional additional metadata
        """
        # Register message with the agent network visualizer
        self.agent_network_visualizer.register_message(
            source_agent=source_agent,
            target_agent=target_agent,
            message_type=message_type,
            content=content,
            metadata=metadata
        )
        
        # Update visualizations if needed
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.update_dashboard()
            self.last_update = current_time
    
    def create_decision_tree(self, 
                           agent_id: str, 
                           name: Optional[str] = None,
                           description: Optional[str] = None) -> str:
        """
        Create a new decision tree for an agent.
        
        Args:
            agent_id: ID of the agent that owns the tree
            name: Optional name for the tree
            description: Optional description of the tree
        
        Returns:
            tree_id: ID of the created tree
        """
        tree_id = self.decision_tree_visualizer.create_decision_tree(
            agent_id=agent_id,
            name=name,
            description=description
        )
        
        # Update visualizations if needed
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.update_dashboard()
            self.last_update = current_time
            
        return tree_id
    
    def add_decision_node(self, 
                         tree_id: str, 
                         parent_id: Optional[str], 
                         name: str,
                         node_type: str = "decision",
                         content: Optional[str] = None,
                         confidence: Optional[float] = None,
                         alternatives: Optional[List[Dict]] = None,
                         metadata: Optional[Dict] = None) -> str:
        """
        Add a decision node to a tree.
        
        Args:
            tree_id: ID of the tree to add the node to
            parent_id: ID of the parent node, or None for root
            name: Name/title of the node
            node_type: Type of node (decision, analysis, action, etc.)
            content: Detailed content/description of the node
            confidence: Confidence level (0-100) for this decision
            alternatives: List of alternative decisions that were not taken
            metadata: Additional metadata for the node
        
        Returns:
            node_id: ID of the created node
        """
        node_id = self.decision_tree_visualizer.add_decision_node(
            tree_id=tree_id,
            parent_id=parent_id,
            name=name,
            node_type=node_type,
            content=content,
            confidence=confidence,
            alternatives=alternatives,
            metadata=metadata
        )
        
        # Update visualizations if needed
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.update_dashboard()
            self.last_update = current_time
            
        return node_id
    
    def add_alternative(self, 
                       tree_id: str, 
                       node_id: str,
                       name: str,
                       content: Optional[str] = None,
                       confidence: Optional[float] = None,
                       metadata: Optional[Dict] = None):
        """
        Add an alternative to a decision node.
        
        Args:
            tree_id: ID of the tree
            node_id: ID of the node to add alternative to
            name: Name/title of the alternative
            content: Detailed content/description of the alternative
            confidence: Confidence level (0-100) for this alternative
            metadata: Additional metadata for the alternative
        """
        self.decision_tree_visualizer.add_alternative(
            tree_id=tree_id,
            node_id=node_id,
            name=name,
            content=content,
            confidence=confidence,
            metadata=metadata
        )
        
        # Update visualizations if needed
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.update_dashboard()
            self.last_update = current_time
    
    def update_dashboard(self):
        """Update all dashboard visualizations and data."""
        try:
            # Update individual visualizations
            self.thought_chain_visualizer.update_visualizations()
            self.agent_network_visualizer.update_visualizations()
            self.decision_tree_visualizer.update_visualizations()
            
            # Export JSON data for each visualization
            # Thought chains data
            try:
                if hasattr(self.thought_chain_visualizer, 'thought_chains'):
                    thought_chains_path = os.path.join(self.output_dir, "thought_chains", "thought_chains.json")
                    content_str = json.dumps(self.thought_chain_visualizer.thought_chains, indent=2)
                    atomic_write(thought_chains_path, content_str.encode('utf-8'))
                    self.fs_cache.invalidate(thought_chains_path)
            except Exception as e:
                logger.error(f"Error exporting thought chains data: {e}")
                
            # Agent network data
            try:
                if hasattr(self.agent_network_visualizer, 'messages'):
                    messages_path = os.path.join(self.output_dir, "agent_network", "messages.json")
                    content_str = json.dumps(self.agent_network_visualizer.messages, indent=2)
                    atomic_write(messages_path, content_str.encode('utf-8'))
                    self.fs_cache.invalidate(messages_path)
            except Exception as e:
                logger.error(f"Error exporting messages data: {e}")
                
            # Decision trees data
            try:
                if hasattr(self.decision_tree_visualizer, 'trees'):
                    trees_path = os.path.join(self.output_dir, "decision_trees", "decision_trees.json")
                    content_str = json.dumps(self.decision_tree_visualizer.trees, indent=2)
                    atomic_write(trees_path, content_str.encode('utf-8'))
                    self.fs_cache.invalidate(trees_path)
            except Exception as e:
                logger.error(f"Error exporting decision trees data: {e}")
                
            # Timeline events data
            try:
                all_events = []
                
                # Collect thoughts for timeline
                if hasattr(self.thought_chain_visualizer, 'thought_chains'):
                    for chain_id, chain in self.thought_chain_visualizer.thought_chains.items():
                        if isinstance(chain, dict) and "thoughts" in chain and isinstance(chain["thoughts"], list):
                            for thought in chain["thoughts"]:
                                if isinstance(thought, dict):
                                    all_events.append({
                                        "type": "thought",
                                        "timestamp": thought.get("timestamp", "Unknown"),
                                        "agent_id": thought.get("agent_id", "Unknown"),
                                        "content": f"Thought ({thought.get('thought_type', 'Unknown')}): {thought.get('content', 'No content')}"
                                    })
                
                # Collect messages for timeline
                if hasattr(self.agent_network_visualizer, 'messages'):
                    if isinstance(self.agent_network_visualizer.messages, list):
                        for message in self.agent_network_visualizer.messages:
                            if isinstance(message, dict):
                                all_events.append({
                                    "type": "message",
                                    "timestamp": message.get("timestamp", "Unknown"),
                                    "agent_id": message.get("source_agent", "Unknown"),
                                    "content": f"Message to {message.get('target_agent', 'Unknown')} ({message.get('message_type', 'Unknown')}): {message.get('content', '')}"
                                })
                
                # Sort events by timestamp
                all_events.sort(key=lambda x: x.get("timestamp", "") if isinstance(x, dict) else "")
                
                # Save timeline data
                timeline_path = os.path.join(self.output_dir, "timeline", "timeline_events.json")
                content_str = json.dumps(all_events, indent=2)
                atomic_write(timeline_path, content_str.encode('utf-8'))
                self.fs_cache.invalidate(timeline_path)
                    
            except Exception as e:
                logger.error(f"Error exporting timeline data: {e}")
            
            # Regenerate main dashboard
            template_path = Path(self.templates_dir) / "dashboard.html"
            # Check cache for template_path existence
            if not self.fs_cache.exists(str(template_path)):
                if not template_path.exists(): # Double check FS
                    logger.warning(f"Dashboard template {template_path} not found. Recreating.")
                    self._create_main_dashboard() # This will create and save it using atomic_write
                else: # Cache stale
                    self.fs_cache.invalidate(str(template_path))

            # Direct read for template content
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            html = self._generate_dashboard_html(template)
            
            # Write HTML file (index.html)
            index_output_path = os.path.join(self.output_dir, "index.html")
            atomic_write(index_output_path, html.encode('utf-8'))
            self.fs_cache.invalidate(index_output_path)
            
            # Save dashboard data as JSON for AJAX updates
            data = {
                "global_progress": self.global_progress,
                "agent_progress": self.agent_progress,
                "agent_activity": self.agent_activity,
                "last_updated": datetime.datetime.now().isoformat()
            }
            
            data_path = os.path.join(self.output_dir, "data", "dashboard_data.json")
            data_content_str = json.dumps(data, indent=2)
            atomic_write(data_path, data_content_str.encode('utf-8'))
            self.fs_cache.invalidate(data_path)
            
            logger.debug("Dashboard updated")
        
        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
    
    def save_dashboard_state(self, output_path: Optional[str] = None):
        """
        Save the current dashboard state to a JSON file.
        
        Args:
            output_path: Path to save the JSON file. If None, uses default path.
        """
        if output_path is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.output_dir, f"dashboard_state_{timestamp}.json")
        
        # Prepare data for serialization
        data = {
            "global_progress": self.global_progress,
            "agent_progress": self.agent_progress,
            "agent_activity": self.agent_activity,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Save to file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True) # Ensure parent exists
        self.fs_cache.invalidate(str(Path(output_path).parent))

        content_str = json.dumps(data, indent=2)
        atomic_write(output_path, content_str.encode('utf-8'))
        self.fs_cache.invalidate(output_path)
        
        logger.info(f"Dashboard state saved to {output_path} using atomic_write")
        return output_path
    
    def stop(self):
        """Stop the dashboard server and save final state."""
        # Save final states
        self.thought_chain_visualizer.save_thought_chains()
        self.agent_network_visualizer.save_network_data()
        self.save_dashboard_state()
        
        # Stop server if running
        if self.server:
            self.server.shutdown()
            self.server_thread.join(timeout=1.0)
            logger.info("Dashboard server stopped")


# Demo usage when run directly
if __name__ == "__main__":
    # Create dashboard
    dashboard = AgenticDashboard(output_dir="./agentic_dashboard_demo")
    
    try:
        # Define agents
        agents = [
            "orchestrator",
            "bug_detector",
            "relationship_analyst",
            "verification",
            "priority_analyzer",
            "code_fixer"
        ]
        
        # Simulate agent activity
        print("Starting dashboard demo...")
        
        # Initialize global progress
        dashboard.update_global_progress(0.0, "Initializing", 0, 100)
        
        # Simulate agent progress over time
        for step in range(1, 101):
            time.sleep(0.1)  # Simulate work
            
            # Update global progress
            dashboard.update_global_progress(step, "Processing", step, 100)
            
            # Update random agent progress
            for agent_id in agents:
                agent_progress = min(100, step + random.randint(-10, 10))
                agent_progress = max(0, agent_progress)  # Ensure non-negative
                
                status = "Active" if random.random() > 0.3 else "Idle"
                activity = f"Processing task {random.randint(1, 20)}"
                tasks = random.randint(0, 10)
                
                dashboard.update_agent_progress(
                    agent_id=agent_id,
                    percent_complete=agent_progress,
                    status=status,
                    current_activity=activity,
                    tasks_completed=tasks,
                    total_tasks=10,
                    thought_count=random.randint(0, 50)
                )
                
                # Register some thoughts
                if random.random() > 0.7:
                    dashboard.register_thought(
                        agent_id=agent_id,
                        chain_id=f"chain_{random.randint(1, 5)}",
                        content=f"Thinking about step {step} with confidence {random.randint(70, 99)}%",
                        thought_type=random.choice(["analysis", "decision", "discovery"])
                    )
                
                # Register some messages
                if random.random() > 0.8:
                    target_idx = random.randint(0, len(agents) - 1)
                    target = agents[target_idx]
                    
                    if target != agent_id:
                        dashboard.register_message(
                            source_agent=agent_id,
                            target_agent=target,
                            message_type=random.choice(["request", "response", "notification"]),
                            content=f"Message about task {random.randint(1, 10)}"
                        )
        
        # Final update
        dashboard.update_global_progress(100.0, "Completed", 100, 100)
        
        print("Dashboard demo running. Press Ctrl+C to exit...")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nStopping dashboard demo...")
    
    finally:
        # Stop dashboard
        dashboard.stop()
        print("Dashboard demo stopped.")
