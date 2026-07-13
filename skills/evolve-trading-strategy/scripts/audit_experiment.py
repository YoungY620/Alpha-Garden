#!/usr/bin/env python3
"""Audit spec confirmation, split sealing, hashes, and unique test opening."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    issues: list[str] = []
    spec_path = args.experiment / "experiment-spec.json"
    database_path = args.experiment / "experiment.sqlite"
    if not spec_path.exists():
        issues.append("missing experiment-spec.json")
        spec = {}
    else:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        if not spec.get("confirmation", {}).get("confirmed"):
            issues.append("experiment spec is not confirmed")
        for name in ("train", "validation", "sealed_test"):
            if not spec.get("splits", {}).get(name):
                issues.append(f"missing split: {name}")
    spec_digest = hashlib.sha256(spec_path.read_bytes()).hexdigest() if spec_path.exists() else None
    events = 0
    openings = 0
    stored_digest = None
    if not database_path.exists():
        issues.append("missing experiment.sqlite")
    else:
        connection = sqlite3.connect(database_path)
        try:
            stored = connection.execute("SELECT spec_sha256 FROM run WHERE singleton = 1").fetchone()
            stored_digest = stored[0] if stored else None
            events = int(connection.execute("SELECT COUNT(*) FROM events").fetchone()[0])
            openings = int(connection.execute("SELECT COUNT(*) FROM events WHERE event_type = 'sealed_test_opened'").fetchone()[0])
        finally:
            connection.close()
    if stored_digest != spec_digest:
        issues.append("confirmed experiment spec hash does not match SQLite state")
    if openings > 1:
        issues.append("sealed test was opened more than once")
    report = {
        "schema_version": "experiment-audit/v1",
        "accepted": not issues,
        "issues": issues,
        "spec_sha256": spec_digest,
        "database_sha256": hashlib.sha256(database_path.read_bytes()).hexdigest() if database_path.exists() else None,
        "sealed_test_open_count": openings,
        "ledger_events": events,
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
