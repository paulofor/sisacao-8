"""Optional structured Gemini advisor for neural EOD evolution.

The advisor is deliberately consultative: it only turns structured JSON into
validated candidate configurations. It never executes returned code and never
promotes models.
"""

from __future__ import annotations

import datetime as dt
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from sisacao8.neural_evolution import (
    BATCH_SIZE_SPACE,
    DROPOUT_SPACE,
    EPOCHS_SPACE,
    HIDDEN_UNITS_SPACE,
    LEARNING_RATE_SPACE,
    CandidateConfig,
    EvolutionBudget,
    _candidate_from_parts,
    candidate_hash,
    estimate_parameter_count,
)

ALLOWED_ARCHITECTURE_TYPES = {"mlp"}
ALLOWED_CLASS_WEIGHTS = {"none", "balanced", "directional"}
DEFAULT_GEMINI_MODEL = "gemini-1.5-pro"


@dataclass(frozen=True)
class AdvisorCandidateValidation:
    """Validation result for one advisor-proposed candidate."""

    accepted: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AdvisorRunAudit:
    """Persistable audit payload for one advisor interaction."""

    advisor_run_id: str
    evolution_run_id: str
    created_at: str
    model_name: str
    prompt_json: dict[str, Any]
    response_json: dict[str, Any] | None
    validation_status: str
    accepted_count: int
    rejected_count: int
    rejection_reasons: tuple[str, ...]


@dataclass(frozen=True)
class AdvisorEvaluationComparison:
    """A/B comparison between advisor and deterministic candidates."""

    advisor_count: int
    control_count: int
    advisor_best_score: float | None
    control_best_score: float | None
    advisor_won: bool
    summary: str


def build_advisor_prompt(
    *,
    leaderboard: Sequence[Mapping[str, Any]],
    budget: EvolutionBudget,
    rejected_reasons: Sequence[str] = (),
) -> dict[str, Any]:
    """Build a restricted JSON prompt without raw market data or credentials."""

    return {
        "task": "propose_neural_eod_candidate_configs",
        "guardrails": [
            "return_json_only",
            "do_not_execute_code",
            "do_not_promote_models",
            "respect_budget_and_search_space",
        ],
        "budget": {
            "max_trials": budget.max_trials,
            "max_runtime_minutes": budget.max_runtime_minutes,
            "max_parameter_count": budget.max_parameter_count,
            "max_layers": budget.max_layers,
        },
        "search_space": {
            "architecture_types": sorted(ALLOWED_ARCHITECTURE_TYPES),
            "hidden_units": [list(item) for item in HIDDEN_UNITS_SPACE],
            "dropout_rate": list(DROPOUT_SPACE),
            "learning_rate": list(LEARNING_RATE_SPACE),
            "batch_size": list(BATCH_SIZE_SPACE),
            "epochs": list(EPOCHS_SPACE),
            "class_weight": sorted(ALLOWED_CLASS_WEIGHTS),
        },
        "leaderboard_summary": [dict(item) for item in leaderboard[:10]],
        "rejected_reasons": list(rejected_reasons),
        "expected_response_schema": advisor_response_schema(),
    }


def advisor_response_schema() -> dict[str, Any]:
    """Return the local structured-output schema expected from the advisor."""

    return {
        "type": "object",
        "required": ["rationale", "candidates"],
        "properties": {
            "rationale": {"type": "string"},
            "candidates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["architecture", "hyperparameters"],
                    "properties": {
                        "architecture": {
                            "type": "object",
                            "required": ["type", "hidden_units"],
                        },
                        "hyperparameters": {
                            "type": "object",
                            "required": [
                                "dropout_rate",
                                "learning_rate",
                                "batch_size",
                                "epochs",
                            ],
                        },
                        "risk_notes": {"type": "array"},
                    },
                },
            },
        },
    }


def parse_advisor_response(raw_response: str | Mapping[str, Any]) -> dict[str, Any]:
    """Parse a structured advisor response and reject non-object payloads."""

    parsed: Any
    if isinstance(raw_response, str):
        parsed = json.loads(raw_response)
    else:
        parsed = dict(raw_response)
    if not isinstance(parsed, dict):
        raise ValueError("advisor response must be a JSON object")
    if not isinstance(parsed.get("rationale"), str):
        raise ValueError("advisor response must include string rationale")
    if not isinstance(parsed.get("candidates"), list):
        raise ValueError("advisor response must include candidates array")
    return parsed


