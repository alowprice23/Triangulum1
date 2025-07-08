"""
Human integration hub for Triangulum.

Implements a SQLite-backed review queue for human intervention in the debugging process.
"""

import sqlite3
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import uuid
import os

# FastAPI for REST API
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Setup logging
logger = logging.getLogger("triangulum.human_hub")


# Database setup
DB_PATH = Path("triangulum_data/human_queue.db")


class ReviewItem(BaseModel):
    """Pydantic model for a review item."""
    id: int
    bug_id: str
    status: str
    created_at: str
    updated_at: str
    patch_bundle: str
    metadata: Dict[str, Any]


class ReviewDecision(BaseModel):
    """Pydantic model for a review decision."""
    decision: str  # 'approve', 'reject', 'escalate'
    comment: str = ""


class HumanReviewHub:
    """
    Central hub for managing human review of patches.
    
    This class provides:
    1. A SQLite database for storing review items
    2. Methods for adding, updating, and retrieving review items
    3. Integration with the patch bundle system
    """
    
    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    STATUS_ESCALATED = "ESCALATED"
    
    def __init__(self, db_path: Union[str, Path] = DB_PATH):
        """
        Initialize the human review hub.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        
        # Create directory if needed
        self.db_path.parent.mkdir(exist_ok=True, parents=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the database and create tables if needed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create review_items table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bug_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                patch_bundle TEXT NOT NULL,
                metadata TEXT
            )
            """)
            
            # Create review_history table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                comment TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (item_id) REFERENCES review_items (id)
            )
            """)
            
            conn.commit()
    
    def add_item(self, 
                bug_id: str, 
                patch_bundle: str,
                metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Add a new item to the review queue.
        
        Args:
            bug_id: Unique identifier for the bug
            patch_bundle: Path to the patch bundle file
            metadata: Additional metadata about the review item
            
        Returns:
            int: ID of the created review item
        """
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
            INSERT INTO review_items 
            (bug_id, status, created_at, updated_at, patch_bundle, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                bug_id,
                self.STATUS_PENDING,
                now,
                now,
                patch_bundle,
                json.dumps(metadata or {})
            ))
            
            item_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Added review item {item_id} for bug {bug_id}")
            return item_id
    
    def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a review item by ID.
        
        Args:
            item_id: ID of the review item
            
        Returns:
            Dict with review item details, or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT * FROM review_items WHERE id = ?
            """, (item_id,))
            
            row = cursor.fetchone()
            
            if row is None:
                return None
                
            item = dict(row)
            item["metadata"] = json.loads(item["metadata"])
            
            return item
    
    def get_queue(self, 
                 status: Optional[str] = None, 
                 limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get items from the review queue.
        
        Args:
            status: Filter by status (or None for all)
            limit: Maximum items to return
            
        Returns:
            List of review items
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if status:
                cursor.execute("""
                SELECT * FROM review_items WHERE status = ?
                ORDER BY created_at DESC LIMIT ?
                """, (status, limit))
            else:
                cursor.execute("""
                SELECT * FROM review_items
                ORDER BY created_at DESC LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            
            items = []
            for row in rows:
                item = dict(row)
                item["metadata"] = json.loads(item["metadata"])
                items.append(item)
                
            return items
    
    def update_item(self, 
                   item_id: int, 
                   status: str, 
                   comment: str = "") -> bool:
        """
        Update the status of a review item.
        
        Args:
            item_id: ID of the review item
            status: New status
            comment: Optional comment
            
        Returns:
            bool: True if the update was successful
        """
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # First check if the item exists
            cursor.execute("""
            SELECT id FROM review_items WHERE id = ?
            """, (item_id,))
            
            if cursor.fetchone() is None:
                logger.error(f"Review item {item_id} not found")
                return False
            
            # Update the item
            cursor.execute("""
            UPDATE review_items
            SET status = ?, updated_at = ?
            WHERE id = ?
            """, (status, now, item_id))
            
            # Add to history
            cursor.execute("""
            INSERT INTO review_history 
            (item_id, action, comment, timestamp)
            VALUES (?, ?, ?, ?)
            """, (item_id, status, comment, now))
            
            conn.commit()
            
            logger.info(f"Updated review item {item_id} to status {status}")
            return True
    
    def get_history(self, item_id: int) -> List[Dict[str, Any]]:
        """
        Get the history of a review item.
        
        Args:
            item_id: ID of the review item
            
        Returns:
            List of history entries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT * FROM review_history WHERE item_id = ?
            ORDER BY timestamp DESC
            """, (item_id,))
            
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Dict with queue statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get counts by status
            cursor.execute("""
            SELECT status, COUNT(*) FROM review_items
            GROUP BY status
            """)
            
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get average review time for completed items
            cursor.execute("""
            SELECT AVG(JULIANDAY(updated_at) - JULIANDAY(created_at)) * 24 * 60
            FROM review_items
            WHERE status IN (?, ?)
            """, (self.STATUS_APPROVED, self.STATUS_REJECTED))
            
            avg_minutes = cursor.fetchone()[0] or 0
            
            # Get totals
            cursor.execute("SELECT COUNT(*) FROM review_items")
            total = cursor.fetchone()[0]
            
            return {
                "total_items": total,
                "pending": status_counts.get(self.STATUS_PENDING, 0),
                "approved": status_counts.get(self.STATUS_APPROVED, 0),
                "rejected": status_counts.get(self.STATUS_REJECTED, 0),
                "escalated": status_counts.get(self.STATUS_ESCALATED, 0),
                "avg_review_minutes": round(avg_minutes, 1)
            }


