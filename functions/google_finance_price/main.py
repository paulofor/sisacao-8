"""Cloud Run function to fetch Google Finance prices."""

from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, Tuple

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


def google_finance_price(request: Any) -> Tuple[Dict[str, float | str], int]:
    """HTTP Cloud Run entry point returning latest price for a ticker."""

    ticker = request.args.get("ticker", "YDUQ3")
    logger.warning("Received request for ticker %s", ticker)
    brasil_tz = timezone("America/Sao_Paulo")
    now = datetime.datetime.now(brasil_tz)
    data_atual = now.strftime("%Y-%m-%d")
    hora_atual = now.strftime("%H:%M")
    data_hora_atual = now
    try:
        price = fetch_google_finance_price(ticker)
        logger.warning("Returning price %.2f for ticker %s", price, ticker)
        df = pd.DataFrame(
            [
                {
                    "ticker": ticker,
                    "data": data_atual,
                    "hora": hora_atual,
                    "valor": round(price, 2),
                    "hora_atual": hora_atual,
                    "data_hora_atual": data_hora_atual,
                }
            ]
        )
        append_dataframe_to_bigquery(df)
        return {"ticker": ticker, "price": price}, 200
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to fetch price for ticker %s: %s",
            ticker,
            exc,
            exc_info=True,
        )
        return {"error": str(exc)}, 500
