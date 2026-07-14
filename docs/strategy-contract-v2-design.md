# Strategy Contract v2 Design

Status: design grilling in progress  
Baseline: v0.1.0

## Objective

Generalize the skill beyond single-instrument time-series strategies without
forcing every strategy into one signal, selection, allocation, or lifecycle
model. The common contract should guarantee that a strategy can be backtested,
audited, reproduced, and compared when its assumptions are compatible.

## Confirmed decisions

### Standardize execution and evidence, not strategy internals

- Do not prescribe universal hooks for signals, ranking, top-k selection,
  allocation, rebalancing, or risk rules.
- Let the runtime define and freeze a `strategy-contract.json` appropriate to
  the research question and chosen backtest framework.
- Permit arbitrary strategy rules inside that contract, including
  single-instrument timing, cross-sectional selection, multi-asset stateful
  logic, and newly invented rules.
- Keep causality, data isolation, code safety, ledger integrity, and sealed-test
  discipline non-overridable.

### Standardize the runnable package

Every candidate must expose a reproducible backtest entry point and emit a
standard result bundle. The exact file formats remain to be finalized, but the
bundle must cover resolved configuration, equity, positions, trades, metrics,
diagnostics, and provenance.

### Compare only compatible results

- Permit incompatible strategies in the same research report and monitor.
- Mark incompatible results as descriptive side-by-side evidence only.
- Allow numerical ranking only after a compatibility check passes.
- Use the term `comparison_group` / 可比组 rather than `cohort`.
- A comparison group means candidates evaluated under sufficiently compatible
  data, execution, accounting, cost, and metric assumptions.
- Cross-sectional assets are constituents of one strategy, not separate
  comparison groups.

### Freeze one external backtest contract per comparison group

- Each comparison group freezes one contract for data semantics, universe
  formation, decision and execution timing, costs, accounting, capital and
  leverage conventions, data splits, metrics, and result formats.
- Strategy internals remain free to evolve inside the group, including signals,
  selection, weights, rebalancing, and risk rules.
- A candidate that requires materially different external assumptions belongs
  in a new comparison group.

## Pending decisions

1. Which fields form the compatibility signature and which dimensions may vary
   intentionally inside a group.
2. Whether framework choice is fixed per group or may vary behind an adapter.
3. The minimum runnable command and standard result-bundle schema.
4. How populations, breeding, and budgets are allocated across groups.
5. How validation and sealed testing work at group and study levels.
6. How the SQLite state and monitoring API represent groups and heterogeneous
   strategy artifacts.
7. Migration boundaries from the v0.1.0 single-instrument format.

## Design constraints

- Keep the skill and bundled scripts concise.
- Avoid a universal strategy DSL.
- Preserve honest failure outcomes and extinction-safe population control.
- Do not rank results whose assumptions are materially incompatible.
- Do not weaken point-in-time, causality, or data-isolation requirements.
