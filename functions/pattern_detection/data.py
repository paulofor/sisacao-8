"""Dataset preparation helpers for price move classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pandas as pd  # type: ignore[import-untyped]

CLASS_NAMES = {0: "down", 1: "neutral", 2: "up"}


@dataclass(frozen=True)
class WindowConfig:
    """Configuration for rolling window datasets."""

    lookback: int = 20
    horizon: int = 5
    threshold: float = 0.08
    price_column: str = "close"

    def __post_init__(self) -> None:
        if self.lookback <= 0:
            msg = "lookback must be positive"
            raise ValueError(msg)
        if self.horizon <= 0:
            msg = "horizon must be positive"
            raise ValueError(msg)
        if self.threshold <= 0:
            msg = "threshold must be positive"
            raise ValueError(msg)


def _label_future_move(future_return: float, threshold: float) -> int:
    """Return the class index for a future return."""

    if future_return >= threshold:
        return 2
    if future_return <= -threshold:
        return 0
    return 1


def prepare_training_data(
    data: pd.DataFrame,
    config: WindowConfig | None = None,
) -> Tuple[np.ndarray, np.ndarray, pd.Index]:
    """Create feature matrix and labels for neural network training.

    Parameters
    ----------
    data:
        DataFrame containing at least the configured price column. The data is
        sorted by index before processing to ensure chronological order.
    config:
        Sliding window configuration. Defaults to :class:`WindowConfig` if not
        provided.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray, pd.Index]
        Feature matrix with shape ``(n_samples, lookback)``, label vector with
        shape ``(n_samples,)`` and the index positions associated with each
        sample.
    """

    cfg = config or WindowConfig()
    if cfg.price_column not in data.columns:
        msg = f"Missing required column: {cfg.price_column}"
        raise KeyError(msg)

    series = data[[cfg.price_column]].dropna().astype(float)
    if series.empty:
        msg = "Input data is empty after dropping NaNs"
        raise ValueError(msg)

    series = series.sort_index()
    prices = series[cfg.price_column]

    returns = prices.pct_change()
    returns = returns.replace([np.inf, -np.inf], np.nan)
    returns = returns.fillna(0.0)
    future_returns = (prices.shift(-cfg.horizon) / prices) - 1.0

    start = cfg.lookback
    end = len(prices) - cfg.horizon
    if end <= start:
        msg = "Not enough data for the requested configuration"
        raise ValueError(msg)

    features: List[np.ndarray] = []
    labels: List[int] = []
    sample_index: List[pd.Timestamp] = []

    for idx in range(start, end):
        window_series = returns.iloc[slice(idx - cfg.lookback, idx)]
        window = window_series.to_numpy(dtype=np.float32)
        future_value = float(future_returns.iloc[idx])
        label_value = _label_future_move(future_value, cfg.threshold)
        features.append(window)
        labels.append(label_value)
        sample_index.append(series.index[idx])

    x = np.stack(features).astype(np.float32)
    y = np.asarray(labels, dtype=np.int64)
    index = pd.Index(sample_index)
    return x, y, index


def split_time_series(
    features: np.ndarray,
    labels: np.ndarray,
    validation_split: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Split sequential data keeping chronological order."""

    if not 0 < validation_split < 1:
        msg = "validation_split must be between 0 and 1"
        raise ValueError(msg)

    total = len(features)
    if total != len(labels):
        msg = "features and labels must have the same length"
        raise ValueError(msg)
    split_index = int(total * (1 - validation_split))
    if split_index <= 0 or split_index >= total:
        msg = "validation_split leads to empty train or validation set"
        raise ValueError(msg)

    return (
        features[:split_index],
        labels[:split_index],
        features[split_index:],
        labels[split_index:],
    )
