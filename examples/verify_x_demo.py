#!/usr/bin/env python3
"""
VerifyX Demo

This script demonstrates the VerifyX verification framework with Python plugins.
It creates sample Python files with known issues, verifies them, and displays
the results.
"""

import os
import sys
import logging
import asyncio
import json
from typing import Dict, Any, List

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.verification.core import (
    VerifierPlugin,
    VerifierRegistry,
    CodeArtifact,
    VerificationContext
)
from triangulum_lx.verification.metrics import MetricsAggregator
from triangulum_lx.verification.adaptive import SimpleAIProvider, AdaptiveVerificationPipeline
from triangulum_lx.verification.plugins.python import (
    PythonSyntaxVerifier,
    PythonSecurityVerifier,
    PythonStyleVerifier
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# Sample Python files with issues
SAMPLE_FILES = {
    "syntax_error.py": """
def function_with_syntax_error()
    # Missing colon after function definition
    print("This has a syntax error")
    
    return "Error"
""",
    
    "security_issues.py": """
import os
import tempfile
import pickle

# Hardcoded credentials - security issue
password = "super_secret_password123"
api_key = "1234567890abcdef"

def execute_query(user_input):
    # SQL injection vulnerability
    query = "SELECT * FROM users WHERE name = '%s'" % user_input
    execute(query)
    
    # Shell injection vulnerability
    os.system("echo " + user_input)
    
    # Temporary file vulnerability
    temp_file = tempfile.mktemp()
    
    # Dangerous functions
    eval("print('Hello, world!')")
    exec("x = 1 + 1")
    
    # Pickle security issue
    data = pickle.loads(user_input)
    
    return data

def execute(query):
    # Mock function
    print(f"Executing: {query}")
""",
    
    "style_issues.py": """
import os, sys, json  # Multiple imports on one line

def function_with_style_issues():
    # Line too long
    very_long_variable_name = "This is a very long string that exceeds the maximum line length recommendation of 79 characters in PEP 8"
    
    # Mixed tabs and spaces
	indented_with_tab = "This line uses a tab for indentation"
    
    # Trailing whitespace
    trailing_whitespace = "This line has trailing whitespace"    
    
    # Inconsistent indentation
     inconsistently_indented = "This line has inconsistent indentation"
    
    return very_long_variable_name
"""
}


async def main():
    """Main function to run the demo."""
    logger.info("Starting VerifyX Demo")
    
    # Create sample files in a temporary directory
    temp_dir = os.path.join(os.path.dirname(__file__), "temp_verify_x")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Write sample files
    file_paths = {}
    for filename, content in SAMPLE_FILES.items():
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, "w") as f:
            f.write(content)
        file_paths[filename] = file_path
        logger.info(f"Created sample file: {file_path}")
    
    # Create artifacts from sample files
    artifacts = []
    for filename, file_path in file_paths.items():
        with open(file_path, "r") as f:
            content = f.read()
        
        artifact = CodeArtifact(
            id=f"artifact_{filename}",
            name=filename,
            language="python",
            file_path=file_path,
            content=content
        )
        artifacts.append(artifact)
    
    # Create verifier registry
    registry = VerifierRegistry()
    
    # Register Python verifiers
    registry.register("python", "syntax", PythonSyntaxVerifier)
    registry.register("python", "security", PythonSecurityVerifier)
    registry.register("python", "style", PythonStyleVerifier)
    
    # Create metrics aggregator
    metrics_aggregator = MetricsAggregator()
    
    # Create AI provider
    ai_provider = SimpleAIProvider()
    
    # Create adaptive verification pipeline
    pipeline = AdaptiveVerificationPipeline(registry, ai_provider)
    
    # Verify each artifact
    results = []
    for artifact in artifacts:
        logger.info(f"\n=== Verifying {artifact.name} ===")
        
        # Verify with learning
        report = await pipeline.verify_with_learning(artifact)
        results.append((artifact, report))
        
        # Print summary
        logger.info(f"Verification Status: {report.overall_status.value}")
        logger.info(f"Success: {report.overall_success}")
        logger.info(f"Confidence: {report.overall_confidence:.2f}")
        logger.info(f"Issues: {report.get_issues_count()}")
        logger.info(f"Recommendations: {report.get_recommendations_count()}")
        
        # Print detailed results
        logger.info("\nDetailed Results:")
        for result in report.results:
            logger.info(f"  Plugin: {result.plugin_id}")
            logger.info(f"    Status: {result.status.value}")
            logger.info(f"    Success: {result.success}")
            logger.info(f"    Confidence: {result.confidence:.2f}")
            logger.info(f"    Issues: {len(result.issues)}")
            
            if result.issues:
                logger.info("    Issue Details:")
                for issue in result.issues[:5]:  # Show first 5 issues
                    logger.info(f"      - {issue.get('message', '')}")
                
                if len(result.issues) > 5:
                    logger.info(f"      ... and {len(result.issues) - 5} more issues")
            
            if result.recommendations:
                logger.info("    Recommendations:")
                for rec in result.recommendations:
                    logger.info(f"      - {rec.get('message', '')}")
    
    # Print final metrics
    metrics_aggregator.print_summary()
    
    # Clean up temporary files
    for file_path in file_paths.values():
        os.remove(file_path)
    
    os.rmdir(temp_dir)
    logger.info("Cleaned up temporary files")
    
    logger.info("\nVerifyX Demo completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
