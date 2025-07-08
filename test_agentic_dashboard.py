#!/usr/bin/env python3
"""
Test script for the Agentic Dashboard

This script creates a minimal version of the agentic dashboard with controlled
test data to help identify and fix issues with the visualization and data handling.
"""

import os
import time
import shutil
import datetime
import logging
import json

from triangulum_lx.monitoring.agentic_dashboard import AgenticDashboard
from triangulum_lx.monitoring.thought_chain_visualizer import ThoughtChainVisualizer
from triangulum_lx.monitoring.agent_network_visualizer import AgentNetworkVisualizer

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_data():
    """Create test data for dashboard visualizations."""
    # Create test output directory
    output_dir = "./dashboard_test"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Create test thought chains directory
    thought_chains_dir = os.path.join(output_dir, "thought_chains")
    os.makedirs(thought_chains_dir, exist_ok=True)
    
    # Create test agent network directory
    agent_network_dir = os.path.join(output_dir, "agent_network")
    os.makedirs(agent_network_dir, exist_ok=True)
    
    # Create test decision trees directory
    decision_trees_dir = os.path.join(output_dir, "decision_trees")
    os.makedirs(decision_trees_dir, exist_ok=True)
    
    # Create sample thought chains data
    thought_chains = {
        "chain_1": {
            "agent_id": "orchestrator",
            "thoughts": [
                {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "agent_id": "orchestrator",
                    "content": "Starting orchestration process",
                    "thought_type": "analysis"
                }
            ]
        }
    }
    
    # Create sample agent network data
    messages = [
        {
            "timestamp": datetime.datetime.now().isoformat(),
            "source_agent": "orchestrator",
            "target_agent": "bug_detector",
            "message_type": "command",
            "content": "Start bug detection"
        }
    ]
    
    # Save test data
    with open(os.path.join(thought_chains_dir, "thought_chains.json"), 'w') as f:
        json.dump(thought_chains, f, indent=2)
    
    with open(os.path.join(agent_network_dir, "messages.json"), 'w') as f:
        json.dump(messages, f, indent=2)
    
    return output_dir

def test_dashboard_update():
    """Test dashboard update functionality."""
    # Create test data and directories
    output_dir = create_test_data()
    
    # Create dashboard with test data
    dashboard = AgenticDashboard(
        output_dir=output_dir,
        update_interval=0.5,
        server_port=9000,  # Use a different port to avoid conflicts
        auto_open_browser=False
    )
    
    try:
        # Register some test data
        agents = ["orchestrator", "bug_detector", "code_fixer"]
        
        # Update global progress
        dashboard.update_global_progress(50.0, "Testing", 5, 10)
        
        # Update agent progress
        for i, agent_id in enumerate(agents):
            dashboard.update_agent_progress(
                agent_id=agent_id,
                percent_complete=(i + 1) * 30,
                status="Active" if i % 2 == 0 else "Idle",
                current_activity=f"Testing dashboard {i+1}",
                tasks_completed=i,
                total_tasks=10,
                thought_count=i*5
            )
        
        # Register thoughts - basic test
        dashboard.register_thought(
            agent_id="orchestrator",
            chain_id="test_chain_1",
            content="Test thought for dashboard",
            thought_type="analysis"
        )
        
        # Register message - basic test
        dashboard.register_message(
            source_agent="orchestrator",
            target_agent="bug_detector",
            message_type="command",
            content="Test message for dashboard"
        )
        
        # Create and populate decision tree - basic test
        tree_id = dashboard.create_decision_tree(
            agent_id="orchestrator",
            name="Test Decision Tree",
            description="Tree for dashboard testing"
        )
        
        node_id = dashboard.add_decision_node(
            tree_id=tree_id,
            parent_id=None,
            name="Root Node",
            content="Test decision node",
            confidence=90
        )
        
        # Force update dashboard
        logger.info("Forcing dashboard update...")
        dashboard.update_dashboard()
        logger.info("Dashboard update completed")
        
        # Print dashboard URL
        if dashboard.server:
            server_port = dashboard.server.server_address[1]
            print(f"Dashboard running at http://localhost:{server_port}/")
            print("Press Ctrl+C to exit.")
            
            # Keep running for a bit to monitor for errors
            for i in range(10):
                time.sleep(1)
                print(f"Monitoring for errors... ({i+1}/10)")
                # Force update to see if errors occur
                dashboard.update_dashboard()
        
    except Exception as e:
        logger.error(f"Error during dashboard test: {e}", exc_info=True)
    
    finally:
        # Clean up
        if dashboard:
            dashboard.stop()
        
        logger.info("Test completed")

if __name__ == "__main__":
    print("=" * 80)
    print("TESTING AGENTIC DASHBOARD".center(80))
    print("=" * 80)
    test_dashboard_update()
