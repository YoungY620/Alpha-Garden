#!/usr/bin/env python3
"""Build deterministic descriptions for isolated generic agent tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPERTS = (
    ("market_cycle", "I", "market cycle, trend, range, expansion, contraction, and phase transitions"),
    ("volatility_regime", "I", "calm and turbulent volatility states and their transitions"),
    ("tail_risk", "II", "downside asymmetry, extreme loss propensity, and left-tail exposure"),
    ("crash_precursor", "II", "compression, failed breakouts, participation depletion, and pre-crash fragility"),
    ("liquidity_proxy", "III", "bar-based liquidity, price-impact, turnover, and participation proxies"),
    ("order_imbalance_proxy", "III", "bar-based directional pressure proxies without claiming true book depth"),
    ("price_volume_coherence", "III", "confirmation, divergence, and decoupling between price and volume"),
    ("volume_structure", "III", "volume persistence, concentration, surprise, bursts, and dry-ups"),
    ("directional_trend", "IV", "causal trend persistence, breakouts, path efficiency, and adjusted momentum"),
    ("reversal_exhaustion", "IV", "state-aware transient overreaction and exhaustion"),
    ("range_volatility", "IV", "range compression, expansion, breakout pressure, and close location"),
    ("lagged_response", "IV", "causal delayed adjustment among returns, range, volatility, and volume"),
    ("volatility_asymmetry", "IV", "upside and downside volatility asymmetry and persistence"),
    ("drawdown_geometry", "V", "drawdown depth, duration, speed, recovery, and failed recovery"),
    ("fractal_multiscale", "V", "path roughness, efficiency, memory, and cross-horizon agreement"),
    ("regime_gating", "VI", "economically justified state-dependent activation and sizing gates"),
    ("signal_stability", "VI", "temporal persistence, nearby-window agreement, and instability suppression"),
    ("bar_geometry", "VII", "body, wick, gap, close-location, symmetry, and multi-bar shape evidence"),
    ("creative_transform", "VII", "interpretable nonlinear transforms, saturation, soft gates, and path summaries"),
    ("compact_composite", "VII", "compact complementary fusion through gating, modulation, or confirmation"),
    ("herding_crowding_proxy", "VII", "one-instrument alignment, crowding, breakout, and unwind proxies"),
)

MODES = {
    "light": "Preserve the core mechanism and change no more than one justified detail.",
    "moderate": "Add one justified confirmation, smoothing, exit, or state nuance.",
    "creative": "Find a less obvious but financially interpretable causal expression.",
    "divergent": "Explore an adjacent mechanism and state why it remains relevant.",
    "concrete": "Specify causal indicators, parameter bounds, branches, positions, exits, and risk controls.",
}


def _sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _task(
    spec: dict,
    generation: int,
    expert: tuple[str, str, str],
    mode: str,
    parents: list[str],
    context: dict | None = None,
) -> dict:
    context = context or {}
    expert_id, layer, remit = expert
    experiment_id = spec["experiment_id"]
    task_id = f"g{generation:03d}__{expert_id}__{mode}"
    task = {
        "schema_version": "generation-task/v1",
        "task_id": task_id,
        "experiment_id": experiment_id,
        "generation": generation,
        "cell": {"expert_id": expert_id, "expert_layer": layer, "guidance_mode": mode},
        "runtime": {
            "executor": "isolated_generic_task",
            "one_candidate_only": True,
            "inherit_conversation": False,
            "allow_worker_reuse_only_with_context_reset": True,
        },
        "inputs": {
            "experiment_spec_ref": "experiment-spec.json",
            "execution_contract": "bar-v1",
            "instrument": spec["instrument"],
            "bar_interval": spec["bar_interval"],
            "available_fields": ["open", "high", "low", "close", "volume"],
            "knowledge_sources": spec.get("knowledge_sources", []),
            "testable_hypotheses": spec.get("testable_hypotheses", []),
            "creative_zone": spec.get("creative_zone", []),
            "knowledge_excerpt_ids": context.get("knowledge_excerpt_ids", []),
            "effective_memory_ids": context.get("effective_memory_ids", []),
            "ineffective_memory_ids": context.get("ineffective_memory_ids", []),
            "blind_split_access": False,
        },
        "guidance": {"research_remit": remit, "mode_instruction": MODES[mode]},
        "evolution": {
            "operator": "seed" if generation == 0 else "semantic_crossover",
            "parent_ids": parents,
            "required_semantic_delta": True,
            "forbid_code_concatenation": True,
            "novelty_constraints": context.get("novelty_constraints", []),
        },
        "constraints": {
            "binding": spec.get("binding_constraints", []),
            "soft_preferences": spec.get("soft_preferences", []),
            "single_primary_hypothesis": True,
            "max_logical_steps": int(spec.get("complexity", {}).get("max_logical_steps", 5)),
            "max_tunable_parameters": int(spec.get("complexity", {}).get("max_tunable_parameters", 8)),
            "point_in_time_only": True,
            "blind_split_access": False,
        },
        "response_contract": {
            "schema_version": "candidate-response/v1",
            "required_artifacts": ["candidate.json", "strategy.py", "params.json"],
        },
    }
    task["task_sha256"] = _sha(task)
    return task


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--generation", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--parents", type=Path, help="JSON mapping task_id to two parent IDs")
    parser.add_argument("--context", type=Path, help="JSON mapping task_id to frozen memory and novelty IDs")
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if not spec.get("confirmation", {}).get("confirmed"):
        raise SystemExit("experiment spec is not confirmed")
    parent_map = json.loads(args.parents.read_text(encoding="utf-8")) if args.parents else {}
    context_map = json.loads(args.context.read_text(encoding="utf-8")) if args.context else {}
    tasks = []
    if args.generation == 0:
        anchor = _task(
            spec,
            0,
            ("faithful_anchor", "anchor", "faithfully formalize the approved user hypothesis"),
            "concrete",
            [],
        )
        anchor["task_id"] = "g000__faithful_anchor"
        anchor["cell"]["guidance_mode"] = "faithful"
        anchor["guidance"]["mode_instruction"] = "Make no creative departure from the approved hypothesis."
        anchor["evolution"]["operator"] = "anchor"
        anchor.pop("task_sha256", None)
        anchor["task_sha256"] = _sha(anchor)
        tasks.append(anchor)
        tasks.extend(_task(spec, 0, expert, "concrete", []) for expert in EXPERTS)
    else:
        for expert in EXPERTS:
            for mode in MODES:
                task_id = f"g{args.generation:03d}__{expert[0]}__{mode}"
                parents = parent_map.get(task_id, [])
                if len(parents) != 2 or parents[0] == parents[1]:
                    raise SystemExit(f"{task_id} requires two distinct parent IDs")
                context = context_map.get(task_id, {})
                if not context.get("ineffective_memory_ids"):
                    raise SystemExit(f"{task_id} requires at least one frozen ineffective-memory ID")
                tasks.append(_task(spec, args.generation, expert, mode, parents, context))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(task, sort_keys=True) + "\n" for task in tasks), encoding="utf-8")
    print(json.dumps({"tasks": len(tasks), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
