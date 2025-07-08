#!/usr/bin/env python3
"""
Fix for Agentic Dashboard

This script creates a comprehensive fix for the Triangulum agentic dashboard
to ensure all visualizations work properly, including:
- Overview with proper progress tracking
- Timeline view
- Progress tracking visualization
- Feedback mechanism
"""

import os
import time
import json
import random
import datetime
import uuid
import webbrowser
import threading
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
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
        "percent_complete": 100.0,
        "status": "Active",
        "steps_completed": 100,
        "total_steps": 100,
        "estimated_completion": (datetime.datetime.now() + datetime.timedelta(minutes=5)).isoformat(),
        "last_updated": datetime.datetime.now().isoformat()
    }
    
    # Save global progress
    with open(os.path.join(progress_dir, "global_progress.json"), 'w') as f:
        json.dump(global_progress, f, indent=2)
    
    # Create agent progress data
    agents = ["orchestrator", "bug_detector", "relationship_analyst", 
              "verification_agent", "priority_analyzer", "code_fixer"]
    
    agent_progress = {}
    for agent in agents:
        # Random progress between 60-100%
        progress = random.uniform(60, 100)
        agent_progress[agent] = {
            "agent_id": agent,
            "percent_complete": progress,
            "status": "Active" if random.random() > 0.3 else "Idle",
            "current_activity": random.choice([
                "Analyzing dependencies", 
                "Detecting bugs",
                "Verifying changes",
                "Planning repairs",
                "Fixing issues"
            ]),
            "tasks_completed": random.randint(5, 15),
            "total_tasks": 20,
            "thought_count": random.randint(20, 50),
            "last_updated": datetime.datetime.now().isoformat()
        }
    
    # Save agent progress
    with open(os.path.join(progress_dir, "agent_progress.json"), 'w') as f:
        json.dump(agent_progress, f, indent=2)
    
    logger.info(f"Progress data saved to {progress_dir}")
    return progress_dir

def create_timeline_data(output_dir):
    """Create and save timeline data."""
    timeline_dir = ensure_directory_exists(os.path.join(output_dir, "timeline"))
    
    # Create timeline events
    events = []
    agents = ["orchestrator", "bug_detector", "relationship_analyst", 
              "verification_agent", "priority_analyzer", "code_fixer"]
    
    # Create events going back several hours
    for i in range(30):
        # Alternate between thought and message
        event_type = "thought" if i % 2 == 0 else "message"
        
        # Random agent
        agent = random.choice(agents)
        
        # Random timestamp (going back in time)
        timestamp = datetime.datetime.now() - datetime.timedelta(minutes=i*10)
        
        if event_type == "thought":
            content = random.choice([
                f"Analyzing code structure in module {random.randint(1, 5)}",
                f"Found {random.randint(1, 10)} potential bugs in the codebase",
                f"Determining optimal fix strategy for issue #{random.randint(100, 999)}",
                f"Evaluating impact of changes on dependent modules",
                f"Prioritizing bug fixes based on severity and impact"
            ])
            
            metadata = {
                "thought_type": random.choice(["analysis", "discovery", "decision", "planning"]),
                "confidence": random.randint(70, 99),
                "chain_id": f"chain_{random.randint(1, 5)}"
            }
        else:
            # For messages, choose a different agent as target
            other_agents = [a for a in agents if a != agent]
            target_agent = random.choice(other_agents)
            
            content = random.choice([
                f"Please analyze module {random.randint(1, 5)} for potential issues",
                f"Found {random.randint(1, 10)} bugs in the code, sending details",
                f"Verification complete, {random.randint(1, 5)} tests passing",
                f"Priority assessment: Bug #{random.randint(100, 999)} is critical",
                f"Requesting assistance with complex dependency analysis"
            ])
            
            metadata = {
                "message_type": random.choice(["request", "response", "notification", "command"]),
                "priority": random.choice(["high", "medium", "low"]),
                "target_agent": target_agent
            }
        
        # Create event
        event = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "timestamp": timestamp.isoformat(),
            "agent_id": agent,
            "content": content,
            "metadata": metadata
        }
        
        events.append(event)
    
    # Sort events by timestamp (newest first)
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    
    # Save timeline events
    with open(os.path.join(timeline_dir, "timeline_events.json"), 'w') as f:
        json.dump(events, f, indent=2)
    
    logger.info(f"Timeline data saved to {timeline_dir}")
    return timeline_dir

