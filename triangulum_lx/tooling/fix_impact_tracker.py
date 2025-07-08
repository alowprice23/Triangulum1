#!/usr/bin/env python3
"""
Fix Impact Tracker

Tracks the impact of fixes across multiple files, identifying potential
cross-file dependencies and validating that fixes don't break dependencies.
"""

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
    """Tracks the impact of fixes across files with dependencies."""
    
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
            "diff": "\n".join(diff)
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
