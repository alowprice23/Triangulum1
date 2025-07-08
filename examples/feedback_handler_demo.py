#!/usr/bin/env python3
"""
Feedback Handler Demo

This script demonstrates the real-time feedback mechanism, allowing users
to interact with and adjust agent reasoning.
"""

import os
import time
import json
import argparse
import webbrowser
from triangulum_lx.monitoring.agentic_dashboard import AgenticDashboard

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Run Feedback Handler Demo')
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./feedback_demo',
        help='Directory for dashboard outputs'
    )
    
    parser.add_argument(
        '--auto-open',
        action='store_true',
        help='Automatically open dashboard in browser'
    )
    
    return parser.parse_args()

def agent_feedback_callback(feedback: dict):
    """
    Callback function to process feedback for an agent.
    """
    print(f"Agent received feedback: {feedback}")
    # In a real application, this would trigger a change in the agent's behavior
    # For example, adjusting its strategy, re-evaluating a decision, etc.

def run_demo(output_dir: str, auto_open: bool = False):
    """
    Run the feedback handler demo.
    
    Args:
        output_dir: Directory for dashboard outputs
        auto_open: Whether to automatically open the dashboard in a browser
    """
    # Create the dashboard with random port to avoid conflicts
    port = 8000 + (os.getpid() % 1000)  # Use process ID to generate a unique port
    dashboard = AgenticDashboard(
        output_dir=output_dir,
        update_interval=1.0,
        server_port=port,
        auto_open_browser=auto_open
    )
    
    # Define agents
    agents = [
        "orchestrator",
        "bug_detector",
        "code_fixer"
    ]
    
    # Register feedback callbacks for each agent
    for agent_id in agents:
        dashboard.feedback_handler.register_feedback_callback(agent_id, agent_feedback_callback)
    
    # Create decision trees for agents
    def create_decision_tree_for_agent(agent_id):
        """Create a sample decision tree for an agent."""
        tree_id = dashboard.create_decision_tree(
            agent_id=agent_id,
            name=f"{agent_id.capitalize()} Decision Process",
            description=f"Sample decision tree for {agent_id}"
        )
        
        # Add root node
        root_id = dashboard.add_decision_node(
            tree_id=tree_id,
            parent_id=None,
            name="Initial Analysis",
            node_type="analysis",
            content="Analyzing system state and determining appropriate action",
            confidence=90
        )
        
        # Add child nodes
        child_id = dashboard.add_decision_node(
            tree_id=tree_id,
            parent_id=root_id,
            name="Implementation Strategy",
            node_type="decision",
            content="Deciding on the best approach to fix the issue",
            confidence=85
        )
        
        # Add an alternative
        dashboard.add_alternative(
            tree_id=tree_id,
            node_id=child_id,
            name="Alternative Approach",
            content="An alternative implementation strategy",
            confidence=70
        )
        
        return tree_id
    
    # Create decision trees for each agent
    for agent_id in agents:
        create_decision_tree_for_agent(agent_id)
    
    # Force immediate export of decision trees to JSON file
    trees_path = os.path.join(output_dir, "decision_trees", "decision_trees.json")
    os.makedirs(os.path.join(output_dir, "decision_trees"), exist_ok=True)
    
    # Export decision trees to JSON
    with open(trees_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard.decision_tree_visualizer.decision_trees, f, indent=2)
    
    print(f"Decision trees exported to {trees_path}")
    
    # Simulate agent activity
    print("Starting feedback handler demo...")
    
    try:
        for step in range(1, 61):
            time.sleep(1)
            
            # Update agent progress
            for agent_id in agents:
                dashboard.update_agent_progress(
                    agent_id=agent_id,
                    percent_complete=(step / 60) * 100,
                    status="Active",
                    current_activity=f"Processing step {step}"
                )
            
            # Occasionally register thoughts and messages
            if step % 5 == 0:
                dashboard.register_thought(
                    agent_id="bug_detector",
                    chain_id="bug_analysis",
                    content=f"Analyzing bug at step {step}"
                )
                dashboard.register_message(
                    source_agent="bug_detector",
                    target_agent="orchestrator",
                    message_type="status_update",
                    content=f"Analysis at {step}% complete"
                )
        
        print("\nDemo running. Open the dashboard to provide feedback.")
        print("Press Ctrl+C to exit.")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping feedback handler demo...")
        
    finally:
        print("\nStopping feedback handler demo...")
        dashboard.stop()
        print("Feedback handler demo stopped.")

def main():
    """Run the feedback handler demo."""
    args = parse_arguments()
    
    print("=" * 80)
    print("TRIANGULUM FEEDBACK HANDLER DEMO".center(80))
    print("=" * 80)
    print("\nThis demo showcases the real-time feedback mechanism, allowing you to")
    print("interact with agents through the dashboard.")
    
    run_demo(args.output_dir, args.auto_open)

if __name__ == "__main__":
    main()
