#!/usr/bin/env python3
"""
Feedback Processor

This module systematically analyzes user and test feedback to improve system performance
and repair effectiveness. It processes structured feedback, tracks repair effectiveness,
identifies false positives/negatives, extracts learning signals, and provides
feedback-based adjustment mechanisms.
"""

import os
import json
import time
import logging
import hashlib
import re
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("triangulum.feedback_processor")

# Try to import optional dependencies
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import DBSCAN
    from sklearn.ensemble import RandomForestClassifier
    HAVE_ML_DEPS = True
except ImportError:
    logger.warning("Machine learning dependencies not available. Using basic feedback processing only.")
    HAVE_ML_DEPS = False


class FeedbackItem:
    """
    Represents a feedback item from a user or test.
    """
    
    def __init__(self, 
                 feedback_id: str,
                 source_type: str,
                 content: str,
                 context: Dict[str, Any],
                 metadata: Dict[str, Any]):
        """
        Initialize a feedback item.
        
        Args:
            feedback_id: Unique identifier for the feedback
            source_type: Type of feedback source (user, test, system)
            content: Feedback content
            context: Context information for the feedback
            metadata: Additional metadata about the feedback
        """
        self.feedback_id = feedback_id
        self.source_type = source_type
        self.content = content
        self.context = context
        self.metadata = metadata
        self.created_at = datetime.now().isoformat()
        self.processed = False
        self.processed_at = None
        self.analysis_results = {}
        self.learning_signals = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert feedback item to dictionary for serialization."""
        return {
            "feedback_id": self.feedback_id,
            "source_type": self.source_type,
            "content": self.content,
            "context": self.context,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "processed": self.processed,
            "processed_at": self.processed_at,
            "analysis_results": self.analysis_results,
            "learning_signals": self.learning_signals
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedbackItem':
        """Create feedback item from dictionary."""
        feedback = cls(
            feedback_id=data["feedback_id"],
            source_type=data["source_type"],
            content=data["content"],
            context=data["context"],
            metadata=data["metadata"]
        )
        
        # Restore state
        feedback.created_at = data["created_at"]
        feedback.processed = data["processed"]
        feedback.processed_at = data["processed_at"]
        feedback.analysis_results = data["analysis_results"]
        feedback.learning_signals = data["learning_signals"]
        
        return feedback
    
    def mark_processed(self, analysis_results: Dict[str, Any], learning_signals: List[Dict[str, Any]]):
        """
        Mark the feedback item as processed.
        
        Args:
            analysis_results: Results of feedback analysis
            learning_signals: Learning signals extracted from feedback
        """
        self.processed = True
        self.processed_at = datetime.now().isoformat()
        self.analysis_results = analysis_results
        self.learning_signals = learning_signals


class RepairEffectiveness:
    """
    Tracks the effectiveness of repairs.
    """
    
    def __init__(self, 
                 repair_id: str,
                 bug_type: str,
                 file_path: str,
                 repair_description: str):
        """
        Initialize repair effectiveness tracking.
        
        Args:
            repair_id: Unique identifier for the repair
            bug_type: Type of bug that was fixed
            file_path: Path to the file that was fixed
            repair_description: Description of the repair
        """
        self.repair_id = repair_id
        self.bug_type = bug_type
        self.file_path = file_path
        self.repair_description = repair_description
        self.created_at = datetime.now().isoformat()
        self.feedback_items = []
        self.success_count = 0
        self.failure_count = 0
        self.effectiveness_score = 0.0
        self.last_updated = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert repair effectiveness to dictionary for serialization."""
        return {
            "repair_id": self.repair_id,
            "bug_type": self.bug_type,
            "file_path": self.file_path,
            "repair_description": self.repair_description,
            "created_at": self.created_at,
            "feedback_items": self.feedback_items,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "effectiveness_score": self.effectiveness_score,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RepairEffectiveness':
        """Create repair effectiveness from dictionary."""
        effectiveness = cls(
            repair_id=data["repair_id"],
            bug_type=data["bug_type"],
            file_path=data["file_path"],
            repair_description=data["repair_description"]
        )
        
        # Restore state
        effectiveness.created_at = data["created_at"]
        effectiveness.feedback_items = data["feedback_items"]
        effectiveness.success_count = data["success_count"]
        effectiveness.failure_count = data["failure_count"]
        effectiveness.effectiveness_score = data["effectiveness_score"]
        effectiveness.last_updated = data["last_updated"]
        
        return effectiveness
    
    def add_feedback(self, feedback_id: str, success: bool):
        """
        Add feedback for the repair.
        
        Args:
            feedback_id: ID of the feedback item
            success: Whether the feedback indicates success
        """
        self.feedback_items.append(feedback_id)
        
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        # Update effectiveness score
        total = self.success_count + self.failure_count
        self.effectiveness_score = self.success_count / total if total > 0 else 0.0
        
        self.last_updated = datetime.now().isoformat()


class FeedbackProcessor:
    """
    Processes feedback to improve system performance and repair effectiveness.
    """
    
    def __init__(self, database_path: Optional[str] = None):
        """
        Initialize the feedback processor.
        
        Args:
            database_path: Path to the feedback database file
        """
        self.database_path = database_path or "triangulum_lx/learning/feedback.json"
        self.feedback_items: Dict[str, FeedbackItem] = {}
        self.repair_effectiveness: Dict[str, RepairEffectiveness] = {}
        self.feedback_clusters: Dict[str, List[str]] = {}
        self.learning_signals: List[Dict[str, Any]] = []
        
        # Initialize vectorizer for similarity matching
        self.vectorizer = None
        if HAVE_ML_DEPS:
            self.vectorizer = TfidfVectorizer(
                analyzer='word',
                token_pattern=r'\b\w+\b',
                ngram_range=(1, 2),
                max_features=5000
            )
        
        # Load feedback if available
        self._load_feedback()
    
    def _load_feedback(self):
        """Load feedback from the database file."""
        if os.path.exists(self.database_path):
            try:
                with open(self.database_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load feedback items
                for feedback_data in data.get("feedback_items", []):
                    feedback = FeedbackItem.from_dict(feedback_data)
                    self.feedback_items[feedback.feedback_id] = feedback
                
                # Load repair effectiveness
                for effectiveness_data in data.get("repair_effectiveness", []):
                    effectiveness = RepairEffectiveness.from_dict(effectiveness_data)
                    self.repair_effectiveness[effectiveness.repair_id] = effectiveness
                
                # Load feedback clusters
                self.feedback_clusters = data.get("feedback_clusters", {})
                
                # Load learning signals
                self.learning_signals = data.get("learning_signals", [])
                
                logger.info(f"Loaded {len(self.feedback_items)} feedback items from {self.database_path}")
            except Exception as e:
                logger.error(f"Error loading feedback: {e}")
                self.feedback_items = {}
                self.repair_effectiveness = {}
                self.feedback_clusters = {}
                self.learning_signals = []
        else:
            logger.info("No feedback database found. Starting with empty database.")
    
    def _save_feedback(self):
        """Save feedback to the database file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
            
            # Prepare data for serialization
            data = {
                "feedback_items": [feedback.to_dict() for feedback in self.feedback_items.values()],
                "repair_effectiveness": [effectiveness.to_dict() for effectiveness in self.repair_effectiveness.values()],
                "feedback_clusters": self.feedback_clusters,
                "learning_signals": self.learning_signals,
                "last_updated": datetime.now().isoformat()
            }
            
            # Save to file
            with open(self.database_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Saved {len(self.feedback_items)} feedback items to {self.database_path}")
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
    
    def process_feedback(self, 
                        source_type: str,
                        content: str,
                        context: Dict[str, Any],
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a feedback item.
        
        Args:
            source_type: Type of feedback source (user, test, system)
            content: Feedback content
            context: Context information for the feedback
            metadata: Additional metadata about the feedback
            
        Returns:
            Feedback ID
        """
        # Generate feedback ID
        timestamp = int(time.time())
        content_hash = hashlib.md5(f"{source_type}{content}".encode()).hexdigest()[:8]
        feedback_id = f"feedback_{timestamp}_{content_hash}"
        
        # Create feedback item
        feedback = FeedbackItem(
            feedback_id=feedback_id,
            source_type=source_type,
            content=content,
            context=context,
            metadata=metadata or {}
        )
        
        # Add feedback item to database
        self.feedback_items[feedback_id] = feedback
        
        # Process feedback
        self._analyze_feedback(feedback)
        
        # Update repair effectiveness if applicable
        if "repair_id" in context:
            repair_id = context["repair_id"]
            success = self._determine_success(feedback)
            
            if repair_id in self.repair_effectiveness:
                # Update existing repair effectiveness
                self.repair_effectiveness[repair_id].add_feedback(feedback_id, success)
            else:
                # Create new repair effectiveness
                bug_type = context.get("bug_type", "unknown")
                file_path = context.get("file_path", "unknown")
                repair_description = context.get("repair_description", "")
                
                effectiveness = RepairEffectiveness(
                    repair_id=repair_id,
                    bug_type=bug_type,
                    file_path=file_path,
                    repair_description=repair_description
                )
                effectiveness.add_feedback(feedback_id, success)
                
                self.repair_effectiveness[repair_id] = effectiveness
        
        # Update feedback clusters
        self._update_feedback_clusters()
        
        # Save feedback
        self._save_feedback()
        
        logger.info(f"Processed feedback {feedback_id} from {source_type}")
        return feedback_id
    
    def _analyze_feedback(self, feedback: FeedbackItem):
        """
        Analyze a feedback item.
        
        Args:
            feedback: Feedback item to analyze
        """
        # Initialize analysis results
        analysis_results = {
            "sentiment": self._analyze_sentiment(feedback.content),
            "categories": self._categorize_feedback(feedback),
            "entities": self._extract_entities(feedback.content),
            "keywords": self._extract_keywords(feedback.content),
            "false_positive": self._detect_false_positive(feedback),
            "false_negative": self._detect_false_negative(feedback),
            "actionable": self._is_actionable(feedback)
        }
        
        # Extract learning signals
        learning_signals = self._extract_learning_signals(feedback, analysis_results)
        
        # Mark feedback as processed
        feedback.mark_processed(analysis_results, learning_signals)
        
        # Add learning signals to global list
        self.learning_signals.extend(learning_signals)
    
    def _analyze_sentiment(self, content: str) -> Dict[str, float]:
        """
        Analyze sentiment of feedback content.
        
        Args:
            content: Feedback content
            
        Returns:
            Dictionary with sentiment scores
        """
        # Simple rule-based sentiment analysis
        positive_words = [
            "good", "great", "excellent", "awesome", "amazing", "fantastic",
            "helpful", "useful", "effective", "efficient", "works", "working",
            "fixed", "resolved", "solved", "success", "successful", "correct"
        ]
        
        negative_words = [
            "bad", "poor", "terrible", "awful", "horrible", "useless",
            "unhelpful", "ineffective", "inefficient", "broken", "fails", "failing",
            "failed", "unresolved", "unsolved", "error", "wrong", "incorrect",
            "issue", "problem", "bug", "glitch", "crash"
        ]
        
        # Count positive and negative words
        content_lower = content.lower()
        positive_count = sum(1 for word in positive_words if re.search(r'\b' + word + r'\b', content_lower))
        negative_count = sum(1 for word in negative_words if re.search(r'\b' + word + r'\b', content_lower))
        
        # Calculate sentiment scores
        total = positive_count + negative_count
        if total == 0:
            return {"positive": 0.5, "negative": 0.5, "neutral": 1.0}
        
        positive_score = positive_count / total
        negative_score = negative_count / total
        neutral_score = 1.0 - (positive_score + negative_score)
        
        return {
            "positive": positive_score,
            "negative": negative_score,
            "neutral": neutral_score
        }
    
    def _categorize_feedback(self, feedback: FeedbackItem) -> List[str]:
        """
        Categorize feedback.
        
        Args:
            feedback: Feedback item
            
        Returns:
            List of categories
        """
        categories = []
        content_lower = feedback.content.lower()
        
        # Bug-related categories
        if any(word in content_lower for word in ["bug", "issue", "problem", "error", "crash", "exception"]):
            categories.append("bug")
        
        # Performance-related categories
        if any(word in content_lower for word in ["slow", "performance", "speed", "fast", "efficient", "memory", "cpu"]):
            categories.append("performance")
        
        # UI/UX-related categories
        if any(word in content_lower for word in ["ui", "ux", "interface", "design", "layout", "usability"]):
            categories.append("ui_ux")
        
        # Feature-related categories
        if any(word in content_lower for word in ["feature", "functionality", "capability", "ability"]):
            categories.append("feature")
        
        # Documentation-related categories
        if any(word in content_lower for word in ["doc", "documentation", "example", "tutorial", "guide"]):
            categories.append("documentation")
        
        # Add source type as category
        categories.append(f"source_{feedback.source_type}")
        
        # Add context-based categories
        if "bug_type" in feedback.context:
            categories.append(f"bug_type_{feedback.context['bug_type']}")
        
        if "file_path" in feedback.context:
            file_extension = os.path.splitext(feedback.context["file_path"])[1].lower()
            if file_extension:
                categories.append(f"file_type_{file_extension[1:]}")
        
        return categories
    
    def _extract_entities(self, content: str) -> Dict[str, List[str]]:
        """
        Extract entities from feedback content.
        
        Args:
            content: Feedback content
            
        Returns:
            Dictionary of entity types and values
        """
        entities = {
            "file_paths": [],
            "function_names": [],
            "variable_names": [],
            "error_messages": []
        }
        
        # Extract file paths
        file_path_pattern = r'[a-zA-Z0-9_\-/\\\.]+\.(py|js|java|cpp|h|rb|go|php|cs|html|css|json|xml)'
        entities["file_paths"] = re.findall(file_path_pattern, content)
        
        # Extract function names
        function_pattern = r'[a-zA-Z_][a-zA-Z0-9_]*\(\)'
        entities["function_names"] = [name[:-2] for name in re.findall(function_pattern, content)]
        
        # Extract variable names
        variable_pattern = r'[a-zA-Z_][a-zA-Z0-9_]*'
        potential_variables = re.findall(variable_pattern, content)
        
        # Filter out common words and keywords
        common_words = [
            "the", "and", "or", "if", "else", "for", "while", "in", "is", "not",
            "def", "class", "function", "var", "let", "const", "return", "import",
            "from", "as", "with", "try", "except", "catch", "finally", "raise",
            "throw", "this", "self", "super", "null", "None", "nil", "true",
            "false", "True", "False", "bug", "issue", "error", "fix", "fixed"
        ]
        
        entities["variable_names"] = [var for var in potential_variables if var not in common_words and len(var) > 1]
        
        # Extract error messages
        error_pattern = r'(Error|Exception|Warning):[^\n]+'
        entities["error_messages"] = re.findall(error_pattern, content)
        
        return entities
    
    def _extract_keywords(self, content: str) -> List[str]:
        """
        Extract keywords from feedback content.
        
        Args:
            content: Feedback content
            
        Returns:
            List of keywords
        """
        # Simple keyword extraction using word frequency
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', content.lower())
        
        # Filter out common words
        common_words = [
            "the", "and", "or", "if", "else", "for", "while", "in", "is", "not",
            "a", "an", "of", "to", "on", "at", "by", "with", "about", "as",
            "from", "into", "during", "including", "until", "against", "among",
            "throughout", "despite", "towards", "upon", "concerning", "this",
            "that", "these", "those", "my", "your", "his", "her", "its", "our",
            "their", "i", "you", "he", "she", "it", "we", "they", "me", "him",
            "her", "us", "them", "what", "which", "who", "whom", "whose", "when",
            "where", "why", "how", "all", "any", "both", "each", "few", "more",
            "most", "other", "some", "such", "no", "nor", "not", "only", "own",
            "same", "so", "than", "too", "very", "can", "will", "just", "should",
            "now", "also", "been", "had", "has", "have", "was", "were", "be", "am",
            "are", "is", "do", "does", "did", "but", "however", "yet", "because"
        ]
        
        filtered_words = [word for word in words if word not in common_words and len(word) > 2]
        
        # Count word frequency
        word_counts = Counter(filtered_words)
        
        # Get top keywords
        keywords = [word for word, count in word_counts.most_common(10)]
        
        return keywords
    
    def _detect_false_positive(self, feedback: FeedbackItem) -> bool:
        """
        Detect if feedback indicates a false positive.
        
        Args:
            feedback: Feedback item
            
        Returns:
            True if feedback indicates a false positive, False otherwise
        """
        content_lower = feedback.content.lower()
        
        # Check for false positive indicators
        false_positive_indicators = [
            "false positive", "not a bug", "not an issue", "not a problem",
            "incorrectly identified", "incorrectly detected", "wrong detection",
            "misidentified", "misdetected", "false alarm", "false alert"
        ]
        
        return any(indicator in content_lower for indicator in false_positive_indicators)
    
    def _detect_false_negative(self, feedback: FeedbackItem) -> bool:
        """
        Detect if feedback indicates a false negative.
        
        Args:
            feedback: Feedback item
            
        Returns:
            True if feedback indicates a false negative, False otherwise
        """
        content_lower = feedback.content.lower()
        
        # Check for false negative indicators
        false_negative_indicators = [
            "false negative", "missed bug", "missed issue", "missed problem",
            "not detected", "not identified", "failed to detect", "failed to identify",
            "should have detected", "should have identified", "overlooked"
        ]
        
        return any(indicator in content_lower for indicator in false_negative_indicators)
    
    def _is_actionable(self, feedback: FeedbackItem) -> bool:
        """
        Determine if feedback is actionable.
        
        Args:
            feedback: Feedback item
            
        Returns:
            True if feedback is actionable, False otherwise
        """
        # Check if feedback has specific details
        has_details = (
            len(feedback.content) > 50 and  # Minimum length
            (self._extract_entities(feedback.content)["file_paths"] or  # Has file paths
             self._extract_entities(feedback.content)["function_names"] or  # Has function names
             self._extract_entities(feedback.content)["error_messages"])  # Has error messages
        )
        
        # Check if feedback has a clear sentiment
        sentiment = self._analyze_sentiment(feedback.content)
        has_clear_sentiment = max(sentiment["positive"], sentiment["negative"]) > 0.6
        
        # Check if feedback is from a reliable source
        is_reliable_source = feedback.source_type in ["user", "test"]
        
        # Check if feedback has context
        has_context = bool(feedback.context)
        
        # Combine factors
        return (has_details or has_clear_sentiment) and is_reliable_source and has_context
    
    def _determine_success(self, feedback: FeedbackItem) -> bool:
        """
        Determine if feedback indicates success.
        
        Args:
            feedback: Feedback item
            
        Returns:
            True if feedback indicates success, False otherwise
        """
        # Check metadata for explicit success indicator
        if "success" in feedback.metadata:
            return bool(feedback.metadata["success"])
        
        if "rating" in feedback.metadata:
            rating = feedback.metadata["rating"]
            if isinstance(rating, (int, float)):
                # Assume rating is on a scale of 1-5
                return rating >= 3
        
        # Check sentiment
        sentiment = self._analyze_sentiment(feedback.content)
        return sentiment["positive"] > sentiment["negative"]
    
    def _extract_learning_signals(self, feedback: FeedbackItem, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract learning signals from feedback.
        
        Args:
            feedback: Feedback item
            analysis_results: Results of feedback analysis
            
        Returns:
            List of learning signals
        """
        signals = []
        
        # Generate signal ID
        timestamp = int(time.time())
        signal_hash = hashlib.md5(f"{feedback.feedback_id}{timestamp}".encode()).hexdigest()[:8]
        signal_id = f"signal_{timestamp}_{signal_hash}"
        
        # Extract sentiment-based signals
        sentiment = analysis_results["sentiment"]
        if sentiment["positive"] > 0.7:
            signals.append({
                "signal_id": f"{signal_id}_positive",
                "signal_type": "positive_feedback",
                "source": feedback.feedback_id,
                "strength": sentiment["positive"],
                "context": feedback.context,
                "created_at": datetime.now().isoformat()
            })
        elif sentiment["negative"] > 0.7:
            signals.append({
                "signal_id": f"{signal_id}_negative",
                "signal_type": "negative_feedback",
                "source": feedback.feedback_id,
                "strength": sentiment["negative"],
                "context": feedback.context,
                "created_at": datetime.now().isoformat()
            })
        
        # Extract false positive/negative signals
        if analysis_results["false_positive"]:
            signals.append({
                "signal_id": f"{signal_id}_false_positive",
                "signal_type": "false_positive",
                "source": feedback.feedback_id,
                "strength": 1.0,
                "context": feedback.context,
                "created_at": datetime.now().isoformat()
            })
        
        if analysis_results["false_negative"]:
            signals.append({
                "signal_id": f"{signal_id}_false_negative",
                "signal_type": "false_negative",
                "source": feedback.feedback_id,
                "strength": 1.0,
                "context": feedback.context,
                "created_at": datetime.now().isoformat()
            })
        
        # Extract actionable signals
        if analysis_results["actionable"]:
            signals.append({
                "signal_id": f"{signal_id}_actionable",
                "signal_type": "actionable_feedback",
                "source": feedback.feedback_id,
                "strength": 1.0,
                "context": feedback.context,
                "created_at": datetime.now().isoformat()
            })
        
        # Extract category-based signals
        for category in analysis_results["categories"]:
            signals.append({
                "signal_id": f"{signal_id}_{category}",
                "signal_type": f"category_{category}",
                "source": feedback.feedback_id,
                "strength": 1.0,
                "context": feedback.context,
                "created_at": datetime.now().isoformat()
            })
        
        return signals
    
    def _update_feedback_clusters(self):
        """Update feedback clusters based on similarity."""
        if not HAVE_ML_DEPS or len(self.feedback_items) < 2:
            # Skip clustering if ML dependencies are not available or not enough feedback
            return
        
        try:
            # Extract feedback texts for vectorization
            feedback_texts = []
            feedback_ids = []
            
            for feedback_id, feedback in self.feedback_items.items():
                feedback_text = feedback.content
                feedback_texts.append(feedback_text)
                feedback_ids.append(feedback_id)
            
            # Vectorize feedback
            X = self.vectorizer.fit_transform(feedback_texts)
            
            # Cluster feedback using DBSCAN
            clustering = DBSCAN(eps=0.3, min_samples=2).fit(X.toarray())
            
            # Update feedback clusters
            self.feedback_clusters = {}
            for i, cluster_id in enumerate(clustering.labels_):
                if cluster_id == -1:
                    # Noise points (no cluster)
                    continue
                
                cluster_key = f"cluster_{cluster_id}"
                if cluster_key not in self.feedback_clusters:
                    self.feedback_clusters[cluster_key] = []
                
                self.feedback_clusters[cluster_key].append(feedback_ids[i])
            
            logger.info(f"Updated feedback clusters: {len(self.feedback_clusters)} clusters")
        except Exception as e:
            logger.error(f"Error updating feedback clusters: {e}")
    
    def get_repair_effectiveness(self, repair_id: str) -> Optional[RepairEffectiveness]:
        """
        Get repair effectiveness.
        
        Args:
            repair_id: ID of the repair
            
        Returns:
            Repair effectiveness or None if not found
        """
        return self.repair_effectiveness.get(repair_id)
    
    def get_feedback_item(self, feedback_id: str) -> Optional[FeedbackItem]:
        """
        Get feedback item.
        
        Args:
            feedback_id: ID of the feedback item
            
        Returns:
            Feedback item or None if not found
        """
        return self.feedback_items.get(feedback_id)
    
    def get_learning_signals(self, signal_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get learning signals.
        
        Args:
            signal_type: Type of signal to filter by
            
        Returns:
            List of learning signals
        """
        if signal_type:
            return [signal for signal in self.learning_signals if signal["signal_type"] == signal_type]
        
        return self.learning_signals
    
    def get_feedback_by_category(self, category: str) -> List[FeedbackItem]:
        """
        Get feedback items by category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of feedback items
        """
        return [
            feedback for feedback in self.feedback_items.values()
            if feedback.processed and category in feedback.analysis_results.get("categories", [])
        ]
    
    def get_feedback_by_sentiment(self, sentiment_type: str, threshold: float = 0.7) -> List[FeedbackItem]:
        """
        Get feedback items by sentiment.
        
        Args:
            sentiment_type: Type of sentiment to filter by (positive, negative, neutral)
            threshold: Minimum sentiment score
            
        Returns:
            List of feedback items
        """
        return [
            feedback for feedback in self.feedback_items.values()
            if feedback.processed and feedback.analysis_results.get("sentiment", {}).get(sentiment_type, 0.0) >= threshold
        ]
