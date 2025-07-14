"""
Unit tests for the BugDetectorAgent.

These tests ensure that the BugDetectorAgent correctly identifies potential bugs
in code, analyzes test failures, and provides meaningful fix recommendations.
"""
import unittest
import os
import tempfile
import shutil
import binascii
from unittest.mock import patch, MagicMock, mock_open

from triangulum_lx.agents.bug_detector_agent import BugDetectorAgent, FileAnalysisResult, BugDetectorError, ErrorSeverity
from triangulum_lx.agents.message import AgentMessage, MessageType


class TestBugDetectorAgent(unittest.TestCase):
    """Test cases for the BugDetectorAgent."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create the agent with a mock message bus
        self.message_bus = MagicMock()
        self.agent = BugDetectorAgent(
            agent_id="test_bug_detector",
            message_bus=self.message_bus,
            config={
                "max_bug_patterns": 100,
                "max_file_size": 1024 * 1024  # 1 MB
            }
        )
    
    def tearDown(self):
        """Clean up after the tests."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def create_test_file(self, filename, content):
        """Create a test file with the given content."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    def test_bug_pattern_management(self):
        """Test adding, enabling, and disabling bug patterns."""
        # Add a new pattern
        result = self.agent.add_bug_pattern(
            pattern_id="test_pattern",
            pattern=r"test\s*pattern",
            languages=["python", "java"],
            description="Test pattern for unit tests",
            severity="medium",
            remediation="Fix the test pattern"
        )
        self.assertTrue(result)
        self.assertIn("test_pattern", self.agent.bug_patterns)
        
        # Disable the pattern
        result = self.agent.disable_bug_pattern("test_pattern")
        self.assertTrue(result)
        self.assertFalse(self.agent.bug_patterns["test_pattern"]["enabled"])
        
        # Enable the pattern
        result = self.agent.enable_bug_pattern("test_pattern")
        self.assertTrue(result)
        self.assertTrue(self.agent.bug_patterns["test_pattern"]["enabled"])
        
        # Try to disable a non-existent pattern
        result = self.agent.disable_bug_pattern("non_existent_pattern")
        self.assertFalse(result)
    
    def test_detect_null_reference_bug(self):
        """Test detecting a null reference bug."""
        # Create a Python file with a null reference bug
        file_content = """
def process_data(data):
    # This will cause a null reference error if data is None
    return data.get('value')

result = process_data(None)
"""
        file_path = self.create_test_file("null_reference.py", file_content)
        
        # Detect bugs in the file
        bugs = self.agent.detect_bugs_in_file(file_path)
        
        # Verify the results
        self.assertGreaterEqual(len(bugs), 1)
        bug = bugs[0]
        self.assertEqual(bug["pattern_id"], "null_pointer")
        self.assertEqual(bug["file"], file_path)
        self.assertEqual(bug["severity"], "high")
    
    def test_detect_resource_leak_bug(self):
        """Test detecting a resource leak bug."""
        # Create a Python file with a resource leak
        file_content = """
def read_file(filename):
    # This file is opened but never closed
    f = open(filename, 'r')
    content = f.read()
    return content
"""
        file_path = self.create_test_file("resource_leak.py", file_content)
        
        # Detect bugs in the file
        bugs = self.agent.detect_bugs_in_file(file_path)
        
        # Verify the results
        self.assertGreaterEqual(len(bugs), 1)
        found_resource_leak = False
        for bug in bugs:
            if bug["pattern_id"] == "resource_leak":
                found_resource_leak = True
                self.assertEqual(bug["file"], file_path)
                self.assertEqual(bug["severity"], "medium")
        
        self.assertTrue(found_resource_leak)
    
    def test_detect_sql_injection_bug(self):
        """Test detecting a SQL injection bug."""
        # Create a Python file with a SQL injection vulnerability
        file_content = """
def get_user(user_id):
    # This is vulnerable to SQL injection
    cursor.execute("SELECT * FROM users WHERE id = " + user_id)
    return cursor.fetchone()
"""
        file_path = self.create_test_file("sql_injection.py", file_content)
        
        # Detect bugs in the file
        bugs = self.agent.detect_bugs_in_file(file_path)
        
        # Verify the results
        self.assertGreaterEqual(len(bugs), 1)
        found_sql_injection = False
        for bug in bugs:
            if bug["pattern_id"] == "sql_injection":
                found_sql_injection = True
                self.assertEqual(bug["file"], file_path)
                self.assertEqual(bug["severity"], "critical")
        
        self.assertTrue(found_sql_injection)
    
    def test_detect_hardcoded_credentials_bug(self):
        """Test detecting hardcoded credentials."""
        # Create a Python file with hardcoded credentials
        file_content = """
def connect_to_database():
    # Hardcoded credentials are a security risk
    password = "supersecret123"
    connection = db.connect("localhost", "admin", password)
    return connection
