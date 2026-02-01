"""Cloud Run function to fetch Google Finance prices."""

from __future__ import annotations

import datetime
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from sys import version_info
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    import pandas as pd  # type: ignore[import-untyped]
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    pd = None  # type: ignore[assignment]
from google.cloud import bigquery  # type: ignore[import-untyped]

try:
    from flask import Response as FlaskResponse  # type: ignore[import-untyped]
except ModuleNotFoundError:  # pragma: no cover - flask is optional for tests
    FlaskResponse = None  # type: ignore[assignment]


class _FallbackResponse:
    """Minimal stand-in for :class:`flask.Response` used in tests."""

    def __init__(
        self,
        response: Any,
        status: int = 200,
        mimetype: str | None = "application/json",
    ) -> None:
        if isinstance(response, bytes):
            self._data = response
        else:
            self._data = str(response).encode("utf-8")
        self.status_code = status
        self.mimetype = mimetype

    def get_data(self, as_text: bool = False) -> str | bytes:
        """Return stored payload mirroring ``flask.Response`` semantics."""

        if as_text:
            return self._data.decode("utf-8")
        return self._data


Response = FlaskResponse or _FallbackResponse

if version_info >= (3, 9):  # pragma: no branch - runtime dependent import
    from zoneinfo import ZoneInfo
else:  # pragma: no branch - runtime dependent import
    try:
        from backports.zoneinfo import ZoneInfo  # type: ignore[import-untyped]
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        ZoneInfo = None  # type: ignore[assignment]

try:
    from pytz import timezone  # type: ignore[import-untyped]
except ModuleNotFoundError:  # pragma: no cover - fallback when pytz is absent

    def timezone(name: str):  # type: ignore[misc]
        """Return timezone instance even when optional deps are missing."""

        if ZoneInfo is not None:  # pragma: no branch - runtime guard
            return ZoneInfo(name)

        if name != "America/Sao_Paulo":  # pragma: no cover - defensive branch
            raise ModuleNotFoundError(
                f"Timezone support unavailable for name: {name}"
            )

        return datetime.timezone(  # type: ignore[return-value]
            datetime.timedelta(hours=-3),
            name,
        )

try:
    from functions.google_finance_price.google_scraper import (
        fetch_google_finance_price,
    )
except ImportError:  # pragma: no cover - fallback when imported as a package
    try:
        from .google_scraper import fetch_google_finance_price
    except ImportError:  # pragma: no cover - when executed as a script in Cloud Run
        import importlib

        fetch_google_finance_price = importlib.import_module(
            "google_scraper"
        ).fetch_google_finance_price

logger = logging.getLogger(__name__)

DATASET_ID = "cotacao_intraday"
TABELA_ID = "cotacao_bovespa"

client = bigquery.Client()

app: Optional[Any] = None


DEFAULT_FALLBACK_TICKERS = [
    "PETR4",
    "VALE3",
    "ITUB4",
    "BBDC4",
    "BBAS3",
    "IBOV",
]
FALLBACK_TICKERS_ENV = "FALLBACK_TICKERS"
FALLBACK_TICKERS_FILE_ENV = "FALLBACK_TICKERS_FILE"
MAX_INTRADAY_TICKERS_ENV = "MAX_INTRADAY_TICKERS"
MAX_WORKERS_ENV = "GOOGLE_FINANCE_MAX_WORKERS"
FUNCTION_DEADLINE_SECONDS_ENV = "FUNCTION_DEADLINE_SECONDS"
BATCH_SIZE_ENV = "GOOGLE_FINANCE_BATCH_SIZE"
DEFAULT_TICKERS_FILE = (
    Path(__file__).resolve().parent.parent
    / "get_stock_data"
    / "tickers.txt"
)


def _max_intraday_tickers() -> int:
    raw_value = os.environ.get(MAX_INTRADAY_TICKERS_ENV)
    if not raw_value:
        return 50
    try:
        parsed = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid value '%s' for %s. Falling back to 50 tickers.",
            raw_value,
            MAX_INTRADAY_TICKERS_ENV,
        )
        return 50
    return parsed if parsed > 0 else 50


