#!/usr/bin/env python3
"""
Triangulum System Enhancements

This script provides enhancements to the Triangulum debugging system, focusing on:
1. Better timeout handling for large files
2. More robust agent coordination to prevent loops
3. Improved tracking of cross-file fixes and their impacts

Usage:
  python fix_triangulum_enhancements_complete.py apply
"""

import os
import sys
import json
import time
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Any, Set

def enhance_timeout_handling():
    """
    Enhances timeout handling in debug_with_relationships.py and triangulum_folder_debugger.py
    
    Changes:
    1. Add adaptive timeouts based on file size
    2. Implement graceful timeout recovery
    3. Add checkpoint saving during long operations
    """
    print("Enhancing timeout handling...")
    
    # 1. Update debug_with_relationships.py
    debug_file = "debug_with_relationships.py"
    if os.path.exists(debug_file):
        with open(debug_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add adaptive timeout calculation based on file size
        if "def main():" in content and "adaptive_timeout" not in content:
            content = content.replace(
                "def main():",
                """def calculate_adaptive_timeout(file_path: str, base_timeout: int = 300) -> int:
    \"\"\"Calculate adaptive timeout based on file size and complexity.\"\"\"
    if not os.path.exists(file_path):
        return base_timeout
        
    # Get file size in KB
    file_size = os.path.getsize(file_path) / 1024
    
    # Count lines of code as a complexity measure
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            line_count = sum(1 for _ in f)
    except Exception:
        line_count = 100  # Default assumption
    
    # Calculate timeout: base + additional time for large/complex files
    timeout = base_timeout + min(600, int(file_size * 0.5) + int(line_count * 0.2))
    
    print(f"Adaptive timeout for {file_path}: {timeout} seconds")
    return timeout

def main():"
            )
            
            # Update subprocess call to use adaptive timeout
            if "subprocess.run" in content and "timeout=300" in content:
                content = content.replace(
                    "timeout=300",
                    "timeout=calculate_adaptive_timeout(file_path)"
                )
            
            # Add checkpoint saving mechanism
            if "# Run the debug cycle with adjusted verbosity" in content:
                content = content.replace(
                    "# Run the debug cycle with adjusted verbosity",
                    """# Set up checkpointing
        checkpoint_file = Path(args.log_dir) / f"checkpoint_{timestamp}.json"
        system.enable_checkpointing(checkpoint_file)
        
        # Run the debug cycle with adjusted verbosity"""
                )
                
            # Implement the checkpointing mechanism in the TriangulumGPT class
            if "class TriangulumGPT:" in content and "enable_checkpointing" not in content:
                checkpoint_method = """    def enable_checkpointing(self, checkpoint_path: Path):
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
                
                # Insert the checkpoint method before the _extract_next_agent method
                content = content.replace(
                    "    def _extract_next_agent",
                    checkpoint_method + "\n\n    def _extract_next_agent"
                )
                
                # Call checkpoint saving at key points in the debug cycle
                if "agent.actions_taken += 1" in content:
                    content = content.replace(
                        "agent.actions_taken += 1",
                        "agent.actions_taken += 1\n            self._save_checkpoint(bug)"
                    )
                
                # Initialize checkpoint attributes in __init__
                content = content.replace(
                    "        self.max_debug_iterations = 15  # Maximum number of debug iterations before forcing escalation",
                    "        self.max_debug_iterations = 15  # Maximum number of debug iterations before forcing escalation\n        self.use_checkpointing = False\n        self.checkpoint_path = None"
                )
            
            # Handle timeout exceptions more gracefully
            if "except subprocess.TimeoutExpired:" in content:
                content = content.replace(
                    "            except subprocess.TimeoutExpired:",
                    "            except subprocess.TimeoutExpired as timeout_err:\n                print(f\"\\nTimeout while debugging {file_path} after {timeout_err.timeout:.1f} seconds\")\n                print(\"Attempting to recover any partial results...\")"
                )
            
            # Write the updated content back to the file
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Enhanced timeout handling in {debug_file}")
    
    # 2. Update triangulum_folder_debugger.py
    folder_debugger = "triangulum_folder_debugger.py"
    if os.path.exists(folder_debugger):
        with open(folder_debugger, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add adaptive timeouts for file complexity
        if "def debug_file" in content and "adaptive_timeout" not in content:
            content = content.replace(
                "def debug_file",
                """def _calculate_timeout(self, file_path: str) -> int:
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
            )
            
            # Update subprocess timeout to use adaptive calculation
            if "timeout=300" in content:
                content = content.replace(
                    "timeout=300",
                    "timeout=self._calculate_timeout(file_path)"
                )
            
            # Improve error handling for timeouts
            if "except subprocess.TimeoutExpired:" in content:
                content = content.replace(
                    "except subprocess.TimeoutExpired:",
                    "except subprocess.TimeoutExpired as timeout_err:\n            logger.error(f\"Timeout ({timeout_err.timeout:.1f}s) while debugging {file_path}\")\n            # Try to recover partial results from log files\n            partial_results = self._recover_partial_results(file_path)"
                )
                
                # Add recovery method
                content = content.replace(
                    "    def debug_project",
                    """    def _recover_partial_results(self, file_path: str) -> Dict[str, Any]:
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
                )
            
            # Write the updated content back to the file
            with open(folder_debugger, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Enhanced timeout handling in {folder_debugger}")

def enhance_agent_coordination():
    """
    Improves agent coordination to prevent loops
    
    Changes:
    1. Add smarter agent selection based on task state
    2. Implement diversity-aware agent scheduling
    3. Add memory of past actions to avoid repetition
    """
    print("Enhancing agent coordination...")
    
    # Update debug_with_relationships.py to improve agent coordination
    debug_file = "debug_with_relationships.py"
    if os.path.exists(debug_file):
        with open(debug_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add agent diversity tracking
        if "class TriangulumGPT:" in content and "agent_diversity_score" not in content:
            # Add diversity tracking attributes to __init__
            content = content.replace(
                "        self.next_bug_id = 1",
                "        self.next_bug_id = 1\n        self.agent_selection_history = []\n        self.agent_effectiveness = {role: 1.0 for role in AGENTS}"
            )
            
            # Add method to calculate agent diversity score
            content = content.replace(
                "    def _extract_next_agent",
                """    def _calculate_agent_diversity_score(self, role: str, last_states: List[str]) -> float:
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
            )
            
            # Update the agent selection logic to use diversity score
            if "        # Look for specific agent assignments with deterministic language" in content:
                content = content.replace(
                    "        # Look for specific agent assignments with deterministic language",
                    """        # If coordinator strongly specifies an agent, use that
        strongly_specified_agent = None
        
        # Look for specific agent assignments with deterministic language"""
                )
                
                # Add diversity-aware selection logic before the return statement
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
            
            # Update agent tracking in run_debug_cycle
            if "            next_agent_role = self._extract_next_agent(coord_content)" in content:
                content = content.replace(
                    "            next_agent_role = self._extract_next_agent(coord_content)",
                    "            self.current_bug_state = bug.state  # Track current state for agent selection\n            next_agent_role = self._extract_next_agent(coord_content)"
                )
                
                # Track selected agent
                content = content.replace(
                    "            if not next_agent_role or next_agent_role not in self.agents:",
                    "            if not next_agent_role or next_agent_role not in self.agents:"
                )
                
                # Update agent selection history
                content = content.replace(
                    "            agent = self.agents[next_agent_role]",
                    "            # Track agent selection for diversity\n            if hasattr(self, 'agent_selection_history'):\n                self.agent_selection_history.append(next_agent_role)\n                \n            agent = self.agents[next_agent_role]"
                )
                
                # Add effectiveness tracking based on state changes
                if "            new_state = self._extract_new_state(agent_content, bug.state)" in content:
                    content = content.replace(
                        "            if new_state and new_state != bug.state:",
                        "            if new_state and new_state != bug.state:\n                # Agent was effective - reward it\n                if hasattr(self, 'agent_effectiveness') and next_agent_role in self.agent_effectiveness:\n                    self.agent_effectiveness[next_agent_role] = min(2.0, self.agent_effectiveness[next_agent_role] * 1.2)"
                    )
            
            # Write the updated content back to the file
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Enhanced agent coordination in {debug_file}")

