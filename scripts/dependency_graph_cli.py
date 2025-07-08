import argparse
import logging
from triangulum_lx.tooling.dependency_graph import DependencyGraphBuilder, DependencyAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Dependency Graph Tool")
    parser.add_argument("root_dir", help="Root directory of the codebase to analyze")
    parser.add_argument("--analyze", action="store_true", help="Analyze the dependency graph")
    parser.add_argument("--incremental", action="store_true", help="Perform incremental analysis")
    
    args = parser.parse_args()
    
    builder = DependencyGraphBuilder(cache_dir="cache")
    
    if args.analyze:
        graph = builder.build_graph(args.root_dir, incremental=args.incremental)
        analyzer = DependencyAnalyzer(graph)
        
        print("Dependency Graph Analysis:")
        print(f"  - Files: {len(graph)}")
        print(f"  - Dependencies: {len(list(graph.edges()))}")
        
        cycles = analyzer.find_cycles()
        if cycles:
            print("Cycles found:")
            for cycle in cycles:
                print(f"  - {' -> '.join(cycle)}")
        else:
            print("No cycles found.")
            
if __name__ == "__main__":
    main()
