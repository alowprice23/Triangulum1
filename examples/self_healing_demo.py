#!/usr/bin/env python3
"""
Triangulum Self-Healing Demo

This demo showcases the dependency-aware initialization, error handling,
recovery, and system health monitoring capabilities of Triangulum.
"""

import os
import sys
import json
import time
import logging
import tempfile
import argparse
from pathlib import Path

# Add parent directory to path to enable imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger("triangulum.self_healing_demo")


def create_demo_config() -> str:
    """
    Create a demo configuration file.
    
    Returns:
        Path to configuration file
    """
    # Create a temporary directory for the demo
    demo_dir = Path("triangulum_demo")
    demo_dir.mkdir(exist_ok=True)
    
    # Create a minimal config
    config = {
        "logging": {
            "level": "INFO",
            "file": "triangulum_logs/demo_startup.log"
        },
        "providers": {
            "default_provider": "local",
            "local": {
                "enabled": True,
                "models": ["echo"]
            }
        },
        "agents": {
            "meta": {
                "enabled": True,
                "max_retries": 2
            },
            "relationship_analyst": {
                "enabled": True
            },
            "bug_detector": {
                "enabled": True
            }
        },
        "startup": {
            "parallel": True,
            "retry_count": 2,
            "timeout": 30,
            "auto_recover": True,
            "health_check_interval": 15
        }
    }
    
    # Write config to file
    config_file = demo_dir / "demo_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Created demo configuration at {config_file}")
    return str(config_file)


def demonstration_intro():
    """Display an introduction to the demonstration."""
    print("\n" + "=" * 80)
    print("Welcome to the Triangulum Self-Healing System Demo")
    print("=" * 80)
    print("""
This demonstration showcases Triangulum's key features:

1. Dependency-Aware Initialization
   - Components are initialized in the correct order based on dependencies
   - Independent components can be initialized in parallel for faster startup

2. Robust Error Handling & Recovery
   - The system can recover from initialization failures
   - Different recovery strategies are attempted automatically

3. System Health Monitoring
   - Real-time monitoring of component status
   - Automatic health checks for early problem detection

4. Visual Dashboard
   - Web-based dashboard for system monitoring
   - Real-time updates of system status and health
""")
    print("=" * 80)
    input("Press Enter to begin the demonstration...\n")


def demonstration_normal_startup(config_file: str):
    """
    Demonstrate normal system startup.
    
    Args:
        config_file: Path to configuration file
    """
    print("\n" + "-" * 80)
    print("Step 1: Normal System Startup")
    print("-" * 80)
    print("""
In this step, we'll start the Triangulum system with a standard configuration.
The system will initialize all components in dependency order, ensuring that
each component's dependencies are initialized before the component itself.
""")
    input("Press Enter to start the system...\n")
    
    from triangulum_self_heal import SystemStartupManager
    
    # Create system manager
    manager = SystemStartupManager(config_file)
    
    # Start system
    print("Starting Triangulum system...")
    start_time = time.time()
    success = manager.start_system()
    end_time = time.time()
    
    if success:
        print(f"System started successfully in {end_time - start_time:.2f} seconds")
        
        # Get system status
        status = manager.get_status()
        print("\nSystem Status:")
        print(f"- Initialization Time: {status.get('startup_time', 'unknown'):.2f} seconds")
        print("- Components:")
        
        component_status = status.get("engine", {}).get("component_status", {})
        for component, component_status in sorted(component_status.items()):
            print(f"  - {component}: {component_status}")
        
        # Run diagnostics
        diagnostics = manager._run_diagnostics()
        print("\nSystem Health:")
        print(f"- Overall Health: {diagnostics.get('overall_health', False)}")
        
        # Shutdown system
        input("\nPress Enter to shutdown the system...\n")
        print("Shutting down system...")
        manager.shutdown_system()
        print("System shutdown complete")
        
    else:
        print("System failed to start")


def demonstration_error_recovery(config_file: str):
    """
    Demonstrate error recovery during startup.
    
    Args:
        config_file: Path to configuration file
    """
    print("\n" + "-" * 80)
    print("Step 2: Error Recovery During Startup")
    print("-" * 80)
    print("""
In this step, we'll deliberately introduce an error in the configuration
to demonstrate the system's self-healing capabilities. The system will
detect the error and automatically attempt different recovery strategies.
""")
    input("Press Enter to start the system with an invalid configuration...\n")
    
    # Load original configuration
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Create a modified configuration with an invalid provider
    modified_config = config.copy()
    modified_config["providers"]["default_provider"] = "invalid_provider"
    
    # Save to a temporary file
    fd, modified_config_file = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    
    with open(modified_config_file, 'w') as f:
        json.dump(modified_config, f, indent=2)
    
    print(f"Created configuration with an invalid provider")
    
    from triangulum_self_heal import SystemStartupManager
    
    # Create system manager
    manager = SystemStartupManager(modified_config_file)
    
    # Start system (should trigger recovery)
    print("Starting system with invalid configuration...")
    print("(This will trigger the recovery process)")
    start_time = time.time()
    success = manager.start_system()
    end_time = time.time()
    
    if success:
        print(f"System recovered and started successfully in {end_time - start_time:.2f} seconds")
        
        # Get recovery attempts
        status = manager.get_status()
        recovery_attempts = status.get("recovery_attempts", {})
        
        print("\nRecovery Process:")
        for key, value in recovery_attempts.items():
            if key == "general":
                print(f"- Total recovery attempts: {value}")
            elif key == "disabled_components":
                print(f"- Disabled components: {value}")
            elif key.startswith("strategy"):
                print(f"- {key}: {value}")
            else:
                print(f"- {key}: {value}")
        
        # Shutdown system
        input("\nPress Enter to shutdown the system...\n")
        print("Shutting down system...")
        manager.shutdown_system()
        print("System shutdown complete")
        
    else:
        print("System failed to start even with recovery attempts")
    
    # Clean up
    os.unlink(modified_config_file)


