"""Cloud Function that builds 15m intraday candles from raw quotes."""

from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Any, Dict, List

import pandas as pd  # type: ignore[import-untyped]
from google.cloud import bigquery  # type: ignore[import-untyped]

if __package__:
    from .candles import SAO_PAULO_TZ
    from .intraday import build_intraday_candles, rollup_candles
    from .observability import StructuredLogger
else:
    from candles import SAO_PAULO_TZ
    from intraday import build_intraday_candles, rollup_candles
    from observability import StructuredLogger

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))

DATASET_ID = os.environ.get("BQ_INTRADAY_DATASET", "cotacao_intraday")
RAW_TABLE_ID = os.environ.get("BQ_INTRADAY_RAW_TABLE", "cotacao_b3")
CANDLES_15M_TABLE_ID = os.environ.get("BQ_INTRADAY_15M_TABLE", "candles_intraday_15m")
CANDLES_1H_TABLE_ID = os.environ.get("BQ_INTRADAY_1H_TABLE", "candles_intraday_1h")
AGGREGATE_HOURLY = os.environ.get("INTRADAY_ENABLE_HOURLY", "true").lower() == "true"
JOB_NAME = os.environ.get("JOB_NAME", "intraday_candles")

client = bigquery.Client()


def _now_sao_paulo() -> dt.datetime:
    return dt.datetime.now(tz=SAO_PAULO_TZ)


def _parse_request_date(request: Any) -> dt.date:
    if request and hasattr(request, "args") and request.args:
        requested = request.args.get("date")
        if requested:
            return dt.datetime.strptime(requested, "%Y-%m-%d").date()
    return _now_sao_paulo().date()


def _run_query(query: str, params: List[bigquery.ScalarQueryParameter]) -> pd.DataFrame:
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    logging.info("Executando consulta: %s", query)
    return client.query(query, job_config=job_config).to_dataframe()


def _table_ref(table_id: str) -> str:
    return f"{client.project}.{DATASET_ID}.{table_id}"


def _delete_partition(table_id: str, reference_date: dt.date) -> None:
    query = (
        "DELETE FROM `"
        f"{table_id}"
        "` WHERE reference_date = @ref_date"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)
        ]
    )
    client.query(query, job_config=job_config).result()
    logging.info("Partição %s removida de %s", reference_date, table_id)


def _load_rows(table_id: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        logging.warning("Nenhum candle para gravar em %s", table_id)
        return

    serialized_rows = [_json_ready_row(row) for row in rows]
    load_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    job = client.load_table_from_json(
        serialized_rows,
        table_id,
        job_config=load_config,
    )
    job.result()
    logging.info("%s linhas inseridas em %s", len(rows), table_id)


def _json_ready_row(row: Dict[str, Any]) -> Dict[str, Any]:
    serialized: Dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, dt.datetime):
            serialized[key] = value.isoformat()
        elif isinstance(value, dt.date):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


def generate_intraday_candles(request: Any) -> Dict[str, Any]:
    """HTTP entrypoint expected by Cloud Functions."""

    reference_date = _parse_request_date(request)
    run_logger = StructuredLogger(JOB_NAME)
    run_logger.update_context(date_ref=reference_date.isoformat())
    run_logger.started()
    logging.info("Gerando candles intraday para %s", reference_date)

    query = (
        "SELECT ticker, data, hora, valor "
        f"FROM `{_table_ref(RAW_TABLE_ID)}` "
        "WHERE data = @ref_date"
    )
    df = _run_query(
        query,
        [bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)],
    )
    if df.empty:
        run_logger.warn(
            "Nenhum dado intraday encontrado",
            reason="empty_source",
        )
        logging.warning("Nenhum dado intraday encontrado para %s", reference_date)
        return {"status": "empty", "reference_date": reference_date.isoformat()}

    candles = build_intraday_candles(df)
    rows = [candle.to_bq_row() for candle in candles]
    target_table = _table_ref(CANDLES_15M_TABLE_ID)
    _delete_partition(target_table, reference_date)
    _load_rows(target_table, rows)

    response: Dict[str, Any] = {
        "status": "ok",
        "reference_date": reference_date.isoformat(),
        "candles_15m": len(rows),
    }

    if AGGREGATE_HOURLY:
        hourly_candles = rollup_candles(candles)
        hourly_rows = [candle.to_bq_row() for candle in hourly_candles]
        hourly_table = _table_ref(CANDLES_1H_TABLE_ID)
        _delete_partition(hourly_table, reference_date)
        _load_rows(hourly_table, hourly_rows)
        response["candles_1h"] = len(hourly_rows)
    else:
        hourly_rows = []
        hourly_table = None

    run_logger.ok(
        "Candles intraday gravados",
        candles_15m=len(rows),
        candles_1h=response.get("candles_1h", 0),
        table_15m=target_table,
        table_1h=hourly_table,
    )
    return response
