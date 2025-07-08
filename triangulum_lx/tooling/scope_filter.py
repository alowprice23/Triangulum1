import re
import fnmatch
from pathlib import Path

class ScopeFilter:
    def __init__(self):
        # Default ignore patterns based on common build and dependency directories
        self.ignore_patterns = [
            'node_modules/**',
            '.git/**',
            'dist/**',
            'build/**',
            '__pycache__/**',
            '*.min.js',
            '*.map'
        ]
        
        self.allowed_extensions = [
            '.js', '.jsx', '.ts', '.tsx',  # JavaScript/TypeScript
            '.py',                         # Python
            '.html', '.css',               # Web
            '.json', '.yaml', '.yml',      # Config
            '.md',                         # Documentation
            '.sh', '.bash',                # Shell scripts
            '.c', '.cpp', '.h',            # C/C++
            '.java',                       # Java
            '.rb',                         # Ruby
            '.go',                         # Go
        ]
        
    def load_from_goal(self, goal):
        """Update ignore patterns from goal configuration."""
        if hasattr(goal, 'ignore_paths') and goal.ignore_paths:
            self.ignore_patterns.extend(goal.ignore_paths)
            
    def allowed(self, file_path):
        """Check if the file is within allowed editing scope."""
        path = Path(file_path)
        
        # First check extension
        if path.suffix not in self.allowed_extensions:
            return False
            
        # Then check ignore patterns
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(str(path), pattern):
                return False
                
        return True
        
    def filter_files(self, file_list):
        """Filter a list of files to only those allowed for editing."""
        return [f for f in file_list if self.allowed(f)]
