import unittest
from click.testing import CliRunner
from triangulum_lx.shell.main import cli
from triangulum_lx.core.engine import TriangulumEngine

class TestShellIntegration(unittest.TestCase):
    def test_start_and_status_commands(self):
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

            result = runner.invoke(cli, ['start', '--config', 'triangulum.yaml'])
            self.assertEqual(result.exit_code, 0)
            self.assertIn('Starting the Triangulum engine...', result.output)

            result = runner.invoke(cli, ['status'])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("'initialized': True", result.output)

if __name__ == '__main__':
    unittest.main()
