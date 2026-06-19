"""Paper-trading gate helpers for neural EOD signals."""

from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import dataclass
from typing import Iterable, Mapping

import pandas as pd  # type: ignore[import-untyped]


@dataclass(frozen=True)
class NeuralPaperTradingCriteria:
    """Minimum backtest evidence required before neural paper trading."""

    min_profit_factor: float = 1.10
    min_win_rate: float = 0.50
    min_fill_rate: float = 0.40
    max_drawdown_pct: float = 0.15
    min_trades: int = 30
    min_avg_return_pct: float = 0.0
    max_cost_sensitivity_pct: float = 0.25

    def __post_init__(self) -> None:
        if self.min_trades <= 0:
            raise ValueError("min_trades must be positive")
        if self.min_profit_factor <= 0:
            raise ValueError("min_profit_factor must be positive")
        for field_name in ("min_win_rate", "min_fill_rate", "max_drawdown_pct"):
            value = float(getattr(self, field_name))
            if not 0 <= value <= 1:
                raise ValueError(f"{field_name} must be between 0 and 1")


@dataclass(frozen=True)
class NeuralPaperTradingDecision:
    """Gate result for a neural model/version before paper trading."""

    approved: bool
    status: str
    failed_criteria: tuple[str, ...]
    metrics: Mapping[str, float]


def evaluate_neural_backtest_for_paper(
    metrics: Mapping[str, object],
    criteria: NeuralPaperTradingCriteria | None = None,
) -> NeuralPaperTradingDecision:
    """Return whether a neural backtest passes the paper-trading gate."""

    criteria = criteria or NeuralPaperTradingCriteria()
    normalized = {
        "profit_factor": _float(metrics.get("profit_factor")),
        "win_rate": _float(metrics.get("win_rate")),
        "fill_rate": _float(metrics.get("fill_rate")),
        "max_drawdown_pct": abs(_float(metrics.get("max_drawdown_pct"))),
        "trade_count": _float(metrics.get("trade_count") or metrics.get("trades")),
        "avg_return_pct": _float(metrics.get("avg_return_pct")),
        "cost_sensitivity_pct": abs(_float(metrics.get("cost_sensitivity_pct"))),
    }
    failed: list[str] = []
    if normalized["profit_factor"] < criteria.min_profit_factor:
        failed.append("profit_factor")
    if normalized["win_rate"] < criteria.min_win_rate:
        failed.append("win_rate")
    if normalized["fill_rate"] < criteria.min_fill_rate:
        failed.append("fill_rate")
    if normalized["max_drawdown_pct"] > criteria.max_drawdown_pct:
        failed.append("max_drawdown_pct")
    if normalized["trade_count"] < criteria.min_trades:
        failed.append("trade_count")
    if normalized["avg_return_pct"] <= criteria.min_avg_return_pct:
        failed.append("avg_return_pct")
    if normalized["cost_sensitivity_pct"] > criteria.max_cost_sensitivity_pct:
        failed.append("cost_sensitivity_pct")
    approved = not failed
    return NeuralPaperTradingDecision(
        approved=approved,
        status="approved_for_paper" if approved else "blocked_for_paper",
        failed_criteria=tuple(failed),
        metrics=normalized,
    )


def build_neural_paper_orders(
    signals: Iterable[Mapping[str, object]] | pd.DataFrame,
    *,
    run_id: str,
    quantity: int = 100,
    cost_pct: float = 0.0005,
    slippage_pct: float = 0.001,
    max_orders: int = 5,
    created_at: dt.datetime | None = None,
) -> list[dict[str, object]]:
    """Create conservative simulated orders from neural EOD signals."""

    if quantity <= 0:
        raise ValueError("quantity must be positive")
    if max_orders < 0:
        raise ValueError("max_orders must be non-negative")
    if cost_pct < 0 or slippage_pct < 0:
        raise ValueError("cost_pct and slippage_pct must be non-negative")
    if max_orders == 0:
        return []
    if isinstance(signals, pd.DataFrame):
        df = signals.copy()
    else:
        df = pd.DataFrame(list(signals))
    if df.empty:
        return []
    required_columns = (
        "date_ref",
        "valid_for",
        "ticker",
        "side",
        "entry",
        "model_version",
    )
    for required in required_columns:
        if required not in df.columns:
            raise KeyError(f"Missing column '{required}' for neural paper trading")
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["side"] = df["side"].astype(str).str.upper().str.strip()
    df["entry"] = pd.to_numeric(df["entry"], errors="coerce")
    if "rank" in df.columns:
        df["rank"] = pd.to_numeric(df["rank"], errors="coerce").fillna(999999)
    else:
        df["rank"] = range(1, len(df) + 1)
    if "score" in df.columns:
        df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0)
    else:
        df["score"] = 0.0
    df = df[df["ticker"].ne("") & df["side"].isin(["BUY", "SELL"])]
    df = df.dropna(subset=["entry"])
    df = df.sort_values(["rank", "score", "ticker"], ascending=[True, False, True])
    now = created_at or dt.datetime.now(dt.timezone.utc)
    rows: list[dict[str, object]] = []
    for record in df.head(max_orders).to_dict("records"):
        entry = float(record["entry"])
        slippage_multiplier = (
            1 + slippage_pct if record["side"] == "BUY" else 1 - slippage_pct
        )
        simulated_entry = entry * slippage_multiplier
        order_id = _paper_order_id(record, run_id)
        rows.append(
            {
                "paper_order_id": order_id,
                "signal_id": record.get("signal_id"),
                "strategy_id": "neural_eod",
                "strategy_family": "neural_eod",
                "strategy_version": str(record["model_version"]),
                "config_version": record.get("config_version"),
                "ticker": record["ticker"],
                "side": record["side"],
                "reference_date": _date_value(record["date_ref"]),
                "valid_for": _date_value(record["valid_for"]),
                "expected_entry_price": entry,
                "simulated_entry_price": simulated_entry,
                "quantity": quantity,
                "notional_brl": abs(simulated_entry * quantity),
                "estimated_cost_pct": cost_pct,
                "slippage_pct": slippage_pct,
                "order_status": "aberta",
                "exit_reason": None,
                "opened_at": now,
                "closed_at": None,
                "notes": "paper trading neural sem capital real",
                "created_at": now,
                "updated_at": now,
            }
        )
    return rows


def _paper_order_id(record: Mapping[str, object], run_id: str) -> str:
    payload = "|".join(
        str(record.get(key, ""))
        for key in ("date_ref", "valid_for", "ticker", "side", "model_version", "rank")
    )
    return hashlib.sha256(f"{run_id}|{payload}".encode("utf-8")).hexdigest()[:32]


def _date_value(value: object) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.datetime.strptime(str(value), "%Y-%m-%d").date()


def _float(value: object) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
