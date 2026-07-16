"""Cloud Function that writes neural EOD predictions in shadow mode only."""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import shutil
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Mapping
from uuid import uuid4

import pandas as pd
from google.cloud import bigquery, storage  # type: ignore[import-untyped]

from sisacao8.neural_inference import NeuralInferenceConfig, predict_neural_eod

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))

DATASET_ID = os.environ.get("BQ_INTRADAY_DATASET", "cotacao_intraday")
DAILY_TABLE_ID = os.environ.get("BQ_DAILY_TABLE", "cotacao_ohlcv_diario")
PREDICTIONS_TABLE_ID = os.environ.get(
    "BQ_NEURAL_EOD_PREDICTIONS_TABLE", "neural_eod_predictions"
)
MODEL_REGISTRY_TABLE_ID = os.environ.get(
    "BQ_NEURAL_MODEL_REGISTRY_TABLE", "neural_model_registry"
)
HOLIDAYS_TABLE_ID = os.environ.get("BQ_HOLIDAYS_TABLE", "feriados_b3")
MODEL_ID = os.environ.get("NEURAL_MODEL_ID", "").strip()
MODEL_VERSION = os.environ.get("NEURAL_MODEL_VERSION")
APPROVED_STATUSES = tuple(
    item.strip().lower()
    for item in os.environ.get("NEURAL_MODEL_STATUSES", "shadow,approved").split(",")
    if item.strip()
)
LOOKBACK_DAYS = int(os.environ.get("NEURAL_INFERENCE_LOOKBACK_DAYS", "90"))
DECISION_THRESHOLD = float(os.environ.get("NEURAL_DECISION_THRESHOLD", "0.60"))
EARLY_RUN = os.environ.get("ALLOW_EARLY_NEURAL_INFERENCE", "false").lower() == "true"
BQ_LOCATION = os.environ.get("BQ_LOCATION", "us-east1").replace("region-", "")
ENABLE_DAILY_CANDLES_RECOVERY = (
    os.environ.get("ENABLE_DAILY_CANDLES_RECOVERY", "true").lower() == "true"
)
DAILY_CANDLES_RECOVERY_URL = os.environ.get(
    "DAILY_CANDLES_RECOVERY_URL",
    "https://us-east1-ingestaokraken.cloudfunctions.net/get_stock_data",
)
DAILY_CANDLES_RECOVERY_TIMEOUT_SECONDS = int(
    os.environ.get("DAILY_CANDLES_RECOVERY_TIMEOUT_SECONDS", "240")
)

_BQ_CLIENT: bigquery.Client | None = None


def _get_client() -> bigquery.Client:
    global _BQ_CLIENT
    if _BQ_CLIENT is None:
        _BQ_CLIENT = bigquery.Client(location=BQ_LOCATION)
    return _BQ_CLIENT


def neural_eod_predictions(request: Any) -> tuple[Dict[str, Any], int]:
    """HTTP entrypoint for shadow-mode neural prediction generation."""

    payload = _request_payload(request)
    force = _as_bool(payload.get("force", False))
    if not _ensure_after_cutoff(force):
        return {"status": "skipped", "reason": "before_cutoff_18h_brt"}, 200
    reference_date = _parse_request_date(payload)
    bq_client = _get_client()
    valid_for = _next_trading_day(bq_client, reference_date)
    job_run_id = str(payload.get("job_run_id") or uuid4())
    registry = _load_registry_entry(bq_client, payload)
    model_version = str(registry.get("model_version") or MODEL_VERSION or "manual")
    existing_predictions = _count_existing_predictions(
        bq_client, reference_date, valid_for, model_version
    )
    if existing_predictions > 0 and not force:
        logging.info(
            "[run_id=%s] skipping neural_eod_predictions for %s/%s/%s; "
            "already has %s rows",
            job_run_id,
            reference_date.isoformat(),
            valid_for.isoformat(),
            model_version,
            existing_predictions,
        )
        return {
            "status": "ok",
            "reason": "existing_predictions",
            "job_run_id": job_run_id,
            "reference_date": reference_date.isoformat(),
            "valid_for": valid_for.isoformat(),
            "rows": existing_predictions,
            "model_version": model_version,
            "inserted": 0,
        }, 200
    if existing_predictions > 0 and force:
        _delete_existing_predictions(
            bq_client, reference_date, valid_for, model_version
        )
    artifact_dir = _materialize_artifact(registry["artifact_uri"])
    try:
        manifest = _load_manifest(artifact_dir)
        model = _load_model(artifact_dir)
        candles = _load_candles(bq_client, reference_date)
        if not _has_reference_candles(candles, reference_date):
            _recover_daily_candles(reference_date, force=force)
            candles = _load_candles(bq_client, reference_date)
        if not _has_reference_candles(candles, reference_date):
            logging.warning(
                "[run_id=%s] missing daily candles for reference_date=%s",
                job_run_id,
                reference_date.isoformat(),
            )
            return {
                "status": "empty",
                "reason": "missing_daily_candles",
                "job_run_id": job_run_id,
                "reference_date": reference_date.isoformat(),
                "valid_for": valid_for.isoformat(),
                "rows": 0,
                "model_id": manifest["model_id"],
                "model_version": manifest["model_version"],
            }, 200
        predictions = predict_neural_eod(
            candles=candles,
            model=model,
            manifest=manifest,
            reference_date=reference_date,
            valid_for=valid_for,
            job_run_id=job_run_id,
            config=NeuralInferenceConfig(decision_threshold=DECISION_THRESHOLD),
        )
        inserted = _insert_predictions(bq_client, predictions)
    finally:
        if artifact_dir.is_dir() and artifact_dir.name.startswith("neural-artifact-"):
            shutil.rmtree(artifact_dir, ignore_errors=True)
    logging.info(
        "[run_id=%s] neural_eod_predictions finished reference_date=%s rows=%s",
        job_run_id,
        reference_date.isoformat(),
        inserted,
    )
    return {
        "status": "ok",
        "job_run_id": job_run_id,
        "reference_date": reference_date.isoformat(),
        "valid_for": valid_for.isoformat(),
        "rows": inserted,
        "model_id": manifest["model_id"],
        "model_version": manifest["model_version"],
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


def _parse_request_date(payload: Mapping[str, Any]) -> dt.date:
    requested = payload.get("date_ref") or payload.get("date")
    if requested:
        return dt.datetime.strptime(str(requested), "%Y-%m-%d").date()
    now_brt = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3)))
    if now_brt.time() >= dt.time(18, 0):
        return now_brt.date()
    return now_brt.date() - dt.timedelta(days=1)


