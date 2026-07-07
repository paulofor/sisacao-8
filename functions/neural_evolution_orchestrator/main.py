"""Cloud Function that orchestrates deterministic neural EOD evolution rounds."""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
from typing import Any, Dict, Iterable, Mapping
from urllib import error, request
from uuid import uuid4

from google.cloud import bigquery

from sisacao8.neural_evolution import (
    CandidateConfig,
    EvaluationScore,
    EvolutionBudget,
    generate_architecture_variant_candidates,
    generate_controlled_diversity_candidates,
    generate_deterministic_candidates,
    generate_phase3_family_candidates,
    mutate_top_candidates,
    penalized_score,
    repeat_finalists_with_fresh_seeds,
    repeat_finalists_with_seeds,
    select_diverse_top_candidates,
)
from sisacao8.neural_muen import (
    FamilyEvaluation,
    FoldEconomicMetrics,
    GateDecision,
    aggregate_family_evaluation,
    family_evaluation_row,
    fold_metrics_row,
    gate_decision_row,
    research_gate_decision,
)

PROJECT_ID = os.environ.get("GCP_PROJECT", "ingestaokraken")
BQ_DATASET = os.environ.get("BQ_INTRADAY_DATASET", "cotacao_intraday")
BQ_LOCATION = os.environ.get("BQ_LOCATION", "us-east1")
EVOLUTION_RUNS_TABLE = os.environ.get(
    "BQ_NEURAL_EVOLUTION_RUNS_TABLE", "neural_evolution_runs"
)
CANDIDATE_CONFIGS_TABLE = os.environ.get(
    "BQ_NEURAL_CANDIDATE_CONFIGS_TABLE", "neural_candidate_configs"
)
CANDIDATE_EVALUATIONS_TABLE = os.environ.get(
    "BQ_NEURAL_CANDIDATE_EVALUATIONS_TABLE", "neural_candidate_evaluations"
)
MODEL_REGISTRY_TABLE = os.environ.get(
    "BQ_NEURAL_MODEL_REGISTRY_TABLE", "neural_model_registry"
)
GATE_DECISIONS_TABLE = os.environ.get(
    "BQ_NEURAL_GATE_DECISIONS_TABLE", "neural_gate_decisions"
)
FOLD_METRICS_TABLE = os.environ.get(
    "BQ_NEURAL_FOLD_METRICS_TABLE", "neural_fold_metrics"
)
FAMILY_EVALUATIONS_TABLE = os.environ.get(
    "BQ_NEURAL_FAMILY_EVALUATIONS_TABLE", "neural_family_evaluations"
)
TRAINING_DATASET_TABLE = os.environ.get(
    "BQ_NEURAL_TRAINING_DATASET_TABLE", "neural_eod_training_dataset"
)
NEURAL_TRAINING_URL = os.environ.get(
    "NEURAL_TRAINING_URL",
    "https://us-east1-ingestaokraken.cloudfunctions.net/neural_training",
)
DEFAULT_MODEL_VERSION_PREFIX = os.environ.get(
    "NEURAL_EVOLUTION_MODEL_VERSION_PREFIX", "neural_eod_mlp_evo1"
)
DEFAULT_STRATEGY = os.environ.get("NEURAL_EVOLUTION_STRATEGY", "deterministic_phase1")
DEFAULT_MAX_TRIALS = int(os.environ.get("NEURAL_EVOLUTION_MAX_TRIALS", "10"))
DEFAULT_TRAINING_TIMEOUT_SECONDS = int(
    os.environ.get("NEURAL_EVOLUTION_TRAINING_TIMEOUT_SECONDS", "3600")
)

_BQ_CLIENT: bigquery.Client | None = None


def _get_bq_client() -> bigquery.Client:
    global _BQ_CLIENT
    if _BQ_CLIENT is None:
        _BQ_CLIENT = bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)
    return _BQ_CLIENT


