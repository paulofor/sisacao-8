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
    DEFAULT_HORIZON_DAYS,
    DEFAULT_RANKING_KEY,
    MODEL_VERSION,
    MAX_SIGNALS_PER_DAY,
    ConditionalSignal,
    compute_source_snapshot,
    generate_conditional_signals,
)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))

DATASET_ID = os.environ.get("BQ_INTRADAY_DATASET", "cotacao_intraday")
DAILY_TABLE_ID = os.environ.get("BQ_DAILY_TABLE", "cotacao_ohlcv_diario")
SIGNALS_TABLE_ID = os.environ.get("BQ_SIGNALS_TABLE", "sinais_eod")
FERIADOS_TABLE_ID = os.environ.get("BQ_HOLIDAYS_TABLE", "feriados_b3")
BACKTEST_METRICS_TABLE_ID = os.environ.get(
    "BQ_BACKTEST_METRICS_TABLE", "backtest_metrics"
)
MIN_VOLUME = float(os.environ.get("MIN_SIGNAL_VOLUME", "0"))
EARLY_RUN = os.environ.get("ALLOW_EARLY_SIGNAL", "false").lower() == "true"
X_PCT = float(os.environ.get("SIGNAL_X_PCT", os.environ.get("X_PCT", "0.02")))
TARGET_PCT = float(
    os.environ.get("SIGNAL_TARGET_PCT", os.environ.get("TARGET_PCT", "0.07"))
)
STOP_PCT = float(os.environ.get("SIGNAL_STOP_PCT", os.environ.get("STOP_PCT", "0.07")))
MAX_SIGNALS = min(
    MAX_SIGNALS_PER_DAY,
    max(1, int(os.environ.get("MAX_SIGNALS", str(MAX_SIGNALS_PER_DAY))))
)
ALLOW_SELL = os.environ.get("ALLOW_SELL_SIGNALS", "true").lower() == "true"
HORIZON_DAYS = int(os.environ.get("SIGNAL_HORIZON_DAYS", str(DEFAULT_HORIZON_DAYS)))
RANKING_KEY = os.environ.get("SIGNAL_RANKING_KEY", DEFAULT_RANKING_KEY)

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


def _holidays_table() -> str:
    return _table_ref(FERIADOS_TABLE_ID)


def _metrics_table() -> str:
    return _table_ref(BACKTEST_METRICS_TABLE_ID)


def _is_b3_holiday(date_value: dt.date) -> bool:
    query = (
        "SELECT 1 FROM `"
        f"{_holidays_table()}"
        "` WHERE data_feriado = @ref_date LIMIT 1"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("ref_date", "DATE", date_value)
        ]
    )
    try:
        rows = list(client.query(query, job_config=job_config).result())
    except Exception as exc:  # noqa: BLE001
        logging.warning("Falha ao consultar feriados B3: %s", exc, exc_info=True)
        return False
    return bool(rows)


def _is_trading_day(date_value: dt.date) -> bool:
    if date_value.weekday() >= 5:
        return False
    return not _is_b3_holiday(date_value)


def _next_business_day(date_value: dt.date) -> dt.date:
    next_day = date_value + dt.timedelta(days=1)
    while not _is_trading_day(next_day):
        next_day += dt.timedelta(days=1)
    return next_day


def _fetch_daily_frame(reference_date: dt.date) -> pd.DataFrame:
    query = (
        "SELECT ticker, data_pregao, open, close, high, low, volume_financeiro, qtd_negociada "
        f"FROM `{_table_ref(DAILY_TABLE_ID)}` "
        "WHERE data_pregao = @ref_date"
    )
    params = [bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)]
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    df = client.query(query, job_config=job_config).to_dataframe()
    df.sort_values("ticker", inplace=True)
    return df


def _fetch_latest_metrics() -> pd.DataFrame:
    table = _metrics_table()
    query = f"""
        WITH latest AS (
            SELECT MAX(as_of_date) AS as_of_date FROM `{table}`
        )
        SELECT ticker, side, win_rate, profit_factor
        FROM `{table}`
        WHERE as_of_date = (SELECT as_of_date FROM latest WHERE as_of_date IS NOT NULL)
    """
    try:
        return client.query(query).to_dataframe()
    except Exception as exc:  # noqa: BLE001
        logging.info("Backtest metrics indisponíveis: %s", exc)
        return pd.DataFrame()


def _delete_partition(table_id: str, reference_date: dt.date) -> None:
    query = (
        "DELETE FROM `"
        f"{table_id}"
        "` WHERE date_ref = @ref_date"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)
        ]
    )
    client.query(query, job_config=job_config).result()
    logging.info("Partição de %s removida em %s", reference_date, table_id)


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
    if not _is_trading_day(reference_date):
        message = f"{reference_date} não é dia útil da B3 (feriado/fim de semana)."
        logging.warning(message)
        return {"status": "skipped", "reason": message}

    valid_for = _next_business_day(reference_date)
    logging.info(
        (
            "Gerando sinais para %s válidos em %s | modelo=%s | X=%.2f%% | TP=%.2f%% | "
            "SL=%.2f%% | horizon=%sd | ranking=%s"
        ),
        reference_date,
        valid_for,
        MODEL_VERSION,
        X_PCT * 100,
        TARGET_PCT * 100,
        STOP_PCT * 100,
        HORIZON_DAYS,
        RANKING_KEY,
    )

    frame = _fetch_daily_frame(reference_date)
    if frame.empty:
        message = f"Sem candles disponíveis para {reference_date}"
        logging.warning(message)
        return {"status": "empty", "reason": message}

    frame = frame.fillna(0)
    if MIN_VOLUME > 0 and "volume_financeiro" in frame.columns:
        frame = frame[frame["volume_financeiro"].fillna(0) >= MIN_VOLUME]
        logging.info(
            "Filtrando por volume financeiro mínimo %.0f: %s tickers",
            MIN_VOLUME,
            len(frame),
        )
        if frame.empty:
            return {"status": "filtered", "reason": "volume"}

    limit = min(MAX_SIGNALS, MAX_SIGNALS_PER_DAY)
    metrics_df = _fetch_latest_metrics()
    signals = generate_conditional_signals(
        frame,
        top_n=limit,
        x_pct=X_PCT,
        target_pct=TARGET_PCT,
        stop_pct=STOP_PCT,
        allow_sell=ALLOW_SELL,
        horizon_days=HORIZON_DAYS,
        ranking_key=RANKING_KEY,
        backtest_metrics=metrics_df,
    )
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
        "requested": len(frame),
        "generated": len(signals),
        "ranking_key": RANKING_KEY,
        "horizon_days": HORIZON_DAYS,
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
    response["max_signals"] = limit
    return response
