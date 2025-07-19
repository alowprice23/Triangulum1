import unittest
from click.testing import CliRunner
from triangulum_lx.shell.main import cli

class TestShell(unittest.TestCase):
    def test_shell_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Usage: cli [OPTIONS] COMMAND [ARGS]', result.output)

    def test_run_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['run'])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output, 'Running the Triangulum engine...\n')

    def test_analyze_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['analyze'])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output, 'Running a static analysis...\n')

    def test_benchmark_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['benchmark'])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output, 'Running the system\'s benchmark suite...\n')

    def test_start_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['start'])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output, 'Starting the Triangulum engine...\n')

    def test_stop_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['stop'])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output, 'Stopping the Triangulum engine...\n')

    def test_status_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['status'])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output, 'Showing the status of the Triangulum engine...\n')

    def test_shell_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['shell'], input='exit\n')
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Welcome to the Triangulum Lx interactive shell.', result.output)
        self.assertIn('Exiting the interactive shell.', result.output)

    def test_script_command(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open('test_script.tsh', 'w') as f:
                f.write('run\n')
                f.write('analyze\n')
            result = runner.invoke(cli, ['script', 'test_script.tsh'])
            self.assertEqual(result.exit_code, 0)
            self.assertIn('Running script: test_script.tsh', result.output)
            self.assertIn('Running command: run', result.output)
            self.assertIn('Running command: analyze', result.output)

    def test_agent_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['agent'], input='hello\nexit\n')
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Welcome to the agent chat.', result.output)
        self.assertIn('Agent > hello', result.output)
        self.assertIn('Exiting the agent chat.', result.output)

if __name__ == '__main__':
    unittest.main()
