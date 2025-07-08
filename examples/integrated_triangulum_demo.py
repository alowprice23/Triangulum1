"""
Integrated Triangulum Demo - Demonstrates the capabilities of the Triangulum system.

This script showcases the key features of the Triangulum system, including:
- Code relationship analysis
- System monitoring
- Self-healing
- Feedback collection

Usage:
    python examples/integrated_triangulum_demo.py [config_file]
"""

import os
import sys
import time
import json
import logging
import argparse
from typing import Dict, Any

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the Triangulum system
from triangulum_integrated_system import TriangulumSystem

def setup_logging():
    """Set up logging for the demo."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Triangulum Integrated System Demo')
    parser.add_argument('config_file', nargs='?', help='Path to configuration file (optional)')
    return parser.parse_args()

def ensure_directories():
    """Ensure required directories exist."""
    os.makedirs('triangulum_data', exist_ok=True)
    os.makedirs('docs', exist_ok=True)
    
    # Create a demo file for testing
    with open('docs/demo.md', 'w') as f:
        f.write('# Triangulum Demo\n\nThis is a demo file for testing the Triangulum system.\n')

def run_demo(config_path=None):
    """Run the Triangulum system demo."""
    print("\n" + "="*60)
    print("Triangulum Integrated System Demo")
    print("="*60 + "\n")
    
    # Ensure required directories exist
    ensure_directories()
    
    # Initialize the system
    print("Initializing Triangulum system...")
    triangulum = TriangulumSystem(config_path)
    
    # Give the system a moment to initialize
    time.sleep(1)
    
    # Display initial system status
    print("\nInitial system status:")
    status = triangulum.get_system_status()
    print(f"Timestamp: {time.ctime(status['timestamp'])}")
    print(f"Engine status: {status['engine_status']}")
    print(f"Health status: {status['health_status']['status']}")
    print(f"Files analyzed: {status['relationship_status']['files_analyzed']}")
    
    # Analyze code relationships
    print("\nAnalyzing code relationships...")
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    relationships = triangulum.analyze_code_relationships(target_dir)
    print(f"Analyzed {len(relationships)} files")
    
    # Diagnose the system
    print("\nDiagnosing system...")
    diagnosis = triangulum.diagnose_system(target_dir)
    print(f"Found {len(diagnosis['detected_issues'])} issues")
    
    # Display some issues
    if diagnosis['detected_issues']:
        print("\nDetected issues:")
        for i, issue in enumerate(diagnosis['detected_issues'][:5], 1):
            print(f"{i}. {issue['type']} ({issue['severity']}): {issue['description']}")
        
        # Display recommendations
        if diagnosis['recommendations']:
            print("\nRecommendations:")
            for i, rec in enumerate(diagnosis['recommendations'][:5], 1):
                print(f"{i}. {rec['action']}: {rec['details']}")
        
        # Attempt self-healing
        print("\nAttempting self-healing...")
        healing_results = triangulum.self_heal(target_dir, diagnosis['detected_issues'])
        print(f"Successfully fixed {healing_results['successful_fixes']} out of {healing_results['issues_addressed']} issues")
    
    # Collect feedback
    print("\nCollecting feedback...")
    feedback_id = triangulum.record_feedback(
        content="Demo feedback for testing",
        feedback_type="test",
        source="demo",
        rating=5
    )
    print(f"Recorded feedback with ID: {feedback_id}")
    
    # Get final system status
    print("\nFinal system status:")
    status = triangulum.get_system_status()
    print(f"Timestamp: {time.ctime(status['timestamp'])}")
    print(f"Engine status: {status['engine_status']}")
    print(f"Health status: {status['health_status']['status']}")
    print(f"Files analyzed: {status['relationship_status']['files_analyzed']}")
    
    # Shutdown the system
    print("\nShutting down Triangulum system...")
    triangulum.shutdown()
    
    print("\nDemo completed successfully!")
    print("="*60 + "\n")

if __name__ == "__main__":
    # Set up logging
    setup_logging()
    
    # Parse command line arguments
    args = parse_args()
    
    # Run the demo
    run_demo(args.config_file)
