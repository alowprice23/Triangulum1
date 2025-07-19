"""
System Monitor - Monitors the health and performance of the Triangulum system.

This module provides functionality for checking system health, gathering metrics,
and diagnosing issues in the Triangulum system.
"""

import logging
import os
import sys
import time
import psutil
import threading
from typing import Dict, List, Any, Optional, Union
from pathlib import Path # Added for consistency

from triangulum_lx.tooling.fs_ops import atomic_write
from triangulum_lx.core.fs_state import FileSystemStateCache

logger = logging.getLogger(__name__)

class SystemMonitor:
    """
    Monitors the health and performance of the Triangulum system.
    """

    def __init__(self, engine, fs_cache: Optional[FileSystemStateCache] = None):
        """
        Initialize the SystemMonitor.

        Args:
            engine: The Triangulum engine
            fs_cache: Optional FileSystemStateCache instance.
        """
        self.engine = engine
        self.metrics = {}
        self.warnings = []
        self.errors = []
        self.monitoring_thread = None
        self.monitoring_interval = 60  # seconds
        self.is_monitoring = False
        self.last_check_time = None
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()
        
        # Resource thresholds
        self.thresholds = {
            'cpu_percent': 90.0,  # 90% CPU usage is high
            'memory_percent': 85.0,  # 85% memory usage is high
            'disk_percent': 90.0,  # 90% disk usage is high
        }
        
        logger.info("SystemMonitor initialized")

    def start_monitoring(self, interval: int = 60) -> None:
        """
        Start continuous monitoring in a background thread.

        Args:
            interval: Monitoring interval in seconds
        """
        if self.is_monitoring:
            logger.warning("Monitoring is already active")
            return
        
        self.monitoring_interval = interval
        self.is_monitoring = True
        
        def monitor_loop():
            while self.is_monitoring:
                try:
                    self.check_health()
                    time.sleep(self.monitoring_interval)
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(self.monitoring_interval)
        
        self.monitoring_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info(f"Started system monitoring with interval {interval}s")

    def stop_monitoring(self) -> None:
        """Stop continuous monitoring."""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1.0)
            self.monitoring_thread = None
        
        logger.info("Stopped system monitoring")

    def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the system.

        Returns:
            Dictionary containing health status
        """
        self.last_check_time = time.time()
        self.warnings = []
        self.errors = []
        
        # Get resource usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Check against thresholds
        if cpu_percent > self.thresholds['cpu_percent']:
            self.warnings.append(f"High CPU usage: {cpu_percent}%")
        
        if memory.percent > self.thresholds['memory_percent']:
            self.warnings.append(f"High memory usage: {memory.percent}%")
        
        if disk.percent > self.thresholds['disk_percent']:
            self.warnings.append(f"High disk usage: {disk.percent}%")
        
        # Check engine status
        engine_status = self.engine.get_status()
        
        # Store metrics
        self.metrics = {
            'timestamp': self.last_check_time,
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used': memory.used,
            'memory_total': memory.total,
            'disk_percent': disk.percent,
            'disk_used': disk.used,
            'disk_total': disk.total,
            'engine_status': engine_status,
            'warnings': self.warnings,
            'errors': self.errors
        }
        
        # Log issues
        for warning in self.warnings:
            logger.warning(warning)
        
        for error in self.errors:
            logger.error(error)
        
        health_status = self.get_health_status()

        # Record health metrics
        if self.engine and hasattr(self.engine, 'metrics_collector'):
            self.engine.metrics_collector.record_health_metrics(health_status)

        return health_status

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get the current health status.

        Returns:
            Dictionary containing health status
        """
        # Determine overall health status
        status = "healthy"
        if self.errors:
            status = "critical"
        elif self.warnings:
            status = "warning"
        
        return {
            'status': status,
            'timestamp': self.last_check_time or time.time(),
            'metrics': self.metrics,
            'warnings': self.warnings,
            'errors': self.errors
        }

    def check_component_health(self, component_name: str) -> Dict[str, Any]:
        """
        Check the health of a specific component.

        Args:
            component_name: Name of the component to check

        Returns:
            Dictionary containing component health status
        """
        # This would involve more sophisticated component-specific checks
        # For now, we'll just provide a basic health check
        
        component_status = {
            'name': component_name,
            'status': 'healthy',
            'timestamp': time.time(),
            'warnings': [],
            'errors': []
        }
        
        # Check engine components
        if component_name == 'engine':
            engine_status = self.engine.get_status()
            component_status['details'] = engine_status
            
            # Check if engine is running
            if not engine_status.get('running', False):
                component_status['warnings'].append("Engine is not running")
                component_status['status'] = 'warning'
        
        # Add more component-specific checks as needed
        
        return component_status

    def diagnose_issue(self, issue_description: str) -> Dict[str, Any]:
        """
        Diagnose a reported issue.

        Args:
            issue_description: Description of the issue

        Returns:
            Dictionary containing diagnosis results
        """
        # This would involve more sophisticated diagnosis logic
        # For now, we'll just provide a basic diagnosis
        
        diagnosis = {
            'issue': issue_description,
            'timestamp': time.time(),
            'possible_causes': [],
            'recommended_actions': []
        }
        
        # Analyze the issue description
        if 'memory' in issue_description.lower():
            diagnosis['possible_causes'].append("High memory usage")
            diagnosis['recommended_actions'].append("Check for memory leaks")
            diagnosis['recommended_actions'].append("Increase available memory")
        
        elif 'cpu' in issue_description.lower():
            diagnosis['possible_causes'].append("High CPU usage")
            diagnosis['recommended_actions'].append("Optimize CPU-intensive operations")
            diagnosis['recommended_actions'].append("Check for runaway processes")
        
        elif 'disk' in issue_description.lower():
            diagnosis['possible_causes'].append("Disk space issues")
            diagnosis['recommended_actions'].append("Free up disk space")
            diagnosis['recommended_actions'].append("Check for large temporary files")
        
        # If no specific diagnosis, provide general recommendations
        if not diagnosis['possible_causes']:
            diagnosis['possible_causes'].append("Unknown issue")
            diagnosis['recommended_actions'].append("Check system logs")
            diagnosis['recommended_actions'].append("Monitor system resources")
            diagnosis['recommended_actions'].append("Restart the affected component")
        
        return diagnosis

    def generate_health_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive health report.

        Returns:
            Dictionary containing the health report
        """
        # Ensure we have up-to-date metrics
        if not self.last_check_time or (time.time() - self.last_check_time) > 60:
            self.check_health()
        
        # Generate the report
        report = {
            'timestamp': time.time(),
            'system_health': self.get_health_status(),
            'components': {},
            'recommendations': []
        }
        
        # Check key components
        components = ['engine', 'meta_agent', 'coordinator', 'router']
        for component in components:
            report['components'][component] = self.check_component_health(component)
        
        # Generate recommendations
        if self.warnings or self.errors:
            for warning in self.warnings:
                diagnosis = self.diagnose_issue(warning)
                report['recommendations'].extend(diagnosis['recommended_actions'])
            
            for error in self.errors:
                diagnosis = self.diagnose_issue(error)
                report['recommendations'].extend(diagnosis['recommended_actions'])
        
        # Remove duplicate recommendations
        report['recommendations'] = list(set(report['recommendations']))
        
        return report

    def export_metrics(self, output_format: str = 'json', file_path: Optional[str] = None) -> Union[str, Dict[str, Any]]:
        """
        Export metrics in the specified format.

        Args:
            output_format: Format to export metrics in ('json', 'csv', or 'text')
            file_path: Path to save the metrics to (optional)

        Returns:
            Exported metrics as a string or dictionary
        """
        # Ensure we have up-to-date metrics
        if not self.last_check_time or (time.time() - self.last_check_time) > 60:
            self.check_health()
        
        result = None
        
        if output_format == 'json':
            import json
            result = json.dumps(self.metrics, indent=2)
        
        elif output_format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Metric', 'Value'])
            
            # Write metrics
            for key, value in self.metrics.items():
                if key not in ['warnings', 'errors', 'engine_status']:
                    writer.writerow([key, value])
            
            result = output.getvalue()
            output.close()
        
        elif output_format == 'text':
            result = "Triangulum System Health Report\n"
            result += "=" * 30 + "\n"
            result += f"Timestamp: {time.ctime(self.metrics['timestamp'])}\n"
            result += "\nResource Usage:\n"
            result += f"  CPU: {self.metrics['cpu_percent']}%\n"
            result += f"  Memory: {self.metrics['memory_percent']}% ({self.metrics['memory_used'] / (1024 * 1024):.1f} MB / {self.metrics['memory_total'] / (1024 * 1024):.1f} MB)\n"
            result += f"  Disk: {self.metrics['disk_percent']}% ({self.metrics['disk_used'] / (1024 * 1024 * 1024):.1f} GB / {self.metrics['disk_total'] / (1024 * 1024 * 1024):.1f} GB)\n"
            
            if self.warnings:
                result += "\nWarnings:\n"
                for warning in self.warnings:
                    result += f"  - {warning}\n"
            
            if self.errors:
                result += "\nErrors:\n"
                for error in self.errors:
                    result += f"  - {error}\n"
        
        # Save to file if specified
        if file_path and result:
            output_path = Path(file_path)
            # Ensure parent directory exists
            if not self.fs_cache.exists(str(output_path.parent)):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self.fs_cache.invalidate(str(output_path.parent))
            elif not self.fs_cache.is_dir(str(output_path.parent)):
                logger.warning(f"Parent path for {output_path} exists but is not a directory. Attempting mkdir.")
                output_path.parent.mkdir(parents=True, exist_ok=True) # May fail
                self.fs_cache.invalidate(str(output_path.parent))

            atomic_write(str(output_path), result.encode('utf-8')) # Result is already a string
            self.fs_cache.invalidate(str(output_path))
            logger.info(f"Exported metrics to {output_path} using atomic_write")
        
        return result if result else self.metrics
