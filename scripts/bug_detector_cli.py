import argparse
import logging
from triangulum_lx.agents.bug_detector_agent import BugDetectorAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Bug Detector Agent CLI")
    parser.add_argument("root_dir", help="Root directory of the codebase to scan")
    parser.add_argument("--scan", action="store_true", help="Scan the codebase for bugs")
    
    args = parser.parse_args()
    
    if args.scan:
        agent = BugDetectorAgent()
        results = agent.detect_bugs_in_folder(args.root_dir)
        
        if results and results.get("total_bugs", 0) > 0:
            print("Bugs found:")
            for file_path, bugs in results.get("bugs_by_file", {}).items():
                print(f"\n--- {file_path} ---")
                for bug in bugs:
                    print(f"  - [L{bug.line_number}] {bug.description}")
        else:
            print("No bugs found.")
            
if __name__ == "__main__":
    main()
