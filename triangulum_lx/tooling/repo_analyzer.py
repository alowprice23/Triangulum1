#!/usr/bin/env python3
"""
Repository Analyzer

This module provides functionality for analyzing entire repositories,
including traversing file structures and analyzing individual files.
"""

import os
import logging
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RepoAnalyzer:
    """
    Analyzes an entire repository to provide a comprehensive overview.
    """
    
    def __init__(self, repo_path: str, file_extensions: Optional[List[str]] = None):
        """
        Initialize the repository analyzer.
        
        Args:
            repo_path: The path to the repository to analyze.
            file_extensions: A list of file extensions to include in the analysis.
                             If None, all files will be included.
        """
        self.repo_path = repo_path
        self.file_extensions = file_extensions
        
        if not os.path.isdir(repo_path):
            raise ValueError(f"Repository path not found: {repo_path}")
        
        logger.info(f"Repository Analyzer initialized for path: {repo_path}")
    
    def analyze_repo(self) -> Dict[str, Any]:
        """
        Analyze the entire repository.
        
        Returns:
            A dictionary containing the analysis results.
        """
        analysis_results = {
            "repo_path": self.repo_path,
            "total_files": 0,
            "total_lines": 0,
            "file_details": []
        }
        
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check if the file extension should be included
                if self.file_extensions and not any(file.endswith(ext) for ext in self.file_extensions):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        line_count = len(lines)
                        
                        analysis_results["total_files"] += 1
                        analysis_results["total_lines"] += line_count
                        
                        analysis_results["file_details"].append({
                            "path": file_path,
                            "line_count": line_count
                        })
                except Exception as e:
                    logger.warning(f"Could not analyze file {file_path}: {e}")
        
        logger.info(f"Repository analysis completed for {self.repo_path}")
        return analysis_results
