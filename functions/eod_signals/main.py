"""Cloud Function that generates end-of-day Sisacao-8 signals."""

from __future__ import annotations

import datetime as dt
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

import pandas as pd  # type: ignore[import-untyped]
from google.cloud import bigquery  # type: ignore[import-untyped]

if __package__:
    from .candles import SAO_PAULO_TZ
    from .observability import StructuredLogger
    from .signals import (
        DEFAULT_HORIZON_DAYS,
        DEFAULT_RANKING_KEY,
        MODEL_VERSION,
        MAX_SIGNALS_PER_DAY,
        ConditionalSignal,
        compute_source_snapshot,
        generate_conditional_signals,
    )
else:
    from candles import SAO_PAULO_TZ
    from observability import StructuredLogger
    from signals import (
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
ENV_X_PCT = float(os.environ.get("SIGNAL_X_PCT", os.environ.get("X_PCT", "0.02")))
ENV_TARGET_PCT = float(
    os.environ.get("SIGNAL_TARGET_PCT", os.environ.get("TARGET_PCT", "0.07"))
)
ENV_STOP_PCT = float(
    os.environ.get("SIGNAL_STOP_PCT", os.environ.get("STOP_PCT", "0.07"))
)
ENV_MAX_SIGNALS = min(
    MAX_SIGNALS_PER_DAY,
    max(1, int(os.environ.get("MAX_SIGNALS", str(MAX_SIGNALS_PER_DAY)))),
)
ENV_ALLOW_SELL = os.environ.get("ALLOW_SELL_SIGNALS", "true").lower() == "true"
ENV_HORIZON_DAYS = int(os.environ.get("SIGNAL_HORIZON_DAYS", str(DEFAULT_HORIZON_DAYS)))
RANKING_KEY = os.environ.get("SIGNAL_RANKING_KEY", DEFAULT_RANKING_KEY)
STRATEGY_CONFIG_TABLE_ID = os.environ.get(
    "BQ_STRATEGY_CONFIG_TABLE", "parametros_estrategia"
)
STRATEGY_CONFIG_ID = os.environ.get("STRATEGY_CONFIG_ID", "signals_v1")
JOB_NAME = os.environ.get("JOB_NAME", "eod_signals")


@dataclass(frozen=True)
class StrategyConfig:
    config_version: str
    x_pct: float
    target_pct: float
    stop_pct: float
    allow_sell: bool
    horizon_days: int
    max_signals: int


client: bigquery.Client | None = None


def _get_client() -> bigquery.Client:
    global client
    if client is None:
        client = bigquery.Client()
    return client


def _now_sp() -> dt.datetime:
    return dt.datetime.now(tz=SAO_PAULO_TZ)


def _naive_sp(value: dt.datetime) -> dt.datetime:
    return value.astimezone(SAO_PAULO_TZ).replace(tzinfo=None)


def _request_payload(request: Any) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    if request is None:
        return data
    if hasattr(request, "args") and request.args:
        for key in request.args:
            value = request.args.get(key)
            if value is not None:
                data.setdefault(key, value)
    if hasattr(request, "get_json"):
        try:
            body = request.get_json(silent=True) or {}
        except Exception:  # noqa: BLE001
            body = {}
        if isinstance(body, dict):
            for key, value in body.items():
                if value is not None:
                    data[key] = value
    return data


def _get_first_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _parse_request_date(payload: Mapping[str, Any]) -> dt.date:
    requested = _get_first_value(payload, ("date_ref", "date"))
    if requested:
        return dt.datetime.strptime(requested, "%Y-%m-%d").date()
    return _now_sp().date() - dt.timedelta(days=1)


def _ensure_after_cutoff(force: bool) -> bool:
    if force or EARLY_RUN:
        return True
    local_now = _now_sp().time()
    return local_now >= dt.time(18, 0)


def _table_ref(table_id: str) -> str:
    bq_client = _get_client()
    return f"{bq_client.project}.{DATASET_ID}.{table_id}"


def _holidays_table() -> str:
    return _table_ref(FERIADOS_TABLE_ID)


def _metrics_table() -> str:
    return _table_ref(BACKTEST_METRICS_TABLE_ID)


def _limit_signals(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = ENV_MAX_SIGNALS
    parsed = max(1, parsed)
    return min(parsed, MAX_SIGNALS_PER_DAY)


def _default_strategy_config() -> StrategyConfig:
    version = os.environ.get("STRATEGY_CONFIG_VERSION", "env-default")
    return StrategyConfig(
        config_version=version,
        x_pct=ENV_X_PCT,
        target_pct=ENV_TARGET_PCT,
        stop_pct=ENV_STOP_PCT,
        allow_sell=ENV_ALLOW_SELL,
        horizon_days=ENV_HORIZON_DAYS,
        max_signals=_limit_signals(ENV_MAX_SIGNALS),
    )


def _load_strategy_config() -> StrategyConfig:
    table_id = _table_ref(STRATEGY_CONFIG_TABLE_ID)
    query = (
        "SELECT parametro_id, x_pct, target_pct, stop_pct, horizon_days, "
        "allow_sell, max_signals, updated_at "
        f"FROM `{table_id}` "
        "WHERE parametro_id = @config_id "
        "ORDER BY updated_at DESC "
        "LIMIT 1"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("config_id", "STRING", STRATEGY_CONFIG_ID)
        ]
    )
    try:
        row_iter = _get_client().query(query, job_config=job_config).result()
        row = next(iter(row_iter), None)
    except Exception as exc:  # noqa: BLE001
        logging.warning(
            "Falha ao carregar parametros_estrategia %s: %s",
            STRATEGY_CONFIG_TABLE_ID,
            exc,
            exc_info=True,
        )
        return _default_strategy_config()
    if row is None:
        logging.warning(
            "Config ID %s não encontrado em %s; usando defaults",
            STRATEGY_CONFIG_ID,
            STRATEGY_CONFIG_TABLE_ID,
        )
        return _default_strategy_config()
    updated_at = getattr(row, "updated_at", None)
    version_token = getattr(row, "parametro_id", STRATEGY_CONFIG_ID)
    if updated_at is not None and hasattr(updated_at, "isoformat"):
        config_version = f"{version_token}:{updated_at.isoformat()}"
    else:
        config_version = str(version_token)
    allow_sell = getattr(row, "allow_sell", ENV_ALLOW_SELL)
    horizon_days = getattr(row, "horizon_days", ENV_HORIZON_DAYS) or ENV_HORIZON_DAYS
    return StrategyConfig(
        config_version=config_version,
        x_pct=float(getattr(row, "x_pct", ENV_X_PCT) or ENV_X_PCT),
        target_pct=float(getattr(row, "target_pct", ENV_TARGET_PCT) or ENV_TARGET_PCT),
        stop_pct=float(getattr(row, "stop_pct", ENV_STOP_PCT) or ENV_STOP_PCT),
        allow_sell=_as_bool(allow_sell),
        horizon_days=int(horizon_days),
        max_signals=_limit_signals(getattr(row, "max_signals", ENV_MAX_SIGNALS)),
    )


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
        rows = list(_get_client().query(query, job_config=job_config).result())
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
        "SELECT ticker, data_pregao, open, close, high, low, "
        "volume_financeiro, qtd_negociada "
        f"FROM `{_table_ref(DAILY_TABLE_ID)}` "
        "WHERE data_pregao = @ref_date"
    )
    params = [bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)]
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    df = _get_client().query(query, job_config=job_config).to_dataframe()
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
        return _get_client().query(query).to_dataframe()
    except Exception as exc:  # noqa: BLE001
        logging.info("Backtest metrics indisponíveis: %s", exc)
        return pd.DataFrame()


