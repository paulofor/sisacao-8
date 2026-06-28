"""Cloud Function that materializes the supervised neural EOD training dataset."""

from __future__ import annotations

import datetime as dt
import json
import logging
import math
import numbers
import os
from typing import Any, Dict, Mapping
from uuid import uuid4

import pandas as pd
from google.cloud import bigquery  # type: ignore[import-untyped]

from sisacao8.neural_dataset import (
    BarrierLabelConfig,
    NestedWalkForwardConfig,
    TemporalSplitConfig,
    build_dataset_manifest,
    build_training_dataset,
)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))

DATASET_ID = os.environ.get("BQ_INTRADAY_DATASET", "cotacao_intraday")
DAILY_TABLE_ID = os.environ.get("BQ_DAILY_TABLE", "cotacao_ohlcv_diario")
HOLIDAYS_TABLE_ID = os.environ.get("BQ_HOLIDAYS_TABLE", "feriados_b3")
TRAINING_DATASET_TABLE_ID = os.environ.get(
    "BQ_NEURAL_TRAINING_DATASET_TABLE", "neural_eod_training_dataset"
)
MANIFESTS_TABLE_ID = os.environ.get(
    "BQ_NEURAL_DATASET_MANIFESTS_TABLE", "neural_dataset_manifests"
)
PROTOCOL_VERSION = os.environ.get("NEURAL_PROTOCOL_VERSION", "neural_eod_protocol_v1")
UNIVERSE_VERSION = os.environ.get("NEURAL_UNIVERSE_VERSION", "b3_point_in_time_v1")
BQ_LOCATION = os.environ.get("BQ_LOCATION", "us-east1").replace("region-", "")
DEFAULT_LOOKBACK_DAYS = int(os.environ.get("NEURAL_TRAINING_LOOKBACK_DAYS", "1825"))
DEFAULT_MIN_HISTORY_DAYS = int(os.environ.get("NEURAL_TRAINING_MIN_HISTORY_DAYS", "20"))
INTEGER_FIELDS = {"days_to_event_buy", "days_to_event_sell", "holding_sessions"}

TRAINING_DATASET_COLUMNS = [
    "ticker",
    "reference_date",
    "valid_for",
    "feature_version",
    "label_version",
    "dataset_split",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "financial_volume",
    "log_return_1d",
    "log_return_5d",
    "log_return_10d",
    "log_return_20d",
    "log_financial_volume",
    "log_volume",
    "return_5d",
    "return_10d",
    "return_20d",
    "volatility_10d",
    "volatility_20d",
    "daily_range_pct",
    "intraday_return_pct",
    "gap_open_pct",
    "financial_volume_z20",
    "volume_ratio_20d",
    "distance_high_20d_pct",
    "distance_low_20d_pct",
    "distance_sma_20d_pct",
    "has_missing_ohlcv",
    "has_zero_volume",
    "is_suspicious_candle",
    "label_class",
    "future_return",
    "buy_net_return",
    "sell_net_return",
    "entry_filled_buy",
    "entry_filled_sell",
    "days_to_event_buy",
    "days_to_event_sell",
    "trade_side",
    "entry_filled",
    "entry_date",
    "entry_price",
    "exit_date",
    "exit_price",
    "exit_reason",
    "gross_return",
    "net_return",
    "holding_sessions",
    "max_adverse_excursion",
    "max_favorable_excursion",
    "execution_policy_version",
    "created_at",
    "dataset_snapshot",
    "metadata_json",
    "temporal_protocol_json",
]

_BQ_CLIENT: bigquery.Client | None = None


def _get_client() -> bigquery.Client:
    global _BQ_CLIENT
    if _BQ_CLIENT is None:
        _BQ_CLIENT = bigquery.Client(location=BQ_LOCATION)
    return _BQ_CLIENT


def neural_training_dataset(request: Any) -> tuple[Dict[str, Any], int]:
    """HTTP entrypoint that builds and loads the neural EOD training dataset."""

    try:
        return _neural_training_dataset(request)
    except Exception as exc:  # noqa: BLE001
        logging.exception("neural_training_dataset failed")
        return {
            "status": "error",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }, 500


