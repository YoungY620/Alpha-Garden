# Market data contract

## Canonical bar fields

Require `timestamp`, `symbol`, `open`, `high`, `low`, `close`, and `volume`.
Record timezone, venue session, interval, currency, adjustment convention,
source, retrieval time, and file checksum in a separate manifest.

## Mandatory validation

- Parse timestamps unambiguously and sort them strictly ascending.
- Reject duplicate timestamps for the same symbol.
- Verify `high >= max(open, close, low)` and
  `low <= min(open, close, high)`.
- Reject negative prices or volume and non-finite price values.
- Report gaps against the declared venue calendar; distinguish closures,
  halts, and missing observations.
- State whether bars are raw, split-adjusted, or total-return adjusted.
- Verify that the requested train, validation, embargo, and sealed-test ranges
  are covered after indicator warmup.
- Record resampling rules. Never present synthesized minute bars as observed
  minute data.

## Auxiliary series

Require an event timestamp and an `available_at` timestamp. Join with an as-of
operation using `available_at`, not the period being described. Reject revised
fundamental, sentiment, macro, or on-chain history when the original historical
publication state cannot be established.

## Isolation

Store split boundaries in the experiment manifest before candidate generation.
Do not compute normalization, feature selection, or parameter ranges using
validation or sealed-test observations. Fit transformations on training data
and carry the fitted state forward.