def _delete_partition(table_id: str, reference_date: dt.date) -> None:
    query = "DELETE FROM `" f"{table_id}" "` WHERE date_ref = @ref_date"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)
        ]
    )
    _get_client().query(query, job_config=job_config).result()
    logging.info("Partição de %s removida em %s", reference_date, table_id)


def _persist_signals(
    table_id: str,
    signals: List[ConditionalSignal],
    reference_date: dt.date,
    valid_for: dt.date,
    created_at: dt.datetime,
    source_snapshot: str,
    code_version: str,
    *,
    run_id: str,
    config_version: str,
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
    for row in rows:
        row["job_run_id"] = run_id
        row["config_version"] = config_version
    if not rows:
        logging.warning("Nenhum sinal para gravar no BigQuery")
        return
    load_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    job = _get_client().load_table_from_json(rows, table_id, job_config=load_config)
    job.result()
    logging.info("%s sinais gravados em %s", len(rows), table_id)


def generate_eod_signals(request: Any) -> Dict[str, Any]:
    """HTTP handler executed by Cloud Functions."""

    run_logger = StructuredLogger(JOB_NAME)
    run_logger.update_context(
        model_version=MODEL_VERSION,
        ranking_key=RANKING_KEY,
    )

    payload = _request_payload(request)
    reason = _get_first_value(payload, ("reason",))
    mode = payload.get("mode")
    force = _as_bool(payload.get("force"))
    if reason:
        run_logger.update_context(reason=reason)
    if mode:
        run_logger.update_context(mode=mode)
    run_logger.update_context(force=force)

    if not _ensure_after_cutoff(force):
        message = "Execução bloqueada antes do cutoff (18:00 BRT)."
        run_logger.warn(message, reason="before_cutoff")
        logging.warning(message)
        return {"status": "skipped", "reason": message, "request_reason": reason}, 400

    reference_date = _parse_request_date(payload)
    run_logger.update_context(date_ref=reference_date.isoformat())
    run_logger.started()

    if not _is_trading_day(reference_date):
        message = f"{reference_date} não é dia útil da B3 (feriado/fim de semana)."
        run_logger.warn(message, reason="non_trading_day")
        logging.warning(message)
        return {"status": "skipped", "reason": message, "request_reason": reason}

    strategy_config = _load_strategy_config()
    run_logger.update_context(
        config_version=strategy_config.config_version,
        horizon_days=strategy_config.horizon_days,
    )

    valid_for = _next_business_day(reference_date)
    run_logger.update_context(valid_for=valid_for.isoformat())
    logging.info(
        (
            "Gerando sinais para %s válidos em %s | modelo=%s | X=%.2f%% | TP=%.2f%% | "
            "SL=%.2f%% | horizon=%sd | ranking=%s | config=%s"
        ),
        reference_date,
        valid_for,
        MODEL_VERSION,
        strategy_config.x_pct * 100,
        strategy_config.target_pct * 100,
        strategy_config.stop_pct * 100,
        strategy_config.horizon_days,
        RANKING_KEY,
        strategy_config.config_version,
    )

    frame = _fetch_daily_frame(reference_date)
    initial_rows = len(frame)
    if frame.empty:
        message = f"Sem candles disponíveis para {reference_date}"
        run_logger.warn(message, reason="empty_daily_frame")
        logging.warning(message)
        return {
            "status": "empty",
            "reason": message,
            "request_reason": reason,
            "config_version": strategy_config.config_version,
        }

    frame = frame.fillna(0)
    if MIN_VOLUME > 0 and "volume_financeiro" in frame.columns:
        frame = frame[frame["volume_financeiro"].fillna(0) >= MIN_VOLUME]
        logging.info(
            "Filtrando por volume financeiro mínimo %.0f: %s tickers",
            MIN_VOLUME,
            len(frame),
        )
        if frame.empty:
            run_logger.warn(
                "Nenhum ticker passou no filtro de volume",
                reason="volume_filter",
                min_volume=MIN_VOLUME,
                requested=initial_rows,
            )
            return {
                "status": "filtered",
                "reason": "volume",
                "request_reason": reason,
                "config_version": strategy_config.config_version,
            }

    limit = strategy_config.max_signals
    metrics_df = _fetch_latest_metrics()
    signals = generate_conditional_signals(
        frame,
        top_n=limit,
        x_pct=strategy_config.x_pct,
        target_pct=strategy_config.target_pct,
        stop_pct=strategy_config.stop_pct,
        allow_sell=strategy_config.allow_sell,
        horizon_days=strategy_config.horizon_days,
        ranking_key=RANKING_KEY,
        backtest_metrics=metrics_df,
    )
    created_at = _now_sp()
    created_at_naive = _naive_sp(created_at)
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
        "requested": initial_rows,
        "generated": len(signals),
        "ranking_key": RANKING_KEY,
        "horizon_days": strategy_config.horizon_days,
        "config_version": strategy_config.config_version,
        "request_reason": reason,
        "mode": mode,
        "force": force,
    }

    table_id = _table_ref(SIGNALS_TABLE_ID)
    _delete_partition(table_id, reference_date)
    _persist_signals(
        table_id,
        signals,
        reference_date,
        valid_for,
        created_at_naive,
        source_snapshot,
        code_version,
        run_id=run_logger.run_id,
        config_version=strategy_config.config_version,
    )

    response["stored"] = len(signals)
    response["max_signals"] = limit
    if signals:
        run_logger.ok(
            "Sinais EOD armazenados",
            generated=len(signals),
            requested=initial_rows,
            table=table_id,
        )
    else:
        run_logger.warn(
            "Nenhum sinal gerado",
            requested=initial_rows,
            table=table_id,
        )
    return response
