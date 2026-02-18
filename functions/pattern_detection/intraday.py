"""Helpers for preparing intraday price data for model training."""

from __future__ import annotations

from typing import Iterable

import pandas as pd  # type: ignore[import-untyped]


def format_intraday_prices(
    data: pd.DataFrame,
    *,
    date_column: str = "data",
    time_column: str = "hora",
    price_column: str = "valor",
    timezone: str | None = "America/Sao_Paulo",
    dropna: bool = True,
    deduplicate: bool = True,
) -> pd.DataFrame:
    """Return a DataFrame indexed by intraday timestamps.

    Parameters
    ----------
    data:
        Raw DataFrame fetched from ``cotacao_intraday.cotacao_b3`` or a
        similar source containing the ``date``/``time`` columns.
    date_column:
        Name of the column containing the trade date (``YYYY-MM-DD``).
    time_column:
        Name of the column containing the time of the quote (``HH:MM:SS``).
    price_column:
        Column with the numeric price that will feed the training pipeline.
    timezone:
        Optional timezone to localize the combined timestamp. Use ``None`` to
        keep naive timestamps.
    dropna:
        When ``True`` (default), rows with invalid timestamps or price values
        are removed from the result.
    deduplicate:
        When ``True`` (default), keep only the last occurrence for duplicated
        timestamps to ensure a strictly increasing index.

    Returns
    -------
    pandas.DataFrame
        A copy of ``data`` indexed by the combined timestamp, sorted in
        chronological order and ready to be consumed by
        :func:`prepare_training_data`.

    Raises
    ------
    KeyError
        If ``date_column``, ``time_column`` or ``price_column`` is missing.
    """

    required_columns: Iterable[str] = (date_column, time_column, price_column)
    missing = [
        column
        for column in required_columns
        if column not in data.columns
    ]
    if missing:
        missing_str = ", ".join(missing)
        msg = f"Missing required columns: {missing_str}"
        raise KeyError(msg)

    df = data.copy()
    combined = pd.to_datetime(
        df[date_column].astype(str) + " " + df[time_column].astype(str),
        errors="coerce",
    )

    if timezone:
        combined = combined.dt.tz_localize(
            timezone,
            ambiguous="NaT",
            nonexistent="NaT",
        )

    df[price_column] = pd.to_numeric(df[price_column], errors="coerce")

    if dropna:
        valid_mask = combined.notna() & df[price_column].notna()
        df = df.loc[valid_mask].copy()
        combined = combined[valid_mask]

    df.index = combined

    if deduplicate:
        df = df[~df.index.duplicated(keep="last")]

    df.sort_index(inplace=True)
    return df
