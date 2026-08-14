"""Research-only pilot collector for Binance Spot cryptocurrency candles."""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
from typing import Any, Iterable, Mapping, Sequence
from urllib import parse, request
from uuid import uuid4

from google.cloud import bigquery

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GCP_PROJECT", "ingestaokraken")
DATASET_ID = os.environ.get("BQ_CRYPTO_DATASET", "crypto_market")
TABLE_ID = os.environ.get("BQ_CRYPTO_CANDLES_1M_TABLE", "candles_1m")
BQ_LOCATION = os.environ.get("BQ_LOCATION", "us-east1")
BINANCE_API_BASE_URL = os.environ.get(
    # Public market-data-only endpoint.  Unlike the trading API hostname, this
    # endpoint is reachable from the current GCP/CI regions and needs no key.
    "BINANCE_API_BASE_URL",
    "https://data-api.binance.vision",
).rstrip("/")
DEFAULT_PAIRS = tuple(
    pair.strip().upper()
    for pair in os.environ.get("CRYPTO_PILOT_PAIRS", "BTCUSDT,ETHUSDT").split(",")
    if pair.strip()
)
DEFAULT_LIMIT = int(os.environ.get("CRYPTO_PILOT_LIMIT", "5"))
MAX_LIMIT = 1000
INTERVAL = "1m"
SOURCE = "binance_spot_rest"
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("CRYPTO_REQUEST_TIMEOUT_SECONDS", "20"))

_BQ_CLIENT: bigquery.Client | None = None