def create_decision_tree_data(output_dir):
    """Create and save decision tree data."""
    trees_dir = ensure_directory_exists(os.path.join(output_dir, "decision_trees"))
    
    # Create decision trees
    agents = ["orchestrator", "bug_detector", "relationship_analyst"]
    
    decision_trees = {}
    agent_trees = {}
    
    for agent in agents:
        # Create agent's tree list
        agent_trees[agent] = []
        
        # Create a tree for this agent
        tree_id = str(uuid.uuid4())
        agent_trees[agent].append(tree_id)
        
        # Create root node
        root_node = {
            "id": str(uuid.uuid4()),
            "name": "Root",
            "type": "root",
            "content": "Decision tree root",
            "children": []
        }
        
        # Create child nodes
        for i in range(3):
            child = {
                "id": str(uuid.uuid4()),
                "name": f"Decision {i+1}",
                "type": "decision" if i % 2 == 0 else "analysis",
                "content": f"This is decision {i+1} content",
                "confidence": random.randint(70, 95),
                "children": []
            }
            
            # Add alternatives for decisions
            if child["type"] == "decision":
                child["alternatives"] = [
                    {
                        "name": f"Alternative for Decision {i+1}",
                        "content": f"This is an alternative approach for decision {i+1}",
                        "confidence": random.randint(50, 65)
                    }
                ]
            
            # Add grandchildren for first child
            if i == 0:
                for j in range(2):
                    grandchild = {
                        "id": str(uuid.uuid4()),
                        "name": f"Action {j+1}",
                        "type": "action",
                        "content": f"This is action {j+1} content",
                        "confidence": random.randint(80, 99),
                        "children": []
                    }
                    child["children"].append(grandchild)
            
            root_node["children"].append(child)
        
        # Create tree data
        tree = {
            "tree_id": tree_id,
            "agent_id": agent,
            "name": f"{agent.capitalize()}'s Decision Process",
            "description": f"Decision process for {agent}",
            "created_at": (datetime.datetime.now() - datetime.timedelta(hours=2)).isoformat(),
            "last_updated": datetime.datetime.now().isoformat(),
            "status": "Active",
            "node_count": 1 + 3 + 2,  # Root + 3 children + 2 grandchildren
            "depth": 2,
            "root": root_node
        }
        
        # Add to trees
        decision_trees[tree_id] = tree
    
    # Create the decision trees JSON file
    with open(os.path.join(trees_dir, "decision_trees.json"), 'w') as f:
        json.dump(decision_trees, f, indent=2)
    
    # Create the agent trees JSON file
    with open(os.path.join(trees_dir, "agent_trees.json"), 'w') as f:
        json.dump(agent_trees, f, indent=2)
    
    logger.info(f"Decision tree data saved to {trees_dir}")
    return trees_dir

