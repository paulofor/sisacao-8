from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Iterable, Literal, Mapping

Side = Literal["BUY", "SELL"]
ExitReason = Literal[
    "TARGET",
    "STOP",
    "EXPIRED_MARK_TO_MARKET",
    "EXPIRED_UNFILLED",
    "INVALID",
    "NO_DATA",
]

EXECUTION_POLICY_VERSION = "execution_eod_barrier_v2_conservative_daily"


@dataclass(frozen=True)
class TradeEngineConfig:
    """Versioned EOD barrier execution policy shared by labels and backtests."""

    horizon_days: int = 15
    cost_pct: float = 0.0
    spread_pct: float = 0.0
    slippage_pct: float = 0.0
    borrow_cost_pct: float = 0.0
    same_bar_policy: str = "conservative_stop_first"
    version: str = EXECUTION_POLICY_VERSION

    def __post_init__(self) -> None:
        if self.horizon_days < 1:
            raise ValueError("horizon_days must be positive")
        for field_name in ["cost_pct", "spread_pct", "slippage_pct", "borrow_cost_pct"]:
            value = getattr(self, field_name)
            if value < 0:
                raise ValueError(f"{field_name} cannot be negative")
        if self.same_bar_policy != "conservative_stop_first":
            raise ValueError("only conservative_stop_first is supported for daily bars")


@dataclass(frozen=True)
class TradeBar:
    date: dt.date
    open: float
    high: float
    low: float
    close: float

    @staticmethod
    def from_mapping(row: Mapping[str, object]) -> "TradeBar":
        raw_date = (
            row.get("data_pregao") or row.get("date") or row.get("reference_date")
        )
        if isinstance(raw_date, dt.datetime):
            date = raw_date.date()
        elif isinstance(raw_date, dt.date):
            date = raw_date
        else:
            date = dt.datetime.strptime(str(raw_date), "%Y-%m-%d").date()
        return TradeBar(
            date=date,
            open=float(row.get("open", 0.0) or 0.0),
            high=float(row.get("high", 0.0) or 0.0),
            low=float(row.get("low", 0.0) or 0.0),
            close=float(row.get("close", 0.0) or 0.0),
        )


@dataclass(frozen=True)
class TradeSimulationResult:
    trade_side: str
    entry_filled: bool
    entry_date: dt.date | None
    entry_price: float | None
    exit_date: dt.date | None
    exit_price: float | None
    exit_reason: ExitReason
    gross_return: float
    net_return: float
    holding_sessions: int | None
    max_adverse_excursion: float | None
    max_favorable_excursion: float | None
    execution_policy_version: str
    transitions: tuple[Mapping[str, object], ...] = field(default_factory=tuple)


