"""Parsers for the official B3 COTAHIST files."""

from __future__ import annotations

import datetime as dt
import io
import zipfile
from typing import Iterable, List, Mapping, MutableMapping, Sequence

if __package__:
    from .candles import Candle, Timeframe, SAO_PAULO_TZ
else:
    from candles import Candle, Timeframe, SAO_PAULO_TZ

PRICE_SCALE = 100.0
TURNOVER_SCALE = 100.0
B3_SOURCE = "B3_DAILY_COTAHIST"


class B3FileError(RuntimeError):
    """Raised when the downloaded file is not valid or cannot be read."""


_SLICE_MAP = {
    "trade_date": slice(2, 10),
    "ticker": slice(12, 24),
    "open": slice(56, 69),
    "high": slice(69, 82),
    "low": slice(82, 95),
    "close": slice(108, 121),
    "trades": slice(147, 152),
    "quantity": slice(152, 170),
    "turnover": slice(170, 188),
    "factor": slice(210, 217),
}


def _parse_price(segment: str, *, scale: float = PRICE_SCALE) -> float:
    return int((segment.strip() or "0")) / scale


def _parse_int(segment: str) -> int:
    return int(segment.strip() or "0")



def _parse_factor(segment: str) -> int:
    value = _parse_int(segment)
    return max(value, 1)


def parse_b3_daily_lines(
    lines: Iterable[str], *, tickers: Sequence[str] | None = None
) -> List[Candle]:
    allowed = {ticker.strip().upper() for ticker in tickers or [] if ticker.strip()}
    normalize_all = not allowed
    ingestion_time = dt.datetime.now(tz=SAO_PAULO_TZ)
    candles: List[Candle] = []
    for line in lines:
        if not line.startswith("01"):
            continue
        ticker = line[_SLICE_MAP["ticker"]].strip().upper()
        if not ticker or (not normalize_all and ticker not in allowed):
            continue
        trade_date = dt.datetime.strptime(
            line[_SLICE_MAP["trade_date"]], "%Y%m%d"
        ).replace(tzinfo=SAO_PAULO_TZ)
        factor = _parse_factor(line[_SLICE_MAP["factor"]])
        open_price = _parse_price(line[_SLICE_MAP["open"]]) / factor
        high_price = _parse_price(line[_SLICE_MAP["high"]]) / factor
        low_price = _parse_price(line[_SLICE_MAP["low"]]) / factor
        close_price = _parse_price(line[_SLICE_MAP["close"]]) / factor
        trades = _parse_int(line[_SLICE_MAP["trades"]])
        quantity = float(_parse_int(line[_SLICE_MAP["quantity"]]))
        turnover = _parse_price(line[_SLICE_MAP["turnover"]], scale=TURNOVER_SCALE)
        flags: List[str] = []
        if quantity == 0:
            flags.append("ZERO_VOLUME")
        if trades == 0:
            flags.append("ZERO_TRADES")
        if high_price == low_price:
            flags.append("NO_RANGE")
        candles.append(
            Candle(
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
                    "fator_cotacao": factor,
                },
            )
        )
    return candles


def parse_b3_daily_zip(
    payload: bytes,
    *,
    tickers: Sequence[str] | None = None,
    expected_filename: str | None = None,
    diagnostics: MutableMapping[str, str] | None = None,
) -> List[Candle]:
    diagnostics = diagnostics or {}
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            text_files = [
                name for name in archive.namelist() if name.lower().endswith(".txt")
            ]
            if not text_files:
                raise B3FileError("ZIP file does not contain .txt payload")
            if expected_filename and expected_filename not in text_files:
                diagnostics["missing_file"] = expected_filename
            filename = (
                expected_filename
                if expected_filename in text_files
                else text_files[0]
            )
            with archive.open(filename) as handle:
                lines = [
                    line.rstrip("\r\n")
                    for line in io.TextIOWrapper(handle, encoding="latin1")
                ]
            candles = parse_b3_daily_lines(lines, tickers=tickers)
            if not candles:
                diagnostics["empty_dataset"] = filename
            return candles
    except zipfile.BadZipFile as exc:
        raise B3FileError("Arquivo ZIP inválido retornado pela B3") from exc


def candles_by_ticker(candles: Sequence[Candle]) -> Mapping[str, Candle]:
    mapping: MutableMapping[str, Candle] = {}
    for candle in candles:
        mapping[candle.ticker] = candle
    return dict(mapping)
