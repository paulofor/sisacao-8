from __future__ import annotations

import datetime as dt

import pandas as pd

from sisacao8.neural_dataset import (
    BarrierLabelConfig,
    TemporalSplitConfig,
    assign_temporal_splits,
    build_dataset_manifest,
    build_training_dataset,
)


def _candles() -> pd.DataFrame:
    rows = []
    start = dt.date(2024, 1, 1)
    for day in range(35):
        close = 100 + day
        rows.append(
            {
                "ticker": "TEST3",
                "data_pregao": start + dt.timedelta(days=day),
                "open": close - 0.5,
                "high": close + 2.0,
                "low": close - 2.0,
                "close": close,
                "volume": 1000 + day,
            }
        )
    return pd.DataFrame(rows)


def test_build_training_dataset_creates_features_labels_and_splits() -> None:
    dataset = build_training_dataset(
        _candles(),
        label_config=BarrierLabelConfig(horizon_days=3),
        split_config=TemporalSplitConfig(
            train_pct=0.5, validation_pct=0.25, embargo_days=1
        ),
        min_history_days=20,
    )

    assert not dataset.empty
    assert set(dataset["label_class"]).issubset({"up", "down", "neutral"})
    assert dataset["feature_version"].eq("feature_eod_tabular_v2").all()
    assert dataset["label_version"].eq("label_eod_barrier_v2").all()
    assert dataset["valid_for"].gt(dataset["reference_date"]).all()
    assert dataset["return_20d"].notna().any()
    assert dataset["dataset_split"].isin(["train", "validation", "test"]).any()


def test_assign_temporal_splits_leaves_embargo_gap() -> None:
    dates = pd.Series(pd.date_range("2024-01-01", periods=10, freq="D").date)
    splits = assign_temporal_splits(
        dates, TemporalSplitConfig(train_pct=0.5, validation_pct=0.3, embargo_days=1)
    )

    assert splits.iloc[0] == "train"
    assert pd.isna(splits.iloc[5])
    assert splits.iloc[6] == "validation"
    assert pd.isna(splits.iloc[8])
    assert splits.iloc[9] == "test"


def test_assign_temporal_splits_caps_embargo_for_short_windows() -> None:
    dates = pd.Series(pd.date_range("2024-03-30", periods=80, freq="D").date)

    splits = assign_temporal_splits(dates, TemporalSplitConfig(embargo_days=15))

    assert splits.eq("train").sum() == 52
    assert splits.eq("validation").sum() == 7
    assert splits.eq("test").sum() == 7
    assert splits.isna().sum() > 0


def test_label_v2_keeps_trade_open_after_entry_until_later_target() -> None:
    rows = []
    start = dt.date(2024, 1, 1)
    for day in range(25):
        rows.append(
            {
                "ticker": "TEST3",
                "data_pregao": start + dt.timedelta(days=day),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 1000,
            }
        )
    rows[20].update({"low": 98.0, "high": 100.0, "close": 99.0})
    rows[21].update({"low": 98.5, "high": 105.0, "close": 104.0})

    dataset = build_training_dataset(
        pd.DataFrame(rows),
        label_config=BarrierLabelConfig(
            entry_pct=0.02, target_pct=0.05, stop_pct=0.05, horizon_days=3
        ),
        min_history_days=20,
    )
    row = dataset[dataset["reference_date"].eq(dt.date(2024, 1, 20))].iloc[0]

    assert row["label_version"] == "label_eod_barrier_v2"
    assert row["label_class"] == "up"
    assert bool(row["entry_filled"]) is True
    assert row["exit_reason"] == "TARGET"
    assert row["holding_sessions"] == 2
    assert (
        row["execution_policy_version"] == "execution_eod_barrier_v2_conservative_daily"
    )


def test_dataset_manifest_records_phase2_point_in_time_controls() -> None:
    dataset = build_training_dataset(
        _candles(),
        label_config=BarrierLabelConfig(horizon_days=3, cost_pct=0.001),
        split_config=TemporalSplitConfig(
            train_pct=0.5, validation_pct=0.25, embargo_days=3
        ),
        min_history_days=20,
    )

    manifest = build_dataset_manifest(
        dataset,
        dataset_snapshot="snapshot_test",
        query_text="SELECT * FROM candles WHERE data_pregao <= @end_date",
        label_config=BarrierLabelConfig(horizon_days=3, cost_pct=0.001),
    ).to_json_dict()

    assert manifest["dataset_snapshot"] == "snapshot_test"
    assert manifest["protocol_version"] == "neural_eod_protocol_v1"
    assert manifest["feature_version"] == "feature_eod_tabular_v2"
    assert manifest["label_version"] == "label_eod_barrier_v2"
    assert manifest["universe_version"] == "b3_point_in_time_v1"
    assert len(manifest["query_hash"]) == 64
    assert len(manifest["code_hash"]) == 64
    assert manifest["rows"] == len(dataset)
    assert manifest["tickers"] == 1
    assert manifest["cost_assumptions"]["cost_pct"] == 0.001
    assert "embargo_rows" in manifest["quality_summary"]
