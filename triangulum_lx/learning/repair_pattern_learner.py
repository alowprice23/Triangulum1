#!/usr/bin/env python3
"""
Repair Pattern Learner

This module implements a learning system that analyzes successful repairs,
extracts patterns, and improves future fix suggestions based on learned patterns.
"""

import os
import sys
import time
import json
import logging
import datetime
import re
import hashlib
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
from collections import Counter, defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RepairPattern:
    """
    Represents a repair pattern extracted from successful fixes.
    """
    
    def __init__(self, 
                pattern_id: str = None,
                name: str = None, 
                description: str = None,
                examples: List[Dict] = None,
                conditions: List[Dict] = None,
                fix_template: str = None,
                success_rate: float = None,
                language: str = None,
                tags: List[str] = None,
                metadata: Dict = None):
        """
        Initialize a repair pattern.
        
        Args:
            pattern_id: Unique identifier for the pattern
            name: Name of the repair pattern
            description: Human-readable description of the pattern
            examples: List of example fixes that illustrate the pattern
            conditions: List of conditions that indicate when the pattern applies
            fix_template: Template for generating fixes based on the pattern
            success_rate: Success rate of the pattern (0.0 to 1.0)
            language: Programming language the pattern applies to
            tags: List of tags for categorizing the pattern
            metadata: Additional information about the pattern
        """
        self.pattern_id = pattern_id or f"pattern_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        self.name = name or "Unnamed Pattern"
        self.description = description or ""
        self.examples = examples or []
        self.conditions = conditions or []
        self.fix_template = fix_template or ""
        self.success_rate = success_rate or 0.0
        self.language = language or "python"
        self.tags = tags or []
        self.metadata = metadata or {}
        self.created_at = datetime.datetime.now().isoformat()
        self.updated_at = self.created_at
        self.usage_count = 0
        self.success_count = 0
    
    def to_dict(self) -> Dict:
        """Convert pattern to dictionary for serialization."""
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "description": self.description,
            "examples": self.examples,
            "conditions": self.conditions,
            "fix_template": self.fix_template,
            "success_rate": self.success_rate,
            "language": self.language,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "usage_count": self.usage_count,
            "success_count": self.success_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RepairPattern':
        """Create pattern from dictionary."""
        pattern = cls(
            pattern_id=data.get("pattern_id"),
            name=data.get("name"),
            description=data.get("description"),
            examples=data.get("examples"),
            conditions=data.get("conditions"),
            fix_template=data.get("fix_template"),
            success_rate=data.get("success_rate"),
            language=data.get("language"),
            tags=data.get("tags"),
            metadata=data.get("metadata")
        )
        pattern.created_at = data.get("created_at", pattern.created_at)
        pattern.updated_at = data.get("updated_at", pattern.updated_at)
        pattern.usage_count = data.get("usage_count", 0)
        pattern.success_count = data.get("success_count", 0)
        return pattern
    
    def update_stats(self, success: bool):
        """
        Update pattern statistics based on usage result.
        
        Args:
            success: Whether the pattern was successfully applied
        """
        self.usage_count += 1
        if success:
            self.success_count += 1
        
        self.success_rate = self.success_count / self.usage_count if self.usage_count > 0 else 0.0
        self.updated_at = datetime.datetime.now().isoformat()

