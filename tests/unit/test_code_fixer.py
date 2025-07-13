"""
Unit tests for the CodeFixer class.
"""

import os
import unittest
import tempfile
import shutil
from triangulum_lx.verification.code_fixer import CodeFixer

class TestCodeFixer(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.code_fixer = CodeFixer()
        
        # Copy test file to temp directory
        self.original_file = os.path.join('example_files', 'code_with_issues.py')
        self.test_file = os.path.join(self.test_dir, 'code_with_issues.py')
        shutil.copy(self.original_file, self.test_file)
    
    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_fix_hardcoded_credentials(self):
        """Test that hardcoded credentials are fixed."""
        verification_result = {
            "bug_type": "hardcoded_credentials",
            "overall_success": False,
            "issues": ["Hardcoded credentials detected"]
        }
        
        result = self.code_fixer.fix_code(self.test_file, verification_result)
        
        # Check that the fix was successful
        self.assertTrue(result["success"])
        self.assertTrue(result["modified"])
        self.assertTrue(len(result["fixes_applied"]) > 0)
        
        # Check that hardcoded credentials were replaced with environment variables
        with open(self.test_file, 'r') as f:
            fixed_code = f.read()
        
        self.assertIn("os.environ.get('PASSWORD'", fixed_code)
        self.assertNotIn('password = "supersecret123"', fixed_code)
    
    def test_fix_resource_leak(self):
        """Test that resource leaks are fixed."""
        verification_result = {
            "bug_type": "resource_leak",
            "overall_success": False,
            "issues": ["Resource leak detected"]
        }
        
        result = self.code_fixer.fix_code(self.test_file, verification_result)
        
        # Check that the fix was successful
        self.assertTrue(result["success"])
        self.assertTrue(result["modified"])
        
        # Check that resource leaks were fixed
        with open(self.test_file, 'r') as f:
            fixed_code = f.read()
        
        self.assertTrue(
            "with open(filename, 'r') as f:" in fixed_code or
            "f.close()" in fixed_code
        )
    
    def test_fix_sql_injection(self):
        """Test that SQL injection vulnerabilities are fixed."""
        verification_result = {
            "bug_type": "sql_injection",
            "overall_success": False,
            "issues": ["SQL injection vulnerability detected"]
        }
        
        result = self.code_fixer.fix_code(self.test_file, verification_result)
        
        # Check that the fix was successful
        self.assertTrue(result["success"])
        
        # Check that SQL injection vulnerabilities were fixed
        with open(self.test_file, 'r') as f:
            fixed_code = f.read()
        
        self.assertNotIn('cursor.execute("SELECT * FROM users WHERE id = " + user_id)', fixed_code)
        self.assertIn('%s', fixed_code)
    
    def test_fix_exception_swallowing(self):
        """Test that exception swallowing is fixed."""
        verification_result = {
            "bug_type": "exception_swallowing",
            "overall_success": False,
            "issues": ["Exception swallowing detected"]
        }
        
        result = self.code_fixer.fix_code(self.test_file, verification_result)
        
        # Check that the fix was successful
        self.assertTrue(result["success"])
        
        # Check that exception swallowing was fixed
        with open(self.test_file, 'r') as f:
            fixed_code = f.read()
        
        self.assertNotIn('except ZeroDivisionError:\n        pass', fixed_code)
        self.assertIn('logger.error', fixed_code)
    
    def test_fix_null_pointer(self):
        """Test that null pointer issues are fixed."""
        verification_result = {
            "bug_type": "null_pointer",
            "overall_success": False,
            "issues": ["Null pointer dereference detected"]
        }
        
        result = self.code_fixer.fix_code(self.test_file, verification_result)
        
        # Check that the fix was successful
        self.assertTrue(result["success"])
        
        # Check that null pointer issues were fixed
        with open(self.test_file, 'r') as f:
            fixed_code = f.read()
        
        self.assertIn("if data is None", fixed_code)

if __name__ == '__main__':
    unittest.main()
