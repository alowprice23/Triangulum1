import os
import importlib
import click
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def get_shell_commands():
    """
    Returns a dictionary of all available shell commands.
    """
    commands = {}
    domains_path = os.path.join(os.path.dirname(__file__), 'domains')
    for filename in os.listdir(domains_path):
        if filename.endswith('.py') and not filename.startswith('__'):
            command_name = filename[:-3]
            module = importlib.import_module(f'tsh.domains.{command_name}')
            if hasattr(module, 'cli'):
                cli = module.cli
                commands[command_name] = {
                    'description': cli.help,
                    'params': [],
                    'usage': f'tsh {command_name} [OPTIONS]'
                }
                if isinstance(cli, click.Group):
                    commands[command_name]['usage'] = f'tsh {command_name} [COMMAND] [OPTIONS]'
                    commands[command_name]['subcommands'] = {}
                    for subcommand_name, subcommand in cli.commands.items():
                        commands[command_name]['subcommands'][subcommand_name] = {
                            'description': subcommand.help,
                            'params': [],
                            'usage': f'tsh {command_name} {subcommand_name} [OPTIONS]'
                        }
                        for param in subcommand.params:
                            help_record = param.get_help_record(None)
                            commands[command_name]['subcommands'][subcommand_name]['params'].append({
                                'name': param.name,
                                'type': param.type.name,
                                'required': param.required,
                                'help': help_record[1] if help_record else None
                            })
                else:
                    for param in cli.params:
                        help_record = param.get_help_record(None)
                        commands[command_name]['params'].append({
                            'name': param.name,
                            'type': param.type.name,
                            'required': param.required,
                            'help': help_record[1] if help_record else None
                        })
    return commands

if __name__ == '__main__':
    import json
    commands = get_shell_commands()
    output_path = os.path.join(os.path.dirname(__file__), 'shell_commands.json')
    with open(output_path, 'w') as f:
        json.dump(commands, f, indent=2)
    print(f"Successfully generated shell_commands.json at {output_path}")
