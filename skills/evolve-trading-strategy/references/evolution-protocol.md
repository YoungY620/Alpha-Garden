# Evolution protocol

## Expert catalog

Preserve 21 OHLCV discovery perspectives as versioned task metadata:

1. Market cycle
2. Volatility regime
3. Tail risk
4. Crash precursor
5. Liquidity proxy
6. Order-imbalance proxy
7. Price-volume coherence
8. Volume structure
9. Trend persistence
10. Reversal
11. Range volatility
12. Lagged response
13. Volatility asymmetry
14. Drawdown and recovery
15. Fractal or multi-scale structure
16. Regime gating
17. Temporal stability
18. Bar geometry
19. Creative nonlinear transformation
20. Composite signal fusion
21. Herding or directional alignment

These are descriptions, not persistent agents. An isolated generic agent task
adopts the assigned perspective from its artifact.

## Guidance modes

- `light`: preserve the primary mechanism and change one justified element.
- `moderate`: combine nearby complementary mechanisms.
- `creative`: reinterpret the hypothesis while remaining economically legible.
- `divergent`: introduce a distant but relevant mechanism and challenge an
  unproven assumption.
- `concrete`: convert ideas into explicit indicators, branches, parameters,
  positions, exits, and risk controls.

## Generations

Generation zero contains one faithful anchor and 21 concrete expert seeds.
Generation one and later contain all 105 expert-mode combinations, with one
candidate per task. A repair does not create another candidate.

## Semantic crossover

Give each child one primary effective parent, one complementary effective
parent, and one ineffective example. Require it to state what it retained,
discarded, learned from the failure, and introduced. Generate a complete new
implementation; never concatenate parent code.

Pair distinct valid parents and forbid near-duplicate pairing. Parents do not
need to be finally qualified. If fewer than two valid parents exist, generate
fresh seeds from the user's approved hypothesis before continuing.

## Task isolation

Dispatch one isolated generic task per candidate and expose only the task,
relevant source excerpts, assigned parents, contract, and output schema. A
worker may execute another task only after a guaranteed context reset. Hide
sibling outputs until the generation closes. Hash tasks, prompts, outputs,
code, parent IDs, and configuration.

Claim tasks transactionally from `experiment.sqlite`. Commit each completion
immediately and begin deterministic validation without waiting for every sibling
to finish. Use leases and heartbeats so interrupted work can be recovered
without silently duplicating an attempt.
