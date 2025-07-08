#!/usr/bin/env python3
"""
Triangulum-FixWurx Integration with Auto Verification

This script integrates the Triangulum auto verification system with the FixWurx repair process,
automatically verifying fixes and ensuring they resolve the original issues without
introducing regressions.
"""

import os
import sys
import time
import json
import logging
import argparse
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Triangulum components
from triangulum_lx.tooling.auto_verification import AutoVerifier
from triangulum_lx.monitoring.progress_tracker import ProgressTracker
from triangulum_lx.monitoring.agentic_dashboard import AgenticDashboard

def setup_dashboard(output_dir: str, auto_open: bool = True) -> AgenticDashboard:
    """
    Set up the agentic dashboard for monitoring the verification process.
    
    Args:
        output_dir: Directory for dashboard outputs
        auto_open: Whether to automatically open the dashboard in a browser
    
    Returns:
        Configured dashboard instance
    """
    dashboard_dir = os.path.join(output_dir, "dashboard")
    os.makedirs(dashboard_dir, exist_ok=True)
    
    dashboard = AgenticDashboard(
        output_dir=dashboard_dir,
        update_interval=0.5,
        enable_server=True,
        server_port=8081,
        auto_open_browser=auto_open
    )
    
    # Initialize global progress
    dashboard.update_global_progress(
        percent_complete=0.0,
        status="Initializing verification system",
        steps_completed=0,
        total_steps=0
    )
    
    return dashboard

def load_fixwurx_repair_plan(repair_plan_path: str) -> Union[Dict, List]:
    """
    Load a FixWurx repair plan from a JSON file.
    
    Args:
        repair_plan_path: Path to the repair plan JSON file
    
    Returns:
        Dictionary or List with repair plan information
    """
    if not os.path.exists(repair_plan_path):
        raise FileNotFoundError(f"Repair plan not found: {repair_plan_path}")
    
    with open(repair_plan_path, 'r', encoding='utf-8') as f:
        repair_plan = json.load(f)
    
    if isinstance(repair_plan, dict):
        logger.info(f"Loaded repair plan with {len(repair_plan.get('fixes', []))} fixes")
    elif isinstance(repair_plan, list):
        logger.info(f"Loaded repair plan with {len(repair_plan)} fixes")
    
    return repair_plan

def convert_fixwurx_fixes_to_verification_format(repair_plan: Union[Dict, List]) -> List[Dict]:
    """
    Convert FixWurx repair plan fixes to the format expected by the auto verifier.
    
    Args:
        repair_plan: FixWurx repair plan dictionary or list
    
    Returns:
        List of fix dictionaries in auto verifier format
    """
    fixes = []
    
    if isinstance(repair_plan, dict):
        fix_list = repair_plan.get("fixes", [])
    elif isinstance(repair_plan, list):
        fix_list = repair_plan
    else:
        fix_list = []

    for fix in fix_list:
        # Extract file path, removing any absolute path components
        file_path = fix.get("file", "")
        if os.path.isabs(file_path):
            file_path = os.path.basename(file_path)
        
        # Convert to auto verifier format
        verification_fix = {
            "file": file_path,
            "line": fix.get("line"),
            "severity": fix.get("severity", "medium"),
            "description": fix.get("description", "Unknown fix")
        }
        
        fixes.append(verification_fix)
    
    return fixes

