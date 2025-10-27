"""Cloud Run function to fetch Google Finance prices."""

from __future__ import annotations

import datetime
import logging
from sys import version_info
from typing import Any, Dict, Iterable, List, Tuple

try:
    import pandas as pd  # type: ignore[import-untyped]
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    pd = None  # type: ignore[assignment]
from google.cloud import bigquery  # type: ignore[import-untyped]

if version_info >= (3, 9):  # pragma: no branch - runtime dependent import
    from zoneinfo import ZoneInfo
else:  # pragma: no branch - runtime dependent import
    from backports.zoneinfo import ZoneInfo  # type: ignore[import-untyped]

try:
    from pytz import timezone  # type: ignore[import-untyped]
except ModuleNotFoundError:  # pragma: no cover - fallback when pytz is absent

    def timezone(name: str) -> ZoneInfo:  # type: ignore[misc]
        """Return ``ZoneInfo`` instance mimicking :func:`pytz.timezone`."""

        return ZoneInfo(name)

try:
    from .google_scraper import fetch_google_finance_price
except ImportError:  # pragma: no cover - fallback when executed as script
    from importlib import import_module

    google_scraper = import_module(
        "functions.google_finance_price.google_scraper"
    )
    fetch_google_finance_price = google_scraper.fetch_google_finance_price

logger = logging.getLogger(__name__)

DATASET_ID = "cotacao_intraday"
TABELA_ID = "cotacao_bovespa"

client = bigquery.Client()


def _normalize_time_value(raw_value: Any) -> str:
    """Return a BigQuery compatible ``TIME`` value."""

    if isinstance(raw_value, datetime.time):
        return raw_value.strftime("%H:%M:%S")
    value = str(raw_value)
    if len(value) == 5:
        return f"{value}:00"
    if len(value) == 8:
        return value
    return value


def _normalize_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert iterable of rows into BigQuery friendly dictionaries."""

    normalized: List[Dict[str, Any]] = []
    for row in rows:
        record = dict(row)
        data_value = record.get("data")
        if isinstance(data_value, datetime.date):
            record["data"] = data_value.isoformat()
        hora_value = record.get("hora")
        if hora_value is not None:
            record["hora"] = _normalize_time_value(hora_value)
        hora_atual_value = record.get("hora_atual")
        if hora_atual_value is not None:
            record["hora_atual"] = _normalize_time_value(hora_atual_value)
        data_hora_value = record.get("data_hora_atual")
        if isinstance(data_hora_value, datetime.datetime):
            record["data_hora_atual"] = data_hora_value.isoformat()
        normalized.append(record)
    return normalized


def append_dataframe_to_bigquery(data: Any) -> None:
    """Append data to the BigQuery table accepting DataFrame or JSON rows."""

    try:
        tabela_id = f"{client.project}.{DATASET_ID}.{TABELA_ID}"
        logger.warning("Destination table: %s", tabela_id)
        job_config = bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField("ticker", "STRING"),
                bigquery.SchemaField("data", "DATE"),
                bigquery.SchemaField("hora", "TIME"),
                bigquery.SchemaField("valor", "FLOAT"),
                bigquery.SchemaField("hora_atual", "TIME"),
                bigquery.SchemaField("data_hora_atual", "DATETIME"),
            ],
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )

        inserted_rows: int
        if pd is not None and isinstance(data, pd.DataFrame):
            df = data.copy()
            logger.warning(
                "DataFrame received with %s rows and columns %s",
                len(df),
                list(df.columns),
            )
            if "data" in df.columns:
                df["data"] = pd.to_datetime(df["data"]).dt.date
            if "hora" in df.columns:
                df["hora"] = pd.to_datetime(df["hora"], format="%H:%M").dt.time
            if "hora_atual" in df.columns:
                hora_atual_col = pd.to_datetime(
                    df["hora_atual"],
                    format="%H:%M",
                )
                df["hora_atual"] = hora_atual_col.dt.time
            if "data_hora_atual" in df.columns:
                df["data_hora_atual"] = pd.to_datetime(df["data_hora_atual"])

            job = client.load_table_from_dataframe(
                df,
                tabela_id,
                job_config=job_config,
            )
            inserted_rows = len(df)
        else:
            rows = list(data) if not isinstance(data, list) else data
            logger.warning(
                "Received %s rows without pandas installed", len(rows)
            )
            normalized_rows = _normalize_rows(rows)
            job = client.load_table_from_json(
                normalized_rows,
                tabela_id,
                job_config=job_config,
            )
            inserted_rows = len(rows)
        job.result()
        logger.warning(
            "Data inserted successfully into BigQuery (%s rows).",
            inserted_rows,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to insert data into BigQuery: %s",
            exc,
            exc_info=True,
        )


def fetch_active_tickers() -> List[str]:
    """Return list of active tickers from ``acao_bovespa`` table."""
    table_id = f"{client.project}.{DATASET_ID}.acao_bovespa"
    query = f"SELECT ticker FROM `{table_id}` WHERE ativo = TRUE"
    try:
        query_job = client.query(query)
        if pd is not None:
            df = query_job.to_dataframe()
            return df["ticker"].astype(str).tolist()
        results = query_job.result()
        return [str(row["ticker"]) for row in results]
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to fetch active tickers: %s",
            exc,
            exc_info=True,
        )
        raise


def google_finance_price(request: Any) -> Tuple[Dict[str, Any], int]:
    """HTTP Cloud Run entry point returning latest prices for active
    tickers."""

    brasil_tz = timezone("America/Sao_Paulo")
    now = datetime.datetime.now(brasil_tz)
    data_atual = now.strftime("%Y-%m-%d")
    hora_atual = now.strftime("%H:%M")
    data_hora_atual = now

    try:
        tickers = fetch_active_tickers()
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}, 500

    rows = []
    errors: List[str] = []
    for ticker in tickers:
        try:
            price = fetch_google_finance_price(ticker)
            rows.append(
                {
                    "ticker": ticker,
                    "data": data_atual,
                    "hora": hora_atual,
                    "valor": round(price, 2),
                    "hora_atual": hora_atual,
                    "data_hora_atual": data_hora_atual,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to fetch price for ticker %s: %s",
                ticker,
                exc,
                exc_info=True,
            )
            errors.append(str(exc))

    if rows:
        if pd is not None:
            df = pd.DataFrame(rows)
            append_dataframe_to_bigquery(df)
        else:
            logger.warning(
                "Pandas is not installed. Loading %s rows using JSON payload.",
                len(rows),
            )
            append_dataframe_to_bigquery(rows)

    if rows:
        return {"tickers": tickers, "processed": len(rows)}, 200

    return {"error": "; ".join(errors) or "No tickers processed"}, 500
