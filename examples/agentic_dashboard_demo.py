#!/usr/bin/env python3
"""
Agentic Dashboard Demo

This script demonstrates how the agentic dashboard and progress tracker
work together to provide real-time visibility into the Triangulum system's
internal processing, including thought chains, agent communication, and
progress tracking.
"""

import os
import sys
import time
import random
import threading
import logging
import datetime
import json
from typing import Dict, List, Any, Optional

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.monitoring.agentic_dashboard import AgenticDashboard
from triangulum_lx.monitoring.progress_tracker import ProgressTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define simulated repair task
REPAIR_TASK = {
    "files": [
        "module_a.py",
        "module_b.py",
        "module_c.py",
        "utils.py",
        "config.py"
    ],
    "bugs": [
        {"file": "module_a.py", "line": 42, "severity": "high", "description": "Null pointer exception"},
        {"file": "module_b.py", "line": 17, "severity": "medium", "description": "Memory leak"},
        {"file": "module_c.py", "line": 123, "severity": "low", "description": "Inefficient algorithm"},
        {"file": "utils.py", "line": 56, "severity": "high", "description": "Race condition"},
        {"file": "config.py", "line": 29, "severity": "medium", "description": "Hardcoded credentials"}
    ]
}

class SimulatedAgent:
    """
    Simulates a Triangulum agent performing work and reporting progress.
    """
    
    def __init__(self, agent_id: str, dashboard: AgenticDashboard, role: str, work_items: List[Dict]):
        """
        Initialize the simulated agent.
        
        Args:
            agent_id: ID of the agent
            dashboard: The agentic dashboard instance
            role: The role of the agent (determines behavior)
            work_items: List of work items for the agent to process
        """
        self.agent_id = agent_id
        self.dashboard = dashboard
        self.role = role
        self.work_items = work_items
        self.total_items = len(work_items)
        self.completed_items = 0
        self.tracker = ProgressTracker(
            dashboard=dashboard,
            agent_id=agent_id,
            enable_local_logging=True,
            log_dir="./triangulum_demo_logs"
        )
        self.chain_id = f"{agent_id}_chain_{random.randint(1000, 9999)}"
        self.active = False
        self.thread = None
    
    def start(self):
        """Start the agent's processing thread."""
        if self.active:
            return
        
        self.active = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Agent {self.agent_id} started")
    
    def stop(self):
        """Stop the agent's processing thread."""
        self.active = False
        if self.thread:
            self.thread.join(timeout=1.0)
        logger.info(f"Agent {self.agent_id} stopped")
    
    def _run(self):
        """Main processing loop for the agent."""
        self.tracker.update_progress(
            percent_complete=0.0,
            status="Active",
            current_activity=f"Starting {self.role} tasks",
            tasks_completed=0,
            total_tasks=self.total_items
        )
        
        self.tracker.record_thought(
            f"Initializing {self.role} for {self.total_items} items",
            thought_type="initialization",
            chain_id=self.chain_id
        )
        
        # Process each work item
        for i, item in enumerate(self.work_items):
            if not self.active:
                break
            
            # Simulate varying processing times
            process_time = random.uniform(0.5, 2.0)
            steps = random.randint(3, 7)
            
            for step in range(steps):
                if not self.active:
                    break
                
                # Update progress
                percent = (i * 100 / self.total_items) + (step * 100 / steps / self.total_items)
                self.tracker.update_progress(
                    percent_complete=min(99.0, percent),  # Cap at 99% until complete
                    status="Active",
                    current_activity=self._generate_activity(item, step),
                    tasks_completed=self.completed_items,
                    total_tasks=self.total_items
                )
                
                # Record thoughts based on role and step
                self._generate_thoughts(item, step)
                
                # Send messages to other agents
                self._send_messages(item, step)
                
                # Simulate work
                time.sleep(process_time / steps)
            
            # Mark item as completed
            self.completed_items += 1
        
        # Final update
        self.tracker.update_progress(
            percent_complete=100.0,
            status="Completed" if self.completed_items == self.total_items else "Partial",
            current_activity=f"Completed {self.role} tasks",
            tasks_completed=self.completed_items,
            total_tasks=self.total_items
        )
        
        self.tracker.record_thought(
            f"Finished processing {self.completed_items}/{self.total_items} items",
            thought_type="completion",
            chain_id=self.chain_id
        )
        
        self.active = False
    
    def _generate_activity(self, item: Dict, step: int) -> str:
        """Generate a description of the current activity."""
        if self.role == "bug_detector":
            activities = [
                f"Scanning {item['file']} for bugs",
                f"Analyzing code around line {item['line']}",
                f"Detecting bug pattern in {item['file']}",
                f"Verifying {item['severity']} bug at line {item['line']}",
                f"Documenting bug: {item['description']}"
            ]
        elif self.role == "relationship_analyst":
            activities = [
                f"Mapping dependencies for {item['file']}",
                f"Analyzing imports in {item['file']}",
                f"Checking references to line {item['line']}",
                f"Evaluating impact of changes to {item['file']}",
                f"Building relationship graph for {item['file']}"
            ]
        elif self.role == "verification":
            activities = [
                f"Verifying fix for {item['file']}",
                f"Running tests for {item['file']}",
                f"Checking for regressions after fixing line {item['line']}",
                f"Validating fix for: {item['description']}",
                f"Finalizing verification of {item['file']}"
            ]
        else:  # Default for orchestrator, etc.
            activities = [
                f"Processing {item['file']}",
                f"Coordinating fix for line {item['line']}",
                f"Planning repair strategy for {item['severity']} bug",
                f"Assigning agents to fix: {item['description']}",
                f"Tracking progress on {item['file']}"
            ]
        
        return activities[min(step, len(activities) - 1)]
    
    def _generate_thoughts(self, item: Dict, step: int):
        """Generate thoughts based on agent role and step."""
        # Different thought patterns based on role
        if self.role == "bug_detector":
            if step == 0:
                self.tracker.record_thought(
                    f"Starting analysis of {item['file']}",
                    thought_type="analysis",
                    chain_id=self.chain_id
                )
            elif step == 1:
                self.tracker.record_thought(
                    f"Examining code patterns around line {item['line']}",
                    thought_type="analysis",
                    chain_id=self.chain_id
                )
            elif step == 2:
                self.tracker.record_thought(
                    f"Detected potential {item['severity']} bug: {item['description']}",
                    thought_type="discovery",
                    chain_id=self.chain_id
                )
            elif step == 3:
                self.tracker.record_thought(
                    f"Bug confirmed: {item['description']} at line {item['line']}",
                    thought_type="decision",
                    chain_id=self.chain_id
                )
        
        elif self.role == "relationship_analyst":
            if step == 0:
                self.tracker.record_thought(
                    f"Mapping import structure of {item['file']}",
                    thought_type="analysis",
                    chain_id=self.chain_id
                )
            elif step == 1:
                self.tracker.record_thought(
                    f"Analyzing code references to and from line {item['line']}",
                    thought_type="analysis",
                    chain_id=self.chain_id
                )
            elif step == 2:
                deps = random.randint(1, 4)
                self.tracker.record_thought(
                    f"Found {deps} dependent modules that may be affected by changes to {item['file']}",
                    thought_type="discovery",
                    chain_id=self.chain_id
                )
            elif step == 3:
                impact = random.choice(["Low", "Medium", "High"])
                self.tracker.record_thought(
                    f"{impact} impact: Changes to fix {item['description']} will affect multiple modules",
                    thought_type="assessment",
                    chain_id=self.chain_id
                )
        
        elif self.role == "verification":
            if step == 0:
                self.tracker.record_thought(
                    f"Preparing test environment for {item['file']}",
                    thought_type="preparation",
                    chain_id=self.chain_id
                )
            elif step == 1:
                self.tracker.record_thought(
                    f"Running test suite after fix to line {item['line']}",
                    thought_type="analysis",
                    chain_id=self.chain_id
                )
            elif step == 2:
                tests = random.randint(5, 20)
                passed = random.randint(0, tests)
                self.tracker.record_thought(
                    f"Test results: {passed}/{tests} tests passed after fixing {item['description']}",
                    thought_type="assessment",
                    chain_id=self.chain_id
                )
            elif step == 3:
                if random.random() > 0.2:  # 80% success rate
                    self.tracker.record_thought(
                        f"Fix verified: {item['description']} is resolved without regressions",
                        thought_type="decision",
                        chain_id=self.chain_id
                    )
                else:
                    self.tracker.record_thought(
                        f"Fix requires revision: {item['description']} patch caused regression",
                        thought_type="decision",
                        chain_id=self.chain_id
                    )
        
        elif self.role == "orchestrator":
            if step == 0:
                self.tracker.record_thought(
                    f"Planning repair strategy for {item['file']}",
                    thought_type="planning",
                    chain_id=self.chain_id
                )
            elif step == 1:
                self.tracker.record_thought(
                    f"Prioritizing {item['severity']} bug: {item['description']}",
                    thought_type="decision",
                    chain_id=self.chain_id
                )
            elif step == 2:
                agents = ["bug_detector", "relationship_analyst", "code_fixer"]
                random.shuffle(agents)
                self.tracker.record_thought(
                    f"Assigning agents: {agents[0]} and {agents[1]} to collaborate on fixing {item['file']}",
                    thought_type="coordination",
                    chain_id=self.chain_id
                )
            elif step == 3:
                complete = random.randint(10, 90)
                self.tracker.record_thought(
                    f"Repair progress for {item['file']} is {complete}% complete",
                    thought_type="monitoring",
                    chain_id=self.chain_id
                )
    
    def _send_messages(self, item: Dict, step: int):
        """Send messages to other agents based on role and step."""
        # Only send messages occasionally
        if random.random() > 0.3:
            return
        
        # Pick a target agent that's not us
        target_agents = [
            "orchestrator",
            "bug_detector",
            "relationship_analyst", 
            "verification",
            "priority_analyzer",
            "code_fixer"
        ]
        target_agents.remove(self.agent_id)
        target = random.choice(target_agents)
        
        # Generate message content based on role
        if self.role == "bug_detector":
            message_type = "notification"
            content = f"Bug detected in {item['file']} at line {item['line']}: {item['description']}"
        elif self.role == "relationship_analyst":
            message_type = "analysis"
            content = f"Impact analysis for {item['file']}: changes may affect {random.randint(1, 5)} other modules"
        elif self.role == "verification":
            message_type = "verification"
            content = f"Fix for {item['description']} in {item['file']} has been verified"
        elif self.role == "orchestrator":
            message_type = "command"
            content = f"Please prioritize fixing {item['description']} in {item['file']}"
        else:
            message_type = "update"
            content = f"Working on {item['file']} line {item['line']}"
        
        # Send the message
        self.tracker.send_message(
            target_agent=target,
            content=content,
            message_type=message_type
        )


