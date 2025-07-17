import os
import json
import ast

def get_script_info(script_path):
    """
    Extracts information from a Python script file.
    """
    with open(script_path, 'r') as f:
        tree = ast.parse(f.read(), filename=script_path)

    docstring = ast.get_docstring(tree)
    description = docstring.strip().split('\n')[0] if docstring else "No description available."

    return {
        'description': description,
        'usage': f'python {os.path.basename(script_path)}'
    }

def get_shell_scripts():
    """
    Returns a dictionary of all available shell scripts.
    """
    scripts = {}
    scripts_path = os.path.dirname(__file__)
    for filename in os.listdir(scripts_path):
        if filename.endswith('.py') and not filename.startswith('__') and filename != 'generate_script_json.py':
            script_name = filename[:-3]
            script_path = os.path.join(scripts_path, filename)
            scripts[script_name] = get_script_info(script_path)
    return scripts

if __name__ == '__main__':
    scripts = get_shell_scripts()
    output_path = os.path.join(os.path.dirname(__file__), '..', 'tsh', 'shell_scripts.json')
    with open(output_path, 'w') as f:
        json.dump(scripts, f, indent=2)
    print(f"Successfully generated shell_scripts.json at {output_path}")
