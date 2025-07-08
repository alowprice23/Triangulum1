"""
Feedback Collector - Collects and manages feedback from human users.

This module provides functionality for collecting, storing, and analyzing feedback
from human users to improve the Triangulum system.
"""

import logging
import os
import time
import json
import sqlite3
from enum import Enum, auto
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    """Types of feedback."""
    BUG = auto()
    FEATURE_REQUEST = auto()
    PERFORMANCE = auto()
    USABILITY = auto()
    DOCUMENTATION = auto()
    OTHER = auto()

class FeedbackItem:
    """Represents a feedback item."""
    
    def __init__(self, feedback_type: FeedbackType, rating: Optional[int] = None, 
                comment: Optional[str] = None, timestamp: Optional[float] = None,
                bug_id: Optional[str] = None, tags: Optional[List[str]] = None):
        self.feedback_type = feedback_type
        self.rating = rating
        self.comment = comment
        self.timestamp = timestamp or time.time()
        self.bug_id = bug_id
        self.tags = tags or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "feedback_type": self.feedback_type.name,
            "rating": self.rating,
            "comment": self.comment,
            "timestamp": self.timestamp,
            "bug_id": self.bug_id,
            "tags": self.tags
        }

class FeedbackManager:
    """Manages feedback collection and storage."""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or os.path.join("triangulum_data", "feedback")
        os.makedirs(self.storage_path, exist_ok=True)
    
    def add_feedback(self, feedback: FeedbackItem) -> bool:
        """Add a feedback item."""
        try:
            # Create filename
            timestamp_str = datetime.fromtimestamp(feedback.timestamp).strftime("%Y%m%d_%H%M%S")
            filename = f"feedback_{timestamp_str}.json"
            
            # Save to file
            with open(os.path.join(self.storage_path, filename), 'w') as f:
                json.dump(feedback.to_dict(), f, indent=2)
            
            logger.info(f"Saved feedback to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save feedback: {e}")
            return False
    
    def get_all_feedback(self) -> List[Dict[str, Any]]:
        """Get all feedback items."""
        feedback_files = [f for f in os.listdir(self.storage_path) if f.endswith('.json')]
        
        all_feedback = []
        for file in feedback_files:
            try:
                with open(os.path.join(self.storage_path, file), 'r') as f:
                    feedback = json.load(f)
                    all_feedback.append(feedback)
            except Exception as e:
                logger.error(f"Error reading feedback file {file}: {e}")
        
        return all_feedback

