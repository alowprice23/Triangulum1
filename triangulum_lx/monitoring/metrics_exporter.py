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

from triangulum_lx.tooling.fs_ops import atomic_write
from triangulum_lx.core.fs_state import FileSystemStateCache
# Path is already imported from pathlib

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
                flush_interval: int = 60,
                fs_cache: Optional[FileSystemStateCache] = None):
        """
        Initialize the file exporter.
        
        Args:
            output_dir: Directory to write metrics to
            filename_template: Template for filenames
            buffer_size: How many metrics to buffer before writing
            flush_interval: Seconds between forced flushes
            fs_cache: Optional FileSystemStateCache instance.
        """
        super().__init__("file")
        self.output_dir = Path(output_dir)
        self.filename_template = filename_template
        self.buffer: List[Dict[str, Any]] = []
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.last_flush = time.time()
        self.lock = threading.RLock()
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()
        
        # Create output directory if it doesn't exist
        if not self.fs_cache.exists(str(self.output_dir)):
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.fs_cache.invalidate(str(self.output_dir))
        elif not self.fs_cache.is_dir(str(self.output_dir)):
            logger.warning(f"Output dir {self.output_dir} exists but is not a directory. Attempting to create.")
            self.output_dir.mkdir(parents=True, exist_ok=True) # May fail
            self.fs_cache.invalidate(str(self.output_dir))
        
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
                data_to_write = {
                    "batch_timestamp": timestamp,
                    "metrics_count": len(self.buffer),
                    "metrics": self.buffer
                }
                content_str = json.dumps(data_to_write, indent=2)
                atomic_write(str(file_path), content_str.encode('utf-8'))
                self.fs_cache.invalidate(str(file_path))
                
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
                rotate_daily: bool = True,
                fs_cache: Optional[FileSystemStateCache] = None):
        """
        Initialize the CSV exporter.
        
        Args:
            output_dir: Directory to write CSV files to
            filename_template: Template for CSV filenames
            rotate_daily: Whether to create a new file each day
            fs_cache: Optional FileSystemStateCache instance.
        """
        super().__init__("csv")
        self.output_dir = Path(output_dir)
        self.filename_template = filename_template
        self.rotate_daily = rotate_daily
        self.current_day = datetime.now().date()
        self.current_file_path_str: Optional[str] = None # Store path for invalidation
        self.lock = threading.RLock()
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()
        
        # In-memory buffer for CSV rows
        self.csv_rows: List[Dict[str, Any]] = []
        self.headers: List[str] = ["timestamp"] # Ensure timestamp is always first if possible
        self.headers_written_to_current_file = False

        # Create output directory if it doesn't exist
        if not self.fs_cache.exists(str(self.output_dir)):
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.fs_cache.invalidate(str(self.output_dir))
        elif not self.fs_cache.is_dir(str(self.output_dir)):
            logger.warning(f"Output dir {self.output_dir} exists but is not a directory. Attempting to create.")
            self.output_dir.mkdir(parents=True, exist_ok=True) # May fail
            self.fs_cache.invalidate(str(self.output_dir))
    
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
                # Add a timestamp to the metrics
                flat_metrics = self._flatten_metrics(metrics)
                flat_metrics["timestamp"] = datetime.now().isoformat()

                # Update headers: ensure all keys from flat_metrics are in self.headers
                # and maintain order if possible (new keys added at the end for simplicity here)
                new_keys_found = False
                for key in flat_metrics.keys():
                    if key not in self.headers:
                        self.headers.append(key)
                        new_keys_found = True
                
                self.csv_rows.append(flat_metrics)
                
                # Simple periodic flush or buffer size based flush
                # A more robust solution might use a background thread like FileExporter
                if len(self.csv_rows) >= 10 or new_keys_found: # Flush if buffer full or headers changed
                    self._flush_csv_buffer()
                
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

    def _get_current_file_path(self) -> Path:
        """Determines the current CSV file path based on rotation policy."""
        date_str = self.current_day.strftime("%Y%m%d")
        filename = self.filename_template.format(date=date_str)
        return self.output_dir / filename

    def _flush_csv_buffer(self) -> bool:
        """Flushes the in-memory CSV row buffer to disk using atomic_write."""
        if not self.csv_rows:
            return True

        file_path = self._get_current_file_path()
        self.current_file_path_str = str(file_path) # Store for potential later use if needed

        output_buffer = io.StringIO()
        # Ensure headers are sorted for consistent column order if they changed.
        # If self.headers is a list and we append, it preserves insertion order.
        # For DictWriter, fieldnames order matters.
        sorted_headers = sorted(list(set(self.headers))) # Use set to ensure uniqueness, then sort

        writer = csv.DictWriter(output_buffer, fieldnames=sorted_headers, lineterminator='\n')
        
        existing_content_lines = []
        file_existed_prior = False

        if self.fs_cache.exists(str(file_path)):
            if Path(file_path).exists(): # Double check FS if cache says yes
                file_existed_prior = True
                try:
                    with open(file_path, 'r', newline='', encoding='utf-8') as f_read:
                        # Naively skip header if present; a more robust way would be to check content
                        first_line = f_read.readline()
                        if first_line.strip() == ",".join(sorted_headers): # Basic header check
                            existing_content_lines.extend(f_read.readlines())
                        else:
                            existing_content_lines.append(first_line) # Put it back if not header
                            existing_content_lines.extend(f_read.readlines())
                except Exception as e:
                    logger.error(f"Error reading existing CSV {file_path} for append: {e}")
                    # Proceed as if writing a new file if read fails
                    file_existed_prior = False
            else: # Cache was stale, file doesn't exist
                self.fs_cache.invalidate(str(file_path))
                file_existed_prior = False


        if not file_existed_prior or not existing_content_lines: # Write header if new file or empty
            writer.writeheader()
            self.headers_written_to_current_file = True # Mark that we've written headers for this conceptual "file stream"

        # Write existing content if any (from a previous atomic_write of this same daily file)
        # This part is tricky; if existing_content_lines were read, they are already strings.
        # We need to ensure they are written correctly before new rows.
        # For simplicity now, if file_existed_prior, we are re-writing the whole thing
        # including old data + new data. This is the "read all, append, atomic_write all" pattern.

        if file_existed_prior: # Rewrite header if file existed, then all old rows, then new rows
            output_buffer = io.StringIO() # Restart buffer
            writer = csv.DictWriter(output_buffer, fieldnames=sorted_headers, lineterminator='\n')
            writer.writeheader()
            # This requires parsing existing_content_lines back into dicts to use DictWriter,
            # or just writing them as strings. Simpler to just write new rows if appending to string buffer.
            # For true append-like behavior with DictWriter and atomic_write, it's complex.

            # Let's simplify: if file existed, read its rows, append new rows, then write all.
            all_rows_to_write = []
            if file_existed_prior:
                try:
                    # Re-read as dicts to merge properly
                    with open(file_path, 'r', newline='', encoding='utf-8') as f_read_dict:
                        reader = csv.DictReader(f_read_dict)
                        # Update headers from existing file if they are more comprehensive
                        if reader.fieldnames:
                            for header_key in reader.fieldnames:
                                if header_key not in self.headers:
                                    self.headers.append(header_key)
                            sorted_headers = sorted(list(set(self.headers))) # Re-sort
                        all_rows_to_write.extend(list(reader))
                except Exception as e:
                    logger.error(f"Could not properly parse existing CSV {file_path} to merge rows: {e}")
                    # Fallback: just write new rows, potentially losing old if format changed
                    all_rows_to_write = [] # This means old data might be lost if read fails.

            all_rows_to_write.extend(self.csv_rows) # Add the new rows from buffer

            # Re-initialize buffer and writer with potentially updated sorted_headers
            output_buffer = io.StringIO()
            writer = csv.DictWriter(output_buffer, fieldnames=sorted_headers, lineterminator='\n')
            writer.writeheader()
            writer.writerows(all_rows_to_write)

        else: # New file, just write buffered rows
            writer.writerows(self.csv_rows)

        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            self.fs_cache.invalidate(str(Path(file_path).parent))

            atomic_write(str(file_path), output_buffer.getvalue().encode('utf-8'))
            self.fs_cache.invalidate(str(file_path))
            self.csv_rows.clear()
            self.headers_written_to_current_file = True # Since we wrote, headers are conceptually there.
            logger.debug(f"Flushed {len(self.csv_rows)} CSV rows to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error flushing CSV buffer to {file_path}: {e}")
            return False
        finally:
            output_buffer.close()

    # def _open_file(self) -> None: ... (Commented out / To be removed)
    # def _rewrite_headers(self) -> None: ... (Commented out / To be removed)
    # def _close_file(self) -> None: ... (Commented out / To be removed)


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
