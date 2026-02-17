"""Parsers for the official B3 COTAHIST files."""

from __future__ import annotations

import datetime as dt
import io
import zipfile
from typing import Iterable, List, Mapping, MutableMapping, Sequence

from .candles import Candle, Timeframe, SAO_PAULO_TZ

PRICE_SCALE = 100.0
TURNOVER_SCALE = 100.0
B3_SOURCE = "B3_DAILY_COTAHIST"


class B3FileError(RuntimeError):
    """Raised when the downloaded file is not valid or cannot be read."""


_SLICE_MAP = {
    "record_type": slice(0, 2),
    "trade_date": slice(2, 10),
    "ticker": slice(12, 24),
    "open": slice(56, 69),
    "high": slice(69, 82),
    "low": slice(82, 95),
    "close": slice(108, 121),
    "trades": slice(147, 152),
    "quantity": slice(152, 170),
    "turnover": slice(170, 188),
}


def _parse_price(segment: str, *, scale: float = PRICE_SCALE) -> float:
    segment = segment.strip() or "0"
    return int(segment) / scale


def _parse_int(segment: str) -> int:
    segment = segment.strip() or "0"
    return int(segment)


def _parse_trade_date(raw: str) -> dt.datetime:
    date_value = dt.datetime.strptime(raw, "%Y%m%d").replace(tzinfo=SAO_PAULO_TZ)
    return date_value


def _quality_flags(high: float, low: float, volume: float, trades: int) -> Sequence[str]:
    flags: List[str] = []
    if volume == 0:
        flags.append("ZERO_VOLUME")
    if trades == 0:
        flags.append("ZERO_TRADES")
    if high == low:
        flags.append("NO_RANGE")
    return flags


def parse_b3_daily_lines(
    lines: Iterable[str],
    *,
    tickers: Sequence[str] | None = None,
    ingestion_time: dt.datetime | None = None,
) -> List[Candle]:
    """Parse raw lines from the COTAHIST file returning :class:`Candle` objects."""

    allowed = {ticker.strip().upper() for ticker in tickers or [] if ticker.strip()}
    normalize_all = not allowed
    ingestion_time = ingestion_time or dt.datetime.now(tz=SAO_PAULO_TZ)
    candles: List[Candle] = []
    for line in lines:
        if not line.startswith("01"):
            continue
        raw_ticker = line[_SLICE_MAP["ticker"]].strip()
        if not raw_ticker:
            continue
        ticker = raw_ticker.upper()
        if not normalize_all and ticker not in allowed:
            continue
        trade_date = _parse_trade_date(line[_SLICE_MAP["trade_date"]])
        try:
            open_price = _parse_price(line[_SLICE_MAP["open"]])
            high_price = _parse_price(line[_SLICE_MAP["high"]])
            low_price = _parse_price(line[_SLICE_MAP["low"]])
            close_price = _parse_price(line[_SLICE_MAP["close"]])
            trades = _parse_int(line[_SLICE_MAP["trades"]])
            quantity = float(_parse_int(line[_SLICE_MAP["quantity"]]))
            turnover = _parse_price(line[_SLICE_MAP["turnover"]], scale=TURNOVER_SCALE)
        except ValueError as exc:  # pragma: no cover - defensive
            raise B3FileError(f"Invalid numeric block for ticker {ticker}") from exc

        flags = _quality_flags(high_price, low_price, quantity, trades)
        candle = Candle(
            ticker=ticker,
            timestamp=trade_date,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=quantity,
            source=B3_SOURCE,
            timeframe=Timeframe.DAILY,
            ingested_at=ingestion_time,
            data_quality_flags=flags,
            metadata={
                "trades": trades,
                "turnover_brl": turnover,
                "quantity": quantity,
            },
        )
        candles.append(candle)
    return candles


def parse_b3_daily_zip(
    payload: bytes,
    *,
    tickers: Sequence[str] | None = None,
    expected_filename: str | None = None,
    diagnostics: MutableMapping[str, str] | None = None,
) -> List[Candle]:
    """Parse the zipped payload returned by B3 COTAHIST endpoint."""

    diagnostics = diagnostics or {}
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            text_files = [name for name in archive.namelist() if name.lower().endswith(".txt")]
            if not text_files:
                raise B3FileError("ZIP file does not contain .txt payload")
            target_name = expected_filename
            if target_name and target_name not in text_files:
                diagnostics["missing_file"] = target_name
            filename = target_name if target_name in text_files else text_files[0]
            decoded_lines = []
            with archive.open(filename) as handle:
                for raw_line in io.TextIOWrapper(handle, encoding="latin1"):
                    decoded_lines.append(raw_line.rstrip("\r\n"))
            candles = parse_b3_daily_lines(decoded_lines, tickers=tickers)
            if not candles:
                diagnostics["empty_dataset"] = filename
            return candles
    except zipfile.BadZipFile as exc:  # pragma: no cover - guarded by tests
        raise B3FileError("Arquivo ZIP inválido retornado pela B3") from exc

    return []


def candles_by_ticker(candles: Sequence[Candle]) -> Mapping[str, Candle]:
    """Return a dictionary indexed by ticker keeping the latest occurrence."""

    mapping: MutableMapping[str, Candle] = {}
    for candle in candles:
        mapping[candle.ticker] = candle
    return dict(mapping)
