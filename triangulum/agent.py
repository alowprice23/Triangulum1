import openai
import os
import json
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from triangulum.shell_commands import get_shell_commands
from triangulum.shell_scripts import get_shell_scripts

class TriangulumAgent:
    def __init__(self, openai_api_key):
        self.openai_api_key = openai_api_key
        openai.api_key = self.openai_api_key
        self.commands = get_shell_commands()
        self.scripts = get_shell_scripts()
        self.history = []

    def get_context(self):
        context = {
            "commands": self.commands,
            "scripts": self.scripts,
            "history": self.history
        }
        return json.dumps(context, indent=2)

    def get_prompt(self, user_input):
        context = self.get_context()
        prompt = f"""You are the Triangulum Shell Agent (TSA). Your role is to assist users by executing shell commands and scripts.

Here is the current context:
{context}

The user said: "{user_input}"

Based on the user's request, what command or script should be executed? Your response should be a JSON object with the following format:
{{
  "type": "command" or "script",
  "name": "the command or script name",
  "args": ["arg1", "arg2", ...]
}}

If you are unsure or the request is ambiguous, respond with:
{{
  "type": "clarification",
  "message": "your clarifying question"
}}
"""
        return prompt

    def process_user_input(self, user_input):
        prompt = self.get_prompt(user_input)
        try:
            response = openai.chat.completions.create(
                model="o3",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = response.choices[0].message.content.strip()
            response_json = json.loads(response_text)
            self.history.append({"user": user_input, "agent": response_json})
            return response_json
        except Exception as e:
            return {"type": "error", "message": str(e)}

    def execute_action(self, action):
        action_type = action.get("type")
        if action_type == "command":
            self.execute_command(action)
        elif action_type == "script":
            self.execute_script(action)
        else:
            print(action.get("message"))

    def execute_command(self, action):
        command_parts = action.get("name").split()
        command_name = command_parts[0]
        subcommand_name = command_parts[1] if len(command_parts) > 1 else None

        command = self.commands.get(command_name)
        if not command:
            print(f"Command '{command_name}' not found.")
            return

        import subprocess
        if subcommand_name:
            subcommand = command.get("subcommands", {}).get(subcommand_name)
            if not subcommand:
                print(f"Subcommand '{subcommand_name}' for command '{command_name}' not found.")
                return
            try:
                process = subprocess.run(['python3', 'triangulum/main.py', command_name, subcommand_name] + action.get('args', []), capture_output=True, text=True)
                print(process.stdout)
                print(process.stderr)
            except Exception as e:
                print(f"Error executing command: {e}")
        else:
            try:
                process = subprocess.run(['python3', 'triangulum/main.py', command_name] + action.get('args', []), capture_output=True, text=True)
                print(process.stdout)
                print(process.stderr)
            except Exception as e:
                print(f"Error executing command: {e}")

    def execute_script(self, action):
        script_name = action.get("name")
        script = self.scripts.get(script_name)
        if not script:
            print(f"Script '{script_name}' not found.")
            return

        # This is a placeholder for the execution logic
        print(f"Executing script: {script_name} with args: {action.get('args')}")

    def run(self, test_input=None):
        print("Triangulum Shell Agent (TSA) is running. Type 'exit' to quit.")
        if test_input:
            action = self.process_user_input(test_input)
            self.execute_action(action)
            return

        while True:
            try:
                user_input = input("> ")
                if user_input.lower() == 'exit':
                    break
                action = self.process_user_input(user_input)
                self.execute_action(action)
            except (KeyboardInterrupt, EOFError):
                break

if __name__ == '__main__':
    # It is recommended to use an environment variable for the API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
    else:
        agent = TriangulumAgent(api_key)
        agent.run()
