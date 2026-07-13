#!/usr/bin/env python3
"""Validate canonical single-instrument OHLCV bars."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


REQUIRED = ("timestamp", "symbol", "open", "high", "low", "close", "volume")


def load_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def validate(frame: pd.DataFrame, timezone: str | None) -> dict:
    issues: list[str] = []
    missing = [column for column in REQUIRED if column not in frame.columns]
    if missing:
        return {"accepted": False, "issues": [f"missing columns: {missing}"]}
    if frame.empty:
        return {"accepted": False, "issues": ["data is empty"]}
    timestamps = pd.to_datetime(frame["timestamp"], errors="coerce", utc=False)
    if timestamps.isna().any():
        issues.append("one or more timestamps are invalid")
    elif timestamps.dt.tz is None and not timezone:
        issues.append("timezone-naive timestamps require --timezone")
    if frame.duplicated(["symbol", "timestamp"]).any():
        issues.append("duplicate symbol/timestamp rows")
    if not timestamps.is_monotonic_increasing:
        issues.append("timestamps are not strictly ordered")
    if frame["symbol"].nunique(dropna=False) != 1:
        issues.append("bar-v1 experiment requires exactly one symbol")
    numeric = frame[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any():
        issues.append("OHLCV contains non-numeric or missing values")
    if (numeric[["open", "high", "low", "close"]] <= 0).any().any():
        issues.append("prices must be positive")
    if (numeric["volume"] < 0).any():
        issues.append("volume must be non-negative")
    if (numeric["high"] < numeric[["open", "low", "close"]].max(axis=1)).any():
        issues.append("high is below another OHLC field")
    if (numeric["low"] > numeric[["open", "high", "close"]].min(axis=1)).any():
        issues.append("low is above another OHLC field")
    return {
        "accepted": not issues,
        "issues": issues,
        "rows": int(len(frame)),
        "symbol": str(frame["symbol"].iloc[0]),
        "start": str(timestamps.min()),
        "end": str(timestamps.max()),
        "zero_volume_rows": int((numeric["volume"] == 0).sum()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path)
    parser.add_argument("--timezone")
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    raw = args.data.read_bytes()
    report = validate(load_frame(args.data), args.timezone)
    report.update({"schema_version": "data-audit/v1", "sha256": hashlib.sha256(raw).hexdigest()})
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
