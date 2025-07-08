#!/usr/bin/env python3
"""
Run Simple Agentic Dashboard

A simplified version of the dashboard server that works with Python 3.12.
This script serves the fixed Triangulum agentic dashboard with all visualizations.
"""

import os
import http.server
import socketserver
import webbrowser
import random
import logging
import argparse
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Simple HTTP request handler for serving dashboard files."""
    
    def __init__(self, *args, **kwargs):
        # Get the directory from the class
        self.directory = DashboardHandler.dashboard_directory
        super().__init__(*args, **kwargs)
    
    # This is needed to silence the default logging from SimpleHTTPRequestHandler
    def log_message(self, format, *args):
        pass

def main():
    """Run the simple dashboard server."""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Run the Triangulum agentic dashboard')
    
    parser.add_argument(
        '--directory',
        type=str,
        default='./triangulum_dashboard_fixed',
        help='Directory containing the dashboard files'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='Port to run the server on (default: random port between 8000-9000)'
    )
    
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not open the browser automatically'
    )
    
    args = parser.parse_args()
    
    # Ensure directory exists
    if not os.path.exists(args.directory):
        print(f"Error: Dashboard directory '{args.directory}' does not exist.")
        print("Please run fix_agentic_dashboard.py first.")
        return 1
    
    # Set the directory in the handler class
    DashboardHandler.dashboard_directory = args.directory
    
    # Change to the dashboard directory
    os.chdir(args.directory)
    
    # Select a port
    port = args.port
    if port is None:
        # Try to find an available port
        for _ in range(10):
            port = random.randint(8000, 9000)
            try:
                with socketserver.TCPServer(("", port), None) as s:
                    pass  # Port is available if we get here
                break
            except OSError:
                continue
        else:
            port = 8765  # Default fallback
    
    print("=" * 80)
    print("TRIANGULUM AGENTIC DASHBOARD".center(80))
    print("=" * 80)
    print(f"\nStarting dashboard server at http://localhost:{port}/")
    
    # Create and start the server
    try:
        with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
            # Print server info
            print(f"Server started at http://localhost:{port}/")
            print("Press Ctrl+C to stop the server")
            
            # Open browser if requested
            if not args.no_browser:
                threading.Thread(target=lambda: webbrowser.open(f"http://localhost:{port}/"), 
                                daemon=True).start()
            
            # Serve until interrupted
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"Error starting server: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
