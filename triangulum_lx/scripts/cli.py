import click
import logging
import sys
from pathlib import Path

# Add the parent directory to sys.path to enable imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from triangulum_lx.core.engine import TriangulumEngine
from triangulum_lx.monitoring.system_monitor import start_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("triangulum.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("triangulum.cli")

@click.group()
@click.version_option(version="1.1.0", prog_name="Triangulum Lx")
def cli():
    """
    Triangulum Lx: An autonomous, self-healing software system.
    """
    pass

@cli.command()
@click.option('--goal', default='triangulum_lx/goal/app_goal.yaml', help='Path to the goal definition file.')
@click.option('--verbose', is_flag=True, help='Enable verbose logging.')
def run(goal, verbose):
    """
    Run the Triangulum engine with a specified goal.
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Initializing Triangulum Engine...")
    engine = TriangulumEngine()
    
    # Start the system monitor
    monitor = start_monitor(engine)
    
    try:
        logger.info(f"Starting engine with goal file: {goal}")
        engine.run(goal_file=goal)
    except KeyboardInterrupt:
        logger.info("Shutdown signal received.")
    finally:
        logger.info("Shutting down Triangulum Engine...")
        engine.shutdown()
        monitor.stop()
        logger.info("Shutdown complete.")

@cli.command()
@click.argument('path', type=click.Path(exists=True))
def analyze(path):
    """
    Run a static analysis on a specific file or directory.
    """
    from triangulum_lx.tooling.code_relationship_analyzer import CodeRelationshipAnalyzer
    analyzer = CodeRelationshipAnalyzer()
    
    target_path = Path(path)
    if target_path.is_file():
        relationships = analyzer.analyze_file(target_path)
        click.echo(f"Analysis for file: {path}")
        click.echo(relationships)
    elif target_path.is_dir():
        relationships = analyzer.analyze_directory(target_path)
        click.echo(f"Analysis for directory: {path}")
        click.echo(relationships)

@cli.command()
def benchmark():
    """
    Run the system's benchmark suite.
    """
    from scripts.run_benchmarks import main as run_benchmarks_main
    click.echo("Running benchmarks...")
    run_benchmarks_main()

if __name__ == "__main__":
    cli()
