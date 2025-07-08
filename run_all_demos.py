#!/usr/bin/env python3
"""
Run All Triangulum Demos

This script runs all available demos for the Triangulum system,
showcasing its various features and capabilities.
"""

import os
import sys
import subprocess
import logging
import time
import webbrowser
from typing import List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# List of demos to run
DEMOS = [
    ("Auto Verification Demo", "examples/auto_verification_demo.py"),
    ("Repair Pattern Learner Demo", "examples/repair_pattern_learner_demo.py"),
    ("Quantum Code Analyzer Demo", "examples/quantum_code_analyzer_demo.py"),
    ("FixWurx Verification Demo", "run_triangulum_fixwurx_verify.py"),
]

def run_demo(demo_name: str, demo_script: str) -> Tuple[bool, str]:
    """
    Run a single demo script.
    
    Args:
        demo_name: The name of the demo
        demo_script: The path to the demo script
    
    Returns:
        A tuple of (success, output)
    """
    logger.info(f"\n--- Running Demo: {demo_name} ---")
    
    if not os.path.exists(demo_script):
        logger.error(f"Demo script not found: {demo_script}")
        return False, f"Demo script not found: {demo_script}"
    
    try:
        # Prepare command
        cmd = [sys.executable, demo_script]
        
        # Add arguments for specific demos
        if "quantum" in demo_script.lower():
            cmd.append("--use-quantum")
        
        if "fixwurx" in demo_script.lower():
            # Add required arguments for FixWurx demo
            # These are dummy paths for demonstration purposes
            cmd.extend([
                "--fixwurx-path", "C:/Users/Yusuf/Downloads/FixWurx/main.py",
                "--repair-plan", "main_repair_plan.json",
                "--project-root", ".",
                "--skip-dashboard"
            ])
        
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        # For other demos, run and wait for completion
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Log output in real-time
        for line in iter(process.stdout.readline, ''):
            logger.info(f"  {demo_name}: {line.strip()}")
        
        # Get return code and stderr
        return_code = process.wait(timeout=120) # 2 minute timeout
        stderr_output = process.stderr.read()
        
        if return_code != 0:
            logger.error(f"Demo '{demo_name}' failed with code {return_code}")
            logger.error(f"Stderr: {stderr_output}")
            return False, stderr_output
        
        logger.info(f"Demo '{demo_name}' completed successfully")
        return True, "Success"
        
    except subprocess.TimeoutExpired:
        logger.error(f"Demo '{demo_name}' timed out")
        process.kill()
        return False, "Demo timed out"
    except Exception as e:
        logger.exception(f"An error occurred while running demo '{demo_name}': {e}")
        return False, str(e)

def main():
    """Main entry point for running all demos."""
    logger.info("Starting all Triangulum demos...")
    
    results = {}
    
    for demo_name, demo_script in DEMOS:
        success, output = run_demo(demo_name, demo_script)
        results[demo_name] = {
            "script": demo_script,
            "success": success,
            "output": output
        }
    
    # Print summary
    logger.info("\n--- Demo Summary ---")
    
    for demo_name, result in results.items():
        status = "SUCCESS" if result["success"] else "FAILURE"
        logger.info(f"  - {demo_name}: {status}")
        if not result["success"]:
            logger.warning(f"    - Reason: {result['output']}")
    
    # Check for any failures
    failures = [name for name, result in results.items() if not result["success"]]
    if failures:
        logger.error(f"\nSome demos failed: {', '.join(failures)}")
        sys.exit(1)
    else:
        logger.info("\nAll demos completed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()