def neural_evolution_orchestrator(request_obj: Any) -> tuple[Dict[str, Any], int]:
    """HTTP entrypoint for one deterministic neural evolution round."""

    payload = _request_payload(request_obj)
    client = _get_bq_client()
    started_at = _utcnow()
    dry_run = bool(payload.get("dry_run", False))
    train_candidates = bool(payload.get("train_candidates", True)) and not dry_run

    dataset_snapshot = str(
        payload.get("dataset_snapshot") or _latest_dataset_snapshot(client)
    )
    feature_version = str(
        payload.get("feature_version")
        or _snapshot_value(client, dataset_snapshot, "feature_version")
    )
    label_version = str(
        payload.get("label_version")
        or _snapshot_value(client, dataset_snapshot, "label_version")
    )
    evolution_run_id = str(
        payload.get("evolution_run_id")
        or f"neural_evolution_{started_at.strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    )
    strategy = str(payload.get("strategy") or DEFAULT_STRATEGY)
    model_version_prefix = _model_version_prefix(payload, strategy, started_at)
    budget = _budget_from_payload(payload.get("budget"))
    existing_hashes = _existing_hashes(client)

    candidates = _generate_candidates_for_strategy(
        client=client,
        strategy=strategy,
        evolution_run_id=evolution_run_id,
        dataset_snapshot=dataset_snapshot,
        budget=budget,
        existing_hashes=existing_hashes,
        model_version_prefix=model_version_prefix,
        payload=payload,
    )
    if not candidates:
        raise ValueError("No neural evolution candidates were generated")
    for candidate in candidates:
        candidate.training_request.setdefault("feature_version", feature_version)
        candidate.training_request.setdefault("label_version", label_version)

    run_row = {
        "evolution_run_id": evolution_run_id,
        "started_at": started_at.isoformat(),
        "finished_at": None,
        "dataset_snapshot": dataset_snapshot,
        "feature_version": feature_version,
        "label_version": label_version,
        "strategy": strategy,
        "budget_json": _budget_json(budget),
        "status": "dry_run" if dry_run else "running",
        "summary_json": {"candidate_count": len(candidates), "trained_count": 0},
    }
    if not dry_run:
        _append_rows(client, _table_id(EVOLUTION_RUNS_TABLE), [run_row])
        _append_rows(
            client,
            _table_id(CANDIDATE_CONFIGS_TABLE),
            [_candidate_config_row(candidate, started_at) for candidate in candidates],
        )

    if dry_run:
        return {
            "status": "ok",
            "evolution_run_id": evolution_run_id,
            "dataset_snapshot": dataset_snapshot,
            "strategy": strategy,
            "candidate_count": len(candidates),
            "trained_count": 0,
            "evaluated_count": 0,
            "failed_count": 0,
            "dry_run": True,
            "candidates": [candidate.model_version for candidate in candidates],
            "candidate_sources": sorted(
                {candidate.candidate_source for candidate in candidates}
            ),
            "architecture_types": sorted(
                {
                    str(candidate.architecture.get("type", "mlp"))
                    for candidate in candidates
                }
            ),
            "candidate_details": _candidate_response_details(candidates),
            "failures": [],
        }, 200

    training_results: list[dict[str, Any]] = []
    skipped_candidates: list[str] = []
    evaluation_rows: list[dict[str, Any]] = []
    gate_decision_rows: list[dict[str, Any]] = []
    fold_metric_rows: list[dict[str, Any]] = []
    family_evaluation_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for candidate in candidates:
        try:
            if train_candidates:
                training_results.append(_invoke_training(candidate.training_request))
                registry_row = _fetch_registry_row(client, candidate.model_version)
            else:
                skipped_candidates.append(candidate.model_version)
                continue
            metrics = _metrics_from_registry(registry_row)
            score = _score_registry_row(candidate.architecture, registry_row)
            evaluation_rows.append(
                _evaluation_row(
                    candidate_id=candidate.candidate_id,
                    model_version=candidate.model_version,
                    dataset_snapshot=dataset_snapshot,
                    metrics=metrics,
                    score=score,
                )
            )
            muen_rows = _muen_economic_rows_from_metrics(
                dataset_snapshot=dataset_snapshot,
                candidate=candidate,
                metrics=metrics,
                score=score,
            )
            fold_metric_rows.extend(muen_rows["fold_metrics"])
            family_evaluation_rows.extend(muen_rows["family_evaluations"])
            gate_decision_rows.extend(muen_rows["gate_decisions"])
        except (
            Exception
        ) as exc:  # noqa: BLE001 - persist per-candidate failure and continue.
            logging.exception("Candidate %s failed", candidate.model_version)
            failures.append(
                {"model_version": candidate.model_version, "error": str(exc)}
            )

    if evaluation_rows and not dry_run:
        _append_rows(client, _table_id(CANDIDATE_EVALUATIONS_TABLE), evaluation_rows)
    if fold_metric_rows and not dry_run:
        _append_rows(client, _table_id(FOLD_METRICS_TABLE), fold_metric_rows)
    if family_evaluation_rows and not dry_run:
        _append_rows(
            client, _table_id(FAMILY_EVALUATIONS_TABLE), family_evaluation_rows
        )
    if gate_decision_rows and not dry_run:
        _append_rows(client, _table_id(GATE_DECISIONS_TABLE), gate_decision_rows)

    status = "completed" if not failures else "completed_with_errors"
    if len(failures) == len(candidates):
        status = "failed"
    summary = {
        "candidate_count": len(candidates),
        "trained_count": len(training_results),
        "skipped_count": len(skipped_candidates),
        "evaluated_count": len(evaluation_rows),
        "failed_count": len(failures),
        "gate_decision_count": len(gate_decision_rows),
        "fold_metric_count": len(fold_metric_rows),
        "family_evaluation_count": len(family_evaluation_rows),
        "failures": failures,
    }
    if not dry_run:
        _update_run_status(client, evolution_run_id, status, summary)

    return {
        "status": "ok" if status != "failed" else "error",
        "evolution_run_id": evolution_run_id,
        "dataset_snapshot": dataset_snapshot,
        "strategy": strategy,
        "candidate_count": len(candidates),
        "trained_count": len(training_results),
        "skipped_count": len(skipped_candidates),
        "evaluated_count": len(evaluation_rows),
        "failed_count": len(failures),
        "gate_decision_count": len(gate_decision_rows),
        "fold_metric_count": len(fold_metric_rows),
        "family_evaluation_count": len(family_evaluation_rows),
        "dry_run": dry_run,
        "candidates": [candidate.model_version for candidate in candidates],
        "candidate_sources": sorted(
            {candidate.candidate_source for candidate in candidates}
        ),
        "architecture_types": sorted(
            {str(candidate.architecture.get("type", "mlp")) for candidate in candidates}
        ),
        "candidate_details": _candidate_response_details(candidates),
        "failures": failures,
        "skipped_candidates": skipped_candidates,
    }, (200 if status != "failed" else 500)


def _candidate_response_details(
    candidates: Iterable[CandidateConfig],
) -> list[dict[str, Any]]:
    return [
        {
            "model_version": candidate.model_version,
            "model_id": candidate.model_id,
            "candidate_source": candidate.candidate_source,
            "architecture_type": str(candidate.architecture.get("type", "mlp")),
        }
        for candidate in candidates
    ]


def _model_version_prefix(
    payload: Mapping[str, Any], strategy: str, started_at: dt.datetime
) -> str:
    if payload.get("model_version_prefix"):
        return str(payload["model_version_prefix"])
    date_suffix = started_at.strftime("%Y%m%d")
    if _is_phase3_strategy(strategy):
        return f"neural_eod_phase3_{date_suffix}"
    if _is_phase2_strategy(strategy):
        return f"neural_eod_mlp_evo2_{date_suffix}"
    return f"{DEFAULT_MODEL_VERSION_PREFIX}_{date_suffix}"


def _generate_candidates_for_strategy(
    *,
    client: bigquery.Client,
    strategy: str,
    evolution_run_id: str,
    dataset_snapshot: str,
    budget: EvolutionBudget,
    existing_hashes: Iterable[str],
    model_version_prefix: str,
    payload: Mapping[str, Any],
) -> list[CandidateConfig]:
    if _is_phase3_strategy(strategy):
        return _generate_phase3_candidates(
            evolution_run_id=evolution_run_id,
            dataset_snapshot=dataset_snapshot,
            budget=budget,
            existing_hashes=existing_hashes,
            model_version_prefix=model_version_prefix,
            payload=payload,
        )
    if _is_phase2_strategy(strategy):
        return _generate_phase2_candidates(
            client=client,
            evolution_run_id=evolution_run_id,
            dataset_snapshot=dataset_snapshot,
            budget=budget,
            existing_hashes=existing_hashes,
            model_version_prefix=model_version_prefix,
            payload=payload,
        )

    return generate_deterministic_candidates(
        evolution_run_id=evolution_run_id,
        dataset_snapshot=dataset_snapshot,
        budget=budget,
        existing_hashes=existing_hashes,
        model_version_prefix=model_version_prefix,
    )


def _is_phase2_strategy(strategy: str) -> bool:
    return strategy.lower() in {"deterministic_phase2", "phase2", "phase2_mutation"}


def _is_phase3_strategy(strategy: str) -> bool:
    return strategy.lower() in {"phase3_new_families", "phase3", "new_families"}


def _generate_phase3_candidates(
    *,
    evolution_run_id: str,
    dataset_snapshot: str,
    budget: EvolutionBudget,
    existing_hashes: Iterable[str],
    model_version_prefix: str,
    payload: Mapping[str, Any],
) -> list[CandidateConfig]:
    phase3_options = (
        payload.get("phase3") if isinstance(payload.get("phase3"), Mapping) else {}
    )
    family_space = phase3_options.get("family_space")
    kwargs: dict[str, Any] = {}
    if isinstance(family_space, list):
        kwargs["family_space"] = family_space
    return generate_phase3_family_candidates(
        evolution_run_id=evolution_run_id,
        dataset_snapshot=dataset_snapshot,
        budget=budget,
        existing_hashes=existing_hashes,
        model_version_prefix=model_version_prefix,
        **kwargs,
    )


def _generate_phase2_candidates(
    *,
    client: bigquery.Client,
    evolution_run_id: str,
    dataset_snapshot: str,
    budget: EvolutionBudget,
    existing_hashes: Iterable[str],
    model_version_prefix: str,
    payload: Mapping[str, Any],
) -> list[CandidateConfig]:
    phase2_options = (
        payload.get("phase2") if isinstance(payload.get("phase2"), Mapping) else {}
    )
    top_fraction = float(phase2_options.get("top_fraction", 1.0))
    parent_limit = int(phase2_options.get("parent_limit", 10))
    max_parents_per_family = int(phase2_options.get("max_parents_per_family", 1))
    include_seed_repeats = bool(phase2_options.get("include_seed_repeats", True))
    enable_controlled_diversity = bool(phase2_options.get("controlled_diversity", True))
    scored_parents = _phase2_parent_candidates(client, limit=parent_limit)
    top_candidates = select_diverse_top_candidates(
        scored_parents,
        top_fraction=top_fraction,
        max_per_family=max_parents_per_family,
    )
    if not top_candidates:
        raise ValueError("No kept neural candidates available for deterministic_phase2")

    candidates = mutate_top_candidates(
        top_candidates,
        evolution_run_id=evolution_run_id,
        dataset_snapshot=dataset_snapshot,
        budget=budget,
        existing_hashes=existing_hashes,
        model_version_prefix=f"{model_version_prefix}_mutation",
    )
    if include_seed_repeats:
        candidates.extend(
            repeat_finalists_with_seeds(
                top_candidates,
                evolution_run_id=evolution_run_id,
                dataset_snapshot=dataset_snapshot,
                model_version_prefix=f"{model_version_prefix}_seed",
            )
        )
    if not candidates:
        logging.warning(
            "Phase-2 mutation grid exhausted; generating architecture variants "
            "for %s selected parents",
            len(top_candidates),
        )
        candidates = generate_architecture_variant_candidates(
            top_candidates,
            evolution_run_id=evolution_run_id,
            dataset_snapshot=dataset_snapshot,
            budget=budget,
            existing_hashes=existing_hashes,
            model_version_prefix=f"{model_version_prefix}_arch",
        )
    if not candidates and enable_controlled_diversity:
        logging.warning(
            "Phase-2 architecture variants exhausted; generating controlled "
            "diversity candidates for %s selected parents",
            len(top_candidates),
        )
        candidates = generate_controlled_diversity_candidates(
            top_candidates,
            evolution_run_id=evolution_run_id,
            dataset_snapshot=dataset_snapshot,
            budget=budget,
            existing_hashes=existing_hashes,
            model_version_prefix=f"{model_version_prefix}_diversity",
        )
    if not candidates:
        logging.warning(
            "Phase-2 controlled diversity exhausted; generating fresh seed "
            "repeats for %s selected parents",
            len(top_candidates),
        )
        candidates = repeat_finalists_with_fresh_seeds(
            top_candidates,
            evolution_run_id=evolution_run_id,
            dataset_snapshot=dataset_snapshot,
            budget=budget,
            existing_hashes=existing_hashes,
            model_version_prefix=f"{model_version_prefix}_seed_fresh",
        )
    return candidates[: budget.max_trials]


def _phase2_parent_candidates(
    client: bigquery.Client, *, limit: int
) -> list[tuple[CandidateConfig, EvaluationScore]]:
    sql = (
        "SELECT candidate_id, evolution_run_id, model_version, model_id, "
        "candidate_source, architecture_json, hyperparameters_json, "
        "score_total, score_directional_precision, score_coverage, "
        "score_generalization, score_stability, score_cost_penalty, "
        "decision, decision_reasons_json "
        f"FROM `{_table_id('vw_neural_evolution_leaderboard')}` "
        "WHERE decision != 'reject' "
        "ORDER BY score_total DESC, score_directional_precision DESC "
        "LIMIT @limit"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("limit", "INT64", limit)]
    )
    rows = list(client.query(sql, job_config=job_config).result())
    scored: list[tuple[CandidateConfig, EvaluationScore]] = []
    for row in rows:
        data = _row_to_dict(row)
        architecture = _json_mapping(data.get("architecture_json"))
        hyperparameters = _json_mapping(data.get("hyperparameters_json"))
        if not architecture or not hyperparameters:
            continue
        candidate = CandidateConfig(
            candidate_id=str(data["candidate_id"]),
            evolution_run_id=str(data["evolution_run_id"]),
            model_id=str(data.get("model_id") or "neural_eod_mlp"),
            model_version=str(data["model_version"]),
            candidate_source=str(data.get("candidate_source") or "leaderboard"),
            architecture=dict(architecture),
            hyperparameters=dict(hyperparameters),
            training_request={},
            dedupe_hash="",
        )
        score = EvaluationScore(
            score_total=float(data.get("score_total") or 0.0),
            score_directional_precision=float(
                data.get("score_directional_precision") or 0.0
            ),
            score_coverage=float(data.get("score_coverage") or 0.0),
            score_generalization=float(data.get("score_generalization") or 0.0),
            score_stability=float(data.get("score_stability") or 0.0),
            score_cost_penalty=float(data.get("score_cost_penalty") or 0.0),
            decision=str(data.get("decision") or "keep_candidate"),
            decision_reasons=tuple(_json_list(data.get("decision_reasons_json"))),
        )
        scored.append((candidate, score))
    return scored


