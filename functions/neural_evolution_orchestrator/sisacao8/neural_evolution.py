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
DEFAULT_MIN_DIRECTIONAL_PROBABILITY = 0.45
DEFAULT_MIN_DIRECTIONAL_MARGIN = 0.05
PHASE3_FAMILY_SPACE: tuple[dict[str, Any], ...] = (
    {
        "architecture_type": "residual_mlp",
        "model_id": "neural_eod_residual_mlp",
        "hidden_units": (128, 64),
        "dropout_rate": 0.15,
        "learning_rate": 0.0005,
        "batch_size": 256,
        "epochs": 60,
        "class_weight": "balanced",
    },
    {
        "architecture_type": "wide_deep_mlp",
        "model_id": "neural_eod_wide_deep_mlp",
        "hidden_units": (128, 64, 32),
        "dropout_rate": 0.10,
        "learning_rate": 0.0005,
        "batch_size": 256,
        "epochs": 60,
        "class_weight": "directional",
    },
    {
        "architecture_type": "tabular_bottleneck_mlp",
        "model_id": "neural_eod_tabular_bottleneck_mlp",
        "hidden_units": (256, 64, 16),
        "dropout_rate": 0.25,
        "learning_rate": 0.0003,
        "batch_size": 256,
        "epochs": 80,
        "class_weight": "balanced",
    },
)

PHASE4_RECURRENT_SPACE: tuple[dict[str, Any], ...] = (
    {
        "architecture_type": "gru_sequence",
        "model_id": "neural_eod_gru_sequence",
        "hidden_units": (32,),
        "dropout_rate": 0.20,
        "learning_rate": 0.0003,
        "batch_size": 128,
        "epochs": 60,
        "class_weight": "balanced",
        "sequence_lookback": 20,
        "min_directional_probability": 0.50,
        "min_directional_margin": 0.08,
        "max_trades_per_fold": 35,
        "candidate_family_hash": "neural_eod_phase4_gru_sequence_p50_m08_t35_l20",
    },
    {
        "architecture_type": "lstm_sequence",
        "model_id": "neural_eod_lstm_sequence",
        "hidden_units": (32,),
        "dropout_rate": 0.20,
        "learning_rate": 0.0003,
        "batch_size": 128,
        "epochs": 60,
        "class_weight": "balanced",
        "sequence_lookback": 20,
        "min_directional_probability": 0.50,
        "min_directional_margin": 0.08,
        "max_trades_per_fold": 35,
        "candidate_family_hash": "neural_eod_phase4_lstm_sequence_p50_m08_t35_l20",
    },
    {
        "architecture_type": "tcn_sequence",
        "model_id": "neural_eod_tcn_sequence",
        "hidden_units": (32,),
        "dropout_rate": 0.20,
        "learning_rate": 0.0003,
        "batch_size": 128,
        "epochs": 60,
        "class_weight": "balanced",
        "sequence_lookback": 20,
        "min_directional_probability": 0.50,
        "min_directional_margin": 0.08,
        "max_trades_per_fold": 35,
        "candidate_family_hash": "neural_eod_phase4_tcn_sequence_p50_m08_t35_l20",
    },
)


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
            "min_directional_probability": DEFAULT_MIN_DIRECTIONAL_PROBABILITY,
            "min_directional_margin": DEFAULT_MIN_DIRECTIONAL_MARGIN,
            "max_trades_per_fold": None,
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


def generate_architecture_variant_candidates(
    finalists: Sequence[CandidateConfig],
    *,
    evolution_run_id: str,
    dataset_snapshot: str,
    budget: EvolutionBudget,
    existing_hashes: Iterable[str] | None = None,
    model_version_prefix: str = "neural_eod_mlp_evo2_arch",
) -> list[CandidateConfig]:
    """Return new candidates by changing finalist hidden-layer topologies.

    This is the preferred fallback when Phase 2 has exhausted ordinary
    hyperparameter mutations: keep the best economic families as parents, but
    explore wider, narrower, deeper and shallower MLP shapes before resorting
    to pure seed repeats.
    """

    seen = set(existing_hashes or [])
    candidates: list[CandidateConfig] = []
    seed_offset = 0
    for parent in finalists:
        parent_hidden = tuple(int(item) for item in parent.architecture["hidden_units"])
        for hidden_units in _architecture_variant_space(parent_hidden):
            if len(candidates) >= budget.max_trials:
                return candidates
            if len(hidden_units) > budget.max_layers:
                continue
            if estimate_parameter_count(hidden_units) > budget.max_parameter_count:
                continue
            architecture = dict(parent.architecture)
            architecture["hidden_units"] = list(hidden_units)
            hyperparameters = dict(parent.hyperparameters)
            hyperparameters["random_seed"] = (
                int(budget.random_seed) + 20_000 + seed_offset
            )
            hyperparameters["early_stopping"] = True
            hyperparameters.setdefault("early_stopping_patience", 8)
            seed_offset += 1
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
                    candidate_source="architecture_variant",
                    architecture=architecture,
                    hyperparameters=hyperparameters,
                    dedupe_hash=dedupe_hash,
                    notes=(
                        f"Fase 2 arquitetura alternativa de {parent.model_version}; "
                        f"hidden_units={list(hidden_units)}; candidate_index={index}"
                    ),
                )
            )
    return candidates


