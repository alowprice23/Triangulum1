"""
Code fixing capabilities for the verification system.

This module provides functionality for automatically fixing issues found during
verification. It includes support for common bug patterns and can generate patches
to fix those issues.
"""

import os
import re
import ast
import difflib
import logging
from typing import Dict, List, Any, Optional, Union, Tuple

logger = logging.getLogger(__name__)

class CodeFixer:
    """
    Automatically fixes issues in code based on verification results.
    
    This class provides methods to analyze code, detect common issues, and
    generate patches to fix those issues. It supports a variety of bug patterns
    and can adapt to the specific context of the code being fixed.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the code fixer.
        
        Args:
            config: Configuration for the code fixer (optional)
        """
        self.config = config or {}
        
        # Register bug fixers
        self.bug_fixers = {
            "null_pointer": self._fix_null_pointer_issues,
            "resource_leak": self._fix_resource_leak,
            "sql_injection": self._fix_sql_injection,
            "hardcoded_credentials": self._fix_hardcoded_credentials,
            "exception_swallowing": self._fix_exception_swallowing
        }
    
    def fix_code(
        self,
        file_path: str,
        verification_result: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fix issues in code based on verification results.
        
        Args:
            file_path: Path to the file to fix
            verification_result: Verification results with issues to fix
            output_path: Path to save the fixed code (optional, defaults to file_path)
            
        Returns:
            Dictionary with fix results
        """
        # Default to overwriting the original file if output_path is not provided
        output_path = output_path or file_path
        
        # Read the current code
        with open(file_path, 'r') as f:
            current_code = f.read()
        
        # Apply fixes based on the issues found
        fixed_code = current_code
        fixes_applied = []
        
        # Extract bug type from verification result
        bug_type = verification_result.get("bug_type", "unknown")
        if bug_type == "unknown" and "implementation" in verification_result:
            bug_type = verification_result["implementation"].get("bug_type", "unknown")
        
        # Apply specific fixers based on bug type if available
        if bug_type in self.bug_fixers:
            fixed_code, applied = self.bug_fixers[bug_type](
                fixed_code,
                verification_result
            )
            fixes_applied.extend(applied)
        
        # Apply general fixes for any issues not covered by specific fixers
        if not fixes_applied and not verification_result.get("overall_success", False):
            fixed_code, applied = self._apply_general_fixes(
                fixed_code,
                verification_result
            )
            fixes_applied.extend(applied)
        
        # Only write the file if changes were made
        if fixed_code != current_code:
            # Create a diff to show the changes
            diff = self._generate_diff(current_code, fixed_code, file_path)
            
            # Write the fixed code
            with open(output_path, 'w') as f:
                f.write(fixed_code)
            
            logger.info(f"Applied {len(fixes_applied)} fixes to {file_path}")
            if output_path != file_path:
                logger.info(f"Fixed code saved to {output_path}")
            
            result = {
                "success": True,
                "fixes_applied": fixes_applied,
                "diff": diff,
                "modified": True
            }
        else:
            logger.info(f"No fixes applied to {file_path}")
            result = {
                "success": False,
                "fixes_applied": [],
                "diff": "",
                "modified": False
            }
        
        return result
    
    def _generate_diff(
        self,
        old_code: str,
        new_code: str,
        file_path: str
    ) -> str:
        """
        Generate a diff between old and new code.
        
        Args:
            old_code: Original code
            new_code: Fixed code
            file_path: Path to the file being fixed
            
        Returns:
            Diff as a string
        """
        old_lines = old_code.splitlines(True)
        new_lines = new_code.splitlines(True)
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{os.path.basename(file_path)}",
            tofile=f"b/{os.path.basename(file_path)}",
            n=3
        )
        
        return ''.join(diff)
    
    def _extract_function_info(
        self,
        code: str,
        function_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract information about functions in the code.
        
        Args:
            code: Source code to analyze
            function_name: Name of the function to focus on (optional)
            
        Returns:
            Dictionary with function information
        """
        info = {
            "functions": {},
            "classes": {},
            "imports": []
        }
        
        try:
            tree = ast.parse(code)
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        info["imports"].append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for name in node.names:
                        info["imports"].append(f"{module}.{name.name}")
            
            # Extract function definitions
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    func_info = self._extract_function_def(node, code)
                    info["functions"][node.name] = func_info
                    
                    # If this is the function we're looking for, record its location
                    if function_name and node.name == function_name:
                        info["target_function"] = func_info
                
                elif isinstance(node, ast.ClassDef):
                    class_info = {"methods": {}}
                    
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = self._extract_function_def(item, code)
                            class_info["methods"][item.name] = method_info
                            
                            # If this is the method we're looking for, record its location
                            if function_name and f"{node.name}.{item.name}" == function_name:
                                info["target_function"] = method_info
                    
                    info["classes"][node.name] = class_info
        
        except SyntaxError:
            # Code might have syntax errors; try a more basic approach
            logger.warning("Syntax error when parsing code; using regex-based approach")
            
            # Use regex to find function definitions
            function_pattern = r"def\s+(\w+)\s*\("
            for match in re.finditer(function_pattern, code):
                func_name = match.group(1)
                start_pos = match.start()
                
                # Find the function body (naively)
                end_pos = code.find("\n\n", start_pos)
                if end_pos == -1:
                    end_pos = len(code)
                
                info["functions"][func_name] = {
                    "name": func_name,
                    "start": start_pos,
                    "end": end_pos,
                    "body": code[start_pos:end_pos],
                    "parameters": []
                }
                
                # If this is the function we're looking for, record its location
                if function_name and func_name == function_name:
                    info["target_function"] = info["functions"][func_name]
        
        return info
    
    def _extract_function_def(self, node: ast.FunctionDef, code: str) -> Dict[str, Any]:
        """
        Extract information about a function definition.
        
        Args:
            node: AST node for the function definition
            code: Source code
            
        Returns:
            Dictionary with function information
        """
        # Get the function's source code
        start_line = node.lineno - 1  # AST uses 1-indexed line numbers
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
        
        # Get the function's parameters
        parameters = []
        for arg in node.args.args:
            parameters.append(arg.arg)
        
        # Find docstring if it exists
        docstring = ast.get_docstring(node)
        
        # Get the line where the function body starts
        body_start_line = start_line + 1
        if docstring:
            # Skip past the docstring
            body_start_line += docstring.count('\n') + 2  # +2 for the docstring quotes
        
        # Split the code into lines and extract the function's source
        code_lines = code.split('\n')
        func_source = '\n'.join(code_lines[start_line:end_line])
        
        return {
            "name": node.name,
            "start": start_line,
            "end": end_line,
            "body_start": body_start_line,
            "body": func_source,
            "parameters": parameters,
            "docstring": docstring
        }
    
    def _apply_general_fixes(
        self,
        code: str,
        verification_result: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """
        Apply general fixes based on verification results.
        
        Args:
            code: Source code to fix
            verification_result: Verification results with issues to fix
            
        Returns:
            Tuple of (fixed code, list of fixes applied)
        """
        fixed_code = code
        fixes_applied = []
        
        # Get the checks and issues from the verification result
        checks = verification_result.get("checks", {})
        issues = verification_result.get("issues", [])
        
        # Fix syntax issues
        if "syntax" in checks and not checks["syntax"].get("success", True):
            # Attempt to fix common syntax issues
            fixed_code, syntax_fixes = self._fix_syntax_issues(fixed_code)
            if syntax_fixes:
                fixes_applied.extend(syntax_fixes)
        
        # Fix specific issues based on issue descriptions
        for issue in issues:
            issue_lower = issue.lower()
            
            # Check for null/None handling issues
            if "null" in issue_lower or "none" in issue_lower:
                fixed_code, null_fixes = self._fix_null_handling_issues(fixed_code, verification_result)
                if null_fixes:
                    fixes_applied.extend(null_fixes)
            
            # Check for resource handling issues
            elif "resource" in issue_lower or "leak" in issue_lower or "close" in issue_lower:
                fixed_code, resource_fixes = self._fix_resource_handling_issues(fixed_code, verification_result)
                if resource_fixes:
                    fixes_applied.extend(resource_fixes)
            
            # Check for SQL injection issues
            elif "sql" in issue_lower or "injection" in issue_lower or "query" in issue_lower:
                fixed_code, sql_fixes = self._fix_sql_injection_issues(fixed_code, verification_result)
                if sql_fixes:
                    fixes_applied.extend(sql_fixes)
            
            # Check for credential issues
            elif "credential" in issue_lower or "password" in issue_lower or "secret" in issue_lower:
                fixed_code, cred_fixes = self._fix_credential_issues(fixed_code, verification_result)
                if cred_fixes:
                    fixes_applied.extend(cred_fixes)
            
            # Check for exception handling issues
            elif "exception" in issue_lower or "error" in issue_lower or "catch" in issue_lower:
                fixed_code, exception_fixes = self._fix_exception_handling_issues(fixed_code, verification_result)
                if exception_fixes:
                    fixes_applied.extend(exception_fixes)
        
        return fixed_code, fixes_applied
    
    def _fix_syntax_issues(self, code: str) -> Tuple[str, List[str]]:
        """
        Fix common syntax issues in code.
        
        Args:
            code: Source code to fix
            
        Returns:
            Tuple of (fixed code, list of fixes applied)
        """
        fixed_code = code
        fixes_applied = []
        
        # Try to identify and fix common syntax errors
        
        # Fix missing parentheses
        if "(" in fixed_code and ")" not in fixed_code:
            fixed_code = fixed_code + ")"
            fixes_applied.append("Added missing closing parenthesis")
        
        # Fix missing quotes
        quote_chars = ["'", '"', '"""', "'''"]
        for quote in quote_chars:
            count = fixed_code.count(quote)
            if count % 2 == 1:  # Odd number of quotes
                fixed_code = fixed_code + quote
                fixes_applied.append(f"Added missing {quote} quote")
        
        # Fix indentation issues
        lines = fixed_code.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            if i > 0 and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                # Check if previous line ends with a colon (indicating a block should start)
                if lines[i-1].strip().endswith(':'):
                    fixed_lines.append('    ' + line)
                    fixes_applied.append(f"Fixed indentation on line {i+1}")
                    continue
            
            fixed_lines.append(line)
        
        if fixed_lines != lines:
            fixed_code = '\n'.join(fixed_lines)
        
        return fixed_code, fixes_applied
    
    def _fix_null_handling_issues(
        self, 
        code: str, 
        verification_result: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """
        Fix issues related to null/None handling.
        
        Args:
            code: Source code to fix
            verification_result: Verification results
            
        Returns:
            Tuple of (fixed code, list of fixes applied)
        """
        fixed_code = code
        fixes_applied = []
        
        # Look for variable access without None checks
        # This is a simplified approach - in a real implementation, you would
        # need more sophisticated analysis to identify variables that could be None
        pattern = r'(\w+)\.(\w+)'
        
        for match in re.finditer(pattern, fixed_code):
            var_name = match.group(1)
            attr_name = match.group(2)
            
            # Check if there's already a null check for this variable
            if f"if {var_name} is None" not in fixed_code and f"if {var_name} is not None" not in fixed_code:
                # Try to find a suitable location to add the null check
                # For simplicity, we'll look for the first occurrence of the variable
                var_match = re.search(rf'\b{var_name}\b\s*=', fixed_code)
                
                if var_match:
                    # Find the end of the line
                    line_end = fixed_code.find('\n', var_match.end())
                    if line_end == -1:
                        line_end = len(fixed_code)
                    
                    # Add the null check after the variable assignment
                    null_check = f"\nif {var_name} is None:\n    return None  # Handle null input"
                    fixed_code = fixed_code[:line_end] + null_check + fixed_code[line_end:]
                    
                    fixes_applied.append(f"Added null check for variable '{var_name}'")
        
        # Look for direct attribute access that might cause AttributeError
        for match in re.finditer(pattern, fixed_code):
            var_name = match.group(1)
            attr_name = match.group(2)
            
            # Check if the attribute access is already wrapped in a safe check
            if f"getattr({var_name}, '{attr_name}'" not in fixed_code:
                # Replace direct attribute access with getattr
                replacement = f"getattr({var_name}, '{attr_name}', None)"
                expr = f"{var_name}.{attr_name}"
                
                # Only replace standalone expressions, not method calls
                if not re.search(rf'{re.escape(expr)}\s*\(', fixed_code):
                    fixed_code = fixed_code.replace(expr, replacement)
                    fixes_applied.append(f"Replaced direct attribute access with getattr for '{expr}'")
        
        return fixed_code, fixes_applied
    
    def _fix_resource_handling_issues(
        self, 
        code: str, 
        verification_result: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """
        Fix issues related to resource handling.
        
        Args:
            code: Source code to fix
            verification_result: Verification results
            
        Returns:
            Tuple of (fixed code, list of fixes applied)
        """
        # This function delegates to _fix_resource_leak which implements this functionality
        return self._fix_resource_leak(code, verification_result)
    
    def _fix_resource_leak(
        self,
        code: str,
        verification_result: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """
        Fix resource leak issues in code.
        
        Args:
            code: Source code to fix
            verification_result: Verification results
            
        Returns:
            Tuple of (fixed code, list of fixes applied)
        """
        fixed_code = code
        fixes_applied = []
        
        # Pattern to find resource acquisition without proper release
        # This is a simplified approach focused on file handling
        open_pattern = r'(\w+)\s*=\s*open\([^)]+\)'
        
        for match in re.finditer(open_pattern, fixed_code):
            var_name = match.group(1)
            
            # Check if the file is properly closed
            if f"{var_name}.close()" not in fixed_code and f"with open" not in match.group(0):
                # Find a good place to add the close statement
                # Look for the end of the function or the last use of the variable
                var_uses = list(re.finditer(rf'{var_name}\.\w+', fixed_code))
                
                if var_uses:
                    last_use = var_uses[-1]
                    last_use_end = last_use.end()
                    
                    # Find the end of the line
                    line_end = fixed_code.find('\n', last_use_end)
                    if line_end == -1:
                        line_end = len(fixed_code)
                    
                    # Add close statement after the last use
                    close_stmt = f"\n    {var_name}.close()  # Close resource to prevent leak"
                    fixed_code = fixed_code[:line_end] + close_stmt + fixed_code[line_end:]
                    
                    fixes_applied.append(f"Added close() for resource {var_name}")
                
                # Alternatively, convert to using 'with' statement
                if not fixes_applied:
                    start_pos = match.start()
                    end_pos = match.end()
                    
                    # Extract the open function call
                    open_call = match.group(0).split('=')[1].strip()
                    
                    # Find the indentation
                    line_start = fixed_code.rfind('\n', 0, start_pos) + 1
                    indentation = ' ' * (start_pos - line_start)
                    
                    # Replace with 'with' statement
                    with_stmt = f"with {open_call} as {var_name}"
                    fixed_code = fixed_code[:start_pos] + with_stmt + fixed_code[end_pos:]
                    
                    fixes_applied.append(f"Replaced direct open() with 'with' statement for {var_name}")
        
        # Pattern to find other resources that need explicit cleanup
        # This is a simplified approach focused on database connections
        conn_pattern = r'(\w+)\s*=\s*\w+\.connect\([^)]*\)'
        
        for match in re.finditer(conn_pattern, fixed_code):
            var_name = match.group(1)
            
            # Check if the connection is properly closed
            if f"{var_name}.close()" not in fixed_code:
                # Find a good place to add the close statement
                var_uses = list(re.finditer(rf'{var_name}\.\w+', fixed_code))
                
                if var_uses:
                    last_use = var_uses[-1]
                    last_use_end = last_use.end()
                    
                    # Find the end of the line
                    line_end = fixed_code.find('\n', last_use_end)
                    if line_end == -1:
                        line_end = len(fixed_code)
                    
                    # Add close statement after the last use
                    close_stmt = f"\n    {var_name}.close()  # Close connection to prevent resource leak"
                    fixed_code = fixed_code[:line_end] + close_stmt + fixed_code[line_end:]
                    
                    fixes_applied.append(f"Added close() for connection {var_name}")
        
        return fixed_code, fixes_applied
    
    def _fix_null_pointer_issues(
        self,
        code: str,
        verification_result: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """
        Fix null pointer issues in code.
        
        Args:
            code: Source code to fix
            verification_result: Verification results
            
        Returns:
            Tuple of (fixed code, list of fixes applied)
        """
        fixed_code = code
        fixes_applied = []
        
        # Extract function information to find parameters and variables
        func_info = self._extract_function_info(code)
        
        # Look for dictionary access without get()
        dict_access_pattern = r'(\w+)\[[\'"](.*?)[\'"]\]'
        
        for match in re.finditer(dict_access_pattern, fixed_code):
            dict_name = match.group(1)
            key = match.group(2)
            
            # Replace with safer get() method if it's not already in a condition
            # This is a simplistic approach and might need context-specific adjustments
            expr = f"{dict_name}['{key}']"
            if expr in fixed_code:
                # Check if it's already inside a condition
                if not re.search(rf'if\s+{dict_name}\s*(?:and|or|not|is|in|==|!=|>|<|>=|<=)', fixed_code):
                    replacement = f"{dict_name}.get('{key}')"
                    fixed_code = fixed_code.replace(expr, replacement)
                    fixes_applied.append(f"Replaced unsafe dictionary access with get() for '{expr}'")
        
        # Look for direct attribute access on variables that could be None
        attr_access_pattern = r'(\w+)\.(\w+)'
        
        for match in re.finditer(attr_access_pattern, fixed_code):
            var_name = match.group(1)
            attr_name = match.group(2)
            
            # Check if there's already a null check for this variable
            if f"if {var_name} is None" not in fixed_code and f"if {var_name} is not None" not in fixed_code:
                # Try to find a suitable location to add the null check
                # Look for assignments to this variable
                var_assignment = re.search(rf'\b{var_name}\b\s*=', fixed_code)
                
                if var_assignment:
                    # Find the function containing this variable
                    func_start = fixed_code.rfind('def ', 0, var_assignment.start())
                    if func_start != -1:
                        # Find the indentation level
                        func_line_end = fixed_code.find('\n', func_start)
                        next_line_start = func_line_end + 1
                        next_line_end = fixed_code.find('\n', next_line_start)
                        if next_line_end == -1:
                            next_line_end = len(fixed_code)
                        
                        indentation = ''
                        for char in fixed_code[next_line_start:next_line_end]:
                            if char in (' ', '\t'):
                                indentation += char
                            else:
                                break
                        
                        # Find the end of the assignment line
                        assign_line_end = fixed_code.find('\n', var_assignment.end())
                        if assign_line_end == -1:
                            assign_line_end = len(fixed_code)
                        
                        # Add null check after the assignment
                        null_check = f"\n{indentation}if {var_name} is None:\n{indentation}    return None  # Handle null input"
                        fixed_code = fixed_code[:assign_line_end] + null_check + fixed_code[assign_line_end:]
                        
                        fixes_applied.append(f"Added null check for variable '{var_name}'")
        
        # Add null checks for function parameters
        for func_name, func_data in func_info["functions"].items():
            params = func_data.get("parameters", [])
            
            for param in params:
                # Skip self parameter in methods
                if param == 'self':
                    continue
                
                # Check if there's already a null check for this parameter
                if f"if {param} is None" not in fixed_code and f"if {param} is not None" not in fixed_code:
                    # Find the function body start
                    body_start = func_data.get("body_start", 0)
                    
                    # Find the indentation level
                    body_line_end = fixed_code.find('\n', body_start)
                    if body_line_end == -1:
                        body_line_end = len(fixed_code)
                    
                    indentation = ''
                    for char in fixed_code[body_start:body_line_end]:
                        if char in (' ', '\t'):
                            indentation += char
                        else:
                            break
                    
                    # Check if parameter is used with attribute access
                    if re.search(rf'\b{param}\.\w+', fixed_code):
                        # Add null check at the beginning of the function body
                        null_check = f"{indentation}if {param} is None:\n{indentation}    return None  # Handle null input\n"
                        insert_pos = body_start
                        fixed_code = fixed_code[:insert_pos] + null_check + fixed_code[insert_pos:]
                        
                        fixes_applied.append(f"Added null check for parameter '{param}' in function '{func_name}'")
        
        return fixed_code, fixes_applied
    
    def _fix_sql_injection(
        self,
        code: str,
        verification_result: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """
        Fix SQL injection issues in code.
        
        Args:
            code: Source code to fix
            verification_result: Verification results
            
        Returns:
            Tuple of (fixed code, list of fixes applied)
        """
        fixed_code = code
        fixes_applied = []
        
        # Pattern to find SQL queries with string concatenation
        concat_query_pattern = r'cursor\.execute\s*\(\s*(["\'])(.*?)(?:\s*\+\s*)([^)]+)\)'
        
        for match in re.finditer(concat_query_pattern, fixed_code):
            quote = match.group(1)
            query_part = match.group(2)
            concat_var = match.group(3).strip()
            
            # Create a parameterized query
            if query_part.strip() and concat_var:
                # Check if the query ends with a space
                if not query_part.endswith(' '):
                    query_part += ' '
                
                # Replace the concatenation with a parameterized query
                parameterized_query = f"cursor.execute({quote}{query_part}%s{quote}, ({concat_var},))"
                fixed_code = fixed_code.replace(match.group(0), parameterized_query)
                
                fixes_applied.append(f"Replaced string concatenation in SQL query with parameterized query using {concat_var}")
        
        # Pattern to find execute with format string
        format_query_pattern = r'cursor\.execute\s*\(\s*(["\'])(.*?)%s(.*?)(?:["\'])\s*%\s*([^)]+)\)'
        
        for match in re.finditer(format_query_pattern, fixed_code):
            quote = match.group(1)
            query_before = match.group(2)
            query_after = match.group(3)
            format_var = match.group(4).strip()
            
            # Replace with proper parameterization
            if format_var:
                parameterized_query = f"cursor.execute({quote}{query_before}%s{query_after}{quote}, ({format_var},))"
                fixed_code = fixed_code.replace(match.group(0), parameterized_query)
                
                fixes_applied.append(f"Fixed SQL query parameterization for variable {format_var}")
        
        # Pattern to find execute with f-strings (Python 3.6+)
        fstring_query_pattern = r'cursor\.execute\s*\(\s*f(["\'])(.*?){\s*([^}]+)\s*}(.*?)(["\'])\s*\)'
        
        for match in re.finditer(fstring_query_pattern, fixed_code):
            quote = match.group(1)
            query_before = match.group(2)
            var_name = match.group(3).strip()
            query_after = match.group(4)
            
            # Replace with proper parameterization
            parameterized_query = f"cursor.execute({quote}{query_before}%s{query_after}{quote}, ({var_name},))"
            fixed_code = fixed_code.replace(match.group(0), parameterized_query)
            
            fixes_applied.append(f"Replaced f-string SQL query with parameterized query for variable {var_name}")
        
        return fixed_code, fixes_applied
    
    def _fix_sql_injection_issues(
        self, 
        code: str, 
        verification_result: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """
        Fix SQL injection issues in code.
        
        Args:
            code: Source code to fix
            verification_result: Verification results
            
        Returns:
            Tuple of (fixed code, list of fixes applied)
        """
        # This function delegates to _fix_sql_injection which implements this functionality
        return self._fix_sql_injection(code, verification_result)
    
    def _fix_credential_issues(
        self, 
        code: str, 
        verification_result: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """
        Fix issues related to handling credentials.
        
        Args:
            code: Source code to fix
            verification_result: Verification results
            
        Returns:
            Tuple of (fixed code, list of fixes applied)
        """
        # This function delegates to _fix_hardcoded_credentials which implements this functionality
        return self._fix_hardcoded_credentials(code, verification_result)
    
    def _fix_exception_handling_issues(
        self, 
        code: str, 
        verification_result: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """
        Fix issues related to exception handling.
        
        Args:
            code: Source code to fix
            verification_result: Verification results
            
        Returns:
            Tuple of (fixed code, list of fixes applied)
        """
        fixed_code = code
        fixes_applied = []
        
        # Look for empty except blocks (exception swallowing)
        empty_except_pattern = r'except\s+(\w+(?:\.\w+)*)(?:\s+as\s+\w+)?:\s*\n\s*pass'
        
        for match in re.finditer(empty_except_pattern, fixed_code):
            exception_type = match.group(1)
            
            # Replace empty except block with logging
            replacement = f"except {exception_type} as e:\n    logger.error(f\"Exception occurred: {{e}}\")"
            fixed_code = fixed_code.replace(match.group(0), replacement)
            
            fixes_applied.append(f"Added logging to empty except block for {exception_type}")
        
        # Look for broad exception handlers
        broad_except_pattern = r'except\s*:'
        
        for match in re.finditer(broad_except_pattern, fixed_code):
            # Replace broad except with specific exceptions
            replacement = "except Exception as e:"
            fixed_code = fixed_code.replace(match.group(0), replacement)
            
            fixes_applied.append("Replaced broad except with specific Exception type")
        
        # Look for try blocks without finally
        try_without_finally_pattern = r'try:.*?except.*?(?:^\s*\S|\Z)'
        
        for match in re.search(try_without_finally_pattern, fixed_code, re.DOTALL):
            if "finally:" not in match.group(0):
                # Find the end of the except block
                except_pos = match.group(0).rfind("except")
                end_pos = len(match.group(0))
                
                # Add a finally block
                finally_block = "\nfinally:\n    # Ensure resources are properly cleaned up\n    pass"
                
                # Insert the finally block
                fixed_block = match.group(0)[:end_pos] + finally_block
                fixed_code = fixed_code.replace(match.group(0), fixed_block)
                
                fixes_applied.append("Added finally block to try-except")
        
        return fixed_code, fixes_applied
    
    def _fix_exception_swallowing(
        self, 
        code: str, 
        verification_result: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """
        Fix exception swallowing issues in code.
        
        Args:
            code: Source code to fix
            verification_result: Verification results
            
        Returns:
            Tuple of (fixed code, list of fixes applied)
        """
        fixed_code = code
        fixes_applied = []
        
        # Look for empty except blocks or except blocks with only pass
        empty_except_pattern = r'except\s+([^:]+)(?:\s+as\s+(\w+))?:\s*(?:pass|#[^\n]*)?(?:\n\s*)+(?=\S|$)'
        
        for match in re.finditer(empty_except_pattern, fixed_code):
            exception_type = match.group(1)
            exception_var = match.group(2) or 'e'
            
            # Replace with proper error handling
            if "as" in match.group(0):
                replacement = f"except {exception_type}:\n    logger.error(f\"Exception occurred: {{{exception_var}}}\")\n    raise  # Re-raise the exception after logging\n"
            else:
                replacement = f"except {exception_type} as {exception_var}:\n    logger.error(f\"Exception occurred: {{{exception_var}}}\")\n    raise  # Re-raise the exception after logging\n"
                
            fixed_code = fixed_code.replace(match.group(0), replacement)
            
            fixes_applied.append(f"Fixed exception swallowing in except block for {exception_type}")
        
        # Look for try-except blocks that completely silence exceptions
        silent_try_pattern = r'try:\s*([^#\n]+)(?:\n\s+[^#\n]+)*\s*except\s+([^:]+)(?:\s+as\s+(\w+))?:\s*pass'
        
        for match in re.finditer(silent_try_pattern, fixed_code):
            code_in_try = match.group(1).strip()
            exception_type = match.group(2)
            exception_var = match.group(3) or 'e'
            
            # Replace with proper error handling
            replacement = f"try:\n    {code_in_try}\nexcept {exception_type} as {exception_var}:\n    logger.warning(f\"Handled exception in {code_in_try}: {{{exception_var}}}\")"
            fixed_code = fixed_code.replace(match.group(0), replacement)
            
            fixes_applied.append(f"Improved exception handling for {code_in_try}")
        
        return fixed_code, fixes_applied
    
    def _fix_hardcoded_credentials(
        self,
        code: str,
        verification_result: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """
        Fix hardcoded credentials issues in code.
        
        Args:
            code: Source code to fix
            verification_result: Verification results
            
        Returns:
            Tuple of (fixed code, list of fixes applied)
        """
        fixed_code = code
        fixes_applied = []
        
        # Look for hardcoded credentials
        credential_patterns = [
            (r'password\s*=\s*["\']([^"\']+)["\']', 'password', 'PASSWORD'),
            (r'passwd\s*=\s*["\']([^"\']+)["\']', 'passwd', 'PASSWORD'),
            (r'pwd\s*=\s*["\']([^"\']+)["\']', 'pwd', 'PASSWORD'),
            (r'api_key\s*=\s*["\']([^"\']+)["\']', 'api_key', 'API_KEY'),
            (r'apikey\s*=\s*["\']([^"\']+)["\']', 'apikey', 'API_KEY'),
            (r'secret\s*=\s*["\']([^"\']+)["\']', 'secret', 'SECRET'),
            (r'token\s*=\s*["\']([^"\']+)["\']', 'token', 'TOKEN')
        ]
        
        # Add imports for os module if not already present
        if "import os" not in fixed_code and "from os import" not in fixed_code:
            fixed_code = "import os\n" + fixed_code
            fixes_applied.append("Added import for os module")
        
        # Replace hardcoded credentials with environment variables
        for pattern, var_name, env_var in credential_patterns:
            for match in re.finditer(pattern, fixed_code):
                # Extract the credential value
                credential = match.group(1)
                
                # Replace the hardcoded credential with an environment variable
                replacement = f"{var_name} = os.environ.get('{env_var}', 'default_{var_name}')"
                fixed_code = fixed_code.replace(match.group(0), replacement)
                
                fixes_applied.append(f"Replaced hardcoded {var_name} with environment variable {env_var}")
                
                # Add a comment about setting up environment variables
                if "# Set up environment variables before running:" not in fixed_code:
                    comment = f"# Set up environment variables before running:\n# export {env_var}=your_{var_name}_here\n"
                    # Add the comment at the beginning of the file after any imports
                    import_end = 0
                    for line in fixed_code.split("\n"):
                        if line.startswith("import ") or line.startswith("from "):
                            import_end = fixed_code.find(line) + len(line) + 1
                    
                    fixed_code = fixed_code[:import_end] + "\n" + comment + fixed_code[import_end:]
                    fixes_applied.append("Added comment about setting up environment variables")
        
        return fixed_code, fixes_applied
