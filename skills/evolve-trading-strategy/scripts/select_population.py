#!/usr/bin/env python3
"""Select a fixed-size breeding population from valid parents and children."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _rank(row: dict) -> tuple:
    return (
        float(row.get("violation_score", 1_000_000_000.0)),
        -float(row.get("fitness", -1_000_000_000.0)),
        int(row.get("logical_steps", 999)),
        float(row.get("turnover", 1_000_000_000.0)),
        str(row.get("candidate_id", "")),
    )


def select(rows: list[dict], target: int) -> list[dict]:
    ranked = sorted((row for row in rows if row.get("is_valid") is True), key=_rank)
    unique: list[dict] = []
    seen_ids: set[str] = set()
    seen_fingerprints: set[str] = set()
    for row in ranked:
        candidate_id = str(row.get("candidate_id", ""))
        fingerprint = str(row.get("behavior_fingerprint", ""))
        if not candidate_id or candidate_id in seen_ids:
            continue
        if fingerprint and fingerprint in seen_fingerprints:
            continue
        unique.append(row)
        seen_ids.add(candidate_id)
        if fingerprint:
            seen_fingerprints.add(fingerprint)

    champions: list[dict] = []
    champion_ids: set[str] = set()
    seen_experts: set[str] = set()
    for row in unique:
        expert = str(row.get("expert_id", "unknown"))
        if expert in seen_experts:
            continue
        champions.append({**row, "selection_reason": "expert_champion"})
        champion_ids.add(str(row["candidate_id"]))
        seen_experts.add(expert)
        if len(champions) >= target:
            return champions

    selected = list(champions)
    for row in unique:
        if len(selected) >= target:
            break
        if str(row["candidate_id"]) in champion_ids:
            continue
        selected.append({**row, "selection_reason": "global_rank_fill"})
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluated", required=True, nargs="+", type=Path, help="Evaluated parent and child JSONL files")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target", type=int, default=42)
    args = parser.parse_args()
    if args.target < 1:
        raise SystemExit("population target must be positive")
    rows = [
        json.loads(line)
        for path in args.evaluated
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    chosen = select(rows, args.target)
    args.output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in chosen), encoding="utf-8")
    summary = {
        "selected": len(chosen),
        "target": args.target,
        "complete": len(chosen) == args.target,
        "replenish_count": max(0, args.target - len(chosen)),
        "qualified_selected": sum(row.get("is_qualified") is True for row in chosen),
    }
    print(json.dumps(summary))
    return 0 if summary["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