"""
        file_path = self.create_test_file("hardcoded_credentials.py", file_content)
        
        # Detect bugs in the file
        bugs = self.agent.detect_bugs_in_file(file_path)
        
        # Verify the results
        self.assertGreaterEqual(len(bugs), 1)
        found_hardcoded_credentials = False
        for bug in bugs:
            if bug["pattern_id"] == "hardcoded_credentials":
                found_hardcoded_credentials = True
                self.assertEqual(bug["file"], file_path)
                self.assertEqual(bug["severity"], "critical")
        
        self.assertTrue(found_hardcoded_credentials)
    
    def test_detect_exception_swallowing_bug(self):
        """Test detecting exception swallowing."""
        # Create a Python file with exception swallowing
        file_content = """
def process_data(data):
    try:
        result = complex_operation(data)
        return result
    except Exception:
        # This silently swallows the exception
        pass
"""
        file_path = self.create_test_file("exception_swallowing.py", file_content)
        
        # Detect bugs in the file
        bugs = self.agent.detect_bugs_in_file(file_path)
        
        # Verify the results
        self.assertGreaterEqual(len(bugs), 1)
        found_exception_swallowing = False
        for bug in bugs:
            if bug["pattern_id"] == "exception_swallowing":
                found_exception_swallowing = True
                self.assertEqual(bug["file"], file_path)
                self.assertEqual(bug["severity"], "medium")
        
        self.assertTrue(found_exception_swallowing)
    
    def test_analyze_test_failure(self):
        """Test analyzing a test failure."""
        # Create a Python file with a bug
        file_content = """
def divide(a, b):
    # This will raise a ZeroDivisionError if b is 0
    return a / b

def calculate_ratio(numerator, denominator):
    return divide(numerator, denominator)
"""
        file_path = self.create_test_file("division.py", file_content)
        
        # Create a test failure scenario
        test_name = "test_calculate_ratio"
        error_message = "ZeroDivisionError: division by zero"
        stack_trace = f"""Traceback (most recent call last):
  File "test_division.py", line 5, in test_calculate_ratio
    result = calculate_ratio(10, 0)
  File "{file_path}", line 6, in calculate_ratio
    return divide(numerator, denominator)
  File "{file_path}", line 3, in divide
    return a / b
ZeroDivisionError: division by zero
"""
        
        # Analyze the test failure
        analysis = self.agent.analyze_test_failure(
            test_name=test_name,
            error_message=error_message,
            stack_trace=stack_trace,
            source_files=[file_path]
        )
        
        # Verify the analysis
        self.assertEqual(analysis["test_name"], test_name)
        self.assertEqual(analysis["error_type"], "ZeroDivisionError")
        self.assertIn("recommended_fixes", analysis)
        self.assertGreaterEqual(len(analysis["recommended_fixes"]), 0)
    
    def test_infer_language_from_path(self):
        """Test inferring language from file path."""
        # Test with various file extensions
        self.assertEqual(self.agent._infer_language_from_path("file.py"), "python")
        self.assertEqual(self.agent._infer_language_from_path("file.java"), "java")
        self.assertEqual(self.agent._infer_language_from_path("file.js"), "javascript")
        self.assertEqual(self.agent._infer_language_from_path("file.ts"), "typescript")
        self.assertEqual(self.agent._infer_language_from_path("file.unknown"), "unknown")
    
    def test_extract_error_type(self):
        """Test extracting error type from error message."""
        # Test with various error messages
        self.assertEqual(
            self.agent._extract_error_type("ValueError: invalid literal for int()"),
            "ValueError"
        )
        self.assertEqual(
            self.agent._extract_error_type("java.lang.NullPointerException: null"),
            "java.lang.NullPointerException"
        )
        self.assertEqual(
            self.agent._extract_error_type("TypeError: Cannot read property 'length' of undefined"),
            "TypeError"
        )
    
    def test_extract_error_location(self):
        """Test extracting error location from stack trace."""
        # Test with Python stack trace
        python_stack = """Traceback (most recent call last):
  File "test.py", line 10, in test_function
    result = process(data)
  File "processor.py", line 25, in process
    return transform(data)
ValueError: invalid data
"""
        location = self.agent._extract_error_location(python_stack)
        self.assertEqual(location["file"], "test.py")
        self.assertEqual(location["line"], 10)
        
        # Test with Java stack trace
        java_stack = """java.lang.NullPointerException
    at com.example.Main.process(Main.java:25)
    at com.example.Main.main(Main.java:10)
"""
        location = self.agent._extract_error_location(java_stack)
        self.assertEqual(location["file"], "Main.java")
        self.assertEqual(location["line"], 25)
    
    async def test_handle_task_request_detect_bugs(self):
        """Test handling a task request to detect bugs."""
        # Create a Python file with a bug
        file_content = """
