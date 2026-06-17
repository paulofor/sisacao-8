"""Daily self-evaluation job for quantitative systems.

The job materializes an operational verdict from existing BigQuery views. It does
not retrain or promote models by itself; it creates an auditable daily decision
record that can be used by a future controlled promotion workflow.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping

from zoneinfo import ZoneInfo

from google.cloud import bigquery  # type: ignore[import-untyped]

from .observability import StructuredLogger

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))

DATASET_ID = os.environ.get("BQ_INTRADAY_DATASET", "cotacao_intraday")
EVALUATION_TABLE_ID = os.environ.get(
    "BQ_QUANT_EVALUATION_TABLE", "quant_daily_model_evaluation"
)
RANKING_PERFORMANCE_VIEW = os.environ.get(
    "BQ_QUANT_RANKING_PERFORMANCE_VIEW", "vw_quant_phase3_ranking_performance"
)
ROBUSTNESS_VIEW = os.environ.get(
    "BQ_QUANT_ROBUSTNESS_VIEW", "vw_quant_phase5_robustness_dashboard"
)
PAPER_TRADING_VIEW = os.environ.get(
    "BQ_QUANT_PAPER_TRADING_VIEW", "vw_quant_phase6_paper_trading_dashboard"
)
JOB_NAME = os.environ.get("JOB_NAME", "quant_daily_evaluation")
DEFAULT_BQ_LOCATION = "us-east1"
SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")

PROMOTE_THRESHOLD = float(os.environ.get("QUANT_PROMOTE_SCORE_THRESHOLD", "80"))
PAPER_THRESHOLD = float(os.environ.get("QUANT_PAPER_SCORE_THRESHOLD", "65"))
BLOCK_THRESHOLD = float(os.environ.get("QUANT_BLOCK_SCORE_THRESHOLD", "35"))
MIN_RANKING_DAYS = int(os.environ.get("QUANT_MIN_RANKING_DAYS", "60"))


def _normalize_bq_location(
    value: str | None, default: str = DEFAULT_BQ_LOCATION
) -> str:
    raw_value = default if value is None else value
    text = str(raw_value).strip()
    if not text:
        text = default
    lowered = text.lower()
    if lowered.startswith("region-"):
        lowered = lowered.split("region-", 1)[1]
    if lowered == "east1":
        return "us-east1"
    return lowered


BQ_LOCATION = _normalize_bq_location(os.environ.get("BQ_LOCATION"))
_BQ_CLIENT: bigquery.Client | None = None


def _get_client() -> bigquery.Client:
    global _BQ_CLIENT
    if _BQ_CLIENT is None:
        _BQ_CLIENT = bigquery.Client(location=BQ_LOCATION)
    return _BQ_CLIENT


@dataclass(frozen=True)
class EvaluationResult:
    """One persisted daily quantitative readiness decision."""

    reference_date: dt.date
    evaluation_type: str
    subject_id: str
    subject_version: str
    score: float
    decision: str
    status: str
    reasons: List[str]
    metrics: Dict[str, Any]

    def to_bq_row(self, *, evaluated_at: dt.datetime, run_id: str) -> Dict[str, Any]:
        return {
            "reference_date": self.reference_date.isoformat(),
            "evaluated_at": evaluated_at.isoformat(),
            "run_id": run_id,
            "evaluation_type": self.evaluation_type,
            "subject_id": self.subject_id,
            "subject_version": self.subject_version,
            "readiness_score": round(self.score, 4),
            "decision": self.decision,
            "status": self.status,
            "reasons_json": json.dumps(self.reasons, ensure_ascii=False),
            "metrics_json": json.dumps(self.metrics, ensure_ascii=False, default=str),
        }


def _now_sp() -> dt.datetime:
    return dt.datetime.now(tz=SAO_PAULO_TZ)


def _request_payload(request: Any) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    if request is None:
        return data
    if hasattr(request, "args") and request.args:
        for key in request.args:
            value = request.args.get(key)
            if value is not None:
                data.setdefault(key, value)
    if hasattr(request, "get_json"):
        try:
            body = request.get_json(silent=True) or {}
        except Exception:  # noqa: BLE001
            body = {}
        if isinstance(body, dict):
            for key, value in body.items():
                if value is not None:
                    data[key] = value
    return data


def _parse_reference_date(payload: Mapping[str, Any]) -> dt.date:
    raw = (
        payload.get("reference_date") or payload.get("date_ref") or payload.get("date")
    )
    if raw:
        return dt.datetime.strptime(str(raw), "%Y-%m-%d").date()
    local_now = _now_sp()
    if local_now.time() >= dt.time(18, 0):
        return local_now.date()
    return local_now.date() - dt.timedelta(days=1)


def _table_ref(table_id: str) -> str:
    client = _get_client()
    return f"{client.project}.{DATASET_ID}.{table_id}"


def _ensure_evaluation_table() -> None:
    client = _get_client()
    table_id = _table_ref(EVALUATION_TABLE_ID)
    schema = [
        bigquery.SchemaField("reference_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("evaluated_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("evaluation_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("subject_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("subject_version", "STRING"),
        bigquery.SchemaField("readiness_score", "FLOAT"),
        bigquery.SchemaField("decision", "STRING"),
        bigquery.SchemaField("status", "STRING"),
        bigquery.SchemaField("reasons_json", "STRING"),
        bigquery.SchemaField("metrics_json", "STRING"),
    ]
    try:
        client.get_table(table_id)
    except Exception as exc:  # noqa: BLE001
        if exc.__class__.__name__ != "NotFound":
            raise
        table = bigquery.Table(table_id, schema=schema)
        table.time_partitioning = bigquery.TimePartitioning(field="reference_date")
        table.clustering_fields = ["evaluation_type", "subject_id"]
        client.create_table(table)
        logging.warning("Tabela %s criada automaticamente.", table_id)


def _query_rows(query: str) -> List[Dict[str, Any]]:
    rows = _get_client().query(query, location=BQ_LOCATION).result()
    return [dict(row.items()) for row in rows]


def _load_rows(rows: Iterable[Dict[str, Any]]) -> None:
    materialized = list(rows)
    if not materialized:
        return
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND
    )
    job = _get_client().load_table_from_json(
        materialized,
        _table_ref(EVALUATION_TABLE_ID),
        job_config=job_config,
        location=BQ_LOCATION,
    )
    job.result()


def _delete_reference_date(reference_date: dt.date) -> None:
    query = f"""
        DELETE FROM `{_table_ref(EVALUATION_TABLE_ID)}`
        WHERE reference_date = @reference_date
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("reference_date", "DATE", reference_date)
        ]
    )
    _get_client().query(query, job_config=job_config, location=BQ_LOCATION).result()


