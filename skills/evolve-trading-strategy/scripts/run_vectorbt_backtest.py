#!/usr/bin/env python3
"""Run a bar-v1 strategy with vectorbt using next-open target execution."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def _load_strategy(path: Path):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("candidate_strategy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load strategy module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_data(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    return frame.sort_values("timestamp").set_index("timestamp")


def _json_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        number = float(value)
    except Exception:
        return str(value)
    return number if np.isfinite(number) else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--params", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cash", type=float, default=100000.0)
    parser.add_argument("--fees-bps", type=float, required=True)
    parser.add_argument("--slippage-bps", type=float, required=True)
    parser.add_argument("--frequency", required=True, help="Pandas/vectorbt frequency, for example 1h")
    args = parser.parse_args()
    try:
        import vectorbt as vbt
    except ImportError as exc:
        raise SystemExit("vectorbt is required for the default backtest adapter") from exc

    frame = _load_data(args.data)
    params = json.loads(args.params.read_text(encoding="utf-8"))
    strategy = _load_strategy(args.strategy)
    decisions = strategy.generate_target_positions(frame.copy(), params)
    if not isinstance(decisions, pd.Series) or not decisions.index.equals(frame.index):
        raise SystemExit("strategy must return a Series aligned exactly to input index")
    if decisions.replace([np.inf, -np.inf], np.nan).isna().any():
        raise SystemExit("strategy returned non-finite positions")
    if ((decisions < -1) | (decisions > 1)).any():
        raise SystemExit("strategy returned positions outside [-1, 1]")

    executed_target = decisions.shift(1).fillna(0.0)
    portfolio = vbt.Portfolio.from_orders(
        close=frame["close"],
        size=executed_target,
        size_type="targetpercent",
        direction="both",
        price=frame["open"],
        val_price=frame["open"],
        update_value=True,
        fees=args.fees_bps / 10000.0,
        slippage=args.slippage_bps / 10000.0,
        init_cash=args.cash,
        seed=0,
        freq=args.frequency,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    value = portfolio.value()
    returns = portfolio.returns()
    pd.DataFrame({"decision_target": decisions, "executed_target": executed_target, "equity": value, "return": returns}).to_csv(
        args.output / "bar_ledger.csv"
    )
    try:
        portfolio.trades.records_readable.to_csv(args.output / "trades.csv", index=False)
    except Exception:
        (args.output / "trades.csv").write_text("", encoding="utf-8")
    stats = portfolio.stats()
    metrics = {str(key): _json_value(value) for key, value in stats.items()}
    manifest = {
        "schema_version": "backtest-result/v1",
        "engine": {"name": "vectorbt", "version": str(vbt.__version__)},
        "strategy_sha256": hashlib.sha256(args.strategy.read_bytes()).hexdigest(),
        "data_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
        "params_sha256": hashlib.sha256(args.params.read_bytes()).hexdigest(),
        "execution": {
            "decision": "bar_close_t",
            "fill": "bar_open_t_plus_1",
            "fees_bps": args.fees_bps,
            "slippage_bps": args.slippage_bps,
            "cash": args.cash,
            "frequency": args.frequency,
        },
        "metrics": metrics,
    }
    (args.output / "result.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "bars": len(frame)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