def _max_workers(ticker_count: int | None = None) -> int:
    """Return the number of concurrent workers to fetch prices."""

    raw_value = os.environ.get(MAX_WORKERS_ENV)
    default_workers = 5
    if not raw_value:
        return min(default_workers, ticker_count or default_workers)
    try:
        parsed = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid value '%s' for %s. Falling back to %s workers.",
            raw_value,
            MAX_WORKERS_ENV,
            default_workers,
        )
        return min(default_workers, ticker_count or default_workers)

    if parsed <= 0:
        return min(default_workers, ticker_count or default_workers)

    # Keep a sane upper bound to avoid overwhelming Google Finance.
    bounded = min(parsed, 16)
    return min(bounded, ticker_count or bounded)


def _function_deadline_seconds() -> float:
    """Return the maximum time the request should run before aborting."""

    raw_value = os.environ.get(FUNCTION_DEADLINE_SECONDS_ENV)
    default_deadline = 55.0
    if not raw_value:
        return default_deadline
    try:
        parsed = float(raw_value)
    except ValueError:
        logger.warning(
            "Invalid value '%s' for %s. Falling back to %.1f seconds.",
            raw_value,
            FUNCTION_DEADLINE_SECONDS_ENV,
            default_deadline,
        )
        return default_deadline

    # Never allow a value too small to finish at least a couple requests.
    return max(10.0, parsed)


def _batch_size() -> int:
    raw_value = os.environ.get(BATCH_SIZE_ENV)
    default_size = 10
    if not raw_value:
        return default_size
    try:
        parsed = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid value '%s' for %s. Falling back to %s rows.",
            raw_value,
            BATCH_SIZE_ENV,
            default_size,
        )
        return default_size
    if parsed <= 0:
        return default_size
    return min(parsed, 200)


def _normalize_ticker_list(values: Iterable[Any]) -> List[str]:
    tickers: List[str] = []
    for raw in values:
        ticker = str(raw).strip().upper()
        if ticker and ticker not in tickers:
            tickers.append(ticker)
    return tickers


def _load_tickers_from_file(path: Path) -> List[str]:
    try:
        return _normalize_ticker_list(path.read_text(encoding="utf-8").splitlines())
    except OSError:
        logger.warning("Fallback tickers file not accessible: %%s", path)
        return []


def _fallback_tickers() -> List[str]:
    env_value = os.environ.get(FALLBACK_TICKERS_ENV)
    if env_value:
        tickers = _normalize_ticker_list(env_value.split(","))
        if tickers:
            logger.warning(
                "Using fallback tickers from environment variable %s: %s",
                FALLBACK_TICKERS_ENV,
                tickers,
            )
            return tickers[: _max_intraday_tickers()]

    file_override = os.environ.get(FALLBACK_TICKERS_FILE_ENV)
    if file_override:
        tickers = _load_tickers_from_file(Path(file_override))
        if tickers:
            logger.warning(
                "Using fallback tickers from file specified in %s: %s",
                FALLBACK_TICKERS_FILE_ENV,
                tickers,
            )
            return tickers[: _max_intraday_tickers()]

    tickers = _load_tickers_from_file(DEFAULT_TICKERS_FILE)
    if tickers:
        logger.warning(
            "Using fallback tickers from default file %s",
            DEFAULT_TICKERS_FILE,
        )
        return tickers[: _max_intraday_tickers()]

    logger.warning(
        "Fallback tickers file %s not found. Falling back to built-in defaults.",
        DEFAULT_TICKERS_FILE,
    )
    return DEFAULT_FALLBACK_TICKERS[: _max_intraday_tickers()]


def _normalize_time_value(raw_value: Any) -> str:
    """Return a BigQuery compatible ``TIME`` value."""

    if isinstance(raw_value, datetime.time):
        return raw_value.strftime("%H:%M:%S")
    value = str(raw_value)
    if len(value) == 5:
        return f"{value}:00"
    if len(value) == 8:
        return value
    return value