CANDLE_SCHEMA = (
    bigquery.SchemaField("exchange", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("symbol", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("base_asset", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("quote_asset", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("interval", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("event_time", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("close_time", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("open", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("high", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("low", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("close", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("base_volume", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("quote_volume", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("trade_count", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("taker_buy_base_volume", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("taker_buy_quote_volume", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("job_run_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("data_quality_flags", "STRING", mode="REPEATED"),
)


def crypto_market_pilot(http_request: Any) -> tuple[dict[str, Any], int]:
    """Fetch closed BTC/ETH one-minute candles and idempotently store them."""

    payload = _request_payload(http_request)
    try:
        pairs = _normalize_pairs(payload.get("pairs", DEFAULT_PAIRS))
        limit = _bounded_limit(payload.get("limit", DEFAULT_LIMIT))
        start_time = _optional_epoch_ms(payload.get("start_time"))
        end_time = _optional_epoch_ms(payload.get("end_time"))
        dry_run = _as_bool(payload.get("dry_run", False))
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}, 400

    now = dt.datetime.now(dt.timezone.utc)
    job_run_id = f"crypto_pilot_{now:%Y%m%d_%H%M%S}_{uuid4().hex[:8]}"
    rows: list[dict[str, Any]] = []
    failures: dict[str, str] = {}
    for symbol in pairs:
        try:
            raw_klines = _fetch_klines(
                symbol=symbol,
                limit=limit,
                start_time=start_time,
                end_time=end_time,
            )
            rows.extend(
                _parse_closed_klines(
                    symbol=symbol,
                    raw_klines=raw_klines,
                    now=now,
                    ingested_at=now,
                    job_run_id=job_run_id,
                )
            )
        except Exception as exc:  # noqa: BLE001 - report failure per pair.
            logger.exception("Crypto pilot collection failed for %s", symbol)
            failures[symbol] = str(exc)

    if not rows and failures:
        return {
            "status": "error",
            "job_run_id": job_run_id,
            "pairs": list(pairs),
            "failures": failures,
            "row_count": 0,
        }, 502

    persisted_count = 0
    if rows and not dry_run:
        try:
            _ensure_destination_table(_get_bigquery_client())
            _merge_rows(_get_bigquery_client(), rows, job_run_id)
            persisted_count = len(rows)
        except Exception as exc:  # noqa: BLE001 - return observable storage failure.
            logger.exception("Crypto pilot BigQuery persistence failed")
            return {
                "status": "error",
                "job_run_id": job_run_id,
                "pairs": list(pairs),
                "failures": {**failures, "bigquery": str(exc)},
                "row_count": len(rows),
                "persisted_count": 0,
            }, 500

    return {
        "status": "ok" if not failures else "partial",
        "job_run_id": job_run_id,
        "pairs": list(pairs),
        "interval": INTERVAL,
        "dry_run": dry_run,
        "row_count": len(rows),
        "persisted_count": persisted_count,
        "failures": failures,
        "first_event_time": min((row["event_time"] for row in rows), default=None),
        "last_event_time": max((row["event_time"] for row in rows), default=None),
    }, 200


def _request_payload(http_request: Any) -> Mapping[str, Any]:
    if http_request is None:
        return {}
    if isinstance(http_request, Mapping):
        return http_request
    payload = http_request.get_json(silent=True)
    return payload if isinstance(payload, Mapping) else {}


def _normalize_pairs(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        values: Iterable[Any] = value.split(",")
    elif isinstance(value, Sequence):
        values = value
    else:
        raise ValueError("pairs deve ser string CSV ou lista")
    pairs: list[str] = []
    for item in values:
        symbol = str(item).strip().upper()
        if not symbol:
            continue
        if not symbol.isalnum() or len(symbol) > 20:
            raise ValueError(f"par inválido: {symbol}")
        if symbol not in pairs:
            pairs.append(symbol)
    if not pairs:
        raise ValueError("ao menos um par é obrigatório")
    if len(pairs) > 10:
        raise ValueError("piloto limitado a 10 pares por execução")
    return tuple(pairs)


def _bounded_limit(value: Any) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("limit deve ser inteiro") from exc
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit deve estar entre 1 e {MAX_LIMIT}")
    return limit


def _optional_epoch_ms(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"timestamp inválido: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return int(parsed.timestamp() * 1000)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "sim"}


def _fetch_klines(
    *, symbol: str, limit: int, start_time: int | None, end_time: int | None
) -> list[list[Any]]:
    params: dict[str, Any] = {
        "symbol": symbol,
        "interval": INTERVAL,
        "limit": limit,
    }
    if start_time is not None:
        params["startTime"] = start_time
    if end_time is not None:
        params["endTime"] = end_time
    url = f"{BINANCE_API_BASE_URL}/api/v3/klines?{parse.urlencode(params)}"
    req = request.Request(url, headers={"Accept": "application/json"})
    with request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"resposta Binance inválida para {symbol}")
    return payload


def _parse_closed_klines(
    *,
    symbol: str,
    raw_klines: Iterable[Sequence[Any]],
    now: dt.datetime,
    ingested_at: dt.datetime,
    job_run_id: str,
) -> list[dict[str, Any]]:
    base_asset, quote_asset = _split_symbol(symbol)
    rows: list[dict[str, Any]] = []
    for raw in raw_klines:
        if len(raw) < 11:
            raise ValueError(f"kline incompleto para {symbol}")
        event_time = _from_epoch_ms(raw[0])
        close_time = _from_epoch_ms(raw[6])
        if close_time > now:
            continue
        open_price, high, low, close = (float(raw[index]) for index in range(1, 5))
        base_volume = float(raw[5])
        quote_volume = float(raw[7])
        trade_count = int(raw[8])
        flags = _quality_flags(
            open_price=open_price,
            high=high,
            low=low,
            close=close,
            base_volume=base_volume,
            quote_volume=quote_volume,
            trade_count=trade_count,
        )
        rows.append(
            {
                "exchange": "BINANCE",
                "symbol": symbol,
                "base_asset": base_asset,
                "quote_asset": quote_asset,
                "interval": INTERVAL,
                "event_time": event_time.isoformat(),
                "close_time": close_time.isoformat(),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "base_volume": base_volume,
                "quote_volume": quote_volume,
                "trade_count": trade_count,
                "taker_buy_base_volume": float(raw[9]),
                "taker_buy_quote_volume": float(raw[10]),
                "source": SOURCE,
                "ingested_at": ingested_at.isoformat(),
                "job_run_id": job_run_id,
                "data_quality_flags": flags,
            }
        )
    return rows


def _split_symbol(symbol: str) -> tuple[str, str]:
    for quote_asset in ("USDT", "USDC", "FDUSD", "BTC", "ETH", "BRL"):
        if symbol.endswith(quote_asset) and len(symbol) > len(quote_asset):
            return symbol[: -len(quote_asset)], quote_asset
    raise ValueError(f"não foi possível identificar o ativo de cotação: {symbol}")


def _from_epoch_ms(value: Any) -> dt.datetime:
    return dt.datetime.fromtimestamp(int(value) / 1000, tz=dt.timezone.utc)


def _quality_flags(
    *,
    open_price: float,
    high: float,
    low: float,
    close: float,
    base_volume: float,
    quote_volume: float,
    trade_count: int,
) -> list[str]:
    flags: list[str] = []
    if min(open_price, high, low, close) <= 0:
        flags.append("NON_POSITIVE_PRICE")
    if high < max(open_price, low, close) or low > min(open_price, high, close):
        flags.append("INVALID_OHLC_RANGE")
    if base_volume < 0 or quote_volume < 0:
        flags.append("NEGATIVE_VOLUME")
    if trade_count < 0:
        flags.append("NEGATIVE_TRADE_COUNT")
    return flags


def _get_bigquery_client() -> bigquery.Client:
    global _BQ_CLIENT
    if _BQ_CLIENT is None:
        _BQ_CLIENT = bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)
    return _BQ_CLIENT


def _destination_table_id() -> str:
    return f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"


def _ensure_destination_table(client: bigquery.Client) -> None:
    dataset_id = f"{PROJECT_ID}.{DATASET_ID}"
    # Dataset/IAM provisioning is an operator responsibility.  Keeping it out
    # of the runtime avoids granting broad project-level datasets.create.
    client.get_dataset(dataset_id)
    table = bigquery.Table(_destination_table_id(), schema=CANDLE_SCHEMA)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="event_time",
    )
    table.clustering_fields = ["exchange", "symbol"]
    client.create_table(table, exists_ok=True)


def _merge_rows(
    client: bigquery.Client, rows: list[dict[str, Any]], job_run_id: str
) -> None:
    staging_table_id = f"{PROJECT_ID}.{DATASET_ID}._candles_1m_{job_run_id}"
    staging = bigquery.Table(staging_table_id, schema=CANDLE_SCHEMA)
    staging.expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
    client.create_table(staging)
    try:
        load_job = client.load_table_from_json(
            rows,
            staging_table_id,
            job_config=bigquery.LoadJobConfig(
                schema=CANDLE_SCHEMA,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            ),
        )
        load_job.result()
        columns = [field.name for field in CANDLE_SCHEMA]
        update_columns = [
            column
            for column in columns
            if column not in {"exchange", "symbol", "interval", "event_time"}
        ]
        merge_sql = (
            f"MERGE `{_destination_table_id()}` AS target "
            f"USING `{staging_table_id}` AS source "
            "ON target.`exchange` = source.`exchange` "
            "AND target.`symbol` = source.`symbol` "
            "AND target.`interval` = source.`interval` "
            "AND target.`event_time` = source.`event_time` "
            "WHEN MATCHED THEN UPDATE SET "
            + ", ".join(
                f"target.`{column}` = source.`{column}`" for column in update_columns
            )
            + " WHEN NOT MATCHED THEN INSERT ("
            + ", ".join(f"`{column}`" for column in columns)
            + ") VALUES ("
            + ", ".join(f"source.`{column}`" for column in columns)
            + ")"
        )
        client.query(merge_sql).result()
    finally:
        client.delete_table(staging_table_id, not_found_ok=True)
