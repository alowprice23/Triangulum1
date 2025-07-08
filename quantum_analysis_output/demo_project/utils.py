
import json
import logging

def load_data(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return None

def save_results(results):
    # Bug: hardcoded filename
    with open("results.json", 'w') as f:
        json.dump(results, f, indent=2)
