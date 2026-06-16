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
MAX_DATES_PER_RUN = max(1, int(os.environ.get("BACKTEST_MAX_DATES_PER_RUN", "1")))
JOB_NAME = os.environ.get("JOB_NAME", "backtest_daily")
DEFAULT_BQ_LOCATION = "us-east1"


def _normalize_bq_location(
    value: str | None, default: str = DEFAULT_BQ_LOCATION
) -> str:
    raw_value = default if value is None else value
    text = str(raw_value).strip()
    if not text:
        text = default
    lowered = text.lower()
    if lowered.startswith("region-"):
        lowered = lowered.split("region-", 1)[1]
    if lowered == "east1":
        return "us-east1"
    return lowered


BQ_LOCATION = _normalize_bq_location(os.environ.get("BQ_LOCATION"))

client = bigquery.Client(location=BQ_LOCATION)


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


def _parse_iso_date(value: str) -> dt.date:
    return dt.datetime.strptime(value, "%Y-%m-%d").date()


def _request_arg(request: Any, key: str) -> str | None:
    if request and hasattr(request, "args") and request.args:
        value = request.args.get(key)
        if value:
            return str(value)
    return None


def _request_int(request: Any, key: str, default: int) -> int:
    raw_value = _request_arg(request, key)
    if raw_value is None:
        return default
    try:
        return max(1, int(raw_value))
    except ValueError:
        logging.warning("Parâmetro inteiro inválido: %s=%s", key, raw_value)
        return default


def _trading_dates_between(
    start_date: dt.date,
    end_date: dt.date,
    *,
    limit: int,
) -> List[dt.date]:
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    dates: List[dt.date] = []
    current = start_date
    while current <= end_date and len(dates) < limit:
        if _is_trading_day(current):
            dates.append(current)
        current += dt.timedelta(days=1)
    return dates


def _parse_request_dates(request: Any) -> List[dt.date]:
    limit = _request_int(request, "limit", MAX_DATES_PER_RUN)
    requested = _request_arg(request, "date")
    if requested:
        return [_parse_iso_date(requested)]
    requested_from = _request_arg(request, "date_from") or _request_arg(request, "from")
    requested_to = _request_arg(request, "date_to") or _request_arg(request, "to")
    if requested_from and requested_to:
        return _trading_dates_between(
            _parse_iso_date(requested_from),
            _parse_iso_date(requested_to),
            limit=limit,
        )
    today = _now_sp().date()
    backlog_dates = _find_pending_signals_dates(today, limit=limit)
    if backlog_dates:
        return backlog_dates
    if _is_trading_day(today):
        return [today]
    return [_previous_trading_day(today)]


def _find_pending_signals_dates(as_of_date: dt.date, *, limit: int) -> List[dt.date]:
    """Return oldest signal dates that still need backtest processing."""

    query = (
        "WITH daily AS ("
        "  SELECT date_ref, COUNT(*) AS signals_count "
        f"  FROM `{_table_ref(SIGNALS_TABLE_ID)}` "
        "  WHERE date_ref <= @as_of_date "
        "  GROUP BY date_ref"
        "), trades AS ("
        "  SELECT date_ref, COUNT(*) AS trades_count "
        f"  FROM `{_table_ref(BACKTEST_TRADES_TABLE_ID)}` "
        "  WHERE date_ref <= @as_of_date "
        "  GROUP BY date_ref"
        "), metrics AS ("
        "  SELECT as_of_date, COUNT(*) AS metrics_count "
        f"  FROM `{_table_ref(BACKTEST_METRICS_TABLE_ID)}` "
        "  WHERE as_of_date <= @as_of_date "
        "  GROUP BY as_of_date"
        ") "
        "SELECT daily.date_ref "
        "FROM daily "
        "LEFT JOIN trades USING (date_ref) "
        "LEFT JOIN metrics ON metrics.as_of_date = daily.date_ref "
        "WHERE IFNULL(trades.trades_count, 0) < daily.signals_count "
        "   OR IFNULL(metrics.metrics_count, 0) = 0 "
        "ORDER BY daily.date_ref ASC "
        "LIMIT @limit"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("as_of_date", "DATE", as_of_date),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ]
    )
    try:
        rows = list(client.query(query, job_config=job_config).result())
    except Exception as exc:  # noqa: BLE001
        logging.warning(
            "Falha ao descobrir backlog de sinais pendentes: %s",
            exc,
            exc_info=True,
        )
        return []
    return [_coerce_date(row.date_ref) for row in rows]


def _coerce_date(value: object) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.datetime.strptime(str(value), "%Y-%m-%d").date()


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
        logging.info("Sem linhas para persistir em %s", table_id)
        return
    logging.info(
        "Iniciando carga no BigQuery: tabela=%s linhas=%s",
        table_id,
        len(rows),
    )
    job = client.load_table_from_json(
        [_json_safe_row(row) for row in rows],
        table_id,
        job_config=bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND
        ),
    )
    job.result()
    logging.info(
        "Carga concluída no BigQuery: tabela=%s job_id=%s linhas=%s",
        table_id,
        job.job_id,
        len(rows),
    )


def _delete_by_date(table_id: str, column: str, date_value: dt.date) -> None:
    query = "DELETE FROM `" f"{table_id}" f"` WHERE {column} = @ref_date"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("ref_date", "DATE", date_value)]
    )
    job = client.query(query, job_config=job_config)
    job.result()
    logging.info(
        "DELETE executado: tabela=%s coluna=%s data=%s job_id=%s",
        table_id,
        column,
        date_value.isoformat(),
        job.job_id,
    )


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


def _json_safe_value(value: object) -> object:
    if isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    return value


