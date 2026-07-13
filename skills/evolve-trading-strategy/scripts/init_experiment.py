#!/usr/bin/env python3
"""Create a portable draft experiment and its authoritative SQLite state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiment_db import initialize


SPEC = {
    "schema_version": "experiment-spec/v1",
    "experiment_id": "replace-with-stable-id",
    "version": 1,
    "status": "draft",
    "idea_summary": "",
    "knowledge_sources": [],
    "instrument": {"symbol": "", "venue": "", "currency": "", "timezone": "UTC"},
    "bar_interval": "",
    "holding_horizon": "",
    "primary_objective": "",
    "benchmark": "",
    "binding_constraints": [],
    "soft_preferences": [],
    "testable_hypotheses": [],
    "creative_zone": [],
    "data": {"bars": "", "auxiliary": []},
    "execution": {
        "contract": "bar-v1",
        "decision_timing": "bar_close_t",
        "execution_timing": "bar_open_t_plus_1",
        "fees_bps": None,
        "slippage_bps": None,
        "allow_short": False,
        "allow_leverage": False,
    },
    "splits": {"train": {}, "validation": {}, "sealed_test": {}, "purge_bars": None, "embargo_bars": None},
    "risk_gates": {},
    "complexity": {"max_logical_steps": 5, "max_tunable_parameters": 8},
    "search_budget": {"max_generations": None, "generation0_population": 22, "population_target": 42},
    "dashboard_brief": {
        "language": "",
        "visual_direction": "",
        "information_density": "dense",
        "preferred_chart_library": "@visactor/vchart",
    },
    "confirmation": {"confirmed": False, "confirmed_at": None},
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path, help="Experiment directory")
    args = parser.parse_args()
    root = args.output
    root.mkdir(parents=True, exist_ok=False)
    for name in ("artifacts", "candidates", "dashboard", "data", "reports", "tasks", "tmp"):
        (root / name).mkdir()
    (root / "experiment-spec.json").write_text(json.dumps(SPEC, indent=2) + "\n", encoding="utf-8")
    initialize(root / "experiment.sqlite", SPEC["experiment_id"])
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
