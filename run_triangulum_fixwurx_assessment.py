#!/usr/bin/env python3
"""
Triangulum-FixWurx Baseline Assessment Script

This script implements Phase 1 of the Triangulum-FixWurx Evaluation Plan.
It performs a comprehensive baseline assessment of the FixWurx codebase
to gather data about its current state, relationships, and issues.

Usage:
    python run_triangulum_fixwurx_assessment.py [--fixwurx-dir PATH] [--output-dir PATH]
"""

import os
import sys
import json
import time
import logging
import argparse
import shutil
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("triangulum_fixwurx_assessment.log")
    ]
)
logger = logging.getLogger("triangulum_fixwurx_assessment")

# Add the current directory to the path so we can import our modules
sys.path.append('.')

# Import Triangulum components
try:
    from triangulum_lx.tooling.dependency_graph import DependencyGraphBuilder
    from triangulum_lx.agents.bug_detector_agent import BugDetectorAgent
    from triangulum_lx.agents.relationship_analyst_agent import RelationshipAnalystAgent
    from triangulum_lx.agents.message_bus import MessageBus
    from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus
    from triangulum_lx.agents.message import AgentMessage, MessageType
    from fix_timeout_and_progress_minimal import (
        TimeoutManager, ProgressManager, TimeoutConfig, TimeoutPolicy,
        ProgressStatus, with_timeout, with_progress, get_timeout_manager,
        get_progress_manager
    )
    
    logger.info("Successfully imported Triangulum components")
except ImportError as e:
    logger.error(f"Failed to import Triangulum components: {e}")
    sys.exit(1)

# Initialize managers for progress tracking
timeout_manager = get_timeout_manager()
progress_manager = get_progress_manager()