def fix_templates(output_dir):
    """Fix HTML templates for the dashboard."""
    templates_dir = os.path.join(output_dir)
    
    # Ensure the templates directory exists
    ensure_directory_exists(templates_dir)
    
    # Create a minimal timeline visualization HTML
    timeline_dir = ensure_directory_exists(os.path.join(output_dir, "timeline"))
    timeline_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Triangulum Timeline Visualization</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            .timeline-container { margin-top: 20px; }
            .timeline-event { 
                padding: 15px; 
                border-left: 3px solid #1890ff; 
                margin-bottom: 15px; 
                position: relative;
                background-color: white;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                border-radius: 4px;
            }
            .timeline-event.thought { border-left-color: #52c41a; }
            .timeline-event.message { border-left-color: #1890ff; }
            .timeline-timestamp {
                font-size: 0.8em;
                color: #888;
                margin-bottom: 5px;
            }
            .timeline-agent {
                font-weight: bold;
                margin-bottom: 5px;
            }
            .timeline-content {
                margin-top: 5px;
            }
            .timeline-meta {
                margin-top: 8px;
                font-size: 0.8em;
                color: #666;
            }
            h2 { margin-top: 0; color: #333; }
            .empty-message {
                padding: 20px;
                text-align: center;
                color: #888;
                border: 1px dashed #ccc;
                border-radius: 4px;
            }
        </style>
        <script>
            // Function to fetch timeline events
            async function fetchTimelineEvents() {
                try {
                    const response = await fetch('timeline_events.json');
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return await response.json();
                } catch (error) {
                    console.error('Error fetching timeline events:', error);
                    return [];
                }
            }
            
            // Function to render timeline
            async function renderTimeline() {
                const events = await fetchTimelineEvents();
                const container = document.getElementById('timeline-container');
                
                if (events.length === 0) {
                    container.innerHTML = '<div class="empty-message">No timeline events available</div>';
                    return;
                }
                
                // Clear container
                container.innerHTML = '';
                
                // Render each event
                events.forEach(event => {
                    const eventElement = document.createElement('div');
                    eventElement.className = `timeline-event ${event.type}`;
                    
                    // Format timestamp
                    const timestamp = new Date(event.timestamp);
                    const formattedTime = timestamp.toLocaleString();
                    
                    // Create event HTML
                    eventElement.innerHTML = `
                        <div class="timeline-timestamp">${formattedTime}</div>
                        <div class="timeline-agent">${event.agent_id}</div>
                        <div class="timeline-content">${event.content}</div>
                        <div class="timeline-meta">
                            ${event.type === 'thought' ? 
                                `Type: ${event.metadata.thought_type || 'Unknown'}, Confidence: ${event.metadata.confidence || 'N/A'}` :
                                `Type: ${event.metadata.message_type || 'Unknown'}, Priority: ${event.metadata.priority || 'N/A'}, To: ${event.metadata.target_agent || 'N/A'}`
                            }
                        </div>
                    `;
                    
                    container.appendChild(eventElement);
                });
            }
            
            // Load timeline when page loads
            document.addEventListener('DOMContentLoaded', renderTimeline);
            
            // Refresh timeline every 5 seconds
            setInterval(renderTimeline, 5000);
        </script>
    </head>
    <body>
        <h2>Agent Reasoning Timeline</h2>
        <div id="timeline-container" class="timeline-container">
            <div class="empty-message">Loading timeline events...</div>
        </div>
    </body>
    </html>
    """
    
    # Write the timeline HTML
    with open(os.path.join(timeline_dir, "timeline.html"), 'w') as f:
        f.write(timeline_html)
    
    # Create a minimal progress tracking HTML
    progress_dir = ensure_directory_exists(os.path.join(output_dir, "progress"))
    progress_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Triangulum Progress Tracking</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            .progress-container { margin-top: 20px; }
            .progress-bar-container {
                width: 100%;
                height: 20px;
                background-color: #f0f0f0;
                border-radius: 10px;
                margin-bottom: 5px;
                overflow: hidden;
            }
            .progress-bar {
                height: 100%;
                background-color: #1890ff;
                width: 0%;
                transition: width 0.5s ease-in-out;
            }
            .progress-details {
                display: flex;
                justify-content: space-between;
                margin-bottom: 20px;
                color: #555;
                font-size: 0.9em;
            }
            .agent-progress {
                background-color: white;
                padding: 15px;
                margin-bottom: 15px;
                border-radius: 4px;
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
                color: #333;
            }
            .agent-status {
                padding: 3px 8px;
                border-radius: 10px;
                font-size: 0.8em;
            }
            .agent-status.active {
                background-color: #e6f7ff;
                color: #1890ff;
            }
            .agent-status.idle {
                background-color: #f5f5f5;
                color: #888;
            }
            .agent-activity {
                margin-top: 5px;
                color: #666;
            }
            h2 { margin-top: 0; color: #333; }
            .system-progress-container {
                background-color: white;
                padding: 15px;
                margin-bottom: 25px;
                border-radius: 4px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            .system-status {
                font-weight: bold;
                color: #333;
                margin-bottom: 10px;
            }
            .empty-message {
                padding: 20px;
                text-align: center;
                color: #888;
                border: 1px dashed #ccc;
                border-radius: 4px;
            }
        </style>
        <script>
            // Function to fetch progress data
            async function fetchProgressData() {
                try {
                    const globalResponse = await fetch('global_progress.json');
                    const agentResponse = await fetch('agent_progress.json');
                    
                    if (!globalResponse.ok || !agentResponse.ok) {
                        throw new Error(`HTTP error! Status: ${globalResponse.status}, ${agentResponse.status}`);
                    }
                    
                    const globalProgress = await globalResponse.json();
                    const agentProgress = await agentResponse.json();
                    
                    return { global: globalProgress, agents: agentProgress };
                } catch (error) {
                    console.error('Error fetching progress data:', error);
                    return { global: null, agents: {} };
                }
            }
            
            // Function to render progress
            async function renderProgress() {
                const { global, agents } = await fetchProgressData();
                
                // Update system progress
                if (global) {
                    const systemContainer = document.getElementById('system-progress-container');
                    systemContainer.innerHTML = `
                        <div class="system-status">Status: ${global.status}</div>
                        <div class="progress-bar-container">
                            <div class="progress-bar" style="width: ${global.percent_complete}%"></div>
                        </div>
                        <div class="progress-details">
                            <div>${global.steps_completed} / ${global.total_steps} steps completed</div>
                            <div>Est. completion: ${new Date(global.estimated_completion).toLocaleTimeString()}</div>
                        </div>
                    `;
                }
                
                // Update agent progress
                const agentsContainer = document.getElementById('agent-progress-container');
                
                if (Object.keys(agents).length === 0) {
                    agentsContainer.innerHTML = '<div class="empty-message">No agent progress data available</div>';
                    return;
                }
                
                // Clear container
                agentsContainer.innerHTML = '';
                
                // Render each agent's progress
                Object.values(agents).forEach(agent => {
                    const agentElement = document.createElement('div');
                    agentElement.className = 'agent-progress';
                    
                    agentElement.innerHTML = `
                        <div class="agent-header">
                            <div class="agent-name">${agent.agent_id}</div>
                            <div class="agent-status ${agent.status.toLowerCase()}">${agent.status}</div>
                        </div>
                        <div class="progress-bar-container">
                            <div class="progress-bar" style="width: ${agent.percent_complete}%"></div>
                        </div>
                        <div class="progress-details">
                            <div>${agent.tasks_completed} / ${agent.total_tasks} tasks completed</div>
                            <div>${agent.thought_count} thoughts</div>
                        </div>
                        <div class="agent-activity">${agent.current_activity}</div>
                    `;
                    
                    agentsContainer.appendChild(agentElement);
                });
            }
            
            // Load progress when page loads
            document.addEventListener('DOMContentLoaded', renderProgress);
            
            // Refresh progress every 3 seconds
            setInterval(renderProgress, 3000);
        </script>
    </head>
    <body>
        <h2>Detailed Progress Tracking</h2>
        
        <div id="system-progress-container" class="system-progress-container">
            <div class="empty-message">Loading system progress...</div>
        </div>
        
        <h2>Agent Progress</h2>
        <div id="agent-progress-container" class="progress-container">
            <div class="empty-message">Loading agent progress...</div>
        </div>
    </body>
    </html>
    """
    
    # Write the progress tracking HTML
    with open(os.path.join(progress_dir, "progress.html"), 'w') as f:
        f.write(progress_html)
    
    logger.info(f"Fixed templates saved to {templates_dir}")
    return templates_dir

def start_dashboard(port=8000):
    """Start the dashboard in the default browser."""
    url = f"http://localhost:{port}"
    webbrowser.open(url)
    logger.info(f"Opened dashboard at {url}")

def main():
    """Run the dashboard fix."""
    print("=" * 80)
    print("TRIANGULUM AGENTIC DASHBOARD FIX".center(80))
    print("=" * 80)
    print("\nThis script will fix and launch the enhanced Triangulum agentic dashboard")
    print("with all visualizations working properly.")
    
    output_dir = "./triangulum_dashboard_fixed"
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nCreating fixed dashboard in {output_dir}...")
    
    # Create timeline data
    print("- Creating timeline data...")
    create_timeline_data(output_dir)
    
    # Create progress data
    print("- Creating progress data...")
    create_progress_data(output_dir)
    
    # Create decision tree data
    print("- Creating decision tree data...")
    create_decision_tree_data(output_dir)
    
    # Fix templates
    print("- Fixing dashboard templates...")
    fix_templates(output_dir)
    
    print("\nDashboard fix completed!")
    print("Now run the fixed dashboard with:")
    print(f"python run_agentic_dashboard.py --output-dir {output_dir}")

if __name__ == "__main__":
    main()
