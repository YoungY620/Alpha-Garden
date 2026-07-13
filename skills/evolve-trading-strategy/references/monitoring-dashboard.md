# Live evolution monitor

Generate the frontend for the current problem after the experiment spec is
confirmed and before generation zero starts. The skill supplies no fixed page
template. Use plain HTML, CSS, and TypeScript or JavaScript by default. Prefer
`@visactor/vchart` for charts and bundle it locally; do not depend on a CDN.
Use React or Vue only when the required interactions justify the extra layer.

## Fixed runtime contract

Use `experiment.sqlite` as the single authority for scheduling, recovery, and
monitoring. Write state only through `scripts/manage_experiment.py`. Serve the
generated frontend with `scripts/serve_dashboard.py`, whose database connection
is read-only. It exposes exactly these experiment APIs:

- `GET /api/health`
- `GET /api/snapshot`
- `GET /api/generations/<generation>`
- `GET /api/candidates/<candidate_id>`

Poll snapshot every two seconds. Honor ETag and treat `304` as no change. Load
generation and candidate details only when requested. Never add a write route,
arbitrary SQL, arbitrary file access, or a control action. Bind to `localhost`.
For remote compute, use an authorized secure port forward without persisting
host or account details in artifacts.

## Required information

- Current phase, generation, elapsed time, and pending/running/complete/failed
  task counts.
- Target, valid, qualified, selected, and replenishment population counts.
- Existing evaluator outputs by generation, including fitness, violation,
  qualification, diversity, and complexity when present.
- Candidate space, expert-mode coverage, lineage, and effective or ineffective
  mechanism summaries.
- A short research-progress feed explaining hypotheses, improvements, repeated
  failures, diversity collapse, next exploration, risks, and uncertainty.
- Data coverage, accessible split, validation access, sealed-test lock state,
  protocol version, and integrity warnings.

Do not invent a metric, benchmark, score, or selection rule for the dashboard.
Render only authoritative experiment outputs. Clearly separate train,
validation, and sealed-test state. A valid but unqualified candidate may be
shown as promising but never as qualified.

Candidate detail may show its hypothesis, parents, mutation direction, status,
parameters, existing metrics, violation components, selection explanation,
charts, and relative artifact links. Keep full prompts, responses, source code,
and long logs outside the page.

## Interaction and visual quality

Permit filtering, sorting, search, zoom, candidate comparison, metric toggles,
and client-side CSV or screenshot export. These interactions change browser
view state only. Use sign, label, and color together; never rely on red and
green alone. Keep units and dataset splits visible.

Validate the design with a separate, clearly marked fixture that never enters
the experiment database. Then switch to the live empty state, which shows the
confirmed spec and waits for generation zero without fake candidates. Verify
health, snapshot, ETag polling, desktop rendering, narrow-screen summary,
keyboard focus, and reduced motion. Give the user the live local URL before
starting generation zero. The Flask process may remain running; if it fails,
restart it against the same database without interrupting research.

