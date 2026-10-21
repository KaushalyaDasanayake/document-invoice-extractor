"""Asynchronous job queue and persistent store for invoice extraction."""

from __future__ import annotations

import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path("data/jobs.db")


@dataclass
class JobRecord:
    job_id: str
    status: str  # pending, processing, completed, failed
    filename: str
    created_at: str
    completed_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class JobQueue:
    """Thread-safe persistent job store backed by SQLite."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._lock = threading.Lock()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    result_json TEXT,
                    error TEXT
                )
                """
            )
            conn.commit()

    def create_job(self, filename: str) -> str:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._get_connection() as conn:
            conn.execute(
                "INSERT INTO jobs (job_id, status, filename, created_at) VALUES (?, ?, ?, ?)",
                (job_id, "pending", filename, now),
            )
            conn.commit()
        return job_id

    def update_job_success(self, job_id: str, result: dict[str, Any]) -> None:
        import json

        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._get_connection() as conn:
            conn.execute(
                "UPDATE jobs SET status = ?, completed_at = ?, result_json = ? WHERE job_id = ?",
                ("completed", now, json.dumps(result), job_id),
            )
            conn.commit()

    def update_job_failed(self, job_id: str, error: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._get_connection() as conn:
            conn.execute(
                "UPDATE jobs SET status = ?, completed_at = ?, error = ? WHERE job_id = ?",
                ("failed", now, error, job_id),
            )
            conn.commit()

    def get_job(self, job_id: str) -> JobRecord | None:
        import json

        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = json.loads(row["result_json"]) if row["result_json"] else None
            return JobRecord(
                job_id=row["job_id"],
                status=row["status"],
                filename=row["filename"],
                created_at=row["created_at"],
                completed_at=row["completed_at"],
                result=res,
                error=row["error"],
            )


# Global queue singleton
GLOBAL_QUEUE = JobQueue()
