import unittest
import os
from unittest.mock import MagicMock, patch
from triangulum_lx.tooling.dependency_graph import DependencyGraphBuilder, DependencyAnalyzer
from triangulum_lx.tooling.graph_models import DependencyGraph, FileNode, DependencyMetadata, DependencyType, LanguageType

class TestDependencyGraph(unittest.TestCase):
    def setUp(self):
        self.builder = DependencyGraphBuilder()
        self.graph = DependencyGraph()
        self.analyzer = DependencyAnalyzer(self.graph)

    def test_add_node(self):
        node = FileNode(path="file1.py", language=LanguageType.PYTHON)
        self.graph.add_node(node)
        self.assertIn("file1.py", self.graph)

    def test_add_edge(self):
        node1 = FileNode(path="file1.py", language=LanguageType.PYTHON)
        node2 = FileNode(path="file2.py", language=LanguageType.PYTHON)
        self.graph.add_node(node1)
        self.graph.add_node(node2)
        metadata = DependencyMetadata(dependency_type=DependencyType.IMPORT)
        self.graph.add_edge("file1.py", "file2.py", metadata)
        self.assertIn("file2.py", self.graph.successors("file1.py"))

    def test_visualize_graph(self):
        node1 = FileNode(path="file1.py", language=LanguageType.PYTHON)
        node2 = FileNode(path="file2.py", language=LanguageType.PYTHON)
        self.graph.add_node(node1)
        self.graph.add_node(node2)
        metadata = DependencyMetadata(dependency_type=DependencyType.IMPORT)
        self.graph.add_edge("file1.py", "file2.py", metadata)
        
        with patch("matplotlib.pyplot.savefig") as mock_savefig:
            self.analyzer.visualize_graph("test.png")
            mock_savefig.assert_called_once_with("test.png")

if __name__ == "__main__":
    unittest.main()
