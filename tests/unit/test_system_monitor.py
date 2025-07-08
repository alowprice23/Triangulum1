"""
Unit tests for the SystemMonitor class.
"""

import unittest
import time
import json
from unittest.mock import patch, MagicMock

from triangulum_lx.monitoring.system_monitor import SystemMonitor

class TestSystemMonitor(unittest.TestCase):
    """Tests for the SystemMonitor class."""

    def setUp(self):
        """Set up test environment."""
        self.mock_engine = MagicMock()
        self.mock_engine.get_status.return_value = {
            'session_id': 'test_session',
            'running': True,
            'state': {'health': 'good'}
        }
        self.monitor = SystemMonitor(self.mock_engine)

    def test_initialization(self):
        """Test initialization of the monitor."""
        self.assertIsInstance(self.monitor, SystemMonitor)
        self.assertEqual(self.monitor.engine, self.mock_engine)
        self.assertEqual(self.monitor.warnings, [])
        self.assertEqual(self.monitor.errors, [])
        self.assertFalse(self.monitor.is_monitoring)
        self.assertIsNone(self.monitor.last_check_time)

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_check_health(self, mock_disk, mock_memory, mock_cpu):
        """Test checking system health."""
        # Mock the psutil functions
        mock_cpu.return_value = 50.0
        
        mock_memory_obj = MagicMock()
        mock_memory_obj.percent = 60.0
        mock_memory_obj.used = 8 * 1024 * 1024 * 1024  # 8GB
        mock_memory_obj.total = 16 * 1024 * 1024 * 1024  # 16GB
        mock_memory.return_value = mock_memory_obj
        
        mock_disk_obj = MagicMock()
        mock_disk_obj.percent = 70.0
        mock_disk_obj.used = 500 * 1024 * 1024 * 1024  # 500GB
        mock_disk_obj.total = 1000 * 1024 * 1024 * 1024  # 1TB
        mock_disk.return_value = mock_disk_obj
        
        # Check health
        health = self.monitor.check_health()
        
        # Verify the result
        self.assertEqual(health['status'], 'healthy')
        self.assertIn('metrics', health)
        self.assertEqual(health['metrics']['cpu_percent'], 50.0)
        self.assertEqual(health['metrics']['memory_percent'], 60.0)
        self.assertEqual(health['metrics']['disk_percent'], 70.0)
        self.assertEqual(len(health['warnings']), 0)
        self.assertEqual(len(health['errors']), 0)
        
        # Now test with high resource usage to trigger warnings
        mock_cpu.return_value = 95.0
        mock_memory_obj.percent = 90.0
        mock_disk_obj.percent = 95.0
        
        # Check health again
        health = self.monitor.check_health()
        
        # Verify warnings were generated
        self.assertEqual(health['status'], 'warning')
        self.assertGreater(len(health['warnings']), 0)
        self.assertIn('High CPU usage', health['warnings'][0])

    @patch('threading.Thread')
    def test_start_stop_monitoring(self, mock_thread):
        """Test starting and stopping monitoring."""
        # Start monitoring
        self.monitor.start_monitoring(interval=10)
        
        # Verify monitoring started
        self.assertTrue(self.monitor.is_monitoring)
        self.assertEqual(self.monitor.monitoring_interval, 10)
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        
        # Verify monitoring stopped
        self.assertFalse(self.monitor.is_monitoring)

    def test_get_health_status(self):
        """Test getting health status."""
        # Set up some test data
        self.monitor.last_check_time = time.time()
        self.monitor.metrics = {
            'cpu_percent': 50.0,
            'memory_percent': 60.0,
            'disk_percent': 70.0
        }
        
        # Get health status
        status = self.monitor.get_health_status()
        
        # Verify the result
        self.assertEqual(status['status'], 'healthy')
        self.assertIn('timestamp', status)
        self.assertIn('metrics', status)
        self.assertEqual(len(status['warnings']), 0)
        self.assertEqual(len(status['errors']), 0)
        
        # Now add some warnings and errors
        self.monitor.warnings = ['Warning 1', 'Warning 2']
        self.monitor.errors = ['Error 1']
        
        # Get health status again
        status = self.monitor.get_health_status()
        
        # Verify warnings and errors
        self.assertEqual(status['status'], 'critical')
        self.assertEqual(len(status['warnings']), 2)
        self.assertEqual(len(status['errors']), 1)

    def test_check_component_health(self):
        """Test checking component health."""
        # Check engine health
        health = self.monitor.check_component_health('engine')
        
        # Verify the result
        self.assertEqual(health['name'], 'engine')
        self.assertEqual(health['status'], 'healthy')
        self.assertIn('details', health)
        
        # Test with a non-running engine
        self.mock_engine.get_status.return_value['running'] = False
        
        # Check engine health again
        health = self.monitor.check_component_health('engine')
        
        # Verify warning was generated
        self.assertEqual(health['status'], 'warning')
        self.assertGreater(len(health['warnings']), 0)

    def test_diagnose_issue(self):
        """Test diagnosing an issue."""
        # Diagnose a memory issue
        diagnosis = self.monitor.diagnose_issue('High memory usage detected')
        
        # Verify the diagnosis
        self.assertIn('issue', diagnosis)
        self.assertIn('timestamp', diagnosis)
        self.assertIn('possible_causes', diagnosis)
        self.assertIn('recommended_actions', diagnosis)
        self.assertGreater(len(diagnosis['possible_causes']), 0)
        self.assertGreater(len(diagnosis['recommended_actions']), 0)
        
        # Check that memory-specific recommendations were given
        self.assertIn('memory', str(diagnosis['possible_causes']).lower())

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_generate_health_report(self, mock_disk, mock_memory, mock_cpu):
        """Test generating a health report."""
        # Mock the psutil functions
        mock_cpu.return_value = 50.0
        
        mock_memory_obj = MagicMock()
        mock_memory_obj.percent = 60.0
        mock_memory_obj.used = 8 * 1024 * 1024 * 1024  # 8GB
        mock_memory_obj.total = 16 * 1024 * 1024 * 1024  # 16GB
        mock_memory.return_value = mock_memory_obj
        
        mock_disk_obj = MagicMock()
        mock_disk_obj.percent = 70.0
        mock_disk_obj.used = 500 * 1024 * 1024 * 1024  # 500GB
        mock_disk_obj.total = 1000 * 1024 * 1024 * 1024  # 1TB
        mock_disk.return_value = mock_disk_obj
        
        # Generate a report
        report = self.monitor.generate_health_report()
        
        # Verify the report
        self.assertIn('timestamp', report)
        self.assertIn('system_health', report)
        self.assertIn('components', report)
        self.assertIn('recommendations', report)
        self.assertIn('engine', report['components'])

    @patch('builtins.open')
    @patch('json.dumps')
    def test_export_metrics(self, mock_json_dumps, mock_open):
        """Test exporting metrics."""
        # Set up test metrics
        self.monitor.metrics = {
            'timestamp': time.time(),
            'cpu_percent': 50.0,
            'memory_percent': 60.0,
            'disk_percent': 70.0,
            'warnings': [],
            'errors': []
        }
        mock_json_dumps.return_value = '{"metrics": "test"}'
        
        # Export metrics to JSON
        result = self.monitor.export_metrics(output_format='json')
        
        # Verify JSON export
        mock_json_dumps.assert_called_once()
        self.assertEqual(result, '{"metrics": "test"}')
        
        # Export metrics to a file
        self.monitor.export_metrics(output_format='json', file_path='test.json')
        
        # Verify file export
        mock_open.assert_called_once_with('test.json', 'w')
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with('{"metrics": "test"}')

if __name__ == "__main__":
    unittest.main()
