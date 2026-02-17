"""Signal generation helpers for Sprint 1."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Sequence

import pandas as pd  # type: ignore[import-untyped]

MODEL_VERSION = "X_rule_v0"


@dataclass(frozen=True)
class ConditionalSignal:
    """Representation of a conditional entry generated at EOD."""

    ticker: str
    side: str
    entry: float
    target: float
    stop: float
    rank: int
    reason: str
    volume: float
    close: float

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
            "reference_date": reference_date.isoformat(),
            "valid_for": valid_for.isoformat(),
            "ticker": self.ticker,
            "side": self.side,
            "entry": round(self.entry, 4),
            "target": round(self.target, 4),
            "stop": round(self.stop, 4),
            "rank": self.rank,
            "reason": self.reason,
            "model_version": model_version,
            "created_at": created_at.isoformat(timespec="seconds"),
            "source_snapshot": source_snapshot,
            "code_version": code_version,
            "volume": self.volume,
            "close": self.close,
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
            "reference_date": reference_date,
            "valid_for": valid_for,
            "ticker": self.ticker,
            "side": self.side,
            "entry": self.entry,
            "target": self.target,
            "stop": self.stop,
            "rank": self.rank,
            "reason": self.reason,
            "model_version": model_version,
            "created_at": created_at,
            "source_snapshot": source_snapshot,
            "code_version": code_version,
            "volume": self.volume,
            "close": self.close,
        }


def _next_business_day(date_value: dt.date) -> dt.date:
    next_day = date_value + dt.timedelta(days=1)
    while next_day.weekday() >= 5:  # Saturday/Sunday
        next_day += dt.timedelta(days=1)
    return next_day


def compute_source_snapshot(rows: Sequence[Mapping[str, object]]) -> str:
    """Return a deterministic hash describing the dataset used in the model."""

    serializable = [
        {
            "ticker": row.get("ticker"),
            "close": float(row.get("close", 0) or 0),
            "volume": float(row.get("volume", 0) or 0),
        }
        for row in rows
    ]
    payload = json.dumps(sorted(serializable, key=lambda item: item["ticker"]), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _preferred_side(close_price: float, open_price: float | None) -> str:
    if open_price is None:
        return "BUY"
    return "SELL" if close_price > open_price else "BUY"


def _build_candidate(
    ticker: str,
    side: str,
    close_price: float,
    *,
    buy_multiplier: float,
    sell_multiplier: float,
    target_gain: float,
    stop_loss: float,
    preferred_side: str,
    score: float,
    volume: float,
) -> Mapping[str, object]:
    if side == "BUY":
        entry = close_price * buy_multiplier
        target = entry * (1 + target_gain)
        stop = entry * (1 - stop_loss)
        reason = "close(D) * 0.98"
    else:
        entry = close_price * sell_multiplier
        target = entry * (1 - target_gain)
        stop = entry * (1 + stop_loss)
        reason = "close(D) * 1.02"
    priority = 0 if side == preferred_side else 1
    return {
        "ticker": ticker,
        "side": side,
        "entry": entry,
        "target": target,
        "stop": stop,
        "reason": reason,
        "score": score,
        "priority": priority,
        "volume": volume,
        "close": close_price,
    }


def generate_conditional_signals(
    rows: Iterable[Mapping[str, object]] | pd.DataFrame,
    *,
    top_n: int = 5,
    buy_multiplier: float = 0.98,
    sell_multiplier: float = 1.02,
    target_gain: float = 0.07,
    stop_loss: float = 0.07,
) -> List[ConditionalSignal]:
    """Generate conditional entries limited to ``top_n`` tickers."""

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
    if "turnover_brl" in df.columns:
        df["score"] = pd.to_numeric(df["turnover_brl"], errors="coerce").fillna(0)
    else:
        df["score"] = pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0)
    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0)
    df = df.dropna(subset=["close"])

    candidates: List[Mapping[str, object]] = []
    for _, row in df.iterrows():
        ticker = row["ticker"]
        close_price = float(row["close"])
        open_price = row.get("open")
        preferred = _preferred_side(close_price, float(open_price) if pd.notna(open_price) else None)
        score = float(row["score"])
        volume = float(row["volume"])
        for side in ("BUY", "SELL"):
            candidates.append(
                _build_candidate(
                    ticker,
                    side,
                    close_price,
                    buy_multiplier=buy_multiplier,
                    sell_multiplier=sell_multiplier,
                    target_gain=target_gain,
                    stop_loss=stop_loss,
                    preferred_side=preferred,
                    score=score,
                    volume=volume,
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

    selected: List[ConditionalSignal] = []
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
            reason=str(candidate["reason"]),
            volume=float(candidate["volume"]),
            close=float(candidate["close"]),
        )
        selected.append(signal)
        used.add(ticker)
        if len(selected) >= top_n:
            break
    return selected
