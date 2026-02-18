from __future__ import annotations

import datetime as dt


from sisacao8 import calendar
from sisacao8.backtest import (
    build_candle_lookup,
    build_signal_payloads,
    compute_metrics,
    run_backtest,
)


def _signal(date_ref: str, valid_for: str, side: str = "BUY") -> dict[str, object]:
    return {
        "date_ref": dt.date.fromisoformat(date_ref),
        "valid_for": dt.date.fromisoformat(valid_for),
        "ticker": "TEST3",
        "side": side,
        "entry": 10.0,
        "target": 10.5 if side == "BUY" else 9.5,
        "stop": 9.5 if side == "BUY" else 10.5,
        "horizon_days": 3,
        "model_version": "signals_v1",
    }


def test_run_backtest_hits_buy_target() -> None:
    signals = build_signal_payloads([_signal("2024-01-02", "2024-01-03")])
    candles = build_candle_lookup(
        [
            {
                "ticker": "TEST3",
                "data_pregao": dt.date(2024, 1, 3),
                "open": 10.0,
                "high": 10.1,
                "low": 9.8,
                "close": 10.0,
            },
            {
                "ticker": "TEST3",
                "data_pregao": dt.date(2024, 1, 4),
                "open": 10.0,
                "high": 10.6,
                "low": 9.9,
                "close": 10.55,
            },
        ]
    )
    trades = run_backtest(signals, candles)
    trade = trades[0]
    assert trade.entry_hit is True
    assert trade.exit_reason == "TARGET"
    assert trade.exit_date == dt.date(2024, 1, 4)
    assert trade.return_pct > 0


def test_run_backtest_prefers_stop_on_tie() -> None:
    signals = build_signal_payloads([_signal("2024-01-02", "2024-01-03")])
    candles = build_candle_lookup(
        [
            {
                "ticker": "TEST3",
                "data_pregao": dt.date(2024, 1, 3),
                "open": 10.0,
                "high": 10.6,
                "low": 9.4,
                "close": 9.9,
            }
        ]
    )
    trade = run_backtest(signals, candles)[0]
    assert trade.entry_hit is True
    assert trade.exit_reason == "STOP"
    assert trade.return_pct < 0


def test_run_backtest_handles_sell_side() -> None:
    signal = _signal("2024-01-02", "2024-01-03", side="SELL")
    signals = build_signal_payloads([signal])
    candles = build_candle_lookup(
        [
            {
                "ticker": "TEST3",
                "data_pregao": dt.date(2024, 1, 3),
                "open": 10.0,
                "high": 10.7,
                "low": 9.3,
                "close": 9.8,
            }
        ]
    )
    trade = run_backtest(signals, candles)[0]
    assert trade.exit_reason == "STOP"
    assert trade.return_pct < 0


def test_compute_metrics_returns_global_row() -> None:
    trades = [
        {
            "date_ref": dt.date(2024, 1, 2),
            "ticker": "AAA",
            "side": "BUY",
            "horizon_days": 3,
            "entry_hit": True,
            "return_pct": 0.05,
            "entry_fill_date": dt.date(2024, 1, 3),
            "exit_date": dt.date(2024, 1, 4),
        },
        {
            "date_ref": dt.date(2024, 1, 2),
            "ticker": "BBB",
            "side": "SELL",
            "horizon_days": 3,
            "entry_hit": True,
            "return_pct": -0.02,
            "entry_fill_date": dt.date(2024, 1, 3),
            "exit_date": dt.date(2024, 1, 5),
        },
    ]
    metrics = compute_metrics(trades, dt.date(2024, 2, 1))
    global_rows = [m for m in metrics if m["ticker"] is None and m["side"] is None]
    assert global_rows
    assert global_rows[0]["signals"] == 2
    assert global_rows[0]["fills"] == 2
    assert global_rows[0]["win_rate"] > 0


def test_calendar_next_trading_day_skips_weekend_and_holiday() -> None:
    holidays = {dt.date(2024, 1, 1), dt.date(2024, 1, 2)}
    friday = dt.date(2023, 12, 29)
    assert calendar.next_trading_day(friday, holidays) == dt.date(2024, 1, 3)
    assert calendar.previous_trading_day(dt.date(2024, 1, 1), holidays) == dt.date(
        2023, 12, 29
    )
