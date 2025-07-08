#!/usr/bin/env python3
"""
Agentic Dashboard Demo with Decision Trees

This script demonstrates the enhanced agentic dashboard with decision tree visualization,
showcasing how agents can make decisions with alternatives and visualize their reasoning
process in real-time.
"""

import time
import random
import threading
from typing import Dict, List, Optional

from triangulum_lx.monitoring.agentic_dashboard import AgenticDashboard

def simulate_decision_making(dashboard: AgenticDashboard, agent_id: str, problem_name: str):
    """
    Simulate an agent making decisions and building a decision tree.
    
    Args:
        dashboard: The agentic dashboard instance
        agent_id: ID of the agent making decisions
        problem_name: Name of the problem being solved
    """
    print(f"Agent {agent_id} starting decision process for '{problem_name}'...")
    
    # Create a decision tree
    tree_id = dashboard.create_decision_tree(
        agent_id=agent_id,
        name=f"{problem_name} Decision Process",
        description=f"Decision tree for solving {problem_name}"
    )
    
    # Add the root analysis node
    root_node = dashboard.add_decision_node(
        tree_id=tree_id,
        parent_id=None,  # Root node
        name="Problem Analysis",
        node_type="analysis",
        content=f"Analyzing problem: {problem_name}\n\n"
                f"This problem requires a systematic approach with consideration "
                f"for multiple potential solutions. I'll break it down into steps "
                f"and evaluate each approach."
    )
    
    # Register a thought about starting the analysis
    dashboard.register_thought(
        agent_id=agent_id,
        chain_id=f"chain_{tree_id[:8]}",
        content=f"Starting analysis of problem: {problem_name}",
        thought_type="initialization",
        metadata={"tree_id": tree_id}
    )
    
    # Update agent progress
    dashboard.update_agent_progress(
        agent_id=agent_id,
        percent_complete=10,
        status="Active",
        current_activity=f"Analyzing problem: {problem_name}",
        tasks_completed=1,
        total_tasks=10
    )
    
    # Simulate thinking time
    time.sleep(1.5)
    
    # Add first-level decision nodes
    approaches = [
        {"name": "Iterative Approach", "confidence": 80, 
         "content": "Solve the problem incrementally, building up the solution step by step."},
        {"name": "Divide and Conquer", "confidence": 75, 
         "content": "Break the problem into smaller sub-problems, solve them independently, then combine."},
        {"name": "Dynamic Programming", "confidence": 65, 
         "content": "Use a table-based approach to store and reuse intermediate results."}
    ]
    
    # Select primary approach
    primary_approach = approaches[0]
    approach_nodes = []
    
    # Add each approach as a decision node
    for i, approach in enumerate(approaches):
        # Register thought about considering this approach
        dashboard.register_thought(
            agent_id=agent_id,
            chain_id=f"chain_{tree_id[:8]}",
            content=f"Considering approach: {approach['name']} with confidence {approach['confidence']}%",
            thought_type="analysis",
            metadata={"tree_id": tree_id, "approach": approach['name']}
        )
        
        # Update progress
        dashboard.update_agent_progress(
            agent_id=agent_id,
            percent_complete=20 + i*10,
            status="Active",
            current_activity=f"Evaluating approach: {approach['name']}"
        )
        
        # Add the approach node
        node_id = dashboard.add_decision_node(
            tree_id=tree_id,
            parent_id=root_node,
            name=approach['name'],
            node_type="decision" if i == 0 else "alternative",
            content=approach['content'],
            confidence=approach['confidence']
        )
        approach_nodes.append(node_id)
        
        # For alternatives, add them to the primary approach
        if i > 0:
            dashboard.add_alternative(
                tree_id=tree_id,
                node_id=approach_nodes[0],  # Add as alternative to first approach
                name=approach['name'],
                content=approach['content'],
                confidence=approach['confidence']
            )
        
        # Simulate thinking time
        time.sleep(1)
    
    # Register decision about primary approach
    dashboard.register_thought(
        agent_id=agent_id,
        chain_id=f"chain_{tree_id[:8]}",
        content=f"Selected primary approach: {primary_approach['name']} with confidence {primary_approach['confidence']}%",
        thought_type="decision",
        metadata={"tree_id": tree_id, "selected_approach": primary_approach['name']}
    )
    
    # Update progress
    dashboard.update_agent_progress(
        agent_id=agent_id,
        percent_complete=50,
        status="Active",
        current_activity=f"Developing implementation plan for {primary_approach['name']}"
    )
    
    # Add implementation steps
    steps = [
        {"name": "Define Data Structures", "type": "planning"},
        {"name": "Implement Core Algorithm", "type": "implementation"},
        {"name": "Add Error Handling", "type": "implementation"},
        {"name": "Optimize Performance", "type": "optimization"}
    ]
    
    # Add each step as a child of the primary approach
    for i, step in enumerate(steps):
        # Register thought
        dashboard.register_thought(
            agent_id=agent_id,
            chain_id=f"chain_{tree_id[:8]}",
            content=f"Planning step: {step['name']}",
            thought_type=step['type'],
            metadata={"tree_id": tree_id, "step": step['name']}
        )
        
        # Update progress
        dashboard.update_agent_progress(
            agent_id=agent_id,
            percent_complete=60 + i*10,
            status="Active",
            current_activity=f"Planning: {step['name']}",
            tasks_completed=i+2,
            total_tasks=10
        )
        
        # Add step node
        step_node = dashboard.add_decision_node(
            tree_id=tree_id,
            parent_id=approach_nodes[0],  # Child of primary approach
            name=step['name'],
            node_type=step['type'],
            content=f"Step {i+1}: {step['name']}\n\n"
                   f"Details about implementing this step of the {primary_approach['name']}."
        )
        
        # Simulate thinking time
        time.sleep(0.8)
    
    # Final decision node
    dashboard.add_decision_node(
        tree_id=tree_id,
        parent_id=approach_nodes[0],
        name="Solution Complete",
        node_type="conclusion",
        content=f"Solution implementation plan for {problem_name} is complete using the {primary_approach['name']}.",
        confidence=95
    )
    
    # Register final thought
    dashboard.register_thought(
        agent_id=agent_id,
        chain_id=f"chain_{tree_id[:8]}",
        content=f"Completed decision process for {problem_name}",
        thought_type="conclusion",
        metadata={"tree_id": tree_id, "solution": primary_approach['name']}
    )
    
    # Update final progress
    dashboard.update_agent_progress(
        agent_id=agent_id,
        percent_complete=100,
        status="Completed",
        current_activity=f"Completed decision process for {problem_name}",
        tasks_completed=10,
        total_tasks=10
    )
    
    print(f"Agent {agent_id} completed decision process for '{problem_name}'")
    return tree_id