def _decision_from_score(score: float, blocking_reasons: List[str]) -> str:
    if blocking_reasons or score < BLOCK_THRESHOLD:
        return "blocked"
    if score >= PROMOTE_THRESHOLD:
        return "approved_candidate"
    if score >= PAPER_THRESHOLD:
        return "paper_trading_candidate"
    return "observe"


def evaluate_ranking_row(
    row: Mapping[str, Any], reference_date: dt.date
) -> EvaluationResult:
    """Score one Phase 3 ranking row using monotonicity and excess return."""

    portfolio_days = int(row.get("portfolio_days") or 0)
    positive_rate = float(row.get("positive_day_rate") or 0.0)
    excess = float(row.get("avg_excess_vs_random_5d") or 0.0)
    top_minus_bottom = float(row.get("top_minus_bottom_decile_return_5d") or 0.0)
    correlation = float(row.get("decile_return_correlation") or 0.0)
    status = str(row.get("ranking_status") or "unknown")

    score = 0.0
    reasons: List[str] = []
    blocking: List[str] = []

    if portfolio_days >= MIN_RANKING_DAYS:
        score += 20.0
    else:
        reasons.append("amostra_insuficiente_ranking")
    if positive_rate >= 0.50:
        score += min(25.0, positive_rate * 35.0)
    else:
        reasons.append("taxa_positiva_baixa")
    if excess > 0:
        score += 25.0
    else:
        reasons.append("nao_supera_aleatorio")
    if correlation > 0.25 and top_minus_bottom > 0:
        score += 30.0
    elif correlation <= 0:
        reasons.append("sem_monotonicidade")
        blocking.append("sem_monotonicidade")
    else:
        score += 10.0
        reasons.append("monotonicidade_fraca")

    decision = _decision_from_score(score, blocking)
    if not reasons:
        reasons.append("ranking_aprovado_pelos_criterios_diarios")
    return EvaluationResult(
        reference_date=reference_date,
        evaluation_type="ranking",
        subject_id=str(row.get("ranking_model_id") or "unknown"),
        subject_version=str(row.get("ranking_model_version") or "unknown"),
        score=max(0.0, min(100.0, score)),
        decision=decision,
        status=status,
        reasons=reasons,
        metrics={
            "top_n": row.get("top_n"),
            "portfolio_days": portfolio_days,
            "positive_day_rate": positive_rate,
            "avg_excess_vs_random_5d": excess,
            "decile_return_correlation": correlation,
            "top_minus_bottom_decile_return_5d": top_minus_bottom,
        },
    )


def evaluate_robustness_row(
    row: Mapping[str, Any], reference_date: dt.date
) -> EvaluationResult:
    """Score one Phase 5 robustness row."""

    score = float(row.get("robustness_score") or 0.0)
    alerts_text = str(row.get("overfitting_alerts") or "")
    alerts = [item.strip() for item in alerts_text.split(",") if item.strip()]
    status = str(row.get("oos_status") or "unknown")
    blocking = alerts if score < PAPER_THRESHOLD else []
    decision = _decision_from_score(score, blocking)
    reasons = alerts or ["robustez_aprovada_pelos_criterios_diarios"]
    return EvaluationResult(
        reference_date=reference_date,
        evaluation_type="strategy_robustness",
        subject_id=str(row.get("strategy_id") or "unknown"),
        subject_version=str(row.get("strategy_version") or "unknown"),
        score=max(0.0, min(100.0, score)),
        decision=decision,
        status=status,
        reasons=reasons,
        metrics={
            "strategy_family": row.get("strategy_family"),
            "train_trades": row.get("train_trades"),
            "validation_trades": row.get("validation_trades"),
            "test_trades": row.get("test_trades"),
            "test_expectancy_net_pct": row.get("test_expectancy_net_pct"),
            "walk_forward_windows": row.get("walk_forward_windows"),
            "pct_positive_walk_forward_windows": row.get(
                "pct_positive_walk_forward_windows"
            ),
            "cost_stress_status": row.get("cost_stress_status"),
            "randomization_status": row.get("randomization_status"),
        },
    )


