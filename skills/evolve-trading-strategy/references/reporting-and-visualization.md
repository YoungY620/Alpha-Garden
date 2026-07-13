# PDF reporting and visualization

The formal deliverables are runnable strategy code and a professional financial
research PDF. HTML may be an optional companion, never the only report.

## Visual system

Use an institutional quantitative-research aesthetic: A4 portrait body, rare
landscape pages for wide evidence, restrained navy and graphite palette,
consistent grid, embedded fonts, tabular numerals, visible units, and generous
white space. Prefer Source Han Sans for Chinese headings, Source Han Serif for
Chinese prose, Source Sans 3 for Latin text and numerals, and IBM Plex Mono for
code when available. Discover fonts or accept paths through CLI/environment;
never commit machine-local font paths.

Use sign, label, and color together. Never rely only on red/green. Do not crop
axes or omit bad periods to improve appearance.

## Required narrative

Explain the investment hypothesis, transformation of user ideas, lineage,
entry/add/reduce/exit/stop/cooldown branches, condition precedence, missing and
abnormal data behavior, every parameter and selected value, execution and cost
assumptions, split isolation, metrics, statistical corrections, strengths,
risks, unknowns, valid regimes, and failure regimes.

## Required evidence

- Data coverage and split timeline
- Search and elimination funnel
- 21 by 5 expert-mode heatmap
- Best, median, qualification rate, and diversity by generation
- Lineage graph and effective/ineffective mechanism summaries
- Equity, drawdown, rolling risk, and benchmark comparison
- Trade, holding-time, monthly-return, and regime distributions
- Parameter stability and cost/slippage sensitivity
- Walk-forward panels, bootstrap distribution, DSR/PSR, and PBO status
- Sealed-test status and unique opening ledger event

Visually separate train, validation, and sealed-test results. Put material risks
in the executive summary rather than hiding them in an appendix.

## PDF quality gate

Generate with ReportLab, embed fonts, and keep charts sharp. Check PDF metadata,
page count, text extraction, and embedded fonts. Render every page to PNG with
Poppler and inspect alignment, clipping, table breaks, glyphs, legends, headers,
footers, and transitions. Regenerate after any meaningful change. Deliver only
after the latest rendered pages have zero visual defects.
