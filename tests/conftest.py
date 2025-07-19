import pytest
import os
from click.testing import CliRunner

@pytest.fixture
def cli_runner_with_files():
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.makedirs("tests/benchmarks", exist_ok=True)
        with open("tests/benchmarks/standard_prompts.yaml", "w") as f:
            f.write("- task: test\n  prompt: test")
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
        yield runner
