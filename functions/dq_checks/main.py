"""Daily data-quality checks persisted to BigQuery for Sisacao-8."""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence

try:
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:  # pragma: no cover - fallback for Python 3.8
    from backports.zoneinfo import ZoneInfo  # type: ignore[assignment]

from google.cloud import bigquery  # type: ignore[import-untyped]

from .observability import StructuredLogger

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))

DATASET_ID = os.environ.get("BQ_INTRADAY_DATASET", "cotacao_intraday")
DAILY_TABLE_ID = os.environ.get("BQ_DAILY_TABLE", "cotacao_ohlcv_diario")
RAW_TABLE_ID = os.environ.get("BQ_INTRADAY_RAW_TABLE", "cotacao_b3")
SIGNALS_TABLE_ID = os.environ.get("BQ_SIGNALS_TABLE", "sinais_eod")
BACKTEST_METRICS_TABLE_ID = os.environ.get(
    "BQ_BACKTEST_METRICS_TABLE", "backtest_metrics"
)
TICKERS_TABLE_ID = os.environ.get("BQ_TICKERS_TABLE", "acao_bovespa")
FERIADOS_TABLE_ID = os.environ.get("BQ_HOLIDAYS_TABLE", "feriados_b3")
DQ_CHECKS_TABLE_ID = os.environ.get("BQ_DQ_CHECKS_TABLE", "dq_checks_daily")
DQ_INCIDENTS_TABLE_ID = os.environ.get("BQ_DQ_INCIDENTS_TABLE", "dq_incidents")
JOB_NAME = os.environ.get("JOB_NAME", "dq_checks")
PIPELINE_CONFIG_TABLE_ID = os.environ.get("PIPELINE_CONFIG_TABLE", "pipeline_config")
PIPELINE_CONFIG_ID = os.environ.get("PIPELINE_CONFIG_ID", "default")
DAILY_COVERAGE_THRESHOLD = float(os.environ.get("DQ_DAILY_COVERAGE", "0.9"))
INTRADAY_COVERAGE_THRESHOLD = float(os.environ.get("DQ_INTRADAY_COVERAGE", "0.7"))
INTRADAY_MIN_TIME = os.environ.get("DQ_INTRADAY_MIN_TIME", "17:45:00")
SIGNAL_LIMIT = int(os.environ.get("DQ_MAX_SIGNALS", "5"))
DEFAULT_SIGNALS_DEADLINE = os.environ.get("DQ_SIGNALS_DEADLINE", "22:00:00")
DEFAULT_SIGNALS_GRACE_MINUTES = int(os.environ.get("DQ_SIGNALS_GRACE_MINUTES", "60"))
DEFAULT_BACKTEST_DEADLINE = os.environ.get("DQ_BACKTEST_DEADLINE", "23:00:00")
DEFAULT_BACKTEST_GRACE_MINUTES = int(os.environ.get("DQ_BACKTEST_GRACE_MINUTES", "60"))
DEFAULT_INTRADAY_DUP_TOLERANCE = int(os.environ.get("DQ_INTRADAY_DUP_TOLERANCE", "0"))

SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")


_BQ_CLIENT: bigquery.Client | None = None


def _get_client() -> bigquery.Client:
    global _BQ_CLIENT
    if _BQ_CLIENT is None:
        _BQ_CLIENT = bigquery.Client()
    return _BQ_CLIENT


@dataclass
class CheckResult:
    """Container for a single data-quality evaluation."""

    name: str
    component: str
    status: str
    details: Dict[str, Any]

    @property
    def severity(self) -> str:
        return {
            "PASS": "INFO",
            "WARN": "WARNING",
            "FAIL": "CRITICAL",
        }.get(self.status, "INFO")


@dataclass(frozen=True)
class PipelineConfig:
    config_version: str
    daily_min_coverage: float
    intraday_min_coverage: float
    intraday_latest_time: dt.time
    intraday_duplicate_tolerance: int
    signals_deadline: dt.time
    signals_grace_minutes: int
    backtest_deadline: dt.time
    backtest_grace_minutes: int


def _now_sp() -> dt.datetime:
    return dt.datetime.now(tz=SAO_PAULO_TZ)


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


def _get_first_value(payload: Dict[str, Any], keys: tuple[str, ...]) -> str | None:
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


