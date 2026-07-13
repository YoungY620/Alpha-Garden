# Framework selection

Use vectorbt with the portable `bar-v1` strategy contract by default. Keep
strategy logic independent from engine objects so an adapter can translate the
common subset.

| Scenario | Suggested framework | Reason | Important limitation |
|---|---|---|---|
| Many bar candidates and parameter grids | vectorbt | Fast vectorized research and batch comparison | Not an order-book simulator |
| Small readable single-instrument studies | backtesting.py | Simple strategy surface | Less suitable for large evolutionary runs |
| Complex event-driven bar orders | Backtrader | Mature callback and order lifecycle model | Slower and more stateful generated code |
| Similar backtest and production architecture | NautilusTrader | High-performance event-driven design | More integration complexity |
| QuantConnect deployment ecosystem | LEAN | Broad market and brokerage abstractions | Heavy runtime and engine-specific conventions |
| L2/L3 queue and latency research | hftbacktest | Book replay, queue and latency models | Data and venue semantics remain the user's responsibility |
| Agent-based exchange experiments | ABIDES | Market microstructure simulation | Not a default historical strategy engine |

## Portability rule

Common strategies emit target positions through `bar-v1`. Register any
engine-specific feature explicitly and mark the candidate `engine-specific`.
Do not compare it directly with portable candidates unless execution semantics
have been normalized and documented.
