#!/usr/bin/env python3
"""
Triangulum Agentic Dashboard Launcher

This script launches the Triangulum Agentic System Dashboard, which provides
real-time visualization and monitoring of the agentic system's internal processing,
including thought chains, agent communication, and progress tracking.
"""

import os
import sys
import time
import argparse
import logging
import threading
import random
import datetime
from typing import Dict, List, Any, Optional

from triangulum_lx.monitoring.agentic_dashboard import AgenticDashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Triangulum Agentic Dashboard")
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./triangulum_dashboard",
        help="Directory to store dashboard outputs"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to use for the dashboard HTTP server"
    )
    
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open a browser window"
    )
    
    parser.add_argument(
        "--demo-mode",
        action="store_true",
        help="Run in demo mode with simulated agent activity"
    )
    
    parser.add_argument(
        "--update-interval",
        type=float,
        default=0.5,
        help="How frequently to update visualizations (seconds)"
    )
    
    return parser.parse_args()

def run_dashboard_demo(dashboard: AgenticDashboard):
    """
    Run a demonstration of the dashboard with simulated agent activity.
    
    Args:
        dashboard: The agentic dashboard instance
    """
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
        logger.info("Starting dashboard demo...")
        
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
        
        logger.info("Dashboard demo running. Press Ctrl+C to exit...")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("\nStopping dashboard demo...")

def connect_to_triangulum_agents(dashboard: AgenticDashboard):
    """
    Connect the dashboard to the Triangulum agents to monitor live activity.
    
    Args:
        dashboard: The agentic dashboard instance
    """
    try:
        from triangulum_dashboard_backend_connector import MessageBusDashboardListener
        from triangulum_integrated_dashboard_compact import get_global_message_bus

        message_bus = get_global_message_bus()
        
        if message_bus:
            listener = MessageBusDashboardListener(message_bus, dashboard)
            logger.info("Dashboard connected to Triangulum agents via message bus.")
            return True
        else:
            logger.error("Failed to get message bus instance.")
            return False
            
    except ImportError as e:
        logger.error(f"Failed to import dashboard connector: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while connecting to Triangulum agents: {e}")
        return False

def create_dashboard_templates(dashboard_dir: str):
    """
    Create any necessary template directories for the dashboard.
    
    Args:
        dashboard_dir: The dashboard output directory
    """
    # Create templates directory
    templates_dir = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 
        "triangulum_lx", "monitoring", "templates"
    )
    os.makedirs(templates_dir, exist_ok=True)
    
    # Create dashboard.html template if it doesn't exist
    dashboard_template = os.path.join(templates_dir, "dashboard.html")
    if not os.path.exists(dashboard_template):
        logger.info(f"Creating dashboard template at {dashboard_template}")
        
        # Copy the template from the main dashboard HTML
        # In a real implementation, we would have a template file to copy from
        # For now, we'll just create a minimal template
        with open(dashboard_template, 'w', encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Triangulum Agentic System Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <div class="dashboard-container">
        <div class="dashboard-header">
            <div class="dashboard-title">Triangulum Agentic System Dashboard</div>
            <div class="dashboard-timestamp">Last updated: {{last_updated}}</div>
        </div>
        
        <!-- Dashboard content goes here -->
        
    </div>
</body>
</html>
""")

def main():
    """Main entry point for the dashboard launcher."""
    args = parse_arguments()
    
    try:
        # Create template directories
        create_dashboard_templates(args.output_dir)
        
        # Create and start the dashboard
        dashboard = AgenticDashboard(
            output_dir=args.output_dir,
            update_interval=args.update_interval,
            enable_server=True,
            server_port=args.port,
            auto_open_browser=not args.no_browser
        )
        
        if args.demo_mode:
            # Run in demo mode with simulated agent activity
            run_dashboard_demo(dashboard)
        else:
            # Connect to real Triangulum agents
            if connect_to_triangulum_agents(dashboard):
                logger.info(f"Dashboard running at http://localhost:{args.port}/")
                logger.info("Press Ctrl+C to exit...")
                
                # Keep running until interrupted
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("\nStopping dashboard...")
            else:
                logger.error("Failed to connect to Triangulum agents")
                return 1
    
    except KeyboardInterrupt:
        logger.info("\nDashboard operation canceled")
    except Exception as e:
        logger.exception(f"Error running dashboard: {e}")
        return 1
    finally:
        # Ensure dashboard is properly stopped
        if 'dashboard' in locals():
            dashboard.stop()
            logger.info("Dashboard stopped")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
