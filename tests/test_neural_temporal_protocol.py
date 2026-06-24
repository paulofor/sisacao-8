from __future__ import annotations

import datetime as dt

import pandas as pd

from sisacao8.neural_dataset import (
    NestedWalkForwardConfig,
    assign_research_holdout_split,
    build_nested_walk_forward_plan,
)


def _dates(count: int) -> pd.Series:
    start = dt.date(2024, 1, 1)
    return pd.Series([start + dt.timedelta(days=offset) for offset in range(count)])


def test_build_nested_walk_forward_plan_blocks_holdout_and_embargoes_folds():
    config = NestedWalkForwardConfig(
        min_train_sessions=10,
        outer_folds=2,
        outer_test_sessions=5,
        calibration_sessions=3,
        embargo_sessions=2,
        locked_holdout_sessions=4,
    )

    plan = build_nested_walk_forward_plan(_dates(35), config)

    assert plan.locked_holdout_start == dt.date(2024, 2, 1)
    assert plan.locked_holdout_end == dt.date(2024, 2, 4)
    assert [fold.fold_id for fold in plan.folds] == ["fold_1", "fold_2"]
    first = plan.folds[0]
    assert first.train_sessions == 14
    assert first.calibration_sessions == 3
    assert first.outer_test_sessions == 5
    assert first.train_end < first.calibration_start
    assert (first.calibration_start - first.train_end).days == 3
    assert (first.outer_test_start - first.calibration_end).days == 3
    assert plan.folds[1].train_sessions > first.train_sessions


def test_assign_research_holdout_split_never_exposes_locked_holdout_to_research():
    config = NestedWalkForwardConfig(
        min_train_sessions=10,
        outer_folds=2,
        outer_test_sessions=5,
        calibration_sessions=3,
        embargo_sessions=2,
        locked_holdout_sessions=4,
    )

    splits = assign_research_holdout_split(_dates(35), config)

    assert splits.iloc[-4:].tolist() == ["locked_holdout"] * 4
    assert set(splits.iloc[:-4]) == {"research"}


def test_build_nested_walk_forward_plan_rejects_short_history():
    config = NestedWalkForwardConfig(
        min_train_sessions=10,
        outer_folds=2,
        outer_test_sessions=5,
        calibration_sessions=3,
        embargo_sessions=2,
        locked_holdout_sessions=4,
    )

    try:
        build_nested_walk_forward_plan(_dates(20), config)
    except ValueError as exc:
        assert "not enough sessions" in str(exc)
    else:
        raise AssertionError("expected ValueError")