def _parse_time(value: Any, fallback: str) -> dt.time:
    if isinstance(value, dt.time):
        return value
    try:
        return dt.datetime.strptime(str(value), "%H:%M:%S").time()
    except ValueError:
        return dt.datetime.strptime(fallback, "%H:%M:%S").time()


def _parse_request_date(payload: Dict[str, Any]) -> dt.date:
    requested = _get_first_value(payload, ("date_ref", "date"))
    if requested:
        return dt.datetime.strptime(requested, "%Y-%m-%d").date()
    return _now_sp().date()

    if request and hasattr(request, "args") and request.args:
        requested = request.args.get("date")
        if requested:
            return dt.datetime.strptime(requested, "%Y-%m-%d").date()
    return _now_sp().date()


def _table_ref(table_id: str) -> str:
    return f"{_get_client().project}.{DATASET_ID}.{table_id}"


def _pipeline_config_table() -> str:
    return f"{_get_client().project}.{DATASET_ID}.{PIPELINE_CONFIG_TABLE_ID}"


def _default_pipeline_config() -> PipelineConfig:
    latest_time = _parse_time(INTRADAY_MIN_TIME, INTRADAY_MIN_TIME)
    return PipelineConfig(
        config_version=os.environ.get("PIPELINE_CONFIG_VERSION", "env-default"),
        daily_min_coverage=DAILY_COVERAGE_THRESHOLD,
        intraday_min_coverage=INTRADAY_COVERAGE_THRESHOLD,
        intraday_latest_time=latest_time,
        intraday_duplicate_tolerance=DEFAULT_INTRADAY_DUP_TOLERANCE,
        signals_deadline=_parse_time(
            DEFAULT_SIGNALS_DEADLINE, DEFAULT_SIGNALS_DEADLINE
        ),
        signals_grace_minutes=DEFAULT_SIGNALS_GRACE_MINUTES,
        backtest_deadline=_parse_time(
            DEFAULT_BACKTEST_DEADLINE, DEFAULT_BACKTEST_DEADLINE
        ),
        backtest_grace_minutes=DEFAULT_BACKTEST_GRACE_MINUTES,
    )


def _load_pipeline_config() -> PipelineConfig:
    query = (
        "SELECT config_id, config_version, daily_min_coverage, intraday_min_coverage, "
        "intraday_latest_time, intraday_duplicate_tolerance, signals_deadline, "
        "signals_grace_minutes, backtest_deadline, backtest_grace_minutes "
        f"FROM `{_pipeline_config_table()}` "
        "WHERE config_id = @config_id "
        "ORDER BY created_at DESC "
        "LIMIT 1"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("config_id", "STRING", PIPELINE_CONFIG_ID)
        ]
    )
    try:
        row_iter = _get_client().query(query, job_config=job_config).result()
        row = next(iter(row_iter), None)
    except Exception as exc:  # noqa: BLE001
        logging.warning(
            "Falha ao carregar pipeline_config %s: %s",
            PIPELINE_CONFIG_TABLE_ID,
            exc,
            exc_info=True,
        )
        return _default_pipeline_config()
    if row is None:
        logging.warning(
            "Config %s não encontrado em %s; usando defaults",
            PIPELINE_CONFIG_ID,
            PIPELINE_CONFIG_TABLE_ID,
        )
        return _default_pipeline_config()
    config_id = getattr(row, "config_id", PIPELINE_CONFIG_ID)
    version = getattr(row, "config_version", "unknown")
    return PipelineConfig(
        config_version=f"{config_id}:{version}",
        daily_min_coverage=float(
            getattr(row, "daily_min_coverage", DAILY_COVERAGE_THRESHOLD)
            or DAILY_COVERAGE_THRESHOLD
        ),
        intraday_min_coverage=float(
            getattr(row, "intraday_min_coverage", INTRADAY_COVERAGE_THRESHOLD)
            or INTRADAY_COVERAGE_THRESHOLD
        ),
        intraday_latest_time=_parse_time(
            getattr(row, "intraday_latest_time", None),
            INTRADAY_MIN_TIME,
        ),
        intraday_duplicate_tolerance=int(
            getattr(row, "intraday_duplicate_tolerance", DEFAULT_INTRADAY_DUP_TOLERANCE)
            or DEFAULT_INTRADAY_DUP_TOLERANCE
        ),
        signals_deadline=_parse_time(
            getattr(row, "signals_deadline", None),
            DEFAULT_SIGNALS_DEADLINE,
        ),
        signals_grace_minutes=int(
            getattr(row, "signals_grace_minutes", DEFAULT_SIGNALS_GRACE_MINUTES)
            or DEFAULT_SIGNALS_GRACE_MINUTES
        ),
        backtest_deadline=_parse_time(
            getattr(row, "backtest_deadline", None),
            DEFAULT_BACKTEST_DEADLINE,
        ),
        backtest_grace_minutes=int(
            getattr(row, "backtest_grace_minutes", DEFAULT_BACKTEST_GRACE_MINUTES)
            or DEFAULT_BACKTEST_GRACE_MINUTES
        ),
    )


