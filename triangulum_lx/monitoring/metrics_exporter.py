"""
Metrics exporter for Triangulum.

Exports system metrics to external systems for long-term storage and analysis.
"""

import json
import time
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import threading
import socket
import csv
from datetime import datetime

# Setup logging
logger = logging.getLogger("triangulum.metrics_exporter")


class MetricsExporter:
    """
    Base class for metrics exporters.
    
    This provides a common interface for all metrics exporters.
    """
    
    def __init__(self, name: str):
        """
        Initialize the metrics exporter.
        
        Args:
            name: Name of the exporter
        """
        self.name = name
        
    def export(self, metrics: Dict[str, Any]) -> bool:
        """
        Export metrics to the destination.
        
        Args:
            metrics: Dictionary of metrics to export
            
        Returns:
            bool: True if export was successful
        """
        raise NotImplementedError("Subclasses must implement export()")


class FileExporter(MetricsExporter):
    """
    Exports metrics to files on disk.
    
    This exporter writes metrics to JSON files in a specified directory.
    """
    
    def __init__(self, 
                output_dir: Union[str, Path], 
                filename_template: str = "metrics_{timestamp}.json",
                buffer_size: int = 100,
                flush_interval: int = 60):
        """
        Initialize the file exporter.
        
        Args:
            output_dir: Directory to write metrics to
            filename_template: Template for filenames
            buffer_size: How many metrics to buffer before writing
            flush_interval: Seconds between forced flushes
        """
        super().__init__("file")
        self.output_dir = Path(output_dir)
        self.filename_template = filename_template
        self.buffer: List[Dict[str, Any]] = []
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.last_flush = time.time()
        self.lock = threading.RLock()
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Start background thread for timed flushes
        if flush_interval > 0:
            self._start_flush_thread()
    
    def _start_flush_thread(self) -> None:
        """Start a background thread to flush metrics periodically."""
        def flush_loop():
            while True:
                time.sleep(self.flush_interval)
                
                # Check if we need to flush
                with self.lock:
                    if self.buffer and time.time() - self.last_flush >= self.flush_interval:
                        self._flush()
        
        thread = threading.Thread(
            target=flush_loop, 
            daemon=True,
            name="metrics-flush-thread"
        )
        thread.start()
    
    def export(self, metrics: Dict[str, Any]) -> bool:
        """
        Export metrics to file.
        
        Args:
            metrics: Dictionary of metrics to export
            
        Returns:
            bool: True if metrics were successfully exported or buffered
        """
        with self.lock:
            # Add metrics to buffer
            self.buffer.append({
                **metrics,
                "_timestamp": time.time()
            })
            
            # Flush if buffer is full
            if len(self.buffer) >= self.buffer_size:
                return self._flush()
            
        return True
    
    def _flush(self) -> bool:
        """
        Flush buffered metrics to disk.
        
        Returns:
            bool: True if flush was successful
        """
        with self.lock:
            if not self.buffer:
                return True
            
            try:
                # Create filename
                timestamp = int(time.time())
                filename = self.filename_template.format(timestamp=timestamp)
                file_path = self.output_dir / filename
                
                # Write metrics to file
                with open(file_path, 'w') as f:
                    json.dump({
                        "batch_timestamp": timestamp,
                        "metrics_count": len(self.buffer),
                        "metrics": self.buffer
                    }, f, indent=2)
                
                # Clear buffer and update last flush time
                self.buffer = []
                self.last_flush = time.time()
                
                logger.debug(f"Flushed metrics to {file_path}")
                return True
                
            except Exception as e:
                logger.error(f"Error flushing metrics: {e}")
                return False


