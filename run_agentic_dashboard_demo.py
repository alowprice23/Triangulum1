#!/usr/bin/env python3
"""
Triangulum Agentic Dashboard Demo

This script demonstrates the enhanced agentic dashboard with
all visualizations working together: thought chains, agent network,
decision trees, timeline view, and progress tracking.
"""

import time
import random
import threading
import logging
import uuid
import sys
import os
import json
import datetime
from triangulum_lx.monitoring.agentic_dashboard import AgenticDashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_random_thought(dashboard, agent_id, agents):
    """Generate a random thought for an agent."""
    # Create a random thought chain ID if needed
    chain_id = f"chain_{random.randint(1, 5)}"
    
    # Random thought type
    thought_type = random.choice(["analysis", "decision", "discovery", "planning"])
    
    # Generate content based on thought type
    if thought_type == "analysis":
        content = f"Analyzing code structure in module {random.choice(['core', 'agents', 'tooling'])}. Found {random.randint(1, 10)} potential issues."
    elif thought_type == "decision":
        content = f"Decided to {random.choice(['refactor', 'optimize', 'test', 'document'])} the {random.choice(['class', 'function', 'module'])}."
    elif thought_type == "discovery":
        content = f"Discovered that {random.choice(['bug', 'performance issue', 'design flaw'])} is related to {random.choice(['threading', 'memory usage', 'algorithm choice'])}."
    else:  # planning
        content = f"Planning to implement {random.choice(['new feature', 'bug fix', 'optimization'])} in {random.randint(1, 5)} steps."
    
    # Add random metadata
    metadata = {
        "priority": random.choice(["high", "medium", "low"]),
        "confidence": random.randint(50, 100),
        "related_agents": random.sample(agents, k=min(2, len(agents))),
    }
    
    # Register the thought
    dashboard.register_thought(
        agent_id=agent_id,
        chain_id=chain_id,
        content=content,
        thought_type=thought_type,
        metadata=metadata
    )
    
    logger.debug(f"Registered thought for {agent_id}: {content}")
    return chain_id

def generate_random_message(dashboard, source_agent, agents):
    """Generate a random message between agents."""
    # Select a random target agent (different from source)
    other_agents = [a for a in agents if a != source_agent]
    if not other_agents:
        return
    
    target_agent = random.choice(other_agents)
    
    # Random message type
    message_type = random.choice(["request", "response", "notification", "command"])
    
    # Generate content based on message type
    if message_type == "request":
        content = f"Please {random.choice(['analyze', 'fix', 'review'])} {random.choice(['bug #', 'module ', 'function '])}{random.randint(1, 100)}"
    elif message_type == "response":
        content = f"Completed task. Found {random.randint(1, 10)} {random.choice(['issues', 'improvements', 'bugs'])}."
    elif message_type == "notification":
        content = f"System {random.choice(['warning', 'error', 'info'])}: {random.choice(['Memory usage high', 'CPU overload', 'New data available'])}"
    else:  # command
        content = f"{random.choice(['Start', 'Stop', 'Pause', 'Resume'])} {random.choice(['analysis', 'repair', 'verification'])} process"
    
    # Add random metadata
    metadata = {
        "priority": random.choice(["high", "medium", "low"]),
        "timestamp_sent": time.time(),
    }
    
    # Register the message
    dashboard.register_message(
        source_agent=source_agent,
        target_agent=target_agent,
        message_type=message_type,
        content=content,
        metadata=metadata
    )
    
    logger.debug(f"Registered message from {source_agent} to {target_agent}: {content}")

