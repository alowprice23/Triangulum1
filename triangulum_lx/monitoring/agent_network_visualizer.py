#!/usr/bin/env python3
"""
Agent Network Visualizer

This module provides visualization of agent communication networks,
allowing for transparent visibility into the interactions between
agents in the Triangulum agentic system.
"""

import logging
import datetime
import json
import os
import time
from typing import Dict, List, Any, Optional, Union, Tuple
import math
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from triangulum_lx.tooling.fs_ops import atomic_write
from triangulum_lx.core.fs_state import FileSystemStateCache
from pathlib import Path # For easier path manipulation

class AgentNetworkVisualizer:
    """
    Visualizes agent communication networks, providing transparent
    visibility into the interactions between agents in the agentic system.
    """
    
    def __init__(self, 
                 output_dir: str = "./agent_network_visualizations",
                 update_interval: float = 0.5,
                 max_history: int = 1000,
                 fs_cache: Optional[FileSystemStateCache] = None):
        """
        Initialize the agent network visualizer.
        
        Args:
            output_dir: Directory to store visualization outputs
            update_interval: How frequently to update visualizations (seconds)
            max_history: Maximum number of messages to keep in history
            fs_cache: Optional FileSystemStateCache instance.
        """
        self.output_dir = output_dir
        self.update_interval = update_interval
        self.max_history = max_history
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()

        # Create visualization directory
        output_dir_path = Path(output_dir)
        if not self.fs_cache.exists(str(output_dir_path)):
            output_dir_path.mkdir(parents=True, exist_ok=True)
            self.fs_cache.invalidate(str(output_dir_path))
        elif not self.fs_cache.is_dir(str(output_dir_path)):
            logger.warning(f"Output dir {output_dir_path} exists but is not a directory. Attempting to create.")
            output_dir_path.mkdir(parents=True, exist_ok=True)
            self.fs_cache.invalidate(str(output_dir_path))

        # Initialize network data
        self.agents = set()  # Set of agent IDs
        self.messages = []   # List of messages between agents
        self.connections = {}  # source_agent -> target_agent -> count
        self.agent_stats = {}  # agent_id -> stats
        self.last_update = time.time()
        
        # Templates for visualization
        templates_dir_path = Path(os.path.dirname(__file__)) / "templates"
        self.html_template_path = str(templates_dir_path / "agent_network.html")
        
        # Create templates directory if it doesn't exist
        if not self.fs_cache.exists(str(templates_dir_path)):
            templates_dir_path.mkdir(parents=True, exist_ok=True)
            self.fs_cache.invalidate(str(templates_dir_path))
        elif not self.fs_cache.is_dir(str(templates_dir_path)):
            logger.warning(f"Templates dir {templates_dir_path} exists but is not a directory. Attempting to create.")
            templates_dir_path.mkdir(parents=True, exist_ok=True)
            self.fs_cache.invalidate(str(templates_dir_path))
        
        # Create default HTML template if it doesn't exist
        if not self.fs_cache.exists(self.html_template_path):
            if not Path(self.html_template_path).exists(): # Double check FS
                self._create_default_template()
            else: # Cache stale
                logger.warning(f"Cache miss for existing template {self.html_template_path}. Invalidating.")
                self.fs_cache.invalidate(self.html_template_path)
        
        logger.info(f"Agent Network Visualizer initialized with output_dir={output_dir}")
    
    def _create_default_template(self):
        """Create the default HTML template for agent network visualization."""
        template = """<!DOCTYPE html>
<html>
<head>
    <title>Triangulum Agent Network Visualization</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .dashboard {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .visualization-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .visualization-title {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        .visualization-refresh {
            font-size: 14px;
            color: #888;
        }
        .network-container {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            position: relative;
            height: 600px;
        }
        .stats-container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-top: 20px;
        }
        .stat-card {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            flex: 1;
            min-width: 200px;
        }
        .stat-title {
            font-size: 16px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #1890ff;
        }
        .messages-container {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-top: 20px;
            max-height: 300px;
            overflow-y: auto;
        }
        .message {
            padding: 10px;
            border-bottom: 1px solid #eee;
            font-size: 14px;
        }
        .message:last-child {
            border-bottom: none;
        }
        .message-timestamp {
            font-size: 12px;
            color: #888;
        }
        .message-content {
            margin-top: 5px;
        }
        .agent-node {
            cursor: pointer;
        }
        .link-label {
            font-size: 10px;
            pointer-events: none;
        }
    </style>
</head>
<body>
    <div class="visualization-header">
        <div class="visualization-title">Triangulum Agent Network Visualization</div>
        <div class="visualization-refresh">Last updated: {{last_updated}}</div>
    </div>
    
    <div class="dashboard">
        <div class="network-container" id="network-visualization"></div>
        
        <div class="stats-container">
            <div class="stat-card">
                <div class="stat-title">Total Agents</div>
                <div class="stat-value">{{total_agents}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Total Messages</div>
                <div class="stat-value">{{total_messages}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Active Agents (Last 5m)</div>
                <div class="stat-value">{{active_agents}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Avg. Response Time</div>
                <div class="stat-value">{{avg_response_time}}ms</div>
            </div>
        </div>
        
        <div class="messages-container">
            <div class="stat-title">Recent Messages</div>
            {{recent_messages}}
        </div>
    </div>
    
    <script>
        // Network visualization using D3.js
        const width = document.getElementById('network-visualization').clientWidth;
        const height = document.getElementById('network-visualization').clientHeight;
        
        const svg = d3.select('#network-visualization')
            .append('svg')
            .attr('width', width)
            .attr('height', height);
        
        // Create the graph data
        const graphData = {{graph_data}};
        
        // Create a force simulation
        const simulation = d3.forceSimulation(graphData.nodes)
            .force('link', d3.forceLink(graphData.links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(50));
        
        // Add links
        const link = svg.append('g')
            .selectAll('line')
            .data(graphData.links)
            .enter()
            .append('line')
            .attr('stroke-width', d => Math.max(1, Math.sqrt(d.value)))
            .attr('stroke', '#999')
            .attr('stroke-opacity', 0.6);
        
        // Add link labels
        const linkLabel = svg.append('g')
            .selectAll('text')
            .data(graphData.links)
            .enter()
            .append('text')
            .attr('class', 'link-label')
            .text(d => d.value)
            .attr('fill', '#666')
            .attr('text-anchor', 'middle');
        
        // Add nodes
        const node = svg.append('g')
            .selectAll('circle')
            .data(graphData.nodes)
            .enter()
            .append('circle')
            .attr('r', 20)
            .attr('fill', d => d.color || '#1890ff')
            .attr('class', 'agent-node')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));
        
        // Add node labels
        const nodeLabel = svg.append('g')
            .selectAll('text')
            .data(graphData.nodes)
            .enter()
            .append('text')
            .text(d => d.id)
            .attr('text-anchor', 'middle')
            .attr('dy', 5)
            .attr('fill', 'white')
            .attr('pointer-events', 'none');
        
        // Update positions on simulation tick
        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            linkLabel
                .attr('x', d => (d.source.x + d.target.x) / 2)
                .attr('y', d => (d.source.y + d.target.y) / 2);
            
            node
                .attr('cx', d => d.x = Math.max(20, Math.min(width - 20, d.x)))
                .attr('cy', d => d.y = Math.max(20, Math.min(height - 20, d.y)));
                
            nodeLabel
                .attr('x', d => d.x)
                .attr('y', d => d.y);
        });
        
        // Drag functions
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        
        // Auto-refresh every 5 seconds
        setTimeout(function() {
            location.reload();
        }, 5000);
    </script>
</body>
</html>
"""
        
        # Create templates directory if it doesn't exist (already handled in __init__ with cache checks)
        # Path(self.html_template_path).parent.mkdir(parents=True, exist_ok=True)
        # self.fs_cache.invalidate(str(Path(self.html_template_path).parent))
        
        # Save the template
        atomic_write(self.html_template_path, template.encode('utf-8'))
        self.fs_cache.invalidate(self.html_template_path)
    
    def register_message(self, 
                        source_agent: str, 
                        target_agent: str, 
                        message_type: str, 
                        content: Optional[str] = None,
                        metadata: Optional[Dict] = None):
        """
        Register a message between agents.
        
        Args:
            source_agent: ID of the source agent
            target_agent: ID of the target agent
            message_type: Type of message (command, response, etc.)
            content: Optional message content
            metadata: Optional additional metadata
        """
        timestamp = datetime.datetime.now().isoformat()
        
        message = {
            "source_agent": source_agent,
            "target_agent": target_agent,
            "message_type": message_type,
            "content": content,
            "timestamp": timestamp,
            "metadata": metadata or {}
        }
        
        # Add to message history
        self.messages.append(message)
        
        # Limit history size
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
        
        # Update agents set
        self.agents.add(source_agent)
        self.agents.add(target_agent)
        
        # Update connections
        if source_agent not in self.connections:
            self.connections[source_agent] = {}
        
        if target_agent not in self.connections[source_agent]:
            self.connections[source_agent][target_agent] = 0
        
        self.connections[source_agent][target_agent] += 1
        
        # Update agent stats
        for agent_id in [source_agent, target_agent]:
            if agent_id not in self.agent_stats:
                self.agent_stats[agent_id] = {
                    "messages_sent": 0,
                    "messages_received": 0,
                    "last_active": timestamp,
                    "response_times": []
                }
        
        # Update message counts
        self.agent_stats[source_agent]["messages_sent"] += 1
        self.agent_stats[target_agent]["messages_received"] += 1
        
        # Update last active timestamp
        self.agent_stats[source_agent]["last_active"] = timestamp
        self.agent_stats[target_agent]["last_active"] = timestamp
        
        # Calculate response time if this is a response to a previous message
        if message_type.lower() == "response" and metadata and "request_timestamp" in metadata:
            try:
                request_time = datetime.datetime.fromisoformat(metadata["request_timestamp"])
                response_time = datetime.datetime.fromisoformat(timestamp)
                response_time_ms = (response_time - request_time).total_seconds() * 1000
                self.agent_stats[source_agent]["response_times"].append(response_time_ms)
                
                # Limit response time history
                if len(self.agent_stats[source_agent]["response_times"]) > 100:
                    self.agent_stats[source_agent]["response_times"] = self.agent_stats[source_agent]["response_times"][-100:]
            except (ValueError, TypeError) as e:
                logger.warning(f"Error calculating response time: {e}")
        
        # Update visualizations if needed
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.update_visualizations()
            self.last_update = current_time
    
    def update_visualizations(self):
        """Update all visualizations based on current network data."""
        self._generate_html_visualization()
    
    def _generate_html_visualization(self):
        """Generate HTML visualization of agent network."""
        # Read template
        try:
            with open(self.html_template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except Exception as e:
            logger.error(f"Error reading HTML template: {e}")
            template = "<html><body><h1>Error loading template</h1></body></html>"
        
        # Calculate statistics
        now = datetime.datetime.now()
        five_minutes_ago = (now - datetime.timedelta(minutes=5)).isoformat()
        
        total_agents = len(self.agents)
        total_messages = len(self.messages)
        
        active_agents = sum(1 for agent_id, stats in self.agent_stats.items() 
                           if stats["last_active"] >= five_minutes_ago)
        
        # Calculate average response time across all agents
        response_times = []
        for agent_id, stats in self.agent_stats.items():
            response_times.extend(stats.get("response_times", []))
        
        avg_response_time = round(sum(response_times) / len(response_times)) if response_times else 0
        
        # Generate graph data for D3.js
        graph_data = {
            "nodes": [],
            "links": []
        }
        
        # Add nodes (agents)
        for agent_id in self.agents:
            # Calculate node color based on agent type or activity
            if agent_id.lower() in ["orchestrator", "master"]:
                color = "#1890ff"  # Blue for orchestrator
            elif "analyzer" in agent_id.lower():
                color = "#52c41a"  # Green for analyzers
            elif "detector" in agent_id.lower():
                color = "#fa8c16"  # Orange for detectors
            elif "verification" in agent_id.lower():
                color = "#722ed1"  # Purple for verification
            else:
                color = "#f5222d"  # Red for other agents
            
            graph_data["nodes"].append({
                "id": agent_id,
                "color": color
            })
        
        # Add links (connections between agents)
        for source_agent, targets in self.connections.items():
            for target_agent, count in targets.items():
                graph_data["links"].append({
                    "source": source_agent,
                    "target": target_agent,
                    "value": count
                })
        
        # Generate recent messages HTML
        recent_messages_html = ""
        for message in reversed(self.messages[-10:]):
            source = message["source_agent"]
            target = message["target_agent"]
            msg_type = message["message_type"]
            timestamp = datetime.datetime.fromisoformat(message["timestamp"]).strftime("%H:%M:%S")
            
            content = message.get("content", "")
            if content and len(content) > 50:
                content = content[:47] + "..."
            
            recent_messages_html += f"""
            <div class="message">
                <div class="message-timestamp">{timestamp}</div>
                <div class="message-content">
                    <strong>{source}</strong> → <strong>{target}</strong> ({msg_type})
                    {f': {content}' if content else ''}
                </div>
            </div>
            """
        
        # Replace template placeholders
        html = template.replace("{{total_agents}}", str(total_agents))
        html = html.replace("{{total_messages}}", str(total_messages))
        html = html.replace("{{active_agents}}", str(active_agents))
        html = html.replace("{{avg_response_time}}", str(avg_response_time))
        html = html.replace("{{recent_messages}}", recent_messages_html)
        html = html.replace("{{graph_data}}", json.dumps(graph_data))
        html = html.replace("{{last_updated}}", now.strftime("%Y-%m-%d %H:%M:%S"))
        
        # Write HTML file
        output_path = os.path.join(self.output_dir, "agent_network.html")
        atomic_write(output_path, html.encode('utf-8'))
        self.fs_cache.invalidate(output_path)
        
        logger.debug(f"HTML visualization updated at {output_path} using atomic_write")
    
    def save_network_data(self, output_path: Optional[str] = None):
        """
        Save the current network data to a JSON file.
        
        Args:
            output_path: Path to save the JSON file. If None, uses default path.
        """
        if output_path is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.output_dir, f"agent_network_{timestamp}.json")
        
        # Prepare data for serialization
        data = {
            "agents": list(self.agents),
            "messages": self.messages,
            "connections": self.connections,
            "agent_stats": self.agent_stats,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Save to file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True) # Ensure parent dir for safety
        self.fs_cache.invalidate(str(Path(output_path).parent))

        content_str = json.dumps(data, indent=2)
        atomic_write(output_path, content_str.encode('utf-8'))
        self.fs_cache.invalidate(output_path)
        
        logger.info(f"Agent network data saved to {output_path} using atomic_write")
        return output_path


