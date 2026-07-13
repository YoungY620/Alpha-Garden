# `microstructure-v1` extension boundary

Use this profile only when the strategy depends on trades, quotes, book deltas,
book snapshots, queue priority, latency, or maker/taker behavior and the user
has suitable event data.

Inputs are time-ordered market events. Outputs are abstract `submit`, `cancel`,
and `replace` order intents with side, type, price, quantity, time-in-force, and
reason. Use hftbacktest for queue/latency research or NautilusTrader for a wider
event-driven architecture.

Do not translate a book strategy into `bar-v1` and claim equivalent evidence.
Do not infer L2/L3 state from minute bars. The first skill release documents
this boundary but does not promise complete data adapters or an order-book
engine implementation.
