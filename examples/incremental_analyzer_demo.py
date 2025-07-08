"""
Demo for the incremental analyzer.

This demo shows how to use the incremental analyzer to analyze changes in a codebase
and update the dependency graph incrementally.
"""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path so we can import triangulum_lx
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.tooling.graph_models import DependencyGraph, FileNode, LanguageType
from triangulum_lx.tooling.dependency_graph import DependencyGraphBuilder
from triangulum_lx.tooling.incremental_analyzer import IncrementalAnalyzer

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Run the incremental analyzer demo."""
    # Create a temporary directory for the demo
    demo_dir = Path("demo_files")
    demo_dir.mkdir(exist_ok=True)
    
    try:
        # Create some initial files
        file1_path = demo_dir / "file1.py"
        file2_path = demo_dir / "file2.py"
        
        with open(file1_path, "w") as f:
            f.write("# Initial content for file1.py\n")
            f.write("import os\n")
            f.write("import sys\n")
        
        with open(file2_path, "w") as f:
            f.write("# Initial content for file2.py\n")
            f.write("import file1\n")
        
        # Build the initial dependency graph
        builder = DependencyGraphBuilder()
        graph = DependencyGraph()
        
        # Add nodes to the graph
        node1 = FileNode(path=str(file1_path), language=LanguageType.PYTHON)
        node2 = FileNode(path=str(file2_path), language=LanguageType.PYTHON)
        graph.add_node(node1)
        graph.add_node(node2)
        
        # Create an incremental analyzer
        analyzer = IncrementalAnalyzer(graph)
        
        # Simulate a change to file1.py
        logger.info("Simulating a change to file1.py")
        with open(file1_path, "w") as f:
            f.write("# Modified content for file1.py\n")
            f.write("import os\n")
            f.write("import sys\n")
            f.write("import datetime\n")
        
        # Analyze the changes
        updated_files = {str(file1_path): open(file1_path).read()}
        affected_files = analyzer.analyze_changes(updated_files)
        
        logger.info(f"Affected files: {affected_files}")
        
        # Verify that file1.py was removed from the graph
        logger.info(f"file1.py in graph: {str(file1_path) in graph}")
        
        # Add a new file
        file3_path = demo_dir / "file3.py"
        with open(file3_path, "w") as f:
            f.write("# Content for file3.py\n")
            f.write("import file1\n")
            f.write("import file2\n")
        
        # Analyze the changes
        updated_files = {str(file3_path): open(file3_path).read()}
        affected_files = analyzer.analyze_changes(updated_files)
        
        logger.info(f"Affected files after adding file3.py: {affected_files}")
        
    finally:
        # Clean up
        for file_path in [file1_path, file2_path, file3_path]:
            if file_path.exists():
                file_path.unlink()
        
        if demo_dir.exists():
            demo_dir.rmdir()

if __name__ == "__main__":
    main()
