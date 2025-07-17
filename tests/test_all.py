import os
import json
from click.testing import CliRunner
from triangulum.main import triangulum

def test_triangulum_help():
    runner = CliRunner()
    result = runner.invoke(triangulum, ['--help'])
    assert result.exit_code == 0
    assert 'Usage: triangulum [OPTIONS] COMMAND [ARGS]' in result.output

def test_triage_brainstorm():
    runner = CliRunner()
    result = runner.invoke(triangulum, ['triage', 'brainstorm', 'brainstorm-30'])
    assert result.exit_code == 0
    ideas = json.loads(result.output)
    assert len(ideas) == 30

    result = runner.invoke(triangulum, ['triage', 'brainstorm', 'triangulate-3'])
    assert result.exit_code == 0
    assert "Triangulating top 3 ideas" in result.output

    result = runner.invoke(triangulum, ['triage', 'brainstorm', 'refine-2'])
    assert result.exit_code == 0
    assert "Refining 2 plans" in result.output

    result = runner.invoke(triangulum, ['triage', 'brainstorm', 'backup-1'])
    assert result.exit_code == 0
    assert "Creating 1 backup plan" in result.output


def test_util_grep():
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.makedirs("subdir")
        with open("subdir/test_grep_file.txt", "w") as f:
            f.write("hello world\n")
            f.write("another line\n")
        result = runner.invoke(triangulum, ['util', 'grep', 'hello', 'subdir'])
        assert result.exit_code == 0
        assert "subdir/test_grep_file.txt:1:hello world" in result.output


def test_graph_build():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(triangulum, ['graph', 'build'])
        assert result.exit_code == 0
        assert os.path.exists('.cache/dependency_graph.json')
        with open('.cache/dependency_graph.json', 'r') as f:
            data = json.load(f)
            assert data == {"nodes": [], "edges": []}

def test_all_domains():
    runner = CliRunner()
    domains = {
        'core': 'info',
        'agent': 'list',
        'bus': 'status',
        'repair': 'auto',
        'verify': 'all',
        'perf': 'check',
        'dash': 'show',
        'config': 'get',
        'fs': 'ls'
    }
    for domain, command in domains.items():
        result = runner.invoke(triangulum, [domain, command])
        assert result.exit_code == 0