def generate_controlled_diversity_candidates(
    finalists: Sequence[CandidateConfig],
    *,
    evolution_run_id: str,
    dataset_snapshot: str,
    budget: EvolutionBudget,
    existing_hashes: Iterable[str] | None = None,
    model_version_prefix: str = "neural_eod_mlp_evo2_diversity",
) -> list[CandidateConfig]:
    """Return bounded candidates that vary architecture and training knobs.

    This fallback is intentionally more diverse than a fresh-seed repeat, but
    still controlled: it keeps MLP/tabular EOD assumptions, respects layer and
    parameter budgets, avoids pure seed-only variants of the selected parents,
    and limits exploration to a compact grid around known finalists.
    """

    seen_hashes = set(existing_hashes or [])
    seen_family_keys = {
        candidate_family_key(parent.architecture, parent.hyperparameters)
        for parent in finalists
    }
    candidates: list[CandidateConfig] = []
    seed_offset = 0

    for parent_index, parent in enumerate(finalists, start=1):
        parent_hidden = tuple(int(item) for item in parent.architecture["hidden_units"])
        parent_hp = parent.hyperparameters
        for hidden_units in _controlled_diversity_architecture_space(parent_hidden):
            if len(hidden_units) > budget.max_layers:
                continue
            if estimate_parameter_count(hidden_units) > budget.max_parameter_count:
                continue
            for hp_variant in _controlled_diversity_hyperparameter_space(parent_hp):
                if len(candidates) >= budget.max_trials:
                    return candidates
                architecture = dict(parent.architecture)
                architecture["hidden_units"] = list(hidden_units)
                architecture["type"] = str(architecture.get("type", "mlp"))
                hyperparameters = {**parent_hp, **hp_variant}
                hyperparameters["random_seed"] = (
                    int(budget.random_seed) + 40_000 + seed_offset
                )
                hyperparameters["early_stopping"] = True
                hyperparameters.setdefault("early_stopping_patience", 8)
                seed_offset += 1

                family_key = candidate_family_key(architecture, hyperparameters)
                if family_key in seen_family_keys:
                    continue
                dedupe_hash = candidate_hash(architecture, hyperparameters)
                if dedupe_hash in seen_hashes:
                    continue
                seen_family_keys.add(family_key)
                seen_hashes.add(dedupe_hash)
                index = len(candidates) + 1
                candidates.append(
                    _candidate_from_parts(
                        evolution_run_id=evolution_run_id,
                        dataset_snapshot=dataset_snapshot,
                        model_version=f"{model_version_prefix}_{index:02d}",
                        candidate_source="controlled_diversity",
                        architecture=architecture,
                        hyperparameters=hyperparameters,
                        dedupe_hash=dedupe_hash,
                        notes=(
                            "Fase 2 diversidade controlada; "
                            f"parent={parent.model_version}; "
                            f"parent_index={parent_index}; "
                            f"hidden_units={list(hidden_units)}; "
                            f"candidate_index={index}"
                        ),
                    )
                )

    return candidates


