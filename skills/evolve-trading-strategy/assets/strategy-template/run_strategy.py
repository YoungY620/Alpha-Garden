#!/usr/bin/env python3
"""Direct launcher for the frozen final_strategy.py and final_params.json."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt

import final_strategy


def _data(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    return frame.sort_values("timestamp").set_index("timestamp")


def _value(value):
    if value is None or isinstance(value, str):
        return value
    try:
        number = float(value)
    except Exception:
        return str(value)
    return number if np.isfinite(number) else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--params", type=Path, default=Path(__file__).with_name("final_params.json"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cash", type=float, default=100000.0)
    parser.add_argument("--fees-bps", type=float, required=True)
    parser.add_argument("--slippage-bps", type=float, required=True)
    parser.add_argument("--frequency", required=True)
    args = parser.parse_args()
    frame = _data(args.data)
    params = json.loads(args.params.read_text(encoding="utf-8"))
    decisions = final_strategy.generate_target_positions(frame.copy(), params)
    if not isinstance(decisions, pd.Series) or not decisions.index.equals(frame.index):
        raise SystemExit("strategy output is not aligned")
    if decisions.replace([np.inf, -np.inf], np.nan).isna().any() or ((decisions < -1) | (decisions > 1)).any():
        raise SystemExit("strategy output is non-finite or outside [-1, 1]")
    executed = decisions.shift(1).fillna(0.0)
    portfolio = vbt.Portfolio.from_orders(
        close=frame["close"],
        size=executed,
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
    pd.DataFrame(
        {
            "decision_target": decisions,
            "executed_target": executed,
            "equity": portfolio.value(),
            "return": portfolio.returns(),
        }
    ).to_csv(args.output / "bar_ledger.csv")
    portfolio.trades.records_readable.to_csv(args.output / "trades.csv", index=False)
    manifest = {
        "schema_version": "final-strategy-run/v1",
        "engine": {"name": "vectorbt", "version": str(vbt.__version__)},
        "strategy_sha256": hashlib.sha256(Path(final_strategy.__file__).read_bytes()).hexdigest(),
        "params_sha256": hashlib.sha256(args.params.read_bytes()).hexdigest(),
        "data_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
        "execution": {
            "decision": "bar_close_t",
            "fill": "bar_open_t_plus_1",
            "fees_bps": args.fees_bps,
            "slippage_bps": args.slippage_bps,
            "frequency": args.frequency,
        },
        "metrics": {str(key): _value(value) for key, value in portfolio.stats().items()},
    }
    (args.output / "result.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