class FixWurxAssessment:
    """Class to perform baseline assessment of FixWurx."""
    
    def __init__(self, fixwurx_dir: str, output_dir: str):
        """
        Initialize the assessment.
        
        Args:
            fixwurx_dir: Path to the FixWurx directory
            output_dir: Path to store assessment results
        """
        self.fixwurx_dir = os.path.abspath(fixwurx_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.snapshot_dir = os.path.join(self.output_dir, "fixwurx_snapshot")
        self.assessment_dir = os.path.join(self.output_dir, "fixwurx_assessment")
        self.visualization_dir = os.path.join(self.assessment_dir, "visualizations")
        self.cache_dir = os.path.join(self.output_dir, "cache")
        
        # Create message bus for agent communication
        self.message_bus = EnhancedMessageBus()
        
        # Initialize agents
        self.bug_detector = BugDetectorAgent(message_bus=self.message_bus)
        self.relationship_analyst = RelationshipAnalystAgent(
            agent_id="relationship_analyst",
            name="Relationship Analyst",
            cache_dir=self.cache_dir,
            message_bus=self.message_bus
        )
        
        # Initialize results storage
        self.dependency_graph = None
        self.bugs_report = None
        self.relationship_report = None
        self.component_inventory = {}
        self.missing_connections = []
        
        logger.info(f"FixWurx Assessment initialized with fixwurx_dir={fixwurx_dir}, output_dir={output_dir}")
    
    def setup_directories(self):
        """Set up the directory structure for assessment."""
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.snapshot_dir, exist_ok=True)
        os.makedirs(self.assessment_dir, exist_ok=True)
        os.makedirs(self.visualization_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        logger.info(f"Directory structure set up at {self.output_dir}")
    
    def create_snapshot(self):
        """Create a snapshot of the current FixWurx state."""
        logger.info(f"Creating snapshot of FixWurx from {self.fixwurx_dir} to {self.snapshot_dir}")
        
        try:
            # Remove existing snapshot if it exists
            if os.path.exists(self.snapshot_dir):
                shutil.rmtree(self.snapshot_dir)
            
            # Create the snapshot directory
            os.makedirs(self.snapshot_dir, exist_ok=True)
            
            # Copy all files from FixWurx to the snapshot directory
            for root, dirs, files in os.walk(self.fixwurx_dir):
                # Skip .git and __pycache__ directories
                if '.git' in dirs:
                    dirs.remove('.git')
                if '__pycache__' in dirs:
                    dirs.remove('__pycache__')
                    
                # Get relative path from FixWurx directory
                rel_path = os.path.relpath(root, self.fixwurx_dir)
                if rel_path == '.':
                    rel_path = ''
                
                # Create the corresponding directory in the snapshot
                snapshot_root = os.path.join(self.snapshot_dir, rel_path)
                os.makedirs(snapshot_root, exist_ok=True)
                
                # Copy all files
                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(snapshot_root, file)
                    shutil.copy2(src_file, dst_file)
            
            logger.info(f"Snapshot created successfully at {self.snapshot_dir}")
            return True
        except Exception as e:
            logger.error(f"Error creating snapshot: {e}")
            return False
    
    @with_progress(name="Dependency Graph Analysis", steps=[
        "Initialize Graph Builder", "Build Graph", "Extract Dependencies", "Save Results"
    ])
    def analyze_dependencies(self, operation_id=None):
        """
        Analyze dependencies in the FixWurx codebase.
        
        Args:
            operation_id: Progress operation ID
        
        Returns:
            bool: True if analysis was successful, False otherwise
        """
        try:
            # Step 1: Initialize Graph Builder
            progress_manager.update_progress(operation_id, 0, 0.0, "Initializing dependency graph builder...")
            builder = DependencyGraphBuilder(cache_dir=self.cache_dir)
            progress_manager.update_progress(operation_id, 0, 1.0, "Dependency graph builder initialized")
            
            # Step 2: Build Graph
            progress_manager.update_progress(operation_id, 1, 0.0, "Building dependency graph...")
            self.dependency_graph = builder.build_graph(self.fixwurx_dir)
            progress_manager.update_progress(
                operation_id, 1, 1.0, 
                f"Dependency graph built with {len(self.dependency_graph)} nodes"
            )
            
            # Step 3: Extract Dependencies
            progress_manager.update_progress(operation_id, 2, 0.0, "Extracting dependencies...")
            
            # Save the graph to file
            graph_file = os.path.join(self.assessment_dir, "dependency_graph.json")
            with open(graph_file, 'w', encoding='utf-8') as f:
                json.dump(self.dependency_graph.to_dict(), f, indent=2)
            
            # Extract missing connections
            self.missing_connections = self.identify_missing_connections()
            
            progress_manager.update_progress(
                operation_id, 2, 1.0, 
                f"Dependencies extracted, found {len(self.missing_connections)} potential missing connections"
            )
            
            # Step 4: Save Results
            progress_manager.update_progress(operation_id, 3, 0.0, "Saving dependency analysis results...")
            
            # Create a summary report
            dependency_summary = {
                "total_files": len(self.dependency_graph),
                "total_dependencies": len(list(self.dependency_graph.edges())),
                "disconnected_components": self.find_disconnected_components(),
                "missing_connections": self.missing_connections,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            # Save the summary report
            summary_file = os.path.join(self.assessment_dir, "dependency_summary.json")
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(dependency_summary, f, indent=2)
            
            progress_manager.update_progress(operation_id, 3, 1.0, "Dependency analysis results saved")
            
            logger.info(f"Dependency analysis completed and saved to {self.assessment_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error analyzing dependencies: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def identify_missing_connections(self):
        """
        Identify potential missing connections in the codebase.
        
        Returns:
            list: List of potential missing connections
        """
        missing_connections = []
        
        # Find files that seem related but don't have a direct dependency
        files = list(self.dependency_graph)  # This returns the string paths, not FileNode objects
        
        for i, file1 in enumerate(files):
            for file2 in files[i+1:]:
                # Skip if already directly connected
                if self.dependency_graph.get_edge(file1, file2) is not None or self.dependency_graph.get_edge(file2, file1) is not None:
                    continue
                
                # Check if they might be related based on naming or module structure
                file1_path = str(file1)
                file2_path = str(file2)
                
                # Simple heuristic: files in same directory with similar names might be related
                file1_name = os.path.basename(file1_path)
                file2_name = os.path.basename(file2_path)
                file1_dir = os.path.dirname(file1_path)
                file2_dir = os.path.dirname(file2_path)
                
                # Look for similarities
                if file1_dir == file2_dir:
                    # Files in same directory
                    name_similarity = self.compute_name_similarity(file1_name, file2_name)
                    if name_similarity > 0.7:  # Threshold for similarity
                        missing_connections.append({
                            "file1": file1_path,
                            "file2": file2_path,
                            "reason": "Same directory with similar names",
                            "similarity": name_similarity
                        })
        
        return missing_connections
    
    def compute_name_similarity(self, name1, name2):
        """
        Compute similarity between two file names.
        
        Args:
            name1: First file name
            name2: Second file name
            
        Returns:
            float: Similarity score between 0 and 1
        """
        # Remove extensions
        name1 = os.path.splitext(name1)[0]
        name2 = os.path.splitext(name2)[0]
        
        # Simple Jaccard similarity on character sets
        set1 = set(name1.lower())
        set2 = set(name2.lower())
        
        if not set1 or not set2:
            return 0.0
            
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union
    
    def find_disconnected_components(self):
        """
        Find disconnected components in the dependency graph.
        
        Returns:
            list: List of disconnected components
        """
        # Use a simple depth-first search to find connected components
        visited = set()
        components = []
        
        def dfs(node, component):
            visited.add(node)
            component.append(str(node))
            
            # Visit outgoing edges
            for edge in self.dependency_graph.get_outgoing_edges(node):
                if edge.target not in visited:
                    dfs(edge.target, component)
            
            # Visit incoming edges
            for edge in self.dependency_graph.get_incoming_edges(node):
                if edge.source not in visited:
                    dfs(edge.source, component)
        
        # Find all connected components
        for node in self.dependency_graph:  # This returns the string paths, not FileNode objects
            if node not in visited:
                component = []
                dfs(node, component)
                components.append(component)
        
        return components
    
    @with_progress(name="Bug Detection", steps=[
        "Initialize Bug Detector", "Detect Bugs", "Process Results", "Save Bug Report"
    ])
    def detect_bugs(self, operation_id=None):
        """
        Detect bugs in the FixWurx codebase.
        
        Args:
            operation_id: Progress operation ID
            
        Returns:
            bool: True if detection was successful, False otherwise
        """
        try:
            # Step 1: Initialize Bug Detector
            progress_manager.update_progress(operation_id, 0, 0.0, "Initializing bug detector...")
            # Bug detector already initialized in __init__
            progress_manager.update_progress(operation_id, 0, 1.0, "Bug detector initialized")
            
            # Step 2: Detect Bugs
            progress_manager.update_progress(operation_id, 1, 0.0, "Detecting bugs in FixWurx...")
            
            # Detect bugs using the bug detector agent
            self.bugs_report = self.bug_detector.detect_bugs_in_folder(
                self.fixwurx_dir, 
                recursive=True
            )
            
            progress_manager.update_progress(
                operation_id, 1, 1.0, 
                f"Bug detection completed, found {self.bugs_report.get('total_bugs', 0)} bugs"
            )
            
            # Step 3: Process Results
            progress_manager.update_progress(operation_id, 2, 0.0, "Processing bug detection results...")
            
            # Process the bug report
            bugs_by_file = self.bugs_report.get('bugs_by_file', {})
            bug_counts_by_type = {}
            
            for file_path, bugs in bugs_by_file.items():
                for bug in bugs:
                    # DetectedBug is an object, not a dictionary, so access attributes directly
                    bug_type = getattr(bug, 'type', 'unknown')
                    if bug_type not in bug_counts_by_type:
                        bug_counts_by_type[bug_type] = 0
                    bug_counts_by_type[bug_type] += 1
            
            progress_manager.update_progress(
                operation_id, 2, 1.0, 
                f"Bug detection results processed, found {len(bug_counts_by_type)} bug types"
            )
            
            # Step 4: Save Bug Report
            progress_manager.update_progress(operation_id, 3, 0.0, "Saving bug report...")
            
            # Helper function to convert non-JSON-serializable objects to serializable values
            def serialize_value(value):
                # Handle Enum types
                if hasattr(value, '__class__') and hasattr(value.__class__, '__module__') and 'enum' in value.__class__.__module__.lower():
                    return value.name if hasattr(value, 'name') else str(value)
                
                # Handle complex objects with __dict__
                if hasattr(value, '__dict__'):
                    obj_dict = {}
                    for k, v in value.__dict__.items():
                        # Skip private attributes
                        if not k.startswith('_'):
                            obj_dict[k] = serialize_value(v)
                    return obj_dict
                
                # Handle dictionaries recursively
                if isinstance(value, dict):
                    return {k: serialize_value(v) for k, v in value.items()}
                
                # Handle lists and tuples recursively
                if isinstance(value, (list, tuple)):
                    return [serialize_value(item) for item in value]
                
                # Return primitive values as is
                return value
            
            # Helper function to convert DetectedBug objects to dictionaries
            def serialize_bug(bug):
                return serialize_value(bug)
            
            # Convert bugs report to a serializable format
            serializable_report = {}
            for key, value in self.bugs_report.items():
                if key == 'bugs_by_file':
                    # Special handling for bugs_by_file
                    bugs_dict = {}
                    for file_path, bugs in value.items():
                        # Convert each bug in the list to a dictionary
                        bugs_dict[file_path] = [serialize_bug(bug) for bug in bugs]
                    serializable_report[key] = bugs_dict
                else:
                    serializable_report[key] = value
            
            # Save the full bug report
            bug_report_file = os.path.join(self.assessment_dir, "bug_report.json")
            with open(bug_report_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_report, f, indent=2)
            
            # Save a summary of the bug report
            # Convert bug_counts_by_type to use string keys instead of enum objects
            serializable_bug_counts = {}
            for bug_type, count in bug_counts_by_type.items():
                # Convert enum to string if it's an enum
                if hasattr(bug_type, '__class__') and hasattr(bug_type.__class__, '__module__') and 'enum' in bug_type.__class__.__module__.lower():
                    key = bug_type.name if hasattr(bug_type, 'name') else str(bug_type)
                else:
                    key = str(bug_type)
                serializable_bug_counts[key] = count
                
            bug_summary = {
                "total_bugs": self.bugs_report.get('total_bugs', 0),
                "files_with_bugs": len(bugs_by_file),
                "bug_counts_by_type": serializable_bug_counts,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            summary_file = os.path.join(self.assessment_dir, "bug_summary.json")
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(bug_summary, f, indent=2)
            
            progress_manager.update_progress(operation_id, 3, 1.0, "Bug report saved")
            
            logger.info(f"Bug detection completed and saved to {self.assessment_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error detecting bugs: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    @with_progress(name="Relationship Analysis", steps=[
        "Initialize Relationship Analyst", "Analyze Relationships", "Process Results", "Save Analysis"
    ])
    def analyze_relationships(self, operation_id=None):
        """
        Analyze relationships in the FixWurx codebase.
        
        Args:
            operation_id: Progress operation ID
            
        Returns:
            bool: True if analysis was successful, False otherwise
        """
        try:
            # Step 1: Initialize Relationship Analyst
            progress_manager.update_progress(operation_id, 0, 0.0, "Initializing relationship analyst...")
            # Relationship analyst already initialized in __init__
            progress_manager.update_progress(operation_id, 0, 1.0, "Relationship analyst initialized")
            
            # Step 2: Analyze Relationships
            progress_manager.update_progress(operation_id, 1, 0.0, "Analyzing code relationships...")
            
            # Analyze codebase
            summary = self.relationship_analyst.analyze_codebase(
                root_dir=self.fixwurx_dir,
                incremental=False,
                perform_static_analysis=True,
                save_report=True,
                report_path=os.path.join(self.assessment_dir, "relationship_report.json")
            )
            
            progress_manager.update_progress(
                operation_id, 1, 1.0, 
                f"Relationship analysis completed, analyzed {summary.get('files_analyzed', 0)} files"
            )
            
            # Step 3: Process Results
            progress_manager.update_progress(operation_id, 2, 0.0, "Processing relationship analysis results...")
            
            # Get central files
            central_files = self.relationship_analyst.get_most_central_files(n=20)
            
            # Find cycles in the dependency graph
            cycles = self.relationship_analyst.find_cycles()
            
            # Create a summary of the analysis
            self.relationship_report = {
                "summary": summary,
                "central_files": central_files,
                "cycles": cycles,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            progress_manager.update_progress(
                operation_id, 2, 1.0, 
                f"Relationship analysis results processed, found {len(cycles)} cycles"
            )
            
            # Step 4: Save Analysis
            progress_manager.update_progress(operation_id, 3, 0.0, "Saving relationship analysis...")
            
            # Save the relationship report
            relationship_summary_file = os.path.join(self.assessment_dir, "relationship_summary.json")
            with open(relationship_summary_file, 'w', encoding='utf-8') as f:
                json.dump(self.relationship_report, f, indent=2)
            
            progress_manager.update_progress(operation_id, 3, 1.0, "Relationship analysis saved")
            
            logger.info(f"Relationship analysis completed and saved to {self.assessment_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error analyzing relationships: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def create_component_inventory(self):
        """
        Create an inventory of all components in the FixWurx codebase.
        
        Returns:
            bool: True if inventory was created successfully, False otherwise
        """
        try:
            logger.info("Creating component inventory...")
            
            # Get all Python files in the FixWurx directory
            python_files = []
            for root, _, files in os.walk(self.fixwurx_dir):
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(os.path.join(root, file))
            
            # Categorize files by directory/module
            modules = {}
            for file_path in python_files:
                rel_path = os.path.relpath(file_path, self.fixwurx_dir)
                directory = os.path.dirname(rel_path)
                
                if directory not in modules:
                    modules[directory] = []
                    
                modules[directory].append(os.path.basename(file_path))
            
            # Create component inventory
            self.component_inventory = {
                "total_files": len(python_files),
                "modules": {module: files for module, files in modules.items()},
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            # Save component inventory
            inventory_file = os.path.join(self.assessment_dir, "component_inventory.json")
            with open(inventory_file, 'w', encoding='utf-8') as f:
                json.dump(self.component_inventory, f, indent=2)
            
            logger.info(f"Component inventory created with {len(python_files)} files")
            return True
            
        except Exception as e:
            logger.error(f"Error creating component inventory: {e}")
            return False
    
    def create_assessment_report(self):
        """
        Create a comprehensive assessment report.
        
        Returns:
            bool: True if report was created successfully, False otherwise
        """
        try:
            logger.info("Creating comprehensive assessment report...")
            
            # Create assessment report
            assessment_report = {
                "assessment_timestamp": datetime.datetime.now().isoformat(),
                "fixwurx_directory": self.fixwurx_dir,
                "component_inventory": self.component_inventory,
                "dependency_analysis": {
                    "total_files": len(self.dependency_graph) if self.dependency_graph else 0,
                    "total_dependencies": len(list(self.dependency_graph.edges())) if self.dependency_graph else 0,
                    "missing_connections": self.missing_connections
                },
                "bug_detection": {
                    "total_bugs": self.bugs_report.get('total_bugs', 0) if self.bugs_report else 0,
                    "files_with_bugs": len(self.bugs_report.get('bugs_by_file', {})) if self.bugs_report else 0
                },
                "relationship_analysis": self.relationship_report.get('summary', {}) if self.relationship_report else {}
            }
            
            # Save assessment report
            report_file = os.path.join(self.assessment_dir, "assessment_report.json")
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(assessment_report, f, indent=2)
            
            # Create a human-readable version
            markdown_report = self.create_markdown_report(assessment_report)
            markdown_file = os.path.join(self.assessment_dir, "assessment_report.md")
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(markdown_report)
            
            logger.info(f"Assessment report created and saved to {report_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating assessment report: {e}")
            return False
    
    def create_markdown_report(self, assessment_report):
        """
        Create a human-readable markdown report.
        
        Args:
            assessment_report: Assessment report data
            
        Returns:
            str: Markdown report
        """
        markdown = f"""# FixWurx Baseline Assessment Report

## Overview

This report provides a comprehensive assessment of the FixWurx codebase as of {assessment_report['assessment_timestamp']}.

## Component Inventory

- **Total Files:** {assessment_report['component_inventory']['total_files']}
- **Modules:** {len(assessment_report['component_inventory']['modules'])}

### Module Structure

```
{self.format_module_structure(assessment_report['component_inventory']['modules'])}
```

## Dependency Analysis

- **Total Files Analyzed:** {assessment_report['dependency_analysis']['total_files']}
- **Total Dependencies:** {assessment_report['dependency_analysis']['total_dependencies']}
- **Potential Missing Connections:** {len(assessment_report['dependency_analysis']['missing_connections'])}

### Missing Connections

{self.format_missing_connections(assessment_report['dependency_analysis']['missing_connections'])}

## Bug Detection

- **Total Bugs Detected:** {assessment_report['bug_detection']['total_bugs']}
- **Files with Bugs:** {assessment_report['bug_detection']['files_with_bugs']}

## Relationship Analysis

- **Files Analyzed:** {assessment_report['relationship_analysis'].get('files_analyzed', 'N/A')}
- **Dependencies Found:** {assessment_report['relationship_analysis'].get('dependencies_found', 'N/A')}
- **Cycles Detected:** {assessment_report['relationship_analysis'].get('cycles_detected', 'N/A')}
- **Languages Detected:** {self.format_languages(assessment_report['relationship_analysis'].get('languages_detected', {}))}

## Conclusion

This baseline assessment provides a comprehensive view of the current state of the FixWurx codebase, including its structure, dependencies, bugs, and relationships. This information will be used as a foundation for the subsequent phases of the Triangulum-FixWurx Evaluation Plan.
"""
        return markdown
    
    def format_module_structure(self, modules):
        """Format module structure for markdown."""
        result = []
        for module, files in modules.items():
            if not module:
                module = "."  # Root directory
            result.append(f"{module}/")
            for file in files:
                result.append(f"  ├── {file}")
        return "\n".join(result)
    
    def format_missing_connections(self, missing_connections):
        """Format missing connections for markdown."""
        if not missing_connections:
            return "No missing connections identified."
            
        result = []
        for i, connection in enumerate(missing_connections[:10]):  # Show only the first 10
            result.append(f"{i+1}. {connection['file1']} ↔ {connection['file2']} ({connection['reason']})")
            
        if len(missing_connections) > 10:
            result.append(f"... and {len(missing_connections) - 10} more.")
            
        return "\n".join(result)
    
    def format_languages(self, languages):
        """Format languages for markdown."""
        if not languages:
            return "N/A"
            
        result = []
        for language, count in languages.items():
            result.append(f"{language}: {count}")
            
        return ", ".join(result)
    
    @with_timeout(name="Baseline Assessment", timeout_config=TimeoutConfig(
        duration=600.0,  # 10 minutes
        policy=TimeoutPolicy.EXTEND,
        max_extension=600.0  # Additional 10 minutes if needed
    ))
    @with_progress(name="FixWurx Baseline Assessment", steps=[
        "Setup", "Create Snapshot", "Analyze Dependencies", 
        "Detect Bugs", "Analyze Relationships", "Create Reports"
    ])
    def run_assessment(self, operation_id=None):
        """
        Run the full baseline assessment.
        
        Args:
            operation_id: Progress operation ID
            
        Returns:
            bool: True if assessment was successful, False otherwise
        """
        # Step 1: Setup
        progress_manager.update_progress(operation_id, 0, 0.0, "Setting up assessment environment...")
        self.setup_directories()
        progress_manager.update_progress(operation_id, 0, 1.0, "Assessment environment setup complete")
        
        # Step 2: Create Snapshot
        progress_manager.update_progress(operation_id, 1, 0.0, "Creating snapshot of FixWurx...")
        snapshot_success = self.create_snapshot()
        if not snapshot_success:
            progress_manager.update_progress(operation_id, 1, 1.0, "Failed to create snapshot")
            return False
        progress_manager.update_progress(operation_id, 1, 1.0, "Snapshot created successfully")
        
        # Step 3: Analyze Dependencies
        progress_manager.update_progress(operation_id, 2, 0.0, "Analyzing dependencies...")
        dependency_success = self.analyze_dependencies()
        if not dependency_success:
            progress_manager.update_progress(operation_id, 2, 1.0, "Failed to analyze dependencies")
            return False
        progress_manager.update_progress(operation_id, 2, 1.0, "Dependency analysis complete")
        
        # Step 4: Detect Bugs
        progress_manager.update_progress(operation_id, 3, 0.0, "Detecting bugs...")
        bug_success = self.detect_bugs()
        if not bug_success:
            progress_manager.update_progress(operation_id, 3, 1.0, "Failed to detect bugs")
            return False
        progress_manager.update_progress(operation_id, 3, 1.0, "Bug detection complete")
        
        # Step 5: Analyze Relationships
        progress_manager.update_progress(operation_id, 4, 0.0, "Analyzing relationships...")
        relationship_success = self.analyze_relationships()
        if not relationship_success:
            progress_manager.update_progress(operation_id, 4, 1.0, "Failed to analyze relationships")
            return False
        progress_manager.update_progress(operation_id, 4, 1.0, "Relationship analysis complete")
        
        # Step 6: Create Reports
        progress_manager.update_progress(operation_id, 5, 0.0, "Creating assessment reports...")
        inventory_success = self.create_component_inventory()
        if not inventory_success:
            progress_manager.update_progress(operation_id, 5, 0.5, "Failed to create component inventory")
            return False
        
        report_success = self.create_assessment_report()
        if not report_success:
            progress_manager.update_progress(operation_id, 5, 1.0, "Failed to create assessment report")
            return False
        
        progress_manager.update_progress(operation_id, 5, 1.0, "Assessment reports created successfully")
        
        logger.info(f"Baseline assessment completed successfully. Results saved to {self.assessment_dir}")
        return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run FixWurx baseline assessment using Triangulum")
    parser.add_argument("--fixwurx-dir", default="../FixWurx", help="Path to FixWurx directory")
    parser.add_argument("--output-dir", default="./fixwurx_eval", help="Path to output directory")
    
    args = parser.parse_args()
    
    # Set up progress listener
    def progress_listener(operation_id, progress_info):
        """Progress listener that prints updates."""
        if 'name' in progress_info and 'progress' in progress_info:
            progress_percent = int(progress_info['progress'] * 100)
            status = progress_info.get('status', 'UNKNOWN')
            step_info = ""
            
            if progress_info.get('total_steps', 0) > 0:
                current_step = progress_info.get('current_step', 0) + 1
                total_steps = progress_info.get('total_steps', 0)
                step_info = f" (Step {current_step}/{total_steps})"
            
            eta = ""
            if progress_info.get('eta') is not None:
                eta_seconds = progress_info.get('eta')
                if eta_seconds < 60:
                    eta = f", ETA: {eta_seconds:.1f}s"
                else:
                    eta_min = int(eta_seconds / 60)
                    eta_sec = int(eta_seconds % 60)
                    eta = f", ETA: {eta_min}m{eta_sec}s"
            
            message = progress_info.get('message', '')
            print(f"[{progress_info['name']}] {progress_percent}% {status}{step_info}{eta} | {message}")
    
    # Register the progress listener
    progress_manager.add_progress_listener(progress_listener)
    
    logger.info(f"Starting FixWurx baseline assessment")
    logger.info(f"FixWurx directory: {args.fixwurx_dir}")
    logger.info(f"Output directory: {args.output_dir}")
    
    # Create and run the assessment
    assessment = FixWurxAssessment(args.fixwurx_dir, args.output_dir)
    success = assessment.run_assessment()
    
    if success:
        logger.info("FixWurx baseline assessment completed successfully")
        print("\n=== ASSESSMENT COMPLETED SUCCESSFULLY ===")
        print(f"Results saved to {os.path.abspath(args.output_dir)}")
        return 0
    else:
        logger.error("FixWurx baseline assessment failed")
        print("\n=== ASSESSMENT FAILED ===")
        print("Check logs for details")
        return 1

if __name__ == "__main__":
    sys.exit(main())
