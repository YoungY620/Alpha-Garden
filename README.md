<h1 align="center">
  <img src="assets/alpha-garden-logo-white-pg.png" alt="Alpha Garden" width="560">
</h1>

<p align="center">
  <strong>Grow ideas. Test strategies. Let evidence decide.</strong>
</p>

<p align="center">
  An evidence-first strategy evolution lab.
</p>

![Alpha Garden turns each trading question into a custom, frozen research environment for strategy evolution and sealed holdout testing.](assets/alpha-garden-concept.png)

Alpha Garden's `evolve-trading-strategy` agent skill turns a user's trading idea or
research library into a rigorously tested, single-instrument time-series
strategy. It coordinates isolated generic agent tasks through a transactional
SQLite queue, exposes a generated read-only evolution monitor, applies
deterministic validation and selection gates, and delivers a reproducible
strategy plus a professional PDF research report.

The first release focuses on minute-or-higher OHLCV bars. It does not perform
cross-sectional stock selection or place live orders.

## Repository layout

```text
skills/
└── evolve-trading-strategy/
    ├── SKILL.md
    ├── agents/
    ├── assets/
    ├── references/
    ├── scripts/
    └── tests/
```

## Install

Copy the nested skill folder into the skills directory used by your agent host:

```bash
test -n "$SKILLS_DIR"
mkdir -p "$SKILLS_DIR"
cp -R skills/evolve-trading-strategy "$SKILLS_DIR/"
```

Invoke it with a prompt such as:

```text
Use $evolve-trading-strategy to turn these research notes into a validated
single-instrument strategy and a PDF report.
```

Install the deterministic research and reporting dependencies in a shared
isolated user-cache runtime before running the bundled scripts. Python 3.11
through 3.14 is required:

```bash
python3 skills/evolve-trading-strategy/scripts/bootstrap_runtime.py
```

Freeze the resolved versions in each experiment manifest. A dependency change
creates a new experiment version.

## Validate before publishing

```bash
python3 skills/evolve-trading-strategy/scripts/audit_release.py .
python3 skills/evolve-trading-strategy/tests/run_smoke_tests.py
```

The release audit rejects machine-specific paths, IP addresses, email
addresses, credentials, tokens, and other likely secrets. Do not publish until
both commands pass.

This project produces research artifacts, not investment advice or a promise
of future performance.
