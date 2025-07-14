import os
import json
from click.testing import CliRunner
from tsh.main import tsh

def test_tsh_help():
    runner = CliRunner()
    result = runner.invoke(tsh, ['--help'])
    assert result.exit_code == 0
    assert 'Usage: tsh [OPTIONS] COMMAND [ARGS]' in result.output

def test_triage_brainstorm():
    runner = CliRunner()
    result = runner.invoke(tsh, ['triage', 'brainstorm', 'brainstorm-30'])
    assert result.exit_code == 0
    ideas = json.loads(result.output)
    assert len(ideas) == 30

    result = runner.invoke(tsh, ['triage', 'brainstorm', 'triangulate-3'])
    assert result.exit_code == 0
    assert "Triangulating top 3 ideas" in result.output

    result = runner.invoke(tsh, ['triage', 'brainstorm', 'refine-2'])
    assert result.exit_code == 0
    assert "Refining 2 plans" in result.output

    result = runner.invoke(tsh, ['triage', 'brainstorm', 'backup-1'])
    assert result.exit_code == 0
    assert "Creating 1 backup plan" in result.output


def test_util_grep():
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.makedirs("subdir")
        with open("subdir/test_grep_file.txt", "w") as f:
            f.write("hello world\n")
            f.write("another line\n")
        result = runner.invoke(tsh, ['util', 'grep', 'hello', 'subdir'])
        assert result.exit_code == 0
        assert "subdir/test_grep_file.txt:1:hello world" in result.output


def test_graph_build():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(tsh, ['graph', 'build'])
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
        result = runner.invoke(tsh, [domain, command])
        assert result.exit_code == 0
