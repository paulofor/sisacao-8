"""Deterministic daily backtest utilities for Sisacao-8."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable, List, Mapping, MutableMapping, Sequence

import pandas as pd  # type: ignore[import-untyped]


@dataclass(frozen=True)
class DailyBar:
    ticker: str
    date: dt.date
    open: float
    high: float
    low: float
    close: float

    @staticmethod
    def from_mapping(row: Mapping[str, object]) -> "DailyBar":
        ticker = str(row.get("ticker", "")).strip().upper()
        if not ticker:
            raise ValueError("ticker não pode ser vazio nos candles do backtest")
        raw_date = (
            row.get("data_pregao") or row.get("date") or row.get("reference_date")
        )
        if isinstance(raw_date, dt.datetime):
            trade_date = raw_date.date()
        elif isinstance(raw_date, dt.date):
            trade_date = raw_date
        else:
            trade_date = dt.datetime.strptime(str(raw_date), "%Y-%m-%d").date()
        return DailyBar(
            ticker=ticker,
            date=trade_date,
            open=float(row.get("open", 0.0) or 0.0),
            high=float(row.get("high", 0.0) or 0.0),
            low=float(row.get("low", 0.0) or 0.0),
            close=float(row.get("close", 0.0) or 0.0),
        )


@dataclass(frozen=True)
class SignalPayload:
    date_ref: dt.date
    valid_for: dt.date
    ticker: str
    side: str
    entry: float
    target: float
    stop: float
    horizon_days: int
    model_version: str

    @staticmethod
    def from_mapping(row: Mapping[str, object]) -> "SignalPayload":
        ticker = str(row.get("ticker", "")).strip().upper()
        if not ticker:
            raise ValueError("ticker não pode ser vazio nas entradas do backtest")
        side = str(row.get("side", "")).strip().upper() or "BUY"
        raw_date_ref = row.get("date_ref")
        if isinstance(raw_date_ref, dt.datetime):
            date_ref = raw_date_ref.date()
        elif isinstance(raw_date_ref, dt.date):
            date_ref = raw_date_ref
        else:
            date_ref = dt.datetime.strptime(str(raw_date_ref), "%Y-%m-%d").date()
        raw_valid = row.get("valid_for") or row.get("entrada_em")
        if isinstance(raw_valid, dt.datetime):
            valid_for = raw_valid.date()
        elif isinstance(raw_valid, dt.date):
            valid_for = raw_valid
        else:
            valid_for = dt.datetime.strptime(str(raw_valid), "%Y-%m-%d").date()
        horizon = int(row.get("horizon_days") or row.get("horizon") or 0)
        if horizon <= 0:
            raise ValueError("horizon_days deve ser positivo para o backtest diário")
        model_version = str(row.get("model_version") or "signals_v1")
        return SignalPayload(
            date_ref=date_ref,
            valid_for=valid_for,
            ticker=ticker,
            side=side,
            entry=float(row.get("entry", 0.0) or 0.0),
            target=float(row.get("target", 0.0) or 0.0),
            stop=float(row.get("stop", 0.0) or 0.0),
            horizon_days=horizon,
            model_version=model_version,
        )


@dataclass
class BacktestTrade:
    date_ref: dt.date
    valid_for: dt.date
    ticker: str
    side: str
    entry: float
    target: float
    stop: float
    horizon_days: int
    model_version: str
    entry_hit: bool
    entry_fill_date: dt.date | None
    exit_date: dt.date | None
    exit_reason: str
    exit_price: float | None
    return_pct: float | None
    mfe_pct: float | None
    mae_pct: float | None

    def to_dict(self) -> Mapping[str, object]:
        return {
            "date_ref": self.date_ref,
            "valid_for": self.valid_for,
            "ticker": self.ticker,
            "side": self.side,
            "entry": self.entry,
            "target": self.target,
            "stop": self.stop,
            "horizon_days": self.horizon_days,
            "model_version": self.model_version,
            "entry_hit": self.entry_hit,
            "entry_fill_date": self.entry_fill_date,
            "exit_date": self.exit_date,
            "exit_reason": self.exit_reason,
            "exit_price": self.exit_price,
            "return_pct": self.return_pct,
            "mfe_pct": self.mfe_pct,
            "mae_pct": self.mae_pct,
        }


def build_candle_lookup(
    rows: Iterable[Mapping[str, object]],
) -> Mapping[str, Mapping[dt.date, DailyBar]]:
    """Return candles grouped by ticker/date for quick access."""

    grouped: MutableMapping[str, MutableMapping[dt.date, DailyBar]] = {}
    for row in rows:
        bar = DailyBar.from_mapping(row)
        grouped.setdefault(bar.ticker, {})[bar.date] = bar
    return grouped


def build_signal_payloads(rows: Iterable[Mapping[str, object]]) -> List[SignalPayload]:
    """Normalize BigQuery rows into :class:`SignalPayload` objects."""

    payloads: List[SignalPayload] = []
    for row in rows:
        payloads.append(SignalPayload.from_mapping(row))
    return payloads


def run_backtest(
    signals: Sequence[SignalPayload],
    candles: Mapping[str, Mapping[dt.date, DailyBar]],
) -> List[BacktestTrade]:
    """Simulate trades deterministically using daily highs/lows."""

    trades: List[BacktestTrade] = []
    for signal in signals:
        ticker_candles = candles.get(signal.ticker, {})
        trades.append(_simulate_signal(signal, ticker_candles))
    return trades


def _simulate_signal(
    signal: SignalPayload,
    ticker_candles: Mapping[dt.date, DailyBar],
) -> BacktestTrade:
    ordered_days = [
        bar
        for _, bar in sorted(ticker_candles.items(), key=lambda item: item[0])
        if bar.date >= signal.valid_for
    ]
    ordered_days = ordered_days[: signal.horizon_days]
    entry_hit = False
    entry_fill_date: dt.date | None = None
    exit_date: dt.date | None = None
    exit_reason = "NO_FILL"
    exit_price: float | None = None
    return_pct: float | None = 0.0
    mfe_pct: float | None = None
    mae_pct: float | None = None
    last_bar: DailyBar | None = None

    for bar in ordered_days:
        last_bar = bar
        if not entry_hit:
            if _entry_touched(signal.side, bar, signal.entry):
                entry_hit = True
                entry_fill_date = bar.date
        if not entry_hit:
            continue
        mfe_pct, mae_pct = _update_excursions(
            signal.side,
            signal.entry,
            bar.high,
            bar.low,
            mfe_pct,
            mae_pct,
        )
        reason, price = _check_exit(signal.side, bar, signal.target, signal.stop)
        if reason:
            exit_reason = reason
            exit_price = price
            exit_date = bar.date
            break
    if entry_hit and exit_price is None:
        exit_reason = "EXPIRE"
        if last_bar is not None:
            exit_price = last_bar.close
            exit_date = last_bar.date
    if not ordered_days:
        exit_reason = "NO_DATA"
    if entry_hit and exit_price is not None:
        return_pct = _compute_return(signal.side, signal.entry, exit_price)
    elif not entry_hit:
        return_pct = 0.0
    return BacktestTrade(
        date_ref=signal.date_ref,
        valid_for=signal.valid_for,
        ticker=signal.ticker,
        side=signal.side,
        entry=signal.entry,
        target=signal.target,
        stop=signal.stop,
        horizon_days=signal.horizon_days,
        model_version=signal.model_version,
        entry_hit=entry_hit,
        entry_fill_date=entry_fill_date,
        exit_date=exit_date,
        exit_reason=exit_reason,
        exit_price=exit_price,
        return_pct=return_pct,
        mfe_pct=mfe_pct,
        mae_pct=mae_pct,
    )


def _entry_touched(side: str, bar: DailyBar, entry: float) -> bool:
    if side == "SELL":
        return bar.high >= entry
    return bar.low <= entry


def _update_excursions(
    side: str,
    entry: float,
    day_high: float,
    day_low: float,
    mfe: float | None,
    mae: float | None,
) -> tuple[float | None, float | None]:
    if entry <= 0:
        return mfe, mae
    if side == "SELL":
        favorable = (entry - day_low) / entry
        adverse = (entry - day_high) / entry
    else:
        favorable = (day_high - entry) / entry
        adverse = (day_low - entry) / entry
    mfe = favorable if mfe is None else max(mfe, favorable)
    mae = adverse if mae is None else min(mae, adverse)
    return mfe, mae


def _check_exit(
    side: str,
    bar: DailyBar,
    target: float,
    stop: float,
) -> tuple[str | None, float | None]:
    if side == "SELL":
        hit_stop = bar.high >= stop
        hit_target = bar.low <= target
    else:
        hit_stop = bar.low <= stop
        hit_target = bar.high >= target
    if hit_stop and hit_target:
        return "STOP", stop
    if hit_stop:
        return "STOP", stop
    if hit_target:
        return "TARGET", target
    return None, None


def _compute_return(side: str, entry: float, exit_price: float) -> float:
    if entry == 0:
        return 0.0
    if side == "SELL":
        return (entry - exit_price) / entry
    return (exit_price - entry) / entry


def compute_metrics(
    rows: Sequence[Mapping[str, object]], as_of_date: dt.date
) -> List[Mapping[str, object]]:
    """Aggregate rolling metrics per ticker/side for ranking."""

    if not rows:
        return []
    frame = pd.DataFrame(rows)
    if frame.empty:
        return []
    frame["entry_hit"] = frame["entry_hit"].fillna(False)
    frame["return_pct"] = pd.to_numeric(frame["return_pct"], errors="coerce")
    frame["horizon_days"] = pd.to_numeric(
        frame["horizon_days"], errors="coerce"
    ).astype("Int64")
    frame["ticker"] = frame["ticker"].astype(str).str.upper()
    frame["side"] = frame["side"].astype(str).str.upper()
    frame["entry_fill_date"] = pd.to_datetime(frame["entry_fill_date"])
    frame["exit_date"] = pd.to_datetime(frame["exit_date"])
    frame["days_in_trade"] = (frame["exit_date"] - frame["entry_fill_date"]).dt.days + 1

    metrics: List[Mapping[str, object]] = []
    for horizon, horizon_df in frame.groupby("horizon_days"):
        metrics.extend(_compute_metrics_for_groups(horizon_df, horizon, as_of_date))
    return metrics


def _compute_metrics_for_groups(
    frame: pd.DataFrame,
    horizon: int,
    as_of_date: dt.date,
) -> List[Mapping[str, object]]:
    results: List[Mapping[str, object]] = []
    combos = [(None, None)]
    combos.extend([(None, side) for side in sorted(frame["side"].unique())])
    combos.extend([(ticker, None) for ticker in sorted(frame["ticker"].unique())])
    combos.extend(
        [
            (ticker, side)
            for ticker in sorted(frame["ticker"].unique())
            for side in sorted(frame["side"].unique())
        ]
    )
    for ticker, side in combos:
        subset = frame
        if ticker is not None:
            subset = subset[subset["ticker"] == ticker]
        if side is not None:
            subset = subset[subset["side"] == side]
        if subset.empty:
            continue
        fills = int(subset["entry_hit"].sum())
        signals = int(len(subset))
        filled = subset[subset["entry_hit"]]
        wins = filled[filled["return_pct"] > 0]
        losses = filled[filled["return_pct"] < 0]
        win_rate = float(wins.shape[0] / fills) if fills else 0.0
        avg_return = float(filled["return_pct"].mean()) if not filled.empty else None
        avg_win = float(wins["return_pct"].mean()) if not wins.empty else None
        avg_loss = float(losses["return_pct"].mean()) if not losses.empty else None
        sum_wins = float(wins["return_pct"].sum()) if not wins.empty else 0.0
        sum_losses = float(losses["return_pct"].sum()) if not losses.empty else 0.0
        profit_factor = None
        if sum_losses < 0:
            profit_factor = sum_wins / abs(sum_losses) if abs(sum_losses) > 0 else None
        avg_days = None
        filled_with_days = filled[filled["days_in_trade"].notna()]
        if not filled_with_days.empty:
            avg_days = float(filled_with_days["days_in_trade"].mean())
        horizon_value = None if pd.isna(horizon) else int(horizon)
        results.append(
            {
                "as_of_date": as_of_date,
                "ticker": ticker,
                "side": side,
                "horizon_days": horizon_value,
                "signals": signals,
                "fills": int(fills),
                "win_rate": win_rate,
                "avg_return": avg_return,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": profit_factor,
                "avg_days_in_trade": avg_days,
            }
        )
    return results
