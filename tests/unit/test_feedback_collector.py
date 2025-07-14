"""
Unit tests for the FeedbackCollector class.
"""

import os
import tempfile
import unittest
import json
import sqlite3
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timedelta

from triangulum_lx.human.feedback import FeedbackCollector

class TestFeedbackCollector(unittest.TestCase):
    """Tests for the FeedbackCollector class."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary database file
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp()
        self.collector = FeedbackCollector(db_path=self.temp_db_path)

    def tearDown(self):
        """Clean up test environment."""
        # Close and remove the temporary database file
        os.close(self.temp_db_fd)
        os.unlink(self.temp_db_path)

    def test_initialization(self):
        """Test initialization of the collector."""
        self.assertIsInstance(self.collector, FeedbackCollector)
        self.assertEqual(self.collector.db_path, self.temp_db_path)
        
        # Check that the database was created
        self.assertTrue(os.path.exists(self.temp_db_path))
        
        # Check that the tables were created
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()
        
        # Check feedback table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='feedback'")
        self.assertIsNotNone(cursor.fetchone())
        
        # Check actions table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='actions'")
        self.assertIsNotNone(cursor.fetchone())
        
        conn.close()

    def test_record_feedback(self):
        """Test recording feedback."""
        # Record feedback
        feedback_id = self.collector.record_feedback(
            content="Test feedback",
            feedback_type="bug",
            source="test",
            session_id="test_session",
            rating=5,
            tags=["test", "bug"]
        )
        
        # Check that a feedback ID was returned
        self.assertIsNotNone(feedback_id)
        
        # Check that the feedback was stored in the database
        conn = sqlite3.connect(self.temp_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row['content'], "Test feedback")
        self.assertEqual(row['feedback_type'], "bug")
        self.assertEqual(row['source'], "test")
        self.assertEqual(row['session_id'], "test_session")
        self.assertEqual(row['rating'], 5)
        self.assertEqual(json.loads(row['tags']), ["test", "bug"])
        
        conn.close()

    def test_get_feedback(self):
        """Test getting a specific feedback entry."""
        # Record feedback
        feedback_id = self.collector.record_feedback(
            content="Test feedback",
            feedback_type="bug"
        )
        
        # Record an action for this feedback
        action_id = self.collector.record_action(
            feedback_id=feedback_id,
            action_type="fix",
            description="Fixed the bug"
        )
        
        # Get the feedback
        feedback = self.collector.get_feedback(feedback_id)
        
        # Check that the feedback was retrieved
        self.assertIsNotNone(feedback)
        self.assertEqual(feedback['id'], feedback_id)
        self.assertEqual(feedback['content'], "Test feedback")
        self.assertEqual(feedback['feedback_type'], "bug")
        
        # Check that the action was included
        self.assertIn('actions', feedback)
        self.assertEqual(len(feedback['actions']), 1)
        self.assertEqual(feedback['actions'][0]['id'], action_id)
        self.assertEqual(feedback['actions'][0]['action_type'], "fix")
        self.assertEqual(feedback['actions'][0]['description'], "Fixed the bug")

    def test_get_all_feedback(self):
        """Test getting all feedback entries."""
        # Record multiple feedback entries
        feedback_id1 = self.collector.record_feedback(
            content="Feedback 1",
            feedback_type="bug"
        )
        
        feedback_id2 = self.collector.record_feedback(
            content="Feedback 2",
            feedback_type="feature"
        )
        
        feedback_id3 = self.collector.record_feedback(
            content="Feedback 3",
            feedback_type="bug",
            source="test2"
        )
        
        # Get all feedback
        all_feedback = self.collector.get_all_feedback()
        
        # Check that all feedback entries were retrieved
        self.assertEqual(len(all_feedback), 3)
        
        # Get feedback of a specific type
        bug_feedback = self.collector.get_all_feedback(feedback_type="bug")
        
        # Check that only bug feedback was retrieved
        self.assertEqual(len(bug_feedback), 2)
        self.assertEqual(bug_feedback[0]['feedback_type'], "bug")
        self.assertEqual(bug_feedback[1]['feedback_type'], "bug")
        
        # Get feedback from a specific source
        source_feedback = self.collector.get_all_feedback(source="test2")
        
        # Check that only feedback from the specified source was retrieved
        self.assertEqual(len(source_feedback), 1)
        self.assertEqual(source_feedback[0]['source'], "test2")

    def test_mark_as_processed(self):
        """Test marking feedback as processed."""
        # Record feedback
        feedback_id = self.collector.record_feedback(
            content="Test feedback",
            feedback_type="bug"
        )
        
        # Mark as processed
        success = self.collector.mark_as_processed(feedback_id)
        
        # Check that the operation was successful
        self.assertTrue(success)
        
        # Check that the feedback was marked as processed
        feedback = self.collector.get_feedback(feedback_id)
        self.assertEqual(feedback['processed'], 1)
        
        # Mark as unprocessed
        success = self.collector.mark_as_processed(feedback_id, processed=False)
        
        # Check that the operation was successful
        self.assertTrue(success)
        
        # Check that the feedback was marked as unprocessed
        feedback = self.collector.get_feedback(feedback_id)
        self.assertEqual(feedback['processed'], 0)

    def test_record_action(self):
        """Test recording an action."""
        # Record feedback
        feedback_id = self.collector.record_feedback(
            content="Test feedback",
            feedback_type="bug"
        )
        
        # Record an action
        action_id = self.collector.record_action(
            feedback_id=feedback_id,
            action_type="fix",
            description="Fixed the bug",
            result="Bug fixed successfully"
        )
        
        # Check that an action ID was returned
        self.assertIsNotNone(action_id)
        
        # Check that the action was stored in the database
        conn = sqlite3.connect(self.temp_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM actions WHERE id = ?", (action_id,))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row['feedback_id'], feedback_id)
        self.assertEqual(row['action_type'], "fix")
        self.assertEqual(row['description'], "Fixed the bug")
        self.assertEqual(row['result'], "Bug fixed successfully")
        
        conn.close()

    def test_analyze_feedback(self):
        """Test analyzing feedback."""
        # Record multiple feedback entries
        self.collector.record_feedback(
            content="Bug in login",
            feedback_type="bug",
            rating=2,
            tags=["login", "critical"]
        )
        
        self.collector.record_feedback(
            content="Feature request: Dark mode",
            feedback_type="feature",
            rating=4,
            tags=["ui", "dark-mode"]
        )
        
        self.collector.record_feedback(
            content="Another bug in login",
            feedback_type="bug",
            rating=3,
            tags=["login", "medium"]
        )
        
        # Analyze all feedback
        analysis = self.collector.analyze_feedback()
        
        # Check the analysis results
        self.assertEqual(analysis['total_count'], 3)
        self.assertEqual(len(analysis['by_type']), 2)
        self.assertEqual(analysis['by_type']['bug'], 2)
        self.assertEqual(analysis['by_type']['feature'], 1)
        self.assertIsNotNone(analysis['average_rating'])
        self.assertEqual(analysis['processed_count'], 0)
        self.assertEqual(analysis['unprocessed_count'], 3)
        self.assertEqual(len(analysis['common_tags']), 5)
        self.assertEqual(analysis['common_tags']['login'], 2)
        
        # Analyze bug feedback only
        bug_analysis = self.collector.analyze_feedback(feedback_type="bug")
        
        # Check the bug analysis results
        self.assertEqual(bug_analysis['total_count'], 2)
        self.assertEqual(bug_analysis['by_type']['bug'], 2)
        self.assertNotIn('feature', bug_analysis['by_type'])

    @patch('json.dump')
    @patch('builtins.open', new_callable=mock_open)
    def test_export_feedback_json(self, mock_file, mock_json_dump):
        """Test exporting feedback to JSON."""
        # Record feedback
        self.collector.record_feedback(
            content="Test feedback",
            feedback_type="bug"
        )
        
        # Export to JSON
        success = self.collector.export_feedback("test.json", format="json")
        
        # Check that the export was successful
        self.assertTrue(success)
        
        # Check that the file was opened for writing
        mock_file.assert_called_once_with("test.json", "w")
        
        # Check that json.dump was called with the feedback data
        mock_json_dump.assert_called_once()

    def test_delete_feedback(self):
        """Test deleting feedback."""
        # Record feedback
        feedback_id = self.collector.record_feedback(
            content="Test feedback",
            feedback_type="bug"
        )
        
        # Record an action for this feedback
        self.collector.record_action(
            feedback_id=feedback_id,
            action_type="fix",
            description="Fixed the bug"
        )
        
        # Delete the feedback
        success = self.collector.delete_feedback(feedback_id)
        
        # Check that the operation was successful
        self.assertTrue(success)
        
        # Check that the feedback was deleted
        feedback = self.collector.get_feedback(feedback_id)
        self.assertIsNone(feedback)
        
        # Check that the associated actions were deleted
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM actions WHERE feedback_id = ?", (feedback_id,))
        count = cursor.fetchone()[0]
        
        self.assertEqual(count, 0)
        
        conn.close()

if __name__ == "__main__":
    unittest.main()