def _request_payload(request_obj: Any) -> dict[str, Any]:
    if request_obj is None:
        return {}
    body = (
        request_obj.get_json(silent=True) if hasattr(request_obj, "get_json") else None
    )
    if isinstance(body, Mapping):
        return dict(body)
    return {}


def _budget_from_payload(value: Any) -> EvolutionBudget:
    data = value if isinstance(value, Mapping) else {}
    return EvolutionBudget(
        max_trials=int(data.get("max_trials", DEFAULT_MAX_TRIALS)),
        max_runtime_minutes=int(data.get("max_runtime_minutes", 240)),
        max_parameter_count=int(data.get("max_parameter_count", 150_000)),
        max_layers=int(data.get("max_layers", 4)),
        random_seed=int(data.get("random_seed", 20260621)),
    )


def _budget_json(budget: EvolutionBudget) -> dict[str, int]:
    return {
        "max_trials": budget.max_trials,
        "max_runtime_minutes": budget.max_runtime_minutes,
        "max_parameter_count": budget.max_parameter_count,
        "max_layers": budget.max_layers,
        "random_seed": budget.random_seed,
    }


def _latest_dataset_snapshot(client: bigquery.Client) -> str:
    sql = (
        "SELECT dataset_snapshot "
        f"FROM `{_table_id(TRAINING_DATASET_TABLE)}` "
        "WHERE dataset_snapshot IS NOT NULL "
        "GROUP BY dataset_snapshot "
        "HAVING COUNTIF(dataset_split = 'train') > 0 "
        "AND COUNTIF(dataset_split = 'validation') > 0 "
        "AND COUNTIF(dataset_split = 'test') > 0 "
        "ORDER BY MAX(reference_date) DESC, COUNT(*) DESC "
        "LIMIT 1"
    )
    rows = list(client.query(sql).result())
    if not rows:
        raise ValueError("No neural training dataset snapshot found")
    return str(_value(rows[0], "dataset_snapshot"))


