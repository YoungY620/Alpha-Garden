#!/usr/bin/env python3
"""Measure validity, final qualification, and distance from qualification."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import NormalDist


def probabilistic_sharpe(sr: float, benchmark: float, observations: int, skew: float, kurtosis: float) -> float:
    if observations < 3:
        return 0.0
    denominator = 1.0 - skew * sr + ((kurtosis - 1.0) / 4.0) * sr * sr
    if denominator <= 0:
        return 0.0
    z = (sr - benchmark) * math.sqrt(observations - 1.0) / math.sqrt(denominator)
    return NormalDist().cdf(z)


def deflated_benchmark(trials: int, sr_std: float) -> float:
    if trials <= 1 or sr_std <= 0:
        return 0.0
    gamma = 0.5772156649015329
    normal = NormalDist()
    first = normal.inv_cdf(1.0 - 1.0 / trials)
    second = normal.inv_cdf(1.0 - 1.0 / (trials * math.e))
    return sr_std * ((1.0 - gamma) * first + gamma * second)


def _number(row: dict, field: str) -> float | None:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _minimum_violation(value: float | None, threshold: float) -> float:
    if value is None:
        return 1.0
    scale = abs(threshold) if abs(threshold) > 1e-12 else 1.0
    return max(0.0, threshold - value) / scale


def _maximum_violation(value: float | None, threshold: float) -> float:
    if value is None:
        return 1.0
    scale = abs(threshold) if abs(threshold) > 1e-12 else 1.0
    return max(0.0, value - threshold) / scale


def evaluate(row: dict, gates: dict, total_trials: int, sr_std: float) -> dict:
    integrity_failures: list[str] = []
    for field in gates.get("validity_fields", ["contract_ok", "leakage_ok"]):
        if row.get(field) is not True:
            integrity_failures.append(f"{field} is not true")
    for field, lower in gates.get("validity_minimum", {"trades": 1}).items():
        value = _number(row, field)
        if value is None or value < float(lower):
            integrity_failures.append(f"{field} below validity minimum {lower}")

    failures: list[str] = []
    violation_score = 0.0
    for field, lower in gates.get("minimum", {}).items():
        value = _number(row, field)
        threshold = float(lower)
        violation = _minimum_violation(value, threshold)
        violation_score += violation
        if violation > 0:
            failures.append(f"{field} below minimum {lower}")
    for field, upper in gates.get("maximum", {}).items():
        value = _number(row, field)
        threshold = float(upper)
        violation = _maximum_violation(value, threshold)
        violation_score += violation
        if violation > 0:
            failures.append(f"{field} above maximum {upper}")
    sr = float(row.get("sharpe", 0.0))
    dsr_benchmark = deflated_benchmark(total_trials, sr_std)
    psr = probabilistic_sharpe(sr, float(gates.get("benchmark_sharpe", 0.0)), int(row.get("observations", 0)), float(row.get("skew", 0.0)), float(row.get("kurtosis", 3.0)))
    dsr = probabilistic_sharpe(sr, dsr_benchmark, int(row.get("observations", 0)), float(row.get("skew", 0.0)), float(row.get("kurtosis", 3.0)))
    minimum_psr = float(gates.get("minimum_psr", 0.0))
    psr_violation = _minimum_violation(psr, minimum_psr)
    violation_score += psr_violation
    if psr_violation > 0:
        failures.append("probabilistic Sharpe below threshold")
    minimum_dsr = float(gates.get("minimum_dsr", 0.0))
    dsr_violation = _minimum_violation(dsr, minimum_dsr)
    violation_score += dsr_violation
    if dsr_violation > 0:
        failures.append("deflated Sharpe below threshold")
    if gates.get("require_stress_pass", True) and row.get("stress_pass") is not True:
        violation_score += 1.0
        failures.append("stress tests did not pass")

    fitness_field = str(gates.get("fitness_field", "fitness"))
    fitness = _number(row, fitness_field)
    if fitness is None:
        fitness = _number(row, "sharpe")
    if fitness is None:
        fitness = -1_000_000_000.0
    is_valid = not integrity_failures
    return {
        **row,
        "psr": psr,
        "dsr": dsr,
        "dsr_benchmark": dsr_benchmark,
        "is_valid": is_valid,
        "is_qualified": is_valid and not failures,
        "violation_score": violation_score,
        "fitness": fitness,
        "integrity_failures": integrity_failures,
        "gate_failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True, type=Path, help="JSONL metric records")
    parser.add_argument("--gates", required=True, type=Path, help="Pre-registered gate JSON")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.candidates.read_text(encoding="utf-8").splitlines() if line.strip()]
    gates = json.loads(args.gates.read_text(encoding="utf-8"))
    sharpe_values = [float(row.get("sharpe", 0.0)) for row in rows]
    mean = sum(sharpe_values) / len(sharpe_values) if sharpe_values else 0.0
    sr_std = math.sqrt(sum((value - mean) ** 2 for value in sharpe_values) / max(1, len(sharpe_values) - 1))
    total_trials = sum(max(1, int(row.get("search_trials", 1))) for row in rows)
    assessed = [evaluate(row, gates, total_trials, sr_std) for row in rows]
    args.output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in assessed), encoding="utf-8")
    counts = {
        "valid": sum(row["is_valid"] for row in assessed),
        "invalid": sum(not row["is_valid"] for row in assessed),
        "qualified": sum(row["is_qualified"] for row in assessed),
        "not_qualified": sum(row["is_valid"] and not row["is_qualified"] for row in assessed),
    }
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
