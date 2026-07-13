#!/usr/bin/env python3
"""Transactionally manage experiment tasks, candidates, generations, and events."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from experiment_db import append_event, bump_revision, connect, initialize, utc_now


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return value


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _relative(value: str | None) -> str | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise SystemExit("artifact paths must be relative and cannot contain '..'")
    return path.as_posix()


def _lease(seconds: int) -> str:
    value = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    return value.isoformat().replace("+00:00", "Z")


def _print(row: object) -> None:
    if hasattr(row, "keys"):
        row = dict(row)  # type: ignore[arg-type]
    print(json.dumps(row, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument(
        "action",
        choices=(
            "init",
            "confirm",
            "tasks-init",
            "task-claim",
            "task-heartbeat",
            "task-complete",
            "task-fail",
            "task-retry",
            "recover-expired",
            "candidate",
            "generation",
            "phase",
            "note",
            "sealed-open",
            "summary",
            "export-events",
        ),
    )
    parser.add_argument("--experiment-id")
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--tasks", type=Path)
    parser.add_argument("--task-id")
    parser.add_argument("--worker-id")
    parser.add_argument("--lease-seconds", type=int, default=900)
    parser.add_argument("--artifact")
    parser.add_argument("--reason")
    parser.add_argument("--record", type=Path)
    parser.add_argument("--name")
    parser.add_argument("--generation", type=int)
    parser.add_argument("--message")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.action == "init":
        initialize(args.database, args.experiment_id or "replace-with-stable-id")
        _print({"initialized": True, "database": args.database.name})
        return 0

    connection = connect(args.database)

    if args.action == "summary":
        run = dict(connection.execute("SELECT * FROM run WHERE singleton = 1").fetchone())
        counts = {
            row["status"]: row["count"]
            for row in connection.execute("SELECT status, COUNT(*) AS count FROM tasks GROUP BY status")
        }
        _print({"revision": run["revision"], "phase": run["phase"], "generation": run["current_generation"], "tasks": counts})
        return 0

    if args.action == "export-events":
        if not args.output:
            raise SystemExit("--output is required")
        rows = [dict(row) for row in connection.execute("SELECT * FROM events ORDER BY sequence")]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
        _print({"exported": len(rows), "output": args.output.name})
        return 0

    connection.execute("BEGIN IMMEDIATE")
    try:
        result: dict = {}
        if args.action == "confirm":
            if not args.spec:
                raise SystemExit("--spec is required")
            spec = _read_json(args.spec)
            confirmation = spec.get("confirmation", {})
            if not confirmation.get("confirmed") or not confirmation.get("confirmed_at"):
                raise SystemExit("experiment spec is not confirmed")
            digest = hashlib.sha256(args.spec.read_bytes()).hexdigest()
            connection.execute(
                """
                UPDATE run SET experiment_id = ?, spec_sha256 = ?, status = 'confirmed',
                    phase = 'dashboard_setup' WHERE singleton = 1
                """,
                (spec["experiment_id"], digest),
            )
            append_event(connection, "experiment_confirmed", message="Experiment specification confirmed", payload={"spec_sha256": digest})
            result = {"confirmed": True, "spec_sha256": digest}

        elif args.action == "tasks-init":
            if not args.tasks:
                raise SystemExit("--tasks is required")
            rows = _read_jsonl(args.tasks)
            inserted = 0
            for task in rows:
                existing = connection.execute("SELECT task_sha256 FROM tasks WHERE task_id = ?", (task["task_id"],)).fetchone()
                if existing:
                    if existing["task_sha256"] != task["task_sha256"]:
                        raise SystemExit(f"task hash changed: {task['task_id']}")
                    continue
                cell = task.get("cell", {})
                connection.execute(
                    """
                    INSERT INTO tasks (
                        task_id, task_sha256, generation, expert_id, guidance_mode,
                        status, attempts, max_attempts
                    ) VALUES (?, ?, ?, ?, ?, 'pending', 0, 3)
                    """,
                    (
                        task["task_id"],
                        task["task_sha256"],
                        int(task["generation"]),
                        cell.get("expert_id"),
                        cell.get("guidance_mode"),
                    ),
                )
                inserted += 1
            append_event(connection, "tasks_initialized", generation=rows[0]["generation"] if rows else None, payload={"inserted": inserted})
            result = {"inserted": inserted, "total": len(rows)}

        elif args.action == "task-claim":
            if not args.worker_id:
                raise SystemExit("--worker-id is required")
            row = connection.execute(
                """
                SELECT * FROM tasks
                WHERE status = 'pending' AND attempts < max_attempts
                ORDER BY generation, task_id LIMIT 1
                """
            ).fetchone()
            if row is None:
                connection.rollback()
                _print({})
                return 0
            now = utc_now()
            connection.execute(
                """
                UPDATE tasks SET status = 'running', attempts = attempts + 1,
                    worker_id = ?, lease_expires_at = ?, heartbeat_at = ?,
                    started_at = COALESCE(started_at, ?), reason = NULL
                WHERE task_id = ? AND status = 'pending'
                """,
                (args.worker_id, _lease(args.lease_seconds), now, now, row["task_id"]),
            )
            append_event(connection, "task_started", generation=row["generation"], task_id=row["task_id"], payload={"worker_id": args.worker_id})
            result = dict(connection.execute("SELECT * FROM tasks WHERE task_id = ?", (row["task_id"],)).fetchone())

        elif args.action == "task-heartbeat":
            if not args.task_id or not args.worker_id:
                raise SystemExit("--task-id and --worker-id are required")
            now = utc_now()
            cursor = connection.execute(
                """
                UPDATE tasks SET heartbeat_at = ?, lease_expires_at = ?
                WHERE task_id = ? AND status = 'running' AND worker_id = ?
                """,
                (now, _lease(args.lease_seconds), args.task_id, args.worker_id),
            )
            if cursor.rowcount != 1:
                raise SystemExit("heartbeat requires the current running worker")
            connection.commit()
            revision = int(connection.execute("SELECT revision FROM run WHERE singleton = 1").fetchone()[0])
            _print({"task_id": args.task_id, "heartbeat_at": now, "revision": revision})
            return 0

        elif args.action in {"task-complete", "task-fail"}:
            if not args.task_id:
                raise SystemExit("--task-id is required")
            row = connection.execute("SELECT * FROM tasks WHERE task_id = ?", (args.task_id,)).fetchone()
            if row is None or row["status"] != "running":
                raise SystemExit("task must be running")
            if args.worker_id and row["worker_id"] != args.worker_id:
                raise SystemExit("worker does not own task")
            if args.action == "task-complete":
                if not args.artifact:
                    raise SystemExit("--artifact is required")
                connection.execute(
                    """
                    UPDATE tasks SET status = 'complete', completed_at = ?, artifact = ?,
                        lease_expires_at = NULL, heartbeat_at = NULL
                    WHERE task_id = ?
                    """,
                    (utc_now(), _relative(args.artifact), args.task_id),
                )
                append_event(connection, "task_completed", generation=row["generation"], task_id=args.task_id)
            else:
                if not args.reason:
                    raise SystemExit("--reason is required")
                connection.execute(
                    """
                    UPDATE tasks SET status = 'failed', reason = ?, lease_expires_at = NULL,
                        heartbeat_at = NULL WHERE task_id = ?
                    """,
                    (args.reason, args.task_id),
                )
                append_event(connection, "task_failed", generation=row["generation"], task_id=args.task_id, message=args.reason)
            result = dict(connection.execute("SELECT * FROM tasks WHERE task_id = ?", (args.task_id,)).fetchone())

        elif args.action == "task-retry":
            if not args.task_id:
                raise SystemExit("--task-id is required")
            row = connection.execute("SELECT * FROM tasks WHERE task_id = ?", (args.task_id,)).fetchone()
            if row is None or row["status"] != "failed" or row["attempts"] >= row["max_attempts"]:
                raise SystemExit("retry requires a failed task below its attempt limit")
            connection.execute(
                """
                UPDATE tasks SET status = 'pending', worker_id = NULL, reason = NULL,
                    lease_expires_at = NULL, heartbeat_at = NULL WHERE task_id = ?
                """,
                (args.task_id,),
            )
            append_event(connection, "task_retried", generation=row["generation"], task_id=args.task_id)
            result = dict(connection.execute("SELECT * FROM tasks WHERE task_id = ?", (args.task_id,)).fetchone())

        elif args.action == "recover-expired":
            now = utc_now()
            rows = list(connection.execute("SELECT * FROM tasks WHERE status = 'running' AND lease_expires_at < ?", (now,)))
            for row in rows:
                status = "pending" if row["attempts"] < row["max_attempts"] else "failed"
                connection.execute(
                    """
                    UPDATE tasks SET status = ?, worker_id = NULL, lease_expires_at = NULL,
                        heartbeat_at = NULL, reason = 'lease expired' WHERE task_id = ?
                    """,
                    (status, row["task_id"]),
                )
                append_event(connection, "task_lease_expired", generation=row["generation"], task_id=row["task_id"], payload={"next_status": status})
            result = {"recovered": len(rows)}

        elif args.action == "candidate":
            if not args.record:
                raise SystemExit("--record is required")
            record = _read_json(args.record)
            candidate_id = record["candidate_id"]
            now = utc_now()
            connection.execute(
                """
                INSERT INTO candidates (
                    candidate_id, task_id, generation, expert_id, guidance_mode,
                    parent_ids_json, status, is_valid, is_qualified, fitness,
                    violation_score, complexity, summary, metrics_json, artifact, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(candidate_id) DO UPDATE SET
                    status=excluded.status, is_valid=excluded.is_valid,
                    is_qualified=excluded.is_qualified, fitness=excluded.fitness,
                    violation_score=excluded.violation_score, complexity=excluded.complexity,
                    summary=excluded.summary, metrics_json=excluded.metrics_json,
                    artifact=excluded.artifact, updated_at=excluded.updated_at
                """,
                (
                    candidate_id,
                    record.get("task_id"),
                    int(record["generation"]),
                    record.get("expert_id"),
                    record.get("guidance_mode"),
                    json.dumps(record.get("parent_ids", []), sort_keys=True),
                    record.get("status", "evaluated"),
                    record.get("is_valid"),
                    record.get("is_qualified"),
                    record.get("fitness"),
                    record.get("violation_score"),
                    record.get("complexity"),
                    record.get("summary"),
                    json.dumps(record.get("metrics", {}), sort_keys=True),
                    _relative(record.get("artifact")),
                    now,
                ),
            )
            append_event(connection, "candidate_updated", generation=int(record["generation"]), task_id=record.get("task_id"), candidate_id=candidate_id)
            result = {"candidate_id": candidate_id, "updated": True}

        elif args.action == "generation":
            if not args.record:
                raise SystemExit("--record is required")
            record = _read_json(args.record)
            generation = int(record["generation"])
            connection.execute(
                """
                INSERT INTO generations (
                    generation, target_population, selected_population, valid_count,
                    qualified_count, status, metrics_json, research_note, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(generation) DO UPDATE SET
                    target_population=excluded.target_population,
                    selected_population=excluded.selected_population,
                    valid_count=excluded.valid_count, qualified_count=excluded.qualified_count,
                    status=excluded.status, metrics_json=excluded.metrics_json,
                    research_note=excluded.research_note, updated_at=excluded.updated_at
                """,
                (
                    generation,
                    record.get("target_population"),
                    record.get("selected_population"),
                    record.get("valid_count"),
                    record.get("qualified_count"),
                    record.get("status", "running"),
                    json.dumps(record.get("metrics", {}), sort_keys=True),
                    record.get("research_note"),
                    utc_now(),
                ),
            )
            append_event(connection, "generation_updated", generation=generation, message=record.get("research_note"))
            result = {"generation": generation, "updated": True}

        elif args.action == "phase":
            if not args.name:
                raise SystemExit("--name is required")
            connection.execute(
                "UPDATE run SET phase = ?, current_generation = COALESCE(?, current_generation) WHERE singleton = 1",
                (args.name, args.generation),
            )
            append_event(connection, "phase_changed", generation=args.generation, message=args.name)
            result = {"phase": args.name, "generation": args.generation}

        elif args.action == "note":
            if not args.message:
                raise SystemExit("--message is required")
            append_event(connection, "research_note", generation=args.generation, message=args.message)
            result = {"recorded": True}

        elif args.action == "sealed-open":
            existing = connection.execute("SELECT COUNT(*) FROM events WHERE event_type = 'sealed_test_opened'").fetchone()[0]
            if existing:
                raise SystemExit("sealed test was already opened")
            append_event(connection, "sealed_test_opened", message="Sealed test opened", payload={"artifact": _relative(args.artifact)})
            result = {"sealed_test_opened": True}

        revision = bump_revision(connection)
        connection.commit()
        result["revision"] = revision
        _print(result)
        return 0
    except Exception:
        connection.rollback()
        raise


if __name__ == "__main__":
    raise SystemExit(main())
