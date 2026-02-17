"""Utility package for Sisacao-8 data engineering pipelines."""

from .candles import Candle, Timeframe, ensure_timezone, summarize_flags
from .b3 import parse_b3_daily_zip
from .intraday import build_intraday_candles, rollup_candles
from .signals import ConditionalSignal, generate_conditional_signals

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
]