def _snapshot_value(client: bigquery.Client, dataset_snapshot: str, column: str) -> str:
    sql = (
        f"SELECT ANY_VALUE({column}) AS value "
        f"FROM `{_table_id(TRAINING_DATASET_TABLE)}` "
        "WHERE dataset_snapshot = @dataset_snapshot "
        f"AND {column} IS NOT NULL"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "dataset_snapshot", "STRING", dataset_snapshot
            )
        ]
    )
    rows = list(client.query(sql, job_config=job_config).result())
    if not rows or _value(rows[0], "value") is None:
        raise ValueError(f"No {column} found for snapshot {dataset_snapshot}")
    return str(_value(rows[0], "value"))


def _existing_hashes(client: bigquery.Client) -> set[str]:
    sql = f"SELECT dedupe_hash FROM `{_table_id(CANDIDATE_CONFIGS_TABLE)}`"
    try:
        return {str(_value(row, "dedupe_hash")) for row in client.query(sql).result()}
    except Exception:  # noqa: BLE001 - table may not exist before DDL is applied.
        logging.warning(
            "Could not read existing neural candidate hashes", exc_info=True
        )
        return set()


def _candidate_config_row(candidate: Any, created_at: dt.datetime) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "evolution_run_id": candidate.evolution_run_id,
        "model_id": candidate.model_id,
        "model_version": candidate.model_version,
        "candidate_source": candidate.candidate_source,
        "architecture_json": candidate.architecture,
        "hyperparameters_json": candidate.hyperparameters,
        "training_request_json": candidate.training_request,
        "schema_validation_status": candidate.schema_validation_status,
        "dedupe_hash": candidate.dedupe_hash,
        "created_at": created_at.isoformat(),
    }