def simulate_eod_barrier_trade(
    *,
    side: Side,
    entry: float,
    target: float,
    stop: float,
    bars: Iterable[TradeBar | Mapping[str, object]],
    config: TradeEngineConfig | None = None,
) -> TradeSimulationResult:
    """Run the stateful EOD barrier lifecycle from pending entry to final exit."""

    config = config or TradeEngineConfig()
    normalized = [
        bar if isinstance(bar, TradeBar) else TradeBar.from_mapping(bar) for bar in bars
    ]
    normalized = sorted(normalized, key=lambda item: item.date)[: config.horizon_days]
    transitions: list[Mapping[str, object]] = []
    if entry <= 0 or target <= 0 or stop <= 0:
        return _result(
            side,
            False,
            None,
            None,
            None,
            None,
            "INVALID",
            0.0,
            0.0,
            None,
            None,
            None,
            config,
            transitions,
        )
    if not normalized:
        return _result(
            side,
            False,
            None,
            None,
            None,
            None,
            "NO_DATA",
            0.0,
            0.0,
            None,
            None,
            None,
            config,
            transitions,
        )

    entry_date: dt.date | None = None
    mfe: float | None = None
    mae: float | None = None
    for day_number, bar in enumerate(normalized, start=1):
        if entry_date is None:
            if not _entry_touched(side, bar, entry):
                transitions.append(
                    {
                        "state": "PENDING_ENTRY",
                        "date": bar.date,
                        "event": "ENTRY_NOT_TOUCHED",
                    }
                )
                continue
            entry_date = bar.date
            transitions.append(
                {
                    "state": "OPEN",
                    "date": bar.date,
                    "event": "ENTRY_FILLED",
                    "price": entry,
                }
            )
        mfe, mae = _update_excursions(side, entry, bar.high, bar.low, mfe, mae)
        reason, exit_price = _check_exit(side, bar, target, stop)
        if reason:
            transitions.append(
                {
                    "state": reason,
                    "date": bar.date,
                    "event": reason,
                    "price": exit_price,
                }
            )
            holding = _holding_sessions(normalized, entry_date, bar.date)
            gross = _compute_return(side, entry, exit_price)
            net = _apply_costs(side, gross, holding, config)
            return _result(
                side,
                True,
                entry_date,
                entry,
                bar.date,
                exit_price,
                reason,
                gross,
                net,
                holding,
                mae,
                mfe,
                config,
                transitions,
            )

    if entry_date is None:
        transitions.append(
            {
                "state": "EXPIRED_UNFILLED",
                "date": normalized[-1].date,
                "event": "HORIZON_ENDED",
            }
        )
        return _result(
            side,
            False,
            None,
            None,
            None,
            None,
            "EXPIRED_UNFILLED",
            0.0,
            0.0,
            None,
            None,
            None,
            config,
            transitions,
        )

    last_bar = normalized[-1]
    transitions.append(
        {
            "state": "EXPIRED_MARK_TO_MARKET",
            "date": last_bar.date,
            "event": "HORIZON_ENDED",
            "price": last_bar.close,
        }
    )
    gross = _compute_return(side, entry, last_bar.close)
    holding = _holding_sessions(normalized, entry_date, last_bar.date)
    net = _apply_costs(side, gross, holding, config)
    return _result(
        side,
        True,
        entry_date,
        entry,
        last_bar.date,
        last_bar.close,
        "EXPIRED_MARK_TO_MARKET",
        gross,
        net,
        holding,
        mae,
        mfe,
        config,
        transitions,
    )


def _result(
    side,
    filled,
    entry_date,
    entry_price,
    exit_date,
    exit_price,
    reason,
    gross,
    net,
    holding,
    mae,
    mfe,
    config,
    transitions,
):
    return TradeSimulationResult(
        side,
        filled,
        entry_date,
        entry_price,
        exit_date,
        exit_price,
        reason,
        gross,
        net,
        holding,
        mae,
        mfe,
        config.version,
        tuple(transitions),
    )


def _holding_sessions(
    bars: list[TradeBar], entry_date: dt.date, exit_date: dt.date
) -> int:
    return sum(1 for bar in bars if entry_date <= bar.date <= exit_date)


def _entry_touched(side: str, bar: TradeBar, entry: float) -> bool:
    return bar.high >= entry if side == "SELL" else bar.low <= entry


def _check_exit(
    side: str, bar: TradeBar, target: float, stop: float
) -> tuple[ExitReason | None, float | None]:
    if side == "SELL":
        hit_stop = bar.high >= stop
        hit_target = bar.low <= target
    else:
        hit_stop = bar.low <= stop
        hit_target = bar.high >= target
    if hit_stop:
        return "STOP", stop
    if hit_target:
        return "TARGET", target
    return None, None


def _compute_return(side: str, entry: float, exit_price: float) -> float:
    return (
        (entry - exit_price) / entry if side == "SELL" else (exit_price - entry) / entry
    )


def _apply_costs(
    side: str, gross: float, holding_sessions: int, config: TradeEngineConfig
) -> float:
    borrow = config.borrow_cost_pct * holding_sessions if side == "SELL" else 0.0
    return gross - config.cost_pct - config.spread_pct - config.slippage_pct - borrow


def _update_excursions(
    side: str,
    entry: float,
    day_high: float,
    day_low: float,
    mfe: float | None,
    mae: float | None,
) -> tuple[float | None, float | None]:
    if side == "SELL":
        favorable = (entry - day_low) / entry
        adverse = (entry - day_high) / entry
    else:
        favorable = (day_high - entry) / entry
        adverse = (day_low - entry) / entry
    return (
        favorable if mfe is None else max(mfe, favorable),
        adverse if mae is None else min(mae, adverse),
    )
