"""Cloud Function for governed MUEN neural champion approval."""

from __future__ import annotations

import os
from typing import Any, Dict, Mapping

from google.cloud import bigquery

from sisacao8.neural_champion_approval import (
    APPROVED_STATUS,
    ChampionApprovalRequest,
    audit_approved_champions,
    champion_approval_plan,
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
        return {
            "status": "blocked",
            "mode": mode,
            "reason": "evaluate_candidate_requires_economic_evaluator_integration",
            "next_mode": "approve_if_passed",
        }, 409
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


def _fetch_registry_row(
    client: bigquery.Client, model_version: str
) -> dict[str, Any] | None:
    if not model_version:
        return None
    sql = (
        "SELECT model_id, model_version, status, feature_version, label_version, "
        "training_dataset_snapshot, artifact_uri, notes "
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
