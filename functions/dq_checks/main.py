"""Daily data-quality checks persisted to BigQuery for Sisacao-8."""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence

from google.cloud import bigquery  # type: ignore[import-untyped]

from sisacao8.candles import SAO_PAULO_TZ
from sisacao8.observability import StructuredLogger

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
DAILY_COVERAGE_THRESHOLD = float(os.environ.get("DQ_DAILY_COVERAGE", "0.9"))
INTRADAY_COVERAGE_THRESHOLD = float(os.environ.get("DQ_INTRADAY_COVERAGE", "0.7"))
INTRADAY_MIN_TIME = os.environ.get("DQ_INTRADAY_MIN_TIME", "17:45:00")
SIGNAL_LIMIT = int(os.environ.get("DQ_MAX_SIGNALS", "5"))


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


def _now_sp() -> dt.datetime:
    return dt.datetime.now(tz=SAO_PAULO_TZ)


def _parse_request_date(request: Any) -> dt.date:
    if request and hasattr(request, "args") and request.args:
        requested = request.args.get("date")
        if requested:
            return dt.datetime.strptime(requested, "%Y-%m-%d").date()
    return _now_sp().date()


def _table_ref(table_id: str) -> str:
    return f"{_get_client().project}.{DATASET_ID}.{table_id}"


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


def _check_daily_freshness(reference_date: dt.date) -> CheckResult:
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
        threshold=DAILY_COVERAGE_THRESHOLD,
    )
    details = {
        "expected_tickers": expected,
        "available_tickers": available,
        "coverage_pct": round(coverage, 4),
        "threshold": DAILY_COVERAGE_THRESHOLD,
    }
    if expected == 0:
        details["warning"] = "Tabela de tickers está vazia"
    return CheckResult(
        name="daily_freshness",
        component=DAILY_TABLE_ID,
        status=status,
        details=details,
    )


def _check_intraday_freshness(reference_date: dt.date) -> CheckResult:
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
        bigquery.ScalarQueryParameter("min_time", "TIME", INTRADAY_MIN_TIME),
    ]
    row = next(iter(_query(query, params)), None)
    expected = int(getattr(row, "ativos", 0) or 0)
    recent = int(getattr(row, "tickers_recentes", 0) or 0)
    max_time = getattr(row, "hora_maxima", None)
    status, coverage = _coverage_status(
        available=recent,
        expected=expected,
        threshold=INTRADAY_COVERAGE_THRESHOLD,
    )
    details = {
        "expected_tickers": expected,
        "fresh_tickers": recent,
        "coverage_pct": round(coverage, 4),
        "threshold": INTRADAY_COVERAGE_THRESHOLD,
        "last_time": str(max_time) if max_time else None,
    }
    return CheckResult(
        name="intraday_freshness",
        component=RAW_TABLE_ID,
        status=status,
        details=details,
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
        invalid_side
        + invalid_buy
        + invalid_buy_stop
        + invalid_sell
        + invalid_sell_stop
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


def _check_backtest_metrics(reference_date: dt.date, trading_day: bool) -> CheckResult:
    if not trading_day:
        return CheckResult(
            name="backtest_metrics",
            component=BACKTEST_METRICS_TABLE_ID,
            status="WARN",
            details={"reason": "non_trading_day"},
        )
    query = f"""
        SELECT COUNT(*) AS linhas
        FROM `{_table_ref(BACKTEST_METRICS_TABLE_ID)}`
        WHERE as_of_date = @ref_date
    """
    params = [bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)]
    row = next(iter(_query(query, params)), None)
    rows = int(getattr(row, "linhas", 0) or 0)
    status = "PASS" if rows > 0 else "FAIL"
    return CheckResult(
        name="backtest_metrics",
        component=BACKTEST_METRICS_TABLE_ID,
        status=status,
        details={"rows": rows},
    )


def _persist_results(
    reference_date: dt.date,
    run_logger: StructuredLogger,
    results: Sequence[CheckResult],
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

    reference_date = _parse_request_date(request)
    run_logger = StructuredLogger(JOB_NAME)
    run_logger.update_context(date_ref=reference_date.isoformat())
    run_logger.started()
    trading_day = _is_trading_day(reference_date)

    checks: List[CheckResult] = []
    check_functions = [
        ("daily_freshness", lambda: _check_daily_freshness(reference_date)),
        ("intraday_freshness", lambda: _check_intraday_freshness(reference_date)),
        ("daily_uniqueness", lambda: _check_daily_uniqueness(reference_date)),
        ("ohlc_validity", lambda: _check_ohlc_validity(reference_date)),
        ("signals_limits", lambda: _check_signals(reference_date, trading_day)),
        (
            "backtest_metrics",
            lambda: _check_backtest_metrics(reference_date, trading_day),
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

    _persist_results(reference_date, run_logger, checks)
    failures = [result for result in checks if result.status == "FAIL"]
    _persist_incidents(reference_date, run_logger, failures)

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
        "checks": len(checks),
        "failures": len(failures),
        "trading_day": trading_day,
    }