def run_demo(dashboard_dir: str = "./triangulum_dashboard_demo", duration: int = 60):
    """
    Run the agentic dashboard demo.
    
    Args:
        dashboard_dir: Directory to store dashboard outputs
        duration: Duration of the demo in seconds
    """
    # Create the dashboard
    dashboard = AgenticDashboard(
        output_dir=dashboard_dir,
        update_interval=0.5,
        enable_server=True,
        server_port=8081,
        auto_open_browser=True
    )
    
    # Create templates directory if needed
    templates_dir = os.path.join(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))), 
        "triangulum_lx", "monitoring", "templates"
    )
    os.makedirs(templates_dir, exist_ok=True)
    
    # Create simulated agents
    agents = []
    
    # Distribute bugs among agents
    bugs = REPAIR_TASK["bugs"]
    
    # Create orchestrator
    orchestrator = SimulatedAgent(
        agent_id="orchestrator",
        dashboard=dashboard,
        role="orchestrator",
        work_items=bugs  # Orchestrator oversees all bugs
    )
    agents.append(orchestrator)
    
    # Create bug detector
    bug_detector = SimulatedAgent(
        agent_id="bug_detector",
        dashboard=dashboard,
        role="bug_detector",
        work_items=bugs  # Bug detector analyzes all bugs
    )
    agents.append(bug_detector)
    
    # Create relationship analyst
    relationship_analyst = SimulatedAgent(
        agent_id="relationship_analyst",
        dashboard=dashboard,
        role="relationship_analyst",
        work_items=bugs  # Relationship analyst assesses impact of all bugs
    )
    agents.append(relationship_analyst)
    
    # Create verification agent
    verification = SimulatedAgent(
        agent_id="verification",
        dashboard=dashboard,
        role="verification",
        work_items=bugs  # Verification checks all fixes
    )
    agents.append(verification)
    
    # Initialize global progress
    dashboard.update_global_progress(
        percent_complete=0.0,
        status="Initializing",
        steps_completed=0,
        total_steps=len(bugs)
    )
    
    try:
        # Start all agents
        logger.info("Starting simulated agents...")
        for agent in agents:
            agent.start()
            time.sleep(0.5)  # Stagger start times
        
        # Monitor progress and update global status
        start_time = time.time()
        while time.time() - start_time < duration and any(agent.active for agent in agents):
            # Calculate overall progress from the perspective of the orchestrator
            orchestrator_progress = orchestrator.completed_items
            total_tasks = orchestrator.total_items
            if total_tasks > 0:
                percent_complete = (orchestrator_progress * 100.0) / total_tasks
            else:
                percent_complete = 0.0
            
            # Determine overall status
            if all(not agent.active for agent in agents):
                status = "Completed"
                percent_complete = 100.0
                orchestrator_progress = total_tasks
            else:
                status = "Processing"
            
            # Update global progress
            dashboard.update_global_progress(
                percent_complete=percent_complete,
                status=status,
                steps_completed=orchestrator_progress,
                total_steps=total_tasks
            )
            
            # Wait a bit
            time.sleep(1.0)
        
        # Final update
        total_tasks = sum(agent.total_items for agent in agents)
        completed_tasks = sum(agent.completed_items for agent in agents)
        if total_tasks > 0:
            percent_complete = (completed_tasks * 100.0) / total_tasks
        else:
            percent_complete = 100.0
        
        dashboard.update_global_progress(
            percent_complete=percent_complete,
            status="Completed",
            steps_completed=completed_tasks,
            total_steps=total_tasks
        )
        
        logger.info(f"Demo completed. {completed_tasks}/{total_tasks} tasks processed.")
        
        # Keep the dashboard running until interrupted
        logger.info("Dashboard running. Press Ctrl+C to exit...")
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("\nStopping demo...")
    
    finally:
        # Stop all agents
        for agent in agents:
            agent.stop()
        
        # Stop the dashboard
        dashboard.stop()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Triangulum Agentic Dashboard Demo")
    parser.add_argument(
        "--dashboard-dir",
        type=str,
        default="./triangulum_dashboard_demo",
        help="Directory to store dashboard outputs"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=120,
        help="Duration of the demo in seconds"
    )
    
    args = parser.parse_args()
    
    try:
        run_demo(
            dashboard_dir=args.dashboard_dir,
            duration=args.duration
        )
    except Exception as e:
        logger.exception(f"Error running demo: {e}")
        sys.exit(1)
