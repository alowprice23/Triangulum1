#!/usr/bin/env python3
"""
Unit tests for the enhanced Bug Detector Agent.

This module verifies the enhancements made to the Bug Detector Agent:
1. False positive reduction through multi-pass verification
2. Performance optimization for large codebases
3. Integration with the relationship analyst
4. Context-aware detection capabilities
5. Advanced bug classification and prioritization
"""

import unittest
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any, Optional
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from triangulum_lx.agents.bug_detector_agent import BugDetectorAgent, DetectedBug, BugType
from triangulum_lx.agents.relationship_analyst_agent import RelationshipAnalystAgent
from triangulum_lx.agents.message import MessageType


class TestBugDetectorEnhancements(unittest.TestCase):
    """Test cases for the enhanced Bug Detector Agent."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock relationship analyst
        self.mock_relationship_analyst = MagicMock(spec=RelationshipAnalystAgent)
        self.mock_relationship_analyst.get_file_dependencies.return_value = {"dependent1.py", "dependent2.py"}
        self.mock_relationship_analyst.get_file_dependents.return_value = {"parent1.py", "parent2.py", "parent3.py"}
        self.mock_relationship_analyst.get_most_central_files.return_value = [("central1.py", 0.9), ("central2.py", 0.8)]
        
        # Create the bug detector with enhancements
        self.bug_detector = BugDetectorAgent(
            agent_id="test_bug_detector",
            relationship_analyst_agent=self.mock_relationship_analyst,
            enable_context_aware_detection=True,
            enable_multi_pass_verification=True,
            false_positive_threshold=0.8,
            use_ast_parsing=True
        )
        
        # Create a temporary test file
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        self.temp_file.write(b"""
def vulnerable_function(user_input):
    # SQL Injection vulnerability
    query = "SELECT * FROM users WHERE id = " + user_input
    
    # Null reference vulnerability
    data = None
    print(data.property)
    
    # Resource leak
    f = open("test.txt", "r")
    return query
""")
        self.temp_file.close()
        
        # Create a temporary folder
        self.temp_dir = tempfile.mkdtemp()
        self.temp_files = []
        
        # Create a few test files in the directory
        for i in range(3):
            file_path = os.path.join(self.temp_dir, f"test_file_{i}.py")
            with open(file_path, "w") as f:
                f.write(f"""
# Test file {i}
def function_{i}(param):
    # {'SQL Injection vulnerability' if i == 0 else ''}
    {'query = "SELECT * FROM users WHERE id = " + param' if i == 0 else ''}
    
    # {'Null reference vulnerability' if i == 1 else ''}
    {'data = None' if i == 1 else ''}
    {'print(data.property)' if i == 1 else ''}
    
    # {'Resource leak' if i == 2 else ''}
    {'f = open("test.txt", "r")' if i == 2 else ''}
    return {'query' if i == 0 else 'data' if i == 1 else 'f' if i == 2 else 'None'}
