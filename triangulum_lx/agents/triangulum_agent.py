import os
import json
import subprocess
import openai

class TriangulumAgent:
    def __init__(self, api_key):
        self.api_key = api_key
        self.shell_commands = self.load_json('tsh/shell_commands.json')
        self.shell_scripts = self.load_json('tsh/shell_scripts.json')
        openai.api_key = self.api_key

    def load_json(self, file_path):
        """Loads a JSON file."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        full_path = os.path.join(base_dir, file_path)
        with open(full_path, 'r') as f:
            return json.load(f)

    def get_available_actions(self):
        """Returns a summary of available actions."""
        return f"I can execute any of the {len(self.shell_commands['commands'])} shell commands and {len(self.shell_scripts['scripts'])} shell scripts in my knowledge base. What would you like to do?"

    def understand_request(self, user_request):
        """Uses OpenAI to understand the user's request and identify the command or script to execute."""
        prompt = f"""
        You are Triangulum, an AI assistant that executes shell commands and scripts. Your purpose is to act as a shell interface for the user.
        You have a knowledge base of shell commands and scripts that you can execute.
        Based on the user's request, identify the action to perform and the necessary arguments.
        The response should be a JSON object with the following format:
        {{
            "action": "action_name",
            "args": ["arg1", "arg2", ...]
        }}
        For example, if the user wants to list files, the action should be "list_files".
        If the user wants to run a script, the action should be "run_script".
        Be forgiving of typos and slight variations in the user's request.

        User request: "{user_request}"
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are Triangulum, an AI assistant that executes shell commands and scripts. Your purpose is to act as a shell interface for the user. Your response MUST be a valid JSON object."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
            )
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return None

    def find_command(self, command_name):
        """Finds a command in the shell_commands.json file."""
        for command in self.shell_commands['commands']:
            if command['name'] == command_name:
                return command
        return None

    def find_script(self, script_name):
        """Finds a script in the shell_scripts.json file."""
        for script in self.shell_scripts['scripts']:
            if script['name'] == script_name:
                return script
        return None

    def execute_action(self, action):
        """Executes the identified command or script."""
        action_name = action.get('action')
        action_args = action.get('args', [])

        if action_name == 'list_files':
            command = self.find_command('ls')
            if command:
                return self.run_subprocess([command['name']] + action_args)
            else:
                return "Command 'ls' not found."
        elif action_name == 'run_script':
            script_name = action_args[0]
            script = self.find_script(script_name)
            if script:
                script_path = os.path.join('scripts', f"{script['name']}.py")
                return self.run_subprocess(['python', script_path] + action_args[1:])
            else:
                # Find the closest matching script name
                closest_script = self.find_closest_match(script_name, [s['name'] for s in self.shell_scripts['scripts']])
                if closest_script:
                    return f"Script '{script_name}' not found. Did you mean '{closest_script}'?"
                else:
                    return f"Script '{script_name}' not found."
        else:
            return "Invalid action."

    def find_closest_match(self, query, options):
        """Finds the closest match to a query from a list of options."""
        best_match = None
        best_score = 0
        for option in options:
            score = self.calculate_similarity(query, option)
            if score > best_score:
                best_score = score
                best_match = option
        return best_match if best_score > 0.5 else None

    def calculate_similarity(self, s1, s2):
        """Calculates the similarity between two strings."""
        return 1 - (len(set(s1) - set(s2)) + len(set(s2) - set(s1))) / (len(set(s1)) + len(set(s2)))

    def run_subprocess(self, command):
        """Runs a subprocess and returns the output."""
        print(f"Executing command: {' '.join(command)}")
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Error: {e.stderr}"
        except FileNotFoundError:
            return f"Error: Command not found."

    def chat(self, user_request):
        """Main chat loop."""
        print(f"Triangulum: {self.get_available_actions()}")
        action = self.understand_request(user_request)
        if action:
            return self.execute_action(action)
        else:
            return "I'm sorry, I don't understand what you're asking."

if __name__ == '__main__':
    # Replace with your actual API key
    api_key = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY")
    agent = TriangulumAgent(api_key)

    # Example usage:
    user_request = "list all the files in the current directory"
    response = agent.chat(user_request)
    print(f"Triangulum: {response}")

    user_request = "run the benchmark script"
    response = agent.chat(user_request)
    print(f"Triangulum: {response}")
