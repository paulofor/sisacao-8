"""Inference helpers for shadow-mode neural EOD predictions."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
import pandas as pd

from sisacao8.neural_dataset import FEATURE_VERSION, build_inference_features
from sisacao8.neural_training import (
    FEATURE_COLUMNS,
    FEATURE_COLUMNS_BY_VERSION,
    LABEL_CLASSES,
    FeatureScaler,
)

INFERENCE_CONFIG_VERSION = "neural_eod_inference_config_v1"
DEFAULT_DECISION_THRESHOLD = 0.60


@dataclass(frozen=True)
class NeuralInferenceConfig:
    """Versioned decision parameters used after model probabilities."""

    inference_config_version: str = INFERENCE_CONFIG_VERSION
    decision_threshold: float = DEFAULT_DECISION_THRESHOLD

    def __post_init__(self) -> None:
        if not 0 < self.decision_threshold < 1:
            raise ValueError("decision_threshold must be between 0 and 1")


def scaler_from_manifest(manifest: Mapping[str, Any]) -> FeatureScaler:
    """Rebuild the training scaler persisted in an artifact manifest."""

    scaler = manifest.get("scaler")
    if not isinstance(scaler, Mapping):
        raise ValueError("manifest must contain scaler metadata")
    columns = tuple(str(item) for item in scaler.get("feature_columns", ()))
    means = tuple(float(item) for item in scaler.get("means", ()))
    stds = tuple(float(item) for item in scaler.get("stds", ()))
    known_contracts = set(FEATURE_COLUMNS_BY_VERSION.values()) | {FEATURE_COLUMNS}
    if columns not in known_contracts:
        raise ValueError("manifest feature columns differ from inference contract")
    if len(means) != len(columns) or len(stds) != len(columns):
        raise ValueError("manifest scaler dimensions are invalid")
    return FeatureScaler(feature_columns=columns, means=means, stds=stds)


def predict_neural_eod(
    candles: pd.DataFrame,
    model: Any,
    manifest: Mapping[str, Any],
    reference_date: dt.date,
    valid_for: dt.date,
    job_run_id: str,
    config: NeuralInferenceConfig | None = None,
) -> pd.DataFrame:
    """Generate audit-ready prediction rows without creating operational signals."""

    config = config or NeuralInferenceConfig()
    scaler = scaler_from_manifest(manifest)
    features = build_inference_features(candles)
    features = features[
        pd.to_datetime(features["reference_date"]).dt.date.eq(reference_date)
    ]
    if features.empty:
        return _empty_predictions_frame()
    probabilities = np.asarray(model.predict(scaler.transform(features), verbose=0))
    if probabilities.shape != (len(features), len(LABEL_CLASSES)):
        raise ValueError("model probabilities must have shape (n_rows, 3)")
    probabilities = _normalize_probabilities(probabilities)
    created_at = dt.datetime.now(dt.timezone.utc)
    source_snapshot = compute_source_snapshot(features)
    rows: list[dict[str, Any]] = []
    for row, probs in zip(features.to_dict("records"), probabilities):
        prob_down, prob_neutral, prob_up = [float(value) for value in probs]
        action, confidence = suggested_action(
            prob_up, prob_down, config.decision_threshold
        )
        rows.append(
            {
                "reference_date": reference_date,
                "valid_for": valid_for,
                "ticker": row["ticker"],
                "model_id": str(manifest["model_id"]),
                "model_version": str(manifest["model_version"]),
                "feature_version": str(
                    manifest.get("feature_version", FEATURE_VERSION)
                ),
                "label_version": str(manifest.get("label_version", "")) or None,
                "inference_config_version": config.inference_config_version,
                "prob_up": prob_up,
                "prob_down": prob_down,
                "prob_neutral": prob_neutral,
                "suggested_action": action,
                "confidence": confidence,
                "decision_threshold": config.decision_threshold,
                "close": _optional_float(row.get("close")),
                "financial_volume": _optional_float(row.get("financial_volume")),
                "feature_snapshot": compute_feature_snapshot(
                    row, scaler.feature_columns
                ),
                "source_snapshot": source_snapshot,
                "job_run_id": job_run_id,
                "created_at": created_at,
                "metadata_json": json.dumps(
                    {
                        "history_days": row.get("history_days"),
                        "flags": {
                            "has_missing_ohlcv": bool(
                                row.get("has_missing_ohlcv", False)
                            ),
                            "has_zero_volume": bool(row.get("has_zero_volume", False)),
                            "is_suspicious_candle": bool(
                                row.get("is_suspicious_candle", False)
                            ),
                        },
                    },
                    sort_keys=True,
                ),
            }
        )
    return pd.DataFrame(rows)


def suggested_action(
    prob_up: float, prob_down: float, threshold: float
) -> tuple[str, float]:
    """Map directional probabilities to BUY, SELL or HOLD."""

    if prob_up >= threshold and prob_up >= prob_down:
        return "BUY", float(prob_up)
    if prob_down >= threshold and prob_down > prob_up:
        return "SELL", float(prob_down)
    return "HOLD", float(max(prob_up, prob_down))


def compute_source_snapshot(features: pd.DataFrame) -> str:
    """Hash the inference feature matrix used in a job run."""

    payload = features.sort_values(["reference_date", "ticker"]).to_json(
        date_format="iso", orient="records"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_feature_snapshot(
    row: Mapping[str, Any], feature_columns: tuple[str, ...] = FEATURE_COLUMNS
) -> str:
    """Hash one ticker/date feature vector for row-level audit."""

    payload = {
        column: _json_safe(row.get(column))
        for column in ("ticker", "reference_date", *feature_columns)
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _normalize_probabilities(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(probabilities.astype(float), 0.0, 1.0)
    totals = clipped.sum(axis=1, keepdims=True)
    if np.any(totals <= 0):
        raise ValueError("model returned zero probability mass for at least one row")
    return clipped / totals


def _optional_float(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def _empty_predictions_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "reference_date",
            "valid_for",
            "ticker",
            "model_id",
            "model_version",
            "feature_version",
            "label_version",
            "inference_config_version",
            "prob_up",
            "prob_down",
            "prob_neutral",
            "suggested_action",
            "confidence",
            "decision_threshold",
            "close",
            "financial_volume",
            "feature_snapshot",
            "source_snapshot",
            "job_run_id",
            "created_at",
            "metadata_json",
        ]
    )
