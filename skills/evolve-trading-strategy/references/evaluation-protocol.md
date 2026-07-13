# Evaluation and selection protocol

## Evidence partitions

- Train: generate, tune, and obtain purged walk-forward development evidence.
- Validation: confirm a frozen shortlist only at pre-registered checkpoints.
- Sealed test: open once after finalist code and parameters are frozen.

Fit transformations on train only. Record every validation access and the single
sealed-test opening. Any post-test optimization starts a new experiment with a
new untouched test range.

## Keep validity separate from qualification

Store only four selection fields:

- `is_valid`: code is executable, causal, aligned, numerically safe, produces
  non-degenerate trading behavior, and obeys prohibited-position and
  data-access rules.
- `is_qualified`: every pre-registered final evidence gate passed.
- `violation_score`: normalized distance from gates that did not pass; lower is
  better and zero means all gates passed.
- `fitness`: the user-approved primary development objective; higher is better.

Exclude a candidate from breeding only when `is_valid` is false. Missing return,
risk, trade-count, stability, stress, PSR, or DSR targets must set
`is_qualified` false and increase `violation_score`, but must not erase an
otherwise valid individual.

Keep final qualification strict. Breeding eligibility is not evidence that a
strategy is suitable for delivery, validation, sealed testing, or live use.

## Calibration

If a fold has fully feasible parameter sets, select the best feasible set. If
none is feasible, select the set with the smallest violation score for
development feedback and record `calibration_feasible = false`. Never describe
that fold as qualification evidence.

## Fixed breeding population

Generation 0 targets 22 valid individuals. Generation 1 and later target 42.
For every full generation:

1. Combine the previous parents and all new children.
2. Remove invalid candidates and behavioral duplicates.
3. Rank by lower `violation_score`, higher `fitness`, and lower complexity.
4. Take the best valid candidate from each represented expert direction.
5. Fill remaining seats from the global ranking.
6. If seats remain empty, generate exactly that many fresh seeds from
   underrepresented directions, evaluate them, and rerun selection.

Do not stop because `is_qualified` is zero. Stop only at the confirmed budget,
after three generations without material improvement in both best fitness and
lowest violation score, or when the user stops the run. At the end, report
honestly when no strategy qualifies.

## Multiple testing

Record every attempted candidate and parameter combination. Use PSR, DSR,
bootstrap, and PBO where defensible for qualification and reporting. Do not use
these final evidence checks to empty the breeding population.