def candidates_from_advisor_response(
    response: Mapping[str, Any],
    *,
    evolution_run_id: str,
    dataset_snapshot: str,
    budget: EvolutionBudget,
    existing_hashes: Sequence[str] = (),
    model_version_prefix: str = "neural_eod_mlp_gemini",
) -> tuple[list[CandidateConfig], list[str]]:
    """Validate advisor JSON and convert accepted entries to candidate configs."""

    seen = set(existing_hashes)
    accepted: list[CandidateConfig] = []
    rejections: list[str] = []
    raw_candidates = response.get("candidates", [])
    if not isinstance(raw_candidates, list):
        return [], ["candidates_not_array"]

    for index, raw_candidate in enumerate(raw_candidates, start=1):
        if len(accepted) >= budget.max_trials:
            rejections.append(f"candidate_{index}:budget_max_trials_exceeded")
            continue
        candidate, validation = _candidate_from_advisor_item(
            raw_candidate,
            index=index,
            evolution_run_id=evolution_run_id,
            dataset_snapshot=dataset_snapshot,
            budget=budget,
            model_version_prefix=model_version_prefix,
        )
        if not validation.accepted or candidate is None:
            rejections.extend(
                f"candidate_{index}:{reason}" for reason in validation.reasons
            )
            continue
        if candidate.dedupe_hash in seen:
            rejections.append(f"candidate_{index}:duplicate_candidate")
            continue
        seen.add(candidate.dedupe_hash)
        accepted.append(candidate)
    return accepted, rejections


def build_advisor_audit(
    *,
    advisor_run_id: str,
    evolution_run_id: str,
    model_name: str,
    prompt_json: Mapping[str, Any],
    response_json: Mapping[str, Any] | None,
    accepted_count: int,
    rejection_reasons: Sequence[str],
) -> AdvisorRunAudit:
    """Create a persistable audit record for BigQuery insertion."""

    validation_status = "accepted" if accepted_count > 0 else "rejected"
    if response_json is None:
        validation_status = "skipped"
    return AdvisorRunAudit(
        advisor_run_id=advisor_run_id,
        evolution_run_id=evolution_run_id,
        created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        model_name=model_name,
        prompt_json=dict(prompt_json),
        response_json=dict(response_json) if response_json is not None else None,
        validation_status=validation_status,
        accepted_count=accepted_count,
        rejected_count=len(rejection_reasons),
        rejection_reasons=tuple(rejection_reasons),
    )


def compare_advisor_against_control(
    *,
    advisor_scores: Sequence[float],
    control_scores: Sequence[float],
) -> AdvisorEvaluationComparison:
    """Compare advisor candidates against deterministic random/mutation control."""

    advisor_best = max(advisor_scores) if advisor_scores else None
    control_best = max(control_scores) if control_scores else None
    advisor_won = (
        advisor_best is not None
        and control_best is not None
        and advisor_best > control_best
    )
    if advisor_best is None:
        summary = "advisor_without_accepted_candidates"
    elif control_best is None:
        summary = "control_without_candidates"
    elif advisor_won:
        summary = "advisor_outperformed_control"
    else:
        summary = "control_matched_or_outperformed_advisor"
    return AdvisorEvaluationComparison(
        advisor_count=len(advisor_scores),
        control_count=len(control_scores),
        advisor_best_score=advisor_best,
        control_best_score=control_best,
        advisor_won=advisor_won,
        summary=summary,
    )


