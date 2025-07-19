import os
import json
import sys
from pathlib import Path
from click.testing import CliRunner

# Add the parent directory to sys.path to enable imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from triangulum_lx.scripts.cli import cli as triangulum

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(triangulum, ['--help'])
    assert result.exit_code == 0
    assert 'Usage: cli [OPTIONS] COMMAND [ARGS]' in result.output

def test_analyze_command():
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.makedirs('project/subdir', exist_ok=True)
        with open("project/main.py", "w") as f:
            f.write("import os\nfrom subdir.module import a_function\na_function()")
        with open("project/subdir/module.py", "w") as f:
            f.write("def a_function():\n    print('hello')")

        result = runner.invoke(triangulum, ['analyze', 'project'])
        assert result.exit_code == 0

        output = json.loads(result.output.split('Analysis for directory: project\n')[1])
        assert len(output['nodes']) == 2
        assert len(output['links']) > 0

def test_benchmark_command(cli_runner_with_files):
    result = cli_runner_with_files.invoke(triangulum, ['benchmark'])
    assert result.exit_code == 0
    assert 'Running benchmarks...' in result.output

def test_run_command(cli_runner_with_files):
    with open("goal.yaml", "w") as f:
        f.write("name: test_goal")
    result = cli_runner_with_files.invoke(triangulum, ['run', '--config', 'triangulum.yaml', '--goal', 'goal.yaml'])
    assert result.exit_code == 0
    assert 'Starting engine with goal file: goal.yaml' in result.output

def test_start_stop_status_shell_commands():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("triangulum.yaml", "w") as f:
            f.write("""
llm:
  default_provider: openai
  providers:
    openai:
      default_model: o3
      api_key: os.environ.get("OPENAI_API_KEY", "sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
agents:
  meta_agent:
    enabled: true
""")

        result = runner.invoke(triangulum, ['start', '--config', 'triangulum.yaml'])
        assert result.exit_code == 0
        assert 'Starting Triangulum...' in result.output

        obj = runner.result.obj
        assert 'engine' in obj

        result = runner.invoke(triangulum, ['status'], obj=obj)
        assert result.exit_code == 0
        assert "'initialized': True" in result.output

        result = runner.invoke(triangulum, ['stop'], obj=obj)
        assert result.exit_code == 0
        assert 'Stopping Triangulum...' in result.output

        result = runner.invoke(triangulum, ['shell'], obj=obj)
        assert result.exit_code == 0
        assert 'Starting Triangulum shell...' in result.output