def run_fixwurx_repair(
    fixwurx_path: str,
    repair_plan_path: str,
    output_dir: str,
    tracker: Optional[ProgressTracker] = None
) -> Dict:
    """
    Run the FixWurx repair process.
    
    Args:
        fixwurx_path: Path to the FixWurx executable or script
        repair_plan_path: Path to the repair plan JSON file
        output_dir: Directory to store repair outputs
        tracker: Optional progress tracker for monitoring
    
    Returns:
        Dictionary with repair results
    """
    if tracker:
        tracker.update_progress(
            percent_complete=10.0,
            status="Active",
            current_activity="Initiating FixWurx repair process"
        )
    
    logger.info(f"Running FixWurx repair with plan: {repair_plan_path}")
    
    try:
        # Create command to run FixWurx
        cmd = [
            sys.executable,  # Python executable
            fixwurx_path,
            "--repair-plan", repair_plan_path,
            "--output-dir", output_dir,
            "--verbose"
        ]
        
        # Run FixWurx
        if tracker:
            tracker.update_progress(
                percent_complete=20.0,
                status="Active",
                current_activity=f"Executing FixWurx: {' '.join(cmd)}"
            )
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Track progress by monitoring FixWurx output
        completed_fixes = 0
        total_fixes = 0
        
        # Parse repair plan to get total fixes
        try:
            with open(repair_plan_path, 'r', encoding='utf-8') as f:
                repair_plan = json.load(f)
                total_fixes = len(repair_plan.get("fixes", []))
        except Exception as e:
            logger.warning(f"Could not determine total fixes from repair plan: {e}")
            total_fixes = 100  # Default value
        
        # Process output in real-time
        for line in iter(process.stdout.readline, ''):
            logger.info(f"FixWurx: {line.strip()}")
            
            # Parse output to track progress
            if "Completed repair of" in line:
                completed_fixes += 1
                if tracker and total_fixes > 0:
                    percent = min(80.0, 20.0 + (completed_fixes / total_fixes) * 60.0)
                    tracker.update_progress(
                        percent_complete=percent,
                        status="Active",
                        current_activity=f"Completed {completed_fixes}/{total_fixes} fixes",
                        tasks_completed=completed_fixes,
                        total_tasks=total_fixes
                    )
                    
                    # Record thought about the fix
                    fix_match = re.search(r"Completed repair of (.+): (.+)", line)
                    if fix_match:
                        file_path = fix_match.group(1)
                        description = fix_match.group(2)
                        tracker.record_thought(
                            f"FixWurx completed fix: {description} in {file_path}",
                            thought_type="completion"
                        )
        
        # Get return code
        return_code = process.wait()
        stderr_output = process.stderr.read()
        
        if return_code != 0:
            logger.error(f"FixWurx repair failed with code {return_code}: {stderr_output}")
            if tracker:
                tracker.update_progress(
                    percent_complete=30.0,
                    status="Error",
                    current_activity=f"FixWurx repair failed with code {return_code}"
                )
                tracker.record_thought(
                    f"Error during repair process: {stderr_output}",
                    thought_type="error"
                )
            return {
                "success": False,
                "error": f"FixWurx repair failed with code {return_code}: {stderr_output}",
                "fixes_completed": completed_fixes,
                "total_fixes": total_fixes
            }
        
        # Success
        logger.info("FixWurx repair completed successfully")
        if tracker:
            tracker.update_progress(
                percent_complete=80.0,
                status="Active",
                current_activity="FixWurx repair completed successfully",
                tasks_completed=completed_fixes,
                total_tasks=total_fixes
            )
            tracker.record_thought(
                f"Repair process completed successfully. Applied {completed_fixes} fixes.",
                thought_type="completion"
            )
        
        return {
            "success": True,
            "fixes_completed": completed_fixes,
            "total_fixes": total_fixes
        }
    
    except Exception as e:
        logger.exception(f"Error running FixWurx repair: {e}")
        if tracker:
            tracker.update_progress(
                percent_complete=30.0,
                status="Error",
                current_activity=f"Error running FixWurx repair: {e}"
            )
            tracker.record_thought(
                f"Exception during repair process: {e}",
                thought_type="error"
            )
        
        return {
            "success": False,
            "error": str(e),
            "fixes_completed": 0,
            "total_fixes": 0
        }

