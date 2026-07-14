<h1 align="center">
  <img src="assets/alpha-garden-logo-white-pg.png" alt="Alpha Garden" width="560">
</h1>

<p align="center">
  <strong>Grow ideas. Test strategies. Let evidence decide.</strong>
</p>

<p align="center">
  An evidence-first strategy evolution lab.
</p>

Alpha Garden is a modern, agent-native reconstruction of the research direction
introduced by [CogAlpha: Cognitive Alpha Mining via LLM-Driven Code-Based
Evolution](https://arxiv.org/abs/2511.18850). It preserves the central idea—use
LLMs to create executable strategies, learn from evaluated generations, and
evolve better candidates—but rebuilds the workflow around isolated agent tasks,
reproducible experiments, deterministic gates, and strict holdout discipline.

The repository ships as the `evolve-trading-strategy` agent skill. It turns a
user's trading idea or research library into a rigorously tested,
single-instrument time-series strategy. A transactional SQLite queue
coordinates generic agent workers, a generated read-only monitor exposes live
progress, and deterministic validation decides what survives. The deliverables
are runnable strategy code, a complete experiment trail, and a professional PDF
research report—not an opaque list of LLM suggestions.

![Alpha Garden turns each trading question into a custom, frozen research environment for strategy evolution and sealed holdout testing.](assets/alpha-garden-concept.png)

The first release focuses on minute-or-higher OHLCV bars. It does not perform
cross-sectional stock selection or place live orders.

## Why Alpha Garden

CogAlpha showed that alpha mining becomes more effective when an LLM is treated
as part of an evolutionary research system instead of as a one-shot formula
generator. Alpha Garden carries that insight into a skill designed for current
agent runtimes:

- **Agent-native execution:** candidate creation, critique, repair, and
  synthesis run as isolated tasks with explicit input and output contracts.
- **Evidence has final authority:** compilation, leakage checks, backtests,
  costs, walk-forward validation, and risk gates outrank semantic judgments.
- **Evolution without contamination:** workers may learn from approved
  predecessor evidence, while sibling outputs and the sealed holdout remain
  hidden.
- **Reproducibility by construction:** the experiment specification, data
  provenance, dependency versions, prompts, code, metrics, and selection events
  are recorded in SQLite.
- **Honest stopping:** the system may conclude that no candidate qualifies; it
  does not manufacture a winning strategy to satisfy the prompt.

This is a conceptual and engineering reproduction, not a claim of identical
source code or identical experimental scope. CogAlpha evaluates cross-sectional
equity factors; Alpha Garden currently specializes in one-instrument
time-series strategies and adds stronger experiment isolation, monitoring,
walk-forward validation, and sealed-test controls.

## What the CogAlpha results motivate

The following are **results reported by the CogAlpha paper**, not results
produced by this repository. They show why code-based, iterative agent search is
a compelling foundation to reproduce and extend.

On CSI300 with a 10-day horizon, the paper compares CogAlpha with 21 machine
learning, deep learning, alpha-library, automated-mining, and standalone-LLM
baselines:

| Method | IC | RankIC | ICIR | RankICIR | AER | IR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LightGBM | 0.0269 | 0.0412 | 0.2811 | 0.3327 | 0.0878 | 1.0980 |
| Alpha158 | 0.0358 | 0.0402 | 0.2737 | 0.2866 | 0.0946 | 0.8556 |
| Standalone gpt-oss-120B | 0.0300 | 0.0318 | 0.2501 | 0.2595 | 0.0789 | 0.8015 |
| **CogAlpha + gpt-oss-120B** | **0.0591** | **0.0814** | **0.3410** | **0.4350** | **0.1639** | **1.8999** |

Relative to the strongest listed baseline for each metric in the full paper
table, CogAlpha reports roughly **+65% IC**, **+98% RankIC**, **+37% AER**, and
**+44% IR**. RankICIR is nearly tied with Random Forest (0.4350 versus 0.4385),
which is a useful reminder to inspect every metric rather than presenting a
single headline number.

The paper's ablation study also supports the system-level interpretation:

| Configuration | IC | RankIC | ICIR | RankICIR | AER | IR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Base agent | 0.0300 | 0.0318 | 0.2501 | 0.2595 | 0.0789 | 0.8015 |
| + thinking evolution | 0.0219 | 0.0420 | 0.1932 | 0.3322 | 0.0808 | 0.8999 |
| + adaptive generation | 0.0315 | 0.0491 | 0.2568 | 0.3583 | 0.0825 | 1.0145 |
| + diversified guidance | 0.0414 | 0.0501 | 0.3239 | 0.3599 | 0.1245 | 1.4668 |
| **+ seven-level agent hierarchy (CogAlpha)** | **0.0591** | **0.0814** | **0.3410** | **0.4350** | **0.1639** | **1.8999** |

Finally, the reported Ridge results generalize beyond one index:

| Dataset / horizon | IC | RankIC | ICIR | RankICIR |
| --- | ---: | ---: | ---: | ---: |
| CSI300 / 10 days | 0.0539 | 0.0714 | 0.3471 | 0.4380 |
| CSI300 / 30 days | 0.0815 | 0.1069 | 0.4408 | 0.5403 |
| CSI500 / 10 days | 0.0455 | 0.0738 | 0.2903 | 0.4752 |
| S&P500 / 10 days | 0.0217 | 0.0226 | 0.2189 | 0.1726 |
| HSI / 10 days | 0.0327 | 0.0400 | 0.1903 | 0.2330 |
| HSCI / 10 days | 0.0562 | 0.0495 | 0.5396 | 0.4394 |

These values come from Tables 1, 3, and 5 of the paper. Alpha Garden does not
present them as its own benchmark. Any Alpha Garden experiment must report its
own data window, costs, splits, candidate budget, and sealed-test result before
the two approaches can be compared responsibly.

## Research workflow

1. Interview the user and freeze a machine-readable experiment specification.
2. Generate a problem-specific, read-only evolution monitor.
3. Acquire and audit point-in-time market data.
4. Freeze execution timing, costs, validation splits, gates, and search budget.
5. Seed diverse candidate families from the user's ideas and controlled
   creative directions.
6. Dispatch isolated agent tasks to create, mutate, cross over, repair, or
   challenge candidates.
7. Compile and backtest every candidate under deterministic contracts.
8. Breed from walk-forward evidence while keeping the final holdout sealed.
9. Freeze finalists, open the holdout once, and publish code plus an auditable
   report—even when no strategy passes.

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

The simplest option is to give the repository URL to your agent:

```text
Install the evolve-trading-strategy skill from
https://github.com/YoungY620/Alpha-Garden.git
```

The agent can clone the repository, locate the nested skill, and install it in
the correct skills directory for its host.

For a manual installation, copy the nested skill folder into the skills
directory used by your agent host:

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