def _query(
    query: str,
    params: Sequence[bigquery.ScalarQueryParameter],
) -> Iterable[bigquery.table.Row]:
    job_config = bigquery.QueryJobConfig(query_parameters=list(params))
    return _get_client().query(query, job_config=job_config)


def _is_b3_holiday(date_value: dt.date) -> bool:
    query = (
        "SELECT 1 FROM `"
        f"{_table_ref(FERIADOS_TABLE_ID)}"
        "` WHERE data_feriado = @ref LIMIT 1"
    )
    params = [bigquery.ScalarQueryParameter("ref", "DATE", date_value)]
    try:
        rows = list(_query(query, params))
    except Exception as exc:  # noqa: BLE001
        logging.warning("Falha ao consultar feriados: %s", exc, exc_info=True)
        return False
    return bool(rows)


def _is_trading_day(date_value: dt.date) -> bool:
    if date_value.weekday() >= 5:
        return False
    return not _is_b3_holiday(date_value)


def _coverage_status(
    *,
    available: int,
    expected: int,
    threshold: float,
) -> tuple[str, float]:
    if expected <= 0:
        return "WARN", 0.0
    coverage = available / expected
    if coverage >= threshold:
        return "PASS", coverage
    return "FAIL", coverage


def _check_daily_freshness(
    reference_date: dt.date, config: PipelineConfig
) -> CheckResult:
    query = f"""
        WITH ativos AS (
            SELECT COUNTIF(ativo) AS ativos
            FROM `{_table_ref(TICKERS_TABLE_ID)}`
        ),
        disponiveis AS (
            SELECT COUNT(DISTINCT ticker) AS tickers
            FROM `{_table_ref(DAILY_TABLE_ID)}`
            WHERE data_pregao = @ref_date
        )
        SELECT ativos.ativos AS ativos, disponiveis.tickers AS tickers
        FROM ativos CROSS JOIN disponiveis
    """
    params = [bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)]
    row = next(iter(_query(query, params)), None)
    expected = int(getattr(row, "ativos", 0) or 0)
    available = int(getattr(row, "tickers", 0) or 0)
    status, coverage = _coverage_status(
        available=available,
        expected=expected,
        threshold=config.daily_min_coverage,
    )
    details = {
        "expected_tickers": expected,
        "available_tickers": available,
        "coverage_pct": round(coverage, 4),
        "threshold": config.daily_min_coverage,
    }
    if expected == 0:
        details["warning"] = "Tabela de tickers está vazia"
    return CheckResult(
        name="daily_freshness",
        component=DAILY_TABLE_ID,
        status=status,
        details=details,
    )


def _check_intraday_freshness(
    reference_date: dt.date, config: PipelineConfig
) -> CheckResult:
    query = f"""
        WITH ativos AS (
            SELECT COUNTIF(ativo) AS ativos
            FROM `{_table_ref(TICKERS_TABLE_ID)}`
        ),
        ultimos AS (
            SELECT ticker, MAX(hora) AS ultima_hora
            FROM `{_table_ref(RAW_TABLE_ID)}`
            WHERE data = @ref_date
            GROUP BY ticker
        )
        SELECT
            ativos.ativos AS ativos,
            COUNT(*) AS tickers_com_dados,
            COUNTIF(ultima_hora >= @min_time) AS tickers_recentes,
            MAX(ultima_hora) AS hora_maxima
        FROM ativos, ultimos
    """
    params = [
        bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date),
        bigquery.ScalarQueryParameter("min_time", "TIME", config.intraday_latest_time),
    ]
    row = next(iter(_query(query, params)), None)
    expected = int(getattr(row, "ativos", 0) or 0)
    recent = int(getattr(row, "tickers_recentes", 0) or 0)
    max_time = getattr(row, "hora_maxima", None)
    status, coverage = _coverage_status(
        available=recent,
        expected=expected,
        threshold=config.intraday_min_coverage,
    )
    details = {
        "expected_tickers": expected,
        "fresh_tickers": recent,
        "coverage_pct": round(coverage, 4),
        "threshold": config.intraday_min_coverage,
        "last_time": str(max_time) if max_time else None,
    }
    return CheckResult(
        name="intraday_freshness",
        component=RAW_TABLE_ID,
        status=status,
        details=details,
    )


