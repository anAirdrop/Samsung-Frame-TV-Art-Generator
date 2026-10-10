"""Persistent SQLite storage for generation jobs and managed artwork."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class JobRecord:
    id: str
    description: str
    tv_key: str
    source: str
    status: JobStatus
    message: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ArtworkRecord:
    content_id: str
    tv_key: str


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


class JobStore:
    """SQLite interface for durable generation state."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    tv_key TEXT NOT NULL,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS jobs_status_created
                    ON jobs(status, created_at);
                CREATE TABLE IF NOT EXISTS artworks (
                    content_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    tv_key TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );
                CREATE INDEX IF NOT EXISTS artworks_tv_created
                    ON artworks(tv_key, created_at);
                """
            )

    def recover_running_jobs(self) -> None:
        now = _timestamp()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, message = ?, updated_at = ?
                WHERE status = ?
                """,
                (
                    JobStatus.QUEUED,
                    "Recovered after service restart",
                    now,
                    JobStatus.RUNNING,
                ),
            )

    def enqueue(
        self, description: str, tv_key: str, source: str
    ) -> JobRecord:
        now = _timestamp()
        job = JobRecord(
            id=str(uuid.uuid4()),
            description=description,
            tv_key=tv_key,
            source=source,
            status=JobStatus.QUEUED,
            message="Waiting to generate",
            created_at=now,
            updated_at=now,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    id, description, tv_key, source, status, message,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.description,
                    job.tv_key,
                    job.source,
                    job.status,
                    job.message,
                    job.created_at,
                    job.updated_at,
                ),
            )
        return job

    def claim_next(self) -> JobRecord | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT * FROM jobs
                WHERE status = ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (JobStatus.QUEUED,),
            ).fetchone()
            if row is None:
                return None
            now = _timestamp()
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, message = ?, updated_at = ?
                WHERE id = ? AND status = ?
                """,
                (
                    JobStatus.RUNNING,
                    "Generating image",
                    now,
                    row["id"],
                    JobStatus.QUEUED,
                ),
            )
            return JobRecord(
                id=row["id"],
                description=row["description"],
                tv_key=row["tv_key"],
                source=row["source"],
                status=JobStatus.RUNNING,
                message="Generating image",
                created_at=row["created_at"],
                updated_at=now,
            )

    def get(self, job_id: str) -> JobRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
        return _row_to_job(row) if row is not None else None

    def complete(self, job_id: str, message: str) -> None:
        self._finish(job_id, JobStatus.COMPLETED, message)

    def fail(self, job_id: str, message: str) -> None:
        self._finish(job_id, JobStatus.FAILED, message)

    def _finish(self, job_id: str, status: JobStatus, message: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs
                SET status = ?, message = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, message, _timestamp(), job_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Generation job '{job_id}' does not exist")

    def record_artwork(
        self, content_id: str, job_id: str, tv_key: str
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO artworks (
                    content_id, job_id, tv_key, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (content_id, job_id, tv_key, _timestamp()),
            )

    def stale_artworks(
        self, tv_key: str, keep_count: int
    ) -> list[ArtworkRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT content_id, tv_key FROM artworks
                WHERE tv_key = ?
                ORDER BY created_at DESC, rowid DESC
                LIMIT -1 OFFSET ?
                """,
                (tv_key, keep_count),
            ).fetchall()
        return [
            ArtworkRecord(content_id=row["content_id"], tv_key=row["tv_key"])
            for row in rows
        ]

    def forget_artwork(self, content_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM artworks WHERE content_id = ?", (content_id,)
            )


def _row_to_job(row: sqlite3.Row) -> JobRecord:
    return JobRecord(
        id=row["id"],
        description=row["description"],
        tv_key=row["tv_key"],
        source=row["source"],
        status=JobStatus(row["status"]),
        message=row["message"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
