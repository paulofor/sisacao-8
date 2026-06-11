"""Signal generation helpers for sprint 3 (EOD baseline)."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from dataclasses import dataclass
from typing import Iterable, Mapping, MutableMapping, Sequence

import pandas as pd  # type: ignore[import-untyped]

MODEL_VERSION = "signals_v1"
MAX_SIGNALS_PER_DAY = 5
DEFAULT_RANKING_KEY = "score_v1"
DEFAULT_HORIZON_DAYS = 10


@dataclass(frozen=True)
class ConditionalSignal:
    """Representation of a conditional entry generated at EOD."""

    ticker: str
    side: str
    entry: float
    target: float
    stop: float
    rank: int
    x_rule: str
    y_target_pct: float
    y_stop_pct: float
    volume: float
    close: float
    score: float
    ranking_key: str
    horizon_days: int

    def to_dict(
        self,
        *,
        reference_date: dt.date,
        valid_for: dt.date,
        created_at: dt.datetime,
        model_version: str = MODEL_VERSION,
        source_snapshot: str | None = None,
        code_version: str | None = None,
    ) -> Mapping[str, object]:
        return {
            "date_ref": reference_date.isoformat(),
            "valid_for": valid_for.isoformat(),
            "ticker": self.ticker,
            "side": self.side,
            "entry": round(self.entry, 4),
            "target": round(self.target, 4),
            "stop": round(self.stop, 4),
            "rank": self.rank,
            "x_rule": self.x_rule,
            "y_target_pct": round(self.y_target_pct, 6),
            "y_stop_pct": round(self.y_stop_pct, 6),
            "model_version": model_version,
            "created_at": created_at.isoformat(timespec="seconds"),
            "source_snapshot": source_snapshot,
            "code_version": code_version,
            "volume": self.volume,
            "close": self.close,
            "score": round(self.score, 6),
            "ranking_key": self.ranking_key,
            "horizon_days": self.horizon_days,
        }

    def to_bq_row(
        self,
        *,
        reference_date: dt.date,
        valid_for: dt.date,
        created_at: dt.datetime,
        model_version: str = MODEL_VERSION,
        source_snapshot: str | None = None,
        code_version: str | None = None,
    ) -> Mapping[str, object]:
        return {
            "date_ref": reference_date,
            "valid_for": valid_for,
            "ticker": self.ticker,
            "side": self.side,
            "entry": self.entry,
            "target": self.target,
            "stop": self.stop,
            "rank": self.rank,
            "x_rule": self.x_rule,
            "y_target_pct": self.y_target_pct,
            "y_stop_pct": self.y_stop_pct,
            "model_version": model_version,
            "created_at": created_at,
            "source_snapshot": source_snapshot,
            "code_version": code_version,
            "volume": self.volume,
            "close": self.close,
            "score": self.score,
            "ranking_key": self.ranking_key,
            "horizon_days": self.horizon_days,
        }


def compute_source_snapshot(rows: Sequence[Mapping[str, object]]) -> str:
    """Return a deterministic hash describing the dataset used in the model."""

    def _liquidity(row: Mapping[str, object]) -> float:
        for key in ("volume_financeiro", "volume", "qtd_negociada"):
            value = row.get(key)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
        return 0.0

    serializable = [
        {
            "ticker": row.get("ticker"),
            "close": float(row.get("close", 0) or 0),
            "liquidity": _liquidity(row),
        }
        for row in rows
    ]
    payload = json.dumps(
        sorted(serializable, key=lambda item: item["ticker"]), separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _preferred_side(close_price: float, open_price: float | None) -> str:
    if open_price is None:
        return "BUY"
    return "SELL" if close_price > open_price else "BUY"


def _prepare_metrics_lookup(
    metrics: Iterable[Mapping[str, object]] | pd.DataFrame | None,
) -> MutableMapping[tuple[str, str], Mapping[str, float]]:
    lookup: MutableMapping[tuple[str, str], Mapping[str, float]] = {}
    if metrics is None:
        return lookup
    if isinstance(metrics, pd.DataFrame):
        source = metrics.to_dict("records")
    else:
        source = list(metrics)
    for row in source:
        ticker = str(row.get("ticker", "")).strip().upper()
        side = str(row.get("side", "")).strip().upper()
        if not ticker or side not in {"BUY", "SELL"}:
            continue
        win_rate = float(row.get("win_rate") or 0.0)
        profit_factor = float(row.get("profit_factor") or 0.0)
        lookup[(ticker, side)] = {
            "win_rate": max(0.0, min(1.0, win_rate)),
            "profit_factor": max(0.0, profit_factor),
        }
    return lookup


def _normalize_liquidity(value: float) -> float:
    if value <= 0:
        return 0.0
    log_value = math.log10(value)
    min_log = 4.0
    max_log = 10.0
    normalized = (log_value - min_log) / (max_log - min_log)
    return max(0.0, min(1.0, normalized))


def _volatility_penalty(high: float, low: float, close: float) -> float:
    if close <= 0:
        return 0.0
    range_pct = max(high - low, 0.0) / close
    return min(range_pct / 0.12, 1.0) * 0.1


def _compute_candidate_score(
    ticker: str,
    side: str,
    row: Mapping[str, float],
    metrics_lookup: Mapping[tuple[str, str], Mapping[str, float]],
) -> float:
    liquidity = float(
        row.get("volume_financeiro")
        or row.get("volume")
        or row.get("qtd_negociada")
        or 0.0
    )
    liquidity_score = _normalize_liquidity(liquidity)
    stats = metrics_lookup.get((ticker, side))
    if stats:
        backtest_score = 0.7 * stats.get("win_rate", 0.0) + 0.3 * min(
            1.0, stats.get("profit_factor", 0.0) / 3.0
        )
    else:
        backtest_score = 0.5
    high = float(row.get("high") or row.get("close") or 0.0)
    low = float(row.get("low") or row.get("close") or 0.0)
    close_price = float(row.get("close") or 0.0)
    penalty = _volatility_penalty(high, low, close_price)
    raw_score = 0.6 * backtest_score + 0.4 * liquidity_score
    return max(0.0, min(1.0, raw_score - penalty))


def _build_candidate(
    ticker: str,
    side: str,
    close_price: float,
    *,
    x_pct: float,
    target_pct: float,
    stop_pct: float,
    preferred_side: str,
    score: float,
    volume: float,
    ranking_key: str,
    horizon_days: int,
) -> Mapping[str, object]:
    if side == "BUY":
        multiplier = 1 - x_pct
        entry = close_price * multiplier
        target = entry * (1 + target_pct)
        stop = entry * (1 - stop_pct)
    else:
        multiplier = 1 + x_pct
        entry = close_price * multiplier
        target = entry * (1 - target_pct)
        stop = entry * (1 + stop_pct)
    x_rule = f"close(D)*{multiplier:.4f}"
    priority = 0 if side == preferred_side else 1
    return {
        "ticker": ticker,
        "side": side,
        "entry": entry,
        "target": target,
        "stop": stop,
        "x_rule": x_rule,
        "score": score,
        "priority": priority,
        "volume": volume,
        "close": close_price,
        "y_target_pct": target_pct,
        "y_stop_pct": stop_pct,
        "ranking_key": ranking_key,
        "horizon_days": horizon_days,
    }


def generate_conditional_signals(
    rows: Iterable[Mapping[str, object]] | pd.DataFrame,
    *,
    top_n: int = MAX_SIGNALS_PER_DAY,
    x_pct: float = 0.02,
    target_pct: float = 0.07,
    stop_pct: float = 0.07,
    allow_sell: bool = True,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    ranking_key: str = DEFAULT_RANKING_KEY,
    backtest_metrics: Iterable[Mapping[str, object]] | pd.DataFrame | None = None,
) -> list[ConditionalSignal]:
    """Generate conditional entries limited to ``top_n`` tickers."""

    limit = min(max(0, int(top_n)), MAX_SIGNALS_PER_DAY)
    if limit == 0:
        return []
    if x_pct < 0:
        raise ValueError("x_pct deve ser não negativo")
    if target_pct <= 0 or stop_pct <= 0:
        raise ValueError("target_pct e stop_pct devem ser positivos")
    if horizon_days <= 0:
        raise ValueError("horizon_days deve ser positivo")
    if isinstance(rows, pd.DataFrame):
        df = rows.copy()
    else:
        df = pd.DataFrame(list(rows))
    if df.empty:
        return []
    for required in ("ticker", "close"):
        if required not in df.columns:
            raise KeyError(f"Missing column '{required}' for signal generation")
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df = df[df["ticker"] != ""]
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["open"] = pd.to_numeric(df.get("open", df["close"]), errors="coerce")
    if "volume_financeiro" in df.columns:
        df["volume_financeiro"] = pd.to_numeric(
            df["volume_financeiro"], errors="coerce"
        )
    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    if "qtd_negociada" in df.columns:
        df["qtd_negociada"] = pd.to_numeric(df["qtd_negociada"], errors="coerce")
    df = df.dropna(subset=["close"])

    metrics_lookup = _prepare_metrics_lookup(backtest_metrics)

    candidates: list[Mapping[str, object]] = []
    sides = ("BUY", "SELL") if allow_sell else ("BUY",)
    for _, row in df.iterrows():
        ticker = row["ticker"]
        close_price = float(row["close"])
        open_price = row.get("open")
        preferred = _preferred_side(
            close_price, float(open_price) if pd.notna(open_price) else None
        )
        liquidity_value = float(
            row.get("volume_financeiro")
            or row.get("volume")
            or row.get("qtd_negociada")
            or 0.0
        )
        for side in sides:
            score = _compute_candidate_score(ticker, side, row, metrics_lookup)
            candidates.append(
                _build_candidate(
                    ticker,
                    side,
                    close_price,
                    x_pct=x_pct,
                    target_pct=target_pct,
                    stop_pct=stop_pct,
                    preferred_side=preferred,
                    score=score,
                    volume=liquidity_value,
                    ranking_key=ranking_key,
                    horizon_days=horizon_days,
                )
            )

    candidates.sort(
        key=lambda item: (
            -item["score"],
            item["priority"],
            item["ticker"],
            item["side"],
        )
    )

    selected: list[ConditionalSignal] = []
    used = set()
    for candidate in candidates:
        ticker = candidate["ticker"]
        if ticker in used:
            continue
        signal = ConditionalSignal(
            ticker=ticker,
            side=candidate["side"],
            entry=float(candidate["entry"]),
            target=float(candidate["target"]),
            stop=float(candidate["stop"]),
            rank=len(selected) + 1,
            x_rule=str(candidate["x_rule"]),
            y_target_pct=float(candidate["y_target_pct"]),
            y_stop_pct=float(candidate["y_stop_pct"]),
            volume=float(candidate["volume"]),
            close=float(candidate["close"]),
            score=float(candidate["score"]),
            ranking_key=str(candidate["ranking_key"]),
            horizon_days=int(candidate["horizon_days"]),
        )
        selected.append(signal)
        used.add(ticker)
        if len(selected) >= limit:
            break
    return selected