def _ensure_after_cutoff(force: bool) -> bool:
    if force or EARLY_RUN:
        return True
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).time() >= dt.time(18, 0)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _table_ref(table_id: str) -> str:
    client = _get_client()
    return f"{client.project}.{DATASET_ID}.{table_id}"


def _load_registry_entry(
    client: bigquery.Client, payload: Mapping[str, Any]
) -> dict[str, Any]:
    explicit_uri = payload.get("artifact_uri") or os.environ.get(
        "NEURAL_MODEL_ARTIFACT_URI"
    )
    explicit_model_id = str(payload.get("model_id") or MODEL_ID).strip()
    explicit_version = payload.get("model_version") or MODEL_VERSION
    if explicit_uri:
        return {
            "artifact_uri": str(explicit_uri),
            "model_version": explicit_version or "manual",
        }
    status_params = [status for status in APPROVED_STATUSES]
    query = f"""
        SELECT model_id, model_version, artifact_uri, status, created_at
        FROM `{_table_ref(MODEL_REGISTRY_TABLE_ID)}`
        WHERE (@model_id = '' OR model_id = @model_id)
          AND LOWER(status) IN UNNEST(@statuses)
          AND (@model_version IS NULL OR model_version = @model_version)
        ORDER BY CASE WHEN LOWER(status) = 'approved' THEN 0 ELSE 1 END,
                 created_at DESC
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("model_id", "STRING", explicit_model_id),
            bigquery.ArrayQueryParameter("statuses", "STRING", status_params),
            bigquery.ScalarQueryParameter("model_version", "STRING", explicit_version),
        ]
    )
    rows = list(client.query(query, job_config=job_config).result())
    if not rows:
        raise RuntimeError(
            "No neural model artifact found with an approved shadow/approved status"
        )
    return dict(rows[0].items())


def _materialize_artifact(artifact_uri: str) -> Path:
    if artifact_uri.startswith("gs://"):
        tmp_root = Path(tempfile.mkdtemp(prefix="neural-artifact-"))
        _download_gcs_prefix(artifact_uri, tmp_root)
        return tmp_root
    return Path(artifact_uri)


def _download_gcs_prefix(uri: str, destination: Path) -> None:
    bucket_name, _, prefix = uri.removeprefix("gs://").partition("/")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    for blob in client.list_blobs(bucket, prefix=prefix.rstrip("/") + "/"):
        relative = blob.name.removeprefix(prefix.rstrip("/") + "/")
        if relative:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(target)


def _load_manifest(artifact_dir: Path) -> dict[str, Any]:
    path = artifact_dir / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_model(artifact_dir: Path) -> Any:
    import tensorflow as tf

    model_path = artifact_dir / "model.keras"
    if not model_path.exists():
        raise FileNotFoundError(f"Keras model not found: {model_path}")
    return tf.keras.models.load_model(model_path)


def _load_candles(client: bigquery.Client, reference_date: dt.date) -> pd.DataFrame:
    start_date = reference_date - dt.timedelta(days=LOOKBACK_DAYS)
    query = f"""
        SELECT ticker, data_pregao, open, high, low, close,
               qtd_negociada AS volume,
               volume_financeiro AS financial_volume
        FROM `{_table_ref(DAILY_TABLE_ID)}`
        WHERE data_pregao BETWEEN @start_date AND @reference_date
        ORDER BY ticker, data_pregao
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("reference_date", "DATE", reference_date),
        ]
    )
    return client.query(query, job_config=job_config).to_dataframe()