def _invoke_training(payload: Mapping[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        NEURAL_TRAINING_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(
            http_request, timeout=DEFAULT_TRAINING_TIMEOUT_SECONDS
        ) as resp:
            text = resp.read().decode("utf-8")
            return json.loads(text) if text else {"status": "ok"}
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"neural_training HTTP {exc.code}: {detail}") from exc


def _fetch_registry_row(
    client: bigquery.Client, model_version: str
) -> Mapping[str, Any]:
    sql = (
        "SELECT model_id, model_version, status, feature_version, label_version, "
        "training_dataset_snapshot, metrics_json, directional_precision, coverage, "
        "validation_accuracy, test_accuracy, created_at "
        f"FROM `{_table_id(MODEL_REGISTRY_TABLE)}` "
        "WHERE model_version = @model_version "
        "ORDER BY trained_at DESC, created_at DESC LIMIT 1"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("model_version", "STRING", model_version)
        ]
    )
    rows = list(client.query(sql, job_config=job_config).result())
    if not rows:
        raise ValueError(f"No neural_model_registry row found for {model_version}")
    return _row_to_dict(rows[0])


def _score_registry_row(
    architecture: Mapping[str, Any], registry_row: Mapping[str, Any]
):
    metrics = _metrics_from_registry(registry_row)
    hidden_units = tuple(int(item) for item in architecture.get("hidden_units", ()))
    return penalized_score(metrics, hidden_units=hidden_units)


