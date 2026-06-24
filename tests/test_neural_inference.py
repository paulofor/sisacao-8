import datetime as dt

import numpy as np
import pandas as pd

from sisacao8.neural_inference import (
    NeuralInferenceConfig,
    predict_neural_eod,
    suggested_action,
)
from sisacao8.neural_training import FEATURE_COLUMNS


class DummyModel:
    def predict(self, values, verbose=0):
        assert values.shape[1] == len(FEATURE_COLUMNS)
        return np.array(
            [
                [0.10, 0.20, 0.70],
                [0.65, 0.20, 0.15],
            ]
        )


def _candles():
    rows = []
    start = dt.date(2026, 1, 1)
    for ticker, base in [("AAA3", 10.0), ("BBB4", 20.0)]:
        for index in range(25):
            close = base + index * 0.1
            rows.append(
                {
                    "ticker": ticker,
                    "data_pregao": start + dt.timedelta(days=index),
                    "open": close * 0.99,
                    "high": close * 1.02,
                    "low": close * 0.98,
                    "close": close,
                    "volume": 1000 + index,
                    "financial_volume": close * (1000 + index),
                }
            )
    return pd.DataFrame(rows)


def _manifest():
    return {
        "model_id": "neural_eod_mlp",
        "model_version": "neural_eod_mlp_v1_20260618",
        "feature_version": "feature_eod_tabular_v1",
        "label_version": "label_eod_barrier_v2",
        "scaler": {
            "feature_columns": list(FEATURE_COLUMNS),
            "means": [0.0] * len(FEATURE_COLUMNS),
            "stds": [1.0] * len(FEATURE_COLUMNS),
        },
    }


def test_suggested_action_uses_directional_threshold():
    assert suggested_action(0.61, 0.20, 0.60) == ("BUY", 0.61)
    assert suggested_action(0.30, 0.62, 0.60) == ("SELL", 0.62)
    assert suggested_action(0.59, 0.58, 0.60) == ("HOLD", 0.59)


def test_predict_neural_eod_outputs_auditable_shadow_rows():
    predictions = predict_neural_eod(
        candles=_candles(),
        model=DummyModel(),
        manifest=_manifest(),
        reference_date=dt.date(2026, 1, 25),
        valid_for=dt.date(2026, 1, 26),
        job_run_id="run-1",
        config=NeuralInferenceConfig(decision_threshold=0.60),
    )

    assert list(predictions["suggested_action"]) == ["BUY", "SELL"]
    assert predictions["model_version"].unique().tolist() == [
        "neural_eod_mlp_v1_20260618"
    ]
    assert predictions["job_run_id"].unique().tolist() == ["run-1"]
    assert predictions["source_snapshot"].nunique() == 1
    assert predictions["feature_snapshot"].nunique() == 2
    assert np.allclose(
        predictions[["prob_down", "prob_neutral", "prob_up"]].sum(axis=1),
        1.0,
    )
