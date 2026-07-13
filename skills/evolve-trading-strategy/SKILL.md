---
name: evolve-trading-strategy
description: Turn a user's trading inspiration, notes, existing strategy, or knowledge base into a rigorously validated single-instrument time-series strategy, runnable code, a live read-only evolution monitor, and a professional PDF research report. Use when the user asks to generate, improve, evolve, backtest, eliminate, cross over, or optimize trading strategies from their ideas or research materials for stocks or crypto. Supports minute-or-higher OHLCV research, optional point-in-time auxiliary data, isolated generic agent tasks, walk-forward validation, sealed holdout testing, overfitting controls, and honest failure reports. Do not use for simple price lookups, cross-sectional stock selection, portfolio optimization, order placement, or claims of guaranteed returns.
---

# Evolve Trading Strategy

Turn user knowledge into a reproducible research experiment. Treat the user's
materials as both a search prior and an investment-preference signal without
letting them suppress controlled creative exploration.

## Non-negotiable rules

- Work on one instrument per experiment. Do not perform cross-sectional
  selection or portfolio optimization.
- Keep grilling until every material research input is known. Freeze a
  machine-readable experiment spec only after the user confirms execution.
- Classify user statements as binding constraints, soft preferences, or
  testable hypotheses. Never infer missing risk tolerance.
- Keep the sealed test set inaccessible until final candidates are frozen.
  Open it once. Never feed its result back into the same experiment.
- Use deterministic checks and backtests as authority. Never let an agent's
  semantic opinion override a failed contract, leakage, or risk gate.
- Permit the honest outcome that no candidate qualifies.
- Never let final qualification gates empty the breeding population. Exclude
  only invalid code or behavior; retain the best valid individuals by relative
  distance to the approved gates.
- Deliver research and simulation code only. Never place live orders or handle
  brokerage credentials.
- Never write machine-specific paths, usernames, IP addresses, email
  addresses, passwords, tokens, private endpoints, or secrets into artifacts.
  Use relative paths, CLI arguments, and environment variables. Run
  `scripts/audit_release.py` before publishing or sharing.

## Load references progressively

Read only the references required for the current phase:

- Grilling and spec freeze: `references/research-intake.md`
- Live read-only monitor: `references/monitoring-dashboard.md`
- Market data preparation: `references/data-contract.md` and
  `references/data-sources.md`
- Engine choice: `references/framework-selection.md`
- Default generated code: `references/bar-v1-contract.md`
- Tick or order-book request: `references/microstructure-v1-contract.md`
- Candidate creation and agent-task scheduling:
  `references/evolution-protocol.md`
- Gates, metrics, population control, and sealed testing:
  `references/evaluation-protocol.md`
- Final PDF: `references/reporting-and-visualization.md`

## Workflow

Before the first deterministic run, execute `scripts/bootstrap_runtime.py` and
use the resulting user-cache runtime Python for bundled scripts. Re-run it after dependency
changes and record resolved versions in the experiment manifest.

### 1. Grill and confirm the experiment spec

Interview the user in short rounds. Continue until the objective, instrument,
market, interval, horizon, allowed positions, costs, risk limits, preferences,
source hypotheses, data, creative allowance, budget, stopping policy, and
dashboard direction are complete. Never silently fill a material unknown.

Write `experiment-spec.json`, show a compact execution summary, and obtain an
explicit confirmation. Record the confirmation and spec hash in
`experiment.sqlite`. If the user changes a material field after testing begins,
create a new experiment version.

### 2. Generate and start the monitor

Before downloading data or creating generation zero, read
`references/monitoring-dashboard.md`. Generate a problem-specific frontend in
the experiment's `dashboard/` directory; do not copy a fixed skill template.
Use the bundled read-only Flask server and the four fixed GET APIs. Prefer plain
HTML, CSS, and TypeScript or JavaScript with `@visactor/vchart`; use a frontend
framework only when the interaction genuinely requires it.

Test design with a clearly separate fixture, then switch to the live empty
database. Start the monitor on `localhost`, verify health, snapshot, polling,
desktop rendering, and narrow-screen summary, and give the user the URL. Do not
start generation zero until the live monitor passes. A later monitor failure
must not stop research; restart it against the same SQLite database.

### 3. Prepare and audit data

Use OHLCV as the built-in data capability. Permit auxiliary series only when
their historical publication time and point-in-time alignment are known. Run
`scripts/validate_market_data.py` and stop on timezone ambiguity, illegal OHLC,
duplicate timestamps, inadequate split coverage, or unverifiable auxiliary
availability.

Record source, retrieval time, adjustment convention, timezone, session,
interval, coverage, and checksum. Do not describe a merely downloadable source
as research-grade.

