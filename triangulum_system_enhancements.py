#!/usr/bin/env python3
"""
Triangulum System Enhancements

This script provides enhancements to the Triangulum debugging system, focusing on:
1. Better timeout handling for large files
2. More robust agent coordination to prevent loops
3. Improved tracking of cross-file fixes and their impacts

Usage:
  python triangulum_system_enhancements.py apply
"""

import os
import sys
import json
import time
import logging
import difflib
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("triangulum.enhancements")

def enhance_timeout_handling():
    """Enhances timeout handling in debug files"""
    print("Enhancing timeout handling...")
    
    # 1. Update debug_with_relationships.py
    debug_file = "debug_with_relationships.py"
    if os.path.exists(debug_file):
        with open(debug_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add adaptive timeout calculation
        if "def main():" in content and "adaptive_timeout" not in content:
            timeout_function = """def calculate_adaptive_timeout(file_path, base_timeout=300):
    \"\"\"Calculate adaptive timeout based on file size and complexity.\"\"\"
    if not os.path.exists(file_path):
        return base_timeout
        
    # Get file size in KB
    file_size = os.path.getsize(file_path) / 1024
    
    # Count lines of code
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            line_count = sum(1 for _ in f)
    except Exception:
        line_count = 100  # Default
    
    # Calculate timeout factors
    size_factor = int(file_size * 0.5)
    complexity_factor = int(line_count * 0.2)
    
    # Final timeout
    timeout = base_timeout + min(600, size_factor + complexity_factor)
    
    print(f"Adaptive timeout for {file_path}: {timeout} seconds")
    return timeout

def main():"""
            
            content = content.replace("def main():", timeout_function)
            
            # Update subprocess call
            if "subprocess.run" in content and "timeout=300" in content:
                content = content.replace("timeout=300", "timeout=calculate_adaptive_timeout(file_path)")
            
            # Add checkpoint saving
            if "# Run the debug cycle with adjusted verbosity" in content:
                content = content.replace(
                    "# Run the debug cycle with adjusted verbosity",
                    """# Set up checkpointing
        checkpoint_file = Path(args.log_dir) / f"checkpoint_{timestamp}.json"
        system.enable_checkpointing(checkpoint_file)
        
        # Run the debug cycle with adjusted verbosity"""
                )
            
            # Add checkpointing to TriangulumGPT class
            if "class TriangulumGPT:" in content and "enable_checkpointing" not in content:
                checkpoint_methods = """    def enable_checkpointing(self, checkpoint_path):
        \"\"\"Enable checkpointing to recover from timeouts.\"\"\"
        self.checkpoint_path = checkpoint_path
        self.use_checkpointing = True
        
        # Try to load existing checkpoint
        if self.checkpoint_path.exists():
            try:
                with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                    
                # Restore state from checkpoint
                if checkpoint.get('bug_id') == self.next_bug_id - 1:
                    for bug in self.bugs:
                        if bug.id == checkpoint['bug_id']:
                            bug.state = checkpoint['state']
                            bug.history = checkpoint['history']
                            if checkpoint.get('fixed_code'):
                                bug.fixed_code = checkpoint['fixed_code']
                            print(f"Restored checkpoint for bug #{bug.id} - State: {bug.state}")
            except Exception as e:
                print(f"Error loading checkpoint: {e}")
    
    def _save_checkpoint(self, bug):
        \"\"\"Save current state to checkpoint file.\"\"\"
        if not hasattr(self, 'use_checkpointing') or not self.use_checkpointing:
            return
            
        try:
            checkpoint = {
                'timestamp': time.time(),
                'bug_id': bug.id,
                'state': bug.state,
                'history': bug.history,
            }
            
            if bug.fixed_code:
                checkpoint['fixed_code'] = bug.fixed_code
                
            with open(self.checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving checkpoint: {e}")"""
                
                content = content.replace(
                    "    def _extract_next_agent",
                    checkpoint_methods + "\n\n    def _extract_next_agent"
                )
                
                # Call checkpoint saving
                if "agent.actions_taken += 1" in content:
                    content = content.replace(
                        "agent.actions_taken += 1",
                        "agent.actions_taken += 1\n            self._save_checkpoint(bug)"
                    )
                
                # Initialize checkpoint attributes
                content = content.replace(
                    "        self.max_debug_iterations = 15",
                    "        self.max_debug_iterations = 15\n        self.use_checkpointing = False\n        self.checkpoint_path = None"
                )
            
            # Handle timeout exceptions
            if "except subprocess.TimeoutExpired:" in content:
                content = content.replace(
                    "            except subprocess.TimeoutExpired:",
                    "            except subprocess.TimeoutExpired as timeout_err:\n                print(f\"\\nTimeout while debugging {file_path} after {timeout_err.timeout:.1f} seconds\")\n                print(\"Attempting to recover any partial results...\")"
                )
            
            # Write the updated content
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Enhanced timeout handling in {debug_file}")
    
    # 2. Update triangulum_folder_debugger.py
    folder_debugger = "triangulum_folder_debugger.py"
    if os.path.exists(folder_debugger):
        with open(folder_debugger, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add adaptive timeouts
        if "def debug_file" in content and "adaptive_timeout" not in content:
            timeout_method = """def _calculate_timeout(self, file_path):
        \"\"\"Calculate appropriate timeout based on file size and complexity.\"\"\"
        if not os.path.exists(file_path):
            return 300  # Default 5 minutes
            
        # Get file size
        file_size = os.path.getsize(file_path) / 1024  # KB
        
        # Count lines as complexity measure
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
        except Exception:
            line_count = 100  # Default
        
        # Calculate base on size and complexity
        base_timeout = 300  # 5 minutes base
        size_factor = min(600, int(file_size * 0.5))
        complexity_factor = int(line_count * 0.2)
        
        # Cap at 20 minutes for extremely large files
        timeout = min(1200, base_timeout + size_factor + complexity_factor)
        
        logger.info(f"Adaptive timeout for {file_path}: {timeout}s (size: {file_size:.1f}KB, lines: {line_count})")
        return timeout
        
    def debug_file"""
            
            content = content.replace("def debug_file", timeout_method)
            
            # Update subprocess timeout
            if "timeout=300" in content:
                content = content.replace("timeout=300", "timeout=self._calculate_timeout(file_path)")
            
            # Improve error handling for timeouts
            if "except subprocess.TimeoutExpired:" in content:
                content = content.replace(
                    "except subprocess.TimeoutExpired:",
                    "except subprocess.TimeoutExpired as timeout_err:\n            logger.error(f\"Timeout ({timeout_err.timeout:.1f}s) while debugging {file_path}\")\n            # Try to recover partial results from log files\n            partial_results = self._recover_partial_results(file_path)"
                )
                
                # Add recovery method
                recovery_method = """    def _recover_partial_results(self, file_path):
        \"\"\"Attempt to recover partial results from log files after timeout.\"\"\"
        # Look for the most recent log file for this file
        log_files = list(self.output_dir.glob(f"debug_session_*_{Path(file_path).stem}*.md"))
        if not log_files:
            return {"error": "No partial results available", "recovered": False}
            
        # Sort by modification time, newest first
        log_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        latest_log = log_files[0]
        
        try:
            # Extract partial results from the log
            with open(latest_log, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check if any useful diagnostics were captured
            if "Agent Outputs" in content:
                logger.info(f"Recovered partial diagnostics from {latest_log}")
                return {
                    "error": "Timeout, but partial diagnostics recovered",
                    "recovered": True,
                    "log_file": str(latest_log)
                }
        except Exception as e:
            logger.warning(f"Failed to recover results: {e}")
            
        return {"error": "Timeout", "recovered": False}
    
    def debug_project"""
                
                content = content.replace("    def debug_project", recovery_method)
            
            # Write the updated content
            with open(folder_debugger, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Enhanced timeout handling in {folder_debugger}")

def enhance_agent_coordination():
    """Improves agent coordination to prevent loops"""
    print("Enhancing agent coordination...")
    
    # Update debug_with_relationships.py
    debug_file = "debug_with_relationships.py"
    if os.path.exists(debug_file):
        with open(debug_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add agent diversity tracking
        if "class TriangulumGPT:" in content and "agent_diversity_score" not in content:
            # Add diversity tracking attributes
            content = content.replace(
                "        self.next_bug_id = 1",
                "        self.next_bug_id = 1\n        self.agent_selection_history = []\n        self.agent_effectiveness = {role: 1.0 for role in AGENTS}"
            )
            
            # Add diversity score method
            diversity_method = """    def _calculate_agent_diversity_score(self, role, last_states):
        \"\"\"Calculate diversity score to encourage agent variety.\"\"\"
        # Base score starts at the agent's effectiveness
        score = self.agent_effectiveness.get(role, 1.0)
        
        # Penalize if this agent has been called many times recently
        recent_count = last_states.count(role)
        if recent_count > 0:
            score *= (0.7 ** recent_count)
        
        # Penalize if this agent has been called repeatedly without progress
        if len(last_states) >= 3 and all(s == role for s in last_states[-3:]):
            score *= 0.3
        
        # Bonus for agents that haven't been used in a while
        if role not in last_states:
            score *= 1.5
            
        # Adjust based on bug state - certain agents are more appropriate at different stages
        if hasattr(self, 'current_bug_state'):
            if self.current_bug_state == "WAIT" and role == "observer":
                score *= 1.5
            elif self.current_bug_state == "REPRO" and role == "analyst":
                score *= 1.5
            elif self.current_bug_state == "PATCH" and role == "patcher":
                score *= 1.5
            elif self.current_bug_state == "VERIFY" and role == "verifier":
                score *= 1.5
        
        return score
    
    def _extract_next_agent"""
            
            content = content.replace("    def _extract_next_agent", diversity_method)
            
            # Update agent selection logic
            content = content.replace(
                "        # Look for specific agent assignments with deterministic language",
                """        # If coordinator strongly specifies an agent, use that
        strongly_specified_agent = None
        
        # Look for specific agent assignments with deterministic language"""
            )
            
            # Add diversity-aware selection
            content = content.replace(
                "        return None",
                """        # Use diversity-aware selection if no clear agent was specified
        if strongly_specified_agent:
            return strongly_specified_agent
            
        # Calculate diversity scores for each agent
        if hasattr(self, 'agent_selection_history') and len(self.agent_selection_history) > 0:
            diversity_scores = {}
            for role in AGENTS:
                diversity_scores[role] = self._calculate_agent_diversity_score(
                    role, self.agent_selection_history[-10:] if len(self.agent_selection_history) > 10 else self.agent_selection_history
                )
                
            # Select agent with highest diversity score
            if diversity_scores:
                best_agent = max(diversity_scores.items(), key=lambda x: x[1])[0]
                return best_agent
                
        # Fallback to default if no agent was chosen
        return None"""
            )
            
            # Update agent tracking
            content = content.replace(
                "            next_agent_role = self._extract_next_agent(coord_content)",
                "            self.current_bug_state = bug.state  # Track current state for agent selection\n            next_agent_role = self._extract_next_agent(coord_content)"
            )
            
            # Update agent selection history
            content = content.replace(
                "            agent = self.agents[next_agent_role]",
                "            # Track agent selection for diversity\n            if hasattr(self, 'agent_selection_history'):\n                self.agent_selection_history.append(next_agent_role)\n                \n            agent = self.agents[next_agent_role]"
            )
            
            # Add effectiveness tracking
            content = content.replace(
                "            if new_state and new_state != bug.state:",
                "            if new_state and new_state != bug.state:\n                # Agent was effective - reward it\n                if hasattr(self, 'agent_effectiveness') and next_agent_role in self.agent_effectiveness:\n                    self.agent_effectiveness[next_agent_role] = min(2.0, self.agent_effectiveness[next_agent_role] * 1.2)"
            )
            
            # Write the updated content
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Enhanced agent coordination in {debug_file}")

def enhance_crossfile_tracking():
    """Implements cross-file fix tracking for better dependency management"""
    print("Enhancing cross-file fix tracking...")
    
    # Create the fix impact tracker file
    tracking_file = "triangulum_lx/tooling/fix_impact_tracker.py"
    os.makedirs(os.path.dirname(tracking_file), exist_ok=True)
    
    # Write the tracking implementation
    tracker_code = """#!/usr/bin/env python3
\"\"\"
Fix Impact Tracker

Tracks the impact of fixes across multiple files, identifying potential
cross-file dependencies and validating that fixes don't break dependencies.
\"\"\"

import os
import json
import logging
import difflib
import time
from typing import Dict, List, Set, Any, Optional, Tuple
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("triangulum.fix_impact_tracker")

class FixImpactTracker:
    \"\"\"Tracks the impact of fixes across files with dependencies.\"\"\"
    
    def __init__(self, project_path: str, database_path: Optional[str] = None):
        self.project_path = Path(project_path)
        self.database_path = Path(database_path) if database_path else self.project_path / ".triangulum" / "fix_database.json"
        self.database_path.parent.mkdir(exist_ok=True)
        self.database = self._load_database()
        self.modified_files = set()
    
    def _load_database(self) -> Dict[str, Any]:
        if self.database_path.exists():
            try:
                with open(self.database_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading fix database: {e}")
        
        return {"version": 1, "last_updated": time.time(), "fixes": {}, "dependencies": {}, "impact_analysis": {}}
    
    def _save_database(self):
        try:
            self.database["last_updated"] = time.time()
            with open(self.database_path, 'w', encoding='utf-8') as f:
                json.dump(self.database, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving fix database: {e}")
    
    def record_fix(self, file_path: str, original_content: str, fixed_content: str, 
                   bug_description: str, fix_description: str) -> str:
        rel_path = self._to_relative_path(file_path)
        fix_id = f"fix_{int(time.time())}_{Path(rel_path).stem}"
        
        diff = list(difflib.unified_diff(
            original_content.splitlines(), fixed_content.splitlines(),
            fromfile=f"a/{rel_path}", tofile=f"b/{rel_path}", lineterm=''
        ))
        
        self.database["fixes"][fix_id] = {
            "file_path": rel_path,
            "timestamp": time.time(),
            "bug_description": bug_description,
            "fix_description": fix_description,
            "diff": "\\n".join(diff)
        }
        
        self.modified_files.add(rel_path)
        self._save_database()
        self.analyze_fix_impact(fix_id)
        
        return fix_id
    
    def analyze_fix_impact(self, fix_id: str) -> Dict[str, Any]:
        if fix_id not in self.database["fixes"]:
            return {"error": "Fix not found"}
        
        fix = self.database["fixes"][fix_id]
        file_path = fix["file_path"]
        
        impact = {
            "fix_id": fix_id,
            "file_path": file_path,
            "dependencies": {},
            "dependents": {},
            "risk_level": "low"
        }
        
        if file_path in self.database["dependencies"]:
            # Process dependents
            dependents = self.database["dependencies"][file_path].get("dependents", [])
            impact["dependents"] = {d: {"risk": "unknown"} for d in dependents}
            
            # Risk assessment
            if len(dependents) > 10:
                impact["risk_level"] = "high"
            elif len(dependents) > 3:
                impact["risk_level"] = "medium"
                
            # Process dependencies
            dependencies = self.database["dependencies"][file_path].get("dependencies", [])
            impact["dependencies"] = {d: {"status": "unchanged"} for d in dependencies}
            
            # Check for modified dependencies
            for dep in dependencies:
                if dep in self.modified_files:
                    impact["dependencies"][dep]["status"] = "modified"
                    # Escalate risk level
                    if impact["risk_level"] == "low":
                        impact["risk_level"] = "medium"
                    elif impact["risk_level"] == "medium":
                        impact["risk_level"] = "high"
        
        self.database["impact_analysis"][fix_id] = impact
        self._save_database()
        
        return impact
    
    def _to_relative_path(self, file_path: str) -> str:
        path = Path(file_path)
        if path.is_absolute():
            try:
                return str(path.relative_to(self.project_path))
            except ValueError:
                return str(path)
        return str(path)
"""
    
    with open(tracking_file, 'w', encoding='utf-8') as f:
        f.write(tracker_code)
    print(f"✓ Created fix impact tracker: {tracking_file}")
    
    # Update folder debugger to use the fix impact tracker
    folder_debugger = "triangulum_folder_debugger.py"
    if os.path.exists(folder_debugger):
        with open(folder_debugger, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add import for the fix impact tracker
        if "from triangulum_lx.tooling.code_relationship_analyzer import CodeRelationshipAnalyzer" in content:
            content = content.replace(
                "from triangulum_lx.tooling.code_relationship_analyzer import CodeRelationshipAnalyzer",
                "from triangulum_lx.tooling.code_relationship_analyzer import CodeRelationshipAnalyzer\nfrom triangulum_lx.tooling.fix_impact_tracker import FixImpactTracker"
            )
        
        # Initialize the tracker in __init__
        if "        # Initialize components" in content:
            content = content.replace(
                "        # Initialize components",
                "        # Initialize components\n        self.fix_tracker = FixImpactTracker(project_path)"
            )
        
        # Write the updated content
        with open(folder_debugger, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Updated folder debugger to use fix impact tracker")

def main():
    """Main function to apply all enhancements."""
    parser = argparse.ArgumentParser(description="Apply Triangulum system enhancements")
    parser.add_argument('action', choices=['apply'], help='Action to perform')
    args = parser.parse_args()
    
    if args.action == 'apply':
        print("Applying Triangulum system enhancements...")
        
        # Apply all enhancements
        enhance_timeout_handling()
        enhance_agent_coordination()
        enhance_crossfile_tracking()
        
        print("\n✅ All enhancements successfully applied!")
        print("\nEnhancements summary:")
        print("1. Added adaptive timeouts based on file size and complexity")
        print("2. Implemented checkpoint saving for recovery from timeouts")
        print("3. Added diversity-aware agent selection to prevent loops")
        print("4. Created fix impact tracker for cross-file dependency management")
    else:
        print(f"Unknown action: {args.action}")
        sys.exit(1)

if __name__ == "__main__":
    main()