def evaluate_paper_trading_row(
    row: Mapping[str, Any], reference_date: dt.date
) -> EvaluationResult:
    """Score latest Phase 6 paper-trading adherence."""

    adherence = str(row.get("adherence_status") or "sem_operacoes")
    execution_rate = float(row.get("execution_rate") or 0.0)
    pnl = float(row.get("daily_net_pnl_pct") or 0.0)
    divergence = float(row.get("avg_abs_divergence_pct") or 0.0)
    total_orders = int(row.get("total_orders") or 0)
    score = 0.0
    reasons: List[str] = []
    blocking: List[str] = []
    if total_orders > 0:
        score += 20.0
    else:
        reasons.append("sem_operacoes_paper_trading")
    if adherence == "aderente":
        score += 35.0
    else:
        reasons.append(f"aderencia_{adherence}")
        if adherence == "divergencia_alta":
            blocking.append("divergencia_alta")
    score += min(25.0, execution_rate * 25.0)
    if pnl > 0:
        score += 20.0
    else:
        reasons.append("pnl_diario_nao_positivo")
    decision = _decision_from_score(score, blocking)
    return EvaluationResult(
        reference_date=reference_date,
        evaluation_type="paper_trading",
        subject_id="paper_trading_dashboard",
        subject_version="phase6",
        score=max(0.0, min(100.0, score)),
        decision=decision,
        status=adherence,
        reasons=reasons or ["paper_trading_aprovado_pelos_criterios_diarios"],
        metrics={
            "dashboard_reference_date": row.get("reference_date"),
            "total_orders": total_orders,
            "open_orders": row.get("open_orders"),
            "closed_orders": row.get("closed_orders"),
            "daily_net_pnl_pct": pnl,
            "accumulated_net_pnl_pct": row.get("accumulated_net_pnl_pct"),
            "execution_rate": execution_rate,
            "avg_abs_divergence_pct": divergence,
        },
    )


def _fetch_evaluations(reference_date: dt.date) -> List[EvaluationResult]:
    ranking_rows = _query_rows(f"""
        SELECT *
        FROM `{_table_ref(RANKING_PERFORMANCE_VIEW)}`
        ORDER BY ranking_model_id, ranking_model_version, top_n
        """)
    robustness_rows = _query_rows(f"""
        SELECT *
        FROM `{_table_ref(ROBUSTNESS_VIEW)}`
        ORDER BY strategy_id, strategy_version
        """)
    paper_rows = _query_rows(f"""
        SELECT *
        FROM `{_table_ref(PAPER_TRADING_VIEW)}`
        ORDER BY reference_date DESC
        LIMIT 1
        """)

    evaluations: List[EvaluationResult] = []
    evaluations.extend(
        evaluate_ranking_row(row, reference_date) for row in ranking_rows
    )
    evaluations.extend(
        evaluate_robustness_row(row, reference_date) for row in robustness_rows
    )
    evaluations.extend(
        evaluate_paper_trading_row(row, reference_date) for row in paper_rows
    )
    return evaluations


def quant_daily_evaluation(request: Any) -> Dict[str, Any]:
    """HTTP entrypoint for the daily quantitative self-evaluation job."""

    payload = _request_payload(request)
    reference_date = _parse_reference_date(payload)
    run_logger = StructuredLogger(JOB_NAME)
    run_logger.started(
        reference_date=reference_date.isoformat(),
        evaluation_table=_table_ref(EVALUATION_TABLE_ID),
    )
    try:
        _ensure_evaluation_table()
        evaluations = _fetch_evaluations(reference_date)
        evaluated_at = dt.datetime.now(dt.timezone.utc)
        rows = [
            evaluation.to_bq_row(evaluated_at=evaluated_at, run_id=run_logger.run_id)
            for evaluation in evaluations
        ]
        _delete_reference_date(reference_date)
        _load_rows(rows)
        decisions: Dict[str, int] = {}
        for evaluation in evaluations:
            decisions[evaluation.decision] = decisions.get(evaluation.decision, 0) + 1
        run_logger.ok(
            "Avaliação quantitativa diária persistida",
            evaluations=len(evaluations),
            decisions=decisions,
        )
        return {
            "status": "ok",
            "reference_date": reference_date.isoformat(),
            "evaluations": len(evaluations),
            "decisions": decisions,
        }
    except Exception as exc:  # noqa: BLE001
        run_logger.exception(exc, stage="quant_daily_evaluation")
        raise