### 4. Freeze the experiment protocol

Default to the portable `bar-v1` contract and vectorbt adapter. Generate a
signal only after bar `t` closes and execute no earlier than bar `t+1` opens.
Apply the same fees, slippage, sizing limits, and conservative intrabar rules to
all candidates.

Freeze train, validation, and sealed-test boundaries before generation. Apply a
purge/embargo appropriate to maximum lookback and holding horizon.

### 5. Build generation zero

Run `scripts/build_generation_tasks.py --generation 0`. Create one anchor task
that faithfully formalizes the user's idea and 21 expert seed tasks using the
`concrete` guidance mode. If the user supplied runnable code, use it as the
anchor only after the same validation applied to generated code.

### 6. Dispatch isolated generic agent tasks

Use available agent seats as a rolling worker pool. Dispatch one isolated task
per candidate and never create persistent expert personas. A worker may be
reused only when the runtime guarantees a cleared context between tasks. Give
each task exactly one artifact, its assigned parent evidence, and the relevant
knowledge excerpts. Do not expose same-generation sibling outputs.

Require the executing agent to write the declared result schema and complete runnable
strategy code. A repair is a retry of the same individual, not an extra search
opportunity. Allow at most two repairs.

Claim tasks transactionally with `scripts/manage_experiment.py`. Stream each
completed candidate into deterministic validation without waiting for the whole
generation, while keeping sibling results hidden. If no agent seat is
available, execute the identical contract sequentially. Never replace agent
execution with hidden API calls.

### 7. Validate, backtest, and eliminate

Run static contract and security checks before importing candidate code. Run
candidate code in an isolated subprocess with fixed seeds, dependency
allowlists, no network, resource limits, and captured logs.

Apply contract, leakage, numerical-stability, development, walk-forward, and
stress checks. Record only `is_valid`, `is_qualified`, `violation_score`, and
the experiment spec's primary `fitness`. A valid candidate that misses final evidence
gates remains eligible for breeding. Access validation only at pre-registered
checkpoints and record every access.

Write task, candidate, generation, and research-note transitions to
`experiment.sqlite` through `scripts/manage_experiment.py`. The monitor is a
read-only view of these authoritative records and never recomputes metrics.

### 8. Evolve full generations

For generation 1 and later, create all 21 expert by 5 guidance-mode tasks: 105
children per generation, one candidate per task. Use semantic crossover rather
than code concatenation. Give each task one primary effective parent, one
complementary effective parent, one failure example, and a novelty constraint.

Build the next population from previous parents plus new children. Keep 22
valid individuals in generation zero and exactly 42 from generation one onward.
Rank by lower gate-violation score, higher fitness, then lower complexity. Keep
one best valid representative per available expert direction, skip behavioral
duplicates, and fill remaining seats globally. If valid unique candidates are
insufficient, generate exactly the missing number of fresh seeds and rerun
selection.

Stop at the confirmed budget, after three generations without material
improvement in both best fitness and lowest violation score, or when the user
stops the run. Never stop merely because no candidate is yet qualified.

Run the validation period only for the frozen checkpoint shortlist. Do not show
validation results to same-generation workers or repeatedly tune against them.

### 9. Freeze finalists and open the sealed test once

Freeze code, parameters, dependencies, checksums, and finalist identities
before test access. Record the opening event. Run each frozen finalist once
under the frozen execution configuration. Never mutate or rerank through a new
search using this result.

If all candidates fail, deliver a failure report and diagnostics instead of
promoting the least bad strategy.

### 10. Deliver code and the PDF report

Deliver `final_strategy.py`, `final_params.json`, `run_strategy.py`, a frozen
dependency manifest, reproduction
metadata, detailed backtest artifacts, and `strategy_report.pdf`. Explain every operational branch,
parameter, selected value, underlying idea, dataset split, metric, advantage,
risk, limitation, and failure regime in natural language.

Build the PDF with `scripts/build_pdf_report.py`. Embed fonts, render every page
to PNG, inspect all pages, and do not deliver while any glyph, table, chart,
margin, header, footer, or page transition is defective.

## Completion checklist

- Experiment spec explicitly confirmed after complete grilling.
- Live monitor was available before generation zero began.
- Data and point-in-time audit passed.
- Task, candidate, prompt, response, and lineage hashes recorded.
- All attempts, including failures, retained in the experiment ledger.
- Validation contains walk-forward and robustness evidence.
- Multiple-testing corrections are selection gates, not decorative metrics.
- Sealed test opening recorded exactly once.
- Final code reproduces the stated result from declared inputs.
- PDF separates train, validation, and sealed-test evidence visually and
  verbally.
- Risks receive the same prominence as strengths.
- Release privacy/secret audit passed.
