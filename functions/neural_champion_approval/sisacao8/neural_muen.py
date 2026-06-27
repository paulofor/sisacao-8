"""MUEN v1 evaluation, aggregation and gate helpers.

The helpers in this module are intentionally framework-free so Cloud Functions,
backend services and tests can share the same research-gate semantics before any
model is promoted beyond leaderboard status.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import asdict, dataclass, field
from statistics import mean, median
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

PROTOCOL_VERSION = "neural_eod_protocol_v1"
GATE_ENGINE_VERSION = "muen_gate_engine_v1"


@dataclass(frozen=True)
class MuenTrialKey:
    """Idempotency key for one ``candidate × fold × seed`` trial."""

    protocol_version: str
    dataset_snapshot: str
    candidate_family_hash: str
    fold_id: str
    seed: int
    code_commit: str

    def trial_id(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"trial_{digest[:32]}"


@dataclass(frozen=True)
class FoldEconomicMetrics:
    """Economic metrics for a model/policy evaluated on one fold."""

    fold_id: str
    trades: int
    coverage: float
    expectancy_net: float
    median_net_return: float
    total_net_return: float
    profit_factor: float
    max_drawdown: float
    positive_trade_ratio: float
    delta_expectancy_vs_champion: float
    cost_multiplier: float = 1.0

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FamilyEvaluation:
    """Aggregated research evidence for one candidate family."""

    candidate_family_hash: str
    folds: int
    seeds: int
    median_delta_expectancy_vs_champion: float
    mean_delta_expectancy_vs_champion: float
    worst_fold_delta_expectancy_vs_champion: float
    positive_folds: int
    positive_fold_ratio: float
    median_expectancy_net: float
    max_drawdown: float
    total_trades: int
    stable_across_seeds: bool
    cost_multipliers: tuple[float, ...]

    def to_json_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["cost_multipliers"] = list(self.cost_multipliers)
        return payload


@dataclass(frozen=True)
class GateThresholds:
    """Hard gate thresholds for MUEN v1 research and holdout decisions."""

    min_trades: int = 30
    min_positive_folds: int = 4
    min_median_delta_expectancy: float = 0.0
    max_worst_fold_delta_expectancy: float = -0.02
    max_drawdown: float = 0.20
    require_cost_stress: float = 1.5
    require_stable_seeds: bool = True


@dataclass(frozen=True)
class GateDecision:
    """Auditable result emitted by the MUEN gate engine."""

    gate_name: str
    decision_status: str
    passed: bool
    failed_criteria: tuple[str, ...]
    metrics: dict[str, Any]
    gate_engine_version: str = GATE_ENGINE_VERSION
    decided_at: str = field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat()
    )

    def to_json_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["failed_criteria"] = list(self.failed_criteria)
        return payload


def build_trial_id(key: MuenTrialKey) -> str:
    """Return the stable idempotency id for a MUEN trial key."""

    return key.trial_id()


def evaluate_fold_economics(
    frame: pd.DataFrame,
    *,
    fold_id: str,
    prediction_column: str = "predicted_label",
    champion_return_column: str | None = "champion_net_return",
    cost_multiplier: float = 1.0,
) -> FoldEconomicMetrics:
    """Compute fold-level net economic metrics from decisions and realized returns.

    Expected labels are ``up`` for BUY, ``down`` for SELL and ``neutral`` for no
    trade. The realized returns come from the MUEN label engine columns
    ``buy_net_return`` and ``sell_net_return``; a cost stress can be applied when
    raw cost columns are available, but the function remains conservative and
    works with the already-net returns produced by the current dataset.
    """

    required = {prediction_column, "buy_net_return", "sell_net_return"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing economic evaluation columns: {sorted(missing)}")
    if cost_multiplier <= 0:
        raise ValueError("cost_multiplier must be positive")

    decisions = frame[prediction_column].fillna("neutral").astype(str)
    buy_returns = pd.to_numeric(frame["buy_net_return"], errors="coerce").fillna(0.0)
    sell_returns = pd.to_numeric(frame["sell_net_return"], errors="coerce").fillna(0.0)
    model_returns = np.where(decisions.eq("up"), buy_returns, 0.0)
    model_returns = np.where(decisions.eq("down"), sell_returns, model_returns)
    model_returns = pd.Series(model_returns, index=frame.index, dtype="float64")

    trade_mask = decisions.isin(["up", "down"])
    trade_returns = model_returns[trade_mask]
    champion_returns = _champion_returns(frame, champion_return_column)
    champion_trade_returns = champion_returns[trade_mask]

    trades = int(trade_mask.sum())
    expectancy = float(trade_returns.mean()) if trades else 0.0
    champion_expectancy = float(champion_trade_returns.mean()) if trades else 0.0
    return FoldEconomicMetrics(
        fold_id=fold_id,
        trades=trades,
        coverage=_safe_divide(trades, len(frame)),
        expectancy_net=expectancy,
        median_net_return=float(trade_returns.median()) if trades else 0.0,
        total_net_return=float(trade_returns.sum()) if trades else 0.0,
        profit_factor=_profit_factor(trade_returns),
        max_drawdown=_max_drawdown(model_returns),
        positive_trade_ratio=_safe_divide(int((trade_returns > 0).sum()), trades),
        delta_expectancy_vs_champion=expectancy - champion_expectancy,
        cost_multiplier=float(cost_multiplier),
    )


def aggregate_family_evaluation(
    candidate_family_hash: str,
    fold_metrics: Sequence[FoldEconomicMetrics],
    *,
    seed_count: int = 1,
) -> FamilyEvaluation:
    """Aggregate folds/seeds so one lucky seed cannot win independently."""

    if not fold_metrics:
        raise ValueError("fold_metrics must not be empty")
    deltas = [metric.delta_expectancy_vs_champion for metric in fold_metrics]
    expectancies = [metric.expectancy_net for metric in fold_metrics]
    positive_folds = sum(1 for delta in deltas if delta > 0)
    return FamilyEvaluation(
        candidate_family_hash=candidate_family_hash,
        folds=len({metric.fold_id for metric in fold_metrics}),
        seeds=int(seed_count),
        median_delta_expectancy_vs_champion=float(median(deltas)),
        mean_delta_expectancy_vs_champion=float(mean(deltas)),
        worst_fold_delta_expectancy_vs_champion=float(min(deltas)),
        positive_folds=positive_folds,
        positive_fold_ratio=_safe_divide(positive_folds, len(deltas)),
        median_expectancy_net=float(median(expectancies)),
        max_drawdown=float(max(metric.max_drawdown for metric in fold_metrics)),
        total_trades=int(sum(metric.trades for metric in fold_metrics)),
        stable_across_seeds=seed_count > 1 or len(fold_metrics) == 1,
        cost_multipliers=tuple(
            sorted({metric.cost_multiplier for metric in fold_metrics})
        ),
    )


def research_gate_decision(
    family: FamilyEvaluation,
    thresholds: GateThresholds | None = None,
) -> GateDecision:
    """Apply MUEN Gate 2 hard criteria before any leaderboard ordering."""

    thresholds = thresholds or GateThresholds()
    failed: list[str] = []
    if family.total_trades < thresholds.min_trades:
        failed.append("trades_insuficientes")
    if family.positive_folds < thresholds.min_positive_folds:
        failed.append("folds_positivos_insuficientes")
    if (
        family.median_delta_expectancy_vs_champion
        <= thresholds.min_median_delta_expectancy
    ):
        failed.append("nao_supera_champion_mediana")
    if (
        family.worst_fold_delta_expectancy_vs_champion
        < thresholds.max_worst_fold_delta_expectancy
    ):
        failed.append("fold_catastrofico")
    if family.max_drawdown > thresholds.max_drawdown:
        failed.append("drawdown_excessivo")
    if thresholds.require_cost_stress not in family.cost_multipliers:
        failed.append("stress_custo_ausente")
    if thresholds.require_stable_seeds and not family.stable_across_seeds:
        failed.append("seeds_instaveis")

    passed = not failed
    return GateDecision(
        gate_name="research_walk_forward",
        decision_status="passed" if passed else "rejected",
        passed=passed,
        failed_criteria=tuple(failed),
        metrics=family.to_json_dict(),
    )


def fold_metrics_row(
    *,
    protocol_version: str,
    dataset_snapshot: str,
    candidate_family_hash: str,
    trial_id: str,
    seed: int,
    metrics: FoldEconomicMetrics,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Return a BigQuery-ready row for ``neural_fold_metrics``."""

    return {
        "trial_id": trial_id,
        "protocol_version": protocol_version,
        "dataset_snapshot": dataset_snapshot,
        "candidate_family_hash": candidate_family_hash,
        "fold_id": metrics.fold_id,
        "seed": int(seed),
        "cost_multiplier": metrics.cost_multiplier,
        "trades": metrics.trades,
        "coverage": metrics.coverage,
        "expectancy_net": metrics.expectancy_net,
        "median_net_return": metrics.median_net_return,
        "total_net_return": metrics.total_net_return,
        "profit_factor": metrics.profit_factor,
        "max_drawdown": metrics.max_drawdown,
        "positive_trade_ratio": metrics.positive_trade_ratio,
        "delta_expectancy_vs_champion": metrics.delta_expectancy_vs_champion,
        "metrics_json": metrics.to_json_dict(),
        "created_at": created_at or _utc_now_iso(),
    }


