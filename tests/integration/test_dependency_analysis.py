"""Integration tests for dependency analysis across multiple files."""

import unittest
import os
import tempfile
import shutil
import networkx as nx
from pathlib import Path

from triangulum_lx.tooling.graph_models import (
    DependencyGraph, FileNode, DependencyMetadata,
    DependencyType, LanguageType
)
from triangulum_lx.tooling.dependency_graph import (
    DependencyGraphBuilder, DependencyAnalyzer
)


class TestIntegratedDependencyAnalysis(unittest.TestCase):
    """Integration test for analyzing dependencies across a sample project."""
    
    def setUp(self):
        """Set up a test project structure."""
        # Create a temporary directory
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a sample project structure
        self.project_dir = os.path.join(self.temp_dir, "sample_project")
        os.makedirs(self.project_dir, exist_ok=True)
        
        # Build the sample project
        self.create_sample_project()
        
        # Create a cache directory for the builder
        self.cache_dir = os.path.join(self.temp_dir, "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Create a builder
        self.builder = DependencyGraphBuilder(cache_dir=self.cache_dir)
    
    def tearDown(self):
        """Clean up the temporary directory."""
        shutil.rmtree(self.temp_dir)
    
    def create_sample_project(self):
        """Create a sample project with multiple modules and dependencies."""
        # Create a Python package structure
        package_dir = os.path.join(self.project_dir, "mypackage")
        os.makedirs(package_dir, exist_ok=True)
        
        # Create subdirectories
        core_dir = os.path.join(package_dir, "core")
        utils_dir = os.path.join(package_dir, "utils")
        services_dir = os.path.join(package_dir, "services")
        
        os.makedirs(core_dir, exist_ok=True)
        os.makedirs(utils_dir, exist_ok=True)
        os.makedirs(services_dir, exist_ok=True)
        
        # Create __init__.py files to make them packages
        for dir_path in [package_dir, core_dir, utils_dir, services_dir]:
            with open(os.path.join(dir_path, "__init__.py"), "w") as f:
                f.write("")
        
        # Create core module files
        with open(os.path.join(core_dir, "base.py"), "w") as f:
            f.write("""
from ..utils import helpers

class BaseClass:
    def __init__(self):
        self.helper = helpers.Helper()
    
    def base_method(self):
        return self.helper.get_data()
""")
        
        with open(os.path.join(core_dir, "app.py"), "w") as f:
            f.write("""
from .base import BaseClass
from ..services import data_service

class Application:
    def __init__(self):
        self.base = BaseClass()
        self.service = data_service.DataService()
    
    def run(self):
        data = self.base.base_method()
        return self.service.process(data)
""")
        
        # Create utils module files
        with open(os.path.join(utils_dir, "helpers.py"), "w") as f:
            f.write("""
import os
import json

class Helper:
    def __init__(self):
        self.data = {"key": "value"}
    
    def get_data(self):
        return self.data
""")
        
        with open(os.path.join(utils_dir, "config.py"), "w") as f:
            f.write("""
import os
from . import helpers

class Config:
    def __init__(self):
        self.helper = helpers.Helper()
        self.settings = {"env": os.environ.get("ENV", "dev")}
    
    def get_settings(self):
        return {**self.settings, **self.helper.get_data()}
""")
        
        # Create services module files
        with open(os.path.join(services_dir, "data_service.py"), "w") as f:
            f.write("""
from ..utils import config

class DataService:
    def __init__(self):
        self.config = config.Config()
    
    def process(self, data):
        settings = self.config.get_settings()
        return {**data, **settings}
""")
        
        # Create a main.py file that imports from the package
        with open(os.path.join(self.project_dir, "main.py"), "w") as f:
            f.write("""
from mypackage.core.app import Application

def main():
    app = Application()
    result = app.run()
    print(result)

if __name__ == "__main__":
    main()
""")
    
    def test_full_project_analysis(self):
        """Test analyzing the entire sample project."""
        # Build the dependency graph
        graph = self.builder.build_graph(self.project_dir)
        
        # Verify that the graph has nodes for all Python files
        self.assertGreaterEqual(len(graph), 8)  # 7 .py files + possibly __init__.py files
        
        # Verify that main.py depends on app.py
        main_path = os.path.normpath("main.py")
        app_path = os.path.normpath(os.path.join("mypackage", "core", "app.py"))
        
        self.assertIn(main_path, graph)
        self.assertIn(app_path, graph)
        
        main_deps = graph.transitive_dependencies(main_path)
        self.assertIn(app_path, main_deps)
        
        # Create an analyzer
        analyzer = DependencyAnalyzer(graph)
        
        # Test finding the most central files
        central_files = analyzer.get_most_central_files(n=3)
        self.assertEqual(len(central_files), 3)
        
        # Test finding cycles
        cycles = analyzer.find_cycles()
        
        # There should be at least one cycle (helpers.py -> config.py -> helpers.py)
        helpers_path = os.path.normpath(os.path.join("mypackage", "utils", "helpers.py"))
        config_path = os.path.normpath(os.path.join("mypackage", "utils", "config.py"))
        
        cycle_found = False
        for cycle in cycles:
            if helpers_path in cycle and config_path in cycle:
                cycle_found = True
                break
        
        self.assertTrue(cycle_found, "Expected cycle between helpers.py and config.py not found")
    
    def test_cached_graph_loading(self):
        """Test that the graph can be cached and loaded from cache."""
        # First, build and cache the graph
        original_graph = self.builder.build_graph(self.project_dir)
        
        # Then try to load it from cache
        loaded_graph = self.builder.load_cached_graph(self.project_dir)
        
        # Verify that the loaded graph is not None
        self.assertIsNotNone(loaded_graph)
        
        # Verify that the loaded graph has the same number of nodes
        self.assertEqual(len(loaded_graph), len(original_graph))
        
        # Verify that the loaded graph has the same nodes
        for node_path in original_graph:
            self.assertIn(node_path, loaded_graph)
    
    def test_incremental_analysis(self):
        """Test incremental analysis by modifying a file."""
        # First, build the initial graph
        initial_graph = self.builder.build_graph(self.project_dir)
        
        # Record the initial centrality metrics
        analyzer = DependencyAnalyzer(initial_graph)
        initial_centrality = analyzer.calculate_centrality()
        
        # Modify a file to add a new dependency
        helpers_path = os.path.join(self.project_dir, "mypackage", "utils", "helpers.py")
        with open(helpers_path, "a") as f:
            f.write("""
# Add a new dependency
from ..services import data_service

def get_service():
    return data_service.DataService()
""")
        
        # Build the graph incrementally
        updated_graph = self.builder.build_graph(
            self.project_dir,
            incremental=True,
            previous_graph=initial_graph
        )
        
        # Verify that the graph was updated
        updated_analyzer = DependencyAnalyzer(updated_graph)
        updated_centrality = updated_analyzer.calculate_centrality()
        
        # The centrality of the data_service.py file should have increased
        data_service_path = os.path.normpath(os.path.join("mypackage", "services", "data_service.py"))
        self.assertIn(data_service_path, updated_centrality)
        self.assertIn(data_service_path, initial_centrality)
        
        # The PageRank score should have changed due to the new dependency
        self.assertNotEqual(
            updated_centrality[data_service_path]["pagerank"],
            initial_centrality[data_service_path]["pagerank"]
        )
    
    def test_prioritization(self):
        """Test file prioritization for analysis or repair."""
        # Build the graph
        graph = self.builder.build_graph(self.project_dir)
        
        # Create an analyzer
        analyzer = DependencyAnalyzer(graph)
        
        # Get all Python files
        python_files = [path for path in graph if path.endswith(".py")]
        
        # Test prioritization by PageRank
        prioritized_pagerank = analyzer.prioritize_files(python_files, prioritization_strategy="pagerank")
        
        # Test prioritization by in-degree
        prioritized_in_degree = analyzer.prioritize_files(python_files, prioritization_strategy="in_degree")
        
        # The prioritization should produce a complete ordering of all files
        self.assertEqual(len(prioritized_pagerank), len(python_files))
        self.assertEqual(len(prioritized_in_degree), len(python_files))
        
        # Verify that the two prioritization strategies may produce different orders
        # (This might not always be true, but is likely for a complex enough graph)
        self.assertNotEqual(prioritized_pagerank, prioritized_in_degree)
        
        # Test prioritization with custom weights
        # Make the main.py file the highest priority
        main_path = os.path.normpath("main.py")
        weights = {main_path: 10.0}
        
        prioritized_custom = analyzer.prioritize_files(
            python_files,
            prioritization_strategy="pagerank",
            additional_weights=weights
        )
        
        # The main.py file should now be first
        self.assertEqual(prioritized_custom[0], main_path)
    
    def test_impact_analysis(self):
        """Test impact analysis for determining which files have the most impact."""
        # Build the graph
        graph = self.builder.build_graph(self.project_dir)
        
        # Create an analyzer
        analyzer = DependencyAnalyzer(graph)
        
        # Get the impact score for each file
        python_files = [path for path in graph if path.endswith(".py")]
        impact_scores = {file_path: analyzer.get_impact_score(file_path) for file_path in python_files}
        
        # Sort files by impact score
        sorted_by_impact = sorted(impact_scores.items(), key=lambda x: x[1], reverse=True)
        
        # The helpers.py file should have a high impact score since many files depend on it
        helpers_path = os.path.normpath(os.path.join("mypackage", "utils", "helpers.py"))
        
        # Find helpers.py in the sorted list
        helpers_rank = next((i for i, (path, _) in enumerate(sorted_by_impact) if path == helpers_path), None)
        
        # It should be among the top 3 most impactful files
        self.assertIsNotNone(helpers_rank)
        self.assertLess(helpers_rank, 3)


if __name__ == "__main__":
    unittest.main()
