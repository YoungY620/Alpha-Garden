# `bar-v1` strategy contract

## Interface

Define these module-level objects:

```python
STRATEGY_METADATA = {
    "name": "descriptive-name",
    "contract_version": "bar-v1",
    "hypothesis": "testable economic statement",
    "risk_notes": ["known failure condition"],
}

PARAMETER_SPACE = {
    "lookback": {"type": "int", "min": 5, "max": 80, "default": 20},
}

def generate_target_positions(data, params):
    """Return a float Series aligned to data.index in [-1, 1]."""
```

The generated Series is a decision made after each bar closes. The adapter
shifts it one bar and applies the target no earlier than the next bar open.

## Restrictions

- Use only declared input columns and parameters.
- Do not perform network, file, environment, process, clock, account, or random
  access inside strategy logic.
- Do not import a backtest engine inside strategy logic.
- Do not use negative shifts, centered windows, future indexing, or full-sample
  fitted transformations.
- Return finite positions in `[-1, 1]`; use zero during warmup or uncertainty.
- Keep execution costs and fill prices outside the strategy.
- Declare each operational branch and parameter in metadata and the report.
- Default to at most eight tunable parameters and five logical steps. Change
  either limit only in the confirmed experiment spec before generation.

## Default execution

- Observe complete bar `t`; execute the resulting target at bar `t+1` open.
- Apply fees and slippage to every position change.
- When stop and target could both trigger inside one bar and order is unknown,
  choose the less favorable outcome.
- Apply borrow or funding costs when short exposure is enabled.
- Treat any changed fill convention as a new experiment version.

Use `assets/strategy-template/final_strategy.py` as the strategy starting point
and copy `run_strategy.py` beside it for a direct, reproducible command-line run.
