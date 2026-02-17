"""Intraday aggregation helpers."""

from __future__ import annotations

import datetime as dt
from typing import List, Sequence

import pandas as pd  # type: ignore[import-untyped]

from .candles import Candle, Timeframe, SAO_PAULO_TZ

INTRADAY_SOURCE = "GOOGLE_FINANCE_15M"


def _prepare_timestamp_column(
    frame: pd.DataFrame,
    *,
    date_column: str = "data",
    time_column: str = "hora",
    value_column: str = "valor",
) -> pd.DataFrame:
    required = {date_column, time_column, value_column, "ticker"}
    missing = required - set(frame.columns)
    if missing:
        raise KeyError(f"Missing columns for intraday aggregation: {sorted(missing)}")

    df = frame.copy()
    df[value_column] = pd.to_numeric(df[value_column], errors="coerce")
    df["timestamp"] = pd.to_datetime(
        df[date_column].astype(str) + " " + df[time_column].astype(str),
        errors="coerce",
    )
    df["timestamp"] = df["timestamp"].dt.tz_localize(
        SAO_PAULO_TZ,
        nonexistent="NaT",
        ambiguous="NaT",
    )
    df = df.dropna(subset=["timestamp", value_column, "ticker"])
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df = df[df["ticker"] != ""]
    df.sort_values(["ticker", "timestamp"], inplace=True)
    return df


def build_intraday_candles(
    frame: pd.DataFrame,
    *,
    frequency: str = "15min",
    source: str = INTRADAY_SOURCE,
    ingestion_time: dt.datetime | None = None,
) -> List[Candle]:
    """Aggregate raw intraday quotes into OHLC candles."""

    if frame.empty:
        return []
    ingestion_time = ingestion_time or dt.datetime.now(tz=SAO_PAULO_TZ)
    window_minutes = int(pd.to_timedelta(frequency).total_seconds() // 60)
    df = _prepare_timestamp_column(frame)
    candles: List[Candle] = []
    for ticker, group in df.groupby("ticker"):
        series = group.set_index("timestamp")["valor"]
        resampled = series.resample(frequency).agg(
            open="first",
            high="max",
            low="min",
            close="last",
            samples="count",
        )
        for timestamp, row in resampled.iterrows():
            if any(pd.isna(row[field]) for field in ("open", "high", "low", "close")):
                continue
            flags: List[str] = []
            samples = int(row["samples"])
            if samples == 1:
                flags.append("SINGLE_QUOTE_BUCKET")
            flags.append("NO_VOLUME_SOURCE")
            candle = Candle(
                ticker=ticker,
                timestamp=timestamp.to_pydatetime(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=0.0,
                source=source,
                timeframe=Timeframe.MIN15,
                ingested_at=ingestion_time,
                data_quality_flags=flags,
                metadata={
                    "samples": samples,
                    "window_minutes": window_minutes,
                },
            )
            candles.append(candle)
    return candles


def rollup_candles(
    candles: Sequence[Candle],
    *,
    target_timeframe: Timeframe = Timeframe.H1,
    source: str = INTRADAY_SOURCE,
) -> List[Candle]:
    """Aggregate existing candles into a coarser timeframe."""

    if not candles:
        return []
    records = []
    for candle in candles:
        records.append(
            {
                "ticker": candle.ticker,
                "timestamp": candle.timestamp,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume or 0.0,
            }
        )
    df = pd.DataFrame.from_records(records)
    df.sort_values(["ticker", "timestamp"], inplace=True)
    df.set_index("timestamp", inplace=True)
    freq = {
        Timeframe.H1: "1H",
        Timeframe.DAILY: "1D",
        Timeframe.MIN15: "15min",
    }.get(target_timeframe, "1H")
    aggregated: List[Candle] = []
    for ticker, group in df.groupby("ticker"):
        resampled = group.resample(freq).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        for timestamp, row in resampled.iterrows():
            if any(pd.isna(row[field]) for field in ("open", "high", "low", "close")):
                continue
            candle = Candle(
                ticker=ticker,
                timestamp=timestamp.to_pydatetime(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                source=source,
                timeframe=target_timeframe,
                ingested_at=dt.datetime.now(tz=SAO_PAULO_TZ),
                data_quality_flags=("ROLLED_UP",),
                metadata={"window_minutes": target_timeframe.minutes},
            )
            aggregated.append(candle)
    return aggregated
