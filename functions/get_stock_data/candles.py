"""Common helpers for manipulating OHLCV candles.

Local copy used by Cloud Function packaging when source is `functions/get_stock_data`.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

try:  # pragma: no cover - Python >= 3.9 already bundles zoneinfo
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:  # pragma: no cover - fallback for Python 3.8
    from backports.zoneinfo import ZoneInfo  # type: ignore[assignment]

SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")


class Timeframe(str, Enum):
    DAILY = "1D"
    MIN15 = "15m"
    H1 = "1h"


@dataclass(frozen=True)
class Candle:
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

    @property
    def reference_date(self) -> dt.date:
        return self.timestamp.astimezone(SAO_PAULO_TZ).date()

    def quality_flag_string(self) -> str | None:
        return ",".join(self.data_quality_flags) if self.data_quality_flags else None

    def to_bq_row(self) -> dict[str, Any]:
        candle_dt = self.timestamp.astimezone(SAO_PAULO_TZ).replace(tzinfo=None)
        ingested_dt = self.ingested_at.astimezone(SAO_PAULO_TZ).replace(tzinfo=None)
        timeframe = (
            self.timeframe.value
            if isinstance(self.timeframe, Timeframe)
            else str(self.timeframe)
        )
        metadata = self.metadata or {}
        return {
            "ticker": self.ticker,
            "candle_datetime": candle_dt,
            "reference_date": candle_dt.date(),
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": None if self.volume is None else float(self.volume),
            "source": self.source,
            "timeframe": timeframe,
            "ingested_at": ingested_dt,
            "data_quality_flags": self.quality_flag_string(),
            "trades": int(metadata["trades"]) if "trades" in metadata else None,
            "turnover_brl": (
                float(metadata["turnover_brl"])
                if "turnover_brl" in metadata
                else None
            ),
            "quantity": (
                float(metadata["quantity"]) if "quantity" in metadata else None
            ),
            "window_minutes": None,
            "samples": None,
        }
