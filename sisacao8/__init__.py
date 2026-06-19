"""Utility package for Sisacao-8 data engineering pipelines."""

from .b3 import parse_b3_daily_zip
from .backtest import (
    BacktestTrade,
    DailyBar,
    SignalPayload,
    build_candle_lookup,
    build_signal_payloads,
)
from .backtest import compute_metrics as compute_backtest_metrics
from .backtest import (
    run_backtest,
)
from .calendar import (
    add_trading_days,
    is_trading_day,
    next_trading_day,
    normalize_holidays,
    previous_trading_day,
)
from .candles import Candle, Timeframe, ensure_timezone, summarize_flags
from .intraday import build_intraday_candles, rollup_candles
from .neural_promotion import (
    NeuralPromotionCriteria,
    NeuralPromotionDecision,
    build_promotion_audit_record,
    evaluate_neural_promotion,
    latest_controlled_promotion,
)
from .observability import StructuredLogger
from .signals import (
    ConditionalSignal,
    generate_conditional_signals,
    generate_neural_conditional_signals,
)

__all__ = [
    "Candle",
    "Timeframe",
    "ConditionalSignal",
    "ensure_timezone",
    "summarize_flags",
    "build_intraday_candles",
    "rollup_candles",
    "generate_conditional_signals",
    "generate_neural_conditional_signals",
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
    "NeuralPromotionCriteria",
    "NeuralPromotionDecision",
    "build_promotion_audit_record",
    "evaluate_neural_promotion",
    "latest_controlled_promotion",
    "StructuredLogger",
]
