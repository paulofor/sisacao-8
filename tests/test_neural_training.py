from __future__ import annotations

import datetime as dt
import math

import numpy as np
import pandas as pd

from sisacao8.neural_dataset import build_training_dataset
from sisacao8.neural_training import (
    FEATURE_COLUMNS,
    BaselineMlpConfig,
    FeatureScaler,
    align_config_to_dataset,
    _build_model,
    apply_fold_drawdown_stop,
    apply_ticker_blocklist,
    apply_fold_trade_budget,
    build_artifact_manifest,
    build_muen_economics_from_predictions,
    conservative_directional_labels,
    encode_labels,
    evaluate_predictions,
    prepare_sequence_training_arrays,
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


def test_align_config_to_dataset_uses_snapshot_versions() -> None:
    dataset = pd.DataFrame(
        {
            "feature_version": ["feature_eod_tabular_v2", "feature_eod_tabular_v2"],
            "label_version": ["label_eod_barrier_v2", "label_eod_barrier_v2"],
        }
    )
    config = BaselineMlpConfig(feature_version="feature_eod_tabular_v3")

    aligned = align_config_to_dataset(config, dataset)

    assert aligned.feature_version == "feature_eod_tabular_v2"
    assert aligned.label_version == "label_eod_barrier_v2"


def test_prepare_training_arrays_scales_train_split_and_encodes_labels() -> None:
    dataset = _training_dataset()

    x_by_split, y_by_split, scaler = prepare_training_arrays(dataset)

    assert "train" in x_by_split
    assert x_by_split["train"].shape[1] == len(FEATURE_COLUMNS)
    assert y_by_split["train"].dtype == np.int64
    assert scaler.feature_columns == FEATURE_COLUMNS


def test_prepare_sequence_training_arrays_materializes_point_in_time_windows() -> None:
    dataset = _training_dataset()

    x_by_split, y_by_split, scaler, materialized = prepare_sequence_training_arrays(
        dataset, sequence_lookback=20
    )

    assert "train" in x_by_split
    assert x_by_split["train"].ndim == 3
    assert x_by_split["train"].shape[1:] == (20, len(FEATURE_COLUMNS))
    assert y_by_split["train"].dtype == np.int64
    assert scaler.feature_columns == FEATURE_COLUMNS
    assert len(materialized) == sum(len(values) for values in y_by_split.values())


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


def test_conservative_directional_labels_requires_confidence_and_margin() -> None:
    probabilities = np.array(
        [
            [0.48, 0.47, 0.05],  # SELL: clears probability but not margin
            [0.51, 0.40, 0.09],  # SELL: clears both
            [0.10, 0.45, 0.49],  # BUY: clears probability but not margin
            [0.10, 0.30, 0.60],  # BUY: clears both
            [0.20, 0.60, 0.20],  # Neutral is dominant
        ]
    )

    labels = conservative_directional_labels(
        probabilities, min_directional_probability=0.45, min_directional_margin=0.05
    )

    assert labels.tolist() == ["neutral", "down", "neutral", "up", "neutral"]


def test_apply_fold_trade_budget_keeps_strongest_directional_rows() -> None:
    labels = np.array(["up", "down", "up", "neutral"], dtype=object)
    probabilities = np.array(
        [
            [0.10, 0.20, 0.70],
            [0.72, 0.18, 0.10],
            [0.10, 0.40, 0.50],
            [0.10, 0.80, 0.10],
        ]
    )

    capped = apply_fold_trade_budget(
        labels,
        probabilities,
        max_trades_per_fold=2,
    )

    assert capped.tolist() == ["up", "down", "neutral", "neutral"]


def test_build_model_supports_phase3_architecture_types():
    import pytest

    tf = pytest.importorskip("tensorflow")

    for architecture_type in [
        "mlp",
        "residual_mlp",
        "wide_deep_mlp",
        "tabular_bottleneck_mlp",
        "gru_sequence",
        "lstm_sequence",
        "tcn_sequence",
    ]:
        config = BaselineMlpConfig(
            model_id=f"test_{architecture_type}",
            architecture_type=architecture_type,
            hidden_units=(16, 8),
            epochs=1,
        )
        input_shape = (
            (20, len(FEATURE_COLUMNS))
            if "sequence" in architecture_type
            else len(FEATURE_COLUMNS)
        )
        model = _build_model(input_shape, config)

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
                "dataset_split": "validation",
                "reference_date": dt.date(2026, 1, 5),
                "ticker": "CCC3",
                "label_class": "up",
                "buy_net_return": -0.50,
                "sell_net_return": -0.20,
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
        "validation": np.array(
            [
                [0.1, 0.1, 0.8],
                [0.8, 0.1, 0.1],
                [0.44, 0.40, 0.16],
            ]
        ),
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
    assert economics["daily_returns"][0]["ticker"] == "AAA3"
    assert {row["ticker"] for row in economics["daily_returns"]} >= {"AAA3", "BBB4"}


def test_build_muen_economics_family_hash_override_without_dates() -> None:
    dataset = pd.DataFrame(
        [
            {
                "dataset_split": "validation",
                "label_class": "up",
                "buy_net_return": 0.03,
                "sell_net_return": -0.02,
            },
            {
                "dataset_split": "test",
                "label_class": "down",
                "buy_net_return": -0.01,
                "sell_net_return": 0.02,
            },
        ]
    )
    probabilities = {
        "validation": np.array([[0.1, 0.1, 0.8]]),
        "test": np.array([[0.8, 0.1, 0.1]]),
    }
    config = BaselineMlpConfig(
        model_version="model_seed_1",
        candidate_family_hash="family_tabular_p50_m08_t35",
    )

    economics = build_muen_economics_from_predictions(
        dataset,
        probabilities,
        config=config,
    )

    assert economics["candidate_family_hash"] == "family_tabular_p50_m08_t35"
    assert economics["family_evaluation"]["candidate_family_hash"] == (
        "family_tabular_p50_m08_t35"
    )


def test_build_muen_economics_applies_max_trades_per_fold_budget() -> None:
    dataset = pd.DataFrame(
        [
            {
                "dataset_split": "validation",
                "reference_date": dt.date(2026, 1, day),
                "ticker": f"AAA{day}",
                "label_class": "up",
                "buy_net_return": 0.01 * day,
                "sell_net_return": -0.01,
            }
            for day in range(1, 5)
        ]
    )
    probabilities = {
        "validation": np.array(
            [
                [0.10, 0.20, 0.70],
                [0.68, 0.20, 0.12],
                [0.10, 0.35, 0.55],
                [0.52, 0.40, 0.08],
            ]
        )
    }
    config = BaselineMlpConfig(
        model_version="risk_capped",
        min_directional_probability=0.45,
        min_directional_margin=0.05,
        max_trades_per_fold=2,
    )

    economics = build_muen_economics_from_predictions(
        dataset,
        probabilities,
        config=config,
        cost_multipliers=(1.0,),
    )

    assert economics["fold_metrics"][0]["trades"] == 2
    assert economics["family_evaluation"]["total_trades"] == 2


def test_apply_ticker_blocklist_neutralizes_tail_tickers() -> None:
    labels = np.array(["up", "down", "up", "neutral"], dtype=object)
    frame = pd.DataFrame({"ticker": ["ONCO3", "PETR4", "brkm5", "CSAN3"]})

    adjusted = apply_ticker_blocklist(
        labels,
        frame,
        blocked_tickers=("onco3", "BRKM5"),
    )

    assert adjusted.tolist() == ["neutral", "down", "neutral", "neutral"]


def test_build_muen_economics_applies_ticker_blocklist_before_metrics() -> None:
    dataset = pd.DataFrame(
        [
            {
                "dataset_split": "validation",
                "reference_date": dt.date(2026, 1, day),
                "ticker": ticker,
                "label_class": "up",
                "buy_net_return": value,
                "sell_net_return": -value,
            }
            for day, ticker, value in [
                (1, "ONCO3", -0.07),
                (2, "PETR4", 0.03),
                (3, "BRKM5", -0.07),
            ]
        ]
    )
    probabilities = {"validation": np.array([[0.10, 0.20, 0.70]] * 3)}
    config = BaselineMlpConfig(
        model_version="ticker_guarded",
        min_directional_probability=0.45,
        min_directional_margin=0.05,
        blocked_tickers=("ONCO3", "BRKM5"),
    )

    economics = build_muen_economics_from_predictions(
        dataset,
        probabilities,
        config=config,
        cost_multipliers=(1.0,),
    )

    assert economics["fold_metrics"][0]["trades"] == 1
    assert math.isclose(economics["fold_metrics"][0]["total_net_return"], 0.03)


def test_apply_fold_drawdown_stop_neutralizes_after_breach() -> None:
    labels = np.array(["up", "up", "up", "up"], dtype=object)
    frame = pd.DataFrame(
        {
            "buy_net_return": [0.02, -0.20, 0.50, 0.50],
            "sell_net_return": [-0.02, 0.20, -0.50, -0.50],
        }
    )

    adjusted = apply_fold_drawdown_stop(
        labels,
        frame,
        max_fold_drawdown_stop=0.15,
    )

    assert adjusted.tolist() == ["up", "up", "neutral", "neutral"]


def test_build_muen_economics_applies_drawdown_stop_before_metrics() -> None:
    dataset = pd.DataFrame(
        [
            {
                "dataset_split": "validation",
                "reference_date": dt.date(2026, 1, day),
                "ticker": f"AAA{day}",
                "label_class": "up",
                "buy_net_return": value,
                "sell_net_return": -value,
            }
            for day, value in enumerate([0.02, -0.20, 0.50, 0.50], start=1)
        ]
    )
    probabilities = {"validation": np.array([[0.10, 0.20, 0.70]] * 4)}
    config = BaselineMlpConfig(
        model_version="drawdown_stopped",
        min_directional_probability=0.45,
        min_directional_margin=0.05,
        max_fold_drawdown_stop=0.15,
    )

    economics = build_muen_economics_from_predictions(
        dataset,
        probabilities,
        config=config,
        cost_multipliers=(1.0,),
    )

    assert economics["fold_metrics"][0]["trades"] == 2
    assert math.isclose(economics["fold_metrics"][0]["total_net_return"], -0.18)
