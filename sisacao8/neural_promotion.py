"""Controlled promotion helpers for neural EOD models."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Mapping, Sequence

import pandas as pd  # type: ignore[import-untyped]


@dataclass(frozen=True)
class NeuralPromotionCriteria:
    """Minimum evidence required before capital-enabled neural usage."""

    min_oos_profit_factor: float = 1.15
    min_oos_win_rate: float = 0.52
    min_paper_profit_factor: float = 1.10
    min_paper_win_rate: float = 0.50
    min_paper_days: int = 120
    min_paper_trades: int = 50
    max_paper_drawdown_pct: float = 0.12
    min_fill_rate: float = 0.40
    max_backtest_divergence_pct: float = 0.05
    min_approvals: int = 1
    require_explicit_approval: bool = True

    def __post_init__(self) -> None:
        if self.min_paper_days <= 0:
            raise ValueError("min_paper_days must be positive")
        if self.min_paper_trades <= 0:
            raise ValueError("min_paper_trades must be positive")
        if self.min_approvals <= 0:
            raise ValueError("min_approvals must be positive")
        for field_name in (
            "min_oos_win_rate",
            "min_paper_win_rate",
            "max_paper_drawdown_pct",
            "min_fill_rate",
            "max_backtest_divergence_pct",
        ):
            value = float(getattr(self, field_name))
            if not 0 <= value <= 1:
                raise ValueError(f"{field_name} must be between 0 and 1")


@dataclass(frozen=True)
class NeuralPromotionDecision:
    """Promotion gate result for a neural model/version."""

    approved: bool
    status: str
    failed_criteria: tuple[str, ...]
    effective_signal_source: str
    fallback_signal_source: str
    metrics: Mapping[str, float]
    evaluated_at: dt.datetime


@dataclass(frozen=True)
class NeuralShadowCriteria:
    """Minimum evidence before a neural candidate may run in shadow mode."""

    min_test_accuracy: float = 0.38
    min_directional_precision: float = 0.34
    min_coverage: float = 0.20
    min_test_rows: int = 500
    max_train_test_accuracy_gap: float = 0.20
    max_validation_test_precision_gap: float = 0.12
    max_label_drift_pct: float = 0.15

    def __post_init__(self) -> None:
        if self.min_test_rows <= 0:
            raise ValueError("min_test_rows must be positive")
        for field_name in (
            "min_test_accuracy",
            "min_directional_precision",
            "min_coverage",
            "max_train_test_accuracy_gap",
            "max_validation_test_precision_gap",
            "max_label_drift_pct",
        ):
            value = float(getattr(self, field_name))
            if not 0 <= value <= 1:
                raise ValueError(f"{field_name} must be between 0 and 1")


@dataclass(frozen=True)
class NeuralShadowDecision:
    """Gate result before a candidate can run as shadow_candidate."""

    approved: bool
    status: str
    failed_criteria: tuple[str, ...]
    alerts: tuple[str, ...]
    metrics: Mapping[str, float]
    evaluated_at: dt.datetime


def evaluate_neural_shadow_candidate(
    metrics: Mapping[str, object],
    *,
    criteria: NeuralShadowCriteria | None = None,
    evaluated_at: dt.datetime | None = None,
) -> NeuralShadowDecision:
    """Evaluate whether an evolution winner may enter shadow monitoring.

    Passing this gate never enables paper trading or capital. It only marks the
    model as suitable for non-executing shadow observation.
    """

    criteria = criteria or NeuralShadowCriteria()
    normalized = _shadow_metrics(metrics)
    failed: list[str] = []
    if normalized["test_rows"] < criteria.min_test_rows:
        failed.append("test_rows")
    if normalized["test_accuracy"] < criteria.min_test_accuracy:
        failed.append("test_accuracy")
    if normalized["test_directional_precision"] < criteria.min_directional_precision:
        failed.append("test_directional_precision")
    if normalized["test_coverage"] < criteria.min_coverage:
        failed.append("test_coverage")
    if normalized["train_test_accuracy_gap"] > criteria.max_train_test_accuracy_gap:
        failed.append("train_test_accuracy_gap")
    if (
        normalized["validation_test_precision_gap"]
        > criteria.max_validation_test_precision_gap
    ):
        failed.append("validation_test_precision_gap")
    if normalized["label_drift_pct"] > criteria.max_label_drift_pct:
        failed.append("label_drift_pct")

    alerts = build_neural_governance_alerts(normalized, criteria=criteria)
    approved = not failed
    return NeuralShadowDecision(
        approved=approved,
        status="shadow_candidate" if approved else "blocked_for_shadow",
        failed_criteria=tuple(failed),
        alerts=tuple(alerts),
        metrics=normalized,
        evaluated_at=evaluated_at or dt.datetime.now(dt.timezone.utc),
    )


def build_neural_governance_alerts(
    normalized_metrics: Mapping[str, float],
    *,
    criteria: NeuralShadowCriteria | None = None,
) -> tuple[str, ...]:
    """Return alert labels for overfit, coverage drop and label drift."""

    criteria = criteria or NeuralShadowCriteria()
    alerts: list[str] = []
    if normalized_metrics.get("train_test_accuracy_gap", 0.0) > (
        criteria.max_train_test_accuracy_gap * 0.75
    ):
        alerts.append("overfit_watch")
    if normalized_metrics.get("validation_test_coverage_drop", 0.0) > 0.10:
        alerts.append("coverage_drop_watch")
    if normalized_metrics.get("label_drift_pct", 0.0) > (
        criteria.max_label_drift_pct * 0.75
    ):
        alerts.append("label_drift_watch")
    return tuple(alerts)


def build_shadow_gate_audit_record(
    *,
    model_id: str,
    model_version: str,
    decision: NeuralShadowDecision,
    requested_by: str,
    notes: str | None = None,
) -> dict[str, object]:
    """Return a BigQuery-ready row for a shadow gate decision."""

    return {
        "decision_date": decision.evaluated_at.date(),
        "model_id": model_id,
        "model_version": model_version,
        "decision_status": decision.status,
        "failed_criteria": list(decision.failed_criteria),
        "alerts": list(decision.alerts),
        "metrics": dict(decision.metrics),
        "requested_by": requested_by,
        "notes": notes,
        "created_at": decision.evaluated_at,
    }


def _shadow_metrics(metrics: Mapping[str, object]) -> dict[str, float]:
    train = _mapping(metrics.get("train"))
    validation = _mapping(metrics.get("validation"))
    test = _mapping(metrics.get("test"))
    train_accuracy = _float(train.get("accuracy"))
    test_accuracy = _float(test.get("accuracy"))
    validation_precision = _float(validation.get("directional_precision"))
    test_precision = _float(test.get("directional_precision"))
    validation_coverage = _float(validation.get("coverage"))
    test_coverage = _float(test.get("coverage"))
    return {
        "train_accuracy": train_accuracy,
        "validation_accuracy": _float(validation.get("accuracy")),
        "test_accuracy": test_accuracy,
        "test_rows": _float(test.get("rows_count")),
        "test_directional_precision": test_precision,
        "test_coverage": test_coverage,
        "train_test_accuracy_gap": max(train_accuracy - test_accuracy, 0.0),
        "validation_test_precision_gap": abs(validation_precision - test_precision),
        "validation_test_coverage_drop": max(validation_coverage - test_coverage, 0.0),
        "label_drift_pct": _label_drift_pct(metrics),
    }


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _label_drift_pct(metrics: Mapping[str, object]) -> float:
    train_distribution = _mapping(metrics.get("label_distribution_train"))
    test_distribution = _mapping(metrics.get("label_distribution_test"))
    if not train_distribution or not test_distribution:
        return 0.0
    labels = set(train_distribution) | set(test_distribution)
    return max(
        abs(
            _float(train_distribution.get(label)) - _float(test_distribution.get(label))
        )
        for label in labels
    )


def evaluate_neural_promotion(
    metrics: Mapping[str, object],
    *,
    explicit_approvals: Sequence[str] | None = None,
    criteria: NeuralPromotionCriteria | None = None,
    evaluated_at: dt.datetime | None = None,
) -> NeuralPromotionDecision:
    """Evaluate whether a neural model may be promoted in controlled mode.

    The function never promotes directly to a neural-only source. A passing model
    is released to ``hybrid`` with ``heuristic`` fallback so production can be
    rolled back without changing model artifacts.
    """

    criteria = criteria or NeuralPromotionCriteria()
    approvals = tuple(item for item in (explicit_approvals or ()) if str(item).strip())
    normalized = {
        "oos_profit_factor": _float(metrics.get("oos_profit_factor")),
        "oos_win_rate": _float(metrics.get("oos_win_rate")),
        "paper_profit_factor": _float(metrics.get("paper_profit_factor")),
        "paper_win_rate": _float(metrics.get("paper_win_rate")),
        "paper_days": _float(metrics.get("paper_days")),
        "paper_trades": _float(
            metrics.get("paper_trades") or metrics.get("trade_count")
        ),
        "paper_max_drawdown_pct": abs(_float(metrics.get("paper_max_drawdown_pct"))),
        "fill_rate": _float(metrics.get("fill_rate")),
        "avg_abs_backtest_divergence_pct": abs(
            _float(metrics.get("avg_abs_backtest_divergence_pct"))
        ),
        "approval_count": float(len(approvals)),
    }
    failed: list[str] = []
    if normalized["oos_profit_factor"] < criteria.min_oos_profit_factor:
        failed.append("oos_profit_factor")
    if normalized["oos_win_rate"] < criteria.min_oos_win_rate:
        failed.append("oos_win_rate")
    if normalized["paper_profit_factor"] < criteria.min_paper_profit_factor:
        failed.append("paper_profit_factor")
    if normalized["paper_win_rate"] < criteria.min_paper_win_rate:
        failed.append("paper_win_rate")
    if normalized["paper_days"] < criteria.min_paper_days:
        failed.append("paper_days")
    if normalized["paper_trades"] < criteria.min_paper_trades:
        failed.append("paper_trades")
    if normalized["paper_max_drawdown_pct"] > criteria.max_paper_drawdown_pct:
        failed.append("paper_max_drawdown_pct")
    if normalized["fill_rate"] < criteria.min_fill_rate:
        failed.append("fill_rate")
    if (
        normalized["avg_abs_backtest_divergence_pct"]
        > criteria.max_backtest_divergence_pct
    ):
        failed.append("avg_abs_backtest_divergence_pct")
    if criteria.require_explicit_approval and len(approvals) < criteria.min_approvals:
        failed.append("explicit_approval")
    approved = not failed
    return NeuralPromotionDecision(
        approved=approved,
        status=(
            "approved_for_controlled_promotion" if approved else "blocked_for_promotion"
        ),
        failed_criteria=tuple(failed),
        effective_signal_source="hybrid" if approved else "heuristic",
        fallback_signal_source="heuristic",
        metrics=normalized,
        evaluated_at=evaluated_at or dt.datetime.now(dt.timezone.utc),
    )


def build_promotion_audit_record(
    *,
    model_id: str,
    model_version: str,
    decision: NeuralPromotionDecision,
    requested_by: str,
    approval_ticket: str | None = None,
    notes: str | None = None,
) -> dict[str, object]:
    """Return an auditable BigQuery row for a controlled promotion decision."""

    return {
        "promotion_date": decision.evaluated_at.date(),
        "model_id": model_id,
        "model_version": model_version,
        "promotion_status": decision.status,
        "effective_signal_source": decision.effective_signal_source,
        "fallback_signal_source": decision.fallback_signal_source,
        "failed_criteria": list(decision.failed_criteria),
        "metrics": dict(decision.metrics),
        "requested_by": requested_by,
        "approval_ticket": approval_ticket,
        "notes": notes,
        "created_at": decision.evaluated_at,
    }


def latest_controlled_promotion(
    records: Sequence[Mapping[str, object]] | pd.DataFrame,
) -> Mapping[str, object] | None:
    """Return the latest approved controlled promotion from audit records."""

    if isinstance(records, pd.DataFrame):
        df = records.copy()
    else:
        df = pd.DataFrame(list(records))
    if df.empty:
        return None
    required_columns = ("promotion_status", "created_at")
    for required in required_columns:
        if required not in df.columns:
            raise KeyError(f"Missing column '{required}' for promotion audit records")
    df = df[df["promotion_status"].eq("approved_for_controlled_promotion")]
    if df.empty:
        return None
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    return df.sort_values("created_at", ascending=False).iloc[0].to_dict()


def _float(value: object) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
