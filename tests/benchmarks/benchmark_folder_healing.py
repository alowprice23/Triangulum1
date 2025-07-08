#!/usr/bin/env python
"""
Benchmarking script for the folder-level self-healing system.

This script measures the performance of the Triangulum folder-level self-healing system
by running benchmarks on different-sized codebases, measuring time, resource usage,
and effectiveness metrics.
"""

import os
import sys
import time
import argparse
import tempfile
import shutil
import json
import logging
import resource
import statistics
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from triangulum_lx.agents.message_bus import MessageBus
from triangulum_lx.agents.bug_detector_agent import BugDetectorAgent
from triangulum_lx.agents.relationship_analyst_agent import RelationshipAnalystAgent
from triangulum_lx.agents.priority_analyzer_agent import PriorityAnalyzerAgent
from triangulum_lx.agents.strategy_agent import StrategyAgent
from triangulum_lx.agents.implementation_agent import ImplementationAgent
from triangulum_lx.agents.verification_agent import VerificationAgent
from triangulum_lx.agents.orchestrator_agent import OrchestratorAgent
from triangulum_lx.agents.message import AgentMessage, MessageType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BenchmarkResult:
    """Container for benchmark results."""
    
    def __init__(self, name: str):
        """Initialize with benchmark name."""
        self.name = name
        self.start_time = time.time()
        self.end_time = None
        self.total_time = None
        self.stage_times = {}
        self.memory_usage = {}
        self.cpu_usage = {}
        self.bugs_detected = 0
        self.bugs_fixed = 0
        self.files_processed = 0
        self.files_healed = 0
        self.files_failed = 0
        self.success_rate = 0.0
        self.raw_result = {}
    
    def start_stage(self, stage_name: str) -> None:
        """Mark the start of a benchmark stage."""
        self.stage_times[stage_name] = {"start": time.time()}
        self.memory_usage[stage_name] = {"start": self._get_memory_usage()}
        self.cpu_usage[stage_name] = {"start": self._get_cpu_usage()}
    
    def end_stage(self, stage_name: str) -> None:
        """Mark the end of a benchmark stage."""
        if stage_name in self.stage_times:
            self.stage_times[stage_name]["end"] = time.time()
            self.stage_times[stage_name]["duration"] = (
                self.stage_times[stage_name]["end"] - self.stage_times[stage_name]["start"]
            )
            
            self.memory_usage[stage_name]["end"] = self._get_memory_usage()
            self.memory_usage[stage_name]["increase"] = (
                self.memory_usage[stage_name]["end"] - self.memory_usage[stage_name]["start"]
            )
            
            self.cpu_usage[stage_name]["end"] = self._get_cpu_usage()
    
    def complete(self) -> None:
        """Mark the benchmark as complete."""
        self.end_time = time.time()
        self.total_time = self.end_time - self.start_time
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return usage.ru_maxrss / 1024  # Convert KB to MB
    
    def _get_cpu_usage(self) -> Tuple[float, float]:
        """Get current CPU usage (user time, system time)."""
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return (usage.ru_utime, usage.ru_stime)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the benchmark result to a dictionary."""
        return {
            "name": self.name,
            "total_time": self.total_time,
            "stage_times": self.stage_times,
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
            "bugs_detected": self.bugs_detected,
            "bugs_fixed": self.bugs_fixed,
            "files_processed": self.files_processed,
            "files_healed": self.files_healed,
            "files_failed": self.files_failed,
            "success_rate": self.success_rate,
            "raw_result": self.raw_result
        }


class FolderHealingBenchmark:
    """Benchmark for the folder-level self-healing system."""
    
    def __init__(self, output_dir: str = None, parallel: bool = False, timeout: int = 30):
        """
        Initialize the benchmark.
        
        Args:
            output_dir: Directory to store benchmark results
            parallel: Whether to use parallel execution
            timeout: Timeout for agent operations
        """
        self.output_dir = output_dir or os.path.join(
            "tests", "benchmarks", "results", 
            f"folder_healing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.parallel = parallel
        self.timeout = timeout
        self.results = []
        
        # Project sizes for benchmarks
        self.project_sizes = {
            "small": {"files": 5, "bugs_per_file": 1},
            "medium": {"files": 20, "bugs_per_file": 2},
            "large": {"files": 50, "bugs_per_file": 3}
        }
        
        # Bug types to inject
        self.bug_types = [
            "null_pointer",
            "resource_leak",
            "exception_swallowing",
            "uninitialized_variable",
            "infinite_loop"
        ]
    
    def setup_agents(self) -> Tuple[MessageBus, OrchestratorAgent]:
        """Set up the agent system for benchmarking."""
        # Create message bus
        message_bus = MessageBus()
        
        # Create specialized agents
        BugDetectorAgent(
            agent_id="bug_detector",
            message_bus=message_bus
        )
        
        RelationshipAnalystAgent(
            agent_id="relationship_analyst",
            message_bus=message_bus
        )
        
        PriorityAnalyzerAgent(
            agent_id="priority_analyzer",
            message_bus=message_bus
        )
        
        StrategyAgent(
            agent_id="strategy_agent",
            message_bus=message_bus
        )
        
        ImplementationAgent(
            agent_id="implementation_agent",
            message_bus=message_bus
        )
        
        VerificationAgent(
            agent_id="verification_agent",
            message_bus=message_bus
        )
        
        # Create orchestrator
        orchestrator = OrchestratorAgent(
            agent_id="orchestrator",
            message_bus=message_bus,
            config={
                "timeout": self.timeout,
                "parallel_execution": self.parallel
            }
        )
        
        return message_bus, orchestrator
    
    def create_test_project(self, size: str) -> str:
        """
        Create a test project of the specified size.
        
        Args:
            size: Size of the project (small, medium, large)
            
        Returns:
            Path to the test project directory
        """
        if size not in self.project_sizes:
            raise ValueError(f"Invalid project size: {size}")
        
        config = self.project_sizes[size]
        
        # Create a temporary directory
        project_dir = tempfile.mkdtemp()
        
        # Create directories
        directories = ["core", "api", "utils", "models", "services"]
        for directory in directories:
            os.makedirs(os.path.join(project_dir, directory), exist_ok=True)
        
        # Create __init__.py files
        for directory in [project_dir] + [os.path.join(project_dir, d) for d in directories]:
            with open(os.path.join(directory, "__init__.py"), "w") as f:
                f.write("# Initialize package\n")
        
        # Create files with bugs
        file_count = config["files"]
        bugs_per_file = config["bugs_per_file"]
        
        # Distribute files across directories
        files_per_directory = file_count // len(directories)
        remainder = file_count % len(directories)
        
        file_distribution = {d: files_per_directory for d in directories}
        for i in range(remainder):
            file_distribution[directories[i]] += 1
        
        # Create files
        file_paths = []
        for directory, file_count in file_distribution.items():
            for i in range(file_count):
                file_name = f"{directory}_{i}.py"
                file_path = os.path.join(project_dir, directory, file_name)
                file_paths.append(file_path)
                
                # Create the file with bugs
                with open(file_path, "w") as f:
                    f.write(self._generate_file_with_bugs(bugs_per_file))
        
        # Create a main.py file that imports from all directories
        with open(os.path.join(project_dir, "main.py"), "w") as f:
            f.write("# Main module\n\n")
            for directory in directories:
                f.write(f"from {directory} import *\n")
            
            f.write("\ndef main():\n")
            f.write("    print('Main function')\n\n")
            f.write("if __name__ == '__main__':\n")
            f.write("    main()\n")
        
        logger.info(f"Created test project with {len(file_paths)} files at: {project_dir}")
        return project_dir
    
    def _generate_file_with_bugs(self, bug_count: int) -> str:
        """
        Generate a Python file with the specified number of bugs.
        
        Args:
            bug_count: Number of bugs to insert
            
        Returns:
            Content of the generated file
        """
        # Start with a basic file structure
        content = "# Generated test file with bugs\n\n"
        content += "import os\nimport sys\n\n"
        
        # Add a class
        content += "class TestClass:\n"
        content += "    def __init__(self, config=None):\n"
        content += "        self.config = config\n"
        content += "        self.initialize()\n\n"
        
        # Add methods with bugs
        for i in range(bug_count):
            bug_type = self.bug_types[i % len(self.bug_types)]
            content += f"    def method_{i}(self):\n"
            content += f"        # BUG: {bug_type}\n"
            
            if bug_type == "null_pointer":
                content += "        # No null check before accessing attribute\n"
                content += "        return self.config.attribute\n\n"
            
            elif bug_type == "resource_leak":
                content += "        # Resource leak - file not closed\n"
                content += "        file = open('test.txt', 'r')\n"
                content += "        data = file.read()\n"
                content += "        # Missing file.close()\n"
                content += "        return data\n\n"
            
            elif bug_type == "exception_swallowing":
                content += "        # Exception swallowing without logging\n"
                content += "        try:\n"
                content += "            result = 1 / 0\n"
                content += "        except Exception:\n"
                content += "            # Silently swallowing the exception\n"
                content += "            pass\n"
                content += "        return None\n\n"
            
            elif bug_type == "uninitialized_variable":
                content += "        # Using variable before initialization\n"
                content += "        if some_condition:\n"
                content += "            value = 10\n"
                content += "        # Missing else clause to initialize value\n"
                content += "        return value\n\n"
            
            elif bug_type == "infinite_loop":
                content += "        # Potential infinite loop\n"
                content += "        i = 0\n"
                content += "        while i < 10:\n"
                content += "            # Missing i += 1\n"
                content += "            print(i)\n"
                content += "        return i\n\n"
        
        # Add a main section
        content += "# Main section\n"
        content += "if __name__ == '__main__':\n"
        content += "    test = TestClass()\n"
        
        return content
    
    def run_benchmark(self, size: str, runs: int = 3) -> List[BenchmarkResult]:
        """
        Run the benchmark for a specific project size.
        
        Args:
            size: Size of the project (small, medium, large)
            runs: Number of benchmark runs to perform
            
        Returns:
            List of benchmark results
        """
        results = []
        
        for run in range(runs):
            logger.info(f"Starting benchmark run {run+1}/{runs} for {size} project")
            
            # Create a new result object
            result = BenchmarkResult(f"{size}_run_{run+1}")
            
            try:
                # Set up agents for this run
                message_bus, orchestrator = self.setup_agents()
                
                # Set up message handler
                orchestrator_result = {}
                
                def handle_result(message):
                    nonlocal orchestrator_result
                    if message.sender == "orchestrator":
                        orchestrator_result = message.content
                
                message_bus.register_handler(
                    "benchmark",
                    MessageType.TASK_RESULT,
                    handle_result
                )
                
                # Create test project
                result.start_stage("setup")
                project_dir = self.create_test_project(size)
                result.end_stage("setup")
                
                try:
                    # Run folder healing
                    result.start_stage("healing")
                    
                    # Create a task request message
                    message = AgentMessage(
                        message_type=MessageType.TASK_REQUEST,
                        content={
                            "action": "orchestrate_folder_healing",
                            "folder_path": project_dir,
                            "options": {
                                "dry_run": True,  # Use dry run for benchmarking
                                "max_files": 100,
                                "analysis_depth": 2
                            }
                        },
                        sender="benchmark",
                        recipient="orchestrator"
                    )
                    
                    # Process the message
                    orchestrator.handle_message(message)
                    
                    # Wait for the result (with timeout)
                    wait_timeout = max(self.timeout * 5, 60)  # Longer timeout for benchmarks
                    start_wait = time.time()
                    
                    while time.time() - start_wait < wait_timeout:
                        if orchestrator_result:
                            break
                        time.sleep(0.1)
                    
                    result.end_stage("healing")
                    
                    # Process the result
                    if orchestrator_result:
                        healing_result = orchestrator_result.get("result", {})
                        result.raw_result = healing_result
                        
                        # Extract metrics
                        result.bugs_detected = healing_result.get("bugs_detected", 0)
                        result.bugs_fixed = healing_result.get("bugs_fixed", 0)
                        result.files_processed = len(healing_result.get("files_processed", []))
                        result.files_healed = len(healing_result.get("files_healed", []))
                        result.files_failed = len(healing_result.get("files_failed", []))
                        
                        if result.files_processed > 0:
                            result.success_rate = result.files_healed / result.files_processed
                    else:
                        logger.warning(f"No result received for {size}_run_{run+1}")
                
                finally:
                    # Clean up the test project
                    result.start_stage("cleanup")
                    shutil.rmtree(project_dir)
                    result.end_stage("cleanup")
            
            except Exception as e:
                logger.error(f"Error in benchmark run: {str(e)}")
                import traceback
                logger.debug(traceback.format_exc())
            
            # Complete the result
            result.complete()
            results.append(result)
            
            logger.info(f"Completed benchmark run {run+1}/{runs} for {size} project in {result.total_time:.2f}s")
        
        return results
    
    def run_all_benchmarks(self, runs: int = 3) -> None:
        """
        Run benchmarks for all project sizes.
        
        Args:
            runs: Number of benchmark runs to perform for each size
        """
        logger.info(f"Starting all benchmarks with {runs} runs per size")
        
        for size in self.project_sizes:
            logger.info(f"Running benchmarks for {size} project")
            size_results = self.run_benchmark(size, runs)
            self.results.extend(size_results)
            
            # Save intermediate results
            self.save_results()
        
        # Generate reports
        self.generate_reports()
        
        logger.info(f"All benchmarks completed. Results saved to: {self.output_dir}")
    
    def save_results(self) -> None:
        """Save the benchmark results to a JSON file."""
        results_file = os.path.join(self.output_dir, "benchmark_results.json")
        
        with open(results_file, "w") as f:
            json.dump([r.to_dict() for r in self.results], f, indent=2)
        
        logger.info(f"Saved benchmark results to: {results_file}")
    
    def generate_reports(self) -> None:
        """Generate reports and visualizations from benchmark results."""
        if not self.results:
            logger.warning("No benchmark results to generate reports from")
            return
        
        # Group results by size
        results_by_size = {}
        for result in self.results:
            size = result.name.split("_")[0]  # Extract size from name
            if size not in results_by_size:
                results_by_size[size] = []
            results_by_size[size].append(result)
        
        # Generate summary report
        summary_file = os.path.join(self.output_dir, "benchmark_summary.txt")
        with open(summary_file, "w") as f:
            f.write("Triangulum Folder Healing Benchmark Summary\n")
            f.write("===========================================\n\n")
            
            f.write(f"Benchmark run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Parallel execution: {self.parallel}\n")
            f.write(f"Agent timeout: {self.timeout}s\n\n")
            
            f.write("Performance Summary:\n")
            f.write("-----------------\n")
            
            for size, size_results in results_by_size.items():
                avg_total_time = statistics.mean(r.total_time for r in size_results)
                avg_bugs_detected = statistics.mean(r.bugs_detected for r in size_results)
                avg_bugs_fixed = statistics.mean(r.bugs_fixed for r in size_results)
                avg_files_processed = statistics.mean(r.files_processed for r in size_results)
                avg_success_rate = statistics.mean(r.success_rate for r in size_results)
                
                f.write(f"\n{size.upper()} Project ({len(size_results)} runs):\n")
                f.write(f"  Average total time: {avg_total_time:.2f}s\n")
                f.write(f"  Average bugs detected: {avg_bugs_detected:.1f}\n")
                f.write(f"  Average bugs fixed: {avg_bugs_fixed:.1f}\n")
                f.write(f"  Average files processed: {avg_files_processed:.1f}\n")
                f.write(f"  Average success rate: {avg_success_rate:.2%}\n")
                
                # Stage times
                f.write("  Average stage times:\n")
                for stage in ["setup", "healing", "cleanup"]:
                    stage_times = [r.stage_times.get(stage, {}).get("duration", 0) for r in size_results]
                    if stage_times:
                        avg_stage_time = statistics.mean(stage_times)
                        f.write(f"    {stage}: {avg_stage_time:.2f}s\n")
        
        logger.info(f"Generated summary report: {summary_file}")
        
        # Generate visualizations
        try:
            # Time comparison by project size
            plt.figure(figsize=(12, 6))
            sizes = list(results_by_size.keys())
            avg_times = [statistics.mean(r.total_time for r in results_by_size[size]) for size in sizes]
            plt.bar(sizes, avg_times)
            plt.title('Average Total Time by Project Size')
            plt.xlabel('Project Size')
            plt.ylabel('Time (seconds)')
            plt.savefig(os.path.join(self.output_dir, 'time_by_size.png'))
            
            # Bug detection by project size
            plt.figure(figsize=(12, 6))
            avg_bugs = [statistics.mean(r.bugs_detected for r in results_by_size[size]) for size in sizes]
            plt.bar(sizes, avg_bugs)
            plt.title('Average Bugs Detected by Project Size')
            plt.xlabel('Project Size')
            plt.ylabel('Bugs Detected')
            plt.savefig(os.path.join(self.output_dir, 'bugs_by_size.png'))
            
            # Success rate by project size
            plt.figure(figsize=(12, 6))
            avg_success = [statistics.mean(r.success_rate for r in results_by_size[size]) for size in sizes]
            plt.bar(sizes, avg_success)
            plt.title('Average Success Rate by Project Size')
            plt.xlabel('Project Size')
            plt.ylabel('Success Rate')
            plt.ylim(0, 1)
            plt.savefig(os.path.join(self.output_dir, 'success_by_size.png'))
            
            logger.info(f"Generated visualization charts in: {self.output_dir}")
            
        except Exception as e:
            logger.error(f"Error generating visualizations: {str(e)}")


def main():
    """Main function to run benchmarks."""
    parser = argparse.ArgumentParser(
        description="Benchmark the Triangulum folder-level self-healing system")
    
    parser.add_argument(
        "--output-dir", 
        help="Directory to store benchmark results")
    
    parser.add_argument(
        "--parallel", 
        action="store_true",
        help="Use parallel execution")
    
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=30,
        help="Timeout for agent operations (seconds)")
    
    parser.add_argument(
        "--runs", 
        type=int, 
        default=3,
        help="Number of benchmark runs per project size")
    
    parser.add_argument(
        "--size", 
        choices=["small", "medium", "large", "all"],
        default="all",
        help="Project size to benchmark")
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create benchmark
    benchmark = FolderHealingBenchmark(
        output_dir=args.output_dir,
        parallel=args.parallel,
        timeout=args.timeout
    )
    
    try:
        if args.size == "all":
            # Run all benchmarks
            benchmark.run_all_benchmarks(args.runs)
        else:
            # Run benchmark for a specific size
            logger.info(f"Running benchmarks for {args.size} project")
            results = benchmark.run_benchmark(args.size, args.runs)
            benchmark.results.extend(results)
            benchmark.save_results()
            benchmark.generate_reports()
    
    except KeyboardInterrupt:
        logger.info("Benchmark interrupted by user")
        # Save any results obtained so far
        if benchmark.results:
            benchmark.save_results()
            benchmark.generate_reports()
    
    except Exception as e:
        logger.error(f"Error running benchmarks: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())


if __name__ == "__main__":
    main()
