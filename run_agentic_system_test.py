#!/usr/bin/env python3
"""
Triangulum Agentic System Test Runner

This script provides a simple way to run the Triangulum agentic system tests
with various configurations. It focuses on demonstrating the agentic nature
of the system and ensuring proper visibility into internal LLM processing.

Usage:
    python run_agentic_system_test.py [options]

Options:
    --test=TEST_NAME     Run a specific test (agent_communication, thought_chain_persistence, 
                        long_running_operation_visibility, timeout_handling, cancellation)
    --codebase=PATH      Path to the codebase to use for testing
    --timeout=SECONDS    Maximum test duration in seconds
    --detail-level=LEVEL Progress detail level (minimal, standard, detailed)
    --help               Show this help message
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("triangulum_agentic_test.log")
    ]
)

logger = logging.getLogger("TriangulumAgenticTest")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Triangulum Agentic System Test Runner")
    
    parser.add_argument("--test", type=str, 
                      help="Specific test to run (agent_communication, thought_chain_persistence, "
                           "long_running_operation_visibility, timeout_handling, cancellation)")
    
    parser.add_argument("--codebase", type=str, default="./test_files",
                      help="Path to the codebase to use for testing")
    
    parser.add_argument("--timeout", type=int, default=300,
                      help="Maximum test duration in seconds")
    
    parser.add_argument("--detail-level", type=str, default="detailed",
                      choices=["minimal", "standard", "detailed"],
                      help="Progress detail level")
    
    parser.add_argument("--visualize", action="store_true",
                      help="Enable visualization of test results")
    
    return parser.parse_args()

def import_test_module():
    """Import the test module, handling potential import errors."""
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        # Make sure our agentic monitoring module is importable
        try:
            from triangulum_lx.monitoring.agentic_system_monitor import AgenticSystemMonitor
            logger.debug("Successfully imported AgenticSystemMonitor")
        except ImportError as e:
            logger.warning(f"Unable to import AgenticSystemMonitor: {e}")
            logger.warning("Trying to continue anyway...")
        
        import test_agentic_system
        return test_agentic_system
    except ImportError as e:
        logger.error(f"Failed to import test_agentic_system module: {e}")
        logger.error("Make sure test_agentic_system.py is in the current directory.")
        sys.exit(1)

def run_specific_test(test_module, test_name, args):
    """Run a specific test from the test module."""
    logger.info(f"Running specific test: {test_name}")
    
    # Create tester instance
    tester = test_module.AgenticSystemTester(args.codebase)
    
    # Set up the test environment
    tester.setup()
    
    # Get the test method
    test_method = getattr(tester, f"test_{test_name}", None)
    if not test_method:
        logger.error(f"Unknown test: {test_name}")
        logger.error("Available tests: agent_communication, thought_chain_persistence, "
                    "long_running_operation_visibility, timeout_handling, cancellation")
        return False
    
    # Run the test
    try:
        result = test_method()
        logger.info(f"Test {test_name} {'PASSED' if result else 'FAILED'}")
        return result
    except Exception as e:
        logger.error(f"Test {test_name} failed with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def run_all_tests(test_module, args):
    """Run all tests from the test module."""
    logger.info("Running all agentic system tests")
    
    # Create tester instance
    tester = test_module.AgenticSystemTester(args.codebase)
    
    # Run all tests
    try:
        result = tester.run_all_tests()
        logger.info(f"All tests {'PASSED' if result else 'FAILED'}")
        return result
    except Exception as e:
        logger.error(f"Tests failed with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def visualize_results(log_file="triangulum_agentic_test.log"):
    """Generate visualizations of test results."""
    try:
        import matplotlib.pyplot as plt
        import pandas as pd
        import re
        
        logger.info("Generating test result visualizations...")
        
        # Parse the log file to extract progress events
        with open(log_file, 'r') as f:
            log_lines = f.readlines()
        
        # Extract progress events with timestamps and percentages
        progress_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).*Progress: (.*) - (.*) - (\d+)%'
        progress_events = []
        
        for line in log_lines:
            match = re.search(progress_pattern, line)
            if match:
                timestamp = pd.to_datetime(match.group(1), format='%Y-%m-%d %H:%M:%S,%f')
                agent = match.group(2)
                activity = match.group(3)
                percentage = int(match.group(4))
                progress_events.append({
                    'timestamp': timestamp,
                    'agent': agent,
                    'activity': activity,
                    'percentage': percentage
                })
        
        if not progress_events:
            logger.warning("No progress events found in log file. Cannot generate visualizations.")
            return
        
        # Create DataFrame
        df = pd.DataFrame(progress_events)
        
        # Set initial timestamp as time zero
        start_time = df['timestamp'].min()
        df['seconds'] = (df['timestamp'] - start_time).dt.total_seconds()
        
        # Create progress over time visualization
        plt.figure(figsize=(12, 8))
        
        for agent in df['agent'].unique():
            agent_df = df[df['agent'] == agent]
            plt.plot(agent_df['seconds'], agent_df['percentage'], marker='o', linestyle='-', label=agent)
        
        plt.title('Agent Progress Over Time')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Progress (%)')
        plt.grid(True)
        plt.legend()
        
        # Save the figure
        plt.savefig('triangulum_agentic_progress.png')
        logger.info("Visualization saved to triangulum_agentic_progress.png")
        
        # Create agent activity summary
        agent_activity = df.groupby('agent')['activity'].nunique().reset_index()
        agent_activity.columns = ['Agent', 'Unique Activities']
        
        # Print summary
        logger.info("Agent Activity Summary:")
        for _, row in agent_activity.iterrows():
            logger.info(f"  {row['Agent']}: {row['Unique Activities']} unique activities")
        
    except ImportError:
        logger.warning("Visualization requires matplotlib and pandas. Please install them to enable visualization.")
    except Exception as e:
        logger.error(f"Error generating visualizations: {e}")

def main():
    """Main entry point."""
    args = parse_arguments()
    logger.info(f"Starting Triangulum Agentic System Test Runner")
    logger.info(f"Configuration: codebase={args.codebase}, timeout={args.timeout}s, detail_level={args.detail_level}")
    
    # Set environment variables based on args
    os.environ['TRIANGULUM_TEST_TIMEOUT'] = str(args.timeout)
    os.environ['TRIANGULUM_PROGRESS_LEVEL'] = args.detail_level
    
    # Import the test module
    test_module = import_test_module()
    
    # Run tests
    if args.test:
        result = run_specific_test(test_module, args.test, args)
    else:
        result = run_all_tests(test_module, args)
    
    # Generate visualizations if requested
    if args.visualize and result:
        visualize_results()
    
    # Set exit code based on test result
    sys.exit(0 if result else 1)

if __name__ == "__main__":
    main()