class PrometheusExporter(MetricsExporter):
    """
    Exports metrics in Prometheus format.
    
    This exporter serves metrics on an HTTP endpoint for Prometheus to scrape.
    """
    
    def __init__(self, 
                port: int = 9090, 
                host: str = "127.0.0.1",
                endpoint: str = "/metrics"):
        """
        Initialize the Prometheus exporter.
        
        Args:
            port: Port to listen on
            host: Host to bind to
            endpoint: Endpoint to serve metrics on
        """
        super().__init__("prometheus")
        self.port = port
        self.host = host
        self.endpoint = endpoint
        self.metrics: Dict[str, Any] = {}
        self.lock = threading.RLock()
        
        # Start HTTP server
        self._start_server()
    
    def _start_server(self) -> None:
        """Start HTTP server to serve metrics."""
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        
        # Define request handler
        class PrometheusHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == self.server.endpoint:
                    # Serve metrics
                    with self.server.exporter.lock:
                        metrics_text = self.server.exporter._format_metrics()
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(metrics_text.encode("utf-8"))
                else:
                    # Not found
                    self.send_response(404)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"Not Found")
                    
            def log_message(self, format, *args):
                # Suppress logging
                pass
        
        # Create server
        server = HTTPServer((self.host, self.port), PrometheusHandler)
        server.endpoint = self.endpoint
        server.exporter = self
        
        # Start server in background thread
        thread = threading.Thread(
            target=server.serve_forever,
            daemon=True,
            name="prometheus-metrics-server"
        )
        thread.start()
        
        logger.info(f"Prometheus metrics server started at http://{self.host}:{self.port}{self.endpoint}")
    
    def export(self, metrics: Dict[str, Any]) -> bool:
        """
        Export metrics to Prometheus format.
        
        Args:
            metrics: Dictionary of metrics to export
            
        Returns:
            bool: True if metrics were successfully exported
        """
        with self.lock:
            # Update metrics
            self.metrics.update(metrics)
            return True
    
    def _format_metrics(self) -> str:
        """
        Format metrics in Prometheus text format.
        
        Returns:
            str: Metrics in Prometheus text format
        """
        lines = []
        
        # Helper function to process metrics recursively
        def process_metric(name, value, labels=None):
            labels_str = ""
            if labels:
                labels_str = "{" + ",".join(f'{k}="{v}"' for k, v in labels.items()) + "}"
            
            if isinstance(value, (int, float)):
                lines.append(f"{name}{labels_str} {value}")
            elif isinstance(value, dict):
                for k, v in value.items():
                    new_labels = dict(labels) if labels else {}
                    if k.isalpha():  # If key can be a label
                        new_labels[k] = v
                    else:  # If key needs to be part of the metric name
                        new_name = f"{name}_{k}"
                        process_metric(new_name, v, new_labels)
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    new_labels = dict(labels) if labels else {}
                    new_labels["index"] = i
                    process_metric(name, v, new_labels)
        
        # Process all metrics
        timestamp = int(time.time() * 1000)
        for name, value in self.metrics.items():
            # Skip special fields
            if name.startswith("_"):
                continue
                
            # Add metric
            process_metric(f"triangulum_{name}", value)
        
        return "\n".join(lines) + "\n"


