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

# Updated imports
from triangulum_lx.core.engine import TriangulumEngine # ComponentStatus not directly used here
from triangulum_lx.monitoring.agentic_dashboard import AgenticDashboard # Used for type hint for dashboard instance

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


def run_demo(dashboard_dir: str = "./triangulum_dashboard_final_consolidated", duration: int = 60):
    """
    Run the agentic dashboard demo using TriangulumEngine.
    
    Args:
        dashboard_dir: Directory to store dashboard outputs
        duration: Duration of the demo in seconds
    """
    logger.info(f"Starting Agentic Dashboard Demo. Output will be in: {dashboard_dir}")
    logger.info(f"Demo will run for approximately {duration} seconds.")

    # --- Setup Triangulum Engine with Dashboard Enabled ---
    # This configuration would typically come from a file like config/triangulum_config.json
    engine_config = {
        "llm": {
            "default_provider": "mock_provider",
            "providers": {
                "mock_provider": {
                    "api_key_env_var": "MOCK_API_KEY", # llm_config expects this structure
                    "default_model": "mock_model"
                }
            },
            "agent_model_mapping_defaults": {}, # Empty is fine if no agents use LLMs
            "generation_params": {},
            "resilience": {},
            "routing_rules": {}
        },
        "agents": {}, # No actual agents being initialized by the engine itself for this demo
        "dashboard": { # Configuration for the AgenticDashboard component
            "output_dir": dashboard_dir,
            "enable_server": True,
            "server_port": 8081,
            "auto_open_browser": True,
            "update_interval": 0.5 # seconds
        },
        "logging": {"metrics_dir": os.path.join(dashboard_dir, "metrics_data")} # Example if metrics are needed
    }

    # Mock os.getenv for the dummy provider if llm_config tries to read it during engine init
    original_getenv = os.getenv
    def mock_getenv_for_engine(var_name, default=None):
        if var_name == "MOCK_API_KEY": # Corresponds to api_key_env_var in engine_config
            return "dummy_key_for_mock_provider"
        # Allow other env vars to pass through for potential system settings
        return original_getenv(var_name, default)
    os.getenv = mock_getenv_for_engine
    
    engine: Optional[TriangulumEngine] = None
    try:
        engine = TriangulumEngine(config=engine_config)
        logger.info("Initializing Triangulum Engine...")
        if not engine.initialize():
            logger.error("Failed to initialize Triangulum Engine. Aborting demo.")
            return
        logger.info("Triangulum Engine initialized.")

        dashboard: Optional[AgenticDashboard] = engine.get_dashboard()
        if not dashboard:
            logger.error("Failed to get dashboard instance from engine. Aborting demo.")
            return
        logger.info(f"Dashboard instance obtained from engine. Type: {type(dashboard)}")

    except Exception as e:
        logger.exception(f"Error during engine setup: {e}")
        return
    finally:
        os.getenv = original_getenv # Crucial to restore original os.getenv

    # --- Original Demo Logic (now using engine-provided dashboard) ---
    simulated_agents: List[SimulatedAgent] = []
    bugs = REPAIR_TASK["bugs"]
    
    orchestrator = SimulatedAgent("orchestrator", dashboard, "orchestrator", bugs)
    bugs = REPAIR_TASK["bugs"] # Defined globally in the script
    
    # Create simulated agents, passing the engine-managed dashboard instance
    orchestrator = SimulatedAgent("orchestrator", dashboard, "orchestrator", bugs)
    simulated_agents.append(orchestrator)
    bug_detector = SimulatedAgent("bug_detector", dashboard, "bug_detector", bugs)
    simulated_agents.append(bug_detector)
    relationship_analyst = SimulatedAgent("relationship_analyst", dashboard, "relationship_analyst", bugs)
    simulated_agents.append(relationship_analyst)
    verification = SimulatedAgent("verification", dashboard, "verification", bugs)
    simulated_agents.append(verification)
    
    # Initialize global progress on the dashboard
    dashboard.update_global_progress(0.0, "Initializing", 0, len(bugs)) # Assuming len(bugs) is total steps
    
    try:
        logger.info("Starting simulated agents...")
        for sa in simulated_agents: # Use a different variable name
            sa.start()
            time.sleep(0.5) # Stagger agent starts
        
        demo_start_time = time.time()
        while time.time() - demo_start_time < duration and any(sa.active for sa in simulated_agents):
            # Global progress calculation based on orchestrator's view
            orch_progress = orchestrator.completed_items
            orch_total_tasks = orchestrator.total_items

            current_global_percent = (orch_progress * 100.0) / orch_total_tasks if orch_total_tasks > 0 else 0.0
            current_global_status = "Processing"
            
            if all(not sa.active for sa in simulated_agents): # If all simulated agents are done
                current_global_status = "Completed"
                current_global_percent = 100.0
                orch_progress = orch_total_tasks # Ensure steps completed matches total
            
            dashboard.update_global_progress(
                percent_complete=current_global_percent,
                status=current_global_status,
                steps_completed=orch_progress,
                total_steps=orch_total_tasks
            )
            time.sleep(1.0) # Update global progress every second
        
        # Final global progress update
        final_orch_progress = orchestrator.completed_items
        final_orch_total_tasks = orchestrator.total_items
        final_global_percent = (final_orch_progress * 100.0) / final_orch_total_tasks if final_orch_total_tasks > 0 else 100.0
        
        dashboard.update_global_progress(
            percent_complete=final_global_percent,
            status="Completed" if final_global_percent >= 100.0 else "Timed Out",
            steps_completed=final_orch_progress,
            total_steps=final_orch_total_tasks
        )
        logger.info(f"Demo run loop finished. Orchestrator processed {final_orch_progress}/{final_orch_total_tasks} tasks.")
        
        if engine_config.get("dashboard", {}).get("enable_server"):
            logger.info("Dashboard server is running. Press Ctrl+C to exit and shutdown engine.")
            while True: # Keep the main thread alive so server thread can run
                time.sleep(1)
        else:
            logger.info("Demo finished (dashboard server was not enabled).")

    except KeyboardInterrupt:
        logger.info("\nUser interrupted. Stopping demo...")
    
    finally:
        logger.info("Shutting down simulated agents...")
        for sa in simulated_agents:
            sa.stop()
        
        if engine: # Ensure engine was successfully initialized
            logger.info("Shutting down Triangulum Engine...")
            engine.shutdown()
        logger.info("Demo has concluded.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Triangulum Agentic Dashboard Demo")
    parser.add_argument(
        "--dashboard-dir",
        type=str,
        default="./triangulum_dashboard_final_consolidated",
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
