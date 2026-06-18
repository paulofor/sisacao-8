"""Baseline MLP training helpers for neural EOD signals.

This module keeps model training reproducible and auditable. It consumes the
supervised dataset produced by :mod:`sisacao8.neural_dataset`, trains a small
TensorFlow/Keras MLP, evaluates chronological splits and writes a versioned
artifact manifest next to the saved model.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from sisacao8.neural_dataset import FEATURE_VERSION, LABEL_VERSION

LABEL_CLASSES: tuple[str, ...] = ("down", "neutral", "up")
MODEL_ID = "neural_eod_mlp"
MODEL_VERSION = "neural_eod_mlp_v1_20260618"

FEATURE_COLUMNS: tuple[str, ...] = (
    "open",
    "high",
    "low",
    "close",
    "volume",
    "financial_volume",
    "return_5d",
    "return_10d",
    "return_20d",
    "volatility_10d",
    "volatility_20d",
    "daily_range_pct",
    "intraday_return_pct",
    "gap_open_pct",
    "financial_volume_z20",
    "volume_ratio_20d",
    "distance_high_20d_pct",
    "distance_low_20d_pct",
    "distance_sma_20d_pct",
)


@dataclass(frozen=True)
class BaselineMlpConfig:
    """Hyperparameters for the first auditable EOD MLP baseline."""

    model_id: str = MODEL_ID
    model_version: str = MODEL_VERSION
    feature_version: str = FEATURE_VERSION
    label_version: str = LABEL_VERSION
    hidden_units: tuple[int, ...] = (64, 32)
    dropout_rate: float = 0.15
    learning_rate: float = 0.001
    epochs: int = 40
    batch_size: int = 256
    validation_split_name: str = "validation"
    test_split_name: str = "test"
    random_seed: int = 42

    def __post_init__(self) -> None:
        if not self.hidden_units:
            raise ValueError("hidden_units must have at least one layer")
        if any(unit <= 0 for unit in self.hidden_units):
            raise ValueError("hidden_units must be positive")
        if not 0 <= self.dropout_rate < 1:
            raise ValueError("dropout_rate must be in the [0, 1) range")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if self.epochs <= 0:
            raise ValueError("epochs must be positive")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")


@dataclass(frozen=True)
class FeatureScaler:
    """Simple standard scaler persisted with the model manifest."""

    feature_columns: tuple[str, ...]
    means: tuple[float, ...]
    stds: tuple[float, ...]

    @classmethod
    def fit(
        cls, frame: pd.DataFrame, feature_columns: tuple[str, ...]
    ) -> "FeatureScaler":
        values = frame.loc[:, feature_columns].apply(pd.to_numeric, errors="coerce")
        means = values.mean(axis=0).fillna(0.0)
        stds = values.std(axis=0).replace(0.0, 1.0).fillna(1.0)
        return cls(
            feature_columns=feature_columns,
            means=tuple(float(value) for value in means.to_numpy()),
            stds=tuple(float(value) for value in stds.to_numpy()),
        )

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        values = frame.loc[:, self.feature_columns].apply(
            pd.to_numeric, errors="coerce"
        )
        values = values.fillna(dict(zip(self.feature_columns, self.means)))
        means = np.array(self.means, dtype=np.float32)
        stds = np.array(self.stds, dtype=np.float32)
        return ((values.to_numpy(dtype=np.float32) - means) / stds).astype(np.float32)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def prepare_training_arrays(
    dataset: pd.DataFrame,
    feature_columns: tuple[str, ...] = FEATURE_COLUMNS,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], FeatureScaler]:
    """Return scaled X/y arrays grouped by chronological dataset split."""

    _validate_dataset(dataset, feature_columns)
    train = dataset[dataset["dataset_split"].eq("train")].copy()
    if train.empty:
        raise ValueError("dataset must contain rows with dataset_split='train'")
    scaler = FeatureScaler.fit(train, feature_columns)
    x_by_split: dict[str, np.ndarray] = {}
    y_by_split: dict[str, np.ndarray] = {}
    for split_name, split_frame in dataset.dropna(subset=["dataset_split"]).groupby(
        "dataset_split", sort=False
    ):
        x_by_split[str(split_name)] = scaler.transform(split_frame)
        y_by_split[str(split_name)] = encode_labels(split_frame["label_class"])
    return x_by_split, y_by_split, scaler


def encode_labels(labels: pd.Series) -> np.ndarray:
    """Encode textual labels into stable integer class ids."""

    label_to_index = {label: index for index, label in enumerate(LABEL_CLASSES)}
    unknown = sorted(set(labels.dropna()) - set(label_to_index))
    if unknown:
        raise ValueError(f"Unknown label_class values: {unknown}")
    return labels.map(label_to_index).to_numpy(dtype=np.int64)


def train_baseline_mlp(
    dataset: pd.DataFrame,
    artifact_dir: str | Path,
    config: BaselineMlpConfig | None = None,
) -> dict[str, object]:
    """Train the baseline MLP and save a versioned Keras artifact + manifest."""

    config = config or BaselineMlpConfig()
    np.random.seed(config.random_seed)

    import tensorflow as tf

    tf.keras.utils.set_random_seed(config.random_seed)
    x_by_split, y_by_split, scaler = prepare_training_arrays(dataset)
    model = _build_model(x_by_split["train"].shape[1], config)
    validation_data = None
    if config.validation_split_name in x_by_split:
        validation_data = (
            x_by_split[config.validation_split_name],
            y_by_split[config.validation_split_name],
        )
    history = model.fit(
        x_by_split["train"],
        y_by_split["train"],
        validation_data=validation_data,
        epochs=config.epochs,
        batch_size=config.batch_size,
        verbose=0,
    )
    metrics = evaluate_probabilities_by_split(
        y_by_split,
        {
            split: model.predict(values, verbose=0)
            for split, values in x_by_split.items()
        },
    )
    output_dir = Path(artifact_dir) / config.model_version
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "model.keras"
    model.save(model_path)
    manifest = build_artifact_manifest(
        dataset=dataset,
        config=config,
        scaler=scaler,
        metrics=metrics,
        training_history={
            key: [float(item) for item in value]
            for key, value in history.history.items()
        },
        model_path=model_path,
    )
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return manifest


def evaluate_probabilities_by_split(
    y_true_by_split: dict[str, np.ndarray],
    probabilities_by_split: dict[str, np.ndarray],
) -> dict[str, object]:
    """Evaluate split metrics for class quality and directional coverage."""

    return {
        split: evaluate_predictions(y_true, probabilities_by_split[split])
        for split, y_true in y_true_by_split.items()
        if split in probabilities_by_split
    }


def evaluate_predictions(
    y_true: np.ndarray, probabilities: np.ndarray
) -> dict[str, object]:
    """Evaluate class probabilities against encoded labels."""

    if probabilities.ndim != 2 or probabilities.shape[1] != len(LABEL_CLASSES):
        raise ValueError("probabilities must have shape (n_rows, 3)")
    if len(y_true) != len(probabilities):
        raise ValueError("y_true and probabilities must have the same length")
    predicted = probabilities.argmax(axis=1)
    confusion = _confusion_matrix(y_true, predicted)
    per_class = _per_class_metrics(confusion)
    non_neutral_index = np.array([0, 2])
    directional_mask = np.isin(predicted, non_neutral_index)
    directional_total = int(directional_mask.sum())
    directional_hits = int(
        (predicted[directional_mask] == y_true[directional_mask]).sum()
    )
    return {
        "rows_count": int(len(y_true)),
        "coverage": _safe_divide(directional_total, len(y_true)),
        "directional_precision": _safe_divide(directional_hits, directional_total),
        "accuracy": _safe_divide(int((predicted == y_true).sum()), len(y_true)),
        "confusion_matrix": confusion.tolist(),
        "per_class": per_class,
    }


def build_artifact_manifest(
    dataset: pd.DataFrame,
    config: BaselineMlpConfig,
    scaler: FeatureScaler,
    metrics: dict[str, object],
    training_history: dict[str, list[float]],
    model_path: str | Path,
) -> dict[str, object]:
    """Create the immutable metadata recorded beside the saved model."""

    materialized = dataset.dropna(subset=["dataset_split"]).copy()
    return {
        "model_id": config.model_id,
        "model_version": config.model_version,
        "feature_version": config.feature_version,
        "label_version": config.label_version,
        "label_classes": LABEL_CLASSES,
        "feature_columns": FEATURE_COLUMNS,
        "hyperparameters": asdict(config),
        "dataset_snapshot": _dataset_snapshot(materialized),
        "dataset_rows": int(len(materialized)),
        "reference_date_min": _date_to_iso(materialized["reference_date"].min()),
        "reference_date_max": _date_to_iso(materialized["reference_date"].max()),
        "metrics": metrics,
        "training_history": training_history,
        "scaler": scaler.to_dict(),
        "artifact_path": str(model_path),
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def _build_model(input_size: int, config: BaselineMlpConfig) -> Any:
    import tensorflow as tf

    layers: list[Any] = [tf.keras.layers.Input(shape=(input_size,))]
    for units in config.hidden_units:
        layers.append(tf.keras.layers.Dense(units, activation="relu"))
        if config.dropout_rate > 0:
            layers.append(tf.keras.layers.Dropout(config.dropout_rate))
    layers.append(tf.keras.layers.Dense(len(LABEL_CLASSES), activation="softmax"))
    model = tf.keras.Sequential(layers, name=config.model_id)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=config.learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def _validate_dataset(dataset: pd.DataFrame, feature_columns: tuple[str, ...]) -> None:
    required = set(feature_columns) | {"dataset_split", "label_class", "reference_date"}
    missing = required.difference(dataset.columns)
    if missing:
        raise ValueError(f"Missing required training columns: {sorted(missing)}")
    versions = {
        "feature_version": FEATURE_VERSION,
        "label_version": LABEL_VERSION,
    }
    for column, expected in versions.items():
        if column in dataset and not dataset[column].dropna().eq(expected).all():
            raise ValueError(f"{column} must be {expected}")


def _confusion_matrix(y_true: np.ndarray, predicted: np.ndarray) -> np.ndarray:
    matrix = np.zeros((len(LABEL_CLASSES), len(LABEL_CLASSES)), dtype=np.int64)
    for true_value, predicted_value in zip(y_true, predicted):
        matrix[int(true_value), int(predicted_value)] += 1
    return matrix


def _per_class_metrics(confusion: np.ndarray) -> dict[str, dict[str, float]]:
    metrics: dict[str, dict[str, float]] = {}
    for index, label in enumerate(LABEL_CLASSES):
        true_positive = int(confusion[index, index])
        false_positive = int(confusion[:, index].sum() - true_positive)
        false_negative = int(confusion[index, :].sum() - true_positive)
        metrics[label] = {
            "precision": _safe_divide(true_positive, true_positive + false_positive),
            "recall": _safe_divide(true_positive, true_positive + false_negative),
            "f1": _f1_score(true_positive, false_positive, false_negative),
            "support": int(confusion[index, :].sum()),
        }
    return metrics


def _f1_score(true_positive: int, false_positive: int, false_negative: int) -> float:
    precision = _safe_divide(true_positive, true_positive + false_positive)
    recall = _safe_divide(true_positive, true_positive + false_negative)
    return _safe_divide(2 * precision * recall, precision + recall)


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def _dataset_snapshot(dataset: pd.DataFrame) -> str:
    columns = ["ticker", "reference_date", "dataset_split", "label_class"]
    available = [column for column in columns if column in dataset]
    payload = (
        dataset.loc[:, available]
        .sort_values(available)
        .to_json(date_format="iso", orient="records")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _date_to_iso(value: object) -> str | None:
    if pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()
