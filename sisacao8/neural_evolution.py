"""Neural EOD deterministic evolution helpers."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping, Sequence
from uuid import NAMESPACE_URL, uuid5

MODEL_ID = "neural_eod_mlp"


@dataclass(frozen=True)
class EvolutionBudget:
    """Execution limits for one deterministic neural evolution round."""

    max_trials: int = 10
    max_runtime_minutes: int = 240
    max_parameter_count: int = 150_000
    max_layers: int = 4
    random_seed: int = 20260621


@dataclass(frozen=True)
class CandidateConfig:
    """Validated candidate produced by the deterministic phase-1 generator."""

    candidate_id: str
    evolution_run_id: str
    model_id: str
    model_version: str
    candidate_source: str
    architecture: dict[str, Any]
    hyperparameters: dict[str, Any]
    training_request: dict[str, Any]
    dedupe_hash: str
    schema_validation_status: str = "valid"


@dataclass(frozen=True)
class EvaluationScore:
    """Weighted leaderboard score and gate decision for a trained candidate."""

    score_total: float
    score_directional_precision: float
    score_coverage: float
    score_generalization: float
    score_stability: float
    score_cost_penalty: float
    decision: str
    decision_reasons: tuple[str, ...] = field(default_factory=tuple)


HIDDEN_UNITS_SPACE: tuple[tuple[int, ...], ...] = (
    (32,),
    (64, 32),
    (128, 64),
    (128, 64, 32),
    (256, 128, 64),
)
DROPOUT_SPACE = (0.0, 0.10, 0.15, 0.25, 0.35)
LEARNING_RATE_SPACE = (0.0003, 0.0005, 0.001, 0.002)
BATCH_SIZE_SPACE = (128, 256, 512)
EPOCHS_SPACE = (20, 40, 80)
FINALIST_SEEDS = (20260701, 20260702, 20260703)


def generate_deterministic_candidates(
    *,
    evolution_run_id: str,
    dataset_snapshot: str,
    budget: EvolutionBudget | None = None,
    existing_hashes: Iterable[str] | None = None,
    model_version_prefix: str = "neural_eod_mlp_evo1",
) -> list[CandidateConfig]:
    """Return a reproducible random-search candidate list within budget."""

    selected_budget = budget or EvolutionBudget()
    seen = set(existing_hashes or [])
    rng = random.Random(selected_budget.random_seed)
    candidates: list[CandidateConfig] = []
    attempts = 0
    max_attempts = max(selected_budget.max_trials * 20, 20)

    while len(candidates) < selected_budget.max_trials and attempts < max_attempts:
        attempts += 1
        hidden_units = rng.choice(HIDDEN_UNITS_SPACE)
        architecture = {
            "type": "mlp",
            "hidden_units": list(hidden_units),
            "batch_norm": False,
        }
        if len(hidden_units) > selected_budget.max_layers:
            continue
        if estimate_parameter_count(hidden_units) > selected_budget.max_parameter_count:
            continue

        hyperparameters = {
            "dropout_rate": rng.choice(DROPOUT_SPACE),
            "learning_rate": rng.choice(LEARNING_RATE_SPACE),
            "batch_size": rng.choice(BATCH_SIZE_SPACE),
            "epochs": rng.choice(EPOCHS_SPACE),
            "random_seed": selected_budget.random_seed + attempts,
            "early_stopping": True,
            "early_stopping_patience": 8,
            "class_weight": rng.choice(("none", "balanced", "directional")),
        }
        dedupe_hash = candidate_hash(architecture, hyperparameters)
        if dedupe_hash in seen:
            continue
        seen.add(dedupe_hash)
        index = len(candidates) + 1
        model_version = f"{model_version_prefix}_{index:02d}"
        training_request = {
            "dataset_snapshot": dataset_snapshot,
            "model_id": MODEL_ID,
            "model_version": model_version,
            "hidden_units": list(hidden_units),
            "dropout_rate": hyperparameters["dropout_rate"],
            "learning_rate": hyperparameters["learning_rate"],
            "batch_size": hyperparameters["batch_size"],
            "epochs": hyperparameters["epochs"],
            "random_seed": hyperparameters["random_seed"],
            "early_stopping": hyperparameters["early_stopping"],
            "early_stopping_patience": hyperparameters["early_stopping_patience"],
            "class_weight": hyperparameters["class_weight"],
            "status": "candidate",
            "notes": f"Fase 1 evolução determinística; candidate_index={index}",
        }
        candidate_id = str(uuid5(NAMESPACE_URL, f"{evolution_run_id}:{dedupe_hash}"))
        candidates.append(
            CandidateConfig(
                candidate_id=candidate_id,
                evolution_run_id=evolution_run_id,
                model_id=MODEL_ID,
                model_version=model_version,
                candidate_source="deterministic",
                architecture=architecture,
                hyperparameters=hyperparameters,
                training_request=training_request,
                dedupe_hash=dedupe_hash,
            )
        )
    return candidates


def select_top_candidates(
    scored_candidates: Sequence[tuple[CandidateConfig, EvaluationScore]],
    *,
    top_fraction: float = 0.20,
) -> list[CandidateConfig]:
    """Return top candidates to exploit in phase 2, sorted by score descending."""

    if not scored_candidates:
        return []
    selected_count = max(1, int(len(scored_candidates) * top_fraction))
    ordered = sorted(
        scored_candidates, key=lambda item: item[1].score_total, reverse=True
    )
    return [candidate for candidate, _score in ordered[:selected_count]]


def select_diverse_top_candidates(
    scored_candidates: Sequence[tuple[CandidateConfig, EvaluationScore]],
    *,
    top_fraction: float = 0.20,
    max_per_family: int = 1,
) -> list[CandidateConfig]:
    """Return top candidates after consolidating similar candidate families.

    The family signature ignores random seed so repeated evaluations of the same
    configuration do not occupy multiple parent slots in phase 2.
    """

    if not scored_candidates:
        return []
    selected_count = max(1, int(len(scored_candidates) * top_fraction))
    family_limit = max(1, int(max_per_family))
    ordered = sorted(
        scored_candidates,
        key=lambda item: (
            item[1].score_total,
            item[1].score_directional_precision,
            item[1].score_coverage,
        ),
        reverse=True,
    )
    selected: list[CandidateConfig] = []
    family_counts: dict[str, int] = {}
    for candidate, _score in ordered:
        family_key = candidate_family_key(
            candidate.architecture, candidate.hyperparameters
        )
        if family_counts.get(family_key, 0) >= family_limit:
            continue
        selected.append(candidate)
        family_counts[family_key] = family_counts.get(family_key, 0) + 1
        if len(selected) >= selected_count:
            break
    return selected


def mutate_top_candidates(
    top_candidates: Sequence[CandidateConfig],
    *,
    evolution_run_id: str,
    dataset_snapshot: str,
    budget: EvolutionBudget | None = None,
    existing_hashes: Iterable[str] | None = None,
    model_version_prefix: str = "neural_eod_mlp_evo2_mutation",
) -> list[CandidateConfig]:
    """Exploit prior winners by mutating learning rate, dropout and class weights."""

    selected_budget = budget or EvolutionBudget(max_trials=10, random_seed=20260622)
    seen = set(existing_hashes or [])
    candidates: list[CandidateConfig] = []
    for parent in top_candidates:
        parent_hidden = tuple(int(item) for item in parent.architecture["hidden_units"])
        parent_hp = parent.hyperparameters
        for mutation in _mutation_grid(parent_hp):
            if len(candidates) >= selected_budget.max_trials:
                return candidates
            architecture = dict(parent.architecture)
            architecture["hidden_units"] = list(parent_hidden)
            if (
                estimate_parameter_count(parent_hidden)
                > selected_budget.max_parameter_count
            ):
                continue
            hyperparameters = {**parent_hp, **mutation}
            hyperparameters["early_stopping"] = True
            hyperparameters.setdefault("early_stopping_patience", 8)
            dedupe_hash = candidate_hash(architecture, hyperparameters)
            if dedupe_hash in seen:
                continue
            seen.add(dedupe_hash)
            index = len(candidates) + 1
            candidates.append(
                _candidate_from_parts(
                    evolution_run_id=evolution_run_id,
                    dataset_snapshot=dataset_snapshot,
                    model_version=f"{model_version_prefix}_{index:02d}",
                    candidate_source="mutation",
                    architecture=architecture,
                    hyperparameters=hyperparameters,
                    dedupe_hash=dedupe_hash,
                    notes=(
                        f"Fase 2 mutação de {parent.model_version}; "
                        f"candidate_index={index}"
                    ),
                )
            )
    return candidates


def repeat_finalists_with_fresh_seeds(
    finalists: Sequence[CandidateConfig],
    *,
    evolution_run_id: str,
    dataset_snapshot: str,
    budget: EvolutionBudget,
    existing_hashes: Iterable[str] | None = None,
    model_version_prefix: str = "neural_eod_mlp_evo2_seed_fresh",
) -> list[CandidateConfig]:
    """Return seed-repeat candidates that are not already in ``existing_hashes``.

    Phase-2 automation can exhaust the finite mutation grid.  In that state the
    safest next candidate is a repeat of a strong finalist with a new seed: it
    preserves the economic hypothesis while producing fresh stability evidence
    and a new dedupe hash.
    """

    seen = set(existing_hashes or [])
    repeated: list[CandidateConfig] = []
    seed_offset = 0
    max_attempts = max(budget.max_trials * max(len(finalists), 1) * 50, 50)

    while len(repeated) < budget.max_trials and seed_offset < max_attempts:
        for finalist_index, finalist in enumerate(finalists, start=1):
            if len(repeated) >= budget.max_trials:
                break
            seed = int(budget.random_seed) + 10_000 + seed_offset
            seed_offset += 1
            hyperparameters = {**finalist.hyperparameters, "random_seed": seed}
            hyperparameters["early_stopping"] = True
            hyperparameters.setdefault("early_stopping_patience", 8)
            architecture = dict(finalist.architecture)
            dedupe_hash = candidate_hash(architecture, hyperparameters)
            if dedupe_hash in seen:
                continue
            seen.add(dedupe_hash)
            repeated.append(
                _candidate_from_parts(
                    evolution_run_id=evolution_run_id,
                    dataset_snapshot=dataset_snapshot,
                    model_version=(f"{model_version_prefix}_{len(repeated) + 1:02d}"),
                    candidate_source="seed_repeat_fresh",
                    architecture=architecture,
                    hyperparameters=hyperparameters,
                    dedupe_hash=dedupe_hash,
                    notes=(
                        f"Fase 2 repetição com seed inédita de "
                        f"{finalist.model_version}; parent_index={finalist_index}"
                    ),
                )
            )

    return repeated


def repeat_finalists_with_seeds(
    finalists: Sequence[CandidateConfig],
    *,
    evolution_run_id: str,
    dataset_snapshot: str,
    seeds: Sequence[int] = FINALIST_SEEDS,
    model_version_prefix: str = "neural_eod_mlp_evo2_seed",
) -> list[CandidateConfig]:
    """Repeat finalist configurations with multiple seeds for stability evidence."""

    repeated: list[CandidateConfig] = []
    for finalist_index, finalist in enumerate(finalists, start=1):
        for seed in seeds:
            hyperparameters = {**finalist.hyperparameters, "random_seed": int(seed)}
            hyperparameters["early_stopping"] = True
            hyperparameters.setdefault("early_stopping_patience", 8)
            architecture = dict(finalist.architecture)
            dedupe_hash = candidate_hash(architecture, hyperparameters)
            model_version = f"{model_version_prefix}_{finalist_index:02d}_{int(seed)}"
            repeated.append(
                _candidate_from_parts(
                    evolution_run_id=evolution_run_id,
                    dataset_snapshot=dataset_snapshot,
                    model_version=model_version,
                    candidate_source="seed_repeat",
                    architecture=architecture,
                    hyperparameters=hyperparameters,
                    dedupe_hash=dedupe_hash,
                    notes=f"Fase 2 repetição multi-seed de {finalist.model_version}",
                )
            )
    return repeated


def penalized_score(
    metrics: Mapping[str, Any],
    *,
    hidden_units: Sequence[int],
    runtime_minutes: float = 0.0,
    max_runtime_minutes: float = 240.0,
) -> EvaluationScore:
    """Score candidates with extra penalties for cost and instability."""

    base = score_candidate(metrics, hidden_units=hidden_units)
    parameter_penalty = (
        min(estimate_parameter_count(hidden_units) / 150_000, 1.0) * 0.05
    )
    runtime_penalty = min(runtime_minutes / max(max_runtime_minutes, 1.0), 1.0) * 0.05
    total_cost_penalty = round(
        base.score_cost_penalty + parameter_penalty + runtime_penalty, 6
    )
    adjusted_total = round(base.score_total - parameter_penalty - runtime_penalty, 6)
    return replace(
        base,
        score_total=adjusted_total,
        score_cost_penalty=total_cost_penalty,
    )


def _mutation_grid(hyperparameters: Mapping[str, Any]) -> list[dict[str, Any]]:
    lr = float(hyperparameters.get("learning_rate", 0.001))
    dropout = float(hyperparameters.get("dropout_rate", 0.15))
    epochs = int(hyperparameters.get("epochs", 40))
    return [
        {
            "learning_rate": max(lr / 2, 0.0001),
            "dropout_rate": max(dropout - 0.05, 0.0),
            "epochs": min(epochs + 20, 100),
            "class_weight": "balanced",
        },
        {
            "learning_rate": lr,
            "dropout_rate": dropout,
            "epochs": min(epochs + 20, 100),
            "class_weight": "directional",
        },
        {
            "learning_rate": min(lr * 2, 0.003),
            "dropout_rate": min(dropout + 0.05, 0.45),
            "epochs": epochs,
            "class_weight": "balanced",
        },
    ]


def _candidate_from_parts(
    *,
    evolution_run_id: str,
    dataset_snapshot: str,
    model_version: str,
    candidate_source: str,
    architecture: Mapping[str, Any],
    hyperparameters: Mapping[str, Any],
    dedupe_hash: str,
    notes: str,
) -> CandidateConfig:
    training_request = {
        "dataset_snapshot": dataset_snapshot,
        "model_id": MODEL_ID,
        "model_version": model_version,
        "hidden_units": list(architecture["hidden_units"]),
        "dropout_rate": hyperparameters["dropout_rate"],
        "learning_rate": hyperparameters["learning_rate"],
        "batch_size": hyperparameters["batch_size"],
        "epochs": hyperparameters["epochs"],
        "random_seed": hyperparameters["random_seed"],
        "early_stopping": hyperparameters["early_stopping"],
        "early_stopping_patience": hyperparameters["early_stopping_patience"],
        "class_weight": hyperparameters["class_weight"],
        "status": "candidate",
        "notes": notes,
    }
    candidate_id = str(uuid5(NAMESPACE_URL, f"{evolution_run_id}:{dedupe_hash}"))
    return CandidateConfig(
        candidate_id=candidate_id,
        evolution_run_id=evolution_run_id,
        model_id=MODEL_ID,
        model_version=model_version,
        candidate_source=candidate_source,
        architecture=dict(architecture),
        hyperparameters=dict(hyperparameters),
        training_request=training_request,
        dedupe_hash=dedupe_hash,
    )


def candidate_family_key(
    architecture: Mapping[str, Any], hyperparameters: Mapping[str, Any]
) -> str:
    """Stable key for consolidating nearly identical neural candidates.

    The key keeps architecture and training knobs that define the model family,
    but intentionally ignores ``random_seed`` and early-stopping bookkeeping.
    """

    family_payload = {
        "architecture": {
            "type": architecture.get("type", "mlp"),
            "hidden_units": [
                int(item) for item in architecture.get("hidden_units", [])
            ],
            "batch_norm": bool(architecture.get("batch_norm", False)),
        },
        "hyperparameters": {
            "batch_size": _optional_int(hyperparameters.get("batch_size")),
            "class_weight": str(hyperparameters.get("class_weight", "none")),
            "dropout_rate": _rounded_float(hyperparameters.get("dropout_rate"), 4),
            "epochs": _optional_int(hyperparameters.get("epochs")),
            "learning_rate": _rounded_float(hyperparameters.get("learning_rate"), 6),
        },
    }
    return hashlib.sha256(
        json.dumps(family_payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def candidate_hash(
    architecture: Mapping[str, Any], hyperparameters: Mapping[str, Any]
) -> str:
    """Stable hash used to deduplicate architecture/hyperparameter pairs."""

    payload = json.dumps(
        {"architecture": architecture, "hyperparameters": hyperparameters},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def estimate_parameter_count(
    hidden_units: Sequence[int], feature_count: int = 19, classes: int = 3
) -> int:
    """Estimate dense MLP parameters for budget validation."""

    previous = feature_count
    total = 0
    for units in hidden_units:
        total += (previous + 1) * int(units)
        previous = int(units)
    total += (previous + 1) * classes
    return total


def score_candidate(
    metrics: Mapping[str, Any], *, max_layers: int = 4, hidden_units: Sequence[int] = ()
) -> EvaluationScore:
    """Score one trained candidate using the phase-1 leaderboard formula."""

    train = _split(metrics, "train")
    validation = _split(metrics, "validation")
    test = _split(metrics, "test")
    reasons: list[str] = []
    if not test:
        reasons.append("test_missing")
    coverage_test = _number(test.get("coverage"))
    precision_test = _number(test.get("directional_precision"))
    precision_validation = _number(validation.get("directional_precision"))
    accuracy_test = _number(test.get("accuracy"))
    accuracy_train = _number(train.get("accuracy"))
    if coverage_test is None or coverage_test < 0.05:
        reasons.append("coverage_test_below_minimum")
    if precision_test is None or precision_test <= 0.34:
        reasons.append("directional_precision_test_below_baseline")
    overfit = max((accuracy_train or 0.0) - (accuracy_test or 0.0), 0.0)
    if overfit > 0.20:
        reasons.append("severe_train_test_overfit")

    stability = 1.0 - min(
        abs((precision_validation or 0.0) - (precision_test or 0.0)), 1.0
    )
    complexity_penalty = min(len(hidden_units) / max(max_layers, 1), 1.0) * 0.05
    score_total = (
        0.30 * (precision_test or 0.0)
        + 0.20 * (precision_validation or 0.0)
        + 0.15 * (coverage_test or 0.0)
        + 0.15 * (accuracy_test or 0.0)
        + 0.10 * stability
        - 0.10 * overfit
        - complexity_penalty
    )
    decision = "keep_candidate" if not reasons else "reject"
    if decision == "keep_candidate" and score_total >= 0.45:
        decision = "shadow_candidate"
    return EvaluationScore(
        score_total=round(score_total, 6),
        score_directional_precision=round(precision_test or 0.0, 6),
        score_coverage=round(coverage_test or 0.0, 6),
        score_generalization=round(max(1.0 - overfit, 0.0), 6),
        score_stability=round(stability, 6),
        score_cost_penalty=round(complexity_penalty, 6),
        decision=decision,
        decision_reasons=tuple(reasons),
    )


def _split(metrics: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = metrics.get(name)
    return value if isinstance(value, Mapping) else {}


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _rounded_float(value: Any, digits: int) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)
