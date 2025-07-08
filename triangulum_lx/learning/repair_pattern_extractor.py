#!/usr/bin/env python3
"""
Repair Pattern Extractor

This module analyzes successful repairs to identify patterns that can be applied to
similar issues in the future. It extracts features from code context, categorizes
patterns, and provides similarity matching for new issues.
"""

import os
import json
import time
import logging
import hashlib
import difflib
import re
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("triangulum.repair_pattern_extractor")

# Try to import optional dependencies
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import DBSCAN
    HAVE_ML_DEPS = True
except ImportError:
    logger.warning("Machine learning dependencies not available. Using basic pattern extraction only.")
    HAVE_ML_DEPS = False


class RepairPattern:
    """
    Represents a repair pattern extracted from successful fixes.
    """
    
    def __init__(self, 
                 pattern_id: str,
                 bug_type: str,
                 before_pattern: str,
                 after_pattern: str,
                 context_features: Dict[str, Any],
                 metadata: Dict[str, Any]):
        """
        Initialize a repair pattern.
        
        Args:
            pattern_id: Unique identifier for the pattern
            bug_type: Type of bug this pattern addresses
            before_pattern: Pattern of code before the fix
            after_pattern: Pattern of code after the fix
            context_features: Features extracted from the code context
            metadata: Additional metadata about the pattern
        """
        self.pattern_id = pattern_id
        self.bug_type = bug_type
        self.before_pattern = before_pattern
        self.after_pattern = after_pattern
        self.context_features = context_features
        self.metadata = metadata
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.usage_count = 0
        self.success_count = 0
        self.confidence_score = 0.5  # Initial confidence score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary for serialization."""
        return {
            "pattern_id": self.pattern_id,
            "bug_type": self.bug_type,
            "before_pattern": self.before_pattern,
            "after_pattern": self.after_pattern,
            "context_features": self.context_features,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "confidence_score": self.confidence_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RepairPattern':
        """Create pattern from dictionary."""
        pattern = cls(
            pattern_id=data["pattern_id"],
            bug_type=data["bug_type"],
            before_pattern=data["before_pattern"],
            after_pattern=data["after_pattern"],
            context_features=data["context_features"],
            metadata=data["metadata"]
        )
        
        # Restore state
        pattern.created_at = data["created_at"]
        pattern.updated_at = data["updated_at"]
        pattern.usage_count = data["usage_count"]
        pattern.success_count = data["success_count"]
        pattern.confidence_score = data["confidence_score"]
        
        return pattern
    
    def update_confidence(self, success: bool):
        """
        Update the confidence score based on usage success.
        
        Args:
            success: Whether the pattern was successfully applied
        """
        self.usage_count += 1
        if success:
            self.success_count += 1
        
        # Update confidence score using Bayesian update
        # Start with a prior of 0.5 and update based on success rate
        alpha = 1.0 + self.success_count
        beta = 1.0 + (self.usage_count - self.success_count)
        self.confidence_score = alpha / (alpha + beta)
        
        self.updated_at = datetime.now().isoformat()


class RepairPatternExtractor:
    """
    Extracts repair patterns from successful fixes.
    """
    
    def __init__(self, database_path: Optional[str] = None):
        """
        Initialize the repair pattern extractor.
        
        Args:
            database_path: Path to the pattern database file
        """
        self.database_path = database_path or "triangulum_lx/learning/repair_patterns.json"
        self.patterns: Dict[str, RepairPattern] = {}
        self.pattern_clusters: Dict[str, List[str]] = {}
        
        # Initialize vectorizer for similarity matching
        self.vectorizer = None
        if HAVE_ML_DEPS:
            self.vectorizer = TfidfVectorizer(
                analyzer='word',
                token_pattern=r'[a-zA-Z_][a-zA-Z0-9_]*|\S',
                ngram_range=(1, 3),
                max_features=5000
            )
        
        # Load patterns if available
        self._load_patterns()
    
    def _load_patterns(self):
        """Load patterns from the database file."""
        if os.path.exists(self.database_path):
            try:
                with open(self.database_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load patterns
                for pattern_data in data.get("patterns", []):
                    pattern = RepairPattern.from_dict(pattern_data)
                    self.patterns[pattern.pattern_id] = pattern
                
                # Load pattern clusters
                self.pattern_clusters = data.get("pattern_clusters", {})
                
                logger.info(f"Loaded {len(self.patterns)} patterns from {self.database_path}")
            except Exception as e:
                logger.error(f"Error loading patterns: {e}")
                self.patterns = {}
                self.pattern_clusters = {}
        else:
            logger.info("No pattern database found. Starting with empty database.")
    
    def _save_patterns(self):
        """Save patterns to the database file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
            
            # Prepare data for serialization
            data = {
                "patterns": [pattern.to_dict() for pattern in self.patterns.values()],
                "pattern_clusters": self.pattern_clusters,
                "last_updated": datetime.now().isoformat()
            }
            
            # Save to file
            with open(self.database_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Saved {len(self.patterns)} patterns to {self.database_path}")
        except Exception as e:
            logger.error(f"Error saving patterns: {e}")
    
    def extract_pattern(self, 
                       bug_type: str,
                       before_code: str,
                       after_code: str,
                       file_path: str,
                       bug_description: Optional[str] = None,
                       fix_description: Optional[str] = None) -> str:
        """
        Extract a repair pattern from a successful fix.
        
        Args:
            bug_type: Type of bug that was fixed
            before_code: Code before the fix
            after_code: Code after the fix
            file_path: Path to the file that was fixed
            bug_description: Description of the bug
            fix_description: Description of the fix
            
        Returns:
            Pattern ID
        """
        # Generate pattern ID
        timestamp = int(time.time())
        content_hash = hashlib.md5(f"{bug_type}{before_code}{after_code}".encode()).hexdigest()[:8]
        pattern_id = f"pattern_{timestamp}_{content_hash}"
        
        # Extract diff between before and after code
        diff = self._extract_diff(before_code, after_code)
        
        # Extract context features
        context_features = self._extract_context_features(
            before_code, after_code, file_path, bug_type, diff
        )
        
        # Create metadata
        metadata = {
            "file_path": file_path,
            "bug_description": bug_description,
            "fix_description": fix_description,
            "extracted_at": datetime.now().isoformat()
        }
        
        # Extract before and after patterns
        before_pattern, after_pattern = self._extract_patterns(before_code, after_code, diff)
        
        # Create pattern
        pattern = RepairPattern(
            pattern_id=pattern_id,
            bug_type=bug_type,
            before_pattern=before_pattern,
            after_pattern=after_pattern,
            context_features=context_features,
            metadata=metadata
        )
        
        # Add pattern to database
        self.patterns[pattern_id] = pattern
        
        # Update pattern clusters
        self._update_pattern_clusters()
        
        # Save patterns
        self._save_patterns()
        
        logger.info(f"Extracted pattern {pattern_id} for bug type {bug_type}")
        return pattern_id
    
    def _extract_diff(self, before_code: str, after_code: str) -> List[str]:
        """
        Extract diff between before and after code.
        
        Args:
            before_code: Code before the fix
            after_code: Code after the fix
            
        Returns:
            List of diff lines
        """
        before_lines = before_code.splitlines()
        after_lines = after_code.splitlines()
        
        differ = difflib.Differ()
        diff = list(differ.compare(before_lines, after_lines))
        
        return diff
    
    def _extract_context_features(self, 
                                 before_code: str,
                                 after_code: str,
                                 file_path: str,
                                 bug_type: str,
                                 diff: List[str]) -> Dict[str, Any]:
        """
        Extract context features from code.
        
        Args:
            before_code: Code before the fix
            after_code: Code after the fix
            file_path: Path to the file that was fixed
            bug_type: Type of bug that was fixed
            diff: Diff between before and after code
            
        Returns:
            Dictionary of context features
        """
        # Extract file extension
        file_extension = os.path.splitext(file_path)[1].lower()
        
        # Extract language-specific features
        language_features = self._extract_language_features(before_code, file_extension)
        
        # Extract code structure features
        structure_features = self._extract_structure_features(before_code)
        
        # Extract diff features
        diff_features = self._extract_diff_features(diff)
        
        # Extract bug type features
        bug_features = self._extract_bug_features(bug_type, before_code)
        
        # Combine features
        context_features = {
            "file_extension": file_extension,
            "language_features": language_features,
            "structure_features": structure_features,
            "diff_features": diff_features,
            "bug_features": bug_features
        }
        
        return context_features
    
    def _extract_language_features(self, code: str, file_extension: str) -> Dict[str, Any]:
        """
        Extract language-specific features from code.
        
        Args:
            code: Code to extract features from
            file_extension: File extension
            
        Returns:
            Dictionary of language features
        """
        # Determine language based on file extension
        language = "unknown"
        if file_extension in [".py", ".pyw"]:
            language = "python"
        elif file_extension in [".js", ".jsx", ".ts", ".tsx"]:
            language = "javascript"
        elif file_extension in [".java"]:
            language = "java"
        elif file_extension in [".c", ".cpp", ".cc", ".cxx", ".h", ".hpp"]:
            language = "c_cpp"
        elif file_extension in [".rb"]:
            language = "ruby"
        elif file_extension in [".go"]:
            language = "go"
        elif file_extension in [".php"]:
            language = "php"
        elif file_extension in [".cs"]:
            language = "csharp"
        
        # Extract language-specific features
        features = {
            "language": language,
            "tokens": {}
        }
        
        # Extract tokens based on language
        if language == "python":
            # Python-specific tokens
            features["tokens"] = {
                "import_count": len(re.findall(r'\bimport\b', code)),
                "from_import_count": len(re.findall(r'\bfrom\s+\S+\s+import\b', code)),
                "def_count": len(re.findall(r'\bdef\b', code)),
                "class_count": len(re.findall(r'\bclass\b', code)),
                "if_count": len(re.findall(r'\bif\b', code)),
                "else_count": len(re.findall(r'\belse\b', code)),
                "for_count": len(re.findall(r'\bfor\b', code)),
                "while_count": len(re.findall(r'\bwhile\b', code)),
                "try_count": len(re.findall(r'\btry\b', code)),
                "except_count": len(re.findall(r'\bexcept\b', code)),
                "with_count": len(re.findall(r'\bwith\b', code)),
                "lambda_count": len(re.findall(r'\blambda\b', code)),
                "return_count": len(re.findall(r'\breturn\b', code))
            }
        elif language in ["javascript", "typescript"]:
            # JavaScript/TypeScript-specific tokens
            features["tokens"] = {
                "import_count": len(re.findall(r'\bimport\b', code)),
                "export_count": len(re.findall(r'\bexport\b', code)),
                "function_count": len(re.findall(r'\bfunction\b', code)),
                "class_count": len(re.findall(r'\bclass\b', code)),
                "if_count": len(re.findall(r'\bif\b', code)),
                "else_count": len(re.findall(r'\belse\b', code)),
                "for_count": len(re.findall(r'\bfor\b', code)),
                "while_count": len(re.findall(r'\bwhile\b', code)),
                "try_count": len(re.findall(r'\btry\b', code)),
                "catch_count": len(re.findall(r'\bcatch\b', code)),
                "const_count": len(re.findall(r'\bconst\b', code)),
                "let_count": len(re.findall(r'\blet\b', code)),
                "var_count": len(re.findall(r'\bvar\b', code)),
                "return_count": len(re.findall(r'\breturn\b', code))
            }
        elif language == "java":
            # Java-specific tokens
            features["tokens"] = {
                "import_count": len(re.findall(r'\bimport\b', code)),
                "package_count": len(re.findall(r'\bpackage\b', code)),
                "class_count": len(re.findall(r'\bclass\b', code)),
                "interface_count": len(re.findall(r'\binterface\b', code)),
                "public_count": len(re.findall(r'\bpublic\b', code)),
                "private_count": len(re.findall(r'\bprivate\b', code)),
                "protected_count": len(re.findall(r'\bprotected\b', code)),
                "static_count": len(re.findall(r'\bstatic\b', code)),
                "if_count": len(re.findall(r'\bif\b', code)),
                "else_count": len(re.findall(r'\belse\b', code)),
                "for_count": len(re.findall(r'\bfor\b', code)),
                "while_count": len(re.findall(r'\bwhile\b', code)),
                "try_count": len(re.findall(r'\btry\b', code)),
                "catch_count": len(re.findall(r'\bcatch\b', code)),
                "return_count": len(re.findall(r'\breturn\b', code))
            }
        elif language == "c_cpp":
            # C/C++-specific tokens
            features["tokens"] = {
                "include_count": len(re.findall(r'#include', code)),
                "define_count": len(re.findall(r'#define', code)),
                "struct_count": len(re.findall(r'\bstruct\b', code)),
                "class_count": len(re.findall(r'\bclass\b', code)),
                "public_count": len(re.findall(r'\bpublic\b', code)),
                "private_count": len(re.findall(r'\bprivate\b', code)),
                "protected_count": len(re.findall(r'\bprotected\b', code)),
                "static_count": len(re.findall(r'\bstatic\b', code)),
                "if_count": len(re.findall(r'\bif\b', code)),
                "else_count": len(re.findall(r'\belse\b', code)),
                "for_count": len(re.findall(r'\bfor\b', code)),
                "while_count": len(re.findall(r'\bwhile\b', code)),
                "try_count": len(re.findall(r'\btry\b', code)),
                "catch_count": len(re.findall(r'\bcatch\b', code)),
                "return_count": len(re.findall(r'\breturn\b', code))
            }
        
        return features
    
    def _extract_structure_features(self, code: str) -> Dict[str, Any]:
        """
        Extract code structure features.
        
        Args:
            code: Code to extract features from
            
        Returns:
            Dictionary of structure features
        """
        # Count lines
        lines = code.splitlines()
        line_count = len(lines)
        
        # Count indentation levels
        indentation_levels = set()
        for line in lines:
            if line.strip():  # Skip empty lines
                indentation = len(line) - len(line.lstrip())
                indentation_levels.add(indentation)
        
        # Count blank lines
        blank_line_count = sum(1 for line in lines if not line.strip())
        
        # Count comment lines
        comment_line_count = sum(1 for line in lines if line.strip().startswith('#') or line.strip().startswith('//'))
        
        # Count function/method definitions
        function_pattern = r'(def|function|\w+\s*\([^)]*\)\s*{)'
        function_count = len(re.findall(function_pattern, code))
        
        # Count class definitions
        class_pattern = r'(class\s+\w+|interface\s+\w+)'
        class_count = len(re.findall(class_pattern, code))
        
        # Count control flow statements
        control_flow_pattern = r'(if|else|for|while|switch|case|try|catch|except|finally)'
        control_flow_count = len(re.findall(control_flow_pattern, code))
        
        # Extract structure features
        structure_features = {
            "line_count": line_count,
            "indentation_level_count": len(indentation_levels),
            "blank_line_count": blank_line_count,
            "comment_line_count": comment_line_count,
            "function_count": function_count,
            "class_count": class_count,
            "control_flow_count": control_flow_count,
            "code_to_comment_ratio": (line_count - comment_line_count) / max(1, comment_line_count)
        }
        
        return structure_features
    
    def _extract_diff_features(self, diff: List[str]) -> Dict[str, Any]:
        """
        Extract features from diff.
        
        Args:
            diff: Diff between before and after code
            
        Returns:
            Dictionary of diff features
        """
        # Count added, removed, and changed lines
        added_lines = [line for line in diff if line.startswith('+ ')]
        removed_lines = [line for line in diff if line.startswith('- ')]
        changed_lines = [line for line in diff if line.startswith('? ')]
        
        # Count added, removed, and changed tokens
        added_tokens = []
        removed_tokens = []
        
        for line in added_lines:
            tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', line[2:])
            added_tokens.extend(tokens)
        
        for line in removed_lines:
            tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', line[2:])
            removed_tokens.extend(tokens)
        
        # Find common tokens in added and removed lines
        common_tokens = set(added_tokens) & set(removed_tokens)
        
        # Extract diff features
        diff_features = {
            "added_line_count": len(added_lines),
            "removed_line_count": len(removed_lines),
            "changed_line_count": len(changed_lines),
            "added_token_count": len(added_tokens),
            "removed_token_count": len(removed_tokens),
            "common_token_count": len(common_tokens),
            "diff_size": len(diff),
            "change_ratio": (len(added_lines) + len(removed_lines)) / max(1, len(diff))
        }
        
        return diff_features
    
    def _extract_bug_features(self, bug_type: str, code: str) -> Dict[str, Any]:
        """
        Extract bug-specific features.
        
        Args:
            bug_type: Type of bug
            code: Code to extract features from
            
        Returns:
            Dictionary of bug features
        """
        # Initialize bug features
        bug_features = {
            "bug_type": bug_type,
            "indicators": {}
        }
        
        # Extract bug-specific indicators
        if bug_type == "null_pointer":
            # Null pointer bug indicators
            bug_features["indicators"] = {
                "null_check_count": len(re.findall(r'(if|while)\s*\(\s*\w+\s*[!=]=\s*(null|None|nil|nullptr)\s*\)', code)),
                "null_assignment_count": len(re.findall(r'\w+\s*=\s*(null|None|nil|nullptr)', code)),
                "null_return_count": len(re.findall(r'return\s+(null|None|nil|nullptr)', code)),
                "null_parameter_count": len(re.findall(r'\(\s*(null|None|nil|nullptr)\s*\)', code))
            }
        elif bug_type == "resource_leak":
            # Resource leak bug indicators
            bug_features["indicators"] = {
                "resource_acquisition_count": len(re.findall(r'(open|new|malloc|create|acquire)', code)),
                "resource_release_count": len(re.findall(r'(close|delete|free|release|dispose)', code)),
                "try_finally_count": len(re.findall(r'try.*finally', code, re.DOTALL)),
                "with_count": len(re.findall(r'with\s+\w+', code))
            }
        elif bug_type == "sql_injection":
            # SQL injection bug indicators
            bug_features["indicators"] = {
                "sql_query_count": len(re.findall(r'(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP)', code)),
                "string_concat_count": len(re.findall(r'(\+|\|\||\{\}\.format|\%s)', code)),
                "parameterized_query_count": len(re.findall(r'(\?|:%\w+|%\(\w+\))', code)),
                "user_input_count": len(re.findall(r'(input|request|param|arg)', code))
            }
        elif bug_type == "exception_swallowing":
            # Exception swallowing bug indicators
            bug_features["indicators"] = {
                "try_catch_count": len(re.findall(r'try.*catch|try.*except', code, re.DOTALL)),
                "empty_catch_count": len(re.findall(r'(catch|except).*\{\s*\}', code, re.DOTALL)),
                "pass_count": len(re.findall(r'except.*:\s*pass', code)),
                "print_in_catch_count": len(re.findall(r'(catch|except).*\{\s*(System\.out\.println|console\.log|print)', code, re.DOTALL))
            }
        elif bug_type == "hardcoded_credentials":
            # Hardcoded credentials bug indicators
            bug_features["indicators"] = {
                "password_count": len(re.findall(r'(password|passwd|pwd)', code, re.IGNORECASE)),
                "api_key_count": len(re.findall(r'(api_key|apikey|api-key)', code, re.IGNORECASE)),
                "token_count": len(re.findall(r'(token|secret)', code, re.IGNORECASE)),
                "credential_assignment_count": len(re.findall(r'(password|passwd|pwd|api_key|apikey|api-key|token|secret)\s*=\s*["\']', code, re.IGNORECASE))
            }
        
        return bug_features
    
    def _extract_patterns(self, before_code: str, after_code: str, diff: List[str]) -> Tuple[str, str]:
        """
        Extract before and after patterns from code.
        
        Args:
            before_code: Code before the fix
            after_code: Code after the fix
            diff: Diff between before and after code
            
        Returns:
            Tuple of (before_pattern, after_pattern)
        """
        # Find the changed lines in the diff
        changed_line_indices = []
        for i, line in enumerate(diff):
            if line.startswith('+ ') or line.startswith('- ') or line.startswith('? '):
                changed_line_indices.append(i)
        
        # Extract context around changed lines
        context_size = 2  # Number of lines of context before and after
        context_start = max(0, min(changed_line_indices) - context_size)
        context_end = min(len(diff), max(changed_line_indices) + context_size + 1)
        
        # Extract before and after patterns
        before_pattern = []
        after_pattern = []
        
        for i in range(context_start, context_end):
            line = diff[i]
            if line.startswith('  '):  # Unchanged line
                before_pattern.append(line[2:])
                after_pattern.append(line[2:])
            elif line.startswith('- '):  # Removed line
                before_pattern.append(line[2:])
            elif line.startswith('+ '):  # Added line
                after_pattern.append(line[2:])
            # Ignore lines starting with '? '
        
        # Join patterns
        before_pattern_str = '\n'.join(before_pattern)
        after_pattern_str = '\n'.join(after_pattern)
        
        # Generalize patterns
        before_pattern_str = self._generalize_pattern(before_pattern_str)
        after_pattern_str = self._generalize_pattern(after_pattern_str)
        
        return before_pattern_str, after_pattern_str
    
    def _generalize_pattern(self, pattern: str) -> str:
        """
        Generalize a pattern by replacing specific identifiers with placeholders.
        
        Args:
            pattern: Pattern to generalize
            
        Returns:
            Generalized pattern
        """
        # Replace variable names with placeholders
        generalized = re.sub(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', r'$VAR', pattern)
        
        # Replace string literals with placeholders
        generalized = re.sub(r'"[^"]*"', r'$STR', generalized)
        generalized = re.sub(r"'[^']*'", r'$STR', generalized)
        
        # Replace numeric literals with placeholders
        generalized = re.sub(r'\b\d+\b', r'$NUM', generalized)
        
        return generalized
    
    def _update_pattern_clusters(self):
        """Update pattern clusters based on similarity."""
        if not HAVE_ML_DEPS or len(self.patterns) < 2:
            # Skip clustering if ML dependencies are not available or not enough patterns
            return
        
        try:
            # Extract pattern texts for vectorization
            pattern_texts = []
            pattern_ids = []
            
            for pattern_id, pattern in self.patterns.items():
                pattern_text = f"{pattern.before_pattern} {pattern.after_pattern}"
                pattern_texts.append(pattern_text)
                pattern_ids.append(pattern_id)
            
            # Vectorize patterns
            X = self.vectorizer.fit_transform(pattern_texts)
            
            # Cluster patterns using DBSCAN
            clustering = DBSCAN(eps=0.3, min_samples=2).fit(X.toarray())
            
            # Update pattern clusters
            self.pattern_clusters = {}
            for i, cluster_id in enumerate(clustering.labels_):
                if cluster_id == -1:
                    # Noise points (no cluster)
                    continue
                
                cluster_key = f"cluster_{cluster_id}"
                if cluster_key not in self.pattern_clusters:
                    self.pattern_clusters[cluster_key] = []
                
                self.pattern_clusters[cluster_key].append(pattern_ids[i])
            
            logger.info(f"Updated pattern clusters: {len(self.pattern_clusters)} clusters")
        except Exception as e:
            logger.error(f"Error updating pattern clusters: {e}")