class CSVExporter(MetricsExporter):
    """
    Exports metrics to CSV files.
    
    This is useful for metrics that need to be analyzed in spreadsheets.
    """
    
    def __init__(self, 
                output_dir: Union[str, Path],
                filename_template: str = "metrics_{date}.csv",
                rotate_daily: bool = True):
        """
        Initialize the CSV exporter.
        
        Args:
            output_dir: Directory to write CSV files to
            filename_template: Template for CSV filenames
            rotate_daily: Whether to create a new file each day
        """
        super().__init__("csv")
        self.output_dir = Path(output_dir)
        self.filename_template = filename_template
        self.rotate_daily = rotate_daily
        self.current_day = datetime.now().date()
        self.current_file = None
        self.lock = threading.RLock()
        self.csv_writer = None
        self.headers = set()
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    def export(self, metrics: Dict[str, Any]) -> bool:
        """
        Export metrics to CSV.
        
        Args:
            metrics: Dictionary of metrics to export
            
        Returns:
            bool: True if metrics were successfully exported
        """
        with self.lock:
            try:
                # Check if we need to rotate file
                today = datetime.now().date()
                if self.rotate_daily and today != self.current_day:
                    self._close_file()
                    self.current_day = today
                
                # Open file if needed
                if not self.current_file:
                    self._open_file()
                
                # Flatten metrics
                flat_metrics = self._flatten_metrics(metrics)
                
                # Update headers
                new_headers = set(flat_metrics.keys())
                if new_headers - self.headers:
                    # We have new headers, need to rewrite the file
                    self.headers.update(new_headers)
                    self._rewrite_headers()
                
                # Write metrics row
                row = {}
                for header in self.headers:
                    row[header] = flat_metrics.get(header, "")
                
                self.csv_writer.writerow(row)
                self.current_file.flush()
                
                return True
                
            except Exception as e:
                logger.error(f"Error exporting metrics to CSV: {e}")
                return False
    
    def _flatten_metrics(self, metrics: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """
        Flatten nested metrics for CSV export.
        
        Args:
            metrics: Dictionary of metrics to flatten
            prefix: Prefix for keys in the flattened dictionary
            
        Returns:
            Dict of flattened metrics
        """
        result = {}
        
        for key, value in metrics.items():
            full_key = f"{prefix}{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recursively flatten dictionaries
                nested = self._flatten_metrics(value, f"{full_key}_")
                result.update(nested)
            elif isinstance(value, (list, tuple)):
                # For lists, create keys with indices
                for i, item in enumerate(value):
                    if isinstance(item, (dict, list, tuple)):
                        # Recursively flatten complex items
                        nested = self._flatten_metrics({f"{i}": item}, f"{full_key}_")
                        result.update(nested)
                    else:
                        # Simple items
                        result[f"{full_key}_{i}"] = item
            else:
                # Simple values
                result[full_key] = value
        
        return result
    
    def _open_file(self) -> None:
        """Open a new CSV file for writing."""
        # Generate filename
        date_str = self.current_day.strftime("%Y%m%d")
        filename = self.filename_template.format(date=date_str)
        file_path = self.output_dir / filename
        
        # Check if file exists
        file_exists = file_path.exists()
        
        # Open file
        self.current_file = open(file_path, 'a', newline='')
        self.csv_writer = csv.DictWriter(self.current_file, fieldnames=[])
        
        # If new file, write headers
        if not file_exists:
            self.headers = {"timestamp"}  # Always include timestamp
            self._rewrite_headers()
    
    def _rewrite_headers(self) -> None:
        """Rewrite headers in the current CSV file."""
        # Set writer fieldnames
        self.csv_writer.fieldnames = sorted(self.headers)
        
        # Write header row
        if self.current_file.tell() == 0:  # Only if at start of file
            self.csv_writer.writeheader()
    
    def _close_file(self) -> None:
        """Close the current CSV file."""
        if self.current_file:
            self.current_file.close()
            self.current_file = None
            self.csv_writer = None


# Factory function to create an exporter
def create_exporter(export_type: str, **kwargs) -> MetricsExporter:
    """
    Create a metrics exporter.
    
    Args:
        export_type: Type of exporter to create
        **kwargs: Additional arguments for the exporter
        
    Returns:
        MetricsExporter instance
    """
    if export_type == "file":
        return FileExporter(**kwargs)
    elif export_type == "prometheus":
        return PrometheusExporter(**kwargs)
    elif export_type == "csv":
        return CSVExporter(**kwargs)
    else:
        raise ValueError(f"Unknown exporter type: {export_type}")


class MultiExporter(MetricsExporter):
    """
    Exports metrics to multiple destinations.
    
    This allows metrics to be sent to multiple exporters simultaneously.
    """
    
    def __init__(self, exporters: List[MetricsExporter]):
        """
        Initialize the multi-exporter.
        
        Args:
            exporters: List of exporters to use
        """
        super().__init__("multi")
        self.exporters = exporters
    
    def export(self, metrics: Dict[str, Any]) -> bool:
        """
        Export metrics to all configured exporters.
        
        Args:
            metrics: Dictionary of metrics to export
            
        Returns:
            bool: True if all exports were successful
        """
        success = True
        for exporter in self.exporters:
            try:
                result = exporter.export(metrics)
                if not result:
                    success = False
            except Exception as e:
                logger.error(f"Error exporting to {exporter.name}: {e}")
                success = False
        
        return success
    
    def add_exporter(self, exporter: MetricsExporter) -> None:
        """
        Add an exporter to the multi-exporter.
        
        Args:
            exporter: Exporter to add
        """
        self.exporters.append(exporter)
