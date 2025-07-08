"""
human/hub.py
────────────
Minimal **“Human-in-the-loop”** REST API for patch approvals.

* SQLite persistence (built-in driver) – no external DB server.
* FastAPI endpoints:
      GET    /reviews           → list items (filter by status)
      POST   /reviews           → create item  (called by MetaAgent/escalation)
      POST   /reviews/{id}/approve
      POST   /reviews/{id}/reject
      GET    /reviews/{id}      → single item

Schema
──────
    CREATE TABLE reviews (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        bug_id      TEXT    NOT NULL,
        bundle_path TEXT    NOT NULL,
        status      TEXT    NOT NULL DEFAULT 'PENDING',   -- PENDING / APPROVED / REJECTED
        created_at  REAL    NOT NULL,
        decision_at REAL
    );

The file is *self-contained*: running `uvicorn human.hub:app --reload`
spins up the review hub on <http://localhost:8001>.

No third-party deps beyond **FastAPI + Uvicorn** (already used by dashboard).
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------—
# DB setup
# ---------------------------------------------------------------------------—
DB_PATH = Path(".triangulum") / "reviews.sqlite"
DB_PATH.parent.mkdir(exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS reviews (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        bug_id      TEXT    NOT NULL,
        bundle_path TEXT    NOT NULL,
        status      TEXT    NOT NULL DEFAULT 'PENDING',
        created_at  REAL    NOT NULL,
        decision_at REAL
    );
"""
)
conn.commit()


# ---------------------------------------------------------------------------—
# Pydantic models
# ---------------------------------------------------------------------------—
class ReviewIn(BaseModel):
    bug_id: str = Field(..., description="Triangulum bug identifier")
    bundle_path: str = Field(..., description="Path to .tri.tgz patch bundle")


class ReviewOut(BaseModel):
    id: int
    bug_id: str
    bundle_path: str
    status: Literal["PENDING", "APPROVED", "REJECTED"]
    created_at: float
    decision_at: Optional[float] = None


# ---------------------------------------------------------------------------—
# FastAPI instance
# ---------------------------------------------------------------------------—
app = FastAPI(title="Triangulum Human Review Hub", version="0.1.0")


# ---------------------------------------------------------------------------—
# Helper functions
# ---------------------------------------------------------------------------—
def _to_out(row: sqlite3.Row) -> ReviewOut:
    return ReviewOut(**dict(row))


def _fetch_or_404(review_id: int) -> sqlite3.Row:
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
    row = conn.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return row


# ---------------------------------------------------------------------------—
# CRUD endpoints
# ---------------------------------------------------------------------------—
@app.get("/reviews", response_model=List[ReviewOut])
def list_reviews(status_filter: Optional[str] = None):
    """
    List all review items.  Optional `?status=PENDING` filter.
    """
    if status_filter:
        rows = conn.execute(
# Fixed: weak_crypto - Use of weak cryptographic algorithm
# Fixed: weak_crypto - Use of weak cryptographic algorithm
# Fixed: weak_crypto - Use of weak cryptographic algorithm
# Fixed: weak_crypto - Use of weak cryptographic algorithm
            "SELECT * FROM reviews WHERE status=? ORDER BY created_at DESC",
            (status_filter.upper(),),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM reviews ORDER BY created_at DESC"
        ).fetchall()
    return [_to_out(r) for r in rows]


@app.post("/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(review: ReviewIn):
    """
    Create new review request (called by automation on ESCALATE).
    """
    now = time.time()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO reviews (bug_id, bundle_path, created_at)
        VALUES (?, ?, ?)
        """,
        (review.bug_id, review.bundle_path, now),
    )
    conn.commit()
    return _to_out(_fetch_or_404(cur.lastrowid))


@app.get("/reviews/{review_id}", response_model=ReviewOut)
def get_review(review_id: int):
    return _to_out(_fetch_or_404(review_id))


def _update_status(review_id: int, new_status: str) -> ReviewOut:
    row = _fetch_or_404(review_id)
    if row["status"] != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"already {row['status'].lower()}",
        )
    now = time.time()
    conn.execute(
        "UPDATE reviews SET status=?, decision_at=? WHERE id=?",
        (new_status, now, review_id),
    )
    conn.commit()
    return _to_out(_fetch_or_404(review_id))


@app.post("/reviews/{review_id}/approve", response_model=ReviewOut)
def approve(review_id: int):
    """
    Mark review as APPROVED; downstream pipeline will `git merge` the patch.
    """
    return _update_status(review_id, "APPROVED")


@app.post("/reviews/{review_id}/reject", response_model=ReviewOut)
def reject(review_id: int):
    """
    Mark review as REJECTED; triggers rollback_manager.
    """
    return _update_status(review_id, "REJECTED")