def simulate_agent_communication(dashboard: AgenticDashboard, agents: List[str], tree_ids: Dict[str, str]):
    """
    Simulate communication between agents about their decision trees.
    
    Args:
        dashboard: The agentic dashboard instance
        agents: List of agent IDs
        tree_ids: Dictionary mapping agent IDs to their tree IDs
    """
    for _ in range(20):  # Simulate 20 messages
        source_idx = random.randint(0, len(agents) - 1)
        target_idx = random.randint(0, len(agents) - 1)
        
        # Ensure source and target are different
        while target_idx == source_idx:
            target_idx = random.randint(0, len(agents) - 1)
        
        source_agent = agents[source_idx]
        target_agent = agents[target_idx]
        
        # Get source agent's tree ID
        tree_id = tree_ids.get(source_agent)
        if not tree_id:
            continue
            
        # Generate a message about the decision tree
        message_types = ["request", "response", "notification", "update"]
        message_type = random.choice(message_types)
        
        # Generate content based on message type
        if message_type == "request":
            content = f"Please review my decision tree {tree_id[:8]} and provide feedback"
        elif message_type == "response":
            content = f"I've reviewed your decision tree {tree_id[:8]} and agree with your approach"
        elif message_type == "notification":
            content = f"I've updated my decision tree {tree_id[:8]} with new information"
        else:  # update
            content = f"Decision tree {tree_id[:8]} has been finalized"
        
        # Register the message
        dashboard.register_message(
            source_agent=source_agent,
            target_agent=target_agent,
            message_type=message_type,
            content=content,
            metadata={"tree_id": tree_id}
        )
        
        # Simulate time between messages
        time.sleep(0.5)

def main():
    # Create dashboard
    dashboard = AgenticDashboard(
        output_dir="./agentic_dashboard_decision_trees_demo",
        update_interval=0.5,
        server_port=8085
    )
    
    # Define agents with their problem domains
    agent_problems = {
        "algorithm_designer": "Sorting Algorithm Selection",
        "architecture_planner": "System Architecture Design",
        "optimization_expert": "Performance Bottleneck Resolution",
        "security_analyst": "Authentication System Design"
    }
    
    # Initialize global progress
    dashboard.update_global_progress(0.0, "Initializing", 0, len(agent_problems))
    print("Starting agentic dashboard demo with decision trees...")
    
    # Create threads for each agent's decision process
    threads = []
    tree_ids = {}
    
    for agent_id, problem in agent_problems.items():
        thread = threading.Thread(
            target=lambda a=agent_id, p=problem: tree_ids.update({a: simulate_decision_making(dashboard, a, p)}),
            daemon=True
        )
        threads.append(thread)
    
    # Start all threads
    for thread in threads:
        thread.start()
        time.sleep(1)  # Stagger the start times
    
    # Start a thread for agent communication
    comm_thread = threading.Thread(
        target=lambda: simulate_agent_communication(dashboard, list(agent_problems.keys()), tree_ids),
        daemon=True
    )
    comm_thread.start()
    
    # Update global progress as agents complete their work
    steps_completed = 0
    while any(thread.is_alive() for thread in threads):
        # Count completed threads
        completed = sum(1 for thread in threads if not thread.is_alive())
        if completed > steps_completed:
            steps_completed = completed
            dashboard.update_global_progress(
                percent_complete=(steps_completed / len(threads)) * 100,
                status="Processing",
                steps_completed=steps_completed,
                total_steps=len(threads)
            )
        time.sleep(0.5)
    
    # Make sure all threads are done
    for thread in threads:
        thread.join()
    
    # Update final global progress
    dashboard.update_global_progress(100.0, "Completed", len(agent_problems), len(agent_problems))
    print("All decision processes completed!")
    
    # Keep the dashboard running for viewing
    print("Dashboard server running. Press Ctrl+C to exit...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping dashboard demo...")
    finally:
        dashboard.stop()
        print("Dashboard demo stopped.")

if __name__ == "__main__":
    main()