def demonstration_dashboard(config_file: str):
    """
    Demonstrate the system monitoring dashboard.
    
    Args:
        config_file: Path to configuration file
    """
    print("\n" + "-" * 80)
    print("Step 3: System Monitoring Dashboard")
    print("-" * 80)
    print("""
In this step, we'll start the Triangulum system with the web-based dashboard.
The dashboard provides real-time visualization of system status, component
dependencies, initialization progress, and system health.
""")
    print("NOTE: A web browser will open automatically to display the dashboard.")
    input("Press Enter to start the system with the dashboard...\n")
    
    from triangulum_self_heal import SystemStartupManager
    from triangulum_lx.monitoring.startup_dashboard import StartupDashboard
    
    # Create system manager
    manager = SystemStartupManager(config_file)
    
    # Create dashboard
    dashboard = StartupDashboard(host="localhost", port=8080)
    
    # Start dashboard
    print("Starting dashboard...")
    dashboard.start(manager)
    print("Dashboard started at http://localhost:8080")
    
    # Start system
    print("Starting Triangulum system...")
    success = manager.start_system()
    
    if success:
        print("System started successfully")
        print("\nDashboard Features:")
        print("- Real-time component status updates")
        print("- Dependency graph visualization")
        print("- System health monitoring")
        print("- Recovery operation tracking")
        
        print("\nThe dashboard is now available in your web browser.")
        print("You can see the system status and health in real-time.")
        
        input("\nPress Enter to shutdown the system and close the dashboard...\n")
        
        # Stop dashboard
        print("Stopping dashboard...")
        dashboard.stop()
        
        # Shutdown system
        print("Shutting down system...")
        manager.shutdown_system()
        print("System shutdown complete")
        
    else:
        print("System failed to start")
        
        # Stop dashboard
        print("Stopping dashboard...")
        dashboard.stop()


def demonstration_conclusion():
    """Display a conclusion to the demonstration."""
    print("\n" + "=" * 80)
    print("Triangulum Self-Healing System Demo Conclusion")
    print("=" * 80)
    print("""
You have seen the Triangulum self-healing system in action:

1. Normal startup with dependency-aware initialization
2. Automatic error recovery with multiple strategies
3. Real-time monitoring with the system dashboard

These features make Triangulum highly resilient and self-healing:
- Components are initialized in the correct order
- The system can recover from various failures
- Health issues are detected and reported immediately
- The dashboard provides visibility into system status and health

The enhanced startup sequence ensures Triangulum starts reliably even
in the presence of failures, with faster initialization through parallel
processing where possible.
""")
    print("=" * 80)
    print("Thank you for trying the Triangulum Self-Healing System Demo!")
    print("=" * 80 + "\n")


def main():
    """Main entry point for the demo."""
    parser = argparse.ArgumentParser(description="Triangulum Self-Healing Demo")
    parser.add_argument("--skip-intro", action="store_true", help="Skip introduction")
    parser.add_argument("--step", type=int, choices=[1, 2, 3], help="Run a specific demo step")
    args = parser.parse_args()
    
    # Ensure triangulum_logs directory exists
    os.makedirs("triangulum_logs", exist_ok=True)
    
    # Create demo configuration
    config_file = create_demo_config()
    
    try:
        # Show introduction
        if not args.skip_intro:
            demonstration_intro()
        
        # Run specific step or all steps
        if args.step == 1 or args.step is None:
            demonstration_normal_startup(config_file)
        
        if args.step == 2 or args.step is None:
            demonstration_error_recovery(config_file)
        
        if args.step == 3 or args.step is None:
            demonstration_dashboard(config_file)
        
        # Show conclusion
        if not args.skip_intro and args.step is None:
            demonstration_conclusion()
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        logger.error(f"Error in demo: {e}", exc_info=True)
        print(f"\nAn error occurred: {e}")
    
    # Clean up
    try:
        os.unlink(config_file)
        os.rmdir(os.path.dirname(config_file))
    except:
        pass
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