def _check_intraday_uniqueness(
    reference_date: dt.date, config: PipelineConfig
) -> CheckResult:
    query = f"""
        SELECT COUNT(*) AS duplicados
        FROM (
            SELECT ticker, data, hora
            FROM `{_table_ref(RAW_TABLE_ID)}`
            WHERE data = @ref_date
            GROUP BY ticker, data, hora
            HAVING COUNT(*) > 1
        )
    """
    params = [bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)]
    row = next(iter(_query(query, params)), None)
    duplicates = int(getattr(row, "duplicados", 0) or 0)
    status = "FAIL" if duplicates > config.intraday_duplicate_tolerance else "PASS"
    return CheckResult(
        name="intraday_uniqueness",
        component=RAW_TABLE_ID,
        status=status,
        details={
            "duplicates": duplicates,
            "tolerance": config.intraday_duplicate_tolerance,
        },
    )


def _check_daily_uniqueness(reference_date: dt.date) -> CheckResult:
    query = f"""
        SELECT COUNT(*) AS duplicados
        FROM (
            SELECT ticker, data_pregao
            FROM `{_table_ref(DAILY_TABLE_ID)}`
            WHERE data_pregao = @ref_date
            GROUP BY ticker, data_pregao
            HAVING COUNT(*) > 1
        )
    """
    params = [bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)]
    row = next(iter(_query(query, params)), None)
    duplicates = int(getattr(row, "duplicados", 0) or 0)
    status = "FAIL" if duplicates > 0 else "PASS"
    return CheckResult(
        name="daily_uniqueness",
        component=DAILY_TABLE_ID,
        status=status,
        details={"duplicates": duplicates},
    )


def _check_ohlc_validity(reference_date: dt.date) -> CheckResult:
    query = f"""
        SELECT
            COUNTIF(high < GREATEST(open, close, low)) AS invalid_high,
            COUNTIF(low > LEAST(open, close, high)) AS invalid_low
        FROM `{_table_ref(DAILY_TABLE_ID)}`
        WHERE data_pregao = @ref_date
    """
    params = [bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)]
    row = next(iter(_query(query, params)), None)
    invalid_high = int(getattr(row, "invalid_high", 0) or 0)
    invalid_low = int(getattr(row, "invalid_low", 0) or 0)
    issues = invalid_high + invalid_low
    status = "FAIL" if issues > 0 else "PASS"
    return CheckResult(
        name="ohlc_validity",
        component=DAILY_TABLE_ID,
        status=status,
        details={
            "invalid_high": invalid_high,
            "invalid_low": invalid_low,
        },
    )


def _check_signals(reference_date: dt.date, trading_day: bool) -> CheckResult:
    if not trading_day:
        return CheckResult(
            name="signals_limits",
            component=SIGNALS_TABLE_ID,
            status="WARN",
            details={"reason": "non_trading_day"},
        )
    query = f"""
        SELECT
            COUNT(*) AS total,
            COUNTIF(side NOT IN ('BUY', 'SELL')) AS invalid_side,
            COUNTIF(side = 'BUY' AND target <= entry) AS invalid_buy,
            COUNTIF(side = 'BUY' AND stop >= entry) AS invalid_buy_stop,
            COUNTIF(side = 'SELL' AND target >= entry) AS invalid_sell,
            COUNTIF(side = 'SELL' AND stop <= entry) AS invalid_sell_stop
        FROM `{_table_ref(SIGNALS_TABLE_ID)}`
        WHERE date_ref = @ref_date
    """
    params = [bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)]
    row = next(iter(_query(query, params)), None)
    total = int(getattr(row, "total", 0) or 0)
    invalid_side = int(getattr(row, "invalid_side", 0) or 0)
    invalid_buy = int(getattr(row, "invalid_buy", 0) or 0)
    invalid_buy_stop = int(getattr(row, "invalid_buy_stop", 0) or 0)
    invalid_sell = int(getattr(row, "invalid_sell", 0) or 0)
    invalid_sell_stop = int(getattr(row, "invalid_sell_stop", 0) or 0)
    issues = (
        invalid_side + invalid_buy + invalid_buy_stop + invalid_sell + invalid_sell_stop
    )
    if total == 0:
        status = "FAIL"
    elif total > SIGNAL_LIMIT or issues > 0:
        status = "FAIL"
    else:
        status = "PASS"
    return CheckResult(
        name="signals_limits",
        component=SIGNALS_TABLE_ID,
        status=status,
        details={
            "total": total,
            "limit": SIGNAL_LIMIT,
            "invalid_side": invalid_side,
            "invalid_levels": issues,
        },
    )


