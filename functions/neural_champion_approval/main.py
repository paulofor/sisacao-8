"""Cloud Function for governed MUEN neural champion approval."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Mapping

from google.cloud import bigquery

from sisacao8.neural_champion_approval import (
    APPROVED_STATUS,
    ChampionApprovalRequest,
    audit_approved_champions,
    champion_approval_plan,
)
from sisacao8.neural_muen import (
    FamilyEvaluation,
    FoldEconomicMetrics,
    aggregate_family_evaluation,
    family_evaluation_row,
    fold_metrics_row,
    gate_decision_row,
    research_gate_decision,
)

PROJECT_ID = os.environ.get("GCP_PROJECT", "ingestaokraken")
BQ_DATASET = os.environ.get("BQ_INTRADAY_DATASET", "cotacao_intraday")
BQ_LOCATION = os.environ.get("BQ_LOCATION", "us-east1")
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
DAILY_RETURNS_TABLE = os.environ.get(
    "BQ_NEURAL_DAILY_RETURNS_TABLE", "neural_daily_returns"
)

_BQ_CLIENT: bigquery.Client | None = None


def _get_bq_client() -> bigquery.Client:
    global _BQ_CLIENT
    if _BQ_CLIENT is None:
        _BQ_CLIENT = bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)
    return _BQ_CLIENT


def neural_champion_approval(request_obj: Any) -> tuple[Dict[str, Any], int]:
    """HTTP entrypoint for champion approval modes.

    Supported modes:
    - ``approve_if_passed``: validate one gate decision and optionally update the
      model registry to ``approved``.
    - ``audit_current_champion``: list approved champions and duplicate warnings.
    """

    payload = _request_payload(request_obj)
    mode = str(payload.get("mode") or "approve_if_passed")
    client = _get_bq_client()

    if mode == "approve_if_passed":
        return _approve_if_passed(client, payload)
    if mode == "audit_current_champion":
        return _audit_current_champion(client, payload)
    if mode == "evaluate_candidate":
        return _evaluate_candidate(client, payload)
    return {"status": "error", "message": f"Unsupported mode: {mode}"}, 400


def _approve_if_passed(
    client: bigquery.Client, payload: Mapping[str, Any]
) -> tuple[Dict[str, Any], int]:
    approval_request = ChampionApprovalRequest(
        model_version=str(payload.get("model_version") or ""),
        decision_id=str(payload.get("decision_id") or ""),
        approved_by=str(payload.get("approved_by") or ""),
        approval_ticket=str(payload.get("approval_ticket") or ""),
        dry_run=bool(payload.get("dry_run", True)),
    )
    registry_row = _fetch_registry_row(client, approval_request.model_version)
    gate_row = _fetch_gate_decision_row(client, approval_request.decision_id)
    plan = champion_approval_plan(
        approval_request,
        registry_row=registry_row,
        gate_decision_row=gate_row,
    )
    if not plan.approved:
        return {"status": "blocked", "plan": plan.to_json_dict()}, 409
    if plan.already_approved:
        return {"status": "ok", "plan": plan.to_json_dict()}, 200
    if approval_request.dry_run:
        return {"status": "ok", "plan": plan.to_json_dict()}, 200

    _update_model_registry_status(client, plan.model_version, plan.approval_note or "")
    return {"status": "ok", "plan": plan.to_json_dict()}, 200


def _audit_current_champion(
    client: bigquery.Client, payload: Mapping[str, Any]
) -> tuple[Dict[str, Any], int]:
    limit = int(payload.get("limit") or 100)
    rows = _fetch_approved_registry_rows(client, limit=limit)
    audit = audit_approved_champions(rows)
    return {"status": "ok", "audit": audit.to_json_dict()}, 200


def _evaluate_candidate(
    client: bigquery.Client, payload: Mapping[str, Any]
) -> tuple[Dict[str, Any], int]:
    """Persist MUEN economics from the registry and emit a research gate decision."""

    model_version = str(payload.get("model_version") or "")
    if not model_version:
        return {
            "status": "blocked",
            "reason": "model_version_obrigatorio",
            "mode": "evaluate_candidate",
        }, 400

    registry_row = _fetch_registry_row(client, model_version)
    if not registry_row:
        return {
            "status": "blocked",
            "reason": "registry_modelo_nao_encontrado",
            "mode": "evaluate_candidate",
            "model_version": model_version,
        }, 404

    economics = _muen_economics_from_registry(registry_row)
    if not economics:
        return {
            "status": "blocked",
            "reason": "muen_economics_missing",
            "mode": "evaluate_candidate",
            "model_version": model_version,
            "next_mode": "evaluate_candidate_after_economic_evaluator",
        }, 409

    protocol_version = str(
        payload.get("protocol_version")
        or economics.get("protocol_version")
        or "neural_eod_protocol_v1"
    )
    dataset_snapshot = str(
        payload.get("dataset_snapshot")
        or economics.get("dataset_snapshot")
        or registry_row.get("training_dataset_snapshot")
        or ""
    )
    family_hash = str(
        payload.get("candidate_family_hash")
        or economics.get("candidate_family_hash")
        or model_version
    )
    seed_count = int(economics.get("seed_count") or 1)
    dry_run = bool(payload.get("dry_run", True))

    fold_metric_items = _json_list(economics.get("fold_metrics"))
    fold_metrics = [_fold_metric_from_mapping(item) for item in fold_metric_items]
    if not fold_metrics:
        return {
            "status": "blocked",
            "reason": "fold_metrics_missing",
            "mode": "evaluate_candidate",
            "model_version": model_version,
        }, 409

    family = _family_evaluation_from_mapping(economics.get("family_evaluation"))
    if family is None:
        family = aggregate_family_evaluation(
            family_hash,
            fold_metrics,
            seed_count=seed_count,
        )
    decision = research_gate_decision(family)
    gate_row = gate_decision_row(
        protocol_version=protocol_version,
        dataset_snapshot=dataset_snapshot,
        candidate_family_hash=family_hash,
        decision=decision,
    )
    fold_rows = [
        fold_metrics_row(
            protocol_version=protocol_version,
            dataset_snapshot=dataset_snapshot,
            candidate_family_hash=family_hash,
            trial_id=str(
                item.get("trial_id")
                or _trial_id_for_metric(model_version, metric, index)
            ),
            seed=int(item.get("seed") or economics.get("seed") or 0),
            metrics=metric,
        )
        for index, (item, metric) in enumerate(
            zip(fold_metric_items, fold_metrics), start=1
        )
    ]
    family_row = family_evaluation_row(
        protocol_version=protocol_version,
        dataset_snapshot=dataset_snapshot,
        family=family,
    )
    daily_rows = _daily_return_rows_from_economics(
        economics=economics,
        protocol_version=protocol_version,
        dataset_snapshot=dataset_snapshot,
        family_hash=family_hash,
    )

    if not dry_run:
        _append_rows(client, _table_id(FOLD_METRICS_TABLE), fold_rows)
        if daily_rows:
            _append_rows(client, _table_id(DAILY_RETURNS_TABLE), daily_rows)
        _append_rows(client, _table_id(FAMILY_EVALUATIONS_TABLE), [family_row])
        _append_rows(client, _table_id(GATE_DECISIONS_TABLE), [gate_row])

    return {
        "status": "ok",
        "mode": "evaluate_candidate",
        "model_version": model_version,
        "dry_run": dry_run,
        "decision_id": gate_row["decision_id"],
        "decision_status": gate_row["decision_status"],
        "passed": gate_row["passed"],
        "failed_criteria": gate_row["failed_criteria"],
        "fold_metric_count": len(fold_rows),
        "daily_return_count": len(daily_rows),
        "family_evaluation_count": 1,
        "gate_decision_count": 1,
        "next_mode": "approve_if_passed" if gate_row["passed"] else None,
    }, 200


def _fetch_registry_row(
    client: bigquery.Client, model_version: str
) -> dict[str, Any] | None:
    if not model_version:
        return None
    sql = (
        "SELECT model_id, model_version, status, feature_version, label_version, "
        "training_dataset_snapshot, artifact_uri, notes, metrics_json "
        f"FROM `{_table_id(MODEL_REGISTRY_TABLE)}` "
        "WHERE model_version = @model_version "
        "ORDER BY created_at DESC LIMIT 1"
    )
    rows = _query_rows(
        client,
        sql,
        [bigquery.ScalarQueryParameter("model_version", "STRING", model_version)],
    )
    return rows[0] if rows else None


def _fetch_gate_decision_row(
    client: bigquery.Client, decision_id: str
) -> dict[str, Any] | None:
    if not decision_id:
        return None
    sql = (
        "SELECT decision_id, protocol_version, dataset_snapshot, "
        "candidate_family_hash, gate_name, decision_status, passed, "
        "failed_criteria, metrics_json, gate_engine_version, decided_at "
        f"FROM `{_table_id(GATE_DECISIONS_TABLE)}` "
        "WHERE decision_id = @decision_id "
        "ORDER BY decided_at DESC LIMIT 1"
    )
    rows = _query_rows(
        client,
        sql,
        [bigquery.ScalarQueryParameter("decision_id", "STRING", decision_id)],
    )
    return rows[0] if rows else None


def _fetch_approved_registry_rows(
    client: bigquery.Client, *, limit: int
) -> list[dict[str, Any]]:
    sql = (
        "SELECT model_id, model_version, status, feature_version, label_version, "
        "training_dataset_snapshot, artifact_uri, notes, trained_at, created_at "
        f"FROM `{_table_id(MODEL_REGISTRY_TABLE)}` "
        "WHERE status = @status "
        "ORDER BY trained_at DESC, created_at DESC LIMIT @limit"
    )
    return _query_rows(
        client,
        sql,
        [
            bigquery.ScalarQueryParameter("status", "STRING", APPROVED_STATUS),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ],
    )


def _update_model_registry_status(
    client: bigquery.Client, model_version: str, approval_note: str
) -> None:
    sql = (
        f"UPDATE `{_table_id(MODEL_REGISTRY_TABLE)}` "
        "SET status = @status, notes = CONCAT(COALESCE(notes, ''), @approval_note) "
        "WHERE model_version = @model_version AND status = 'candidate'"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("status", "STRING", APPROVED_STATUS),
            bigquery.ScalarQueryParameter("approval_note", "STRING", approval_note),
            bigquery.ScalarQueryParameter("model_version", "STRING", model_version),
        ]
    )
    client.query(sql, job_config=job_config).result()


def _query_rows(
    client: bigquery.Client,
    sql: str,
    parameters: list[bigquery.ScalarQueryParameter],
) -> list[dict[str, Any]]:
    job_config = bigquery.QueryJobConfig(query_parameters=parameters)
    return [
        _row_to_dict(row) for row in client.query(sql, job_config=job_config).result()
    ]


def _row_to_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    if hasattr(row, "items"):
        return dict(row.items())
    return dict(row)


def _append_rows(
    client: bigquery.Client, table_id: str, rows: list[Mapping[str, Any]]
) -> None:
    if not rows:
        return
    job = client.load_table_from_json(
        [dict(row) for row in rows],
        table_id,
        job_config=bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND
        ),
    )
    job.result()


def _request_payload(request_obj: Any) -> dict[str, Any]:
    if request_obj is None:
        return {}
    body = (
        request_obj.get_json(silent=True) if hasattr(request_obj, "get_json") else None
    )
    return dict(body) if isinstance(body, Mapping) else {}


def _table_id(table: str) -> str:
    if "." in table:
        return table
    return f"{PROJECT_ID}.{BQ_DATASET}.{table}"


def _muen_economics_from_registry(registry_row: Mapping[str, Any]) -> Mapping[str, Any]:
    metrics = _json_mapping(registry_row.get("metrics_json"))
    economics = metrics.get("muen_economics")
    return economics if isinstance(economics, Mapping) else {}


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


def _daily_return_rows_from_economics(
    *,
    economics: Mapping[str, Any],
    protocol_version: str,
    dataset_snapshot: str,
    family_hash: str,
) -> list[dict[str, Any]]:
    rows = []
    for item in _json_list(economics.get("daily_returns")):
        data = dict(_json_mapping(item))
        if not data:
            continue
        data.setdefault("protocol_version", protocol_version)
        data.setdefault("dataset_snapshot", dataset_snapshot)
        data.setdefault("candidate_family_hash", family_hash)
        rows.append(data)
    return rows


def _trial_id_for_metric(
    model_version: str, metric: FoldEconomicMetrics, index: int
) -> str:
    cost = str(metric.cost_multiplier).replace(".", "_")
    return f"{model_version}_{metric.fold_id}_{index}_{cost}"


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
