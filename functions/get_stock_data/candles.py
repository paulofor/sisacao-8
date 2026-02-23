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
    try:
        from backports.zoneinfo import ZoneInfo  # type: ignore[assignment]
    except ModuleNotFoundError:  # pragma: no cover - defensive fallback

        class ZoneInfo(dt.tzinfo):
            """Fallback timezone implementation for fixed UTC offsets."""

            def __init__(self, key: str) -> None:
                if key != "America/Sao_Paulo":
                    msg = f"Timezone support unavailable for name: {key}"
                    raise ModuleNotFoundError(msg)
                self.key = key
                self._offset = dt.timedelta(hours=-3)

            def utcoffset(self, value: dt.datetime | None) -> dt.timedelta:
                return self._offset

            def dst(self, value: dt.datetime | None) -> dt.timedelta:
                return dt.timedelta(0)

            def tzname(self, value: dt.datetime | None) -> str:
                return self.key

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
        metadata = self.metadata or {}
        turnover = metadata.get("turnover_brl")
        quantity = (
            float(metadata["quantity"])
            if "quantity" in metadata
            else (None if self.volume is None else float(self.volume))
        )
        trades = metadata.get("trades")
        fator_cotacao = metadata.get("fator_cotacao")
        return {
            "ticker": self.ticker,
            "data_pregao": candle_dt.date(),
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume_financeiro": float(turnover) if turnover is not None else None,
            "qtd_negociada": quantity,
            "num_negocios": int(trades) if trades is not None else None,
            "fonte": self.source,
            "atualizado_em": ingested_dt,
            "data_quality_flags": self.quality_flag_string(),
            "fator_cotacao": (
                int(fator_cotacao)
                if isinstance(fator_cotacao, int)
                else fator_cotacao
            ),
        }
