"""Cloud Function that generates end-of-day Sisacao-8 signals."""

from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Any, Dict, List

import pandas as pd  # type: ignore[import-untyped]
from google.cloud import bigquery  # type: ignore[import-untyped]

from sisacao8.candles import SAO_PAULO_TZ
from sisacao8.signals import (
    MODEL_VERSION,
    ConditionalSignal,
    compute_source_snapshot,
    generate_conditional_signals,
)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))

DATASET_ID = os.environ.get("BQ_INTRADAY_DATASET", "cotacao_intraday")
DAILY_TABLE_ID = os.environ.get("BQ_DAILY_TABLE", "candles_diarios")
SIGNALS_TABLE_ID = os.environ.get("BQ_SIGNALS_TABLE", "signals_eod_v0")
MIN_VOLUME = float(os.environ.get("MIN_SIGNAL_VOLUME", "0"))
EARLY_RUN = os.environ.get("ALLOW_EARLY_SIGNAL", "false").lower() == "true"

client = bigquery.Client()


def _now_sp() -> dt.datetime:
    return dt.datetime.now(tz=SAO_PAULO_TZ)


def _parse_request_date(request: Any) -> dt.date:
    if request and hasattr(request, "args") and request.args:
        requested = request.args.get("date")
        if requested:
            return dt.datetime.strptime(requested, "%Y-%m-%d").date()
    return _now_sp().date() - dt.timedelta(days=1)


def _ensure_after_cutoff() -> bool:
    if EARLY_RUN:
        return True
    local_now = _now_sp().time()
    return local_now >= dt.time(18, 0)


def _table_ref(table_id: str) -> str:
    return f"{client.project}.{DATASET_ID}.{table_id}"


def _fetch_daily_frame(reference_date: dt.date) -> pd.DataFrame:
    query = (
        "SELECT ticker, candle_datetime, open, close, high, low, volume, turnover_brl "
        f"FROM `{_table_ref(DAILY_TABLE_ID)}` "
        "WHERE reference_date = @ref_date"
    )
    params = [bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)]
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    df = client.query(query, job_config=job_config).to_dataframe()
    df.sort_values("ticker", inplace=True)
    return df


def _delete_partition(table_id: str, reference_date: dt.date) -> None:
    query = "DELETE FROM `" f"{table_id}" "` WHERE reference_date = @ref_date"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)
        ]
    )
    client.query(query, job_config=job_config).result()
    logging.info("Partição de %s removida em %s", reference_date, table_id)


def _next_business_day(date_value: dt.date) -> dt.date:
    next_day = date_value + dt.timedelta(days=1)
    while next_day.weekday() >= 5:
        next_day += dt.timedelta(days=1)
    return next_day


def _persist_signals(
    table_id: str,
    signals: List[ConditionalSignal],
    reference_date: dt.date,
    valid_for: dt.date,
    created_at: dt.datetime,
    source_snapshot: str,
    code_version: str,
) -> None:
    rows = [
        signal.to_bq_row(
            reference_date=reference_date,
            valid_for=valid_for,
            created_at=created_at,
            model_version=MODEL_VERSION,
            source_snapshot=source_snapshot,
            code_version=code_version,
        )
        for signal in signals
    ]
    if not rows:
        logging.warning("Nenhum sinal para gravar no BigQuery")
        return
    load_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    job = client.load_table_from_json(rows, table_id, job_config=load_config)
    job.result()
    logging.info("%s sinais gravados em %s", len(rows), table_id)


def generate_eod_signals(request: Any) -> Dict[str, Any]:
    """HTTP handler executed by Cloud Functions."""

    if not _ensure_after_cutoff():
        message = "Execução bloqueada antes do cutoff (18:00 BRT)."
        logging.warning(message)
        return {"status": "skipped", "reason": message}, 400

    reference_date = _parse_request_date(request)
    valid_for = _next_business_day(reference_date)
    logging.info("Gerando sinais para %s válidos em %s", reference_date, valid_for)

    frame = _fetch_daily_frame(reference_date)
    if frame.empty:
        message = f"Sem candles disponíveis para {reference_date}"
        logging.warning(message)
        return {"status": "empty", "reason": message}

    frame = frame.fillna(0)
    if MIN_VOLUME > 0:
        frame = frame[frame["volume"].fillna(0) >= MIN_VOLUME]
        logging.info(
            "Filtrando por volume mínimo %.0f: %s tickers", MIN_VOLUME, len(frame)
        )
        if frame.empty:
            return {"status": "filtered", "reason": "volume"}

    signals = generate_conditional_signals(frame)
    created_at = _now_sp()
    source_snapshot = compute_source_snapshot(frame.to_dict("records"))
    code_version = os.environ.get("CODE_VERSION", "local")
    response = {
        "date_ref": reference_date.isoformat(),
        "valid_for": valid_for.isoformat(),
        "model_version": MODEL_VERSION,
        "signals": [
            signal.to_dict(
                reference_date=reference_date,
                valid_for=valid_for,
                created_at=created_at,
                model_version=MODEL_VERSION,
                source_snapshot=source_snapshot,
                code_version=code_version,
            )
            for signal in signals
        ],
    }

    table_id = _table_ref(SIGNALS_TABLE_ID)
    _delete_partition(table_id, reference_date)
    _persist_signals(
        table_id,
        signals,
        reference_date,
        valid_for,
        created_at,
        source_snapshot,
        code_version,
    )

    response["stored"] = len(signals)
    return response