def process_data(data):
    # This will cause a null reference error if data is None
    return data.get('value')
"""
        file_path = self.create_test_file("null_reference.py", file_content)
        
        # Create a mock message
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "detect_bugs_in_file",
                "file_path": file_path
            },
            sender="test_sender"
        )
        
        # Handle the message
        await self.agent._handle_task_request(message)
        
        # Verify that send_response was called with the correct arguments
        self.agent.message_bus.publish.assert_called_once()
        response_msg = self.agent.message_bus.publish.call_args[0][0]
        self.assertEqual(response_msg.message_type, MessageType.TASK_RESULT)
        self.assertEqual(response_msg.content["status"], "success")
        self.assertGreaterEqual(len(response_msg.content["bugs"]), 1)
    
    async def test_handle_query_get_bug_patterns(self):
        """Test handling a query for bug patterns."""
        # Create a mock message
        message = AgentMessage(
            message_type=MessageType.QUERY,
            content={
                "query_type": "get_bug_patterns",
                "language": "python"
            },
            sender="test_sender"
        )
        
        # Handle the message
        await self.agent._handle_query(message)
        
        # Verify that send_response was called with the correct arguments
        self.agent.message_bus.publish.assert_called_once()
        response_msg = self.agent.message_bus.publish.call_args[0][0]
        self.assertEqual(response_msg.message_type, MessageType.QUERY_RESPONSE)
        self.assertEqual(response_msg.content["status"], "success")
        self.assertGreater(len(response_msg.content["patterns"]), 0)
    
    async def test_error_handling(self):
        """Test error handling in message processing."""
        # Create a mock message with an invalid query type
        message = AgentMessage(
            message_type=MessageType.QUERY,
            content={
                "query_type": "invalid_query"
            },
            sender="test_sender"
        )
        
        # Handle the message
        await self.agent._handle_query(message)
        
        # Verify that send_response was called with an error message
        self.agent.message_bus.publish.assert_called_once()
        response_msg = self.agent.message_bus.publish.call_args[0][0]
        self.assertEqual(response_msg.message_type, MessageType.ERROR)
        self.assertEqual(response_msg.content["status"], "error")
        self.assertIn("Unknown query type", response_msg.content["error"])
    
    def test_file_not_found_error_handling(self):
        """Test handling of file not found errors."""
        # Try to analyze a nonexistent file with include_errors=True
        nonexistent_file = os.path.join(self.temp_dir, "nonexistent_file.py")
        result = self.agent.detect_bugs_in_file(
            file_path=nonexistent_file,
            include_errors=True
        )
        
        # Verify the result is a FileAnalysisResult
        self.assertIsInstance(result, FileAnalysisResult)
        self.assertFalse(result.success)
        self.assertFalse(result.partial_success)
        self.assertEqual(len(result.bugs), 0)
        self.assertEqual(len(result.errors), 1)
        
        # Verify the error details
        error = result.errors[0]
        self.assertIsInstance(error, BugDetectorError)
        self.assertEqual(error.error_type, "FileNotFoundError")
        self.assertEqual(error.severity, ErrorSeverity.CRITICAL)
        self.assertFalse(error.recoverable)
        self.assertEqual(error.file_path, nonexistent_file)
        
        # Try with include_errors=False (default)
        result = self.agent.detect_bugs_in_file(file_path=nonexistent_file)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
    
    def test_binary_file_detection(self):
        """Test detection and handling of binary files."""
        # Create a binary file
        binary_file_path = os.path.join(self.temp_dir, "binary_file.bin")
        with open(binary_file_path, 'wb') as f:
            # Write some binary data with null bytes
            f.write(b'\x00\x01\x02\x03\x04\xFF\x00\x01')
        
        # Analyze the binary file with include_errors=True
        result = self.agent.detect_bugs_in_file(
            file_path=binary_file_path,
            include_errors=True
        )
        
        # Verify the result
        self.assertIsInstance(result, FileAnalysisResult)
        self.assertFalse(result.success)
        self.assertEqual(len(result.bugs), 0)
        self.assertEqual(len(result.errors), 1)
        
        # Verify the error details
        error = result.errors[0]
        self.assertEqual(error.error_type, "BinaryFileError")
        self.assertEqual(error.severity, ErrorSeverity.MEDIUM)
        self.assertFalse(error.recoverable)
    
    def test_file_size_limit(self):
        """Test handling of files that exceed the size limit."""
        # Set a very small file size limit for testing
        self.agent.max_file_size = 10
        
        # Create a file that exceeds the size limit
        large_file_path = os.path.join(self.temp_dir, "large_file.py")
        with open(large_file_path, 'w') as f:
            f.write("# " + "x" * 100)  # More than 10 bytes
        
        # Analyze the large file with include_errors=True
        result = self.agent.detect_bugs_in_file(
            file_path=large_file_path,
            include_errors=True
        )
        
        # Verify the result
        self.assertIsInstance(result, FileAnalysisResult)
        self.assertFalse(result.success)
        self.assertEqual(len(result.bugs), 0)
        self.assertEqual(len(result.errors), 1)
        
        # Verify the error details
        error = result.errors[0]
        self.assertEqual(error.error_type, "FileTooLargeError")
        self.assertEqual(error.severity, ErrorSeverity.HIGH)
        self.assertFalse(error.recoverable)
    
    @patch('triangulum_lx.agents.bug_detector_agent.re')
    def test_regex_error_handling(self, mock_re):
        """Test handling of regex errors."""
        # Create a Python file with some content
        file_path = self.create_test_file("regex_test.py", "def test(): pass")
        
        # Mock re.finditer to raise a re.error
        mock_re.error = Exception  # Define re.error
        mock_re.finditer.side_effect = mock_re.error("Invalid regex pattern")
        
        # Analyze the file with include_errors=True
        result = self.agent.detect_bugs_in_file(
            file_path=file_path,
            include_errors=True
        )
        
        # Verify the result
        self.assertIsInstance(result, FileAnalysisResult)
        self.assertFalse(result.success)
        self.assertTrue(result.partial_success)  # Partial success because some patterns might work
        
        # Verify at least one error is present and it's related to regex
        regex_errors = [e for e in result.errors if e.error_type == "RegexError"]
        self.assertGreater(len(regex_errors), 0)
        
        # Verify the error details
        error = regex_errors[0]
        self.assertEqual(error.severity, ErrorSeverity.MEDIUM)
        self.assertTrue(error.recoverable)
    
    def test_folder_analysis_error_handling(self):
        """Test error handling in folder analysis."""
        # Create a nonexistent folder
        nonexistent_folder = os.path.join(self.temp_dir, "nonexistent_folder")
        
        # Analyze the nonexistent folder
        result = self.agent.detect_bugs_in_folder(
            folder_path=nonexistent_folder,
            continue_on_error=True
        )
        
        # Verify the result
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_type"], "FolderNotFoundError")
        self.assertEqual(result["files_analyzed"], 0)
        
        # Create an inaccessible folder if possible
        folder_with_permission_issue = os.path.join(self.temp_dir, "inaccessible_folder")
        os.makedirs(folder_with_permission_issue, exist_ok=True)
        
        # Mock os.walk to raise a permission error
        with patch('os.walk') as mock_walk:
            mock_walk.side_effect = PermissionError("Permission denied")
            
            # Analyze the folder with permission issues
            result = self.agent.detect_bugs_in_folder(
                folder_path=folder_with_permission_issue,
                continue_on_error=True
            )
            
            # Verify the result still has some fields even with the error
            self.assertIn("status", result)
            self.assertIn("files_analyzed", result)
            self.assertIn("bugs_by_file", result)
    
    def test_encoding_detection_and_handling(self):
        """Test detection and handling of different file encodings."""
        # Create a file with UTF-8 content
        utf8_file = self.create_test_file("utf8_file.py", "# UTF-8 content: 你好")
        
        # Test detection of UTF-8
        file_type, encoding = self.agent._detect_file_type(utf8_file)
        self.assertEqual(file_type, "text")
        self.assertIsNotNone(encoding)
        
        # Test reading with proper encoding
        content = self.agent._read_file_with_encoding(utf8_file, encoding)
        self.assertIsNotNone(content)
        self.assertIn("你好", content)
        
        # Mock open to simulate encoding error then fallback
        original_open = open
        
        def mock_open_with_encoding_error(*args, **kwargs):
            if 'encoding' in kwargs and kwargs['encoding'] != 'latin-1':
                raise UnicodeDecodeError('utf-8', b'\x80', 0, 1, 'invalid start byte')
            return original_open(*args, **kwargs)
        
        with patch('builtins.open', side_effect=mock_open_with_encoding_error):
            # Should try multiple encodings and eventually succeed with latin-1
            content = self.agent._read_file_with_encoding(utf8_file, 'utf-8')
            self.assertIsNotNone(content)
    
    async def test_error_response_in_message_handling(self):
        """Test that errors are properly reported in message responses."""
        # Create a task request message with missing file_path
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "detect_bugs_in_file",
                # Missing file_path parameter
            },
            sender="test_sender"
        )
        
        # Handle the message
        await self.agent._handle_task_request(message)
        
        # Verify the error response
        self.agent.message_bus.publish.assert_called_once()
        response_msg = self.agent.message_bus.publish.call_args[0][0]
        self.assertEqual(response_msg.message_type, MessageType.ERROR)
        self.assertEqual(response_msg.content["status"], "error")
        self.assertIn("file_path is required", response_msg.content["error"])


if __name__ == "__main__":
    unittest.main()
