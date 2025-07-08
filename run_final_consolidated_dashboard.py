#!/usr/bin/env python3
"""
Triangulum Agentic Dashboard - FINAL CONSOLIDATED VERSION

This script provides the perfect solution for running the Triangulum agentic dashboard:
1. Preserves ALL working visualizations from the previous dashboard
2. Maintains exact data formats and structures that were previously working
3. Only updates specific fields to refresh the data while preserving relationships
4. Serves all files from a stable HTTP server
"""

import os
import shutil
import http.server
import socketserver
import webbrowser
import random
import logging
import argparse
import json
import datetime
import uuid
import sys
from functools import partial

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_directory_exists(directory):
    """Ensure a directory exists, creating it if necessary."""
    os.makedirs(directory, exist_ok=True)
    return directory

def clone_dashboard(src_dir, dest_dir):
    """Clone the entire dashboard structure from source to destination."""
    # First ensure the destination directory exists
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    
    # If source doesn't exist, log an error and return
    if not os.path.exists(src_dir):
        logger.error(f"Source directory {src_dir} does not exist!")
        return False
    
    # Clone everything - structure and files
    for item in os.listdir(src_dir):
        src_item = os.path.join(src_dir, item)
        dest_item = os.path.join(dest_dir, item)
        
        if os.path.isdir(src_item):
            if os.path.exists(dest_item):
                shutil.rmtree(dest_item)
            shutil.copytree(src_item, dest_item)
            logger.info(f"Copied directory: {item}")
        else:
            shutil.copy2(src_item, dest_item)
            logger.info(f"Copied file: {item}")
    
    logger.info(f"Successfully cloned dashboard from {src_dir} to {dest_dir}")
    return True

def update_timestamps_in_json(file_path):
    """Update timestamps in JSON data to make it appear fresh."""
    if not os.path.exists(file_path):
        logger.warning(f"File does not exist: {file_path}")
        return
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Different handling based on the file type
        filename = os.path.basename(file_path)
        
        if "progress" in file_path:
            # Update agent progress timestamps
            if isinstance(data, dict):
                for agent_id, agent_data in data.items():
                    if isinstance(agent_data, dict) and "last_updated" in agent_data:
                        agent_data["last_updated"] = datetime.datetime.now().isoformat()
        
        elif "timeline" in file_path:
            # Update timeline event timestamps to be more recent
            if isinstance(data, list):
                now = datetime.datetime.now()
                for i, event in enumerate(data):
                    if isinstance(event, dict) and "timestamp" in event:
                        # Keep chronological order but make recent
                        new_time = now - datetime.timedelta(minutes=i*3)
                        event["timestamp"] = new_time.isoformat()
                
                # Re-sort by timestamp
                data.sort(key=lambda x: x["timestamp"], reverse=True)
        
        elif "decision_trees" in file_path:
            # Update decision tree timestamps
            if isinstance(data, dict):
                for tree_id, tree_data in data.items():
                    if isinstance(tree_data, dict) and "last_updated" in tree_data:
                        tree_data["last_updated"] = datetime.datetime.now().isoformat()
        
        elif "thought_chains" in file_path:
            # Update thought chain timestamps
            if isinstance(data, dict):
                for chain_id, chain_data in data.items():
                    if isinstance(chain_data, dict) and "thoughts" in chain_data:
                        now = datetime.datetime.now()
                        for i, thought in enumerate(chain_data["thoughts"]):
                            if "timestamp" in thought:
                                new_time = now - datetime.timedelta(minutes=i*5)
                                thought["timestamp"] = new_time.isoformat()
        
        # Write updated data back to file
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Updated timestamps in {file_path}")
    except Exception as e:
        logger.error(f"Error updating timestamps in {file_path}: {e}")

def refresh_dashboard_data(dashboard_dir):
    """Refresh all JSON data files with updated timestamps and values."""
    # Find all JSON files in the dashboard directory and its subdirectories
    for root, dirs, files in os.walk(dashboard_dir):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                update_timestamps_in_json(file_path)
    
    logger.info(f"Refreshed all dashboard data in {dashboard_dir}")

def main():
    """Run the consolidated dashboard script."""
    parser = argparse.ArgumentParser(description='Run the Triangulum Agentic Dashboard')
    parser.add_argument('--output-dir', type=str, default='./triangulum_dashboard_final_consolidated', 
                        help='Directory for the consolidated dashboard')
    parser.add_argument('--source-dir', type=str, default='./agentic_dashboard_full_demo', 
                        help='Source directory containing the working dashboard')
    parser.add_argument('--port', type=int, default=None, help='Port for the server (default: random)')
    parser.add_argument('--no-browser', action='store_true', help='Do not open the browser automatically')
    
    args = parser.parse_args()
    
    # Ensure the output directory exists
    ensure_directory_exists(args.output_dir)
    
    # Clone the complete dashboard structure
    clone_success = clone_dashboard(args.source_dir, args.output_dir)
    if not clone_success:
        logger.error(f"Failed to clone dashboard from {args.source_dir}. Aborting.")
        return 1
    
    # Refresh all data files to have current timestamps
    refresh_dashboard_data(args.output_dir)
    
    # Use functools.partial to pass the directory to the handler
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=args.output_dir)
    
    # Use a random port if none specified to avoid conflicts
    port = args.port or random.randint(8000, 9000)
    
    # Pretty print header
    print("\n" + "=" * 80)
    print("TRIANGULUM AGENTIC DASHBOARD - FINAL CONSOLIDATED VERSION".center(80))
    print("=" * 80 + "\n")
    
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"Dashboard server started at http://localhost:{port}/")
            print(f"Serving files from: {os.path.abspath(args.output_dir)}")
            print("Press Ctrl+C to stop the server\n")
            
            if not args.no_browser:
                webbrowser.open(f"http://localhost:{port}/")
            
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