class FeedbackCollector:
    """
    Collects and manages feedback from human users.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the FeedbackCollector.

        Args:
            db_path: Path to the SQLite database file (optional)
        """
        self.db_path = db_path or os.path.join("triangulum_data", "feedback.db")
        self._ensure_db_exists()
        logger.info("FeedbackCollector initialized")

    def _ensure_db_exists(self) -> None:
        """Ensure the feedback database exists and has the correct schema."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            session_id TEXT,
            source TEXT,
            feedback_type TEXT NOT NULL,
            content TEXT NOT NULL,
            rating INTEGER,
            tags TEXT,
            processed INTEGER DEFAULT 0
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feedback_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            action_type TEXT NOT NULL,
            description TEXT NOT NULL,
            result TEXT,
            FOREIGN KEY (feedback_id) REFERENCES feedback (id)
        )
        ''')
        
        conn.commit()
        conn.close()

    def record_feedback(self, content: str, feedback_type: str = "general", 
                        source: Optional[str] = None, session_id: Optional[str] = None,
                        rating: Optional[int] = None, tags: Optional[List[str]] = None) -> int:
        """
        Record feedback from a user.

        Args:
            content: The feedback content
            feedback_type: Type of feedback (general, bug, feature, etc.)
            source: Source of the feedback (UI, API, etc.)
            session_id: ID of the session the feedback is related to
            rating: Numerical rating (e.g., 1-5)
            tags: List of tags to categorize the feedback

        Returns:
            ID of the newly created feedback entry
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        tags_json = json.dumps(tags) if tags else None
        
        cursor.execute(
            "INSERT INTO feedback (timestamp, session_id, source, feedback_type, content, rating, tags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (timestamp, session_id, source, feedback_type, content, rating, tags_json)
        )
        
        feedback_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Recorded feedback with ID {feedback_id} of type {feedback_type}")
        return feedback_id

    def get_feedback(self, feedback_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific feedback entry.

        Args:
            feedback_id: ID of the feedback to retrieve

        Returns:
            Dictionary containing the feedback entry, or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        feedback = dict(row)
        
        # Convert tags JSON to list
        if feedback['tags']:
            feedback['tags'] = json.loads(feedback['tags'])
        else:
            feedback['tags'] = []
        
        # Get actions for this feedback
        cursor.execute("SELECT * FROM actions WHERE feedback_id = ?", (feedback_id,))
        actions = [dict(action) for action in cursor.fetchall()]
        feedback['actions'] = actions
        
        conn.close()
        return feedback

    def get_all_feedback(self, feedback_type: Optional[str] = None, 
                         source: Optional[str] = None, 
                         session_id: Optional[str] = None,
                         processed: Optional[bool] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all feedback entries, optionally filtered.

        Args:
            feedback_type: Filter by feedback type
            source: Filter by source
            session_id: Filter by session ID
            processed: Filter by processed status
            limit: Maximum number of entries to return

        Returns:
            List of feedback entries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM feedback WHERE 1=1"
        params = []
        
        if feedback_type:
            query += " AND feedback_type = ?"
            params.append(feedback_type)
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if processed is not None:
            query += " AND processed = ?"
            params.append(1 if processed else 0)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        feedbacks = []
        
        for row in cursor.fetchall():
            feedback = dict(row)
            
            # Convert tags JSON to list
            if feedback['tags']:
                feedback['tags'] = json.loads(feedback['tags'])
            else:
                feedback['tags'] = []
            
            feedbacks.append(feedback)
        
        conn.close()
        return feedbacks

    def mark_as_processed(self, feedback_id: int, processed: bool = True) -> bool:
        """
        Mark a feedback entry as processed or unprocessed.

        Args:
            feedback_id: ID of the feedback to update
            processed: Whether the feedback is processed

        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE feedback SET processed = ? WHERE id = ?",
            (1 if processed else 0, feedback_id)
        )
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            logger.info(f"Marked feedback {feedback_id} as {'processed' if processed else 'unprocessed'}")
        
        return success

    def record_action(self, feedback_id: int, action_type: str, description: str, 
                     result: Optional[str] = None) -> int:
        """
        Record an action taken in response to feedback.

        Args:
            feedback_id: ID of the feedback the action is related to
            action_type: Type of action (e.g., "fix", "respond", "escalate")
            description: Description of the action
            result: Result of the action (optional)

        Returns:
            ID of the newly created action entry
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute(
            "INSERT INTO actions (feedback_id, timestamp, action_type, description, result) "
            "VALUES (?, ?, ?, ?, ?)",
            (feedback_id, timestamp, action_type, description, result)
        )
        
        action_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Recorded action {action_id} for feedback {feedback_id}")
        return action_id

    def analyze_feedback(self, feedback_type: Optional[str] = None, 
                        time_period: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyze feedback to extract insights.

        Args:
            feedback_type: Filter by feedback type
            time_period: Time period in days to analyze

        Returns:
            Dictionary containing analysis results
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM feedback WHERE 1=1"
        params = []
        
        if feedback_type:
            query += " AND feedback_type = ?"
            params.append(feedback_type)
        
        if time_period:
            timestamp_cutoff = (datetime.now() - datetime.timedelta(days=time_period)).isoformat()
            query += " AND timestamp >= ?"
            params.append(timestamp_cutoff)
        
        cursor.execute(query, params)
        feedbacks = [dict(row) for row in cursor.fetchall()]
        
        # Basic analysis
        analysis = {
            'total_count': len(feedbacks),
            'by_type': {},
            'by_source': {},
            'average_rating': None,
            'processed_count': 0,
            'unprocessed_count': 0,
            'common_tags': {},
            'recent_feedback': []
        }
        
        # Count by type and source
        for feedback in feedbacks:
            # By type
            feedback_type = feedback['feedback_type']
            if feedback_type not in analysis['by_type']:
                analysis['by_type'][feedback_type] = 0
            analysis['by_type'][feedback_type] += 1
            
            # By source
            source = feedback['source'] or 'unknown'
            if source not in analysis['by_source']:
                analysis['by_source'][source] = 0
            analysis['by_source'][source] += 1
            
            # Processed status
            if feedback['processed']:
                analysis['processed_count'] += 1
            else:
                analysis['unprocessed_count'] += 1
            
            # Tags
            if feedback['tags']:
                tags = json.loads(feedback['tags']) if isinstance(feedback['tags'], str) else feedback['tags']
                for tag in tags:
                    if tag not in analysis['common_tags']:
                        analysis['common_tags'][tag] = 0
                    analysis['common_tags'][tag] += 1
        
        # Calculate average rating
        ratings = [f['rating'] for f in feedbacks if f['rating'] is not None]
        if ratings:
            analysis['average_rating'] = sum(ratings) / len(ratings)
        
        # Get recent feedback
        analysis['recent_feedback'] = sorted(
            feedbacks, 
            key=lambda f: f['timestamp'], 
            reverse=True
        )[:5]
        
        conn.close()
        return analysis

    def export_feedback(self, output_file: str, format: str = 'json', 
                       feedback_type: Optional[str] = None) -> bool:
        """
        Export feedback to a file.

        Args:
            output_file: Path to output file
            format: Format of the output (json, csv, or txt)
            feedback_type: Filter by feedback type

        Returns:
            True if successful, False otherwise
        """
        feedbacks = self.get_all_feedback(feedback_type=feedback_type, limit=1000)
        
        try:
            if format == 'json':
                with open(output_file, 'w') as f:
                    json.dump(feedbacks, f, indent=2)
            
            elif format == 'csv':
                import csv
                
                with open(output_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    
                    # Write header
                    writer.writerow([
                        'ID', 'Timestamp', 'Session ID', 'Source', 'Type', 
                        'Content', 'Rating', 'Tags', 'Processed'
                    ])
                    
                    # Write data
                    for feedback in feedbacks:
                        writer.writerow([
                            feedback['id'],
                            feedback['timestamp'],
                            feedback['session_id'],
                            feedback['source'],
                            feedback['feedback_type'],
                            feedback['content'],
                            feedback['rating'],
                            ','.join(feedback['tags']) if feedback['tags'] else '',
                            'Yes' if feedback['processed'] else 'No'
                        ])
            
            elif format == 'txt':
                with open(output_file, 'w') as f:
                    f.write("Triangulum Feedback Export\n")
                    f.write("=========================\n\n")
                    
                    for feedback in feedbacks:
                        f.write(f"ID: {feedback['id']}\n")
                        f.write(f"Timestamp: {feedback['timestamp']}\n")
                        f.write(f"Session: {feedback['session_id']}\n")
                        f.write(f"Source: {feedback['source']}\n")
                        f.write(f"Type: {feedback['feedback_type']}\n")
                        f.write(f"Rating: {feedback['rating']}\n")
                        f.write(f"Tags: {', '.join(feedback['tags']) if feedback['tags'] else 'None'}\n")
                        f.write(f"Processed: {'Yes' if feedback['processed'] else 'No'}\n")
                        f.write(f"Content: {feedback['content']}\n\n")
                        f.write("-" * 50 + "\n\n")
            
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
            
            logger.info(f"Exported {len(feedbacks)} feedback entries to {output_file}")
            return True
        
        except Exception as e:
            logger.error(f"Error exporting feedback: {e}")
            return False

    def delete_feedback(self, feedback_id: int) -> bool:
        """
        Delete a feedback entry.

        Args:
            feedback_id: ID of the feedback to delete

        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # First delete any actions associated with this feedback
        cursor.execute("DELETE FROM actions WHERE feedback_id = ?", (feedback_id,))
        
        # Then delete the feedback itself
        cursor.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            logger.info(f"Deleted feedback {feedback_id}")
        
        return success
