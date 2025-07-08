#!/usr/bin/env python3
"""
Quantum Code Analyzer Demo

This script demonstrates the quantum-accelerated code analysis capabilities,
including pattern recognition, dependency analysis, and bug detection.
"""

import os
import sys
import time
import json
import argparse
import logging
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.quantum.code_analyzer import QuantumCodeAnalyzer
from triangulum_lx.monitoring.progress_tracker import ProgressTracker
from triangulum_lx.monitoring.agentic_dashboard import AgenticDashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_dashboard(output_dir: str) -> AgenticDashboard:
    """
    Set up the agentic dashboard for monitoring.
    
    Args:
        output_dir: Directory for dashboard outputs
    
    Returns:
        Configured dashboard instance
    """
    dashboard_dir = os.path.join(output_dir, "dashboard")
    os.makedirs(dashboard_dir, exist_ok=True)
    
    dashboard = AgenticDashboard(
        output_dir=dashboard_dir,
        update_interval=0.5,
        enable_server=True,
        server_port=8082,
        auto_open_browser=False
    )
    
    return dashboard

def create_demo_project(base_dir: str):
    """Create a small demo project for analysis."""
    project_dir = os.path.join(base_dir, "demo_project")
    os.makedirs(project_dir, exist_ok=True)
    
    files = {
        "main.py": """
import utils
import analysis
from models import User

def main():
    user = User("test_user")
    data = utils.load_data("data.json")
    if data:
        results = analysis.process_data(data)
        utils.save_results(results)
    print(f"Processing complete for {user.name}")

if __name__ == "__main__":
    main()
""",
        "utils.py": """
import json
import logging

def load_data(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return None

def save_results(results):
    # Bug: hardcoded filename
    with open("results.json", 'w') as f:
        json.dump(results, f, indent=2)
""",
        "analysis.py": """
import models

def process_data(data):
    # Inefficient processing
    results = []
    for item in data:
        if item.get("value") > 50:
            results.append(models.Result(item["id"], "high"))
    return results
""",
        "models.py": """
class User:
    def __init__(self, name):
        self.name = name

class Result:
    def __init__(self, item_id, category):
        self.item_id = item_id
        self.category = category
""",
        "data.json": """
[
    {"id": 1, "value": 75},
    {"id": 2, "value": 30},
    {"id": 3, "value": 90}
]
"""
    }
    
    for file_name, content in files.items():
        with open(os.path.join(project_dir, file_name), 'w') as f:
            f.write(content)
            
    return project_dir

def main():
    parser = argparse.ArgumentParser(description="Quantum Code Analyzer Demo")
    parser.add_argument(
        "--use-quantum",
        action="store_true",
        help="Enable quantum acceleration (if available)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./quantum_analysis_output",
        help="Directory to store analysis outputs"
    )
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Setup dashboard and tracker
    dashboard = setup_dashboard(args.output_dir)
    tracker = ProgressTracker(
        dashboard=dashboard,
        agent_id="quantum_analyzer_demo",
        log_dir=os.path.join(args.output_dir, "logs")
    )
    
    try:
        # Create demo project
        demo_project_dir = create_demo_project(args.output_dir)
        
        # Initialize analyzer
        analyzer = QuantumCodeAnalyzer(use_quantum=args.use_quantum)
        
        # --- 1. Directory Analysis ---
        tracker.update_progress(0, "Active", "Starting directory analysis")
        logger.info("\n--- 1. Analyzing Directory ---")
        dir_analysis = analyzer.analyze_directory(demo_project_dir, include_patterns=["*.py"])
        
        report_path = os.path.join(args.output_dir, "directory_analysis.json")
        with open(report_path, 'w') as f:
            json.dump(dir_analysis, f, indent=2)
        logger.info(f"Directory analysis report saved to {report_path}")
        tracker.record_thought(f"Directory analysis complete. Found {len(dir_analysis['patterns'])} cross-file patterns.", "completion")
        
        # --- 2. Bug Detection ---
        tracker.update_progress(25, "Active", "Starting bug detection")
        logger.info("\n--- 2. Detecting Bugs ---")
        utils_file = os.path.join(demo_project_dir, "utils.py")
        bug_report = analyzer.detect_bugs(utils_file)
        
        report_path = os.path.join(args.output_dir, "bug_report.json")
        with open(report_path, 'w') as f:
            json.dump(bug_report, f, indent=2)
        logger.info(f"Bug detection report saved to {report_path}")
        tracker.record_thought(f"Bug detection complete. Found {bug_report['bug_count']} bugs.", "completion")

        # --- 3. Dependency Analysis ---
        tracker.update_progress(50, "Active", "Starting dependency analysis")
        logger.info("\n--- 3. Analyzing Dependencies ---")
        files_to_analyze = [os.path.join(demo_project_dir, f) for f in os.listdir(demo_project_dir) if f.endswith('.py')]
        dep_analysis = analyzer.analyze_dependencies(files_to_analyze)
        
        report_path = os.path.join(args.output_dir, "dependency_analysis.json")
        with open(report_path, 'w') as f:
            json.dump(dep_analysis, f, indent=2)
        logger.info(f"Dependency analysis report saved to {report_path}")
        tracker.record_thought(f"Dependency analysis complete. Found {len(dep_analysis['cycles'])} cycles.", "completion")

        # --- 4. Code Similarity ---
        tracker.update_progress(75, "Active", "Starting code similarity analysis")
        logger.info("\n--- 4. Finding Code Similarities ---")
        similarity_analysis = analyzer.find_code_similarities(files_to_analyze)
        
        report_path = os.path.join(args.output_dir, "similarity_analysis.json")
        with open(report_path, 'w') as f:
            json.dump(similarity_analysis, f, indent=2)
        logger.info(f"Similarity analysis report saved to {report_path}")
        tracker.record_thought(f"Similarity analysis complete. Found {len(similarity_analysis['clusters'])} clusters.", "completion")

        tracker.update_progress(100, "Completed", "All analyses finished")
        logger.info("\n--- Demo Finished ---")
        
        print("\nQuantum Code Analyzer Demo finished successfully.")
        print(f"Reports saved in: {args.output_dir}")
        
        # Keep dashboard running
        print("\nDashboard is running. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Demo interrupted by user.")
    except Exception as e:
        logger.exception(f"An error occurred during the demo: {e}")
        tracker.update_progress(100, "Error", f"Demo failed: {e}")
    finally:
        dashboard.stop()
        logger.info("Dashboard stopped.")

if __name__ == "__main__":
    main()
