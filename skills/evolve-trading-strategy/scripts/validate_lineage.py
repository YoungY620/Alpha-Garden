#!/usr/bin/env python3
"""Validate an append-only candidate lineage DAG stored as JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("lineage", type=Path)
    args = parser.parse_args()
    nodes = [json.loads(line) for line in args.lineage.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {node.get("candidate_id"): node for node in nodes}
    issues: list[str] = []
    if None in by_id or len(by_id) != len(nodes):
        issues.append("candidate IDs are missing or duplicated")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(candidate_id: str) -> None:
        if candidate_id in visiting:
            issues.append(f"lineage cycle detected at {candidate_id}")
            return
        if candidate_id in visited:
            return
        visiting.add(candidate_id)
        for parent in by_id.get(candidate_id, {}).get("parents", []):
            if parent not in by_id:
                issues.append(f"unknown parent {parent} for {candidate_id}")
            else:
                visit(parent)
        visiting.remove(candidate_id)
        visited.add(candidate_id)

    for candidate_id in sorted(value for value in by_id if value is not None):
        visit(candidate_id)
    report = {"accepted": not issues, "issues": list(dict.fromkeys(issues)), "nodes": len(nodes)}
    print(json.dumps(report))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