def _metrics_from_registry(registry_row: Mapping[str, Any]) -> Mapping[str, Any]:
    metrics = registry_row.get("metrics_json")
    if isinstance(metrics, str):
        return json.loads(metrics)
    if isinstance(metrics, Mapping):
        return metrics
    return {
        "validation": {
            "accuracy": registry_row.get("validation_accuracy"),
            "directional_precision": registry_row.get("directional_precision"),
        },
        "test": {
            "accuracy": registry_row.get("test_accuracy"),
            "coverage": registry_row.get("coverage"),
            "directional_precision": registry_row.get("directional_precision"),
        },
    }


def _evaluation_row(
    *,
    candidate_id: str,
    model_version: str,
    dataset_snapshot: str,
    metrics: Mapping[str, Any],
    score: Any,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "model_version": model_version,
        "dataset_snapshot": dataset_snapshot,
        "metrics_json": dict(metrics),
        "score_total": score.score_total,
        "score_directional_precision": score.score_directional_precision,
        "score_coverage": score.score_coverage,
        "score_generalization": score.score_generalization,
        "score_stability": score.score_stability,
        "score_cost_penalty": score.score_cost_penalty,
        "decision": score.decision,
        "decision_reasons_json": list(score.decision_reasons),
        "created_at": _utcnow().isoformat(),
    }


