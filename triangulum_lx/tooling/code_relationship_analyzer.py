import os
import sys
import json
import logging
import argparse
from pathlib import Path
import networkx as nx
from pyvis.network import Network
import ast

sys.path.append(str(Path(__file__).parent.parent))


logger = logging.getLogger(__name__)

class CodeRelationshipAnalyzer(ast.NodeVisitor):
    def __init__(self, project_path, llm_provider=None, cache_dir=None):
        from triangulum_lx.providers.factory import get_provider
        self.project_path = project_path
        self.llm_provider = llm_provider
        self.cache_dir = cache_dir or '.triangulum_cache'
        self.graph = nx.DiGraph()
        self.file_to_id = {}
        self.id_to_file = {}
        self._file_id_counter = 0
        self.relationships = {
            'files': {},
            'imports': {},
            'classes': {},
            'functions': {}
        }
        self.current_file = None

        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_file_id(self, file_path):
        if file_path not in self.file_to_id:
            self.file_to_id[file_path] = self._file_id_counter
            self.id_to_file[self._file_id_counter] = file_path
            self._file_id_counter += 1
        return self.file_to_id[file_path]

    def analyze(self, max_pass=4):
        # Pass 0: File Discovery
        self._pass_0_discover_files()
        if max_pass == 0: return

        # Pass 1: Syntactic Analysis
        self._pass_1_syntactic_analysis()
        if max_pass == 1: return

        # Pass 2: Semantic Analysis (LLM-based)
        if self.llm_provider:
            self._pass_2_semantic_analysis()
        if max_pass == 2: return

        # Pass 3: Structural Analysis
        self._pass_3_structural_analysis()
        if max_pass == 3: return

        # Pass 4: Historical Analysis
        self._pass_4_historical_analysis()

    def _pass_0_discover_files(self):
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    file_id = self._get_file_id(file_path)
                    self.graph.add_node(file_id, label=os.path.basename(file_path), type='file')

    def _pass_1_syntactic_analysis(self):
        for file_id in list(self.graph.nodes):
            file_path = self.id_to_file[file_id]
            self.analyze_file(Path(file_path))

    def analyze_directory(self, directory_path: str):
        directory = Path(directory_path)
        for file_path in directory.rglob('*.py'):
            self.analyze_file(file_path)

    def analyze_file(self, file_path: Path):
        self.current_file = str(file_path)
        if self.current_file not in self.file_to_id:
            self._get_file_id(self.current_file)

        self.relationships['files'][self.current_file] = {
            'imports': [],
            'classes': [],
            'functions': []
        }
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                tree = ast.parse(f.read(), filename=str(file_path))
                self.visit(tree)
            except SyntaxError as e:
                logger.error(f"Could not parse {file_path}: {e}")

    def visit_Import(self, node):
        for alias in node.names:
            self.relationships['files'][self.current_file]['imports'].append(alias.name)
            if alias.name not in self.relationships['imports']:
                self.relationships['imports'][alias.name] = []
            self.relationships['imports'][alias.name].append(self.current_file)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            full_import = f"{node.module}.{alias.name}"
            self.relationships['files'][self.current_file]['imports'].append(full_import)
            if full_import not in self.relationships['imports']:
                self.relationships['imports'][full_import] = []
            self.relationships['imports'][full_import].append(self.current_file)

            # Add edge to graph
            from_file_id = self.file_to_id[self.current_file]

            # Find the imported file
            imported_file_path = self._find_module_path(node.module)
            if imported_file_path:
                to_file_id = self._get_file_id(str(imported_file_path))
                self.graph.add_edge(from_file_id, to_file_id, type='import')

        self.generic_visit(node)

    def _find_module_path(self, module_name):
        parts = module_name.split('.')
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file == f"{parts[-1]}.py":
                    # Check if the path matches the module structure
                    path_parts = Path(root).relative_to(self.project_path).parts
                    if list(path_parts) == parts[:-1]:
                        return os.path.join(root, file)
        return None

    def visit_ClassDef(self, node):
        self.relationships['files'][self.current_file]['classes'].append(node.name)
        if node.name not in self.relationships['classes']:
            self.relationships['classes'][node.name] = {
                'defined_in': self.current_file,
                'methods': []
            }
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                self.relationships['classes'][node.name]['methods'].append(item.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.relationships['files'][self.current_file]['functions'].append(node.name)
        if node.name not in self.relationships['functions']:
            self.relationships['functions'][node.name] = {
                'defined_in': self.current_file,
                'calls': []
            }
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.relationships['functions'][node.func.id] = self.relationships['functions'].get(node.func.id, {})
            self.relationships['functions'][node.func.id]['calls'] = self.relationships['functions'][node.func.id].get('calls', [])
            self.relationships['functions'][node.func.id]['calls'].append(self.current_file)
        self.generic_visit(node)

    def _pass_2_semantic_analysis(self):
        # Placeholder for LLM-based semantic analysis
        pass

    def _pass_3_structural_analysis(self):
        # Placeholder for structural analysis (e.g., directory structure)
        pass

    def _pass_4_historical_analysis(self):
        # Placeholder for historical analysis (e.g., Git history)
        pass

    def get_related_files(self, file_path):
        file_id = self.file_to_id.get(file_path)
        if file_id is None:
            return {}

        related = {'imports': [], 'imported_by': []}
        for u, v, data in self.graph.edges(data=True):
            if u == file_id and data.get('type') == 'import':
                related['imports'].append(self.id_to_file[v])
            if v == file_id and data.get('type') == 'import':
                related['imported_by'].append(self.id_to_file[u])
        return related

    def export_to_json(self, output_path):
        data = nx.node_link_data(self.graph)
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

    def visualize_graph(self, output_path):
        net = Network(notebook=True, directed=True)
        net.from_nx(self.graph)
        net.save_graph(output_path)
