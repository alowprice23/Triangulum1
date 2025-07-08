#!/usr/bin/env python3
"""
Comprehensive Bug Detector Enhancement

This script enhances the BugDetectorAgent with:
1. False positive reduction through multi-pass verification
2. Performance optimization for large codebases
3. Improved integration with the relationship analyst
4. Context-aware detection capabilities
5. Advanced bug classification and prioritization
6. Parallel processing for faster analysis
"""

import os
import sys
import re
import json
import time
import logging
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bug_detector_fix")

# Constants
MAX_WORKERS = 8  # Maximum number of parallel workers
CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence for reporting bugs
SEVERITY_WEIGHTS = {
    "critical": 1.0,
    "high": 0.8,
    "medium": 0.5,
    "low": 0.3
}


class BugDetectorEnhancer:
    """Class to enhance the BugDetectorAgent."""
    
    def __init__(self, file_path: Path):
        """
        Initialize the enhancer.
        
        Args:
            file_path: Path to the bug_detector_agent.py file
        """
        self.file_path = file_path
        self.backup_path = file_path.with_suffix(".py.bak")
        self.content = None
    
    def read_file(self) -> bool:
        """
        Read the file content.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
            return True
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return False
    
    def create_backup(self) -> bool:
        """
        Create a backup of the original file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.backup_path, 'w', encoding='utf-8') as f:
                f.write(self.content)
            logger.info(f"Created backup at {self.backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False
    
    def enhance_false_positive_reduction(self) -> None:
        """Enhance false positive reduction capabilities."""
        # Find the _verify_bugs method
        verify_bugs_pattern = r'def _verify_bugs\([^)]+\):[^}]+?return verified_bugs'
        verify_bugs_match = re.search(verify_bugs_pattern, self.content, re.DOTALL)
        
        if verify_bugs_match:
            # Replace with enhanced implementation
            old_method = verify_bugs_match.group(0)
            new_method = """def _verify_bugs(
        self, 
        bugs: List[Union[Dict[str, Any], DetectedBug]], 
        content: str,
        file_path: str,
        language: str,
        relationship_context: Optional[Dict[str, Any]] = None
    ) -> List[Union[Dict[str, Any], DetectedBug]]:
        \"\"\"
        Verify detected bugs with multiple strategies to reduce false positives.
        
        Args:
            bugs: List of detected bugs
            content: File content
            file_path: Path to the file
            language: Programming language
            relationship_context: Relationship context information
            
        Returns:
            Filtered list of bugs with updated confidence scores
        \"\"\"
        if not bugs:
            return []
        
        verified_bugs = []
        
        # Convert any dictionary bugs to DetectedBug objects for processing
        bugs_to_verify = [
            bug if isinstance(bug, DetectedBug) else self._convert_to_detected_bug(bug)
            for bug in bugs
        ]
        
        # Apply different verification strategies to each bug
        for bug in bugs_to_verify:
            # Store verification results
            verification_results = {}
            
            # Apply each verification strategy
            for strategy_name, strategy_func in self.verification_strategies.items():
                try:
                    # Skip some strategies based on bug type or file type
                    if strategy_name == "ast_validation" and language not in ["python", "javascript"]:
                        continue
                        
                    if strategy_name == "cross_file_validation" and not relationship_context:
                        continue
                    
                    # Apply the verification strategy
                    result = strategy_func(bug, content, file_path, language, relationship_context)
                    verification_results[strategy_name] = result
                    
                    # Update confidence based on result
                    if result.get("is_valid", True):
                        bug.confidence *= result.get("confidence_factor", 1.0)
                    else:
                        # If strategy determines it's definitely a false positive
                        bug.false_positive_probability = result.get("false_positive_probability", 0.8)
                        
                except Exception as e:
                    logger.warning(f"Error in verification strategy {strategy_name}: {e}")
                    verification_results[strategy_name] = {"error": str(e)}
            
            # Store verification results in the bug
            bug.verification_results = verification_results
            
            # Apply machine learning-based false positive detection if available
            if hasattr(self, '_apply_ml_false_positive_detection'):
                try:
                    ml_result = self._apply_ml_false_positive_detection(bug, content, file_path)
                    if ml_result:
                        bug.false_positive_probability = max(
                            bug.false_positive_probability,
                            ml_result.get("false_positive_probability", 0.0)
                        )
                        verification_results["ml_detection"] = ml_result
                except Exception as e:
                    logger.warning(f"Error in ML false positive detection: {e}")
            
            # Apply code context analysis for better accuracy
            if hasattr(self, '_analyze_code_context'):
                try:
                    context_result = self._analyze_code_context(bug, content, file_path)
                    if context_result:
                        # Adjust confidence based on context analysis
                        bug.confidence *= context_result.get("confidence_factor", 1.0)
                        verification_results["context_analysis"] = context_result
                except Exception as e:
                    logger.warning(f"Error in code context analysis: {e}")
            
            # Filter out high-probability false positives
            if bug.false_positive_probability < self.false_positive_threshold:
                # Additional check for confidence threshold
                if bug.confidence >= CONFIDENCE_THRESHOLD:
                    verified_bugs.append(bug)
                
        # Sort by confidence and severity
        verified_bugs.sort(
            key=lambda b: (
                b.confidence,
                SEVERITY_WEIGHTS.get(b.severity, 0.5)
            ),
            reverse=True
        )
                
        return verified_bugs"""
            
            self.content = self.content.replace(old_method, new_method)
            logger.info("Enhanced false positive reduction")
    
    def add_ml_false_positive_detection(self) -> None:
        """Add machine learning-based false positive detection."""
        # Find a good insertion point after the verification strategies
        insertion_point = self.content.find("def _verify_with_similarity_check")
        
        if insertion_point != -1:
            # Find the end of the method
            method_end = self.content.find("def ", insertion_point + 10)
            
            # Insert the new method
            new_method = """
    def _apply_ml_false_positive_detection(self, bug, content, file_path):
        \"\"\"
        Apply machine learning to detect false positives.
        
        Args:
            bug: The detected bug
            content: File content
            file_path: Path to the file
            
        Returns:
            Dictionary with false positive probability
        \"\"\"
        # This is a simplified implementation that could be replaced with a real ML model
        result = {
            "false_positive_probability": 0.0,
            "confidence_factor": 1.0,
            "notes": []
        }
        
        # Extract features for ML analysis
        features = {
            "bug_type": bug.bug_type.value,
            "severity": bug.severity,
            "confidence": bug.confidence,
            "file_extension": os.path.splitext(file_path)[1],
            "code_length": len(bug.code_snippet),
            "match_length": len(bug.match_text),
            "is_test_file": "test" in file_path.lower(),
            "is_generated_file": "generated" in file_path.lower() or "auto-generated" in content.lower()
        }
        
        # Apply heuristics (could be replaced with a trained model)
        if features["is_test_file"]:
            # Higher false positive probability in test files
            result["false_positive_probability"] += 0.2
            result["notes"].append("Test files often have intentional edge cases")
        
        if features["is_generated_file"]:
            # Higher false positive probability in generated files
            result["false_positive_probability"] += 0.3
            result["notes"].append("Generated files may have unusual patterns")
        
        # Adjust based on bug type
        if bug.bug_type == BugType.NULL_REFERENCE:
            # Check for null checks nearby
            if "if" in bug.code_snippet and ("None" in bug.code_snippet or "null" in bug.code_snippet):
                result["false_positive_probability"] += 0.4
                result["notes"].append("Null check detected in the code")
        
        # Cap the probability
        result["false_positive_probability"] = min(0.9, result["false_positive_probability"])
        
        return result
        
    def _analyze_code_context(self, bug, content, file_path):
        \"\"\"
        Analyze the surrounding code context for better accuracy.
        
        Args:
            bug: The detected bug
            content: File content
            file_path: Path to the file
            
        Returns:
            Dictionary with context analysis results
        \"\"\"
        result = {
            "confidence_factor": 1.0,
            "notes": []
        }
        
        # Get lines around the bug
        lines = content.splitlines()
        line_index = bug.line_number - 1
        
        if line_index < 0 or line_index >= len(lines):
            return result
        
        # Get context lines (5 before and after)
        start = max(0, line_index - 5)
        end = min(len(lines), line_index + 6)
        context_lines = lines[start:end]
        context_text = "\\n".join(context_lines)
        
        # Look for patterns that increase confidence
        if bug.bug_type == BugType.SQL_INJECTION:
            # If there's no input validation nearby, increase confidence
            if not re.search(r'validate|sanitize|escape|prepared', context_text, re.IGNORECASE):
                result["confidence_factor"] = 1.2
                result["notes"].append("No input validation detected")
        
        elif bug.bug_type == BugType.RESOURCE_LEAK:
            # If there's no close or with statement, increase confidence
            if not re.search(r'close\(\)|with\s+|try.*finally', context_text, re.IGNORECASE):
                result["confidence_factor"] = 1.2
                result["notes"].append("No resource cleanup detected")
        
        # Look for patterns that decrease confidence
        if re.search(r'#\s*nosec|//\s*nosec|/\*\s*nosec', context_text, re.IGNORECASE):
            result["confidence_factor"] = 0.5
            result["notes"].append("Security check suppression comment found")
        
        return result

"""
            
            self.content = self.content[:method_end] + new_method + self.content[method_end:]
            logger.info("Added ML-based false positive detection")
    
    def enhance_performance(self) -> None:
        """Enhance performance for large codebases."""
        # Find the detect_bugs_in_folder method
        folder_method_pattern = r'def detect_bugs_in_folder\([^)]+\):[^}]+?return result'
        folder_method_match = re.search(folder_method_pattern, self.content, re.DOTALL)
        
        if folder_method_match:
            # Replace with enhanced implementation
            old_method = folder_method_match.group(0)
            new_method = """def detect_bugs_in_folder(
        self,
        folder_path: str,
        recursive: bool = True,
        language: Optional[str] = None,
        selected_patterns: Optional[List[str]] = None,
        file_extensions: Optional[List[str]] = None,
        max_depth: int = 10,
        continue_on_error: bool = True,
        parallel: bool = True,
        max_workers: int = MAX_WORKERS
    ) -> Dict[str, Any]:
        \"\"\"
        Analyze all files in a folder for potential bugs.
        
        Args:
            folder_path: Path to the folder to analyze
            recursive: Whether to analyze files in subdirectories
            language: Language of the files (if None, inferred from extension)
            selected_patterns: List of pattern IDs to use (if None, use all enabled patterns)
            file_extensions: List of file extensions to include (if None, include all code files)
            max_depth: Maximum recursion depth for subdirectories
            continue_on_error: Whether to continue analysis when errors are encountered
            parallel: Whether to use parallel processing for faster analysis
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dictionary with bug detection results
        \"\"\"
        # Track results
        bugs_by_file = {}
        errors_by_file = {}
        total_bugs = 0
        files_analyzed = 0
        files_with_bugs = 0
        files_with_errors = 0
        skipped_files = 0
        
        # Track performance metrics
        start_time = time.time()
        
        # Validate folder path
        if not os.path.exists(folder_path):
            error_msg = f"Folder does not exist: {folder_path}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "error_type": "FolderNotFoundError",
                "bugs_by_file": {},
                "total_bugs": 0,
                "files_analyzed": 0,
                "files_with_bugs": 0,
                "files_with_errors": 0,
                "skipped_files": 0,
                "workflow_id": self.current_workflow_id,
                "execution_time": 0
            }
        
        if not os.path.isdir(folder_path):
            error_msg = f"Path is not a directory: {folder_path}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "error_type": "NotADirectoryError",
                "bugs_by_file": {},
                "total_bugs": 0,
                "files_analyzed": 0,
                "files_with_bugs": 0,
                "files_with_errors": 0,
                "skipped_files": 0,
                "workflow_id": self.current_workflow_id,
                "execution_time": 0
            }
        
        # If no file extensions provided, use common code file extensions
        if file_extensions is None:
            file_extensions = [
                '.py', '.java', '.js', '.jsx', '.ts', '.tsx', '.php', 
                '.rb', '.go', '.cs', '.cpp', '.c', '.h', '.hpp',
                '.rs', '.swift', '.kt', '.scala', '.sh'
            ]
            logger.debug(f"Using default file extensions: {', '.join(file_extensions)}")
        
        # Generate list of files to analyze
        files_to_analyze = []
        folder_access_error = False
        
        try:
            # Walk through the directory
            if recursive:
                for root, dirs, files in os.walk(folder_path):
                    # Check depth to avoid excessive recursion
                    rel_path = os.path.relpath(root, folder_path)
                    depth = len(rel_path.split(os.sep)) if rel_path != '.' else 0
                    
                    if depth > max_depth:
                        logger.info(f"Skipping {root} - exceeds max depth of {max_depth}")
                        continue
                    
                    # Add files that match extensions
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_ext = os.path.splitext(file)[1].lower()
                        
                        if not file_extensions or file_ext in file_extensions:
                            files_to_analyze.append(file_path)
            else:
                # Only analyze files in the top-level directory
                for item in os.listdir(folder_path):
                    item_path = os.path.join(folder_path, item)
                    if os.path.isfile(item_path):
                        file_ext = os.path.splitext(item)[1].lower()
                        if not file_extensions or file_ext in file_extensions:
                            files_to_analyze.append(item_path)
        except PermissionError as e:
            error_msg = f"Permission error accessing folder {folder_path}: {str(e)}"
            logger.error(error_msg)
            folder_access_error = True
            if not continue_on_error:
                return {
                    "status": "error",
                    "error": error_msg,
                    "error_type": "PermissionError",
                    "bugs_by_file": bugs_by_file,
                    "total_bugs": total_bugs,
                    "files_analyzed": files_analyzed,
                    "files_with_bugs": files_with_bugs,
                    "files_with_errors": files_with_errors,
                    "skipped_files": skipped_files,
                    "workflow_id": self.current_workflow_id,
                    "execution_time": time.time() - start_time
                }
        except Exception as e:
            error_msg = f"Error listing files in folder {folder_path}: {str(e)}"
            logger.error(f"{error_msg}\\n{traceback.format_exc()}")
            folder_access_error = True
            if not continue_on_error:
                return {
                    "status": "error",
                    "error": error_msg,
                    "error_type": type(e).__name__,
                    "bugs_by_file": bugs_by_file,
                    "total_bugs": total_bugs,
                    "files_analyzed": files_analyzed,
                    "files_with_bugs": files_with_bugs,
                    "files_with_errors": files_with_errors,
                    "skipped_files": skipped_files,
                    "workflow_id": self.current_workflow_id,
                    "execution_time": time.time() - start_time
                }
        
        # Log progress
        logger.info(f"Found {len(files_to_analyze)} files to analyze in {folder_path}")
        
        # Create error entry for folder access error if needed
        if folder_access_error:
            errors_by_file[folder_path] = [{
                "message": f"Partial access to folder {folder_path}, some files may have been skipped",
                "severity": "high",
                "error_type": "FolderAccessError",
                "recoverable": True,
                "suggestion": "Check folder permissions and try again with a different user account."
            }]
            files_with_errors += 1
        
        # Function to analyze a single file
        def analyze_file(file_path):
            # Include errors flag for detecting problematic files
            try:
                result = self.detect_bugs_in_file(
                    file_path=file_path,
                    language=language,
                    selected_patterns=selected_patterns,
                    include_errors=True
                )
                return file_path, result
            except Exception as e:
                logger.error(f"Error analyzing file {file_path}: {str(e)}")
                return file_path, None
        
        # Analyze files in parallel or sequentially
        if parallel and len(files_to_analyze) > 1:
            # Use ThreadPoolExecutor for parallel processing
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all files for analysis
                future_to_file = {
                    executor.submit(analyze_file, file_path): file_path
                    for file_path in files_to_analyze
                }
                
                # Process results as they complete
                for i, future in enumerate(concurrent.futures.as_completed(future_to_file)):
                    file_path = future_to_file[future]
                    
                    # Log progress every 10 files or at start/end
                    if i % 10 == 0 or i == len(files_to_analyze) - 1:
                        logger.info(f"Analyzed file {i+1}/{len(files_to_analyze)}: {file_path}")
                    
                    try:
                        file_path, result = future.result()
                        
                        if result is None:
                            skipped_files += 1
                            continue
                        
                        # Process the result
                        files_analyzed += 1
                        
                        if isinstance(result, FileAnalysisResult):
                            # If file has bugs, add them to the results
                            if result.has_bugs:
                                bugs_by_file[file_path] = result.bugs
                                total_bugs += len(result.bugs)
                                files_with_bugs += 1
                            
                            # If file has errors, add them to the error collection
                            if result.has_errors:
                                errors_by_file[file_path] = [error.to_dict() for error in result.errors]
                                files_with_errors += 1
                            
                            # If analysis was neither successful nor partially successful
                            if not result.success and not result.partial_success:
                                skipped_files += 1
                        else:
                            # For backward compatibility with older implementations
                            if result:  # If the list has bugs
                                bugs_by_file[file_path] = result
                                total_bugs += len(result)
                                files_with_bugs += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing result for {file_path}: {str(e)}")
                        skipped_files += 1
        else:
                # Analyze sequentially
            for i, file_path in enumerate(files_to_analyze):
                # Log progress every 10 files or at start/end
                if i % 10 == 0 or i == len(files_to_analyze) - 1:
                    logger.info(f"Analyzing file {i+1}/{len(files_to_analyze)}: {file_path}")
                
                try:
                    file_path, result = analyze_file(file_path)
                    
                    if result is None:
                        skipped_files += 1
                        continue
                    
                    # Process the result
                    files_analyzed += 1
                    
                    if isinstance(result, FileAnalysisResult):
                        # If file has bugs, add them to the results
                        if result.has_bugs:
                            bugs_by_file[file_path] = result.bugs
                            total_bugs += len(result.bugs)
                            files_with_bugs += 1
                        
                        # If file has errors, add them to the error collection
                        if result.has_errors:
                            errors_by_file[file_path] = [error.to_dict() for error in result.errors]
                            files_with_errors += 1
                        
                        # If analysis was neither successful nor partially successful
                        if not result.success and not result.partial_success:
                            skipped_files += 1
                    else:
                        # For backward compatibility with older implementations
                        if result:  # If the list has bugs
                            bugs_by_file[file_path] = result
                            total_bugs += len(result)
                            files_with_bugs += 1
                
                except Exception as e:
                    logger.error(f"Error processing result for {file_path}: {str(e)}")
                    skipped_files += 1
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Determine overall status
        status = "success"
        error_msg = None
        error_type = None
        
        if files_analyzed == 0 and files_to_analyze:
            status = "error"
            error_msg = "No files could be analyzed"
            error_type = "AnalysisFailure"
        elif files_with_errors > 0 and files_analyzed < len(files_to_analyze):
            status = "partial_success"
            error_msg = f"{files_with_errors} files had errors, {skipped_files} files were skipped"
            error_type = "PartialAnalysisFailure"
        
        # Build and return the results
        result = {
            "status": status,
            "bugs_by_file": bugs_by_file,
            "total_bugs": total_bugs,
            "files_analyzed": files_analyzed,
            "files_with_bugs": files_with_bugs,
            "files_with_errors": files_with_errors,
            "skipped_files": skipped_files,
            "workflow_id": self.current_workflow_id,
            "execution_time": execution_time
        }
        
        if error_msg:
            result["error"] = error_msg
        if error_type:
            result["error_type"] = error_type
        if errors_by_file:
            result["errors_by_file"] = errors_by_file
        
        return result"""
            
            self.content = self.content.replace(old_method, new_method)
            logger.info("Enhanced folder analysis with parallel processing")
    
    def enhance_relationship_integration(self) -> None:
        """Enhance integration with the relationship analyst."""
        # Find the _get_relationship_context method
        method_pattern = r'def _get_relationship_context\([^)]+\):[^}]+?return context'
        method_match = re.search(method_pattern, self.content, re.DOTALL)
        
        if method_match:
            # Replace with enhanced implementation
            old_method = method_match.group(0)
            new_method = """def _get_relationship_context(self, file_path: str) -> Dict[str, Any]:
        \"\"\"
        Get relationship context for a file from the relationship analyst.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with relationship context information
        \"\"\"
        # Return cached context if available
        if file_path in self.analyzed_file_context:
            return self.analyzed_file_context[file_path]
        
        # If no relationship analyst, return empty context
        if not self.relationship_analyst:
            return {}
        
        try:
            # Get dependencies and dependents from relationship analyst
            dependencies = self.relationship_analyst.get_file_dependencies(file_path, transitive=True)
            dependents = self.relationship_analyst.get_file_dependents(file_path, transitive=True)
            
            # Get the most central files (high impact files)
            central_files = self.relationship_analyst.get_most_central_files(n=5)
            
            # Get semantic relationship information if available
            semantic_info = {}
            if hasattr(self.relationship_analyst, 'get_semantic_relationships'):
                try:
                    semantic_info = self.relationship_analyst.get_semantic_relationships(file_path)
                except Exception as e:
                    logger.warning(f"Error getting semantic relationships: {e}")
            
            # Get temporal relationship information if available
            temporal_info = {}
            if hasattr(self.relationship_analyst, 'get_temporal_relationships'):
                try:
                    temporal_info = self.relationship_analyst.get_temporal_relationships(file_path)
                except Exception as e:
                    logger.warning(f"Error getting temporal relationships: {e}")
            
            # Cache the dependencies and dependents
            self.file_dependencies_cache[file_path] = dependencies
            self.file_dependents_cache[file_path] = dependents
            
            # Create context
            context = {
                "dependencies": list(dependencies),
                "dependents": list(dependents),
                "central_files": central_files,
                "impact_score": len(dependents) / 10.0,  # Normalize to 0.0-1.0 range
                "semantic_info": semantic_info,
                "temporal_info": temporal_info,
                "is_central": file_path in [f[0] for f in central_files] if central_files else False
            }
            
            # Cache and return
            self.analyzed_file_context[file_path] = context
            return context
        except Exception as e:
            logger.warning(f"Error getting relationship context: {e}")
            return {}"""
            
            self.content = self.content.replace(old_method, new_method)
            logger.info("Enhanced relationship analyst integration")
    
    def add_context_aware_detection(self) -> None:
        """Add context-aware detection capabilities."""
        # Find the __init__ method
        init_pattern = r'def __init__\([^)]+\):[^}]+?self\.verification_strategies'
        init_match = re.search(init_pattern, self.content, re.DOTALL)
        
        if init_match:
            # Add new configuration parameters
            old_init = init_match.group(0)
            new_init = old_init + " = {}\n        \n        # Add context-aware detection capabilities\n        self.enable_context_aware_detection = enable_context_aware_detection\n        self.context_patterns = self._load_context_patterns()"
            
            self.content = self.content.replace(old_init, new_init)
            
            # Find a good insertion point for the _load_context_patterns method
            insertion_point = self.content.find("def _load_bug_patterns")
            if insertion_point != -1:
                # Find the end of the method
                method_end = self.content.find("def ", insertion_point + 10)
                
                # Insert the new method
                new_method = """
    def _load_context_patterns(self) -> Dict[str, Dict[str, Any]]:
        \"\"\"
        Load context-aware bug patterns from the config or use default patterns.
        
        Returns:
            Dictionary mapping pattern IDs to context pattern definitions
        \"\"\"
        # Load from config if available
        patterns = self.config.get("context_patterns", {})
        
        # If no patterns in config, use default patterns
        if not patterns:
            patterns = {
                "dependency_critical": {
                    "description": "Bugs in files with many dependents are more critical",
                    "severity_boost": 1,  # Boost severity by 1 level
                    "condition": lambda context: len(context.get("dependents", [])) > 5
                },
                "central_file": {
                    "description": "Bugs in central files are more important",
                    "confidence_boost": 0.2,  # Boost confidence by 0.2
                    "condition": lambda context: context.get("is_central", False)
                },
                "cross_file_null": {
                    "description": "Null references across file boundaries",
                    "bug_type": "null_reference",
                    "confidence_boost": 0.3,
                    "condition": lambda context, bug: (
                        bug.bug_type == BugType.NULL_REFERENCE and
                        any(dep in bug.match_text for dep in context.get("dependencies", []))
                    )
                },
                "recently_modified": {
                    "description": "Recently modified files are more likely to have bugs",
                    "confidence_boost": 0.1,
                    "condition": lambda context: context.get("temporal_info", {}).get("recently_modified", False)
                }
            }
        
        return patterns

"""
                
                self.content = self.content[:method_end] + new_method + self.content[method_end:]
                logger.info("Added context-aware detection capabilities")
    
    def add_bug_classification(self) -> None:
        """Add advanced bug classification capabilities."""
        # Find the _severity_to_numeric method
        method_pattern = r'def _severity_to_numeric\([^)]+\):[^}]+?return severity_map\.get\([^)]+\)'
        method_match = re.search(method_pattern, self.content, re.DOTALL)
        
        if method_match:
            # Find the end of the method
            method_end = self.content.find("\n    ", method_match.end())
            
            # Add new bug classification methods
            new_methods = """
    
    def _classify_bug_impact(self, bug: DetectedBug, relationship_context: Optional[Dict[str, Any]] = None) -> str:
        \"\"\"
        Classify the impact of a bug based on its severity and relationship context.
        
        Args:
            bug: The detected bug
            relationship_context: Relationship context information
            
        Returns:
            Impact classification (critical, high, medium, low)
        \"\"\"
        # Start with the bug's own severity
        base_impact = bug.severity
        
        # If no relationship context, return the base impact
        if not relationship_context:
            return base_impact
        
        # Adjust based on relationship context
        if relationship_context.get("is_central", False):
            # Central files have higher impact
            if base_impact == "medium":
                return "high"
            elif base_impact == "low":
                return "medium"
        
        dependents_count = len(relationship_context.get("dependents", []))
        if dependents_count > 10:
            # Files with many dependents have higher impact
            if base_impact == "medium":
                return "high"
            elif base_impact == "low":
                return "medium"
        
        return base_impact
    
    def _classify_bug_priority(self, bug: DetectedBug, relationship_context: Optional[Dict[str, Any]] = None) -> int:
        \"\"\"
        Classify the priority of a bug based on its severity, confidence, and impact.
        
        Args:
            bug: The detected bug
            relationship_context: Relationship context information
            
        Returns:
            Priority score (1-10, where 10 is highest priority)
        \"\"\"
        # Base priority on severity
        severity_map = {
            "critical": 8,
            "high": 6,
            "medium": 4,
            "low": 2
        }
        
        base_priority = severity_map.get(bug.severity, 3)
        
        # Adjust based on confidence
        confidence_factor = bug.confidence
        
        # Adjust based on bug type
        bug_type_priority = {
            BugType.SQL_INJECTION: 2,            # Security vulnerabilities get a big boost
            BugType.CREDENTIALS_LEAK: 2,
            BugType.CROSS_SITE_SCRIPTING: 2,
            BugType.PATH_TRAVERSAL: 2,
            BugType.CODE_INJECTION: 2,
            BugType.NULL_REFERENCE: 1,           # Common errors get a medium boost
            BugType.EXCEPTION_HANDLING: 1,
            BugType.RESOURCE_LEAK: 0,            # Others remain at base priority
            BugType.RACE_CONDITION: 0
        }
        
        type_boost = bug_type_priority.get(bug.bug_type, 0)
        
        # Calculate combined priority
        priority = base_priority + type_boost
        
        # Apply confidence factor
        priority = int(priority * confidence_factor)
        
        # If relationship context available, adjust for impact
        if relationship_context:
            impact_score = relationship_context.get("impact_score", 0.0)
            priority += int(impact_score * 2)  # Up to 2 points boost based on impact
        
        # Ensure priority is within range
        return max(1, min(10, priority))
"""
            
            # Insert the new methods
            self.content = self.content[:method_end] + new_methods + self.content[method_end:]
            logger.info("Added advanced bug classification capabilities")
    
    def write_updated_file(self) -> bool:
        """
        Write the updated content back to the file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(self.content)
            logger.info(f"Successfully updated {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing to file: {e}")
            return False
    
    def add_main_function(self) -> None:
        """Add the main function to apply all the enhancements."""
        # Find the end of the file
        main_function = """

def fix_bug_detector_agent():
    \"\"\"
    Enhance the BugDetectorAgent with comprehensive improvements.
    \"\"\"
    # Path to the bug detector agent file
    file_path = Path("triangulum_lx/agents/bug_detector_agent.py")
    
    if not file_path.exists():
        logger.error(f"Error: File not found: {file_path}")
        return False
    
    # Create the enhancer
    enhancer = BugDetectorEnhancer(file_path)
    
    # Read the file
    if not enhancer.read_file():
        return False
    
    # Create a backup
    if not enhancer.create_backup():
        return False
    
    # Apply enhancements
    enhancer.enhance_false_positive_reduction()
    enhancer.add_ml_false_positive_detection()
    enhancer.enhance_performance()
    enhancer.enhance_relationship_integration()
    enhancer.add_context_aware_detection()
    enhancer.add_bug_classification()
    
    # Write the updated file
    if not enhancer.write_updated_file():
        return False
    
    logger.info("Successfully enhanced the BugDetectorAgent")
    return True


def main():
    \"\"\"Main function to run the enhancement.\"\"\"
    print("Enhancing BugDetectorAgent...")
    if fix_bug_detector_agent():
        print("Enhancements applied successfully!")
        return 0
    else:
        print("Failed to apply enhancements.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
"""
        
        # Add the main function to the end of the file
        self.content += main_function
        logger.info("Added main function")
