"""TensorFlow models for price move classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple

import numpy as np
import tensorflow as tf  # type: ignore[import]

from .data import CLASS_NAMES, split_time_series


@dataclass(frozen=True)
class ModelConfig:
    """Hyperparameters for neural network training."""

    hidden_units: Sequence[int] = (64, 32)
    dropout: float = 0.2
    learning_rate: float = 1e-3
    epochs: int = 30
    batch_size: int = 32
    validation_split: float = 0.2
    patience: int = 5

    def __post_init__(self) -> None:
        if any(unit <= 0 for unit in self.hidden_units):
            msg = "All hidden_units must be positive"
            raise ValueError(msg)
        if not 0 <= self.dropout < 1:
            msg = "dropout must be in [0, 1)"
            raise ValueError(msg)
        if self.learning_rate <= 0:
            msg = "learning_rate must be positive"
            raise ValueError(msg)
        if self.epochs <= 0:
            msg = "epochs must be positive"
            raise ValueError(msg)
        if self.batch_size <= 0:
            msg = "batch_size must be positive"
            raise ValueError(msg)
        if not 0 < self.validation_split < 1:
            msg = "validation_split must be between 0 and 1"
            raise ValueError(msg)
        if self.patience < 0:
            msg = "patience must be non-negative"
            raise ValueError(msg)


def build_mlp_model(
    input_shape: Tuple[int, ...],
    num_classes: int = 3,
    hidden_units: Sequence[int] | None = None,
    dropout: float = 0.2,
    learning_rate: float = 1e-3,
) -> tf.keras.Model:
    """Build a dense neural network for multi-class classification."""

    units = hidden_units or (64, 32)
    inputs = tf.keras.Input(shape=input_shape)
    x = inputs
    for unit in units:
        x = tf.keras.layers.Dense(unit, activation="relu")(x)
        if dropout:
            x = tf.keras.layers.Dropout(dropout)(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
    model.compile(
        optimizer=optimizer,
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def train_model(
    features: np.ndarray,
    labels: np.ndarray,
    config: ModelConfig | None = None,
) -> Tuple[tf.keras.Model, tf.keras.callbacks.History]:
    """Train the neural network using chronological split."""

    cfg = config or ModelConfig()
    model = build_mlp_model(
        (features.shape[1],),
        hidden_units=cfg.hidden_units,
        dropout=cfg.dropout,
        learning_rate=cfg.learning_rate,
    )

    x_train, y_train, x_val, y_val = split_time_series(
        features, labels, cfg.validation_split
    )
    num_classes = len(CLASS_NAMES)
    y_train_cat = tf.keras.utils.to_categorical(
        y_train,
        num_classes=num_classes,
    )
    y_val_cat = tf.keras.utils.to_categorical(
        y_val,
        num_classes=num_classes,
    )

    callbacks: Iterable[tf.keras.callbacks.Callback] = []
    if cfg.patience:
        callbacks = (
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=cfg.patience,
                restore_best_weights=True,
            ),
        )

    history = model.fit(
        x_train,
        y_train_cat,
        validation_data=(x_val, y_val_cat),
        epochs=cfg.epochs,
        batch_size=cfg.batch_size,
        callbacks=list(callbacks),
        verbose=0,
        shuffle=False,
    )
    return model, history


def predict_actions(
    model: tf.keras.Model,
    features: np.ndarray,
    threshold: float = 0.5,
) -> np.ndarray:
    """Convert model probabilities into trading actions."""

    if not 0 < threshold < 1:
        msg = "threshold must be between 0 and 1"
        raise ValueError(msg)
    probabilities = model.predict(features, verbose=0)
    actions = []
    for probs in probabilities:
        down_prob, _, up_prob = probs
        if up_prob >= threshold:
            actions.append("buy")
        elif down_prob >= threshold:
            actions.append("sell")
        else:
            actions.append("hold")
    return np.asarray(actions)
