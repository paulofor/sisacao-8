from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]
import pytest

from sisacao8.b3 import parse_b3_daily_lines
from sisacao8.intraday import build_intraday_candles
from sisacao8.signals import (
    DEFAULT_HORIZON_DAYS,
    DEFAULT_RANKING_KEY,
    generate_conditional_signals,
)


def test_parse_b3_daily_lines_extracts_ohlcv() -> None:
    line = (
        "012024050602NTCO3       010GRUPO NATURAON      NM   R$  "
        "000000000171600000000017510000000001712000000000173300000000017270"
        "000000001725000000000172815390000000000005800800000000010053902100"
        "000000000000009999123100000010000000000000BRNTCOACNOR5106"
    )
    candles = parse_b3_daily_lines([line], tickers=["NTCO3"])
    assert len(candles) == 1
    candle = candles[0]
    assert candle.open == pytest.approx(17.16)
    assert candle.high == pytest.approx(17.51)
    assert candle.low == pytest.approx(17.12)
    assert candle.close == pytest.approx(17.27)
    assert candle.volume == pytest.approx(5_800_800)
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
                "volume_financeiro": 1_000_000 - idx * 10,
            }
        )
    df = pd.DataFrame(rows)
    signals = generate_conditional_signals(df)
    assert len(signals) == 5
    assert len({signal.ticker for signal in signals}) == 5
    for signal in signals:
        assert 0 <= signal.score <= 1
        assert signal.horizon_days == DEFAULT_HORIZON_DAYS
        assert signal.ranking_key == DEFAULT_RANKING_KEY


def test_generate_conditional_signals_chooses_sell_for_green_day() -> None:
    df = pd.DataFrame(
        [
            {
                "ticker": "GREEN",
                "open": 10.0,
                "close": 11.0,
                "volume_financeiro": 1000,
            }
        ]
    )
    signals = generate_conditional_signals(df, top_n=1)
    assert signals[0].side == "SELL"
    assert signals[0].entry > df.iloc[0]["close"]


def test_parse_b3_daily_lines_applies_fatcot() -> None:
    line = (
        "012024050602NTCO3       010GRUPO NATURAON      NM   R$  "
        "000000000171600000000017510000000001712000000000173300000000017270"
        "000000001725000000000172815390000000000005800800000000010053902100"
        "000000000000009999123100000010000000000000BRNTCOACNOR5106"
    )
    line_chars = list(line)
    line_chars[210:217] = list("0000010")
    scaled_line = "".join(line_chars)
    candles = parse_b3_daily_lines([scaled_line], tickers=["NTCO3"])
    assert len(candles) == 1
    candle = candles[0]
    assert candle.open == pytest.approx(1.716)
    assert candle.close == pytest.approx(1.727)
    assert candle.metadata["fator_cotacao"] == 10


def test_generate_conditional_signals_applies_x_and_y_pct() -> None:
    df = pd.DataFrame(
        [
            {
                "ticker": "ALFA3",
                "open": 99.0,
                "close": 100.0,
                "volume_financeiro": 1_000_000,
            }
        ]
    )
    signals = generate_conditional_signals(
        df,
        top_n=1,
        x_pct=0.05,
        target_pct=0.2,
        stop_pct=0.1,
    )
    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == "SELL"  # dia de alta privilegia SELL
    assert signal.entry == pytest.approx(105.0)
    assert signal.target == pytest.approx(84.0)
    assert signal.stop == pytest.approx(115.5)
    assert signal.x_rule == "close(D)*1.0500"
    assert signal.y_target_pct == pytest.approx(0.2)
    assert signal.y_stop_pct == pytest.approx(0.1)


def test_generate_conditional_signals_uses_backtest_metrics_for_score() -> None:
    df = pd.DataFrame(
        [
            {"ticker": "AAA", "open": 10.0, "close": 10.0, "volume_financeiro": 1_000_000},
            {"ticker": "BBB", "open": 10.0, "close": 10.0, "volume_financeiro": 1_000_000},
        ]
    )
    metrics = pd.DataFrame(
        [
            {"ticker": "BBB", "side": "BUY", "win_rate": 0.8, "profit_factor": 2.0},
            {"ticker": "AAA", "side": "BUY", "win_rate": 0.2, "profit_factor": 0.5},
        ]
    )
    signals = generate_conditional_signals(
        df,
        top_n=2,
        allow_sell=False,
        backtest_metrics=metrics,
    )
    assert signals[0].ticker == "BBB"
    assert signals[0].score > signals[1].score
