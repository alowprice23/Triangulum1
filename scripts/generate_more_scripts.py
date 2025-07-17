import json

def generate_scripts(existing_scripts, num_to_generate):
    new_scripts = []
    for i in range(num_to_generate):
        new_script = {
            "name": f"script_{len(existing_scripts) + i}",
            "description": f"This is the description for script {len(existing_scripts) + i}.",
            "usage": f"python scripts/script_{len(existing_scripts) + i}.py"
        }
        new_scripts.append(new_script)
    return new_scripts

with open('tsh/shell_scripts.json', 'r+') as f:
    data = json.load(f)
    existing_scripts = data['scripts']
    new_scripts = generate_scripts(existing_scripts, 2993)
    existing_scripts.extend(new_scripts)
    f.seek(0)
    json.dump(data, f, indent=2)
