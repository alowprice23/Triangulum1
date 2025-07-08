"""
Priority Analyzer Demo

This demo showcases the Priority Analyzer Agent's capabilities for analyzing
and prioritizing files, tasks, and bugs based on various factors including:
- Impact analysis
- Dependency chain evaluation
- Resource requirement estimation
- Time criticality assessment
- Business value consideration
- Context-aware priority adjustment
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add the parent directory to the path so we can import triangulum_lx
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.agents.priority_analyzer_agent import PriorityAnalyzerAgent
from triangulum_lx.agents.message import MessageType

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_bugs_by_file():
    """Create sample bugs for demonstration."""
    return {
        "file1.py": [
            {
                "id": "BUG-001",
                "severity": "high",
                "type": "null_pointer",
                "description": "Null pointer exception when processing empty input"
            },
            {
                "id": "BUG-002",
                "severity": "medium",
                "type": "logic",
                "description": "Incorrect calculation in edge case"
            }
        ],
        "file2.py": [
            {
                "id": "BUG-003",
                "severity": "critical",
                "type": "security",
                "description": "SQL injection vulnerability in user input"
            }
        ],
        "file3.py": [
            {
                "id": "BUG-004",
                "severity": "low",
                "type": "ui",
                "description": "UI element misaligned on small screens"
            },
            {
                "id": "BUG-005",
                "severity": "low",
                "type": "typo",
                "description": "Typo in error message"
            },
            {
                "id": "BUG-006",
                "severity": "medium",
                "type": "performance",
                "description": "Slow loading time for large datasets"
            }
        ],
        "file4.py": []  # No bugs
    }

def create_sample_relationships():
    """Create sample file relationships for demonstration."""
    return {
        "file1.py": {
            "dependencies": ["file2.py"],
            "dependents": ["file3.py", "file4.py"]
        },
        "file2.py": {
            "dependencies": [],
            "dependents": ["file1.py"]
        },
        "file3.py": {
            "dependencies": ["file1.py"],
            "dependents": []
        },
        "file4.py": {
            "dependencies": ["file1.py"],
            "dependents": []
        }
    }

def create_sample_tasks():
    """Create sample tasks for demonstration."""
    now = datetime.now()
    return [
        {
            "id": "TASK-001",
            "name": "Fix critical security vulnerability",
            "description": "Address SQL injection vulnerability in user input handling",
            "deadline": (now + timedelta(days=1)).isoformat(),
            "estimated_effort": "high",
            "importance": "critical",
            "impact": "high",
            "dependencies": [],
            "status": "pending"
        },
        {
            "id": "TASK-002",
            "name": "Improve performance for large datasets",
            "description": "Optimize data loading and processing for large datasets",
            "deadline": (now + timedelta(days=7)).isoformat(),
            "estimated_effort": "medium",
            "importance": "medium",
            "impact": "medium",
            "dependencies": ["TASK-003"],
            "status": "pending"
        },
        {
            "id": "TASK-003",
            "name": "Fix null pointer exception",
            "description": "Add null check to prevent exception on empty input",
            "deadline": (now + timedelta(days=3)).isoformat(),
            "estimated_effort": "low",
            "importance": "high",
            "impact": "medium",
            "dependencies": [],
            "status": "completed"
        },
        {
            "id": "TASK-004",
            "name": "Fix UI alignment issues",
            "description": "Correct UI element alignment on small screens",
            "deadline": (now + timedelta(days=14)).isoformat(),
            "estimated_effort": "low",
            "importance": "low",
            "impact": "low",
            "dependencies": [],
            "status": "pending"
        }
    ]

def create_sample_bugs():
    """Create sample bugs for demonstration."""
    now = datetime.now()
    return [
        {
            "id": "BUG-001",
            "severity": "high",
            "type": "null_pointer",
            "description": "Null pointer exception when processing empty input",
            "reported_date": (now - timedelta(days=5)).isoformat(),
            "frequency": "often",
            "affected_users": 500,
            "affected_components": ["data_processor", "input_handler"]
        },
        {
            "id": "BUG-003",
            "severity": "critical",
            "type": "security",
            "description": "SQL injection vulnerability in user input",
            "reported_date": (now - timedelta(days=1)).isoformat(),
            "frequency": "rarely",
            "affected_users": 100,
            "affected_components": ["database", "user_input"]
        },
        {
            "id": "BUG-006",
            "severity": "medium",
            "type": "performance",
            "description": "Slow loading time for large datasets",
            "reported_date": (now - timedelta(days=30)).isoformat(),
            "frequency": "always",
            "affected_users": 1000,
            "affected_components": ["data_loader", "renderer"]
        }
    ]

def create_sample_context():
    """Create sample context for demonstration."""
    return {
        "deadline": (datetime.now() + timedelta(days=7)).isoformat(),
        "project_phase": "testing",
        "priority_boosts": {
            "security": 0.2,
            "performance": 0.1
        },
        "priority_overrides": {
            "file2.py": 0.95  # Override priority for file2.py
        },
        "business_value_mapping": {
            "user_auth": 0.9,
            "payment": 0.8,
            "reporting": 0.6,
            "admin": 0.5,
            "ui": 0.3
        }
    }

def print_priority_results(title, results, show_explanations=False):
    """Print priority results in a readable format."""
    print(f"\n{'-' * 80}")
    print(f"{title}")
    print(f"{'-' * 80}")
    
    # Sort by priority (highest first)
    sorted_results = sorted(
        results.items(),
        key=lambda x: x[1]["priority"],
        reverse=True
    )
    
    for item_id, item_data in sorted_results:
        priority = item_data["priority"]
        print(f"{item_id}: Priority = {priority:.2f}")
        
        if "bug_count" in item_data:
            print(f"  Bug count: {item_data['bug_count']}")
        
        if "factors" in item_data:
            print("  Factors:")
            for factor, value in item_data["factors"].items():
                print(f"    {factor}: {value:.2f}")
        
        if show_explanations and "explanation" in item_data:
            print("\n  Explanation:")
            for line in item_data["explanation"].split("\n"):
                print(f"    {line}")
        
        print()

def main():
    """Run the Priority Analyzer demo."""
    logger.info("Starting Priority Analyzer Demo")
    
    # Create a Priority Analyzer Agent
    agent = PriorityAnalyzerAgent(
        agent_id="demo_priority_analyzer",
        config={
            "weights": {
                "severity": 0.35,
                "bug_count": 0.15,
                "dependencies": 0.20,
                "dependents": 0.15,
                "complexity": 0.05,
                "business_value": 0.10
            },
            "business_value_mapping": {
                "auth": 0.9,
                "payment": 0.8,
                "core": 0.7
            }
        }
    )
    
    # Create sample data
    bugs_by_file = create_sample_bugs_by_file()
    relationships = create_sample_relationships()
    tasks = create_sample_tasks()
    bugs = create_sample_bugs()
    context = create_sample_context()
    
    # Analyze file priorities
    logger.info("Analyzing file priorities...")
    file_priorities = agent.analyze_priorities(
        folder_path="/path/to/project",
        bugs_by_file=bugs_by_file,
        relationships=relationships,
        context=context
    )
    
    # Analyze task priorities
    logger.info("Analyzing task priorities...")
    task_priorities = agent.analyze_task_priorities(
        tasks=tasks,
        context=context
    )
    
    # Analyze bug priorities
    logger.info("Analyzing bug priorities...")
    bug_priorities = agent.analyze_bug_priorities(
        bugs=bugs,
        context=context
    )
    
    # Print results
    print_priority_results("FILE PRIORITIES", file_priorities)
    print_priority_results("TASK PRIORITIES", task_priorities)
    print_priority_results("BUG PRIORITIES", bug_priorities)
    
    # Print detailed explanation for the highest priority file
    highest_priority_file = max(file_priorities.items(), key=lambda x: x[1]["priority"])[0]
    print_priority_results(
        f"DETAILED EXPLANATION FOR {highest_priority_file}",
        {highest_priority_file: file_priorities[highest_priority_file]},
        show_explanations=True
    )
    
    # Print agent metrics
    logger.info("Priority Analyzer metrics:")
    logger.info(json.dumps(agent.metrics, indent=2))
    
    logger.info("Priority Analyzer Demo completed")

if __name__ == "__main__":
    main()