def _has_reference_candles(candles: pd.DataFrame, reference_date: dt.date) -> bool:
    if candles.empty or "data_pregao" not in candles.columns:
        return False
    dates = pd.to_datetime(candles["data_pregao"], errors="coerce").dt.date
    return bool(dates.eq(reference_date).any())


def _recover_daily_candles(reference_date: dt.date, *, force: bool) -> None:
    if not ENABLE_DAILY_CANDLES_RECOVERY:
        logging.warning(
            "Daily candles recovery disabled for %s", reference_date.isoformat()
        )
        return
    payload = {
        "date_ref": reference_date.isoformat(),
        "force": force,
        "reason": "auto-recover-before-neural-eod-predictions",
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        DAILY_CANDLES_RECOVERY_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=DAILY_CANDLES_RECOVERY_TIMEOUT_SECONDS
        ) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            logging.warning(
                "Daily candles recovery returned HTTP %s for %s: %s",
                getattr(response, "status", "unknown"),
                reference_date.isoformat(),
                response_body[:500],
            )
    except urllib.error.URLError as exc:
        logging.warning(
            "Daily candles recovery failed for %s: %s",
            reference_date.isoformat(),
            exc,
            exc_info=True,
        )


def _next_trading_day(client: bigquery.Client, reference_date: dt.date) -> dt.date:
    candidate = reference_date + dt.timedelta(days=1)
    holidays = _load_holidays(
        client, reference_date, reference_date + dt.timedelta(days=10)
    )
    while candidate.weekday() >= 5 or candidate in holidays:
        candidate += dt.timedelta(days=1)
    return candidate


def _load_holidays(
    client: bigquery.Client, start: dt.date, end: dt.date
) -> set[dt.date]:
    query = f"""
        SELECT data_feriado AS holiday_date
        FROM `{_table_ref(HOLIDAYS_TABLE_ID)}`
        WHERE data_feriado BETWEEN @start_date AND @end_date
          AND COALESCE(ativo, TRUE)
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


def _count_existing_predictions(
    client: bigquery.Client,
    reference_date: dt.date,
    valid_for: dt.date,
    model_version: str,
) -> int:
    query = f"""
        SELECT COUNT(*) AS row_count
        FROM `{_table_ref(PREDICTIONS_TABLE_ID)}`
        WHERE reference_date = @reference_date
          AND valid_for = @valid_for
          AND model_version = @model_version
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("reference_date", "DATE", reference_date),
            bigquery.ScalarQueryParameter("valid_for", "DATE", valid_for),
            bigquery.ScalarQueryParameter("model_version", "STRING", model_version),
        ]
    )
    try:
        rows = list(client.query(query, job_config=job_config).result())
    except Exception:  # noqa: BLE001 - table may not exist before first deploy.
        logging.warning("Could not check existing neural predictions", exc_info=True)
        return 0
    if not rows:
        return 0
    row = rows[0]
    if hasattr(row, "get"):
        value = row.get("row_count", 0)
    else:
        value = getattr(row, "row_count", 0)
    return int(value or 0)


def _delete_existing_predictions(
    client: bigquery.Client,
    reference_date: dt.date,
    valid_for: dt.date,
    model_version: str,
) -> None:
    query = f"""
        DELETE FROM `{_table_ref(PREDICTIONS_TABLE_ID)}`
        WHERE reference_date = @reference_date
          AND valid_for = @valid_for
          AND model_version = @model_version
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("reference_date", "DATE", reference_date),
            bigquery.ScalarQueryParameter("valid_for", "DATE", valid_for),
            bigquery.ScalarQueryParameter("model_version", "STRING", model_version),
        ]
    )
    client.query(query, job_config=job_config).result()


def _insert_predictions(client: bigquery.Client, predictions: pd.DataFrame) -> int:
    if predictions.empty:
        return 0
    rows = [
        {key: _json_ready(value) for key, value in row.items()}
        for row in predictions.to_dict("records")
    ]
    errors = client.insert_rows_json(_table_ref(PREDICTIONS_TABLE_ID), rows)
    if errors:
        raise RuntimeError(f"BigQuery insert_rows_json failed: {errors}")
    return int(len(predictions))


def _json_ready(value: Any) -> Any:
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value