def create_decision_tree_example(dashboard, agent_id):
    """Create an example decision tree for an agent."""
    # Create a decision tree
    tree_name = f"{agent_id.capitalize()}'s Decision Process"
    tree_id = dashboard.create_decision_tree(
        agent_id=agent_id,
        name=tree_name,
        description=f"Decision process for {agent_id} when analyzing and fixing issues."
    )
    
    # Create root node
    root_id = dashboard.add_decision_node(
        tree_id=tree_id,
        parent_id=None,
        name="Initial Analysis",
        node_type="analysis",
        content="Analyzing system state and determining appropriate action",
        confidence=95
    )
    
    # First level children - different paths
    paths = [
        ("Bug Detection", "decision", "Determine if there are bugs in the code"),
        ("Performance Analysis", "analysis", "Evaluate system performance metrics"),
        ("Code Quality Review", "analysis", "Review code structure and patterns")
    ]
    
    child_ids = []
    for name, node_type, content in paths:
        child_id = dashboard.add_decision_node(
            tree_id=tree_id,
            parent_id=root_id,
            name=name,
            node_type=node_type,
            content=content,
            confidence=random.randint(70, 90)
        )
        child_ids.append(child_id)
        
        # Add some alternatives for decisions
        if node_type == "decision":
            dashboard.add_alternative(
                tree_id=tree_id,
                node_id=child_id,
                name=f"Alternative approach for {name}",
                content=f"An alternative way to handle {name.lower()}",
                confidence=random.randint(50, 65)
            )
    
    # Second level - add some children to first child
    if child_ids:
        actions = [
            ("Fix Critical Bugs", "action", "Apply patches for critical bugs first"),
            ("Document Issues", "action", "Create documentation for known issues"),
            ("Regression Testing", "action", "Run tests to verify fixes")
        ]
        
        for name, node_type, content in actions:
            dashboard.add_decision_node(
                tree_id=tree_id,
                parent_id=child_ids[0],
                name=name,
                node_type=node_type,
                content=content,
                confidence=random.randint(75, 95)
            )
    
    logger.info(f"Created decision tree for {agent_id}")
    return tree_id

