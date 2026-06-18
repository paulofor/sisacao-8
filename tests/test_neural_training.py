from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from sisacao8.neural_dataset import build_training_dataset
from sisacao8.neural_training import (
    BaselineMlpConfig,
    FEATURE_COLUMNS,
    FeatureScaler,
    build_artifact_manifest,
    encode_labels,
    evaluate_predictions,
    prepare_training_arrays,
)


def _training_dataset() -> pd.DataFrame:
    rows = []
    start = dt.date(2024, 1, 1)
    for ticker, offset in [("AAA3", 0), ("BBB4", 30)]:
        for day in range(90):
            close = 100 + offset + day * 0.3
            rows.append(
                {
                    "ticker": ticker,
                    "data_pregao": start + dt.timedelta(days=day),
                    "open": close - 0.5,
                    "high": close + 2.0,
                    "low": close - 2.0,
                    "close": close,
                    "volume": 1000 + day,
                }
            )
    return build_training_dataset(pd.DataFrame(rows), min_history_days=20)


def test_prepare_training_arrays_scales_train_split_and_encodes_labels() -> None:
    dataset = _training_dataset()

    x_by_split, y_by_split, scaler = prepare_training_arrays(dataset)

    assert "train" in x_by_split
    assert x_by_split["train"].shape[1] == len(FEATURE_COLUMNS)
    assert y_by_split["train"].dtype == np.int64
    assert scaler.feature_columns == FEATURE_COLUMNS


def test_evaluate_predictions_reports_confusion_and_coverage() -> None:
    y_true = encode_labels(pd.Series(["down", "neutral", "up", "up"]))
    probabilities = np.array(
        [
            [0.8, 0.1, 0.1],
            [0.2, 0.6, 0.2],
            [0.1, 0.2, 0.7],
            [0.7, 0.2, 0.1],
        ]
    )

    metrics = evaluate_predictions(y_true, probabilities)

    assert metrics["rows_count"] == 4
    assert metrics["coverage"] == 0.75
    assert metrics["directional_precision"] == 2 / 3
    assert metrics["confusion_matrix"] == [[1, 0, 0], [0, 1, 0], [1, 0, 1]]
    assert metrics["per_class"]["up"]["support"] == 2


def test_build_artifact_manifest_records_versions_metrics_and_dataset_hash() -> None:
    dataset = _training_dataset()
    train = dataset[dataset["dataset_split"].eq("train")]
    scaler = FeatureScaler.fit(train, FEATURE_COLUMNS)
    config = BaselineMlpConfig(epochs=1, batch_size=8)

    manifest = build_artifact_manifest(
        dataset=dataset,
        config=config,
        scaler=scaler,
        metrics={"test": {"accuracy": 0.5}},
        training_history={"loss": [1.0]},
        model_path="artifacts/neural_eod_mlp_v1_20260618/model.keras",
    )

    assert manifest["model_id"] == "neural_eod_mlp"
    assert manifest["model_version"] == "neural_eod_mlp_v1_20260618"
    assert manifest["feature_columns"] == FEATURE_COLUMNS
    assert manifest["dataset_snapshot"]
    assert manifest["metrics"] == {"test": {"accuracy": 0.5}}
