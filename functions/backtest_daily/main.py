"""Cloud Function that simulates Sisacao-8 signals using daily OHLC prices."""

from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Any, Dict, List, Sequence

import pandas as pd  # type: ignore[import-untyped]
from google.cloud import bigquery  # type: ignore[import-untyped]

from backtest import (
    build_candle_lookup,
    build_signal_payloads,
    compute_metrics as compute_backtest_metrics,
    run_backtest,
)
from candles import SAO_PAULO_TZ
from observability import StructuredLogger

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))

DATASET_ID = os.environ.get("BQ_INTRADAY_DATASET", "cotacao_intraday")
DAILY_TABLE_ID = os.environ.get("BQ_DAILY_TABLE", "cotacao_ohlcv_diario")
SIGNALS_TABLE_ID = os.environ.get("BQ_SIGNALS_TABLE", "sinais_eod")
BACKTEST_TRADES_TABLE_ID = os.environ.get("BQ_BACKTEST_TRADES_TABLE", "backtest_trades")
BACKTEST_METRICS_TABLE_ID = os.environ.get(
    "BQ_BACKTEST_METRICS_TABLE", "backtest_metrics"
)
FERIADOS_TABLE_ID = os.environ.get("BQ_HOLIDAYS_TABLE", "feriados_b3")
METRICS_LOOKBACK_DAYS = int(os.environ.get("BACKTEST_METRICS_LOOKBACK_DAYS", "60"))
JOB_NAME = os.environ.get("JOB_NAME", "backtest_daily")

client = bigquery.Client()


def _now_sp() -> dt.datetime:
    return dt.datetime.now(tz=SAO_PAULO_TZ)


def _table_ref(table_id: str) -> str:
    return f"{client.project}.{DATASET_ID}.{table_id}"


def _holidays_table() -> str:
    return _table_ref(FERIADOS_TABLE_ID)


def _is_b3_holiday(date_value: dt.date) -> bool:
    query = (
        "SELECT 1 FROM `"
        f"{_holidays_table()}"
        "` WHERE data_feriado = @ref_date LIMIT 1"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("ref_date", "DATE", date_value)]
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


def _previous_trading_day(date_value: dt.date) -> dt.date:
    candidate = date_value
    while True:
        candidate -= dt.timedelta(days=1)
        if _is_trading_day(candidate):
            return candidate


def _parse_request_date(request: Any) -> dt.date:
    if request and hasattr(request, "args") and request.args:
        requested = request.args.get("date")
        if requested:
            return dt.datetime.strptime(requested, "%Y-%m-%d").date()
    today = _now_sp().date()
    if _is_trading_day(today):
        return today
    return _previous_trading_day(today)


def _fetch_signals(reference_date: dt.date) -> pd.DataFrame:
    query = (
        "SELECT date_ref, valid_for, ticker, side, entry, target, stop, horizon_days, "
        "model_version, ranking_key, score, rank "
        f"FROM `{_table_ref(SIGNALS_TABLE_ID)}` "
        "WHERE date_ref = @ref_date"
    )
    params = [bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)]
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    df = client.query(query, job_config=job_config).to_dataframe()
    df.sort_values("rank", inplace=True)
    return df


def _fetch_candles(
    tickers: Sequence[str],
    start_date: dt.date,
    end_date: dt.date,
) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()
    query = (
        "SELECT ticker, data_pregao, open, high, low, close "
        f"FROM `{_table_ref(DAILY_TABLE_ID)}` "
        "WHERE ticker IN UNNEST(@tickers) "
        "  AND data_pregao BETWEEN @start_date AND @end_date"
    )
    params = [
        bigquery.ArrayQueryParameter("tickers", "STRING", sorted(set(tickers))),
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
    ]
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    df = client.query(query, job_config=job_config).to_dataframe()
    return df


def _load_table(table_id: str, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    job = client.load_table_from_json(
        rows,
        table_id,
        job_config=bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND
        ),
    )
    job.result()


