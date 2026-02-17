"""Utilities for training neural networks to detect price moves."""

from .data import (
    CLASS_NAMES,
    WindowConfig,
    prepare_training_data,
    split_time_series,
)
from .intraday import format_intraday_prices

try:
    from .model import (
        ModelConfig,
        build_mlp_model,
        predict_actions,
        train_model,
    )
except ModuleNotFoundError as exc:  # pragma: no cover
    if exc.name != "tensorflow":
        raise
    ModelConfig = None  # type: ignore[assignment]
    build_mlp_model = None  # type: ignore[assignment]
    predict_actions = None  # type: ignore[assignment]
    train_model = None  # type: ignore[assignment]

__all__ = [
    "CLASS_NAMES",
    "WindowConfig",
    "prepare_training_data",
    "split_time_series",
    "format_intraday_prices",
    "ModelConfig",
    "build_mlp_model",
    "train_model",
    "predict_actions",
]