def _check_signals_freshness(
    reference_date: dt.date, config: PipelineConfig, trading_day: bool
) -> CheckResult:
    if not trading_day:
        return CheckResult(
            name="signals_freshness",
            component=SIGNALS_TABLE_ID,
            status="WARN",
            details={"reason": "non_trading_day"},
        )
    query = f"""
        SELECT
            COUNT(*) AS total,
            MAX(created_at) AS last_created_at,
            DATETIME_ADD(DATETIME(@ref_date, @deadline), INTERVAL @grace MINUTE) AS deadline_dt
        FROM `{_table_ref(SIGNALS_TABLE_ID)}`
        WHERE date_ref = @ref_date
    """
    params = [
        bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date),
        bigquery.ScalarQueryParameter("deadline", "TIME", config.signals_deadline),
        bigquery.ScalarQueryParameter("grace", "INT64", config.signals_grace_minutes),
    ]
    row = next(iter(_query(query, params)), None)
    total = int(getattr(row, "total", 0) or 0)
    last_created = getattr(row, "last_created_at", None)
    deadline_dt = getattr(row, "deadline_dt", None)
    status = "PASS"
    reason = None
    if total == 0:
        status = "FAIL"
        reason = "missing_signals"
    elif isinstance(last_created, dt.datetime) and isinstance(deadline_dt, dt.datetime):
        if last_created > deadline_dt:
            status = "FAIL"
            reason = "late_generation"
    details = {
        "rows": total,
        "last_created_at": str(last_created) if last_created else None,
        "deadline": str(deadline_dt) if deadline_dt else None,
    }
    if reason:
        details["reason"] = reason
    return CheckResult(
        name="signals_freshness",
        component=SIGNALS_TABLE_ID,
        status=status,
        details=details,
    )


def _check_backtest_metrics(
    reference_date: dt.date, trading_day: bool, config: PipelineConfig
) -> CheckResult:
    if not trading_day:
        return CheckResult(
            name="backtest_metrics",
            component=BACKTEST_METRICS_TABLE_ID,
            status="WARN",
            details={"reason": "non_trading_day"},
        )
    query = f"""
        SELECT
            COUNT(*) AS linhas,
            MAX(created_at) AS last_created_at,
            DATETIME_ADD(DATETIME(@ref_date, @deadline), INTERVAL @grace MINUTE) AS deadline_dt
        FROM `{_table_ref(BACKTEST_METRICS_TABLE_ID)}`
        WHERE as_of_date = @ref_date
    """
    params = [
        bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date),
        bigquery.ScalarQueryParameter("deadline", "TIME", config.backtest_deadline),
        bigquery.ScalarQueryParameter("grace", "INT64", config.backtest_grace_minutes),
    ]
    row = next(iter(_query(query, params)), None)
    rows = int(getattr(row, "linhas", 0) or 0)
    last_created = getattr(row, "last_created_at", None)
    deadline_dt = getattr(row, "deadline_dt", None)
    status = "PASS"
    reason = None
    if rows == 0:
        status = "FAIL"
        reason = "missing_backtest"
    elif isinstance(last_created, dt.datetime) and isinstance(deadline_dt, dt.datetime):
        if last_created > deadline_dt:
            status = "FAIL"
            reason = "late_backtest"
    details = {
        "rows": rows,
        "last_created_at": str(last_created) if last_created else None,
        "deadline": str(deadline_dt) if deadline_dt else None,
    }
    if reason:
        details["reason"] = reason
    return CheckResult(
        name="backtest_metrics",
        component=BACKTEST_METRICS_TABLE_ID,
        status=status,
        details=details,
    )