def _muen_economic_rows_from_metrics(
    *,
    dataset_snapshot: str,
    candidate: CandidateConfig,
    metrics: Mapping[str, Any],
    score: EvaluationScore,
) -> dict[str, list[dict[str, Any]]]:
    """Build MUEN persistence rows from registry metrics when available."""

    economics = metrics.get("muen_economics")
    if not isinstance(economics, Mapping):
        return {
            "fold_metrics": [],
            "family_evaluations": [],
            "gate_decisions": [
                _research_gate_missing_economics_row(
                    dataset_snapshot=dataset_snapshot,
                    candidate=candidate,
                    score=score,
                )
            ],
        }

    protocol_version = str(
        economics.get("protocol_version") or "neural_eod_protocol_v1"
    )
    family_hash = str(
        economics.get("candidate_family_hash")
        or candidate.dedupe_hash
        or candidate.candidate_id
    )
    seed_count = int(economics.get("seed_count") or 1)
    fold_metrics = [
        _fold_metric_from_mapping(item)
        for item in _json_list(economics.get("fold_metrics"))
    ]
    family = _family_evaluation_from_mapping(economics.get("family_evaluation"))
    if family is None and fold_metrics:
        family = aggregate_family_evaluation(
            family_hash, fold_metrics, seed_count=seed_count
        )
    if family is None:
        return {
            "fold_metrics": [],
            "family_evaluations": [],
            "gate_decisions": [
                _research_gate_missing_economics_row(
                    dataset_snapshot=dataset_snapshot,
                    candidate=candidate,
                    score=score,
                )
            ],
        }

    fold_rows = [
        fold_metrics_row(
            protocol_version=protocol_version,
            dataset_snapshot=dataset_snapshot,
            candidate_family_hash=family_hash,
            trial_id=str(
                getattr(metric, "trial_id", "")
                or _trial_id_for_metric(candidate, metric, index)
            ),
            seed=int(getattr(metric, "seed", economics.get("seed") or 0) or 0),
            metrics=metric,
        )
        for index, metric in enumerate(fold_metrics, start=1)
    ]
    family_row = family_evaluation_row(
        protocol_version=protocol_version,
        dataset_snapshot=dataset_snapshot,
        family=family,
    )
    decision = research_gate_decision(family)
    gate_row = gate_decision_row(
        protocol_version=protocol_version,
        dataset_snapshot=dataset_snapshot,
        candidate_family_hash=family_hash,
        decision=decision,
    )
    return {
        "fold_metrics": fold_rows,
        "family_evaluations": [family_row],
        "gate_decisions": [gate_row],
    }


def _fold_metric_from_mapping(value: Any) -> FoldEconomicMetrics:
    data = _json_mapping(value)
    return FoldEconomicMetrics(
        fold_id=str(data.get("fold_id")),
        trades=int(data.get("trades") or 0),
        coverage=float(data.get("coverage") or 0.0),
        expectancy_net=float(data.get("expectancy_net") or 0.0),
        median_net_return=float(data.get("median_net_return") or 0.0),
        total_net_return=float(data.get("total_net_return") or 0.0),
        profit_factor=float(data.get("profit_factor") or 0.0),
        max_drawdown=float(data.get("max_drawdown") or 0.0),
        positive_trade_ratio=float(data.get("positive_trade_ratio") or 0.0),
        delta_expectancy_vs_champion=float(
            data.get("delta_expectancy_vs_champion") or 0.0
        ),
        cost_multiplier=float(data.get("cost_multiplier") or 1.0),
    )