# Demo usage when run directly
if __name__ == "__main__":
    # Create visualizer
    visualizer = AgentNetworkVisualizer(output_dir="./agent_network_visualizations")
    
    # Define agents
    agents = [
        "orchestrator",
        "bug_detector",
        "relationship_analyst",
        "verification",
        "priority_analyzer",
        "code_fixer"
    ]
    
    # Simulate message exchange
    for _ in range(50):
        # Select random source and target agents
        source_idx = random.randint(0, len(agents) - 1)
        target_idx = random.randint(0, len(agents) - 1)
        while target_idx == source_idx:
            target_idx = random.randint(0, len(agents) - 1)
        
        source = agents[source_idx]
        target = agents[target_idx]
        
        # Determine message type
        if random.random() < 0.7:
            message_type = "request"
            content = f"Request for analysis of module {random.randint(1, 10)}"
            metadata = None
        else:
            message_type = "response"
            content = f"Analysis complete with confidence {random.randint(70, 99)}%"
            # Simulate a response to a previous message
            request_time = (datetime.datetime.now() - datetime.timedelta(seconds=random.uniform(0.1, 2.0))).isoformat()
            metadata = {"request_timestamp": request_time}
        
        # Register message
        visualizer.register_message(source, target, message_type, content, metadata)
        
        # Pause briefly
        time.sleep(0.1)
    
    # Force update and save
    visualizer.update_visualizations()
    visualizer.save_network_data()
    
    print(f"Agent network visualization demo completed. Check the ./agent_network_visualizations directory.")
