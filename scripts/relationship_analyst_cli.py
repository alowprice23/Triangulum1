import argparse
import logging
from triangulum_lx.agents.relationship_analyst_agent import RelationshipAnalystAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Relationship Analyst Agent CLI")
    parser.add_argument("root_dir", help="Root directory of the codebase to analyze")
    parser.add_argument("--analyze", action="store_true", help="Analyze the codebase for relationships")
    
    args = parser.parse_args()
    
    if args.analyze:
        agent = RelationshipAnalystAgent(cache_dir="cache")
        summary = agent.analyze_codebase(args.root_dir)
        
        print("Relationship Analysis Summary:")
        for key, value in summary.items():
            print(f"  - {key}: {value}")
            
if __name__ == "__main__":
    main()
