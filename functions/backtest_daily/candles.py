"""Common helpers for manipulating OHLCV candles."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping, MutableSequence, Sequence

from zoneinfo import ZoneInfo

SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")


class Timeframe(str, Enum):
    """Supported candle timeframes."""

    DAILY = "1D"
    MIN15 = "15m"
    H1 = "1h"

    @property
    def minutes(self) -> int:
        """Return the duration for the timeframe in minutes."""

        return {
            Timeframe.DAILY: 24 * 60,
            Timeframe.MIN15: 15,
            Timeframe.H1: 60,
        }[self]


def ensure_timezone(
    value: dt.datetime, timezone: ZoneInfo = SAO_PAULO_TZ
) -> dt.datetime:
    """Return ``value`` localized in the requested timezone."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone)
    return value.astimezone(timezone)


def _normalize_float(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid numeric value: {value}") from exc
    if not (parsed == parsed):  # NaN check
        raise ValueError("Numeric values cannot be NaN")
    return parsed


@dataclass(frozen=True)
class Candle:
    """Normalized representation for OHLCV records."""

    ticker: str
    timestamp: dt.datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    source: str
    timeframe: Timeframe | str
    ingested_at: dt.datetime
    data_quality_flags: Sequence[str] = field(default_factory=tuple)
    metadata: Mapping[str, Any] | None = field(default_factory=dict)

    def __post_init__(self) -> None:
        ticker = self.ticker.strip().upper()
        if not ticker:
            msg = "ticker cannot be blank"
            raise ValueError(msg)
        object.__setattr__(self, "ticker", ticker)

        timestamp = ensure_timezone(self.timestamp)
        object.__setattr__(self, "timestamp", timestamp)

        ingested = ensure_timezone(self.ingested_at)
        object.__setattr__(self, "ingested_at", ingested)

        open_price = _normalize_float(self.open)
        high_price = _normalize_float(self.high)
        low_price = _normalize_float(self.low)
        close_price = _normalize_float(self.close)

        if high_price < max(open_price, close_price, low_price):
            msg = "high price cannot be lower than open/close/low"
            raise ValueError(msg)
        if low_price > min(open_price, close_price, high_price):
            msg = "low price cannot be higher than open/close/high"
            raise ValueError(msg)

        object.__setattr__(self, "open", open_price)
        object.__setattr__(self, "high", high_price)
        object.__setattr__(self, "low", low_price)
        object.__setattr__(self, "close", close_price)

        if self.volume is not None:
            volume = float(self.volume)
            if volume < 0:
                msg = "volume cannot be negative"
                raise ValueError(msg)
            object.__setattr__(self, "volume", volume)

        raw_flags = [flag.strip() for flag in self.data_quality_flags if flag]
        object.__setattr__(self, "data_quality_flags", tuple(sorted(set(raw_flags))))

        if isinstance(self.timeframe, str):
            normalized = self.timeframe.strip() or Timeframe.DAILY.value
            lower = normalized.lower()
            mapping = {
                "d": Timeframe.DAILY,
                "1d": Timeframe.DAILY,
                "15m": Timeframe.MIN15,
                "m15": Timeframe.MIN15,
                "1h": Timeframe.H1,
                "h1": Timeframe.H1,
            }
            timeframe = mapping.get(lower, normalized)
            object.__setattr__(self, "timeframe", timeframe)

    @property
    def reference_date(self) -> dt.date:
        """Return the trading date in São Paulo timezone."""

        local_timestamp = ensure_timezone(self.timestamp)
        return local_timestamp.date()

    @property
    def duration_minutes(self) -> int:
        """Return the duration inferred from :attr:`timeframe`."""

        if isinstance(self.timeframe, Timeframe):
            return self.timeframe.minutes
        lookup = {
            "1d": 24 * 60,
            "d": 24 * 60,
            "15m": 15,
            "m15": 15,
            "60m": 60,
            "1h": 60,
            "h1": 60,
        }
        return lookup.get(str(self.timeframe).lower(), 0)

    def quality_flag_string(self) -> str | None:
        """Return flags joined by comma for persistence."""

        return ",".join(self.data_quality_flags) if self.data_quality_flags else None

    def to_bq_row(self) -> dict[str, Any]:
        """Convert the candle into a dictionary ready for BigQuery."""

        candle_dt = ensure_timezone(self.timestamp, SAO_PAULO_TZ).replace(tzinfo=None)
        ingested_dt = ensure_timezone(self.ingested_at, SAO_PAULO_TZ).replace(
            tzinfo=None
        )
        reference_date = candle_dt.date()
        timeframe = (
            self.timeframe.value
            if isinstance(self.timeframe, Timeframe)
            else str(self.timeframe)
        )
        row = {
            "ticker": self.ticker,
            "candle_datetime": candle_dt,
            "reference_date": reference_date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "source": self.source,
            "timeframe": timeframe,
            "ingested_at": ingested_dt,
            "data_quality_flags": self.quality_flag_string(),
        }
        metadata = dict(self.metadata or {})
        if "trades" in metadata:
            row["trades"] = metadata["trades"]
        if "turnover_brl" in metadata:
            row["volume_financeiro"] = metadata["turnover_brl"]
        if "quantity" in metadata:
            row["qtd_negociada"] = metadata["quantity"]
        if "window_minutes" in metadata:
            row["window_minutes"] = metadata["window_minutes"]
        if "samples" in metadata:
            row["samples"] = metadata["samples"]
        return row


def summarize_flags(candles: Iterable[Candle]) -> Mapping[str, int]:
    """Return a counter with flag occurrences."""

    totals: dict[str, int] = {}
    for candle in candles:
        for flag in candle.data_quality_flags:
            totals[flag] = totals.get(flag, 0) + 1
    return totals


def merge_flags(*flags: Iterable[str | None]) -> Sequence[str]:
    """Merge arbitrary flag iterables removing null/empty entries."""

    merged: MutableSequence[str] = []
    for collection in flags:
        if not collection:
            continue
        for flag in collection:
            if not flag:
                continue
            if flag not in merged:
                merged.append(flag)
    return tuple(merged)
