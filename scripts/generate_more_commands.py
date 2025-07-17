import json

def generate_commands(existing_commands, num_to_generate):
    new_commands = []
    for i in range(num_to_generate):
        new_command = {
            "name": f"command_{len(existing_commands) + i}",
            "description": f"This is the description for command {len(existing_commands) + i}.",
            "usage": f"command_{len(existing_commands) + i} [options]"
        }
        new_commands.append(new_command)
    return new_commands

with open('tsh/shell_commands.json', 'r+') as f:
    data = json.load(f)
    existing_commands = data['commands']
    new_commands = generate_commands(existing_commands, 2800)
    existing_commands.extend(new_commands)
    f.seek(0)
    json.dump(data, f, indent=2)