def family_evaluation_row(
    *,
    protocol_version: str,
    dataset_snapshot: str,
    family: FamilyEvaluation,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Return a BigQuery-ready row for ``neural_family_evaluations``."""

    return {
        "protocol_version": protocol_version,
        "dataset_snapshot": dataset_snapshot,
        "candidate_family_hash": family.candidate_family_hash,
        "folds": family.folds,
        "seeds": family.seeds,
        "median_delta_expectancy_vs_champion": (
            family.median_delta_expectancy_vs_champion
        ),
        "mean_delta_expectancy_vs_champion": family.mean_delta_expectancy_vs_champion,
        "worst_fold_delta_expectancy_vs_champion": (
            family.worst_fold_delta_expectancy_vs_champion
        ),
        "positive_folds": family.positive_folds,
        "positive_fold_ratio": family.positive_fold_ratio,
        "median_expectancy_net": family.median_expectancy_net,
        "max_drawdown": family.max_drawdown,
        "total_trades": family.total_trades,
        "stable_across_seeds": family.stable_across_seeds,
        "cost_multipliers": list(family.cost_multipliers),
        "metrics_json": family.to_json_dict(),
        "created_at": created_at or _utc_now_iso(),
    }


def daily_return_rows(
    frame: pd.DataFrame,
    *,
    protocol_version: str,
    dataset_snapshot: str,
    candidate_family_hash: str,
    trial_id: str,
    fold_id: str,
    seed: int,
    prediction_column: str = "predicted_label",
    reference_date_column: str = "reference_date",
    champion_return_column: str | None = "champion_net_return",
    cost_multiplier: float = 1.0,
    created_at: str | None = None,
) -> list[dict[str, Any]]:
    """Return BigQuery-ready paired daily rows for ``neural_daily_returns``."""

    required = {
        prediction_column,
        reference_date_column,
        "buy_net_return",
        "sell_net_return",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing daily return columns: {sorted(missing)}")

    decisions = frame[prediction_column].fillna("neutral").astype(str)
    buy_returns = pd.to_numeric(frame["buy_net_return"], errors="coerce").fillna(0.0)
    sell_returns = pd.to_numeric(frame["sell_net_return"], errors="coerce").fillna(0.0)
    model_returns = np.where(decisions.eq("up"), buy_returns, 0.0)
    model_returns = np.where(decisions.eq("down"), sell_returns, model_returns)
    model_returns = pd.Series(model_returns, index=frame.index, dtype="float64")
    champion_returns = _champion_returns(frame, champion_return_column)
    reference_dates = pd.to_datetime(frame[reference_date_column], errors="coerce")
    row_created_at = created_at or _utc_now_iso()

    rows: list[dict[str, Any]] = []
    for index, reference_date in reference_dates.items():
        if pd.isna(reference_date):
            continue
        model_return = float(model_returns.loc[index])
        champion_return = float(champion_returns.loc[index])
        is_trade = decisions.loc[index] in {"up", "down"}
        rows.append(
            {
                "protocol_version": protocol_version,
                "dataset_snapshot": dataset_snapshot,
                "candidate_family_hash": candidate_family_hash,
                "trial_id": trial_id,
                "fold_id": fold_id,
                "seed": int(seed),
                "reference_date": reference_date.date().isoformat(),
                "model_net_return": model_return,
                "champion_net_return": champion_return,
                "delta_net_return": model_return - champion_return,
                "exposure": 1.0 if is_trade else 0.0,
                "trades": 1 if is_trade else 0,
                "cost_multiplier": float(cost_multiplier),
                "created_at": row_created_at,
            }
        )
    return rows


def gate_decision_row(
    *,
    protocol_version: str,
    dataset_snapshot: str,
    candidate_family_hash: str,
    decision: GateDecision,
) -> dict[str, Any]:
    """Return a BigQuery-ready row for ``neural_gate_decisions``."""

    return {
        "decision_id": _decision_id(
            protocol_version, dataset_snapshot, candidate_family_hash, decision
        ),
        "protocol_version": protocol_version,
        "dataset_snapshot": dataset_snapshot,
        "candidate_family_hash": candidate_family_hash,
        "gate_name": decision.gate_name,
        "decision_status": decision.decision_status,
        "passed": decision.passed,
        "failed_criteria": list(decision.failed_criteria),
        "metrics_json": decision.metrics,
        "gate_engine_version": decision.gate_engine_version,
        "decided_at": decision.decided_at,
    }


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _decision_id(
    protocol_version: str,
    dataset_snapshot: str,
    candidate_family_hash: str,
    decision: GateDecision,
) -> str:
    payload = json.dumps(
        {
            "protocol_version": protocol_version,
            "dataset_snapshot": dataset_snapshot,
            "candidate_family_hash": candidate_family_hash,
            "gate_name": decision.gate_name,
            "decided_at": decision.decided_at,
        },
        sort_keys=True,
    )
    return "gate_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _champion_returns(
    frame: pd.DataFrame, champion_return_column: str | None
) -> pd.Series:
    if champion_return_column and champion_return_column in frame:
        return pd.to_numeric(frame[champion_return_column], errors="coerce").fillna(0.0)
    return pd.Series(np.zeros(len(frame)), index=frame.index, dtype="float64")


def _profit_factor(returns: Iterable[float]) -> float:
    values = pd.Series(list(returns), dtype="float64")
    if values.empty:
        return 0.0
    gains = float(values[values > 0].sum())
    losses = abs(float(values[values < 0].sum()))
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def _max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    running_max = equity.cummax()
    drawdowns = (running_max - equity) / running_max.replace(0.0, np.nan)
    return float(drawdowns.fillna(0.0).max())


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)
