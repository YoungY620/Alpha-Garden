#!/usr/bin/env python3
"""Shared SQLite schema and transaction helpers for one experiment."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = "experiment-db/v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    path = path.resolve()
    if readonly:
        connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2.0)
        connection.execute("PRAGMA query_only=ON")
    else:
        connection = sqlite3.connect(path, timeout=5.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=2000")
    return connection


def initialize(path: Path, experiment_id: str = "replace-with-stable-id") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(path)
    with connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS run (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                schema_version TEXT NOT NULL,
                experiment_id TEXT NOT NULL,
                spec_sha256 TEXT,
                status TEXT NOT NULL,
                phase TEXT NOT NULL,
                current_generation INTEGER,
                revision INTEGER NOT NULL,
                data_access_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                task_sha256 TEXT NOT NULL,
                generation INTEGER NOT NULL,
                expert_id TEXT,
                guidance_mode TEXT,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                worker_id TEXT,
                lease_expires_at TEXT,
                heartbeat_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                artifact TEXT,
                reason TEXT
            );

            CREATE TABLE IF NOT EXISTS candidates (
                candidate_id TEXT PRIMARY KEY,
                task_id TEXT,
                generation INTEGER NOT NULL,
                expert_id TEXT,
                guidance_mode TEXT,
                parent_ids_json TEXT NOT NULL,
                status TEXT NOT NULL,
                is_valid INTEGER,
                is_qualified INTEGER,
                fitness REAL,
                violation_score REAL,
                complexity REAL,
                summary TEXT,
                metrics_json TEXT NOT NULL,
                artifact TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(task_id) REFERENCES tasks(task_id)
            );

            CREATE TABLE IF NOT EXISTS generations (
                generation INTEGER PRIMARY KEY,
                target_population INTEGER,
                selected_population INTEGER,
                valid_count INTEGER,
                qualified_count INTEGER,
                status TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                research_note TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                occurred_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                generation INTEGER,
                task_id TEXT,
                candidate_id TEXT,
                message TEXT,
                payload_json TEXT NOT NULL,
                idempotency_key TEXT UNIQUE
            );

            CREATE INDEX IF NOT EXISTS tasks_status_idx ON tasks(status, generation, task_id);
            CREATE INDEX IF NOT EXISTS candidates_generation_idx ON candidates(generation, candidate_id);
            CREATE INDEX IF NOT EXISTS events_generation_idx ON events(generation, sequence);
            """
        )
        now = utc_now()
        connection.execute(
            """
            INSERT OR IGNORE INTO run (
                singleton, schema_version, experiment_id, status, phase,
                current_generation, revision, data_access_json, created_at, updated_at
            ) VALUES (1, ?, ?, 'draft', 'grilling', NULL, 0, '{}', ?, ?)
            """,
            (SCHEMA_VERSION, experiment_id, now, now),
        )
    connection.close()


def append_event(
    connection: sqlite3.Connection,
    event_type: str,
    *,
    generation: int | None = None,
    task_id: str | None = None,
    candidate_id: str | None = None,
    message: str | None = None,
    payload: dict | None = None,
    idempotency_key: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO events (
            occurred_at, event_type, generation, task_id, candidate_id,
            message, payload_json, idempotency_key
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            utc_now(),
            event_type,
            generation,
            task_id,
            candidate_id,
            message,
            json.dumps(payload or {}, sort_keys=True),
            idempotency_key,
        ),
    )


def bump_revision(connection: sqlite3.Connection) -> int:
    now = utc_now()
    connection.execute(
        "UPDATE run SET revision = revision + 1, updated_at = ? WHERE singleton = 1",
        (now,),
    )
    return int(connection.execute("SELECT revision FROM run WHERE singleton = 1").fetchone()[0])

