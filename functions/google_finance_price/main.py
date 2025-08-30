"""Cloud Run function to fetch Google Finance prices."""

from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, List, Tuple

import pandas as pd  # type: ignore[import-untyped]
from google.cloud import bigquery  # type: ignore[import-untyped]
from pytz import timezone  # type: ignore[import-untyped]

from .google_scraper import fetch_google_finance_price

logger = logging.getLogger(__name__)

DATASET_ID = "cotacao_intraday"
TABELA_ID = "cotacao_bovespa"

client = bigquery.Client()


def append_dataframe_to_bigquery(df: pd.DataFrame) -> None:
    """Append a DataFrame to the BigQuery table."""
    try:
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

        job = client.load_table_from_dataframe(
            df,
            tabela_id,
            job_config=job_config,
        )
        job.result()
        logger.warning(
            "DataFrame with %s rows inserted successfully into BigQuery.",
            len(df),
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
        df = client.query(query).to_dataframe()
        return df["ticker"].astype(str).tolist()
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
        df = pd.DataFrame(rows)
        append_dataframe_to_bigquery(df)

    if rows:
        return {"tickers": tickers, "processed": len(rows)}, 200

    return {"error": "; ".join(errors) or "No tickers processed"}, 500
