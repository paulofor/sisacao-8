from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]
import pytest

from sisacao8.b3 import parse_b3_daily_lines
from sisacao8.intraday import build_intraday_candles
from sisacao8.signals import generate_conditional_signals


def test_parse_b3_daily_lines_extracts_ohlcv() -> None:
    line = "012024050602NTCO3       010GRUPO NATURAON      NM   R$  000000000171600000000017510000000001712000000000173300000000017270000000001725000000000172815390000000000005800800000000010053902100000000000000009999123100000010000000000000BRNTCOACNOR5106"
    candles = parse_b3_daily_lines([line], tickers=["NTCO3"])
    assert len(candles) == 1
    candle = candles[0]
    assert candle.open == pytest.approx(17.16)
    assert candle.high == pytest.approx(17.51)
    assert candle.low == pytest.approx(17.12)
    assert candle.close == pytest.approx(17.27)
    assert candle.volume == pytest.approx(5800800)
    assert candle.metadata["trades"] == 15390


def test_build_intraday_candles_groups_quotes() -> None:
    df = pd.DataFrame(
        {
            "ticker": ["PETR4", "PETR4", "PETR4"],
            "data": ["2024-05-02"] * 3,
            "hora": ["10:00:00", "10:05:00", "10:18:00"],
            "valor": [10.0, 10.5, 11.0],
        }
    )
    candles = build_intraday_candles(df)
    assert len(candles) == 2
    first = candles[0]
    assert first.open == pytest.approx(10.0)
    assert first.close == pytest.approx(10.5)
    second = candles[1]
    assert second.open == pytest.approx(11.0)
    assert second.data_quality_flags == ("NO_VOLUME_SOURCE", "SINGLE_QUOTE_BUCKET")


def test_generate_conditional_signals_limits_top5() -> None:
    rows = []
    for idx in range(6):
        rows.append(
            {
                "ticker": f"TICK{idx}",
                "open": 10 + idx,
                "close": 9 + idx,
                "volume": 1_000_000 - idx * 10,
            }
        )
    df = pd.DataFrame(rows)
    signals = generate_conditional_signals(df)
    assert len(signals) == 5
    assert len({signal.ticker for signal in signals}) == 5


def test_generate_conditional_signals_chooses_sell_for_green_day() -> None:
    df = pd.DataFrame(
        [
            {
                "ticker": "GREEN",
                "open": 10.0,
                "close": 11.0,
                "volume": 1000,
            }
        ]
    )
    signals = generate_conditional_signals(df, top_n=1)
    assert signals[0].side == "SELL"
    assert signals[0].entry > df.iloc[0]["close"]
