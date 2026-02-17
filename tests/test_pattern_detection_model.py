"""Tests for TensorFlow model helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import pytest

pytest.importorskip("tensorflow")

from functions.pattern_detection.data import (
    WindowConfig,
    prepare_training_data,
)
from functions.pattern_detection.model import (
    ModelConfig,
    predict_actions,
    train_model,
)


def _synthetic_dataset() -> tuple[np.ndarray, np.ndarray]:
    dates = pd.date_range("2024-01-01", periods=120, freq="D")
    base = np.linspace(10, 30, num=len(dates))
    # Introduce oscillations to force up/down signals.
    prices = base + np.sin(np.linspace(0, 12, num=len(dates))) * 3
    df = pd.DataFrame({"close": prices}, index=dates)
    config = WindowConfig(lookback=20, horizon=5, threshold=0.08)
    features, labels, _ = prepare_training_data(df, config)
    return features, labels


def test_train_model_returns_history() -> None:
    features, labels = _synthetic_dataset()
    config = ModelConfig(
        hidden_units=(32,),
        dropout=0.0,
        epochs=2,
        batch_size=16,
        validation_split=0.2,
        patience=1,
        learning_rate=1e-3,
    )

    model, history = train_model(features, labels, config)

    assert "loss" in history.history
    assert "val_loss" in history.history
    predictions = model.predict(features[-10:], verbose=0)
    assert predictions.shape == (10, 3)


def test_predict_actions_thresholding() -> None:
    features, labels = _synthetic_dataset()
    config = ModelConfig(
        hidden_units=(16,),
        dropout=0.0,
        epochs=1,
        batch_size=32,
        validation_split=0.3,
        patience=0,
        learning_rate=1e-3,
    )
    model, _ = train_model(features, labels, config)
    actions = predict_actions(model, features[-5:], threshold=0.4)
    assert actions.shape == (5,)
    assert set(actions).issubset({"buy", "sell", "hold"})