def _persist_results(
    reference_date: dt.date,
    run_logger: StructuredLogger,
    results: Sequence[CheckResult],
    config_version: str,
) -> None:
    if not results:
        return
    payloads = []
    created_at = _now_sp().replace(tzinfo=None)
    for result in results:
        payloads.append(
            {
                "check_date": reference_date,
                "check_name": result.name,
                "component": result.component,
                "status": result.status,
                "severity": result.severity,
                "details": json.dumps(result.details, ensure_ascii=False),
                "job_name": JOB_NAME,
                "run_id": run_logger.run_id,
                "config_version": config_version,
                "created_at": created_at,
            }
        )
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    _get_client().load_table_from_json(
        payloads,
        _table_ref(DQ_CHECKS_TABLE_ID),
        job_config=job_config,
    ).result()


def _persist_incidents(
    reference_date: dt.date,
    run_logger: StructuredLogger,
    results: Sequence[CheckResult],
    config_version: str,
) -> None:
    if not results:
        return
    payloads = []
    created_at = _now_sp().replace(tzinfo=None)
    for result in results:
        payloads.append(
            {
                "incident_id": (
                    f"{reference_date.isoformat()}_{result.name}_{run_logger.run_id}"
                ),
                "check_name": result.name,
                "check_date": reference_date,
                "status": result.status,
                "severity": result.severity,
                "details": json.dumps(result.details, ensure_ascii=False),
                "job_name": JOB_NAME,
                "run_id": run_logger.run_id,
                "config_version": config_version,
                "created_at": created_at,
            }
        )
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    _get_client().load_table_from_json(
        payloads,
        _table_ref(DQ_INCIDENTS_TABLE_ID),
        job_config=job_config,
    ).result()


def dq_checks(request: Any) -> Dict[str, Any]:
    """HTTP Cloud Function that records daily data-quality checks."""

    payload = _request_payload(request)
    reference_date = _parse_request_date(payload)
    run_logger = StructuredLogger(JOB_NAME)
    reason = _get_first_value(payload, ("reason",))
    mode = payload.get("mode")
    force = _as_bool(payload.get("force"))
    run_logger.update_context(
        date_ref=reference_date.isoformat(),
        reason=reason,
        mode=mode,
        force=force,
    )
    run_logger.started()
    trading_day = _is_trading_day(reference_date) or force
    config = _load_pipeline_config()
    run_logger.update_context(config_version=config.config_version)

    checks: List[CheckResult] = []
    check_functions = [
        ("daily_freshness", lambda: _check_daily_freshness(reference_date, config)),
        (
            "intraday_freshness",
            lambda: _check_intraday_freshness(reference_date, config),
        ),
        (
            "intraday_uniqueness",
            lambda: _check_intraday_uniqueness(reference_date, config),
        ),
        ("daily_uniqueness", lambda: _check_daily_uniqueness(reference_date)),
        ("ohlc_validity", lambda: _check_ohlc_validity(reference_date)),
        ("signals_limits", lambda: _check_signals(reference_date, trading_day)),
        (
            "signals_freshness",
            lambda: _check_signals_freshness(reference_date, config, trading_day),
        ),
        (
            "backtest_metrics",
            lambda: _check_backtest_metrics(reference_date, trading_day, config),
        ),
    ]

    for name, check_fn in check_functions:
        try:
            result = check_fn()
        except Exception as exc:  # noqa: BLE001
            logging.warning("Falha ao executar check %s: %s", name, exc, exc_info=True)
            run_logger.exception(exc, stage=name)
            result = CheckResult(
                name=name,
                component="unknown",
                status="FAIL",
                details={"error": str(exc)},
            )
        checks.append(result)

    _persist_results(reference_date, run_logger, checks, config.config_version)
    failures = [result for result in checks if result.status == "FAIL"]
    _persist_incidents(reference_date, run_logger, failures, config.config_version)

    if failures:
        run_logger.warn(
            "Checks concluídos com falhas",
            failures=len(failures),
            total=len(checks),
        )
    else:
        run_logger.ok("Checks concluídos", total=len(checks))

    return {
        "date_ref": reference_date.isoformat(),
        "config_version": config.config_version,
        "checks": len(checks),
        "failures": len(failures),
        "trading_day": trading_day,
        "reason": reason,
        "mode": mode,
        "force": force,
    }
