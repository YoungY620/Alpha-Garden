"""Portable bar-v1 strategy template. Replace the example hypothesis."""

from __future__ import annotations

import numpy as np
import pandas as pd


STRATEGY_METADATA = {
    "name": "replace-with-final-strategy-name",
    "contract_version": "bar-v1",
    "hypothesis": "Replace with one testable economic hypothesis.",
    "risk_notes": ["This template is not a validated strategy."],
}

PARAMETER_SPACE = {
    "fast_window": {"type": "int", "min": 5, "max": 40, "default": 12},
    "slow_window": {"type": "int", "min": 20, "max": 160, "default": 48},
}


def generate_target_positions(data: pd.DataFrame, params: dict) -> pd.Series:
    """Return decisions made at each completed bar; the adapter shifts fills."""
    fast_window = int(params["fast_window"])
    slow_window = int(params["slow_window"])
    if fast_window < 1 or slow_window <= fast_window:
        raise ValueError("require 1 <= fast_window < slow_window")
    close = pd.to_numeric(data["close"], errors="raise")
    fast = close.ewm(span=fast_window, adjust=False, min_periods=fast_window).mean()
    slow = close.ewm(span=slow_window, adjust=False, min_periods=slow_window).mean()
    position = pd.Series(np.where(fast > slow, 1.0, 0.0), index=data.index, dtype=float)
    position[(fast.isna()) | (slow.isna())] = 0.0
    return position.rename("target_position")