def _neural_training_dataset(request: Any) -> tuple[Dict[str, Any], int]:
    payload = _request_payload(request)
    client = _get_client()
    end_date = (
        _parse_date(payload.get("end_date") or payload.get("date_ref"))
        or _default_end_date()
    )
    start_date = _parse_date(payload.get("start_date")) or (
        end_date - dt.timedelta(days=DEFAULT_LOOKBACK_DAYS)
    )
    if start_date >= end_date:
        raise ValueError("start_date must be earlier than end_date")

    snapshot = str(
        payload.get("dataset_snapshot")
        or f"neural_eod_training_dataset_{end_date.isoformat()}_{uuid4().hex[:8]}"
    )
    replace_snapshot = _as_bool(payload.get("replace_snapshot", True))

    candles = _load_candles(client, start_date, end_date)
    holidays = _load_holidays(client, start_date, end_date + dt.timedelta(days=30))
    label_config = _label_config(payload)
    split_config = _split_config(payload, label_config)
    nested_split_config = _nested_split_config(payload, label_config)
    dataset = build_training_dataset(
        candles,
        holidays=holidays,
        label_config=label_config,
        split_config=split_config,
        nested_split_config=nested_split_config,
        min_history_days=_int_payload(
            payload, "min_history_days", DEFAULT_MIN_HISTORY_DAYS
        ),
    )
    manifest = build_dataset_manifest(
        dataset,
        dataset_snapshot=snapshot,
        protocol_version=str(payload.get("protocol_version") or PROTOCOL_VERSION),
        universe_version=str(payload.get("universe_version") or UNIVERSE_VERSION),
        query_text=_candles_query_text(),
        code_text=_dataset_code_contract(),
        label_config=label_config,
    )
    dataset = _prepare_for_bigquery(dataset, snapshot, manifest.to_json_dict())
    if replace_snapshot:
        _delete_snapshot(client, snapshot)
    inserted = _load_dataset(client, dataset)
    _load_manifest(client, manifest.to_json_dict())
    split_counts = _split_counts(dataset)

    logging.info(
        "[snapshot=%s] neural_training_dataset finished start=%s end=%s rows=%s",
        snapshot,
        start_date.isoformat(),
        end_date.isoformat(),
        inserted,
    )
    return {
        "status": "ok",
        "dataset_snapshot": snapshot,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "rows": inserted,
        "splits": split_counts,
        "manifest": manifest.to_json_dict(),
    }, 200


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
            data.update(
                {key: value for key, value in body.items() if value is not None}
            )
    return data


def _default_end_date() -> dt.date:
    now_brt = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3)))
    if now_brt.time() >= dt.time(18, 0):
        return now_brt.date()
    return now_brt.date() - dt.timedelta(days=1)


def _parse_date(value: Any) -> dt.date | None:
    if not value:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.datetime.strptime(str(value), "%Y-%m-%d").date()


def _int_payload(payload: Mapping[str, Any], key: str, default: int) -> int:
    value = payload.get(key)
    if value is None or value == "":
        return default
    return int(value)


def _float_payload(payload: Mapping[str, Any], key: str, default: float) -> float:
    value = payload.get(key)
    if value is None or value == "":
        return default
    return float(value)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _label_config(payload: Mapping[str, Any]) -> BarrierLabelConfig:
    defaults = BarrierLabelConfig()
    return BarrierLabelConfig(
        entry_pct=_float_payload(payload, "entry_pct", defaults.entry_pct),
        target_pct=_float_payload(payload, "target_pct", defaults.target_pct),
        stop_pct=_float_payload(payload, "stop_pct", defaults.stop_pct),
        horizon_days=_int_payload(payload, "horizon_days", defaults.horizon_days),
        min_net_return_pct=_float_payload(
            payload, "min_net_return_pct", defaults.min_net_return_pct
        ),
    )


def _split_config(
    payload: Mapping[str, Any], label_config: BarrierLabelConfig | None = None
) -> TemporalSplitConfig:
    defaults = TemporalSplitConfig()
    horizon_days = (label_config or BarrierLabelConfig()).horizon_days
    embargo_days = _int_payload(
        payload, "embargo_days", max(defaults.embargo_days, horizon_days)
    )
    if embargo_days < horizon_days:
        raise ValueError("embargo_days must be greater than or equal to horizon_days")
    return TemporalSplitConfig(
        train_pct=_float_payload(payload, "train_pct", defaults.train_pct),
        validation_pct=_float_payload(
            payload, "validation_pct", defaults.validation_pct
        ),
        embargo_days=embargo_days,
    )


def _nested_split_config(
    payload: Mapping[str, Any], label_config: BarrierLabelConfig | None = None
) -> NestedWalkForwardConfig | None:
    split_mode = str(payload.get("split_mode") or "").strip().lower()
    if split_mode not in {"nested_expanding_walk_forward", "expanding_walk_forward"}:
        return None
    horizon_days = (label_config or BarrierLabelConfig()).horizon_days
    embargo_sessions = _int_payload(
        payload, "embargo_sessions", _int_payload(payload, "embargo_days", horizon_days)
    )
    if embargo_sessions < horizon_days:
        raise ValueError(
            "embargo_sessions must be greater than or equal to horizon_days"
        )
    return NestedWalkForwardConfig(
        min_train_sessions=_int_payload(payload, "min_train_sessions", 504),
        outer_folds=_int_payload(payload, "outer_folds", 5),
        outer_test_sessions=_int_payload(payload, "outer_test_sessions", 63),
        calibration_sessions=_int_payload(payload, "calibration_sessions", 42),
        embargo_sessions=embargo_sessions,
        locked_holdout_sessions=_int_payload(payload, "locked_holdout_sessions", 126),
    )


def _table_ref(table_id: str) -> str:
    client = _get_client()
    return f"{client.project}.{DATASET_ID}.{table_id}"