def _delete_by_date(table_id: str, column: str, date_value: dt.date) -> None:
    query = "DELETE FROM `" f"{table_id}" f"` WHERE {column} = @ref_date"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("ref_date", "DATE", date_value)]
    )
    client.query(query, job_config=job_config).result()


def _fetch_trade_history(start_date: dt.date, end_date: dt.date) -> pd.DataFrame:
    query = (
        "SELECT date_ref, ticker, side, horizon_days, entry_hit, return_pct, "
        "entry_fill_date, exit_date "
        f"FROM `{_table_ref(BACKTEST_TRADES_TABLE_ID)}` "
        "WHERE date_ref BETWEEN @start_date AND @end_date"
    )
    params = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
    ]
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    return client.query(query, job_config=job_config).to_dataframe()


def _as_naive_datetime(value: dt.datetime) -> dt.datetime:
    return value.astimezone(SAO_PAULO_TZ).replace(tzinfo=None)


def backtest_daily(request: Any) -> Dict[str, Any]:
    """Run the deterministic daily backtest for stored signals."""

    run_logger = StructuredLogger(JOB_NAME)
    reference_date = _parse_request_date(request)
    run_logger.update_context(date_ref=reference_date.isoformat())
    run_logger.started()
    if not _is_trading_day(reference_date):
        message = f"{reference_date} não é dia útil para backtest"
        run_logger.warn(message, reason="non_trading_day")
        logging.warning(message)
        return {"status": "skipped", "reason": message}

    signals_df = _fetch_signals(reference_date)
    if signals_df.empty:
        message = f"Nenhum sinal encontrado para {reference_date}"
        run_logger.warn(message, reason="missing_signals")
        logging.warning(message)
        return {"status": "empty", "reason": message}

    signals = build_signal_payloads(signals_df.to_dict("records"))
    min_valid = min(signal.valid_for for signal in signals)
    max_valid = max(signal.valid_for for signal in signals)
    max_horizon = max(signal.horizon_days for signal in signals)
    end_date = max_valid + dt.timedelta(days=max_horizon * 2)
    candles_df = _fetch_candles(
        [signal.ticker for signal in signals],
        min_valid,
        end_date,
    )
    candles = build_candle_lookup(candles_df.to_dict("records"))
    trades = run_backtest(signals, candles)

    created_at = _as_naive_datetime(_now_sp())
    trades_table = _table_ref(BACKTEST_TRADES_TABLE_ID)
    _delete_by_date(trades_table, "date_ref", reference_date)
    trade_rows = []
    for trade in trades:
        record = dict(trade.to_dict())
        record["created_at"] = created_at
        trade_rows.append(record)
    _load_table(trades_table, trade_rows)

    history_start = reference_date - dt.timedelta(days=METRICS_LOOKBACK_DAYS)
    history_df = _fetch_trade_history(history_start, reference_date)
    metrics = compute_backtest_metrics(history_df.to_dict("records"), reference_date)
    metrics_table = _table_ref(BACKTEST_METRICS_TABLE_ID)
    _delete_by_date(metrics_table, "as_of_date", reference_date)
    metric_rows = []
    for metric in metrics:
        payload = dict(metric)
        payload["created_at"] = created_at
        metric_rows.append(payload)
    _load_table(metrics_table, metric_rows)

    result = {
        "status": "ok",
        "date_ref": reference_date.isoformat(),
        "processed_signals": len(signals),
        "trades": len(trade_rows),
        "metrics": len(metric_rows),
    }
    run_logger.ok(
        "Backtest diário atualizado",
        processed_signals=len(signals),
        trades=len(trade_rows),
        metrics=len(metric_rows),
        trades_table=_table_ref(BACKTEST_TRADES_TABLE_ID),
        metrics_table=_table_ref(BACKTEST_METRICS_TABLE_ID),
    )
    return result
