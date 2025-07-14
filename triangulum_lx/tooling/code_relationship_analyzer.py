import ast
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class CodeRelationshipAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.relationships = {
            'files': {},
            'imports': {},
            'classes': {},
            'functions': {}
        }
        self.current_file = None

    def analyze_directory(self, directory_path: str):
        directory = Path(directory_path)
        for file_path in directory.rglob('*.py'):
            self.analyze_file(file_path)

    def analyze_file(self, file_path: Path):
        self.current_file = str(file_path)
        self.relationships['files'][self.current_file] = {
            'imports': [],
            'classes': [],
            'functions': []
        }
        with open(file_path, 'r') as f:
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
        self.generic_visit(node)

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

    def save_relationships(self, output_path: str):
        with open(output_path, 'w') as f:
            json.dump(self.relationships, f, indent=2)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    analyzer = CodeRelationshipAnalyzer()
    analyzer.analyze_directory('.')
    analyzer.save_relationships('relationships.json')
    logger.info("Saved relationships to relationships.json")
