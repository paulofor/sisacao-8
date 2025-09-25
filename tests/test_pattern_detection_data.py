"""Tests for dataset preparation helpers."""

from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]
import pytest

from functions.pattern_detection import data as pattern_data
from functions.pattern_detection.data import (
    CLASS_NAMES,
    WindowConfig,
    prepare_training_data,
    split_time_series,
)


def test_label_future_move_thresholds() -> None:
    """Verify that threshold labeling follows the specification."""

    assert pattern_data._label_future_move(0.1, 0.08) == 2
    assert pattern_data._label_future_move(-0.1, 0.08) == 0
    assert pattern_data._label_future_move(0.05, 0.08) == 1


@pytest.mark.parametrize("lookback,horizon", [(5, 2), (10, 3)])
def test_prepare_samples(lookback: int, horizon: int) -> None:
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    prices = pd.Series(range(1, 61), index=dates, name="close").astype(float)
    df = pd.DataFrame({"close": prices})
    config = WindowConfig(lookback=lookback, horizon=horizon, threshold=0.08)

    features, labels, index = prepare_training_data(df, config)

    expected_samples = len(df) - horizon - lookback
    assert features.shape == (expected_samples, lookback)
    assert labels.shape == (expected_samples,)
    assert len(index) == expected_samples
    assert set(labels).issubset(CLASS_NAMES.keys())


def test_prepare_training_data_requires_enough_rows() -> None:
    df = pd.DataFrame({"close": [10.0, 11.0, 12.0]})
    config = WindowConfig(lookback=5, horizon=2)
    with pytest.raises(ValueError):
        prepare_training_data(df, config)


def test_split_time_series_preserves_order() -> None:
    rolling_mean = pd.Series(range(50)).rolling(window=3).mean().dropna()
    features = rolling_mean.to_frame()
    x = features.values.astype("float32")
    y = pd.Series(range(len(x))).to_numpy()

    x_train, y_train, x_val, y_val = split_time_series(x, y, 0.2)

    assert x_train[-1][0] < x_val[0][0]
    assert y_train[-1] < y_val[0]

    with pytest.raises(ValueError):
        split_time_series(x, y, 0)
    with pytest.raises(ValueError):
        split_time_series(x[:-1], y, 0.2)