def _candles_query_text() -> str:
    return f"""
        SELECT ticker, data_pregao, open, high, low, close,
               qtd_negociada AS volume,
               volume_financeiro AS financial_volume
        FROM `{_table_ref(DAILY_TABLE_ID)}`
        WHERE data_pregao BETWEEN @start_date AND @end_date
        ORDER BY ticker, data_pregao
    """


def _dataset_code_contract() -> str:
    return json.dumps(
        {
            "builder": "sisacao8.neural_dataset.build_training_dataset",
            "protocol_version": PROTOCOL_VERSION,
            "feature_version": "feature_eod_tabular_v2",
            "label_version": "label_eod_barrier_v2",
        },
        sort_keys=True,
    )


def _load_candles(
    client: bigquery.Client, start_date: dt.date, end_date: dt.date
) -> pd.DataFrame:
    query = _candles_query_text()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    )
    return client.query(query, job_config=job_config).to_dataframe()


def _load_holidays(
    client: bigquery.Client, start: dt.date, end: dt.date
) -> set[dt.date]:
    query = f"""
        SELECT data_feriado AS holiday_date
        FROM `{_table_ref(HOLIDAYS_TABLE_ID)}`
        WHERE data_feriado BETWEEN @start_date AND @end_date
          AND ativo IS TRUE
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start),
            bigquery.ScalarQueryParameter("end_date", "DATE", end),
        ]
    )
    try:
        return {
            row.holiday_date
            for row in client.query(query, job_config=job_config).result()
        }
    except Exception:  # noqa: BLE001
        logging.warning(
            "Could not load holidays; using weekend-only calendar", exc_info=True
        )
        return set()


def _prepare_for_bigquery(
    dataset: pd.DataFrame, snapshot: str, manifest: Mapping[str, Any]
) -> pd.DataFrame:
    prepared = dataset.copy()
    prepared["created_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    prepared["dataset_snapshot"] = snapshot
    prepared["metadata_json"] = prepared.apply(
        lambda row: _metadata_json(row, manifest), axis=1
    )
    return prepared.where(pd.notnull(prepared), None)


def _metadata_json(row: pd.Series, manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "builder": "sisacao8.neural_dataset.build_training_dataset",
        "protocol_version": manifest.get("protocol_version"),
        "feature_version": row.get("feature_version"),
        "label_version": row.get("label_version"),
        "manifest_query_hash": manifest.get("query_hash"),
        "manifest_code_hash": manifest.get("code_hash"),
        "survivorship_policy": manifest.get("survivorship_policy"),
    }


def _delete_snapshot(client: bigquery.Client, snapshot: str) -> None:
    query = f"""
        DELETE FROM `{_table_ref(TRAINING_DATASET_TABLE_ID)}`
        WHERE dataset_snapshot = @dataset_snapshot
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("dataset_snapshot", "STRING", snapshot)
        ]
    )
    client.query(query, job_config=job_config).result()


def _load_dataset(client: bigquery.Client, dataset: pd.DataFrame) -> int:
    if dataset.empty:
        return 0
    load_frame = dataset.reindex(columns=TRAINING_DATASET_COLUMNS)
    records = [_json_safe_record(record) for record in load_frame.to_dict("records")]
    job = client.load_table_from_json(
        records,
        _table_ref(TRAINING_DATASET_TABLE_ID),
        job_config=bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND
        ),
    )
    job.result()
    return len(records)


def _load_manifest(client: bigquery.Client, manifest: Mapping[str, Any]) -> None:
    record = {
        "dataset_snapshot": manifest["dataset_snapshot"],
        "protocol_version": manifest["protocol_version"],
        "feature_version": manifest["feature_version"],
        "label_version": manifest["label_version"],
        "universe_version": manifest["universe_version"],
        "start_date": manifest["start_date"],
        "end_date": manifest["end_date"],
        "rows": manifest["rows"],
        "tickers": manifest["tickers"],
        "query_hash": manifest["query_hash"],
        "code_hash": manifest["code_hash"],
        "manifest_json": manifest,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    job = client.load_table_from_json(
        [_json_safe_record(record)],
        _table_ref(MANIFESTS_TABLE_ID),
        job_config=bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND
        ),
    )
    job.result()


def _json_safe_record(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: _json_safe_value(value, key) for key, value in record.items()}


def _json_safe_value(value: Any, key: str | None = None) -> Any:
    if value is None:
        return None
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, numbers.Real) and not isinstance(value, bool):
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            return None
        if key in INTEGER_FIELDS:
            return int(numeric_value)
        return value
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return json.loads(json.dumps(value, default=str))
    return value


def _split_counts(dataset: pd.DataFrame) -> dict[str, int]:
    if dataset.empty or "dataset_split" not in dataset:
        return {}
    return {
        str(split): int(count)
        for split, count in dataset["dataset_split"]
        .fillna("embargo")
        .value_counts()
        .items()
    }


__all__ = ["neural_training_dataset"]
