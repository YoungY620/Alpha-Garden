#!/usr/bin/env python3
"""Exercise the portable deterministic parts of the skill."""

from __future__ import annotations

import json
import hashlib
import os
import runpy
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
ASSETS = SKILL / "assets"
sys.path.insert(0, str(SCRIPTS))


def run(*args: object, expected: int = 0) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, *map(str, args)]
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(command, capture_output=True, text=True, check=False, env=environment)
    if result.returncode != expected:
        raise AssertionError(f"command failed: {command}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        experiment = root / "experiment"
        run(SCRIPTS / "init_experiment.py", experiment)
        spec_path = experiment / "experiment-spec.json"
        database = experiment / "experiment.sqlite"
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        spec.update({"experiment_id": "smoke-v1", "bar_interval": "1h"})
        spec["instrument"].update({"symbol": "EXAMPLE", "venue": "SIM", "currency": "USD"})
        spec["confirmation"].update({"confirmed": True, "confirmed_at": "YYYY-MM-DDT00:00:00Z"})
        spec["splits"] = {
            "train": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
            "validation": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
            "sealed_test": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
            "purge_bars": 48,
            "embargo_bars": 48,
        }
        spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        run(SCRIPTS / "manage_experiment.py", database, "confirm", "--spec", spec_path)

        generation_zero = root / "g0.jsonl"
        run(SCRIPTS / "build_generation_tasks.py", "--spec", spec_path, "--generation", 0, "--output", generation_zero)
        assert len(generation_zero.read_text(encoding="utf-8").splitlines()) == 22

        task_module = runpy.run_path(str(SCRIPTS / "build_generation_tasks.py"))
        parent_map = {
            f"g001__{expert[0]}__{mode}": ["candidate-a", "candidate-b"]
            for expert in task_module["EXPERTS"]
            for mode in task_module["MODES"]
        }
        parent_path = root / "parents.json"
        parent_path.write_text(json.dumps(parent_map), encoding="utf-8")
        context_path = root / "context.json"
        context_path.write_text(
            json.dumps(
                {
                    task_id: {
                        "effective_memory_ids": ["effective-a", "effective-b"],
                        "ineffective_memory_ids": ["failure-a"],
                        "knowledge_excerpt_ids": [],
                        "novelty_constraints": ["not a parameter-only clone"],
                    }
                    for task_id in parent_map
                }
            ),
            encoding="utf-8",
        )
        generation_one = root / "g1.jsonl"
        run(
            SCRIPTS / "build_generation_tasks.py",
            "--spec",
            spec_path,
            "--generation",
            1,
            "--parents",
            parent_path,
            "--context",
            context_path,
            "--output",
            generation_one,
        )
        assert len(generation_one.read_text(encoding="utf-8").splitlines()) == 105
        run(SCRIPTS / "manage_experiment.py", database, "tasks-init", "--tasks", generation_one)
        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [
                pool.submit(
                    run,
                    SCRIPTS / "manage_experiment.py",
                    database,
                    "task-claim",
                    "--worker-id",
                    f"worker-{index:02d}",
                )
                for index in range(16)
            ]
        claimed = [json.loads(future.result().stdout) for future in futures]
        claimed_ids = [row["task_id"] for row in claimed]
        assert len(claimed_ids) == len(set(claimed_ids)) == 16
        queue_task_id = claimed[0]["task_id"]
        worker_id = claimed[0]["worker_id"]
        revision_before_heartbeat = json.loads(
            run(SCRIPTS / "manage_experiment.py", database, "summary").stdout
        )["revision"]
        heartbeat = run(
            SCRIPTS / "manage_experiment.py",
            database,
            "task-heartbeat",
            "--task-id",
            queue_task_id,
            "--worker-id",
            worker_id,
        )
        assert json.loads(heartbeat.stdout)["revision"] == revision_before_heartbeat
        run(
            SCRIPTS / "manage_experiment.py",
            database,
            "task-fail",
            "--task-id",
            queue_task_id,
            "--worker-id",
            worker_id,
            "--reason",
            "fixture failure",
        )
        run(SCRIPTS / "manage_experiment.py", database, "task-retry", "--task-id", queue_task_id)

        completed = claimed[1]
        run(
            SCRIPTS / "manage_experiment.py",
            database,
            "task-complete",
            "--task-id",
            completed["task_id"],
            "--worker-id",
            completed["worker_id"],
            "--artifact",
            "candidates/fixture",
        )

        candidate_record = root / "dashboard-candidate.json"
        candidate_record.write_text(
            json.dumps(
                {
                    "candidate_id": "dashboard-candidate",
                    "task_id": completed["task_id"],
                    "generation": 1,
                    "expert_id": completed["expert_id"],
                    "guidance_mode": completed["guidance_mode"],
                    "parent_ids": ["candidate-a", "candidate-b"],
                    "status": "evaluated",
                    "is_valid": True,
                    "is_qualified": False,
                    "fitness": 0.4,
                    "violation_score": 1.5,
                    "complexity": 3,
                    "summary": "fixture dashboard candidate",
                    "metrics": {"existing_metric": 0.4},
                    "artifact": "candidates/fixture",
                }
            ),
            encoding="utf-8",
        )
        run(SCRIPTS / "manage_experiment.py", database, "candidate", "--record", candidate_record)
        generation_record = root / "dashboard-generation.json"
        generation_record.write_text(
            json.dumps(
                {
                    "generation": 1,
                    "target_population": 42,
                    "selected_population": 1,
                    "valid_count": 1,
                    "qualified_count": 0,
                    "status": "running",
                    "metrics": {"best_fitness": 0.4},
                    "research_note": "fixture generation note",
                }
            ),
            encoding="utf-8",
        )
        run(SCRIPTS / "manage_experiment.py", database, "generation", "--record", generation_record)
        run(SCRIPTS / "manage_experiment.py", database, "phase", "--name", "generation", "--generation", 1)

        dashboard = experiment / "dashboard"
        (dashboard / "index.html").write_text("<!doctype html><title>Fixture dashboard</title>", encoding="utf-8")
        dashboard_module = runpy.run_path(str(SCRIPTS / "serve_dashboard.py"))
        app = dashboard_module["create_app"](database, dashboard)
        client = app.test_client()
        assert client.get("/").status_code == 200
        assert client.get("/api/health").get_json()["ok"]
        snapshot_response = client.get("/api/snapshot")
        assert snapshot_response.status_code == 200
        snapshot = snapshot_response.get_json()
        assert snapshot["run"]["phase"] == "generation"
        assert snapshot["task_counts"]["complete"] == 1
        assert snapshot["candidates"][0]["candidate_id"] == "dashboard-candidate"
        assert client.get("/api/snapshot", headers={"If-None-Match": snapshot_response.headers["ETag"]}).status_code == 304
        assert client.get("/api/generations/1").status_code == 200
        assert client.get("/api/candidates/dashboard-candidate").status_code == 200
        assert client.post("/api/snapshot").status_code == 405

        strategy_report = root / "strategy-audit.json"
        run(SCRIPTS / "validate_strategy.py", ASSETS / "strategy-template" / "final_strategy.py", "--report", strategy_report)
        assert json.loads(strategy_report.read_text(encoding="utf-8"))["accepted"]
        runtime_report = root / "strategy-runtime-audit.json"
        run(
            SCRIPTS / "validate_strategy_runtime.py",
            ASSETS / "strategy-template" / "final_strategy.py",
            "--params",
            ASSETS / "strategy-template" / "final_params.json",
            "--report",
            runtime_report,
        )
        assert json.loads(runtime_report.read_text(encoding="utf-8"))["accepted"]
        anchor_task = json.loads(generation_zero.read_text(encoding="utf-8").splitlines()[0])
        candidate_payload = {
            "schema_version": "candidate-response/v1",
            "candidate_id": "smoke-candidate",
            "task_id": anchor_task["task_id"],
            "task_sha256": anchor_task["task_sha256"],
            "hypothesis": "fixture",
            "single_primary_hypothesis": True,
            "logical_steps": 2,
            "mechanism_tags": ["fixture"],
            "entry_logic": ["fixture"],
            "exit_logic": ["fixture"],
            "sizing_logic": "fixture",
            "parameter_schema": {"fast_window": {}, "slow_window": {}},
            "parent_contributions": [],
            "semantic_delta": "fixture",
            "assumptions": [],
            "failure_modes": ["fixture"],
            "blind_split_access": False,
            "code_sha256": hashlib.sha256((ASSETS / "strategy-template" / "final_strategy.py").read_bytes()).hexdigest(),
        }
        candidate_json = root / "candidate.json"
        candidate_json.write_text(json.dumps(candidate_payload), encoding="utf-8")
        anchor_json = root / "anchor-task.json"
        anchor_json.write_text(json.dumps(anchor_task), encoding="utf-8")
        run(
            SCRIPTS / "validate_candidate.py",
            candidate_json,
            "--strategy",
            ASSETS / "strategy-template" / "final_strategy.py",
            "--params",
            ASSETS / "strategy-template" / "final_params.json",
            "--task",
            anchor_json,
        )

        data = root / "bars.csv"
        data.write_text(
            "timestamp,symbol,open,high,low,close,volume\n"
            "2024-01-01T00:00:00Z,EXAMPLE,10,11,9,10.5,100\n"
            "2024-01-01T01:00:00Z,EXAMPLE,10.5,12,10,11.5,120\n",
            encoding="utf-8",
        )
        data_report = root / "data-audit.json"
        run(SCRIPTS / "validate_market_data.py", data, "--report", data_report)
        assert json.loads(data_report.read_text(encoding="utf-8"))["accepted"]

        candidates = root / "candidates.jsonl"
        rows = [
            {
                "candidate_id": "candidate-a",
                "expert_id": "market_cycle",
                "contract_ok": True,
                "leakage_ok": True,
                "stress_pass": True,
                "observations": 500,
                "trades": 40,
                "sharpe": 1.2,
                "skew": 0.0,
                "kurtosis": 3.0,
                "net_return": 0.18,
                "max_drawdown": 0.12,
                "turnover": 2.0,
                "logical_steps": 3,
            },
            {
                "candidate_id": "candidate-b",
                "expert_id": "tail_risk",
                "contract_ok": True,
                "leakage_ok": True,
                "stress_pass": False,
                "observations": 500,
                "trades": 3,
                "sharpe": 0.1,
                "skew": 0.0,
                "kurtosis": 3.0,
                "net_return": 0.01,
                "max_drawdown": 0.4,
                "turnover": 1.0,
                "logical_steps": 4,
            },
        ]
        candidates.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        gates = root / "gates.json"
        gates.write_text(json.dumps({"minimum": {"trades": 20}, "maximum": {"max_drawdown": 0.25}, "minimum_psr": 0.5, "minimum_dsr": 0.0}), encoding="utf-8")
        evaluated = root / "evaluated.jsonl"
        run(SCRIPTS / "evaluate_candidates.py", "--candidates", candidates, "--gates", gates, "--output", evaluated)
        selected = root / "selected.jsonl"
        run(SCRIPTS / "select_population.py", "--evaluated", evaluated, "--output", selected, "--target", 2)
        selected_rows = [json.loads(line) for line in selected.read_text(encoding="utf-8").splitlines()]
        assert len(selected_rows) == 2
        assert any(row["is_valid"] and not row["is_qualified"] for row in selected_rows)

        deficit = root / "deficit.jsonl"
        deficit_result = run(
            SCRIPTS / "select_population.py",
            "--evaluated",
            evaluated,
            "--output",
            deficit,
            "--target",
            3,
            expected=2,
        )
        assert json.loads(deficit_result.stdout)["replenish_count"] == 1

        extinction_candidates = root / "extinction-candidates.jsonl"
        extinction_rows = [
            {
                "candidate_id": f"survivor-{index:02d}",
                "expert_id": f"expert-{index % 21:02d}",
                "contract_ok": True,
                "leakage_ok": True,
                "stress_pass": False,
                "observations": 500,
                "trades": 30 + index,
                "sharpe": 0.4 + index / 100.0,
                "skew": 0.0,
                "kurtosis": 3.0,
                "max_drawdown": 0.30 + index / 1000.0,
                "turnover": 1.0 + index / 100.0,
                "logical_steps": 3,
                "behavior_fingerprint": f"fingerprint-{index:02d}",
            }
            for index in range(50)
        ]
        extinction_candidates.write_text("".join(json.dumps(row) + "\n" for row in extinction_rows), encoding="utf-8")
        extinction_evaluated = root / "extinction-evaluated.jsonl"
        run(
            SCRIPTS / "evaluate_candidates.py",
            "--candidates",
            extinction_candidates,
            "--gates",
            gates,
            "--output",
            extinction_evaluated,
        )
        evaluated_lines = extinction_evaluated.read_text(encoding="utf-8").splitlines()
        parent_pool = root / "parent-pool.jsonl"
        child_pool = root / "child-pool.jsonl"
        parent_pool.write_text("\n".join(evaluated_lines[:25]) + "\n", encoding="utf-8")
        child_pool.write_text("\n".join(evaluated_lines[25:]) + "\n", encoding="utf-8")
        extinction_selected = root / "extinction-selected.jsonl"
        extinction_result = run(
            SCRIPTS / "select_population.py",
            "--evaluated",
            parent_pool,
            child_pool,
            "--output",
            extinction_selected,
            "--target",
            42,
        )
        extinction_summary = json.loads(extinction_result.stdout)
        extinction_survivors = [json.loads(line) for line in extinction_selected.read_text(encoding="utf-8").splitlines()]
        assert extinction_summary == {
            "selected": 42,
            "target": 42,
            "complete": True,
            "replenish_count": 0,
            "qualified_selected": 0,
        }
        assert len(extinction_survivors) == 42
        assert all(row["is_valid"] and not row["is_qualified"] for row in extinction_survivors)

        experiment_report = root / "experiment-audit.json"
        run(SCRIPTS / "audit_experiment.py", experiment, "--report", experiment_report)
        assert json.loads(experiment_report.read_text(encoding="utf-8"))["accepted"]

        lineage = root / "lineage.jsonl"
        lineage.write_text(
            json.dumps({"candidate_id": "candidate-a", "parents": []}) + "\n"
            + json.dumps({"candidate_id": "candidate-b", "parents": ["candidate-a"]}) + "\n",
            encoding="utf-8",
        )
        run(SCRIPTS / "validate_lineage.py", lineage)

    print("smoke tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