def call_gemini_structured_advisor(
    *,
    api_key: str,
    prompt_json: Mapping[str, Any],
    model_name: str = DEFAULT_GEMINI_MODEL,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Call Gemini only for structured JSON suggestions.

    The response is parsed locally before use. Credentials are passed only as an
    API key argument and are never included in the prompt.
    """

    if not api_key:
        raise ValueError("api_key is required for Gemini advisor calls")
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": json.dumps(prompt_json, sort_keys=True),
                    }
                ],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": advisor_response_schema(),
        },
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError("Gemini advisor request failed") from exc
    text = _gemini_text(body)
    return parse_advisor_response(text)


def _candidate_from_advisor_item(
    raw_candidate: Any,
    *,
    index: int,
    evolution_run_id: str,
    dataset_snapshot: str,
    budget: EvolutionBudget,
    model_version_prefix: str,
) -> tuple[CandidateConfig | None, AdvisorCandidateValidation]:
    if not isinstance(raw_candidate, Mapping):
        return None, AdvisorCandidateValidation(False, ("candidate_not_object",))
    architecture = raw_candidate.get("architecture")
    hyperparameters = raw_candidate.get("hyperparameters")
    if not isinstance(architecture, Mapping) or not isinstance(
        hyperparameters, Mapping
    ):
        return None, AdvisorCandidateValidation(
            False, ("architecture_or_hyperparameters_not_object",)
        )
    reasons = _validate_architecture(architecture, budget) + _validate_hyperparameters(
        hyperparameters
    )
    if reasons:
        return None, AdvisorCandidateValidation(False, tuple(reasons))
    normalized_architecture = {
        "type": str(architecture["type"]),
        "hidden_units": [int(item) for item in architecture["hidden_units"]],
        "batch_norm": bool(architecture.get("batch_norm", False)),
    }
    normalized_hyperparameters = {
        "dropout_rate": float(hyperparameters["dropout_rate"]),
        "learning_rate": float(hyperparameters["learning_rate"]),
        "batch_size": int(hyperparameters["batch_size"]),
        "epochs": int(hyperparameters["epochs"]),
        "random_seed": int(
            hyperparameters.get("random_seed", budget.random_seed + index)
        ),
        "early_stopping": True,
        "early_stopping_patience": int(
            hyperparameters.get("early_stopping_patience", 8)
        ),
        "class_weight": str(hyperparameters.get("class_weight", "balanced")),
    }
    dedupe_hash = candidate_hash(normalized_architecture, normalized_hyperparameters)
    candidate = _candidate_from_parts(
        evolution_run_id=evolution_run_id,
        dataset_snapshot=dataset_snapshot,
        model_version=f"{model_version_prefix}_{index:02d}",
        candidate_source="gemini",
        architecture=normalized_architecture,
        hyperparameters=normalized_hyperparameters,
        dedupe_hash=dedupe_hash,
        notes="Fase 3 advisor Gemini; candidato validado por schema local",
    )
    return candidate, AdvisorCandidateValidation(True)


def _validate_architecture(
    architecture: Mapping[str, Any], budget: EvolutionBudget
) -> list[str]:
    reasons: list[str] = []
    if architecture.get("type") not in ALLOWED_ARCHITECTURE_TYPES:
        reasons.append("architecture_type_not_allowed")
    hidden_units = architecture.get("hidden_units")
    if not isinstance(hidden_units, list) or not hidden_units:
        reasons.append("hidden_units_invalid")
        return reasons
    if len(hidden_units) > budget.max_layers:
        reasons.append("max_layers_exceeded")
    if any(not isinstance(item, int) or item <= 0 for item in hidden_units):
        reasons.append("hidden_units_must_be_positive_ints")
    elif estimate_parameter_count(hidden_units) > budget.max_parameter_count:
        reasons.append("max_parameter_count_exceeded")
    if tuple(hidden_units) not in HIDDEN_UNITS_SPACE:
        reasons.append("hidden_units_outside_search_space")
    return reasons


def _validate_hyperparameters(hyperparameters: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if hyperparameters.get("dropout_rate") not in DROPOUT_SPACE:
        reasons.append("dropout_rate_outside_search_space")
    if hyperparameters.get("learning_rate") not in LEARNING_RATE_SPACE:
        reasons.append("learning_rate_outside_search_space")
    if hyperparameters.get("batch_size") not in BATCH_SIZE_SPACE:
        reasons.append("batch_size_outside_search_space")
    if hyperparameters.get("epochs") not in EPOCHS_SPACE:
        reasons.append("epochs_outside_search_space")
    class_weight = str(hyperparameters.get("class_weight", "balanced"))
    if class_weight not in ALLOWED_CLASS_WEIGHTS:
        reasons.append("class_weight_outside_search_space")
    patience = int(hyperparameters.get("early_stopping_patience", 8))
    if patience <= 0:
        reasons.append("early_stopping_patience_invalid")
    return reasons


def _gemini_text(response_body: Mapping[str, Any]) -> str:
    candidates = response_body.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Gemini response did not include candidates")
    content = candidates[0].get("content")
    if not isinstance(content, Mapping):
        raise ValueError("Gemini response candidate did not include content")
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValueError("Gemini response content did not include parts")
    text = parts[0].get("text")
    if not isinstance(text, str):
        raise ValueError("Gemini response part did not include text")
    return text
