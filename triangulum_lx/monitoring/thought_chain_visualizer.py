#!/usr/bin/env python3
"""
Thought Chain Visualizer

This module provides real-time visualization of agent thought chains,
allowing for transparent visibility into the internal reasoning processes
of the Triangulum agentic system.
"""

import logging
import datetime
import json
from typing import Dict, List, Any, Optional, Union
import os
import time
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from triangulum_lx.tooling.fs_ops import atomic_write
from triangulum_lx.core.fs_state import FileSystemStateCache

class ThoughtChainVisualizer:
    """
    Visualizes agent thought chains in real-time, providing transparent
    visibility into the internal reasoning processes of LLM-powered agents.
    """
    
    def __init__(self, 
                 output_dir: str = "./thought_visualizations",
                 update_interval: float = 0.5,
                 enable_html_output: bool = True,
                 enable_terminal_output: bool = True,
                 max_history: int = 100,
                 fs_cache: Optional[FileSystemStateCache] = None):
        """
        Initialize the thought chain visualizer.
        
        Args:
            output_dir: Directory to store visualization outputs
            update_interval: How frequently to update visualizations (seconds)
            enable_html_output: Whether to generate HTML visualizations
            enable_terminal_output: Whether to display in terminal
            max_history: Maximum number of thoughts to keep in history
            fs_cache: Optional FileSystemStateCache instance.
        """
        self.output_dir = output_dir
        self.update_interval = update_interval
        self.enable_html_output = enable_html_output
        self.enable_terminal_output = enable_terminal_output
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
        
        # Initialize thought storage
        self.thought_chains = {}  # agent_id -> list of thoughts
        self.active_chains = {}   # chain_id -> chain data
        self.last_update = time.time()
        
        # Templates for visualization
        templates_dir_path = Path(os.path.dirname(__file__)) / "templates"
        self.html_template_path = str(templates_dir_path / "thought_chain.html")
        
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
        
        logger.info(f"Thought Chain Visualizer initialized with output_dir={output_dir}")
    
    def _create_default_template(self):
        """Create the default HTML template for thought chain visualization."""
        template = """<!DOCTYPE html>
<html>
<head>
    <title>Triangulum Thought Chain Visualization</title>
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
        .agent-section {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .agent-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }
        .agent-name {
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }
        .agent-status {
            font-size: 14px;
            padding: 4px 8px;
            border-radius: 4px;
            background-color: #e6f7ff;
            color: #1890ff;
        }
        .thought-chain {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-top: 10px;
        }
        .thought {
            padding: 10px;
            border-left: 3px solid #1890ff;
            background-color: #f9f9f9;
            font-size: 14px;
            position: relative;
        }
        .thought-type {
            position: absolute;
            right: 10px;
            top: 10px;
            font-size: 12px;
            color: #888;
        }
        .thought-timestamp {
            font-size: 12px;
            color: #888;
            margin-top: 5px;
        }
        .thought-content {
            margin-top: 5px;
            white-space: pre-wrap;
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
        .progress-bar-container {
            width: 100%;
            height: 8px;
            background-color: #f0f0f0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }
        .progress-bar {
            height: 100%;
            background-color: #52c41a;
            transition: width 0.3s ease;
        }
        .connections {
            margin-top: 20px;
            padding-top: 10px;
            border-top: 1px dashed #eee;
        }
        .connection {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 5px;
            font-size: 12px;
            color: #666;
        }
        .connection-arrow {
            color: #1890ff;
        }
    </style>
</head>
<body>
    <div class="visualization-header">
        <div class="visualization-title">Triangulum Thought Chain Visualization</div>
        <div class="visualization-refresh">Last updated: {{last_updated}}</div>
    </div>
    
    <div class="dashboard">
        {{agent_sections}}
    </div>
    
    <script>
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
    
    def register_thought(self, 
                        agent_id: str, 
                        chain_id: str, 
                        content: str, 
                        thought_type: str = "analysis",
                        metadata: Optional[Dict] = None):
        """
        Register a new thought in a chain.
        
        Args:
            agent_id: ID of the agent that generated the thought
            chain_id: ID of the thought chain
            content: The thought content
            thought_type: Type of thought (analysis, decision, etc.)
            metadata: Additional metadata for the thought
        """
        timestamp = datetime.datetime.now().isoformat()
        
        thought = {
            "agent_id": agent_id,
            "chain_id": chain_id,
            "content": content,
            "thought_type": thought_type,
            "timestamp": timestamp,
            "metadata": metadata or {}
        }
        
        # Initialize agent's thought list if needed
        if agent_id not in self.thought_chains:
            self.thought_chains[agent_id] = []
        
        # Add thought to agent's list
        self.thought_chains[agent_id].append(thought)
        
        # Limit history size
        if len(self.thought_chains[agent_id]) > self.max_history:
            self.thought_chains[agent_id] = self.thought_chains[agent_id][-self.max_history:]
        
        # Initialize or update active chain
        if chain_id not in self.active_chains:
            self.active_chains[chain_id] = {
                "chain_id": chain_id,
                "created_at": timestamp,
                "last_updated": timestamp,
                "thoughts": [],
                "agents": set(),
                "connections": []
            }
        
        # Update chain data
        self.active_chains[chain_id]["last_updated"] = timestamp
        self.active_chains[chain_id]["thoughts"].append(thought)
        self.active_chains[chain_id]["agents"].add(agent_id)
        
        # Update visualizations if needed
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.update_visualizations()
            self.last_update = current_time
        
        # Terminal output if enabled
        if self.enable_terminal_output:
            self._print_thought_to_terminal(thought)
    
    def register_connection(self, source_chain_id: str, target_chain_id: str, 
                           connection_type: str = "reference"):
        """
        Register a connection between two thought chains.
        
        Args:
            source_chain_id: ID of the source thought chain
            target_chain_id: ID of the target thought chain
            connection_type: Type of connection between chains
        """
        if source_chain_id not in self.active_chains or target_chain_id not in self.active_chains:
            logger.warning(f"Cannot connect chains: {source_chain_id} -> {target_chain_id}. One or both chains do not exist.")
            return
        
        connection = {
            "source": source_chain_id,
            "target": target_chain_id,
            "type": connection_type,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        self.active_chains[source_chain_id]["connections"].append(connection)
        
        # Update visualizations if needed
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.update_visualizations()
            self.last_update = current_time
    
    def _print_thought_to_terminal(self, thought: Dict):
        """Print a thought to the terminal in a structured format."""
        agent_id = thought["agent_id"]
        thought_type = thought["thought_type"]
        content = thought["content"]
        
        print(f"[{agent_id}] ({thought_type}): {content}")
    
    def update_visualizations(self):
        """Update all visualizations based on current thought chains."""
        if self.enable_html_output:
            self._generate_html_visualization()
    
    def _generate_html_visualization(self):
        """Generate HTML visualization of thought chains."""
        # Read template
        try:
            with open(self.html_template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except Exception as e:
            logger.error(f"Error reading HTML template: {e}")
            template = "<html><body><h1>Error loading template</h1></body></html>"
        
        # Generate agent sections
        agent_sections = ""
        for agent_id, thoughts in self.thought_chains.items():
            # Calculate agent status based on recent activity
            if thoughts:
                last_thought_time = datetime.datetime.fromisoformat(thoughts[-1]["timestamp"])
                now = datetime.datetime.now()
                time_diff = (now - last_thought_time).total_seconds()
                
                if time_diff < 5:
                    status = "Active"
                elif time_diff < 60:
                    status = "Recent"
                else:
                    status = "Idle"
            else:
                status = "No activity"
            
            # Generate thought HTML
            thoughts_html = ""
            for thought in thoughts:
                thought_content = thought["content"]
                thought_type = thought["thought_type"]
                timestamp = datetime.datetime.fromisoformat(thought["timestamp"]).strftime("%H:%M:%S")
                
                thoughts_html += f"""
                <div class="thought">
                    <div class="thought-type">{thought_type}</div>
                    <div class="thought-content">{thought_content}</div>
                    <div class="thought-timestamp">{timestamp}</div>
                </div>
                """
            
            # Generate agent section
            agent_sections += f"""
            <div class="agent-section">
                <div class="agent-header">
                    <div class="agent-name">{agent_id}</div>
                    <div class="agent-status">{status}</div>
                </div>
                <div class="thought-chain">
                    {thoughts_html}
                </div>
            </div>
            """
        
        # Replace template placeholders
        html = template.replace("{{agent_sections}}", agent_sections)
        html = html.replace("{{last_updated}}", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Write HTML file
        output_path = os.path.join(self.output_dir, "thought_chains.html")
        atomic_write(output_path, html.encode('utf-8'))
        self.fs_cache.invalidate(output_path)
        
        logger.debug(f"HTML visualization updated at {output_path} using atomic_write")
    
    def save_thought_chains(self, output_path: Optional[str] = None):
        """
        Save the current thought chains to a JSON file.
        
        Args:
            output_path: Path to save the JSON file. If None, uses default path.
        """
        if output_path is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.output_dir, f"thought_chains_{timestamp}.json")
        
        # Convert to serializable format
        serializable_chains = {}
        for chain_id, chain in self.active_chains.items():
            serializable_chain = chain.copy()
            serializable_chain["agents"] = list(serializable_chain["agents"])
            serializable_chains[chain_id] = serializable_chain
        
        # Save to file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True) # Ensure parent dir for safety
        self.fs_cache.invalidate(str(Path(output_path).parent))

        content_str = json.dumps(serializable_chains, indent=2)
        atomic_write(output_path, content_str.encode('utf-8'))
        self.fs_cache.invalidate(output_path)
        
        logger.info(f"Thought chains saved to {output_path} using atomic_write")
        return output_path


# Demo usage when run directly
if __name__ == "__main__":
    # Create visualizer
    visualizer = ThoughtChainVisualizer(output_dir="./thought_visualizations")
    
    # Simulate some thought chains
    chain_id_1 = "planning_chain_1"
    chain_id_2 = "execution_chain_1"
    
    # Agent 1 thoughts
    visualizer.register_thought("orchestrator", chain_id_1, "Starting planning process for task", "initialization")
    time.sleep(1)
    visualizer.register_thought("priority_analyzer", chain_id_1, "Analyzing task dependencies and constraints", "analysis")
    time.sleep(1)
    visualizer.register_thought("priority_analyzer", chain_id_1, "Identified 3 critical dependencies", "analysis")
    time.sleep(1)
    
    # Agent 2 thoughts
    visualizer.register_thought("relationship_analyst", chain_id_2, "Examining code structure for dependencies", "analysis")
    time.sleep(1)
    visualizer.register_thought("relationship_analyst", chain_id_2, "Found circular dependency between modules A and B", "discovery")
    
    # Connect the chains
    visualizer.register_connection(chain_id_1, chain_id_2, "leads_to")
    
    # More thoughts
    visualizer.register_thought("orchestrator", chain_id_1, "Developing execution strategy based on priorities", "planning")
    time.sleep(1)
    visualizer.register_thought("orchestrator", chain_id_1, "Strategy finalized: will execute in order A, C, B", "decision")
    
    # Force update and save
    visualizer.update_visualizations()
    visualizer.save_thought_chains()
    
    print(f"Thought chain visualization demo completed. Check the ./thought_visualizations directory.")