def verify_fixwurx_repairs(
    project_root: str,
    fixes: List[Dict],
    output_dir: str,
    test_command: Optional[str] = None,
    tracker: Optional[ProgressTracker] = None
) -> Dict:
    """
    Verify FixWurx repairs using the auto verification tool.
    
    Args:
        project_root: Path to the project root
        fixes: List of fixes to verify
        output_dir: Directory to store verification outputs
        test_command: Command to run project tests
        tracker: Optional progress tracker for monitoring
    
    Returns:
        Dictionary with verification results
    """
    if tracker:
        tracker.update_progress(
            percent_complete=80.0,
            status="Active",
            current_activity="Initializing auto verification"
        )
        tracker.record_thought(
            f"Starting verification of {len(fixes)} fixes",
            thought_type="analysis"
        )
    
    logger.info(f"Verifying {len(fixes)} fixes")
    
    try:
        # Initialize auto verifier
        verification_dir = os.path.join(output_dir, "verification")
        os.makedirs(verification_dir, exist_ok=True)
        
        verifier = AutoVerifier(
            project_root=project_root,
            verification_dir=verification_dir,
            test_command=test_command,
            enable_regression_testing=True,
            enable_performance_testing=True
        )
        
        # Create baseline
        if tracker:
            tracker.update_progress(
                percent_complete=85.0,
                status="Active",
                current_activity="Creating verification baseline"
            )
            tracker.record_thought(
                "Creating baseline for verification",
                thought_type="analysis"
            )
        
        baseline = verifier.create_baseline()
        
        # Verify each fix
        if tracker:
            tracker.update_progress(
                percent_complete=87.0,
                status="Active",
                current_activity=f"Verifying {len(fixes)} fixes",
                tasks_completed=0,
                total_tasks=len(fixes)
            )
        
        verified_count = 0
        failed_count = 0
        verification_results = []
        
        for i, fix in enumerate(fixes):
            if tracker:
                tracker.update_progress(
                    percent_complete=min(98.0, 87.0 + (i / len(fixes)) * 11.0),
                    status="Active",
                    current_activity=f"Verifying fix {i+1}/{len(fixes)}: {fix['description']}",
                    tasks_completed=i,
                    total_tasks=len(fixes)
                )
                tracker.record_thought(
                    f"Verifying fix: {fix['description']} in {fix['file']}",
                    thought_type="verification"
                )
            
            # Verify the fix
            result = verifier.verify_fix(fix)
            verification_results.append(result)
            
            if result["verified"]:
                verified_count += 1
                logger.info(f"Fix {i+1}/{len(fixes)} verified: {fix['description']}")
                
                if tracker:
                    tracker.record_thought(
                        f"Fix verified: {fix['description']} in {fix['file']}",
                        thought_type="success"
                    )
                
                # Generate regression test
                try:
                    test_path = verifier.generate_regression_test(fix)
                    logger.info(f"Generated regression test: {test_path}")
                    
                    if tracker:
                        tracker.record_thought(
                            f"Generated regression test for {fix['description']}",
                            thought_type="creation"
                        )
                except Exception as e:
                    logger.warning(f"Could not generate regression test: {e}")
            else:
                failed_count += 1
                logger.warning(f"Fix {i+1}/{len(fixes)} failed verification: {fix['description']}")
                logger.warning(f"Verification error: {result.get('error', 'Unknown error')}")
                
                if tracker:
                    tracker.record_thought(
                        f"Fix failed verification: {fix['description']} in {fix['file']}. Error: {result.get('error', 'Unknown error')}",
                        thought_type="failure"
                    )
        
        # Run regression tests
        if tracker:
            tracker.update_progress(
                percent_complete=98.0,
                status="Active",
                current_activity="Running regression tests"
            )
            tracker.record_thought(
                "Running regression tests to ensure fixes don't introduce regressions",
                thought_type="verification"
            )
        
        regression_results = verifier.run_regression_tests()
        
        # Export verification report
        report_path = verifier.export_verification_report()
        
        # Final result
        if tracker:
            tracker.update_progress(
                percent_complete=100.0,
                status="Completed",
                current_activity=f"Verification completed: {verified_count}/{len(fixes)} fixes verified",
                tasks_completed=len(fixes),
                total_tasks=len(fixes)
            )
            tracker.record_thought(
                f"Verification completed. {verified_count}/{len(fixes)} fixes verified. Regression tests: {regression_results['passed']}/{regression_results['tests_run']} passed.",
                thought_type="completion"
            )
        
        return {
            "success": verified_count == len(fixes),
            "verified_count": verified_count,
            "failed_count": failed_count,
            "total_fixes": len(fixes),
            "verification_results": verification_results,
            "regression_results": regression_results,
            "report_path": report_path
        }
    
    except Exception as e:
        logger.exception(f"Error during verification: {e}")
        if tracker:
            tracker.update_progress(
                percent_complete=90.0,
                status="Error",
                current_activity=f"Error during verification: {e}"
            )
            tracker.record_thought(
                f"Exception during verification process: {e}",
                thought_type="error"
            )
        
        return {
            "success": False,
            "error": str(e),
            "verified_count": 0,
            "failed_count": 0,
            "total_fixes": len(fixes)
        }

