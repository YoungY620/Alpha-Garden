#!/usr/bin/env python3
"""Serve a generated dashboard and four read-only experiment APIs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiment_db import connect


def _decode(row: dict, *fields: str) -> dict:
    for field in fields:
        value = row.get(field)
        row[field.removesuffix("_json")] = json.loads(value or "{}")
        row.pop(field, None)
    return row


def _candidate(row: dict) -> dict:
    row = _decode(row, "parent_ids_json", "metrics_json")
    for field in ("is_valid", "is_qualified"):
        if row.get(field) is not None:
            row[field] = bool(row[field])
    return row


def create_app(database: Path, frontend: Path):
    try:
        from flask import Flask, abort, jsonify, request, send_from_directory
    except ImportError as error:
        raise SystemExit("Flask is required; run bootstrap_runtime.py") from error

    database = database.resolve()
    frontend = frontend.resolve()
    app = Flask(__name__, static_folder=None)

    def query_one(sql: str, values: tuple = ()) -> dict | None:
        connection = connect(database, readonly=True)
        try:
            row = connection.execute(sql, values).fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    def query_all(sql: str, values: tuple = ()) -> list[dict]:
        connection = connect(database, readonly=True)
        try:
            return [dict(row) for row in connection.execute(sql, values)]
        finally:
            connection.close()

    @app.get("/api/health")
    def health():
        run = query_one("SELECT schema_version, experiment_id, phase, revision, updated_at FROM run WHERE singleton = 1")
        return jsonify({"ok": run is not None, "run": run})

    @app.get("/api/snapshot")
    def snapshot():
        run = query_one("SELECT * FROM run WHERE singleton = 1")
        if run is None:
            abort(503)
        revision = str(run["revision"])
        if request.if_none_match.contains(revision):
            return "", 304
        run = _decode(run, "data_access_json")
        task_counts = {
            row["status"]: row["count"]
            for row in query_all("SELECT status, COUNT(*) AS count FROM tasks GROUP BY status")
        }
        generations = [
            _decode(row, "metrics_json")
            for row in query_all("SELECT * FROM generations ORDER BY generation")
        ]
        current = run.get("current_generation")
        candidates = [] if current is None else [
            _candidate(row)
            for row in query_all(
                """
                SELECT candidate_id, task_id, generation, expert_id, guidance_mode,
                       parent_ids_json, status, is_valid, is_qualified, fitness,
                       violation_score, complexity, summary, metrics_json, artifact, updated_at
                FROM candidates WHERE generation = ? ORDER BY candidate_id
                """,
                (current,),
            )
        ]
        events = [
            _decode(row, "payload_json")
            for row in query_all("SELECT * FROM events ORDER BY sequence DESC LIMIT 20")
        ]
        response = jsonify({"run": run, "task_counts": task_counts, "generations": generations, "candidates": candidates, "recent_events": events})
        response.set_etag(revision)
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/api/generations/<int:generation>")
    def generation_detail(generation: int):
        summary = query_one("SELECT * FROM generations WHERE generation = ?", (generation,))
        if summary is None:
            abort(404)
        candidates = [
            _candidate(row)
            for row in query_all("SELECT * FROM candidates WHERE generation = ? ORDER BY candidate_id", (generation,))
        ]
        return jsonify({"generation": _decode(summary, "metrics_json"), "candidates": candidates})

    @app.get("/api/candidates/<candidate_id>")
    def candidate_detail(candidate_id: str):
        row = query_one("SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,))
        if row is None:
            abort(404)
        return jsonify(_candidate(row))

    @app.get("/")
    def index():
        if not (frontend / "index.html").is_file():
            abort(503, "generated dashboard is not ready")
        return send_from_directory(frontend, "index.html")

    @app.get("/<path:name>")
    def static_file(name: str):
        return send_from_directory(frontend, name)

    return app


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("frontend", type=Path)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    app = create_app(args.database, args.frontend)
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
