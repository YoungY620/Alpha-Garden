#!/usr/bin/env python3
"""Check bar-v1 output invariants and causal prefix stability on synthetic data."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def _load(path: Path):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("runtime_candidate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load strategy")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _frame(rows: int = 256) -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=rows, freq="h", tz="UTC")
    base = 100 + np.cumsum(np.sin(np.arange(rows) / 11) * 0.3 + 0.05)
    return pd.DataFrame(
        {
            "open": base,
            "high": base + 1.0,
            "low": base - 1.0,
            "close": base + np.sin(np.arange(rows) / 7) * 0.2,
            "volume": 1000 + (np.arange(rows) % 17) * 20,
        },
        index=index,
    )


def validate(path: Path, params: dict) -> dict:
    issues: list[str] = []
    module = _load(path)
    data = _frame()
    first = module.generate_target_positions(data.copy(), params)
    second = module.generate_target_positions(data.copy(), params)
    if not isinstance(first, pd.Series) or not first.index.equals(data.index):
        issues.append("output is not a Series aligned to the input index")
        return {"accepted": False, "issues": issues}
    values = pd.to_numeric(first, errors="coerce")
    if values.isna().any() or not np.isfinite(values.to_numpy()).all():
        issues.append("output contains non-finite values")
    if ((values < -1) | (values > 1)).any():
        issues.append("output is outside [-1, 1]")
    if not first.equals(second):
        issues.append("strategy is not deterministic")
    for cutoff in (64, 128, 192):
        altered = data.copy()
        altered.iloc[cutoff + 1 :, altered.columns.get_loc("close")] *= 3.0
        altered.iloc[cutoff + 1 :, altered.columns.get_loc("volume")] *= 10.0
        changed = module.generate_target_positions(altered, params)
        left = pd.to_numeric(first.iloc[: cutoff + 1], errors="coerce")
        right = pd.to_numeric(changed.iloc[: cutoff + 1], errors="coerce")
        if not np.allclose(left.to_numpy(), right.to_numpy(), equal_nan=True):
            issues.append(f"future-data mutation changed decisions through cutoff {cutoff}")
    return {"accepted": not issues, "issues": issues, "rows": len(data)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("strategy", type=Path)
    parser.add_argument("--params", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = {"schema_version": "strategy-runtime-audit/v1", **validate(args.strategy, json.loads(args.params.read_text(encoding="utf-8")))}
    payload = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
