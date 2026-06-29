from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from sisacao8.neural_dataset import build_training_dataset
from sisacao8.neural_training import (
    FEATURE_COLUMNS,
    BaselineMlpConfig,
    FeatureScaler,
    _build_model,
    build_artifact_manifest,
    build_muen_economics_from_predictions,
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


def test_build_model_supports_phase3_architecture_types():
    import pytest

    tf = pytest.importorskip("tensorflow")

    for architecture_type in [
        "mlp",
        "residual_mlp",
        "wide_deep_mlp",
        "tabular_bottleneck_mlp",
    ]:
        config = BaselineMlpConfig(
            model_id=f"test_{architecture_type}",
            architecture_type=architecture_type,
            hidden_units=(16, 8),
            epochs=1,
        )
        model = _build_model(len(FEATURE_COLUMNS), config)

        assert model.output_shape[-1] == 3
        assert isinstance(model.optimizer, tf.keras.optimizers.Adam)


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


def test_class_weight_balances_and_boosts_directional_classes() -> None:
    from sisacao8.neural_training import _class_weight

    y_train = encode_labels(pd.Series(["neutral", "neutral", "neutral", "up", "down"]))

    balanced = _class_weight(y_train, "balanced")
    directional = _class_weight(y_train, "directional")

    assert balanced is not None
    assert directional is not None
    neutral_index = 1
    up_index = 2
    assert balanced[up_index] > balanced[neutral_index]
    assert directional[up_index] > balanced[up_index]


def test_build_muen_economics_from_predictions_uses_non_train_splits() -> None:
    dataset = pd.DataFrame(
        [
            {
                "dataset_split": "train",
                "reference_date": dt.date(2026, 1, 1),
                "ticker": "AAA3",
                "label_class": "up",
                "buy_net_return": 0.10,
                "sell_net_return": -0.02,
            },
            {
                "dataset_split": "validation",
                "reference_date": dt.date(2026, 1, 2),
                "ticker": "AAA3",
                "label_class": "up",
                "buy_net_return": 0.08,
                "sell_net_return": -0.03,
            },
            {
                "dataset_split": "validation",
                "reference_date": dt.date(2026, 1, 3),
                "ticker": "BBB4",
                "label_class": "down",
                "buy_net_return": -0.01,
                "sell_net_return": 0.04,
            },
            {
                "dataset_split": "test",
                "reference_date": dt.date(2026, 1, 4),
                "ticker": "AAA3",
                "label_class": "neutral",
                "buy_net_return": -0.02,
                "sell_net_return": -0.01,
            },
        ]
    )
    probabilities = {
        "train": np.array([[0.1, 0.1, 0.8]]),
        "validation": np.array([[0.1, 0.1, 0.8], [0.8, 0.1, 0.1]]),
        "test": np.array([[0.1, 0.8, 0.1]]),
    }
    config = BaselineMlpConfig(model_version="model_v1", random_seed=123)

    economics = build_muen_economics_from_predictions(
        dataset,
        probabilities,
        config=config,
    )

    assert economics["protocol_version"] == "neural_eod_protocol_v1"
    assert economics["candidate_family_hash"] == "model_v1"
    assert economics["seed"] == 123
    assert len(economics["fold_metrics"]) == 4
    fold_ids = {item["fold_id"] for item in economics["fold_metrics"]}
    assert fold_ids == {
        "validation_cost_1_0",
        "validation_cost_1_5",
        "test_cost_1_0",
        "test_cost_1_5",
    }
    validation = next(
        item
        for item in economics["fold_metrics"]
        if item["fold_id"] == "validation_cost_1_0"
    )
    assert validation["trades"] == 2
    assert validation["expectancy_net"] == 0.06
    assert economics["family_evaluation"]["total_trades"] == 4