def _normalize_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert iterable of rows into BigQuery friendly dictionaries."""

    normalized: List[Dict[str, Any]] = []
    for row in rows:
        record = dict(row)
        data_value = record.get("data")
        if isinstance(data_value, datetime.date):
            record["data"] = data_value.isoformat()
        hora_value = record.get("hora")
        if hora_value is not None:
            record["hora"] = _normalize_time_value(hora_value)
        hora_atual_value = record.get("hora_atual")
        if hora_atual_value is not None:
            record["hora_atual"] = _normalize_time_value(hora_atual_value)
        data_hora_value = record.get("data_hora_atual")
        if isinstance(data_hora_value, datetime.datetime):
            record["data_hora_atual"] = data_hora_value.isoformat()
        normalized.append(record)
    return normalized


def append_dataframe_to_bigquery(data: Any) -> None:
    """Append data to the BigQuery table accepting DataFrame or JSON rows."""

    try:
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

        inserted_rows: int
        if pd is not None and isinstance(data, pd.DataFrame):
            df = data.copy()
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

            job = client.load_table_from_dataframe(
                df,
                tabela_id,
                job_config=job_config,
            )
            inserted_rows = len(df)
        else:
            rows = list(data) if not isinstance(data, list) else data
            logger.warning(
                "Received %s rows without pandas installed", len(rows)
            )
            normalized_rows = _normalize_rows(rows)
            job = client.load_table_from_json(
                normalized_rows,
                tabela_id,
                job_config=job_config,
            )
            inserted_rows = len(rows)
        job.result()
        logger.warning(
            "Data inserted successfully into BigQuery (%s rows).",
            inserted_rows,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to insert data into BigQuery: %s",
            exc,
            exc_info=True,
        )


def _append_rows(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    logger.warning("Appending %s rows to BigQuery.", len(rows))
    if pd is not None:
        append_dataframe_to_bigquery(pd.DataFrame(rows))
    else:
        append_dataframe_to_bigquery(rows)


def fetch_active_tickers() -> List[str]:
    """Return list of active tickers from ``acao_bovespa`` table."""
    table_id = f"{client.project}.{DATASET_ID}.acao_bovespa"
    query = f"SELECT ticker FROM `{table_id}` WHERE ativo = TRUE"
    try:
        query_job = client.query(query)
        tickers: List[str] = []
        if pd is not None:
            df = query_job.to_dataframe()
            if "ticker" in df.columns:
                tickers = _normalize_ticker_list(df["ticker"].tolist())
            else:
                logger.warning(
                    "BigQuery table %s did not return a 'ticker' column. "
                    "Using fallback list.",
                    table_id,
                )
        else:
            results = query_job.result()
            tickers = _normalize_ticker_list(row["ticker"] for row in results)

        if tickers:
            max_items = _max_intraday_tickers()
            if len(tickers) > max_items:
                logger.warning(
                    "Limiting active tickers from %s to %s for intraday collection.",
                    len(tickers),
                    max_items,
                )
            return tickers[:max_items]

        logger.warning(
            "BigQuery table %s returned no active tickers. Falling back to local list.",
            table_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to fetch active tickers from BigQuery table %s: %s",
            table_id,
            exc,
            exc_info=True,
        )
    return _fallback_tickers()


def _exception_details(error: BaseException) -> Dict[str, Any]:
    """Return structured diagnostic details for ``error``."""

    details: Dict[str, Any] = {
        "type": error.__class__.__name__,
        "message": str(error),
    }
    extra: Any = None
    if hasattr(error, "details"):
        extra = getattr(error, "details")
        if callable(extra):
            try:
                extra = extra()
            except Exception:  # pragma: no cover - defensive
                extra = None
    if isinstance(extra, dict):
        for key, value in extra.items():
            details.setdefault(key, value)
    cause = getattr(error, "__cause__", None)
    if cause is not None:
        details.setdefault("cause", f"{cause.__class__.__name__}: {cause}")
    return details


def _build_response(payload: Dict[str, Any], status: int) -> Response:
    """Return an HTTP JSON response compatible with Cloud Run."""

    body = json.dumps(payload, ensure_ascii=False)
    return Response(body, status=status, mimetype="application/json")


def _build_price_row(
    ticker: str,
    data_atual: str,
    hora_atual: str,
    data_hora_atual: datetime.datetime,
) -> Dict[str, Any]:
    """Fetch price for ``ticker`` and return the BigQuery row payload."""

    price = fetch_google_finance_price(ticker)
    return {
        "ticker": ticker,
        "data": data_atual,
        "hora": hora_atual,
        "valor": round(price, 2),
        "hora_atual": hora_atual,
        "data_hora_atual": data_hora_atual,
    }


def google_finance_price(request: Any) -> Response:
    """HTTP Cloud Run entry point returning latest prices for active
    tickers."""

    brasil_tz = timezone("America/Sao_Paulo")
    now = datetime.datetime.now(brasil_tz)
    data_atual = now.strftime("%Y-%m-%d")
    hora_atual = now.strftime("%H:%M")
    data_hora_atual = now

    try:
        tickers = fetch_active_tickers()
    except Exception as exc:  # noqa: BLE001
        return _build_response({"error": str(exc)}, 500)

    rows: List[Dict[str, Any]] = []
    batch_rows: List[Dict[str, Any]] = []
    error_messages: List[str] = []
    error_details: List[Dict[str, Any]] = []

    deadline_seconds = _function_deadline_seconds()
    deadline = time.monotonic() + deadline_seconds
    max_workers = _max_workers(len(tickers))
    batch_size = _batch_size()
    logger.warning(
        "Fetching prices for %s tickers using %s workers (deadline %.1fs, batch %s)",
        len(tickers),
        max_workers,
        deadline_seconds,
        batch_size,
    )

    timed_out = False
    executor = ThreadPoolExecutor(max_workers=max_workers)
    future_to_ticker: Dict[Any, str] = {}
    try:
        for ticker in tickers:
            if time.monotonic() >= deadline:
                timed_out = True
                break
            future = executor.submit(
                _build_price_row,
                ticker,
                data_atual,
                hora_atual,
                data_hora_atual,
            )
            future_to_ticker[future] = ticker

        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            if time.monotonic() >= deadline:
                timed_out = True
                break
            try:
                row = future.result()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to fetch price for ticker %s: %s",
                    ticker,
                    exc,
                    exc_info=True,
                )
                details = _exception_details(exc)
                details.setdefault("ticker", ticker)
                error_details.append(details)
                message = details.get("message", str(exc))
                error_messages.append(f"{ticker}: {message}")
            else:
                rows.append(row)
                batch_rows.append(row)
                if len(batch_rows) >= batch_size:
                    _append_rows(batch_rows)
                    batch_rows.clear()
    finally:
        executor.shutdown(wait=not timed_out, cancel_futures=timed_out)

    if batch_rows:
        _append_rows(batch_rows)
        batch_rows.clear()

    if timed_out:
        skipped = len(tickers) - len(rows) - len(error_details)
        message = "Tempo limite atingido; algumas coletas foram interrompidas"
        if skipped > 0:
            message += f" ({skipped} tickers restantes)"
        error_messages.append(message)
        error_details.append({"type": "Timeout", "message": message})

    if rows:
        response: Dict[str, Any] = {
            "tickers": tickers,
            "processed": len(rows),
        }
        if error_details:
            response["errors"] = error_details
        status = 200 if not error_details else 207
        return _build_response(response, status)

    payload: Dict[str, Any] = {
        "error": "; ".join(error_messages) or "No tickers processed",
    }
    if error_details:
        payload["errors"] = error_details
    return _build_response(payload, 500)


def _create_flask_app() -> Any:
    """Return a lightweight Flask app that proxies to the function."""

    try:
        from flask import Flask, request  # type: ignore[import-untyped]
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        logger.warning(
            "Flask is not installed. Skipping creation of the development app."
        )
        return None

    flask_app = Flask(__name__)

    @flask_app.route("/", methods=["GET", "POST"])
    def _entrypoint():  # noqa: D401
        return google_finance_price(request)

    return flask_app


app = _create_flask_app()


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    port = int(os.environ.get("PORT", "8080"))
    flask_app = _create_flask_app() if app is None else app
    if flask_app is None:
        raise RuntimeError(
            "Flask is required to run the development server but is not installed."
        )
    flask_app.run(host="0.0.0.0", port=port)
