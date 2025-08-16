import datetime
import logging
import time
from typing import List

import pandas as pd
import yfinance as yf
from google.cloud import bigquery, storage
from pytz import timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

DATASET_ID = "cotacao_intraday"
TABELA_ID = "cotacao_bovespa"
BUCKET_NAME = "cotacao-intraday"
ARQUIVO_TICKER = "bovespa.csv"

# Timeout em segundos para requisições ao yfinance
TIMEOUT = 120

client = bigquery.Client()
storage_client = storage.Client()


def get_tickers_from_gcs() -> List[str]:
    """Read tickers list from a GCS bucket."""
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(ARQUIVO_TICKER)
        data = blob.download_as_text()
        tickers = [line.strip() for line in data.splitlines() if line.strip()]
        logging.info("Tickers lidos do GCS: %s", tickers)
        return tickers
    except Exception as exc:  # noqa: BLE001
        logging.error("Erro ao buscar tickers no GCS: %s", exc, exc_info=True)
        return []


def download_in_batches(
    tickers: List[str], batch_size: int = 10, pause: int = 10
) -> dict:
    """Download data from yfinance in batches."""
    all_data: dict = {}
    for i in range(0, len(tickers), batch_size):
        end_index = i + batch_size
        batch = tickers[i:end_index]
        logging.info("Buscando batch: %s", batch)
        try:
            params = {
                "tickers": batch,
                "period": "1d",
                "interval": "15m",
                "threads": False,
                "progress": False,
                "auto_adjust": False,
                "show_errors": False,
                "timeout": TIMEOUT,
            }
            logging.info("yfinance params: %s", params)
            batch_data = yf.download(
                batch,
                period="1d",
                interval="15m",
                group_by="ticker",
                threads=False,
                progress=False,
                auto_adjust=False,
                show_errors=False,
                timeout=TIMEOUT,
            )
            if isinstance(batch_data.columns, pd.MultiIndex):
                for ticker in batch:
                    if ticker in batch_data.columns.levels[0]:
                        all_data[ticker] = batch_data[ticker].dropna()
            else:
                ticker = batch[0]
                all_data[ticker] = batch_data.dropna()
            row_counts = {}
            for t in batch:
                row_counts[t] = len(all_data.get(t, pd.DataFrame()))
            logging.info("Batch %s retornou linhas: %s", batch, row_counts)
        except Exception as exc:  # noqa: BLE001
            logging.warning(
                "Erro ao baixar dados do batch %s: %s",
                batch,
                exc,
                exc_info=True,
            )
        time.sleep(pause)
    return all_data


def append_dataframe_to_bigquery(df: pd.DataFrame) -> None:
    """Append a DataFrame to BigQuery table."""
    try:
        if "data" in df.columns:
            df["data"] = pd.to_datetime(df["data"]).dt.date
        if "hora" in df.columns:
            df["hora"] = pd.to_datetime(df["hora"], format="%H:%M").dt.time
        if "hora_atual" in df.columns:
            hora_atual_col = pd.to_datetime(df["hora_atual"], format="%H:%M")
            df["hora_atual"] = hora_atual_col.dt.time
        if "data_hora_atual" in df.columns:
            df["data_hora_atual"] = pd.to_datetime(df["data_hora_atual"])

        tabela_id = f"{client.project}.{DATASET_ID}.{TABELA_ID}"
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
        logging.info(
            "DataFrame com %s linhas inserido com sucesso no BigQuery.",
            len(df),
        )
    except Exception as exc:  # noqa: BLE001
        logging.error(
            "Erro ao inserir dados no BigQuery: %s",
            exc,
            exc_info=True,
        )


def get_stock_data(request):
    """Entry point for the Cloud Function."""
    tickers = get_tickers_from_gcs()
    if not tickers:
        return "Nenhum ticker encontrado no GCS."

    try:
        logging.info("Iniciando download de %s tickers...", len(tickers))
        data_dict = download_in_batches(tickers, batch_size=10, pause=10)
        logging.info(
            "Download concluído: %s tickers com dados",
            len(data_dict),
        )

        if not data_dict:
            logging.warning("Nenhum dado foi retornado pelo yfinance.")
            return "No data fetched"

        brasil_tz = timezone("America/Sao_Paulo")
        hora_atual = datetime.datetime.now(brasil_tz).strftime("%H:%M")
        data_atual = datetime.datetime.now(brasil_tz).strftime("%Y-%m-%d")
        data_hora_atual = datetime.datetime.now(brasil_tz)

        rows = []

        for ticker in tickers:
            ticker_data = data_dict.get(ticker)
            try:
                if ticker_data is not None and not ticker_data.empty:
                    ult_value = ticker_data["Close"].iloc[-1]
                    timestamp = ticker_data.index[-1]

                    if timestamp.tzinfo is None:
                        timestamp = timestamp.tz_localize("UTC")
                    timestamp_brt = timestamp.tz_convert("America/Sao_Paulo")

                    date_str = timestamp_brt.strftime("%Y-%m-%d")
                    time_str = timestamp_brt.strftime("%H:%M")

                    rows.append(
                        {
                            "ticker": ticker,
                            "data": date_str,
                            "hora": time_str,
                            "valor": round(ult_value, 2),
                            "hora_atual": hora_atual,
                            "data_hora_atual": data_hora_atual,
                        }
                    )
                else:
                    logging.warning("Dados não disponíveis para %s", ticker)
                    rows.append(
                        {
                            "ticker": ticker,
                            "data": data_atual,
                            "hora": None,
                            "valor": -1,
                            "hora_atual": hora_atual,
                            "data_hora_atual": data_hora_atual,
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                logging.warning("Erro ao processar %s: %s", ticker, exc)
                rows.append(
                    {
                        "ticker": ticker,
                        "data": data_atual,
                        "hora": None,
                        "valor": -1,
                        "hora_atual": hora_atual,
                        "data_hora_atual": data_hora_atual,
                    }
                )

        df = pd.DataFrame(rows)
        logging.info(
            "DataFrame final com %s linhas será enviado ao BigQuery.",
            len(df),
        )
        append_dataframe_to_bigquery(df)

        return "Success"

    except Exception as exc:  # noqa: BLE001
        logging.error("Erro geral: %s", exc, exc_info=True)
        return f"Erro geral: {exc}"
