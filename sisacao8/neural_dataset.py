"""Dataset helpers for neural EOD signal training.

The functions in this module build supervised tabular examples using only
candles available up to ``reference_date`` for features and future candles only
for historical labels. They are intentionally side-effect free so the same logic
can be reused by batch extraction jobs and unit tests.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Literal

import numpy as np
import pandas as pd

from sisacao8.trade_engine import TradeEngineConfig, simulate_eod_barrier_trade

LabelClass = Literal["up", "down", "neutral"]

FEATURE_VERSION = "feature_eod_tabular_v2"
LABEL_VERSION = "label_eod_barrier_v2"
DEFAULT_MIN_HISTORY_DAYS = 20


@dataclass(frozen=True)
class BarrierLabelConfig:
    """Versioned parameters used to create barrier-based EOD labels."""

    entry_pct: float = 0.02
    target_pct: float = 0.07
    stop_pct: float = 0.07
    horizon_days: int = 15
    min_net_return_pct: float = 0.0
    cost_pct: float = 0.0
    spread_pct: float = 0.0
    slippage_pct: float = 0.0
    borrow_cost_pct: float = 0.0
    version: str = LABEL_VERSION

    def __post_init__(self) -> None:
        if not 0 < self.entry_pct < 1:
            raise ValueError("entry_pct must be between 0 and 1")
        if not 0 < self.target_pct < 1:
            raise ValueError("target_pct must be between 0 and 1")
        if not 0 < self.stop_pct < 1:
            raise ValueError("stop_pct must be between 0 and 1")
        if self.horizon_days < 1:
            raise ValueError("horizon_days must be positive")


@dataclass(frozen=True)
class DatasetSnapshotManifest:
    """Audit manifest for an immutable point-in-time neural dataset snapshot."""

    dataset_snapshot: str
    protocol_version: str
    feature_version: str
    label_version: str
    universe_version: str
    query_hash: str
    code_hash: str
    start_date: dt.date | None
    end_date: dt.date | None
    tickers: int
    rows: int
    split_counts: dict[str, int]
    label_distribution: dict[str, int]
    quality_summary: dict[str, int]
    cost_assumptions: dict[str, float]
    calendar_version: str
    corporate_actions_policy: str
    survivorship_policy: str

    def to_json_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("start_date", "end_date"):
            if payload[key] is not None:
                payload[key] = payload[key].isoformat()
        return payload


@dataclass(frozen=True)
class TemporalSplitConfig:
    """Chronological split percentages and embargo for model datasets."""

    train_pct: float = 0.65
    validation_pct: float = 0.175
    embargo_days: int = 15

    def __post_init__(self) -> None:
        if not 0 < self.train_pct < 1:
            raise ValueError("train_pct must be between 0 and 1")
        if not 0 < self.validation_pct < 1:
            raise ValueError("validation_pct must be between 0 and 1")
        if self.train_pct + self.validation_pct >= 1:
            raise ValueError("train_pct + validation_pct must be lower than 1")
        if self.embargo_days < 0:
            raise ValueError("embargo_days cannot be negative")


def build_training_dataset(
    candles: pd.DataFrame,
    holidays: Iterable[dt.date] | None = None,
    label_config: BarrierLabelConfig | None = None,
    split_config: TemporalSplitConfig | None = None,
    min_history_days: int = DEFAULT_MIN_HISTORY_DAYS,
) -> pd.DataFrame:
    """Return a supervised neural EOD dataset from daily OHLCV candles.

    Expected input columns are ``ticker``, ``data_pregao``, ``open``, ``high``,
    ``low``, ``close`` and ``volume``. ``financial_volume`` is optional; when it
    is absent the function uses ``close * volume``.
    """

    if min_history_days < 1:
        raise ValueError("min_history_days must be positive")
    label_config = label_config or BarrierLabelConfig()
    split_config = split_config or TemporalSplitConfig(
        embargo_days=label_config.horizon_days
    )
    prepared = _prepare_candles(candles)
    features = _build_features(prepared, min_history_days)
    labels = _build_labels(prepared, label_config)
    dataset = features.merge(labels, on=["ticker", "reference_date"], how="inner")
    if holidays:
        holiday_set = set(holidays)
        dataset = dataset[~dataset["reference_date"].isin(holiday_set)]
        dataset = dataset[~dataset["valid_for"].isin(holiday_set)]
    dataset = dataset.sort_values(["reference_date", "ticker"]).reset_index(drop=True)
    dataset["dataset_split"] = assign_temporal_splits(
        dataset["reference_date"], split_config
    )
    return dataset


def build_inference_features(
    candles: pd.DataFrame,
    min_history_days: int = DEFAULT_MIN_HISTORY_DAYS,
) -> pd.DataFrame:
    """Return feature rows for neural EOD inference without historical labels.

    The output uses the same feature contract as ``build_training_dataset`` but
    intentionally skips label creation, temporal split assignment and future
    candles. It is therefore safe for the daily inference job that runs after
    the close of ``reference_date``.
    """

    if min_history_days < 1:
        raise ValueError("min_history_days must be positive")
    prepared = _prepare_candles(candles)
    return (
        _build_features(prepared, min_history_days)
        .sort_values(["reference_date", "ticker"])
        .reset_index(drop=True)
    )


def assign_temporal_splits(
    reference_dates: pd.Series, split_config: TemporalSplitConfig | None = None
) -> pd.Series:
    """Assign train/validation/test splits by date with embargo rows removed."""

    split_config = split_config or TemporalSplitConfig()
    unique_dates = sorted(pd.to_datetime(reference_dates).dt.date.unique())
    if not unique_dates:
        return pd.Series(dtype="object", index=reference_dates.index)
    train_end_idx = int(len(unique_dates) * split_config.train_pct)
    split_boundary = split_config.train_pct + split_config.validation_pct
    valid_end_idx = int(len(unique_dates) * split_boundary)
    train_dates = set(unique_dates[:train_end_idx])
    validation_embargo_days = _bounded_embargo_days(
        split_config.embargo_days, valid_end_idx - train_end_idx
    )
    test_embargo_days = _bounded_embargo_days(
        split_config.embargo_days, len(unique_dates) - valid_end_idx
    )
    validation_dates = set(
        unique_dates[train_end_idx + validation_embargo_days : valid_end_idx]
    )
    test_dates = set(unique_dates[valid_end_idx + test_embargo_days :])

    def classify(value: object) -> str | None:
        date_value = pd.Timestamp(value).date()
        if date_value in train_dates:
            return "train"
        if date_value in validation_dates:
            return "validation"
        if date_value in test_dates:
            return "test"
        return None

    return reference_dates.map(classify)


def build_dataset_manifest(
    dataset: pd.DataFrame,
    *,
    dataset_snapshot: str,
    protocol_version: str = "neural_eod_protocol_v1",
    universe_version: str = "b3_point_in_time_v1",
    query_text: str = "",
    code_text: str = "sisacao8.neural_dataset.build_training_dataset",
    label_config: BarrierLabelConfig | None = None,
    calendar_version: str = "b3_holidays_v1",
    corporate_actions_policy: str = "daily_ohlcv_adjustment_policy_source_table",
    survivorship_policy: str = "acao_bovespa_point_in_time_when_available",
) -> DatasetSnapshotManifest:
    """Create the Phase 2 immutable manifest for a dataset snapshot."""

    label_config = label_config or BarrierLabelConfig()
    split_counts = _value_counts(dataset, "dataset_split", null_label="embargo")
    return DatasetSnapshotManifest(
        dataset_snapshot=dataset_snapshot,
        protocol_version=protocol_version,
        feature_version=_single_or_default(dataset, "feature_version", FEATURE_VERSION),
        label_version=_single_or_default(
            dataset, "label_version", label_config.version
        ),
        universe_version=universe_version,
        query_hash=_stable_hash(query_text),
        code_hash=_stable_hash(code_text),
        start_date=_min_date(dataset, "reference_date"),
        end_date=_max_date(dataset, "reference_date"),
        tickers=int(dataset["ticker"].nunique()) if "ticker" in dataset else 0,
        rows=int(len(dataset)),
        split_counts=split_counts,
        label_distribution=_value_counts(dataset, "label_class"),
        quality_summary={
            "missing_ohlcv_rows": _true_count(dataset, "has_missing_ohlcv"),
            "zero_volume_rows": _true_count(dataset, "has_zero_volume"),
            "suspicious_candle_rows": _true_count(dataset, "is_suspicious_candle"),
            "embargo_rows": int(split_counts.get("embargo", 0)),
        },
        cost_assumptions={
            "cost_pct": float(label_config.cost_pct),
            "spread_pct": float(label_config.spread_pct),
            "slippage_pct": float(label_config.slippage_pct),
            "borrow_cost_pct": float(label_config.borrow_cost_pct),
        },
        calendar_version=calendar_version,
        corporate_actions_policy=corporate_actions_policy,
        survivorship_policy=survivorship_policy,
    )


def _stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _single_or_default(dataset: pd.DataFrame, column: str, default: str) -> str:
    if column not in dataset or dataset.empty:
        return default
    values = dataset[column].dropna().astype(str).unique()
    return str(values[0]) if len(values) else default


def _value_counts(
    dataset: pd.DataFrame, column: str, null_label: str | None = None
) -> dict[str, int]:
    if column not in dataset or dataset.empty:
        return {}
    values = dataset[column]
    if null_label is not None:
        values = values.fillna(null_label)
    return {str(k): int(v) for k, v in values.value_counts().sort_index().items()}


def _true_count(dataset: pd.DataFrame, column: str) -> int:
    if column not in dataset or dataset.empty:
        return 0
    return int(dataset[column].fillna(False).astype(bool).sum())


def _min_date(dataset: pd.DataFrame, column: str) -> dt.date | None:
    if column not in dataset or dataset.empty:
        return None
    value = pd.to_datetime(dataset[column]).min()
    return None if pd.isna(value) else value.date()


def _max_date(dataset: pd.DataFrame, column: str) -> dt.date | None:
    if column not in dataset or dataset.empty:
        return None
    value = pd.to_datetime(dataset[column]).max()
    return None if pd.isna(value) else value.date()


def _bounded_embargo_days(
    configured_embargo_days: int, split_capacity_days: int
) -> int:
    if split_capacity_days <= 0:
        return 0
    return min(configured_embargo_days, split_capacity_days // 2)


def _prepare_candles(candles: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "data_pregao", "open", "high", "low", "close", "volume"}
    missing = required.difference(candles.columns)
    if missing:
        raise ValueError(f"Missing required candle columns: {sorted(missing)}")
    prepared = candles.copy()
    prepared["ticker"] = prepared["ticker"].astype(str).str.upper().str.strip()
    prepared["data_pregao"] = pd.to_datetime(prepared["data_pregao"]).dt.date
    for column in ["open", "high", "low", "close", "volume"]:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    if "financial_volume" not in prepared:
        prepared["financial_volume"] = prepared["close"] * prepared["volume"]
    prepared["financial_volume"] = pd.to_numeric(
        prepared["financial_volume"], errors="coerce"
    )
    return prepared.sort_values(["ticker", "data_pregao"]).drop_duplicates(
        ["ticker", "data_pregao"], keep="last"
    )


def _build_features(candles: pd.DataFrame, min_history_days: int) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for _, group in candles.groupby("ticker", sort=False):
        group = group.sort_values("data_pregao").copy()
        close = group["close"]
        volume = group["volume"]
        fin_volume = group["financial_volume"]
        returns = close.pct_change()
        group["log_return_1d"] = np.log(close / close.shift(1))
        group["log_return_5d"] = np.log(close / close.shift(5))
        group["log_return_10d"] = np.log(close / close.shift(10))
        group["log_return_20d"] = np.log(close / close.shift(20))
        group["return_5d"] = close.pct_change(5)
        group["return_10d"] = close.pct_change(10)
        group["return_20d"] = close.pct_change(20)
        group["volatility_10d"] = returns.rolling(10).std()
        group["volatility_20d"] = returns.rolling(20).std()
        group["daily_range_pct"] = (group["high"] - group["low"]) / close
        group["intraday_return_pct"] = (close - group["open"]) / group["open"]
        group["gap_open_pct"] = (group["open"] - close.shift(1)) / close.shift(1)
        fin_volume_mean_20 = fin_volume.rolling(20).mean()
        fin_volume_std_20 = fin_volume.rolling(20).std()
        group["financial_volume_z20"] = (
            fin_volume - fin_volume_mean_20
        ) / fin_volume_std_20
        group["log_financial_volume"] = np.log1p(fin_volume.clip(lower=0))
        group["log_volume"] = np.log1p(volume.clip(lower=0))
        group["volume_ratio_20d"] = volume / volume.rolling(20).mean()
        group["distance_high_20d_pct"] = (
            close - group["high"].rolling(20).max()
        ) / close
        group["distance_low_20d_pct"] = (close - group["low"].rolling(20).min()) / close
        group["distance_sma_20d_pct"] = (close - close.rolling(20).mean()) / close
        group["history_days"] = range(1, len(group) + 1)
        group["has_missing_ohlcv"] = (
            group[["open", "high", "low", "close", "volume"]].isna().any(axis=1)
        )
        group["has_zero_volume"] = group["volume"].fillna(0).le(0)
        group["is_suspicious_candle"] = (
            group["close"].le(0)
            | group["open"].le(0)
            | group["high"].lt(group[["open", "close", "low"]].max(axis=1))
            | group["low"].gt(group[["open", "close", "high"]].min(axis=1))
        )
        rows.append(group)
    features = pd.concat(rows, ignore_index=True)
    features = features[features["history_days"] >= min_history_days].copy()
    features = features.rename(columns={"data_pregao": "reference_date"})
    features["feature_version"] = FEATURE_VERSION
    return features[
        [
            "ticker",
            "reference_date",
            "feature_version",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "financial_volume",
            "log_return_1d",
            "log_return_5d",
            "log_return_10d",
            "log_return_20d",
            "return_5d",
            "return_10d",
            "return_20d",
            "volatility_10d",
            "volatility_20d",
            "daily_range_pct",
            "intraday_return_pct",
            "gap_open_pct",
            "financial_volume_z20",
            "log_financial_volume",
            "log_volume",
            "volume_ratio_20d",
            "distance_high_20d_pct",
            "distance_low_20d_pct",
            "distance_sma_20d_pct",
            "has_missing_ohlcv",
            "has_zero_volume",
            "is_suspicious_candle",
        ]
    ]


def _build_labels(candles: pd.DataFrame, config: BarrierLabelConfig) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for ticker, group in candles.groupby("ticker", sort=False):
        records = group.sort_values("data_pregao").to_dict("records")
        for idx, candle in enumerate(records[:-1]):
            valid_for = records[idx + 1]["data_pregao"]
            future = records[idx + 1 : idx + 1 + config.horizon_days]
            buy_result = _evaluate_side(candle, future, "BUY", config)
            sell_result = _evaluate_side(candle, future, "SELL", config)
            buy_return = buy_result.net_return
            sell_return = sell_result.net_return
            label = _choose_label(buy_return, sell_return, config.min_net_return_pct)
            selected_result = (
                buy_result
                if label == "up"
                else sell_result if label == "down" else None
            )
            rows.append(
                {
                    "ticker": ticker,
                    "reference_date": candle["data_pregao"],
                    "valid_for": valid_for,
                    "label_version": config.version,
                    "label_class": label,
                    "future_return": max(buy_return, sell_return),
                    "buy_net_return": buy_return,
                    "sell_net_return": sell_return,
                    "entry_filled_buy": buy_result.entry_filled,
                    "entry_filled_sell": sell_result.entry_filled,
                    "days_to_event_buy": buy_result.holding_sessions,
                    "days_to_event_sell": sell_result.holding_sessions,
                    "trade_side": (
                        selected_result.trade_side if selected_result else None
                    ),
                    "entry_filled": (
                        selected_result.entry_filled if selected_result else False
                    ),
                    "entry_date": (
                        selected_result.entry_date if selected_result else None
                    ),
                    "entry_price": (
                        selected_result.entry_price if selected_result else None
                    ),
                    "exit_date": selected_result.exit_date if selected_result else None,
                    "exit_price": (
                        selected_result.exit_price if selected_result else None
                    ),
                    "exit_reason": (
                        selected_result.exit_reason if selected_result else None
                    ),
                    "gross_return": (
                        selected_result.gross_return if selected_result else 0.0
                    ),
                    "net_return": (
                        selected_result.net_return if selected_result else 0.0
                    ),
                    "holding_sessions": (
                        selected_result.holding_sessions if selected_result else None
                    ),
                    "max_adverse_excursion": (
                        selected_result.max_adverse_excursion
                        if selected_result
                        else None
                    ),
                    "max_favorable_excursion": (
                        selected_result.max_favorable_excursion
                        if selected_result
                        else None
                    ),
                    "execution_policy_version": (
                        selected_result.execution_policy_version
                        if selected_result
                        else TradeEngineConfig().version
                    ),
                }
            )
    return pd.DataFrame(rows)


def _evaluate_side(
    candle: dict[str, object],
    future: list[dict[str, object]],
    side: Literal["BUY", "SELL"],
    config: BarrierLabelConfig,
):
    close = float(candle["close"])
    if side == "BUY":
        entry = close * (1 - config.entry_pct)
        target = entry * (1 + config.target_pct)
        stop = entry * (1 - config.stop_pct)
    else:
        entry = close * (1 + config.entry_pct)
        target = entry * (1 - config.target_pct)
        stop = entry * (1 + config.stop_pct)
    return simulate_eod_barrier_trade(
        side=side,
        entry=entry,
        target=target,
        stop=stop,
        bars=future,
        config=TradeEngineConfig(
            horizon_days=config.horizon_days,
            cost_pct=config.cost_pct,
            spread_pct=config.spread_pct,
            slippage_pct=config.slippage_pct,
            borrow_cost_pct=config.borrow_cost_pct,
        ),
    )


def _choose_label(
    buy_return: float, sell_return: float, min_net_return_pct: float
) -> LabelClass:
    if buy_return > sell_return and buy_return > min_net_return_pct:
        return "up"
    if sell_return > buy_return and sell_return > min_net_return_pct:
        return "down"
    return "neutral"
