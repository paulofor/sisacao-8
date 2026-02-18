"""Utility package for Sisacao-8 data engineering pipelines."""

from .candles import Candle, Timeframe, ensure_timezone, summarize_flags
from .b3 import parse_b3_daily_zip
from .intraday import build_intraday_candles, rollup_candles
from .signals import ConditionalSignal, generate_conditional_signals
from .calendar import (
    add_trading_days,
    is_trading_day,
    next_trading_day,
    normalize_holidays,
    previous_trading_day,
)
from .backtest import (
    BacktestTrade,
    DailyBar,
    SignalPayload,
    build_candle_lookup,
    build_signal_payloads,
    compute_metrics as compute_backtest_metrics,
    run_backtest,
)
from .observability import StructuredLogger

__all__ = [
    "Candle",
    "Timeframe",
    "ConditionalSignal",
    "ensure_timezone",
    "summarize_flags",
    "build_intraday_candles",
    "rollup_candles",
    "generate_conditional_signals",
    "parse_b3_daily_zip",
    "add_trading_days",
    "is_trading_day",
    "next_trading_day",
    "normalize_holidays",
    "previous_trading_day",
    "DailyBar",
    "SignalPayload",
    "BacktestTrade",
    "build_candle_lookup",
    "build_signal_payloads",
    "run_backtest",
    "compute_backtest_metrics",
    "StructuredLogger",
]