def main():
    """Main entry point for the Triangulum-FixWurx verification integration."""
    parser = argparse.ArgumentParser(description="Triangulum-FixWurx Integration with Auto Verification")
    
    parser.add_argument(
        "--fixwurx-path",
        type=str,
        required=True,
        help="Path to the FixWurx executable or script"
    )
    
    parser.add_argument(
        "--repair-plan",
        type=str,
        required=True,
        help="Path to the repair plan JSON file"
    )
    
    parser.add_argument(
        "--project-root",
        type=str,
        required=True,
        help="Path to the project root directory"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./fixwurx_verification",
        help="Directory to store outputs"
    )
    
    parser.add_argument(
        "--test-command",
        type=str,
        help="Command to run project tests (if available)"
    )
    
    parser.add_argument(
        "--skip-repair",
        action="store_true",
        help="Skip the repair step and only run verification"
    )
    
    parser.add_argument(
        "--skip-dashboard",
        action="store_true",
        help="Skip launching the dashboard"
    )
    
    parser.add_argument(
        "--report-file",
        type=str,
        help="Path to save the final report"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Set up dashboard if enabled
    dashboard = None
    verification_tracker = None
    
    if not args.skip_dashboard:
        try:
            dashboard = setup_dashboard(args.output_dir)
            verification_tracker = ProgressTracker(
                dashboard=dashboard,
                agent_id="verification_agent",
                enable_local_logging=True,
                log_dir=os.path.join(args.output_dir, "logs"),
                connect_to_dashboard=True
            )
            logger.info("Dashboard and progress tracker initialized")
        except Exception as e:
            logger.error(f"Could not initialize dashboard: {e}")
    
    try:
        # Load repair plan
        repair_plan = load_fixwurx_repair_plan(args.repair_plan)
        fixes = convert_fixwurx_fixes_to_verification_format(repair_plan)
        
        if verification_tracker:
            verification_tracker.update_progress(
                percent_complete=5.0,
                status="Active",
                current_activity=f"Loaded repair plan with {len(fixes)} fixes",
                total_tasks=len(fixes)
            )
        
        # Run repair if not skipped
        if not args.skip_repair:
            repair_results = run_fixwurx_repair(
                fixwurx_path=args.fixwurx_path,
                repair_plan_path=args.repair_plan,
                output_dir=args.output_dir,
                tracker=verification_tracker
            )
            
            if not repair_results["success"]:
                logger.error("Repair process failed, verification skipped")
                return 1
        else:
            logger.info("Repair step skipped")
            if verification_tracker:
                verification_tracker.update_progress(
                    percent_complete=80.0,
                    status="Active",
                    current_activity="Repair step skipped, proceeding to verification"
                )
        
        # Run verification
        verification_results = verify_fixwurx_repairs(
            project_root=args.project_root,
            fixes=fixes,
            output_dir=args.output_dir,
            test_command=args.test_command,
            tracker=verification_tracker
        )
        
        # Generate final report
        report = {
            "timestamp": time.time(),
            "repair_plan": args.repair_plan,
            "project_root": args.project_root,
            "fixes": fixes,
            "verification_results": verification_results,
            "summary": {
                "total_fixes": len(fixes),
                "verified_fixes": verification_results["verified_count"],
                "failed_fixes": verification_results["failed_count"],
                "success_rate": verification_results["verified_count"] / len(fixes) if len(fixes) > 0 else 0,
                "regression_tests_run": verification_results.get("regression_results", {}).get("tests_run", 0),
                "regression_tests_passed": verification_results.get("regression_results", {}).get("passed", 0)
            }
        }
        
        # Save report
        report_path = args.report_file
        if not report_path:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(args.output_dir, f"verification_report_{timestamp}.json")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Verification report saved to {report_path}")
        
        # Print summary
        print("\n" + "="*80)
        print("TRIANGULUM-FIXWURX VERIFICATION SUMMARY")
        print("="*80)
        
        print(f"\nProject: {args.project_root}")
        print(f"Repair Plan: {args.repair_plan}")
        
        print("\nVerification Results:")
        print(f"  Total Fixes: {len(fixes)}")
        print(f"  Verified Fixes: {verification_results['verified_count']}")
        print(f"  Failed Fixes: {verification_results['failed_count']}")
        print(f"  Success Rate: {verification_results['verified_count'] / len(fixes) * 100:.1f}%" if len(fixes) > 0 else "  Success Rate: N/A")
        
        regression_results = verification_results.get("regression_results", {})
        print("\nRegression Testing:")
        print(f"  Tests Run: {regression_results.get('tests_run', 0)}")
        print(f"  Tests Passed: {regression_results.get('passed', 0)}")
        print(f"  Tests Failed: {regression_results.get('failed', 0)}")
        
        print(f"\nDetailed Report: {report_path}")
        
        print("\nVerification completed successfully!")
        
        # Keep dashboard running if enabled
        if dashboard and not args.skip_dashboard:
            try:
                print("\nDashboard running. Press Ctrl+C to exit...")
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nExiting...")
    
    except KeyboardInterrupt:
        logger.info("Verification process interrupted")
        print("\nVerification process interrupted")
    
    except Exception as e:
        logger.exception(f"Error during verification process: {e}")
        print(f"\nError: {e}")
        return 1
    
    finally:
        # Stop dashboard if running
        if dashboard:
            dashboard.stop()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
