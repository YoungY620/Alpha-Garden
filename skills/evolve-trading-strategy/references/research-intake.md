# Grilling and experiment specification

Do not use a separate approval document. Keep asking short, focused questions
until every material field below is known, then freeze the
answers in `experiment-spec.json` and ask the user to confirm execution.

## Required research fields

1. Stable experiment identity and version.
2. User idea, knowledge sources, existing code, and intended creative freedom.
3. Primary objective and any already-defined benchmark.
4. Instrument, venue, currency, timezone, and trading session.
5. Bar interval, holding horizon, maximum lookback, and permitted exposure.
6. Binding constraints, risk limits, costs, and fill assumptions.
7. Soft preferences: familiar instruments, indicators, style, interpretability,
   and operational complexity.
8. Testable hypotheses and the controlled creative zone.
9. Required and available data, point-in-time limits, and known gaps.
10. Train, validation, purge/embargo, and sealed-test policy.
11. Search, complexity, time, and stopping budgets.
12. Final deliverables and explicit non-goals.

Classify only explicit prohibitions and confirmed limits as binding. Treat
familiarity and preferred style as soft priors. Treat market claims as
hypotheses. Ask about unknown risk tolerance; never infer it.

## Dashboard brief

Before confirmation, propose two or three problem-specific visual directions.
Describe information hierarchy, palette and typography, chart composition, and
one useful signature element. Let the user choose or delegate the choice.
Record language, direction, density, and preferred chart library under
`dashboard_brief`. Do not require another visual approval after confirmation.

## Confirmation gate

Show a compact natural-language execution summary. Require an explicit
confirmation, set `confirmation.confirmed` and `confirmed_at`, then run
`scripts/manage_experiment.py experiment.sqlite confirm --spec
experiment-spec.json`. A later change to instrument, objective, splits, costs,
risk limits, or execution semantics creates a new experiment version.
