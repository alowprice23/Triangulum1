"""
Dependency Graph Demo

This demo showcases the capabilities of the Dependency Graph and Graph Models
components for analyzing code dependencies in a project. It demonstrates:

1. Building a dependency graph from a codebase
2. Analyzing dependencies between files
3. Visualizing the dependency graph
4. Finding cycles in the dependency structure
5. Prioritizing files based on their importance in the dependency network
6. Calculating impact scores for changes
"""

import os
import sys
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import networkx as nx

# Add the parent directory to the path so we can import triangulum_lx
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.tooling.dependency_graph import (
    DependencyGraphBuilder, DependencyAnalyzer, ParserRegistry,
    PythonDependencyParser, JavaScriptDependencyParser, TypeScriptDependencyParser
)
from triangulum_lx.tooling.graph_models import (
    DependencyGraph, FileNode, DependencyMetadata, 
    DependencyType, LanguageType, DependencyEdge
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_graph() -> DependencyGraph:
    """Create a sample dependency graph for demonstration."""
    graph = DependencyGraph()
    
    # Add nodes
    files = [
        "app.py",
        "models/user.py",
        "models/product.py",
        "controllers/user_controller.py",
        "controllers/product_controller.py",
        "utils/helpers.py",
        "utils/validators.py",
        "config.py",
        "database.py",
        "tests/test_user.py",
        "tests/test_product.py"
    ]
    
    for file_path in files:
        language = LanguageType.PYTHON
        node = FileNode(path=file_path, language=language)
        graph.add_node(node)
    
    # Add edges (dependencies)
    dependencies = [
        # app.py depends on controllers and config
        ("app.py", "controllers/user_controller.py", DependencyType.IMPORT),
        ("app.py", "controllers/product_controller.py", DependencyType.IMPORT),
        ("app.py", "config.py", DependencyType.IMPORT),
        
        # Controllers depend on models and utils
        ("controllers/user_controller.py", "models/user.py", DependencyType.IMPORT),
        ("controllers/user_controller.py", "utils/helpers.py", DependencyType.IMPORT),
        ("controllers/user_controller.py", "utils/validators.py", DependencyType.IMPORT),
        ("controllers/product_controller.py", "models/product.py", DependencyType.IMPORT),
        ("controllers/product_controller.py", "utils/helpers.py", DependencyType.IMPORT),
        
        # Models depend on database
        ("models/user.py", "database.py", DependencyType.IMPORT),
        ("models/product.py", "database.py", DependencyType.IMPORT),
        
        # Utils dependencies
        ("utils/validators.py", "utils/helpers.py", DependencyType.IMPORT),
        
        # Tests depend on models
        ("tests/test_user.py", "models/user.py", DependencyType.IMPORT),
        ("tests/test_product.py", "models/product.py", DependencyType.IMPORT),
        
        # Create a cycle for demonstration
        ("utils/helpers.py", "config.py", DependencyType.IMPORT),
        ("config.py", "database.py", DependencyType.IMPORT),
        ("database.py", "utils/helpers.py", DependencyType.IMPORT),
    ]
    
    for source, target, dep_type in dependencies:
        metadata = DependencyMetadata(
            dependency_type=dep_type,
            source_lines=[1],  # Dummy line number
            symbols=["*"],     # Dummy symbol
            verified=True,
            confidence=1.0
        )
        graph.add_edge(source, target, metadata)
    
    return graph

def visualize_graph(graph: DependencyGraph, output_path: str = "dependency_graph.png"):
    """Visualize the dependency graph using NetworkX and matplotlib."""
    analyzer = DependencyAnalyzer(graph)
    analyzer.visualize_graph(output_path)
    logger.info(f"Graph visualization saved to {output_path}")

def analyze_dependencies(graph: DependencyGraph):
    """Analyze dependencies in the graph."""
    analyzer = DependencyAnalyzer(graph)
    
    # Find cycles
    cycles = analyzer.find_cycles()
    logger.info(f"Found {len(cycles)} cycles in the dependency graph:")
    for i, cycle in enumerate(cycles):
        logger.info(f"  Cycle {i+1}: {' -> '.join(cycle)} -> {cycle[0]}")
    
    # Calculate centrality metrics
    centrality = analyzer.calculate_centrality()
    logger.info("\nCentrality metrics for top 5 files:")
    
    # Sort files by PageRank
    top_files = sorted(
        centrality.items(), 
        key=lambda x: x[1]['pagerank'], 
        reverse=True
    )[:5]
    
    for file_path, metrics in top_files:
        logger.info(f"  {file_path}:")
        logger.info(f"    PageRank: {metrics['pagerank']:.4f}")
        logger.info(f"    In-degree: {metrics['in_degree']:.4f}")
        logger.info(f"    Out-degree: {metrics['out_degree']:.4f}")
        logger.info(f"    Betweenness: {metrics['betweenness']:.4f}")
    
    # Calculate impact scores
    logger.info("\nImpact scores for all files:")
    impact_scores = {file_path: analyzer.get_impact_score(file_path) for file_path in graph}
    
    # Sort files by impact score
    sorted_files = sorted(impact_scores.items(), key=lambda x: x[1], reverse=True)
    
    for file_path, score in sorted_files:
        logger.info(f"  {file_path}: {score:.4f}")
        
        # Show dependencies and dependents
        dependencies = list(graph.successors(file_path))
        dependents = list(graph.get_incoming_edges(file_path).keys())
        
        logger.info(f"    Dependencies ({len(dependencies)}): {', '.join(dependencies[:3])}{'...' if len(dependencies) > 3 else ''}")
        logger.info(f"    Dependents ({len(dependents)}): {', '.join(dependents[:3])}{'...' if len(dependents) > 3 else ''}")

def demonstrate_incremental_analysis():
    """Demonstrate incremental analysis with the dependency graph builder."""
    logger.info("\nDemonstrating incremental analysis:")
    
    # Create a temporary directory structure
    temp_dir = "temp_project"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Create some Python files
    files = {
        "main.py": """
import module_a
import module_b

def main():
    module_a.function_a()
    module_b.function_b()

if __name__ == "__main__":
    main()
""",
        "module_a.py": """
import utils

def function_a():
    return utils.helper()
""",
        "module_b.py": """
import utils

def function_b():
    return utils.helper()
""",
        "utils.py": """
def helper():
    return "Helper function"
"""
    }
    
    # Write files
    for file_name, content in files.items():
        with open(os.path.join(temp_dir, file_name), 'w') as f:
            f.write(content)
    
    # Build initial graph
    builder = DependencyGraphBuilder(cache_dir=temp_dir)
    logger.info("Building initial graph...")
    graph = builder.build_graph(temp_dir)
    
    logger.info(f"Initial graph has {len(graph)} nodes and {sum(1 for _ in graph.edges())} edges")
    
    # Modify a file
    logger.info("Modifying module_a.py to add a new dependency...")
    with open(os.path.join(temp_dir, "module_a.py"), 'w') as f:
        f.write("""
import utils
import module_b  # New dependency

def function_a():
    return utils.helper() + module_b.function_b()
""")
    
    # Perform incremental analysis
    logger.info("Performing incremental analysis...")
    updated_graph = builder.build_graph(temp_dir, incremental=True, previous_graph=graph)
    
    logger.info(f"Updated graph has {len(updated_graph)} nodes and {sum(1 for _ in updated_graph.edges())} edges")
    
    # Check if the new dependency was detected
    if updated_graph.get_edge("module_a.py", "module_b.py"):
        logger.info("✓ New dependency from module_a.py to module_b.py was detected")
    else:
        logger.info("✗ New dependency was not detected")
    
    # Clean up
    import shutil
    shutil.rmtree(temp_dir)

def main():
    """Run the dependency graph demo."""
    logger.info("Starting Dependency Graph Demo")
    
    # Create a sample graph
    graph = create_sample_graph()
    logger.info(f"Created sample graph with {len(graph)} nodes and {sum(1 for _ in graph.edges())} edges")
    
    # Visualize the graph
    visualize_graph(graph)
    
    # Analyze dependencies
    analyze_dependencies(graph)
    
    # Demonstrate incremental analysis
    demonstrate_incremental_analysis()
    
    logger.info("Dependency Graph Demo completed")

if __name__ == "__main__":
    main()