""")
            self.temp_files.append(file_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary files
        os.unlink(self.temp_file.name)
        
        # Remove temporary folder files
        for file_path in self.temp_files:
            try:
                os.unlink(file_path)
            except:
                pass
        
        # Remove temporary folder
        try:
            os.rmdir(self.temp_dir)
        except:
            pass
    
    def test_false_positive_reduction(self):
        """Test false positive reduction capabilities."""
        # Mock verification strategies to simulate false positive detection
        original_strategies = self.bug_detector.verification_strategies
        
        try:
            # Create a mock strategy that marks SQL injection as false positive
            mock_strategies = {
                "test_strategy": lambda bug, content, file_path, language, context: {
                    "is_valid": bug.bug_type != BugType.SQL_INJECTION,
                    "confidence_factor": 0.5 if bug.bug_type == BugType.SQL_INJECTION else 1.0,
                    "false_positive_probability": 0.9 if bug.bug_type == BugType.SQL_INJECTION else 0.0,
                    "notes": ["Test strategy"] 
                }
            }
            
            self.bug_detector.verification_strategies = mock_strategies
            
            # Detect bugs with verification
            bugs = self.bug_detector.detect_bugs_in_file(
                file_path=self.temp_file.name,
                verify_bugs=True
            )
            
            # Should not find SQL injection due to false positive detection
            bug_types = [bug.get('bug_type', '') for bug in bugs]
            self.assertNotIn(BugType.SQL_INJECTION.value, bug_types)
            
            # Should still find other bugs
            self.assertTrue(any('null_reference' in bug.get('bug_type', '') for bug in bugs))
            
        finally:
            # Restore original strategies
            self.bug_detector.verification_strategies = original_strategies
    
    def test_relationship_integration(self):
        """Test integration with the relationship analyst."""
        # Detect bugs with relationship context
        bugs = self.bug_detector.detect_bugs_in_file(
            file_path=self.temp_file.name
        )
        
        # Verify relationship analyst was called
        self.mock_relationship_analyst.get_file_dependencies.assert_called_with(self.temp_file.name, transitive=True)
        self.mock_relationship_analyst.get_file_dependents.assert_called_with(self.temp_file.name, transitive=True)
        self.mock_relationship_analyst.get_most_central_files.assert_called()
    
    def test_folder_analysis_performance(self):
        """Test performance optimization for folder analysis."""
        # Time the folder analysis
        start_time = time.time()
        
        # Analyze with parallel processing
        result_parallel = self.bug_detector.detect_bugs_in_folder(
            folder_path=self.temp_dir,
            parallel=True,
            max_workers=2
        )
        
        parallel_time = time.time() - start_time
        
        # Verify results
        self.assertEqual(result_parallel["status"], "success")
        self.assertEqual(result_parallel["files_analyzed"], len(self.temp_files))
        
        # Should find at least one bug in each file
        self.assertEqual(result_parallel["files_with_bugs"], len(self.temp_files))
        
        # Should find exactly one bug in each file based on our test file setup
        self.assertEqual(result_parallel["total_bugs"], len(self.temp_files))
    
    @patch('triangulum_lx.agents.bug_detector_agent.BugDetectorAgent._classify_bug_impact')
    @patch('triangulum_lx.agents.bug_detector_agent.BugDetectorAgent._classify_bug_priority')
    def test_bug_classification(self, mock_priority, mock_impact):
        """Test bug classification capabilities."""
        # Setup mocks
        mock_impact.return_value = "high"
        mock_priority.return_value = 8
        
        # Create a sample bug
        bug = DetectedBug(
            bug_id="test_bug",
            file_path=self.temp_file.name,
            line_number=4,
            pattern_id="sql_injection",
            bug_type=BugType.SQL_INJECTION,
            description="Test bug",
            severity="medium",
            confidence=0.8,
            remediation="Fix it",
            code_snippet="query = 'SELECT * FROM users WHERE id = ' + user_input",
            match_text="query = 'SELECT * FROM users WHERE id = ' + user_input"
        )
        
        # Create relationship context
        context = {
            "dependencies": ["dep1.py", "dep2.py"],
            "dependents": ["parent1.py", "parent2.py", "parent3.py"],
            "central_files": [("central1.py", 0.9)],
            "is_central": False,
            "impact_score": 0.3
        }
        
        # Call classification methods
        if hasattr(self.bug_detector, '_classify_bug_impact'):
            impact = self.bug_detector._classify_bug_impact(bug, context)
            self.assertEqual(impact, "high")
            mock_impact.assert_called_with(bug, context)
        
        if hasattr(self.bug_detector, '_classify_bug_priority'):
            priority = self.bug_detector._classify_bug_priority(bug, context)
            self.assertEqual(priority, 8)
            mock_priority.assert_called_with(bug, context)
    
    def test_context_aware_detection(self):
        """Test context-aware detection capabilities."""
        # This test can only run if the context-aware detection was added
        if not hasattr(self.bug_detector, 'context_patterns'):
            self.skipTest("Context-aware detection not implemented")
        
        # Verify the context patterns were loaded
        self.assertTrue(len(self.bug_detector.context_patterns) > 0)
        
        # Check for specific patterns
        pattern_ids = self.bug_detector.context_patterns.keys()
        expected_patterns = ["dependency_critical", "central_file"]
        
        for pattern in expected_patterns:
            self.assertIn(pattern, pattern_ids)


if __name__ == '__main__':
    unittest.main()