def enhance_crossfile_tracking():
    """
    Implements cross-file fix tracking for better dependency management
    
    Changes:
    1. Track file changes across debugging sessions
    2. Detect and flag files that might be affected by fixes
    3. Add dependency-aware fix validation
    """
    print("Enhancing cross-file fix tracking...")
    
    # Create a new file for tracking cross-file dependencies and fixes
    tracking_file = "triangulum_lx/tooling/fix_impact_tracker.py"
    os.makedirs(os.path.dirname(tracking_file), exist_ok=True)
    
    # Write the tracking implementation
    with open(tracking_file, 'w', encoding='utf-8') as f:
        f.write("""#!/usr/bin/env python3
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
        \"\"\"Initialize the tracker.
        
        Args:
            project_path: Root path of the project
            database_path: Path to the fix database file (default: project_path/.triangulum/fix_database.json)
        \"\"\"
        self.project_path = Path(project_path)
        
        # Set up database location
        if database_path:
            self.database_path = Path(database_path)
        else:
            db_dir = self.project_path / ".triangulum"
            db_dir.mkdir(exist_ok=True)
            self.database_path = db_dir / "fix_database.json"
        
        # Load or initialize the database
        self.database = self._load_database()
        
        # Track files modified in the current session
        self.modified_files = set()
    
    def _load_database(self) -> Dict[str, Any]:
        \"\"\"Load the fix database or create a new one if it doesn't exist.\"\"\"
        if self.database_path.exists():
            try:
                with open(self.database_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading fix database: {e}")
        
        # Create a new database
        return {
            "version": 1,
            "last_updated": time.time(),
            "fixes": {},
            "dependencies": {},
            "impact_analysis": {}
        }
    
    def _save_database(self):
        \"\"\"Save the fix database.\"\"\"
        try:
            self.database["last_updated"] = time.time()
            with open(self.database_path, 'w', encoding='utf-8') as f:
                json.dump(self.database, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving fix database: {e}")
    
    def record_fix(self, file_path: str, original_content: str, fixed_content: str, 
                   bug_description: str, fix_description: str) -> str:
        \"\"\"Record a fix made to a file.
        
        Args:
            file_path: Path to the fixed file (relative to project_path)
            original_content: Original file content before the fix
            fixed_content: Updated file content after the fix
            bug_description: Description of the bug that was fixed
            fix_description: Description of the fix
            
        Returns:
            fix_id: Unique identifier for this fix
        \"\"\"
        # Convert to relative path
        rel_path = self._to_relative_path(file_path)
        
        # Generate a unique fix ID
        fix_id = f"fix_{int(time.time())}_{Path(rel_path).stem}"
        
        # Calculate diff
        diff = list(difflib.unified_diff(
            original_content.splitlines(), 
            fixed_content.splitlines(),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
            lineterm=''
        ))
        diff_text = '\\n'.join(diff)
        
        # Record the fix
        self.database["fixes"][fix_id] = {
            "file_path": rel_path,
            "timestamp": time.time(),
            "bug_description": bug_description,
            "fix_description": fix_description,
            "diff": diff_text
        }
        
        # Update the modified files set
        self.modified_files.add(rel_path)
        
        # Save the database
        self._save_database()
        
        # Run impact analysis
        self.analyze_fix_impact(fix_id)
        
        return fix_id
    
    def analyze_fix_impact(self, fix_id: str) -> Dict[str, Any]:
        \"\"\"Analyze the impact of a fix on dependent files.
        
        Args:
            fix_id: ID of the fix to analyze
            
        Returns:
            impact: Dictionary with impact analysis results
        \"\"\"
        if fix_id not in self.database["fixes"]:
            logger.error(f"Fix {fix_id} not found in database")
            return {"error": "Fix not found"}
        
        fix = self.database["fixes"][fix_id]
        file_path = fix["file_path"]
        
        # Look up dependencies
        impact = {
            "fix_id": fix_id,
            "file_path": file_path,
            "dependencies": {},
            "dependents": {},
            "risk_level": "low"
        }
        
        # Find files that depend on the modified file
        if file_path in self.database["dependencies"]:
            # Files that import/use this file (dependents)
            dependents = self.database["dependencies"][file_path].get("dependents", [])
            impact["dependents"] = {d: {"risk": "unknown"} for d in dependents}
            
            # Risk assessment based on number of dependents
            if len(dependents) > 10:
                impact["risk_level"] = "high"
            elif len(dependents) > 3:
                impact["risk_level"] = "medium"
                
            # Dependencies this file relies on
            dependencies = self.database["dependencies"][file_path].get("dependencies", [])
            impact["dependencies"] = {d: {"status": "unchanged"} for d in dependencies}
            
            # Check if any dependencies were also modified
            for dep in dependencies:
                if dep in self.modified_files:
                    impact["dependencies"][dep]["status"] = "modified"
                    # Multiple changes to dependent files increases risk
                    if impact["risk_level"] == "low":
                        impact["risk_level"] = "medium"
                    elif impact["risk_level"] == "medium":
                        impact["risk_level"] = "high"
        
        # Store the impact analysis
        self.database["impact_analysis"][fix_id] = impact
        self._save_database()
        
        return impact
    
    def update_dependencies(self, dependencies_data: Dict[str, Dict[str, List[str]]]):
        \"\"\"Update the dependency graph from external analysis.
        
        Args:
            dependencies_data: Dictionary mapping files to their dependencies and dependents
        \"\"\"
        self.database["dependencies"] = dependencies_data
        self._save_database()
        
        # Re-analyze the impact of recent fixes
        for fix_id in list(self.database["fixes"].keys())[-10:]:  # Last 10 fixes
            self.analyze_fix_impact(fix_id)
    
    def get_affected_files(self, fix_ids: List[str]) -> Set[str]:
        \"\"\"Get all files potentially affected by a set of fixes.
        
        Args:
            fix_ids: List of fix IDs to check
            
        Returns:
            affected_files: Set of file paths potentially affected
        \"\"\"
        affected = set()
        
        for fix_id in fix_ids:
            if fix_id in self.database["impact_analysis"]:
                impact = self.database["impact_analysis"][fix_id]
                affected.add(impact["file_path"])
                affected.update(impact["dependents"].keys())
        
        return affected
    
    def validate_fixes(self, fix_ids: List[str]) -> Dict[str, Any]:
        \"\"\"Validate that a set of fixes don't conflict or break dependencies.
        
        Args:
            fix_ids: List of fix IDs to validate
            
        Returns:
            validation_result: Dictionary with validation results
        \"\"\"
        # Get all affected files
        affected = self.get_affected_files(fix_ids)
        
        result = {
            "valid": True,
            "conflicts": [],
            "high_risk_changes": [],
            "fixes_validated": fix_ids,
            "affected_files": list(affected)
        }
        
        # Check for conflicts between fixes
        for i, fix_id1 in enumerate(fix_ids):
            if fix_id1 not in self.database["fixes"]:
                continue
                
            file1 = self.database["fixes"][fix_id1]["file_path"]
            
            for fix_id2 in fix_ids[i+1:]:
                if fix_id2 not in self.database["fixes"]:
                    continue
                    
                file2 = self.database["fixes"][fix_id2]["file_path"]
                
                # If two fixes modify the same file, potential conflict
                if file1 == file2:
                    result["conflicts"].append({
                        "file": file1,
                        "fixes": [fix_id1, fix_id2]
                    })
                    result["valid"] = False
        
        # Check for high-risk changes
        for fix_id in fix_ids:
            if fix_id in self.database["impact_analysis"]:
                impact = self.database["impact_analysis"][fix_id]
                if impact["risk_level"] == "high":
                    result["high_risk_changes"].append({
                        "fix_id": fix_id,
                        "file": impact["file_path"],
                        "dependents": len(impact["dependents"])
                    })
        
        return result
    
    def _to_relative_path(self, file_path: str) -> str:
        \"\"\"Convert an absolute path to a path relative to project_path.\"\"\"
        path = Path(file_path)
        if path.is_absolute():
            try:
                return str(path.relative_to(self.project_path))
            except ValueError:
                # Not relative to project_path
                return str(path)
        return str(path)
    
    def suggest_tests(self, fix_ids: List[str]) -> List[str]:
        \"\"\"Suggest tests to run to validate fixes.
        
        Args:
            fix_ids: List of fix IDs to check
            
        Returns:
            test_paths: List of test file paths to run
        \"\"\"
        affected = self.get_affected_files(fix_ids)
        tests = []
        
        for file in affected:
            # Look for corresponding test files
            file_path = Path(file)
            
            test_candidates = [
                self.project_path / "tests" / file_path.parent / f"test_{file_path.name}",
                self.project_path / "tests" / file_path.parent / f"{file_path.stem}_test{file_path.suffix}",
                self.project_path / file_path.parent / "tests" / f"test_{file_path.name}",
                self.project_path / file_path.parent / "tests" / f"{file_path.stem}_test{file_path.suffix}",
            ]
            
            for test in test_candidates:
                if test.exists():
                    tests.append(str(test.relative_to(self.project_path)))
        
        return tests
""")
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
        
        # Add fix tracking code to debug_file method
        if "            # Add to debug results" in content:
            content = content.replace(
                "            # Add to debug results",
                """            # Track the fix impact if there was a successful fix
            if result["success"] and "Bug successfully fixed" in output:
                try:
                    # Get fixed content from the file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        fixed_content = f.read()
                    
                    # Try to find the original content in the debug log
                    original_content = fixed_content  # Default fallback
                    bug_description = "Unknown bug"
                    fix_description = "Unknown fix"
                    
                    # Look for the most recent log file
                    log_files = list(self.output_dir.glob(f"debug_session_*_{Path(file_path).stem}*.md"))
                    if log_files:
                        log_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                        latest_log = log_files[0]
                        
                        with open(latest_log, 'r', encoding='utf-8') as f:
                            log_content = f.read()
                            
                        # Try to extract the original code from the log
                        if "Original Code:" in log_content and "Fixed Code:"
