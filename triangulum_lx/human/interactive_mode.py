import cmd
import sys
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import readline  # For command history

from ..core.engine import TriangulumEngine
from ..core.monitor import Monitor
from ..agents.coordinator import Coordinator
from .feedback import FeedbackType, FeedbackItem, FeedbackManager
from ..monitoring.metrics import MetricsCollector


class InteractiveDebugger(cmd.Cmd):
    """Interactive command-line interface for Triangulum system."""
    
    intro = """
╔═══════════════════════════════════════════════════╗
║                                                   ║
║   Triangulum LX Interactive Debugging Console     ║
║                                                   ║
║   Type 'help' for a list of commands              ║
║   Type 'start' to begin a debugging session       ║
║                                                   ║
╚═══════════════════════════════════════════════════╝
"""
    prompt = "triangulum> "
    
    def __init__(self):
        super().__init__()
        self.engine = TriangulumEngine()
        self.monitor = Monitor(self.engine)
        self.engine.monitor = self.monitor
        self.coordinator = None
        self.metrics = MetricsCollector()
        self.feedback = FeedbackManager()
        self.current_bug_id = None
        self.debug_session_active = False
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        config_path = Path("config/interactive_config.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            # Default config
            return {
                'auto_progress': False,
                'verbose_output': True,
                'save_history': True,
                'max_ticks': 60,
                'visualization': True
            }
    
    def do_start(self, arg):
        """Start a new debugging session."""
        if self.debug_session_active:
            print("A debugging session is already active. Use 'reset' to start over.")
            return
        
        print("Starting a new Triangulum debugging session...")
        self.engine = TriangulumEngine()
        self.monitor = Monitor(self.engine)
        self.engine.monitor = self.monitor
        agents = {"observer": None, "analyst": None, "patcher": None, "verifier": None}
        self.coordinator = Coordinator(self.engine, agents)
        self.metrics = MetricsCollector()
        self.debug_session_active = True
        
        # Initialize the first bug
        print("Please provide information about the bug:")
        bug_id = input("Bug ID or description: ")
        self.current_bug_id = bug_id
        
        print("\nSession started. Use 'status' to see the current state.")
    
    def do_status(self, arg):
        """Show current debugging session status."""
        if not self.debug_session_active:
            print("No active debugging session. Use 'start' to begin.")
            return
        
        print("\n=== Triangulum Debugging Status ===")
        print(f"Current tick: {self.engine.tick_no}")
        print(f"Free agents: {self.engine.free_agents}")
        print(f"Entropy bits: {self.monitor.g_bits:.2f}")
        
        print("\nBugs Status:")
        for i, bug in enumerate(self.engine.bugs):
            if bug.phase.name != "WAIT" or i < 3:  # Show active bugs and a few waiting
                status = f"Bug #{i}: {bug.phase.name}"
                if bug.timer > 0:
                    status += f" (T-{bug.timer})"
                if bug.attempts > 0:
                    status += f" [Attempt: {bug.attempts}]"
                print(status)
        
        if self.monitor.g_bits >= self.monitor.H0_bits:
            print("\n⚠️ Entropy budget exceeded - consider escalation")
    
    def do_step(self, arg):
        """Advance the simulation by one tick."""
        if not self.debug_session_active:
            print("No active debugging session. Use 'start' to begin.")
            return
        
        try:
            self.engine.tick()
            self.metrics.record_tick(self.engine)
            print(f"Advanced to tick {self.engine.tick_no}")
            
            # Check if session is complete
            if self.monitor.done():
                print("\n✅ All bugs resolved!")
                self.do_status("")
                self.debug_session_active = False
                
                # Request feedback
                self._request_feedback()
            
        except Exception as e:
            print(f"Error during step: {e}")
    
    def do_auto(self, arg):
        """Run the simulation automatically until completion or error."""
        if not self.debug_session_active:
            print("No active debugging session. Use 'start' to begin.")
            return
        
        steps = 0
        max_steps = int(arg) if arg.isdigit() else self.config['max_ticks']
        
        try:
            while steps < max_steps and self.debug_session_active:
                self.engine.tick()
                self.metrics.record_tick(self.engine)
                steps += 1
                
                # Print progress
                if steps % 5 == 0:
                    print(f"Advanced to tick {self.engine.tick_no}")
                
                # Check if session is complete
                if self.monitor.done():
                    print("\n✅ All bugs resolved!")
                    self.do_status("")
                    self.debug_session_active = False
                    
                    # Request feedback
                    self._request_feedback()
                    break
                
                time.sleep(0.1)  # Small delay to make output readable
                
            if self.debug_session_active:
                print(f"\nReached maximum of {max_steps} steps.")
                self.do_status("")
                
        except Exception as e:
            print(f"Error during auto run: {e}")
    
    def do_reset(self, arg):
        """Reset the current debugging session."""
        if not self.debug_session_active:
            print("No active debugging session to reset.")
            return
        
        self.debug_session_active = False
        print("Session reset. Use 'start' to begin a new session.")
    
    def do_feedback(self, arg):
        """Provide feedback on the current debugging session."""
        self._request_feedback()
    
    def _request_feedback(self):
        """Request feedback from the user."""
        print("\n=== Please provide feedback on this debugging session ===")
        
        # Get feedback type
        print("\nFeedback type:")
        for i, ft in enumerate(FeedbackType):
            print(f"{i+1}. {ft.name} - {ft.name.replace('_', ' ').title()}")
        
        ft_idx = input("\nSelect feedback type (1-6): ")
        try:
            ft_idx = int(ft_idx) - 1
            if ft_idx < 0 or ft_idx >= len(FeedbackType):
                raise ValueError
            feedback_type = list(FeedbackType)[ft_idx]
        except (ValueError, IndexError):
            print("Invalid selection. Using OTHER.")
            feedback_type = FeedbackType.OTHER
        
        # Get rating
        rating_input = input("\nRating (1-5, where 5 is best): ")
        try:
            rating = int(rating_input)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            print("Invalid rating. Using 3.")
            rating = 3
        
        # Get comment
        comment = input("\nPlease provide detailed feedback:\n")
        
        # Create and save feedback
        feedback_item = FeedbackItem(
            feedback_type=feedback_type,
            rating=rating,
            comment=comment,
            timestamp=time.time(),
            bug_id=self.current_bug_id
        )
        
        if self.feedback.add_feedback(feedback_item):
            print("\nThank you for your feedback!")
        else:
            print("\nThere was an error saving your feedback.")
    
    def do_viz(self, arg):
        """Generate visualization of current debugging session."""
        if not self.debug_session_active and not self.metrics.tick_metrics:
            print("No data to visualize. Start a session first.")
            return
        
        try:
            from ..monitoring.visualization import create_dashboard
            
            print("Generating visualization...")
            dashboard_path = create_dashboard(self.engine, self.metrics)
            print(f"Dashboard created: {dashboard_path}")
            
            # Try to open the dashboard
            import webbrowser
            webbrowser.open(f"file://{dashboard_path}")
            
        except ImportError:
            print("Visualization tools not available. Install matplotlib and bokeh.")
        except Exception as e:
            print(f"Error generating visualization: {e}")
    
    def do_exit(self, arg):
        """Exit the interactive debugger."""
        if self.debug_session_active:
            confirm = input("Debugging session in progress. Are you sure? (y/n): ")
            if confirm.lower() != 'y':
                return
            
            # Save metrics before exiting
            self.metrics.finalize_run()
        
        print("Exiting Triangulum Interactive Debugger.")
        return True
    
    def do_help(self, arg):
        """Show help information."""
        if arg:
            # Help for specific command
            super().do_help(arg)
        else:
            # General help
            print("\nTriangulum LX Interactive Debugger Commands:")
            print("-------------------------------------------")
            print("  start    - Start a new debugging session")
            print("  status   - Show current debugging status")
            print("  step     - Advance simulation by one tick")
            print("  auto [n] - Run automatically for n steps")
            print("  reset    - Reset current debugging session")
            print("  feedback - Provide feedback on session")
            print("  viz      - Generate visualization")
            print("  exit     - Exit the debugger")
            print("  help     - Show this help message")
    
    def emptyline(self):
        """Do nothing on empty line."""
        pass


def launch_interactive_mode():
    """Launch the interactive debugger."""
    debugger = InteractiveDebugger()
    try:
        debugger.cmdloop()
    except KeyboardInterrupt:
        print("\nExiting on user interrupt...")
    except Exception as e:
        print(f"Unexpected error: {e}")
        
    print("Interactive session ended.")


if __name__ == "__main__":
    launch_interactive_mode()