def run_dashboard_demo():
    """Run the full dashboard demo."""
    print("=" * 80)
    print("TRIANGULUM AGENTIC DASHBOARD ENHANCED DEMO".center(80))
    print("=" * 80)
    print("\nThis demo showcases the enhanced Triangulum agentic dashboard with all visualizations.")
    print("The dashboard shows thought chains, agent network, decision trees, timeline, and progress tracking.")
    print("\nWaiting for the dashboard to initialize...")
    
    # Create dashboard with dynamic port selection
    port = random.randint(8100, 8999)  # Use a random port in this range to avoid conflicts
    dashboard = AgenticDashboard(
        output_dir="./agentic_dashboard_full_demo",
        update_interval=0.2,  # Faster updates for demo
        server_port=port,     # Use random port to avoid conflicts
        auto_open_browser=True
    )
    
    # Define agents
    agents = [
        "orchestrator",
        "bug_detector",
        "relationship_analyst",
        "verification_agent",
        "priority_analyzer",
        "code_fixer"
    ]
    
    try:
        # Initialize global progress
        dashboard.update_global_progress(0.0, "Initializing System", 0, 100)
        
        print("\nGenerating simulated agent activity...")
        
        # Create decision trees for some agents
        print("- Creating decision trees...")
        for agent_id in agents[:3]:  # Only create trees for first 3 agents
            tree_id = create_decision_tree_example(dashboard, agent_id)
            logger.info(f"Created decision tree for {agent_id}")
        
        # Force export of decision trees data to JSON
        trees_dir = os.path.join("./agentic_dashboard_full_demo", "decision_trees")
        os.makedirs(trees_dir, exist_ok=True)
        trees_path = os.path.join(trees_dir, "decision_trees.json")
        with open(trees_path, 'w', encoding='utf-8') as f:
            json.dump(dashboard.decision_tree_visualizer.decision_trees, f, indent=2)
        print(f"- Exported decision trees to {trees_path}")
        
        # Create and export timeline data
        timeline_dir = os.path.join("./agentic_dashboard_full_demo", "timeline")
        os.makedirs(timeline_dir, exist_ok=True)
        timeline_path = os.path.join(timeline_dir, "timeline_events.json")
        
        # Generate sample timeline events
        timeline_events = []
        for i in range(10):
            timestamp = datetime.datetime.now() - datetime.timedelta(minutes=i*5)
            event_type = "thought" if i % 2 == 0 else "message"
            agent_id = random.choice(agents)
            
            timeline_events.append({
                "id": str(uuid.uuid4()),
                "type": event_type,
                "timestamp": timestamp.isoformat(),
                "agent_id": agent_id,
                "content": f"Sample {event_type} #{i} from {agent_id}",
                "metadata": {
                    "priority": random.choice(["high", "medium", "low"]),
                }
            })
        
        with open(timeline_path, 'w', encoding='utf-8') as f:
            json.dump(timeline_events, f, indent=2)
        print(f"- Exported timeline events to {timeline_path}")
        
        # Simulate system progress over time
        total_steps = 100
        for step in range(1, total_steps + 1):
            time.sleep(0.1)  # Simulate work
            
            progress_percent = step / total_steps * 100
            status = "Initializing"
            if progress_percent < 20:
                status = "Initializing"
            elif progress_percent < 50:
                status = "Analyzing"
            elif progress_percent < 80:
                status = "Processing"
            else:
                status = "Finalizing"
                
            # Update global progress
            dashboard.update_global_progress(
                percent_complete=progress_percent,
                status=status,
                steps_completed=step,
                total_steps=total_steps
            )
            
            # Update agents (not every step, to make it more realistic)
            if step % 5 == 0:
                print(f"- Updating agent progress: Step {step}/{total_steps} ({int(progress_percent)}%)")
                for agent_id in agents:
                    # Each agent has slightly different progress
                    agent_progress = min(100, progress_percent + random.uniform(-10, 10))
                    agent_progress = max(0, agent_progress)
                    
                    # Randomize status
                    if step % 10 == 0 and random.random() < 0.3:
                        status = "Idle"
                    else:
                        status = "Active"
                    
                    # Random activity description
                    activities = [
                        f"Analyzing module {random.randint(1, 20)}",
                        f"Processing data batch {random.randint(1, 50)}",
                        f"Fixing bug #{random.randint(100, 999)}",
                        f"Optimizing function in {random.choice(['core', 'agents', 'tooling'])} module",
                        f"Running tests on patch #{random.randint(1, 100)}",
                        f"Reviewing code from {random.choice(agents)}"
                    ]
                    activity = random.choice(activities)
                    
                    # Update agent progress
                    dashboard.update_agent_progress(
                        agent_id=agent_id,
                        percent_complete=agent_progress,
                        status=status,
                        current_activity=activity,
                        tasks_completed=int(step / 10),
                        total_tasks=10,
                        thought_count=int(step / 5) + random.randint(-2, 2)
                    )
            
            # Generate thoughts and messages (less frequently)
            if step % 8 == 0:
                # Generate thoughts for random agents
                for _ in range(random.randint(1, 3)):
                    agent_id = random.choice(agents)
                    generate_random_thought(dashboard, agent_id, agents)
                
                # Generate messages between agents
                for _ in range(random.randint(1, 2)):
                    agent_id = random.choice(agents)
                    generate_random_message(dashboard, agent_id, agents)
        
        # Final update
        dashboard.update_global_progress(100.0, "Completed", total_steps, total_steps)
        
        print("\nDemo data generation complete!")
        print("The dashboard is now running with simulated agent activity.")
        print("Open the dashboard in your browser to explore all visualizations.")
        print(f"Dashboard URL: http://localhost:{port}/")
        
        # Keep refreshing data periodically
        refresh_count = 0
        print("\nKeeping dashboard alive. Press Ctrl+C to exit...")
        
        while True:
            time.sleep(5)
            refresh_count += 1
            
            # Add occasional new thoughts and messages to keep dashboard dynamic
            if refresh_count % 3 == 0:
                print(f"Refreshing dashboard data ({refresh_count})...")
                
                # Add a new thought for a random agent
                agent_id = random.choice(agents)
                generate_random_thought(dashboard, agent_id, agents)
                
                # Add a new message
                generate_random_message(dashboard, random.choice(agents), agents)
                
                # Force dashboard update
                dashboard.update_dashboard()
    
    except KeyboardInterrupt:
        print("\nStopping dashboard demo...")
    
    except Exception as e:
        logger.error(f"Error in dashboard demo: {e}", exc_info=True)
    
    finally:
        # Stop dashboard server
        print("Cleaning up...")
        dashboard.stop()
        print("Dashboard demo stopped.")

if __name__ == "__main__":
    run_dashboard_demo()