def create_review_api() -> FastAPI:
    """
    Create a FastAPI app for the human review hub.
    
    Returns:
        FastAPI app
    """
    app = FastAPI(title="Triangulum Human Review Hub")
    hub = HumanReviewHub()
    
    # Static files for UI
    app.mount("/static", StaticFiles(directory="ui"), name="static")
    
    @app.get("/")
    async def read_root():
        """Redirect to the UI."""
        return {"message": "Welcome to Triangulum Human Review Hub API"}
    
    @app.get("/items", response_model=List[ReviewItem])
    async def get_items(status: Optional[str] = None, limit: int = Query(50, le=100)):
        """Get review items."""
        return hub.get_queue(status, limit)
    
    @app.get("/items/{item_id}", response_model=ReviewItem)
    async def get_item(item_id: int):
        """Get a specific review item."""
        item = hub.get_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item
    
    @app.post("/items/{item_id}/review")
    async def review_item(item_id: int, decision: ReviewDecision):
        """Review an item."""
        # Map decision to status
        status_map = {
            "approve": hub.STATUS_APPROVED,
            "reject": hub.STATUS_REJECTED,
            "escalate": hub.STATUS_ESCALATED
        }
        
        if decision.decision not in status_map:
            raise HTTPException(status_code=400, detail="Invalid decision")
            
        status = status_map[decision.decision]
        success = hub.update_item(item_id, status, decision.comment)
        
        if not success:
            raise HTTPException(status_code=404, detail="Item not found")
            
        return {"status": "success", "item_id": item_id, "new_status": status}
    
    @app.post("/submit/{bug_id}")
    async def submit(bug_id: str, 
                    bundle: UploadFile = File(...),
                    metadata: str = Form("{}")):
        """Submit a patch bundle for review."""
        # Parse metadata
        try:
            meta_dict = json.loads(metadata)
        except json.JSONDecodeError:
            meta_dict = {}
        
        # Save the bundle file
        bundle_dir = Path("triangulum_data/bundles")
        bundle_dir.mkdir(exist_ok=True, parents=True)
        
        # Generate a unique filename
        timestamp = int(time.time())
        filename = f"{bug_id}_{timestamp}_{uuid.uuid4().hex[:8]}.tar.gz"
        file_path = bundle_dir / filename
        
        # Write the file
        with open(file_path, "wb") as f:
            f.write(await bundle.read())
        
        # Add to review queue
        item_id = hub.add_item(bug_id, str(file_path), meta_dict)
        
        return {"status": "success", "item_id": item_id, "filename": filename}
    
    @app.get("/stats")
    async def get_stats():
        """Get queue statistics."""
        return hub.get_stats()
    
    @app.get("/history/{item_id}")
    async def get_history(item_id: int):
        """Get history for an item."""
        history = hub.get_history(item_id)
        return {"item_id": item_id, "history": history}
    
    @app.get("/download/{item_id}")
    async def download_bundle(item_id: int):
        """Download a patch bundle."""
        item = hub.get_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
            
        bundle_path = Path(item["patch_bundle"])
        if not bundle_path.exists():
            raise HTTPException(status_code=404, detail="Bundle file not found")
            
        return FileResponse(
            path=bundle_path,
            filename=f"patch_{item['bug_id']}.tar.gz",
            media_type="application/gzip"
        )
    
    return app


# Singleton instance of the hub for global access
_GLOBAL_HUB = None

def get_hub() -> HumanReviewHub:
    """
    Get the global human review hub instance.
    
    Returns:
        HumanReviewHub instance
    """
    global _GLOBAL_HUB
    if _GLOBAL_HUB is None:
        _GLOBAL_HUB = HumanReviewHub()
    return _GLOBAL_HUB


if __name__ == "__main__":
    # If run directly, start the API server
    import uvicorn
    api = create_review_api()
    uvicorn.run(api, host="0.0.0.0", port=8000)