def _family_evaluation_from_mapping(value: Any) -> FamilyEvaluation | None:
    if not isinstance(value, Mapping):
        return None
    data = _json_mapping(value)
    return FamilyEvaluation(
        candidate_family_hash=str(data.get("candidate_family_hash")),
        folds=int(data.get("folds") or 0),
        seeds=int(data.get("seeds") or 1),
        median_delta_expectancy_vs_champion=float(
            data.get("median_delta_expectancy_vs_champion") or 0.0
        ),
        mean_delta_expectancy_vs_champion=float(
            data.get("mean_delta_expectancy_vs_champion") or 0.0
        ),
        worst_fold_delta_expectancy_vs_champion=float(
            data.get("worst_fold_delta_expectancy_vs_champion") or 0.0
        ),
        positive_folds=int(data.get("positive_folds") or 0),
        positive_fold_ratio=float(data.get("positive_fold_ratio") or 0.0),
        median_expectancy_net=float(data.get("median_expectancy_net") or 0.0),
        max_drawdown=float(data.get("max_drawdown") or 0.0),
        total_trades=int(data.get("total_trades") or 0),
        stable_across_seeds=bool(data.get("stable_across_seeds")),
        cost_multipliers=tuple(
            float(item) for item in _json_list(data.get("cost_multipliers"))
        ),
    )


def _trial_id_for_metric(
    candidate: CandidateConfig, metric: FoldEconomicMetrics, index: int
) -> str:
    cost = str(metric.cost_multiplier).replace(".", "_")
    return f"{candidate.candidate_id}_{metric.fold_id}_{index}_{cost}"


def _research_gate_missing_economics_row(
    *,
    dataset_snapshot: str,
    candidate: CandidateConfig,
    score: EvaluationScore,
) -> dict[str, Any]:
    """Emit an auditable blocked gate when economic fold evidence is absent."""

    decision = GateDecision(
        gate_name="research_walk_forward",
        decision_status="blocked",
        passed=False,
        failed_criteria=("muen_economics_missing",),
        metrics={
            "candidate_id": candidate.candidate_id,
            "model_version": candidate.model_version,
            "score_total": score.score_total,
            "decision": score.decision,
            "reason": "neural_fold_metrics/neural_family_evaluations not persisted yet",
        },
    )
    return gate_decision_row(
        protocol_version="neural_eod_protocol_v1",
        dataset_snapshot=dataset_snapshot,
        candidate_family_hash=candidate.dedupe_hash or candidate.candidate_id,
        decision=decision,
    )


def _append_rows(
    client: bigquery.Client, table_id: str, rows: Iterable[Mapping[str, Any]]
) -> None:
    materialized = [dict(row) for row in rows]
    if not materialized:
        return
    job = client.load_table_from_json(
        materialized,
        table_id,
        job_config=bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND
        ),
    )
    job.result()


def _update_run_status(
    client: bigquery.Client,
    evolution_run_id: str,
    status: str,
    summary: Mapping[str, Any],
) -> None:
    sql = (
        f"UPDATE `{_table_id(EVOLUTION_RUNS_TABLE)}` "
        "SET finished_at = CURRENT_TIMESTAMP(), status = @status, "
        "summary_json = PARSE_JSON(@summary_json) "
        "WHERE evolution_run_id = @evolution_run_id"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("status", "STRING", status),
            bigquery.ScalarQueryParameter(
                "summary_json", "STRING", json.dumps(summary, sort_keys=True)
            ),
            bigquery.ScalarQueryParameter(
                "evolution_run_id", "STRING", evolution_run_id
            ),
        ]
    )
    client.query(sql, job_config=job_config).result()


def _table_id(table: str) -> str:
    if "." in table:
        if table.count(".") == 2:
            return table
        return f"{PROJECT_ID}.{table}"
    return f"{PROJECT_ID}.{BQ_DATASET}.{table}"


def _json_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if isinstance(value, str):
        decoded = json.loads(value)
        return decoded if isinstance(decoded, Mapping) else {}
    return {}


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        decoded = json.loads(value)
        return decoded if isinstance(decoded, list) else []
    return []


def _row_to_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    keys = getattr(row, "keys", lambda: [])()
    return {key: _value(row, key) for key in keys}


def _value(row: Any, key: str) -> Any:
    if isinstance(row, Mapping):
        value = row.get(key)
    else:
        try:
            value = row[key]
        except (KeyError, TypeError):
            value = row.get(key) if hasattr(row, "get") else None
    if hasattr(value, "is_null") and value.is_null:
        return None
    if hasattr(value, "value"):
        return value.value
    return value


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


__all__ = ["neural_evolution_orchestrator"]
