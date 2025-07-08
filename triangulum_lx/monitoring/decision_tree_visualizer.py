#!/usr/bin/env python3
"""
Decision Tree Visualizer

This module provides visualization of agent decision trees,
allowing for transparent visibility into the reasoning processes
and decision pathways of the Triangulum agentic system.
"""

import logging
import datetime
import json
import os
import time
from typing import Dict, List, Any, Optional, Union, Tuple
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DecisionTreeVisualizer:
    """
    Visualizes agent decision trees, providing transparent visibility
    into the reasoning processes and decision pathways of LLM-powered agents.
    """
    
    def __init__(self, 
                 output_dir: str = "./decision_tree_visualizations",
                 update_interval: float = 0.5,
                 enable_html_output: bool = True,
                 max_history: int = 100):
        """
        Initialize the decision tree visualizer.
        
        Args:
            output_dir: Directory to store visualization outputs
            update_interval: How frequently to update visualizations (seconds)
            enable_html_output: Whether to generate HTML visualizations
            max_history: Maximum number of decisions to keep in history
        """
        self.output_dir = output_dir
        self.update_interval = update_interval
        self.enable_html_output = enable_html_output
        self.max_history = max_history
        
        # Create visualization directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize decision tree storage
        self.decision_trees = {}  # tree_id -> tree data
        self.agent_trees = {}  # agent_id -> list of tree_ids
        self.last_update = time.time()
        
        # Templates for visualization
        self.html_template_path = os.path.join(os.path.dirname(__file__), "templates", "decision_tree.html")
        
        # Create templates directory if it doesn't exist
        os.makedirs(os.path.join(os.path.dirname(__file__), "templates"), exist_ok=True)
        
        # Create default HTML template if it doesn't exist
        if not os.path.exists(self.html_template_path):
            self._create_default_template()
        
        logger.info(f"Decision Tree Visualizer initialized with output_dir={output_dir}")
    
    def _create_default_template(self):
        """Create the default HTML template for decision tree visualization."""
        template = """<!DOCTYPE html>
<html>
<head>
    <title>Triangulum Decision Tree Visualization</title>
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
        .visualization-controls {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }
        .control-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .control-label {
            font-size: 14px;
            color: #333;
        }
        .control-select {
            padding: 5px;
            border-radius: 4px;
            border: 1px solid #d9d9d9;
        }
        .tree-container {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            height: 600px;
            overflow: auto;
        }
        .node {
            cursor: pointer;
        }
        .node circle {
            fill: #fff;
            stroke: #1890ff;
            stroke-width: 2px;
        }
        .node.decision circle {
            fill: #e6f7ff;
        }
        .node.analysis circle {
            fill: #f6ffed;
        }
        .node.alternative circle {
            fill: #fff7e6;
        }
        .node.rejected circle {
            fill: #fff1f0;
            stroke: #ff4d4f;
        }
        .node text {
            font-size: 12px;
        }
        .link {
            fill: none;
            stroke: #ccc;
            stroke-width: 1.5px;
        }
        .tooltip {
            position: absolute;
            background-color: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px;
            border-radius: 4px;
            font-size: 12px;
            max-width: 300px;
            z-index: 10;
            pointer-events: none;
        }
        .confidence-high {
            color: #52c41a;
        }
        .confidence-medium {
            color: #faad14;
        }
        .confidence-low {
            color: #ff4d4f;
        }
        .tree-info {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-top: 20px;
        }
        .tree-info-title {
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }
        .tree-info-item {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        .tree-info-label {
            font-weight: bold;
            color: #333;
        }
        .tree-info-value {
            color: #666;
        }
        .node-details {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-top: 20px;
            display: none;
        }
        .node-details.active {
            display: block;
        }
        .node-details-title {
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }
        .node-details-content {
            white-space: pre-wrap;
            font-family: monospace;
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
            max-height: 200px;
            overflow: auto;
        }
        .alternatives-container {
            margin-top: 10px;
        }
        .alternative-item {
            padding: 5px;
            border-left: 3px solid #faad14;
            margin-bottom: 5px;
            background-color: #fffbe6;
        }
    </style>
</head>
<body>
    <div class="visualization-header">
        <div class="visualization-title">Triangulum Decision Tree Visualization</div>
        <div class="visualization-refresh">Last updated: {{last_updated}}</div>
    </div>
    
    <div class="visualization-controls">
        <div class="control-group">
            <div class="control-label">Agent:</div>
            <select id="agent-select" class="control-select">
                {{agent_options}}
            </select>
        </div>
        <div class="control-group">
            <div class="control-label">Decision Tree:</div>
            <select id="tree-select" class="control-select">
                {{tree_options}}
            </select>
        </div>
        <div class="control-group">
            <div class="control-label">View:</div>
            <select id="view-select" class="control-select">
                <option value="full">Full Tree</option>
                <option value="selected">Selected Path</option>
                <option value="alternatives">Show Alternatives</option>
            </select>
        </div>
    </div>
    
    <div class="dashboard">
        <div class="tree-container" id="tree-visualization"></div>
        
        <div class="tree-info">
            <div class="tree-info-title">Tree Information</div>
            <div class="tree-info-item">
                <div class="tree-info-label">Tree ID:</div>
                <div class="tree-info-value" id="tree-id">{{tree_id}}</div>
            </div>
            <div class="tree-info-item">
                <div class="tree-info-label">Agent:</div>
                <div class="tree-info-value" id="tree-agent">{{agent_id}}</div>
            </div>
            <div class="tree-info-item">
                <div class="tree-info-label">Created:</div>
                <div class="tree-info-value" id="tree-created">{{created_at}}</div>
            </div>
            <div class="tree-info-item">
                <div class="tree-info-label">Last Updated:</div>
                <div class="tree-info-value" id="tree-updated">{{last_updated_at}}</div>
            </div>
            <div class="tree-info-item">
                <div class="tree-info-label">Nodes:</div>
                <div class="tree-info-value" id="tree-nodes">{{node_count}}</div>
            </div>
            <div class="tree-info-item">
                <div class="tree-info-label">Depth:</div>
                <div class="tree-info-value" id="tree-depth">{{tree_depth}}</div>
            </div>
            <div class="tree-info-item">
                <div class="tree-info-label">Status:</div>
                <div class="tree-info-value" id="tree-status">{{tree_status}}</div>
            </div>
        </div>
        
        <div class="node-details" id="node-details">
            <div class="node-details-title">Node Details</div>
            <div class="node-details-content" id="node-content"></div>
            
            <div class="alternatives-container" id="alternatives-container">
                <div class="tree-info-title">Alternative Paths</div>
                <div id="alternatives-list"></div>
            </div>
        </div>
    </div>
    
    <script>
        // Decision tree data
        const treeData = {{tree_data}};
        const agentTrees = {{agent_trees}};
        
        // Set up the tree visualization using D3.js
        const width = document.getElementById('tree-visualization').clientWidth;
        const height = document.getElementById('tree-visualization').clientHeight;
        const margin = {top: 20, right: 90, bottom: 30, left: 90};
        
        // Clear previous SVG
        d3.select('#tree-visualization').selectAll('svg').remove();
        
        // Create SVG
        const svg = d3.select('#tree-visualization')
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);
            
        // Create a tooltip div
        const tooltip = d3.select('body').append('div')
            .attr('class', 'tooltip')
            .style('opacity', 0);
        
        // Create tree layout
        const treemap = d3.tree().size([height - margin.top - margin.bottom, width - margin.left - margin.right]);
        
        // Helper function to update the tree visualization
        function updateTree(treeId) {
            if (!treeData[treeId]) return;
            
            // Process data for D3
            const root = d3.hierarchy(treeData[treeId].root);
            const nodes = treemap(root);
            
            // Add links
            const link = svg.selectAll('.link')
                .data(nodes.descendants().slice(1))
                .enter().append('path')
                .attr('class', 'link')
                .attr('d', d => {
                    return `M${d.y},${d.x}C${(d.y + d.parent.y) / 2},${d.x} ${(d.y + d.parent.y) / 2},${d.parent.x} ${d.parent.y},${d.parent.x}`;
                });
            
            // Add nodes
            const node = svg.selectAll('.node')
                .data(nodes.descendants())
                .enter().append('g')
                .attr('class', d => {
                    let classes = 'node';
                    if (d.data.type) classes += ` ${d.data.type}`;
                    if (d.data.rejected) classes += ' rejected';
                    return classes;
                })
                .attr('transform', d => `translate(${d.y},${d.x})`)
                .on('mouseover', function(event, d) {
                    tooltip.transition()
                        .duration(200)
                        .style('opacity', .9);
                    
                    // Format confidence with color
                    let confidenceHtml = '';
                    if (d.data.confidence) {
                        let confidenceClass = 'confidence-medium';
                        if (d.data.confidence >= 80) confidenceClass = 'confidence-high';
                        if (d.data.confidence < 50) confidenceClass = 'confidence-low';
                        
                        confidenceHtml = `<div>Confidence: <span class="${confidenceClass}">${d.data.confidence}%</span></div>`;
                    }
                    
                    tooltip.html(`
                        <div>${d.data.name}</div>
                        ${confidenceHtml}
                        <div>${d.data.description || ''}</div>
                    `)
                    .style('left', (event.pageX + 10) + 'px')
                    .style('top', (event.pageY - 28) + 'px');
                })
                .on('mouseout', function() {
                    tooltip.transition()
                        .duration(500)
                        .style('opacity', 0);
                })
                .on('click', function(event, d) {
                    // Show node details
                    document.getElementById('node-details').classList.add('active');
                    document.getElementById('node-content').textContent = d.data.content || d.data.name;
                    
                    // Show alternatives if any
                    const alternativesContainer = document.getElementById('alternatives-container');
                    const alternativesList = document.getElementById('alternatives-list');
                    
                    if (d.data.alternatives && d.data.alternatives.length > 0) {
                        alternativesContainer.style.display = 'block';
                        alternativesList.innerHTML = '';
                        
                        d.data.alternatives.forEach(alt => {
                            const altItem = document.createElement('div');
                            altItem.className = 'alternative-item';
                            altItem.textContent = alt.content || alt.name;
                            alternativesList.appendChild(altItem);
                        });
                    } else {
                        alternativesContainer.style.display = 'none';
                    }
                });
            
            // Add circles to nodes
            node.append('circle')
                .attr('r', d => d.data.type === 'decision' ? 8 : 5)
                .attr('fill', d => d.data.color || '#fff');
            
            // Add labels to nodes
            node.append('text')
                .attr('dy', '.35em')
                .attr('x', d => d.children ? -13 : 13)
                .attr('text-anchor', d => d.children ? 'end' : 'start')
                .text(d => {
                    let text = d.data.name;
                    if (text.length > 30) {
                        return text.substring(0, 27) + '...';
                    }
                    return text;
                });
            
            // Update tree info
            document.getElementById('tree-id').textContent = treeId;
            document.getElementById('tree-agent').textContent = treeData[treeId].agent_id;
            document.getElementById('tree-created').textContent = new Date(treeData[treeId].created_at).toLocaleString();
            document.getElementById('tree-updated').textContent = new Date(treeData[treeId].last_updated).toLocaleString();
            document.getElementById('tree-nodes').textContent = treeData[treeId].node_count || 'Unknown';
            document.getElementById('tree-depth').textContent = treeData[treeId].depth || 'Unknown';
            document.getElementById('tree-status').textContent = treeData[treeId].status || 'Unknown';
        }
        
        // Populate agent select
        const agentSelect = document.getElementById('agent-select');
        Object.keys(agentTrees).forEach(agentId => {
            const option = document.createElement('option');
            option.value = agentId;
            option.textContent = agentId;
            agentSelect.appendChild(option);
        });
        
        // Update tree select when agent changes
        agentSelect.addEventListener('change', () => {
            const agentId = agentSelect.value;
            const treeSelect = document.getElementById('tree-select');
            
            // Clear current options
            treeSelect.innerHTML = '';
            
            // Add options for selected agent
            if (agentTrees[agentId]) {
                agentTrees[agentId].forEach(treeId => {
                    const option = document.createElement('option');
                    option.value = treeId;
                    
                    // Get tree name or use ID
                    let treeName = treeId;
                    if (treeData[treeId] && treeData[treeId].name) {
                        treeName = treeData[treeId].name;
                    }
                    
                    option.textContent = treeName;
                    treeSelect.appendChild(option);
                });
                
                // Update tree visualization
                if (agentTrees[agentId].length > 0) {
                    updateTree(agentTrees[agentId][0]);
                }
            }
        });
        
        // Update visualization when tree changes
        document.getElementById('tree-select').addEventListener('change', (e) => {
            const treeId = e.target.value;
            updateTree(treeId);
        });
        
        // View select handling
        document.getElementById('view-select').addEventListener('change', (e) => {
            const viewType = e.target.value;
            // Implement different view types (full tree, selected path, show alternatives)
            // This would require more complex logic based on the selected tree data
        });
        
        // Initialize with first tree if available
        if (Object.keys(treeData).length > 0) {
            const firstTreeId = Object.keys(treeData)[0];
            updateTree(firstTreeId);
        }
        
        // Auto-refresh every 5 seconds
        setTimeout(function() {
            location.reload();
        }, 5000);
    </script>
</body>
</html>
"""
        
        # Create templates directory if it doesn't exist
        os.makedirs(os.path.dirname(self.html_template_path), exist_ok=True)
        
        # Save the template
        with open(self.html_template_path, 'w', encoding='utf-8') as f:
            f.write(template)
    
    def create_decision_tree(self, 
                           agent_id: str, 
                           name: Optional[str] = None,
                           description: Optional[str] = None) -> str:
        """
        Create a new decision tree.
        
        Args:
            agent_id: ID of the agent that owns the tree
            name: Optional name for the tree
            description: Optional description of the tree
        
        Returns:
            tree_id: ID of the created tree
        """
        tree_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        # Create root node
        root_node = {
            "name": "Root",
            "type": "root",
            "content": "Decision tree root",
            "children": []
        }
        
        # Create tree data
        tree = {
            "tree_id": tree_id,
            "agent_id": agent_id,
            "name": name or f"Decision Tree {tree_id[:8]}",
            "description": description,
            "created_at": timestamp,
            "last_updated": timestamp,
            "status": "Active",
            "node_count": 1,
            "depth": 0,
            "root": root_node
        }
        
        # Add to storage
        self.decision_trees[tree_id] = tree
        
        # Initialize agent's tree list if needed
        if agent_id not in self.agent_trees:
            self.agent_trees[agent_id] = []
        
        # Add tree to agent's list
        self.agent_trees[agent_id].append(tree_id)
        
        # Update visualizations if needed
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.update_visualizations()
            self.last_update = current_time
        
        logger.info(f"Created decision tree {tree_id} for agent {agent_id}")
        return tree_id
    
    def add_decision_node(self, 
                         tree_id: str, 
                         parent_id: Optional[str], 
                         node_id: Optional[str] = None,
                         name: str = "Decision",
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
            node_id: Optional ID for the node, will be generated if None
            name: Name/title of the node
            node_type: Type of node (decision, analysis, action, etc.)
            content: Detailed content/description of the node
            confidence: Confidence level (0-100) for this decision
            alternatives: List of alternative decisions that were not taken
            metadata: Additional metadata for the node
        
        Returns:
            node_id: ID of the created node
        """
        if tree_id not in self.decision_trees:
            logger.warning(f"Tree {tree_id} does not exist")
            return None
        
        tree = self.decision_trees[tree_id]
        
        # Generate node ID if not provided
        if node_id is None:
            node_id = str(uuid.uuid4())
        
        # Create node data
        node = {
            "id": node_id,
            "name": name,
            "type": node_type,
            "content": content,
            "confidence": confidence,
            "alternatives": alternatives or [],
            "metadata": metadata or {},
            "children": []
        }
        
        # Add node to tree
        if parent_id is None:
            # Add to root
            tree["root"]["children"].append(node)
        else:
            # Find parent node
            parent_node = self._find_node(tree["root"], parent_id)
            if parent_node:
                parent_node["children"].append(node)
            else:
                logger.warning(f"Parent node {parent_id} not found in tree {tree_id}")
                return None
        
        # Update tree metadata
        tree["last_updated"] = datetime.datetime.now().isoformat()
        tree["node_count"] = tree.get("node_count", 0) + 1
        
        # Update tree depth
        depth = self._calculate_tree_depth(tree["root"])
        tree["depth"] = depth
        
        # Update visualizations if needed
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.update_visualizations()
            self.last_update = current_time
        
        logger.debug(f"Added node {node_id} to tree {tree_id}")
        return node_id
    
    def _find_node(self, root: Dict, node_id: str) -> Optional[Dict]:
        """Find a node by ID in the tree."""
        if root.get("id") == node_id:
            return root
        
        for child in root.get("children", []):
            found = self._find_node(child, node_id)
            if found:
                return found
        
        return None
    
    def _calculate_tree_depth(self, node: Dict, current_depth: int = 0) -> int:
        """Calculate the depth of a tree."""
        if not node.get("children"):
            return current_depth
        
        child_depths = [self._calculate_tree_depth(child, current_depth + 1) 
                       for child in node.get("children", [])]
        
        return max(child_depths) if child_depths else current_depth
    
    def mark_alternative_rejected(self, tree_id: str, node_id: str, rejected: bool = True):
        """
        Mark a decision node as rejected/accepted.
        
        Args:
            tree_id: ID of the tree
            node_id: ID of the node to mark
            rejected: Whether the node is rejected (True) or accepted (False)
        """
        if tree_id not in self.decision_trees:
            logger.warning(f"Tree {tree_id} does not exist")
            return
        
        tree = self.decision_trees[tree_id]
        
        # Find node
        node = self._find_node(tree["root"], node_id)
        if node:
            node["rejected"] = rejected
            
            # Update tree metadata
            tree["last_updated"] = datetime.datetime.now().isoformat()
            
            # Update visualizations if needed
            current_time = time.time()
            if current_time - self.last_update >= self.update_interval:
                self.update_visualizations()
                self.last_update = current_time
        else:
            logger.warning(f"Node {node_id} not found in tree {tree_id}")
    
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
        if tree_id not in self.decision_trees:
            logger.warning(f"Tree {tree_id} does not exist")
            return
        
        tree = self.decision_trees[tree_id]
        
        # Find node
        node = self._find_node(tree["root"], node_id)
        if node:
            # Initialize alternatives list if needed
            if "alternatives" not in node:
                node["alternatives"] = []
            
            # Add alternative
            alternative = {
                "name": name,
                "content": content,
                "confidence": confidence,
                "metadata": metadata or {}
            }
            
            node["alternatives"].append(alternative)
            
            # Update tree metadata
            tree["last_updated"] = datetime.datetime.now().isoformat()
            
            # Update visualizations if needed
            current_time = time.time()
            if current_time - self.last_update >= self.update_interval:
                self.update_visualizations()
                self.last_update = current_time
        else:
            logger.warning(f"Node {node_id} not found in tree {tree_id}")
    
    def update_visualizations(self):
        """Update all visualizations based on current decision trees."""
        if self.enable_html_output:
            self._generate_html_visualization()
    
    def _generate_html_visualization(self):
        """Generate HTML visualization of decision trees."""
        # Read template
        try:
            with open(self.html_template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except Exception as e:
            logger.error(f"Error reading HTML template: {e}")
            template = "<html><body><h1>Error loading template</h1></body></html>"
        
        # Generate agent options
        agent_options = ""
        for agent_id in self.agent_trees:
            agent_options += f'<option value="{agent_id}">{agent_id}</option>\n'
        
        # Generate tree options (first agent's trees)
        tree_options = ""
        first_agent = next(iter(self.agent_trees.keys()), None)
        if first_agent:
            for tree_id in self.agent_trees[first_agent]:
                tree_name = self.decision_trees[tree_id].get("name", tree_id)
                tree_options += f'<option value="{tree_id}">{tree_name}</option>\n'
        
        # Default tree info (first tree)
        first_tree_id = next(iter(self.decision_trees.keys()), "")
        first_tree = self.decision_trees.get(first_tree_id, {})
        
        tree_id = first_tree_id
        agent_id = first_tree.get("agent_id", "")
        created_at = first_tree.get("created_at", "")
        last_updated_at = first_tree.get("last_updated", "")
        node_count = first_tree.get("node_count", 0)
        tree_depth = first_tree.get("depth", 0)
        tree_status = first_tree.get("status", "Unknown")
        
        # Format dates if they exist
        if created_at:
            try:
                created_at = datetime.datetime.fromisoformat(created_at).strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                pass
                
        if last_updated_at:
            try:
                last_updated_at = datetime.datetime.fromisoformat(last_updated_at).strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                pass
                
        # Prepare tree data for JSON serialization
        serializable_trees = {}
        for tid, tree in self.decision_trees.items():
            serializable_trees[tid] = tree
            
        # Serialize agent trees
        serializable_agent_trees = {}
        for aid, trees in self.agent_trees.items():
            serializable_agent_trees[aid] = trees
        
        # Replace template placeholders
        html = template.replace("{{agent_options}}", agent_options)
        html = html.replace("{{tree_options}}", tree_options)
        html = html.replace("{{tree_id}}", tree_id)
        html = html.replace("{{agent_id}}", agent_id)
        html = html.replace("{{created_at}}", str(created_at))
        html = html.replace("{{last_updated_at}}", str(last_updated_at))
        html = html.replace("{{node_count}}", str(node_count))
        html = html.replace("{{tree_depth}}", str(tree_depth))
        html = html.replace("{{tree_status}}", tree_status)
        html = html.replace("{{tree_data}}", json.dumps(serializable_trees))
        html = html.replace("{{agent_trees}}", json.dumps(serializable_agent_trees))
        html = html.replace("{{last_updated}}", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Write HTML file
        output_path = os.path.join(self.output_dir, "decision_trees.html")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.debug(f"HTML visualization updated at {output_path}")