def _json_safe_row(row: Dict[str, object]) -> Dict[str, object]:
    return {key: _json_safe_value(value) for key, value in row.items()}


def _run_backtest_for_date(
    reference_date: dt.date,
    run_logger: StructuredLogger,
) -> Dict[str, Any]:
    run_logger.update_context(date_ref=reference_date.isoformat())
    if not _is_trading_day(reference_date):
        message = f"{reference_date} não é dia útil para backtest"
        run_logger.warn(message, reason="non_trading_day")
        logging.warning(
            (
                "BACKTEST_DAILY_EARLY_EXIT run_id=%s "
                "reason=non_trading_day message=%s"
            ),
            run_logger.run_id,
            message,
        )
        return {
            "status": "skipped",
            "date_ref": reference_date.isoformat(),
            "reason": message,
        }

    signals_df = _fetch_signals(reference_date)
    logging.info(
        "Consulta de sinais concluída: date_ref=%s linhas=%s",
        reference_date.isoformat(),
        len(signals_df),
    )
    if signals_df.empty:
        message = f"Nenhum sinal encontrado para {reference_date}"
        run_logger.warn(message, reason="missing_signals")
        logging.warning(
            (
                "BACKTEST_DAILY_EARLY_EXIT run_id=%s "
                "reason=missing_signals message=%s"
            ),
            run_logger.run_id,
            message,
        )
        return {
            "status": "empty",
            "date_ref": reference_date.isoformat(),
            "reason": message,
        }

    run_logger.ok(
        "Sinais carregados",
        signals_found=int(len(signals_df)),
        unique_tickers=int(signals_df["ticker"].nunique()),
    )

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
    logging.info(
        "Consulta de candles concluída: linhas=%s intervalo=%s..%s",
        len(candles_df),
        min_valid.isoformat(),
        end_date.isoformat(),
    )
    run_logger.ok(
        "Candles carregados",
        candles_found=int(len(candles_df)),
        candles_start=min_valid.isoformat(),
        candles_end=end_date.isoformat(),
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
    run_logger.ok(
        "Backtest executado e trades persistidos",
        trades_generated=len(trade_rows),
        entries_hit=sum(1 for row in trade_rows if bool(row["entry_hit"])),
        trades_table=trades_table,
    )

    history_start = reference_date - dt.timedelta(days=METRICS_LOOKBACK_DAYS)
    history_df = _fetch_trade_history(history_start, reference_date)
    logging.info(
        "Histórico para métricas carregado: linhas=%s intervalo=%s..%s",
        len(history_df),
        history_start.isoformat(),
        reference_date.isoformat(),
    )
    metrics = compute_backtest_metrics(
        history_df.to_dict("records"),
        reference_date,
    )
    metrics_table = _table_ref(BACKTEST_METRICS_TABLE_ID)
    _delete_by_date(metrics_table, "as_of_date", reference_date)
    metric_rows = []
    for metric in metrics:
        payload = dict(metric)
        payload["created_at"] = created_at
        metric_rows.append(payload)
    _load_table(metrics_table, metric_rows)
    run_logger.ok(
        "Métricas calculadas e persistidas",
        history_rows=len(history_df),
        metrics_rows=len(metric_rows),
        metrics_table=metrics_table,
        history_start=history_start.isoformat(),
        history_end=reference_date.isoformat(),
    )

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
    logging.warning(
        (
            "BACKTEST_DAILY_COMPLETED run_id=%s date_ref=%s "
            "processed_signals=%s trades=%s metrics=%s"
        ),
        run_logger.run_id,
        reference_date.isoformat(),
        len(signals),
        len(trade_rows),
        len(metric_rows),
    )
    return result


def _summarize_backtest_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(results) == 1:
        return results[0]
    ok_results = [result for result in results if result.get("status") == "ok"]
    return {
        "status": "ok" if ok_results else "empty",
        "processed_dates": len(results),
        "ok_dates": len(ok_results),
        "processed_signals": sum(
            int(result.get("processed_signals", 0)) for result in results
        ),
        "trades": sum(int(result.get("trades", 0)) for result in results),
        "metrics": sum(int(result.get("metrics", 0)) for result in results),
        "results": results,
    }


def backtest_daily(request: Any) -> Dict[str, Any]:
    """Run deterministic daily backtests for one or more stored signal dates."""

    run_logger = StructuredLogger(JOB_NAME)
    logging.warning(
        "BACKTEST_DAILY_INVOCATION_RECEIVED job=%s run_id=%s",
        JOB_NAME,
        run_logger.run_id,
    )
    try:
        reference_dates = _parse_request_dates(request)
        run_logger.started(
            bq_location=BQ_LOCATION,
            intraday_dataset=DATASET_ID,
            signals_table=_table_ref(SIGNALS_TABLE_ID),
            daily_table=_table_ref(DAILY_TABLE_ID),
            metrics_lookback_days=METRICS_LOOKBACK_DAYS,
            dates_count=len(reference_dates),
            dates=[date_value.isoformat() for date_value in reference_dates],
        )
        results = [
            _run_backtest_for_date(reference_date, run_logger)
            for reference_date in reference_dates
        ]
        summary = _summarize_backtest_results(results)
        logging.warning(
            (
                "BACKTEST_DAILY_BATCH_COMPLETED run_id=%s "
                "processed_dates=%s ok_dates=%s processed_signals=%s"
            ),
            run_logger.run_id,
            len(results),
            sum(1 for result in results if result.get("status") == "ok"),
            summary.get("processed_signals", 0),
        )
        return summary
    except Exception as exc:  # noqa: BLE001
        run_logger.exception(exc)
        raise