def _architecture_variant_space(
    hidden_units: Sequence[int],
) -> tuple[tuple[int, ...], ...]:
    base = tuple(int(item) for item in hidden_units if int(item) > 0)
    if not base:
        return ()
    variants: list[tuple[int, ...]] = []

    def add(candidate: Sequence[int]) -> None:
        normalized = tuple(max(16, min(256, int(item))) for item in candidate)
        if normalized != base and normalized not in variants:
            variants.append(normalized)

    add(tuple(unit * 2 for unit in base))
    add(tuple(max(16, unit // 2) for unit in base))
    if len(base) > 1:
        add(base[:-1])
    add((*base, max(16, base[-1] // 2)))
    if len(base) == 1:
        add((base[0], max(16, base[0] // 2)))
    else:
        add((base[0], max(16, min(base[0], base[-1])), max(16, base[-1] // 2)))
    add(tuple(sorted(base, reverse=True)))

    return tuple(variants)


def _controlled_diversity_architecture_space(
    hidden_units: Sequence[int],
) -> tuple[tuple[int, ...], ...]:
    base = tuple(int(item) for item in hidden_units if int(item) > 0)
    variants = list(_architecture_variant_space(base))
    for candidate in HIDDEN_UNITS_SPACE:
        normalized = tuple(int(item) for item in candidate)
        if normalized != base and normalized not in variants:
            variants.append(normalized)
    return tuple(variants)


def _controlled_diversity_hyperparameter_space(
    hyperparameters: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    lr = float(hyperparameters.get("learning_rate", 0.001))
    dropout = float(hyperparameters.get("dropout_rate", 0.15))
    batch_size = int(hyperparameters.get("batch_size", 256))
    epochs = int(hyperparameters.get("epochs", 40))
    return (
        {
            "learning_rate": max(lr / 2, 0.0001),
            "dropout_rate": min(dropout + 0.10, 0.45),
            "batch_size": batch_size,
            "epochs": min(epochs + 20, 100),
            "class_weight": "balanced",
        },
        {
            "learning_rate": min(lr * 1.5, 0.003),
            "dropout_rate": max(dropout - 0.05, 0.0),
            "batch_size": min(max(batch_size * 2, 128), 512),
            "epochs": epochs,
            "class_weight": "directional",
        },
        {
            "learning_rate": max(lr, 0.0003),
            "dropout_rate": min(max(dropout, 0.15), 0.35),
            "batch_size": max(min(batch_size // 2, 512), 128),
            "epochs": min(max(epochs, 60), 100),
            "class_weight": "balanced",
        },
    )


def generate_phase3_family_candidates(
    *,
    evolution_run_id: str,
    dataset_snapshot: str,
    budget: EvolutionBudget,
    existing_hashes: Iterable[str] | None = None,
    model_version_prefix: str = "neural_eod_phase3_family",
    family_space: Sequence[Mapping[str, Any]] = PHASE3_FAMILY_SPACE,
    seed_repeats_only: bool = False,
) -> list[CandidateConfig]:
    """Return controlled Phase-3 candidates for new tabular neural families.

    Phase 3 intentionally keeps the same supervised EOD dataset and MUEN gate,
    but changes the trainable architecture family.  This lets research compare
    a small set of challengers against the current MLP champion without
    broadening the search enough to overfit the limited financial sample.
    """

    seen = set(existing_hashes or [])
    rng = random.Random(budget.random_seed)
    shuffled_space = list(family_space)
    rng.shuffle(shuffled_space)
    candidates: list[CandidateConfig] = []
    seed_offset = 0
    repeat_round = 0
    max_attempts = max(budget.max_trials * max(len(shuffled_space), 1) * 30, 30)
    attempts = 0

    while len(candidates) < budget.max_trials and attempts < max_attempts:
        for family in shuffled_space:
            if len(candidates) >= budget.max_trials or attempts >= max_attempts:
                break
            attempts += 1
            hidden_units = tuple(int(item) for item in family["hidden_units"])
            if len(hidden_units) > budget.max_layers:
                continue
            if estimate_parameter_count(hidden_units) > budget.max_parameter_count:
                continue
            architecture_type = str(family["architecture_type"])
            architecture = {
                "type": architecture_type,
                "hidden_units": list(hidden_units),
                "batch_norm": bool(family.get("batch_norm", False)),
                "phase": "phase3_new_family",
            }
            base_hyperparameters = {
                "dropout_rate": float(family.get("dropout_rate", 0.15)),
                "learning_rate": float(family.get("learning_rate", 0.0005)),
                "batch_size": int(family.get("batch_size", 256)),
                "epochs": int(family.get("epochs", 60)),
                "early_stopping": True,
                "early_stopping_patience": int(
                    family.get("early_stopping_patience", 10)
                ),
                "class_weight": str(family.get("class_weight", "balanced")),
                "architecture_type": architecture_type,
            }
            if family.get("min_directional_probability") is not None:
                base_hyperparameters["min_directional_probability"] = float(
                    family.get("min_directional_probability")
                )
            if family.get("min_directional_margin") is not None:
                base_hyperparameters["min_directional_margin"] = float(
                    family.get("min_directional_margin")
                )
            if family.get("max_trades_per_fold") is not None:
                base_hyperparameters["max_trades_per_fold"] = _optional_int(
                    family.get("max_trades_per_fold")
                )
            if family.get("sequence_lookback") is not None:
                base_hyperparameters["sequence_lookback"] = _optional_int(
                    family.get("sequence_lookback")
                )
            hyperparameters = _phase3_controlled_hyperparameters(
                base_hyperparameters,
                repeat_round=0 if seed_repeats_only else repeat_round,
            )
            if family.get("candidate_family_hash"):
                hyperparameters["candidate_family_hash"] = str(
                    family.get("candidate_family_hash")
                )
            hyperparameters["random_seed"] = (
                int(budget.random_seed) + 30_000 + seed_offset
            )
            seed_offset += 1
            dedupe_hash = candidate_hash(architecture, hyperparameters)
            if dedupe_hash in seen:
                continue
            seen.add(dedupe_hash)
            index = len(candidates) + 1
            repeat_suffix = (
                ""
                if repeat_round == 0
                else f"_seed{int(hyperparameters['random_seed'])}"
            )
            policy_suffix = _phase3_policy_suffix(hyperparameters)
            candidates.append(
                _candidate_from_parts(
                    evolution_run_id=evolution_run_id,
                    dataset_snapshot=dataset_snapshot,
                    model_version=(
                        f"{model_version_prefix}_{architecture_type}"
                        f"{policy_suffix}{repeat_suffix}_{index:02d}"
                    ),
                    candidate_source="phase3_family",
                    architecture=architecture,
                    hyperparameters=hyperparameters,
                    dedupe_hash=dedupe_hash,
                    notes=(
                        "Fase 3 pesquisa/shadow de nova família neural; "
                        f"architecture_type={architecture_type}; "
                        f"seed={hyperparameters['random_seed']}; "
                        f"candidate_index={index}"
                    ),
                    model_id=str(family.get("model_id") or MODEL_ID),
                )
            )
        repeat_round += 1
    return candidates


def generate_phase4_recurrent_shadow_candidates(
    *,
    evolution_run_id: str,
    dataset_snapshot: str,
    budget: EvolutionBudget,
    existing_hashes: Iterable[str] | None = None,
    model_version_prefix: str = "neural_eod_phase4_recurrent",
    family_space: Sequence[Mapping[str, Any]] = PHASE4_RECURRENT_SPACE,
    seed_repeats_only: bool = False,
) -> list[CandidateConfig]:
    """Return recurrent/causal sequence candidates for Phase-4 shadow research."""

    phase3_candidates = generate_phase3_family_candidates(
        evolution_run_id=evolution_run_id,
        dataset_snapshot=dataset_snapshot,
        budget=budget,
        existing_hashes=existing_hashes,
        model_version_prefix=model_version_prefix,
        family_space=family_space,
        seed_repeats_only=seed_repeats_only,
    )
    phase4_candidates: list[CandidateConfig] = []
    for candidate in phase3_candidates:
        training_request = dict(candidate.training_request)
        training_request["notes"] = str(training_request.get("notes", "")).replace(
            "Fase 3 pesquisa/shadow de nova família neural",
            "Fase 4 recorrente/temporal em shadow",
        )
        phase4_candidates.append(
            replace(
                candidate,
                candidate_source="phase4_recurrent_shadow",
                training_request=training_request,
            )
        )
    return phase4_candidates


def _phase3_policy_suffix(hyperparameters: Mapping[str, Any]) -> str:
    """Return a compact model-version suffix for non-default trading policies."""

    parts: list[str] = []
    probability = float(
        hyperparameters.get(
            "min_directional_probability", DEFAULT_MIN_DIRECTIONAL_PROBABILITY
        )
    )
    margin = float(
        hyperparameters.get("min_directional_margin", DEFAULT_MIN_DIRECTIONAL_MARGIN)
    )
    max_trades = _optional_int(hyperparameters.get("max_trades_per_fold"))
    if round(probability, 4) != round(DEFAULT_MIN_DIRECTIONAL_PROBABILITY, 4) or round(
        margin, 4
    ) != round(DEFAULT_MIN_DIRECTIONAL_MARGIN, 4):
        parts.extend(
            [
                f"p{int(round(probability * 100)):02d}",
                f"m{int(round(margin * 100)):02d}",
            ]
        )
    if max_trades is not None:
        parts.append(f"t{max_trades}")
    sequence_lookback = _optional_int(hyperparameters.get("sequence_lookback"))
    if sequence_lookback is not None:
        parts.append(f"l{sequence_lookback}")
    return "" if not parts else "_" + "_".join(parts)


def _phase3_controlled_hyperparameters(
    base: Mapping[str, Any],
    *,
    repeat_round: int,
) -> dict[str, Any]:
    """Return bounded Phase-3 hyperparameter variation for repeat rounds.

    Round zero keeps the declared family configuration. Later rounds alter
    training knobs in a compact, auditable grid before the same family falls
    back to pure seed-only repetition.
    """

    selected = dict(base)
    if repeat_round <= 0:
        return selected

    lr = float(base.get("learning_rate", 0.0005))
    dropout = float(base.get("dropout_rate", 0.15))
    batch_size = int(base.get("batch_size", 256))
    epochs = int(base.get("epochs", 60))
    variants = (
        {
            "learning_rate": max(lr * 0.75, 0.0001),
            "dropout_rate": min(dropout + 0.05, 0.45),
            "batch_size": batch_size,
            "epochs": min(epochs + 20, 100),
            "class_weight": "balanced",
        },
        {
            "learning_rate": min(lr * 1.25, 0.003),
            "dropout_rate": max(dropout - 0.05, 0.0),
            "batch_size": batch_size,
            "epochs": epochs,
            "class_weight": "directional",
        },
        {
            "learning_rate": lr,
            "dropout_rate": min(max(dropout, 0.20), 0.40),
            "batch_size": max(min(batch_size // 2, 512), 128),
            "epochs": min(max(epochs, 80), 100),
            "class_weight": "balanced",
        },
        {
            "learning_rate": max(lr * 0.5, 0.0001),
            "dropout_rate": min(dropout + 0.10, 0.45),
            "batch_size": min(max(batch_size * 2, 128), 512),
            "epochs": min(epochs + 10, 100),
            "class_weight": str(base.get("class_weight", "balanced")),
        },
    )
    variant = variants[(repeat_round - 1) % len(variants)]
    selected.update(variant)
    return selected


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
    model_id: str = MODEL_ID,
) -> CandidateConfig:
    training_request = {
        "dataset_snapshot": dataset_snapshot,
        "model_id": model_id,
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
        "architecture_type": architecture.get("type", "mlp"),
        "min_directional_probability": float(
            hyperparameters.get(
                "min_directional_probability",
                DEFAULT_MIN_DIRECTIONAL_PROBABILITY,
            )
        ),
        "min_directional_margin": float(
            hyperparameters.get(
                "min_directional_margin",
                DEFAULT_MIN_DIRECTIONAL_MARGIN,
            )
        ),
        "max_trades_per_fold": _optional_int(
            hyperparameters.get("max_trades_per_fold")
        ),
        "status": "candidate",
        "notes": notes,
    }
    if hyperparameters.get("sequence_lookback") is not None:
        training_request["sequence_lookback"] = _optional_int(
            hyperparameters.get("sequence_lookback")
        )
    if hyperparameters.get("candidate_family_hash"):
        training_request["candidate_family_hash"] = str(
            hyperparameters["candidate_family_hash"]
        )
    candidate_id = str(uuid5(NAMESPACE_URL, f"{evolution_run_id}:{dedupe_hash}"))
    return CandidateConfig(
        candidate_id=candidate_id,
        evolution_run_id=evolution_run_id,
        model_id=model_id,
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
            "min_directional_margin": _rounded_float(
                hyperparameters.get(
                    "min_directional_margin", DEFAULT_MIN_DIRECTIONAL_MARGIN
                ),
                4,
            ),
            "min_directional_probability": _rounded_float(
                hyperparameters.get(
                    "min_directional_probability",
                    DEFAULT_MIN_DIRECTIONAL_PROBABILITY,
                ),
                4,
            ),
            "max_trades_per_fold": _optional_int(
                hyperparameters.get("max_trades_per_fold")
            ),
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
    hidden_units: Sequence[int], feature_count: int = 30, classes: int = 3
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
