#!/usr/bin/env python3
"""Validate a structured candidate response and its declared artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


REQUIRED = {
    "schema_version",
    "candidate_id",
    "task_id",
    "hypothesis",
    "mechanism_tags",
    "entry_logic",
    "exit_logic",
    "sizing_logic",
    "parameter_schema",
    "parent_contributions",
    "semantic_delta",
    "assumptions",
    "failure_modes",
    "code_sha256",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path, help="candidate.json")
    parser.add_argument("--strategy", required=True, type=Path)
    parser.add_argument("--params", type=Path)
    parser.add_argument("--task-id")
    parser.add_argument("--task", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.candidate.read_text(encoding="utf-8"))
    issues: list[str] = []
    missing = sorted(REQUIRED - payload.keys())
    if missing:
        issues.append(f"missing fields: {missing}")
    if payload.get("schema_version") != "candidate-response/v1":
        issues.append("unexpected candidate response version")
    task = json.loads(args.task.read_text(encoding="utf-8")) if args.task else None
    expected_task_id = task.get("task_id") if task else args.task_id
    if not expected_task_id:
        raise SystemExit("provide --task or --task-id")
    if payload.get("task_id") != expected_task_id:
        issues.append("task ID mismatch")
    if task:
        if payload.get("task_sha256") != task.get("task_sha256"):
            issues.append("task hash mismatch")
        constraints = task.get("constraints", {})
        parameters = payload.get("parameter_schema", {})
        if len(parameters) > int(constraints.get("max_tunable_parameters", 8)):
            issues.append("parameter count exceeds task complexity limit")
        if int(payload.get("logical_steps", 999)) > int(constraints.get("max_logical_steps", 5)):
            issues.append("logical step count exceeds task complexity limit")
        if constraints.get("single_primary_hypothesis") and payload.get("single_primary_hypothesis") is not True:
            issues.append("candidate does not declare one primary hypothesis")
        if constraints.get("blind_split_access") is False and payload.get("blind_split_access") is not False:
            issues.append("candidate did not prove blind split remained inaccessible")
    if args.params:
        parameter_values = json.loads(args.params.read_text(encoding="utf-8"))
        if set(parameter_values) != set(payload.get("parameter_schema", {})):
            issues.append("parameter values do not match candidate parameter schema")
    actual_hash = hashlib.sha256(args.strategy.read_bytes()).hexdigest()
    if payload.get("code_sha256") != actual_hash:
        issues.append("strategy hash mismatch")
    if not isinstance(payload.get("mechanism_tags"), list) or not payload.get("mechanism_tags"):
        issues.append("mechanism_tags must be a non-empty list")
    report = {"accepted": not issues, "issues": issues, "code_sha256": actual_hash}
    print(json.dumps(report))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