class RepairPatternLearner:
    """
    Learns repair patterns from successful fixes and applies them to improve future repairs.
    """
    
    def __init__(self, 
                patterns_dir: str = "./repair_patterns",
                verification_dir: Optional[str] = None,
                enable_auto_learning: bool = True,
                min_examples_for_pattern: int = 3,
                confidence_threshold: float = 0.7,
                learning_rate: float = 0.1):
        """
        Initialize the repair pattern learner.
        
        Args:
            patterns_dir: Directory to store learned patterns
            verification_dir: Directory containing verification results
            enable_auto_learning: Whether to automatically learn patterns
            min_examples_for_pattern: Minimum examples needed to create a pattern
            confidence_threshold: Minimum confidence needed to suggest a pattern
            learning_rate: Rate at which to update pattern statistics
        """
        self.patterns_dir = patterns_dir
        self.verification_dir = verification_dir
        self.enable_auto_learning = enable_auto_learning
        self.min_examples_for_pattern = min_examples_for_pattern
        self.confidence_threshold = confidence_threshold
        self.learning_rate = learning_rate
        
        # Create patterns directory
        os.makedirs(patterns_dir, exist_ok=True)
        
        # Load existing patterns
        self.patterns = {}
        self._load_patterns()
        
        logger.info(f"RepairPatternLearner initialized with {len(self.patterns)} patterns")
    
    def _load_patterns(self):
        """Load patterns from the patterns directory."""
        pattern_files = [f for f in os.listdir(self.patterns_dir) if f.endswith('.json')]
        
        for file_name in pattern_files:
            try:
                file_path = os.path.join(self.patterns_dir, file_name)
                with open(file_path, 'r', encoding='utf-8') as f:
                    pattern_data = json.load(f)
                
                pattern = RepairPattern.from_dict(pattern_data)
                self.patterns[pattern.pattern_id] = pattern
                logger.debug(f"Loaded pattern {pattern.pattern_id}: {pattern.name}")
            
            except Exception as e:
                logger.warning(f"Error loading pattern from {file_name}: {e}")
        
        logger.info(f"Loaded {len(self.patterns)} repair patterns")
    
    def _save_pattern(self, pattern: RepairPattern):
        """
        Save a pattern to disk.
        
        Args:
            pattern: The pattern to save
        """
        file_path = os.path.join(self.patterns_dir, f"{pattern.pattern_id}.json")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(pattern.to_dict(), f, indent=2)
        
        logger.debug(f"Saved pattern {pattern.pattern_id} to {file_path}")
    
    def learn_from_verification(self, verification_results: Dict) -> List[RepairPattern]:
        """
        Learn patterns from verification results.
        
        Args:
            verification_results: Results from fix verification
        
        Returns:
            List of newly learned patterns
        """
        if not self.enable_auto_learning:
            logger.info("Auto learning disabled, skipping pattern learning")
            return []
        
        logger.info("Learning patterns from verification results")
        
        # Extract successful fixes
        successful_fixes = []
        for fix_result in verification_results.get("fix_results", []):
            if fix_result.get("verified", False):
                fix_info = fix_result.get("fix_info", {}).copy()
                
                # Add verification result to fix info, but avoid circular reference
                # Create a shallow copy of the fix_result to avoid circular reference
                verification_data = fix_result.copy()
                if 'fix_info' in verification_data:
                    del verification_data['fix_info'] # remove circular part
                
                fix_info["verification_result"] = verification_data
                
                successful_fixes.append(fix_info)
        
        logger.info(f"Found {len(successful_fixes)} successful fixes")
        
        # Group fixes by description
        fix_groups = defaultdict(list)
        for fix in successful_fixes:
            description = fix.get("description", "").lower()
            if description:
                # Extract the general pattern from the description
                # e.g., "Added error handling for..." -> "Added error handling"
                pattern_key = self._extract_pattern_key(description)
                if pattern_key:
                    fix_groups[pattern_key].append(fix)
        
        # Identify potential patterns
        new_patterns = []
        for pattern_key, fixes in fix_groups.items():
            if len(fixes) >= self.min_examples_for_pattern:
                logger.info(f"Found potential pattern '{pattern_key}' with {len(fixes)} examples")
                
                # Check if pattern already exists
                existing_pattern = self._find_existing_pattern(pattern_key)
                
                if existing_pattern:
                    # Update existing pattern with new examples
                    logger.info(f"Updating existing pattern {existing_pattern.pattern_id}: {existing_pattern.name}")
                    self._update_pattern(existing_pattern, fixes)
                else:
                    # Create new pattern
                    logger.info(f"Creating new pattern for '{pattern_key}'")
                    new_pattern = self._create_pattern(pattern_key, fixes)
                    self.patterns[new_pattern.pattern_id] = new_pattern
                    new_patterns.append(new_pattern)
                    self._save_pattern(new_pattern)
        
        return new_patterns
    
    def _extract_pattern_key(self, description: str) -> str:
        """
        Extract a pattern key from a fix description.
        
        Args:
            description: The fix description
        
        Returns:
            Pattern key or empty string if no pattern found
        """
        # Common repair pattern prefixes
        patterns = [
            r"^added? error handling",
            r"^fixed null pointer",
            r"^added? input validation",
            r"^fixed memory leak",
            r"^optimized.*algorithm",
            r"^fixed race condition",
            r"^added? bounds check",
            r"^fixed infinite loop",
            r"^secured.*credentials",
            r"^fixed off-by-one",
            r"^added? defensive cod(e|ing)",
            r"^fixed thread safety",
            r"^added? parameter validation",
            r"^fixed resource leak",
            r"^improved performance",
            r"^added? retry logic",
            r"^fixed concurrency issue",
            r"^added? logging",
            r"^fixed deadlock",
            r"^implemented timeout"
        ]
        
        # Try to match description to known patterns
        for pattern in patterns:
            match = re.search(pattern, description.lower())
            if match:
                return match.group(0)
        
        # If no specific pattern found, use a general categorization
        if "error" in description.lower() or "exception" in description.lower():
            return "error handling"
        elif "validation" in description.lower() or "check" in description.lower():
            return "input validation"
        elif "performance" in description.lower() or "optimiz" in description.lower():
            return "performance optimization"
        elif "security" in description.lower() or "vulnerab" in description.lower():
            return "security fix"
        
        # Default to empty string if no pattern detected
        return ""
    
    def _find_existing_pattern(self, pattern_key: str) -> Optional[RepairPattern]:
        """
        Find an existing pattern matching the pattern key.
        
        Args:
            pattern_key: The pattern key to match
        
        Returns:
            Matching pattern or None
        """
        for pattern in self.patterns.values():
            if pattern_key.lower() in pattern.name.lower() or pattern_key.lower() in pattern.description.lower():
                return pattern
        
        return None
    
    def _update_pattern(self, pattern: RepairPattern, new_fixes: List[Dict]):
        """
        Update an existing pattern with new fix examples.
        
        Args:
            pattern: The pattern to update
            new_fixes: New fix examples
        """
        # Add new examples that aren't already in the pattern
        existing_file_lines = set((ex.get("file", ""), ex.get("line")) for ex in pattern.examples)
        
        for fix in new_fixes:
            file_line = (fix.get("file", ""), fix.get("line"))
            if file_line not in existing_file_lines:
                pattern.examples.append(fix)
                existing_file_lines.add(file_line)
        
        # Update pattern metadata
        pattern.updated_at = datetime.datetime.now().isoformat()
        pattern.success_rate = 1.0  # All examples are from successful fixes
        
        # Update conditions based on new examples
        self._update_pattern_conditions(pattern)
        
        # Save updated pattern
        self._save_pattern(pattern)
    
    def _create_pattern(self, pattern_key: str, fixes: List[Dict]) -> RepairPattern:
        """
        Create a new pattern from fix examples.
        
        Args:
            pattern_key: The pattern key/category
            fixes: List of fix examples
        
        Returns:
            Newly created pattern
        """
        # Determine pattern name and description
        name = self._generate_pattern_name(pattern_key)
        description = self._generate_pattern_description(pattern_key, fixes)
        
        # Determine language
        languages = Counter(self._detect_language(fix.get("file", "")) for fix in fixes)
        language = languages.most_common(1)[0][0] if languages else "python"
        
        # Create pattern
        pattern = RepairPattern(
            name=name,
            description=description,
            examples=fixes,
            language=language,
            tags=[pattern_key],
            success_rate=1.0  # All examples are from successful fixes
        )
        
        # Generate conditions and fix template
        self._update_pattern_conditions(pattern)
        self._generate_fix_template(pattern)
        
        return pattern
    
    def _generate_pattern_name(self, pattern_key: str) -> str:
        """
        Generate a name for a pattern.
        
        Args:
            pattern_key: The pattern key/category
        
        Returns:
            Pattern name
        """
        # Capitalize pattern key and make it more readable
        name = pattern_key.strip().capitalize()
        
        # Add prefix based on pattern type
        if "error handling" in pattern_key.lower():
            name = f"Error Handling: {name}"
        elif "validation" in pattern_key.lower():
            name = f"Input Validation: {name}"
        elif "performance" in pattern_key.lower():
            name = f"Performance: {name}"
        elif "security" in pattern_key.lower():
            name = f"Security: {name}"
        else:
            name = f"Pattern: {name}"
        
        return name
    
    def _generate_pattern_description(self, pattern_key: str, fixes: List[Dict]) -> str:
        """
        Generate a description for a pattern.
        
        Args:
            pattern_key: The pattern key/category
            fixes: List of fix examples
        
        Returns:
            Pattern description
        """
        # Start with a basic description
        description = f"This pattern represents fixes related to {pattern_key}."
        
        # Add more context based on the fixes
        fix_types = Counter(fix.get("description", "").lower() for fix in fixes)
        common_descriptions = [desc for desc, count in fix_types.most_common(3)]
        
        if common_descriptions:
            description += f" Common fix descriptions include: {', '.join(common_descriptions)}."
        
        # Add information about affected files
        file_types = Counter(os.path.splitext(fix.get("file", ""))[1] for fix in fixes if fix.get("file"))
        common_file_types = [ext for ext, count in file_types.most_common(3) if ext]
        
        if common_file_types:
            description += f" Most commonly applied to {', '.join(common_file_types)} files."
        
        return description
    
    def _detect_language(self, file_path: str) -> str:
        """
        Detect programming language from file path.
        
        Args:
            file_path: Path to the file
        
        Returns:
            Detected language
        """
        if not file_path:
            return "unknown"
        
        ext = os.path.splitext(file_path)[1].lower()
        
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".cs": "csharp",
            ".go": "go",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".rs": "rust",
            ".sh": "bash",
            ".html": "html",
            ".css": "css",
            ".sql": "sql"
        }
        
        return language_map.get(ext, "unknown")
    
    def _update_pattern_conditions(self, pattern: RepairPattern):
        """
        Update pattern conditions based on examples.
        
        Args:
            pattern: The pattern to update
        """
        # Clear existing conditions
        pattern.conditions = []
        
        # No examples, nothing to do
        if not pattern.examples:
            return
        
        # Analyze examples to derive conditions
        file_exts = Counter(os.path.splitext(ex.get("file", ""))[1] for ex in pattern.examples if ex.get("file"))
        common_exts = [ext for ext, count in file_exts.most_common() if ext and count > 1]
        
        if common_exts:
            pattern.conditions.append({
                "type": "file_extension",
                "extensions": common_exts,
                "description": f"File has one of these extensions: {', '.join(common_exts)}"
            })
        
        # Extract common terms from descriptions
        descriptions = [ex.get("description", "").lower() for ex in pattern.examples if ex.get("description")]
        words = Counter()
        
        for desc in descriptions:
            # Split description into words, removing common stop words
            stop_words = {"the", "a", "an", "to", "for", "in", "of", "and", "or", "at", "by", "with"}
            desc_words = [w for w in re.findall(r'\b\w+\b', desc) if w not in stop_words]
            words.update(desc_words)
        
        # Find common terms
        common_terms = [word for word, count in words.most_common(5) if count > 1]
        
        if common_terms:
            pattern.conditions.append({
                "type": "fix_description",
                "terms": common_terms,
                "description": f"Fix description contains terms like: {', '.join(common_terms)}"
            })
        
        # Look for common severity levels
        severities = Counter(ex.get("severity", "").lower() for ex in pattern.examples if ex.get("severity"))
        common_severity = severities.most_common(1)[0][0] if severities else None
        
        if common_severity:
            pattern.conditions.append({
                "type": "severity",
                "severity": common_severity,
                "description": f"Issue severity is {common_severity}"
            })
    
    def _generate_fix_template(self, pattern: RepairPattern):
        """
        Generate a fix template based on examples.
        
        Args:
            pattern: The pattern to update
        """
        if not pattern.examples:
            return
        
        # For now, use a placeholder template
        if "error handling" in pattern.name.lower():
            pattern.fix_template = """
# Error handling template
try:
    # Original code
    {{original_code}}
except {{exception_type}} as e:
    # Error handling
    logger.error(f"Error: {e}")
    # Fallback behavior
    {{fallback_code}}
"""
        elif "input validation" in pattern.name.lower():
            pattern.fix_template = """
# Input validation template
if {{validation_condition}}:
    # Original code
    {{original_code}}
else:
    # Validation failure handling
    logger.warning(f"Validation failed: {{validation_message}}")
    {{fallback_code}}
"""
        elif "performance" in pattern.name.lower():
            pattern.fix_template = """
# Performance optimization template
# Original code:
# {{original_code}}

# Optimized code:
{{optimized_code}}
"""
        else:
            pattern.fix_template = """
# Generic fix template
# Original code:
# {{original_code}}

# Fixed code:
{{fixed_code}}
"""
    
    def learn_from_fixes(self, fixes: List[Dict], success_flags: List[bool]) -> List[RepairPattern]:
        """
        Learn patterns from a list of fixes and their success flags.
        
        Args:
            fixes: List of fix dictionaries
            success_flags: List of booleans indicating fix success
        
        Returns:
            List of newly learned patterns
        """
        if not self.enable_auto_learning:
            logger.info("Auto learning disabled, skipping pattern learning")
            return []
        
        if len(fixes) != len(success_flags):
            logger.error(f"Length mismatch: {len(fixes)} fixes vs {len(success_flags)} success flags")
            return []
        
        # Extract successful fixes
        successful_fixes = [fix for fix, success in zip(fixes, success_flags) if success]
        
        # Simulate verification results structure
        verification_results = {
            "fix_results": [
                {"verified": True, "fix_info": fix} for fix in successful_fixes
            ]
        }
        
        # Use the existing learning method
        return self.learn_from_verification(verification_results)
    
    def find_matching_patterns(self, fix_info: Dict, context: Optional[str] = None) -> List[Tuple[RepairPattern, float]]:
        """
        Find patterns that match the given fix info.
        
        Args:
            fix_info: Information about the fix
            context: Optional code context around the fix location
        
        Returns:
            List of (pattern, confidence) tuples, sorted by confidence
        """
        matches = []
        
        for pattern in self.patterns.values():
            confidence = self._calculate_match_confidence(pattern, fix_info, context)
            
            if confidence >= self.confidence_threshold:
                matches.append((pattern, confidence))
        
        # Sort by confidence (descending)
        return sorted(matches, key=lambda x: x[1], reverse=True)
    
    def _calculate_match_confidence(self, pattern: RepairPattern, fix_info: Dict, context: Optional[str] = None) -> float:
        """
        Calculate how well a pattern matches a fix.
        
        Args:
            pattern: The pattern to match
            fix_info: Information about the fix
            context: Optional code context
        
        Returns:
            Match confidence (0.0 to 1.0)
        """
        scores = []
        
        # Check if file extension matches
        file_ext_condition = next((c for c in pattern.conditions if c.get("type") == "file_extension"), None)
        if file_ext_condition:
            file_ext = os.path.splitext(fix_info.get("file", ""))[1]
            if file_ext in file_ext_condition.get("extensions", []):
                scores.append(1.0)
            else:
                scores.append(0.0)
        
        # Check if description contains common terms
        desc_condition = next((c for c in pattern.conditions if c.get("type") == "fix_description"), None)
        if desc_condition and fix_info.get("description"):
            desc = fix_info.get("description", "").lower()
            matches = sum(term in desc for term in desc_condition.get("terms", []))
            total_terms = len(desc_condition.get("terms", []))
            
            if total_terms > 0:
                scores.append(matches / total_terms)
            else:
                scores.append(0.0)
        
        # Check if severity matches
        severity_condition = next((c for c in pattern.conditions if c.get("type") == "severity"), None)
        if severity_condition and fix_info.get("severity"):
            if fix_info.get("severity").lower() == severity_condition.get("severity", "").lower():
                scores.append(1.0)
            else:
                scores.append(0.0)
        
        # Additional context-based scoring
        if context and pattern.language != "unknown":
            # Simple language detection in context
            language_indicators = {
                "python": ["def ", "class ", "import ", "self.", "if __name__"],
                "javascript": ["function ", "const ", "let ", "var ", "=>"],
                "java": ["public ", "private ", "class ", "void ", "extends"],
                "cpp": ["#include", "namespace", "template<", "std::", "->"]
            }
            
            indicators = language_indicators.get(pattern.language, [])
            matches = sum(indicator in context for indicator in indicators)
            
            if indicators:
                language_score = matches / len(indicators)
                scores.append(language_score)
        
        # Check pattern success rate
        scores.append(pattern.success_rate)
        
        # Calculate overall confidence
        return sum(scores) / len(scores) if scores else 0.0
    
    def suggest_fix(self, fix_info: Dict, context: Optional[str] = None) -> Optional[Dict]:
        """
        Suggest a fix based on learned patterns.
        
        Args:
            fix_info: Information about the fix
            context: Optional code context
        
        Returns:
            Dictionary with fix suggestion or None
        """
        # Find matching patterns
        matches = self.find_matching_patterns(fix_info, context)
        
        if not matches:
            logger.info("No matching patterns found")
            return None
        
        # Get the best match
        best_pattern, confidence = matches[0]
        
        logger.info(f"Found matching pattern {best_pattern.pattern_id}: {best_pattern.name} with confidence {confidence:.2f}")
        
        # Create suggestion
        suggestion = {
            "pattern_id": best_pattern.pattern_id,
            "pattern_name": best_pattern.name,
            "confidence": confidence,
            "fix_template": best_pattern.fix_template,
            "suggestion": self._apply_template(best_pattern, fix_info, context)
        }
        
        # Update pattern usage stats
        best_pattern.usage_count += 1
        self._save_pattern(best_pattern)
        
        return suggestion
    
    def _apply_template(self, pattern: RepairPattern, fix_info: Dict, context: Optional[str] = None) -> str:
        """
        Apply a pattern template to generate a fix suggestion.
        
        Args:
            pattern: The pattern to apply
            fix_info: Information about the fix
            context: Optional code context
        
        Returns:
            Suggested fix
        """
        # For now, return a simple placeholder
        template = pattern.fix_template
        
        # Extract information from context if available
        if context:
            # Simple code extraction (this would be more sophisticated in a real implementation)
            lines = context.split("\n")
            original_code = "\n".join(lines)
            
            # Replace placeholders in template
            template = template.replace("{{original_code}}", original_code)
            
            # Try to determine exception types for error handling
            if "error handling" in pattern.name.lower():
                # Look for common exception types in context
                exception_types = re.findall(r'except\s+(\w+(?:\s*,\s*\w+)*)', context)
                exception_type = "Exception"  # Default
                
                if exception_types:
                    # Use the most specific exception if found
                    for ex_type in exception_types:
                        if ex_type != "Exception":
                            exception_type = ex_type
                            break
                
                template = template.replace("{{exception_type}}", exception_type)
                template = template.replace("{{fallback_code}}", "return None  # Default fallback")
            
            # For input validation
            if "input validation" in pattern.name.lower():
                template = template.replace("{{validation_condition}}", "input is not None and input != ''")
                template = template.replace("{{validation_message}}", "Invalid input")
                template = template.replace("{{fallback_code}}", "return None  # Default fallback")
        
        return template
    
    def record_fix_result(self, pattern_id: str, success: bool):
        """
        Record the result of applying a pattern.
        
        Args:
            pattern_id: ID of the pattern that was applied
            success: Whether the pattern application was successful
        """
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            pattern.update_stats(success)
            self._save_pattern(pattern)
            
            logger.info(f"Updated pattern {pattern_id} stats: {pattern.success_count}/{pattern.usage_count} successes")
