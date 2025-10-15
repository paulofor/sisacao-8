"""Tests for intraday dataset helpers."""

from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]
import pytest

from functions.pattern_detection import format_intraday_prices
from functions.pattern_detection.data import WindowConfig, prepare_training_data


@pytest.fixture()
def intraday_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "data": [
                "2024-05-02",
                "2024-05-02",
                "2024-05-01",
                "2024-05-02",
                "2024-05-02",
            ],
            "hora": [
                "10:00:00",
                "09:00:00",
                "17:30:00",
                "10:00:00",
                "11:00:00",
            ],
            "valor": ["10.0", "9.5", "11.0", "10.2", "10.5"],
            "ticker": ["PETR4", "PETR4", "PETR4", "PETR4", "PETR4"],
        }
    )


def test_format_intraday_prices_sorts_and_localizes(intraday_frame: pd.DataFrame) -> None:
    formatted = format_intraday_prices(intraday_frame)

    assert list(formatted.index) == sorted(list(formatted.index))
    assert formatted.index.tz is not None
    # duplicated timestamp resolved by keeping last entry
    duplicated_timestamp = pd.Timestamp("2024-05-02 10:00:00", tz="America/Sao_Paulo")
    assert formatted.loc[duplicated_timestamp, "valor"] == pytest.approx(10.2)
    assert formatted["valor"].dtype.kind == "f"


def test_format_intraday_prices_keeps_rows_valid_for_training(
    intraday_frame: pd.DataFrame,
) -> None:
    intraday_frame.loc[1, "hora"] = "invalid"
    formatted = format_intraday_prices(intraday_frame)

    config = WindowConfig(lookback=1, horizon=1, price_column="valor")
    features, labels, index = prepare_training_data(formatted, config)

    assert features.shape[0] == labels.shape[0] == len(index)
    assert (index.to_series().diff().dropna() > pd.Timedelta(0)).all()
