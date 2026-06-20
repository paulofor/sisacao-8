from __future__ import annotations

import datetime as dt

import pandas as pd

from sisacao8.neural_dataset import (
    BarrierLabelConfig,
    TemporalSplitConfig,
    assign_temporal_splits,
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
    assert dataset["feature_version"].eq("feature_eod_tabular_v1").all()
    assert dataset["label_version"].eq("label_eod_barrier_v1").all()
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
