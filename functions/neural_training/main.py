"""Cloud Function that trains and registers the neural EOD baseline model."""

from __future__ import annotations

import datetime as dt
import json
import logging
import math
import os
import shutil
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, Mapping

import numpy as np
import pandas as pd
from google.cloud import bigquery, storage  # type: ignore[import-untyped]

from sisacao8.neural_training import (
    FEATURE_COLUMNS,
    LABEL_CLASSES,
    BaselineMlpConfig,
    train_baseline_mlp,
)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))

DATASET_ID = os.environ.get("BQ_INTRADAY_DATASET", "cotacao_intraday")
TRAINING_DATASET_TABLE_ID = os.environ.get(
    "BQ_NEURAL_TRAINING_DATASET_TABLE", "neural_eod_training_dataset"
)
MODEL_REGISTRY_TABLE_ID = os.environ.get(
    "BQ_NEURAL_MODEL_REGISTRY_TABLE", "neural_model_registry"
)
BQ_LOCATION = os.environ.get("BQ_LOCATION", "us-east1").replace("region-", "")
ARTIFACT_BUCKET = os.environ.get("NEURAL_MODEL_ARTIFACT_BUCKET", "")
ARTIFACT_PREFIX = os.environ.get("NEURAL_MODEL_ARTIFACT_PREFIX", "neural-eod-models")
DEFAULT_MODEL_STATUS = os.environ.get("NEURAL_MODEL_INITIAL_STATUS", "candidate")

_BQ_CLIENT: bigquery.Client | None = None
_STORAGE_CLIENT: storage.Client | None = None


def _get_bq_client() -> bigquery.Client:
    global _BQ_CLIENT
    if _BQ_CLIENT is None:
        _BQ_CLIENT = bigquery.Client(location=BQ_LOCATION)
    return _BQ_CLIENT


def _get_storage_client() -> storage.Client:
    global _STORAGE_CLIENT
    if _STORAGE_CLIENT is None:
        _STORAGE_CLIENT = storage.Client()
    return _STORAGE_CLIENT


def neural_training(request: Any) -> tuple[Dict[str, Any], int]:
    """HTTP entrypoint that trains a model and writes it to the model registry."""

    payload = _request_payload(request)
    client = _get_bq_client()
    dataset_snapshot = payload.get("dataset_snapshot")
    dataset = _load_training_dataset(client, _optional_str(dataset_snapshot))
    if dataset.empty:
        raise ValueError("No neural training rows found for the requested snapshot")

    config = _align_config_with_dataset(_training_config(payload), dataset, payload)
    status = str(payload.get("status") or DEFAULT_MODEL_STATUS)
    notes = _optional_str(payload.get("notes"))

    with tempfile.TemporaryDirectory(prefix="neural-training-") as tmp_dir:
        manifest = train_baseline_mlp(dataset, tmp_dir, config=config)
        manifest["source_dataset_snapshot"] = _source_dataset_snapshot(dataset)
        local_artifact_dir = Path(tmp_dir) / config.model_version
        artifact_uri = _publish_artifact(local_artifact_dir, payload, config)
        registry_row = _registry_row(
            manifest=manifest,
            artifact_uri=artifact_uri,
            status=status,
            notes=notes,
        )
        _insert_registry_row(client, registry_row)

    logging.info(
        "neural_training finished model_id=%s model_version=%s status=%s snapshot=%s",
        registry_row["model_id"],
        registry_row["model_version"],
        registry_row["status"],
        registry_row["training_dataset_snapshot"],
    )
    return {
        "status": "ok",
        "model_id": registry_row["model_id"],
        "model_version": registry_row["model_version"],
        "model_status": registry_row["status"],
        "training_dataset_snapshot": registry_row["training_dataset_snapshot"],
        "artifact_uri": artifact_uri,
        "rows": int(manifest.get("dataset_rows", len(dataset))),
        "validation_accuracy": registry_row["validation_accuracy"],
        "test_accuracy": registry_row["test_accuracy"],
        "directional_precision": registry_row["directional_precision"],
        "coverage": registry_row["coverage"],
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


def _optional_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _table_ref(table_id: str) -> str:
    client = _get_bq_client()
    return f"{client.project}.{DATASET_ID}.{table_id}"


def _load_training_dataset(
    client: bigquery.Client, dataset_snapshot: str | None
) -> pd.DataFrame:
    query = f"""
        SELECT *
        FROM `{_table_ref(TRAINING_DATASET_TABLE_ID)}`
        WHERE dataset_split IS NOT NULL
          AND (@dataset_snapshot IS NULL OR dataset_snapshot = @dataset_snapshot)
        QUALIFY dataset_snapshot = COALESCE(
          @dataset_snapshot,
          FIRST_VALUE(dataset_snapshot) OVER (ORDER BY created_at DESC)
        )
        ORDER BY reference_date, ticker
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "dataset_snapshot", "STRING", dataset_snapshot
            )
        ]
    )
    dataset = client.query(query, job_config=job_config).to_dataframe()
    return _coerce_dataset(dataset)


def _coerce_dataset(dataset: pd.DataFrame) -> pd.DataFrame:
    prepared = dataset.copy()
    for date_column in ["reference_date", "valid_for"]:
        if date_column in prepared:
            prepared[date_column] = pd.to_datetime(prepared[date_column]).dt.date
    for column in FEATURE_COLUMNS:
        if column in prepared:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    return prepared


def _align_config_with_dataset(
    config: BaselineMlpConfig, dataset: pd.DataFrame, payload: Mapping[str, Any]
) -> BaselineMlpConfig:
    """Keep training config compatible with the materialized snapshot contract."""

    dataset_feature_version = _single_dataset_value(dataset, "feature_version")
    dataset_label_version = _single_dataset_value(dataset, "label_version")
    feature_version = str(
        payload.get("feature_version")
        or dataset_feature_version
        or config.feature_version
    )
    label_version = str(
        payload.get("label_version") or dataset_label_version or config.label_version
    )
    if (
        feature_version == config.feature_version
        and label_version == config.label_version
    ):
        return config
    return replace(
        config,
        feature_version=feature_version,
        label_version=label_version,
    )


def _single_dataset_value(dataset: pd.DataFrame, column: str) -> str | None:
    if column not in dataset.columns:
        return None
    values = {str(value) for value in dataset[column].dropna().unique()}
    if not values:
        return None
    if len(values) > 1:
        raise ValueError(f"dataset contains multiple {column} values: {sorted(values)}")
    return next(iter(values))


def _training_config(payload: Mapping[str, Any]) -> BaselineMlpConfig:
    defaults = BaselineMlpConfig()
    model_version = str(
        payload.get("model_version")
        or os.environ.get("NEURAL_MODEL_VERSION")
        or f"{defaults.model_id}_v1_{dt.datetime.now(dt.timezone.utc):%Y%m%d_%H%M%S}"
    )
    return BaselineMlpConfig(
        model_id=str(payload.get("model_id") or defaults.model_id),
        model_version=model_version,
        feature_version=str(payload.get("feature_version") or defaults.feature_version),
        label_version=str(payload.get("label_version") or defaults.label_version),
        hidden_units=_hidden_units(payload.get("hidden_units"), defaults.hidden_units),
        dropout_rate=_float_value(payload.get("dropout_rate"), defaults.dropout_rate),
        learning_rate=_float_value(
            payload.get("learning_rate"), defaults.learning_rate
        ),
        epochs=_int_value(payload.get("epochs"), defaults.epochs),
        batch_size=_int_value(payload.get("batch_size"), defaults.batch_size),
        validation_split_name=str(
            payload.get("validation_split_name") or defaults.validation_split_name
        ),
        test_split_name=str(payload.get("test_split_name") or defaults.test_split_name),
        random_seed=_int_value(payload.get("random_seed"), defaults.random_seed),
        early_stopping=_bool_value(
            payload.get("early_stopping"), defaults.early_stopping
        ),
        early_stopping_patience=_int_value(
            payload.get("early_stopping_patience"),
            defaults.early_stopping_patience,
        ),
        class_weight=str(payload.get("class_weight") or defaults.class_weight),
        architecture_type=str(
            payload.get("architecture_type") or defaults.architecture_type
        ),
        min_directional_probability=_float_value(
            payload.get("min_directional_probability"),
            defaults.min_directional_probability,
        ),
        min_directional_margin=_float_value(
            payload.get("min_directional_margin"),
            defaults.min_directional_margin,
        ),
        max_trades_per_fold=_optional_int_value(
            payload.get("max_trades_per_fold"),
            defaults.max_trades_per_fold,
        ),
        max_fold_drawdown_stop=_optional_float_value(
            payload.get("max_fold_drawdown_stop"),
            defaults.max_fold_drawdown_stop,
        ),
        blocked_tickers=_string_tuple_value(
            payload.get("blocked_tickers"), defaults.blocked_tickers
        ),
        require_champion_activity=_bool_value(
            payload.get("require_champion_activity"),
            defaults.require_champion_activity,
        ),
        min_regime_return_5d=_optional_float_value(
            payload.get("min_regime_return_5d"),
            defaults.min_regime_return_5d,
        ),
        min_regime_financial_volume_z20=_optional_float_value(
            payload.get("min_regime_financial_volume_z20"),
            defaults.min_regime_financial_volume_z20,
        ),
        min_regime_volume_ratio_20d=_optional_float_value(
            payload.get("min_regime_volume_ratio_20d"),
            defaults.min_regime_volume_ratio_20d,
        ),
        neutral_event_min_abs_return_5d=_optional_float_value(
            payload.get("neutral_event_min_abs_return_5d"),
            defaults.neutral_event_min_abs_return_5d,
        ),
        neutral_event_min_financial_volume_z20=_optional_float_value(
            payload.get("neutral_event_min_financial_volume_z20"),
            defaults.neutral_event_min_financial_volume_z20,
        ),
        neutral_event_min_volume_ratio_20d=_optional_float_value(
            payload.get("neutral_event_min_volume_ratio_20d"),
            defaults.neutral_event_min_volume_ratio_20d,
        ),
        neutral_event_min_volatility_20d=_optional_float_value(
            payload.get("neutral_event_min_volatility_20d"),
            defaults.neutral_event_min_volatility_20d,
        ),
        candidate_family_hash=(
            str(payload.get("candidate_family_hash"))
            if payload.get("candidate_family_hash")
            else defaults.candidate_family_hash
        ),
        sequence_lookback=_int_value(
            payload.get("sequence_lookback"), defaults.sequence_lookback
        ),
    )


def _hidden_units(value: Any, default: tuple[int, ...]) -> tuple[int, ...]:
    if value is None or value == "":
        return default
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",") if part.strip()]
        return tuple(int(part) for part in parts)
    if isinstance(value, (list, tuple)):
        return tuple(int(part) for part in value)
    raise ValueError("hidden_units must be a comma-separated string or list")


def _bool_value(value: Any, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _int_value(value: Any, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


def _float_value(value: Any, default: float) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _optional_int_value(value: Any, default: int | None) -> int | None:
    if value is None or value == "":
        return default
    return int(value)


def _string_tuple_value(value: Any, default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None or value == "":
        return default
    if isinstance(value, str):
        return tuple(part.strip().upper() for part in value.split(",") if part.strip())
    if isinstance(value, (list, tuple, set)):
        return tuple(str(part).strip().upper() for part in value if str(part).strip())
    raise ValueError("blocked_tickers must be a comma-separated string or list")


def _optional_float_value(value: Any, default: float | None) -> float | None:
    if value is None or value == "":
        return default
    return float(value)


def _publish_artifact(
    local_artifact_dir: Path, payload: Mapping[str, Any], config: BaselineMlpConfig
) -> str:
    explicit_uri = _optional_str(payload.get("artifact_uri"))
    if explicit_uri:
        if explicit_uri.startswith("gs://"):
            return _upload_artifact(local_artifact_dir, explicit_uri)
        destination = Path(explicit_uri)
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(local_artifact_dir, destination)
        return str(destination)
    if ARTIFACT_BUCKET:
        prefix = ARTIFACT_PREFIX.strip("/")
        target_uri = f"gs://{ARTIFACT_BUCKET}/{prefix}/{config.model_version}"
        return _upload_artifact(local_artifact_dir, target_uri)
    return str(local_artifact_dir)


def _upload_artifact(local_artifact_dir: Path, target_uri: str) -> str:
    bucket_name, _, prefix = target_uri.removeprefix("gs://").partition("/")
    if not bucket_name or not prefix:
        raise ValueError("GCS artifact_uri must be gs://<bucket>/<prefix>")
    client = _get_storage_client()
    bucket = client.bucket(bucket_name)
    normalized_prefix = prefix.rstrip("/")
    for path in local_artifact_dir.rglob("*"):
        if path.is_file():
            relative = path.relative_to(local_artifact_dir).as_posix()
            blob = bucket.blob(f"{normalized_prefix}/{relative}")
            blob.upload_from_filename(str(path))
    return f"gs://{bucket_name}/{normalized_prefix}"


def _registry_row(
    manifest: Mapping[str, Any], artifact_uri: str, status: str, notes: str | None
) -> dict[str, Any]:
    metrics = (
        manifest.get("metrics") if isinstance(manifest.get("metrics"), dict) else {}
    )
    validation = _metric_split(metrics, "validation")
    test = _metric_split(metrics, "test")
    selected = test or validation
    created_at = dt.datetime.now(dt.timezone.utc).isoformat()
    return {
        "model_id": manifest["model_id"],
        "model_version": manifest["model_version"],
        "status": status,
        "feature_version": manifest["feature_version"],
        "label_version": manifest["label_version"],
        "training_dataset_snapshot": _training_dataset_snapshot(manifest),
        "artifact_uri": artifact_uri,
        "feature_columns": list(manifest.get("feature_columns") or FEATURE_COLUMNS),
        "label_classes": list(manifest.get("label_classes") or LABEL_CLASSES),
        "hyperparameters_json": _json_safe(manifest.get("hyperparameters") or {}),
        "metrics_json": _json_safe(metrics),
        "confusion_matrix_json": _json_safe(selected.get("confusion_matrix")),
        "directional_precision": _optional_float(selected.get("directional_precision")),
        "coverage": _optional_float(selected.get("coverage")),
        "validation_accuracy": _optional_float(validation.get("accuracy")),
        "test_accuracy": _optional_float(test.get("accuracy")),
        "trained_at": manifest.get("created_at") or created_at,
        "created_at": created_at,
        "notes": notes,
    }


def _metric_split(metrics: object, split: str) -> dict[str, Any]:
    if not isinstance(metrics, Mapping):
        return {}
    value = metrics.get(split)
    return dict(value) if isinstance(value, Mapping) else {}


def _source_dataset_snapshot(dataset: pd.DataFrame) -> str:
    if "dataset_snapshot" not in dataset or dataset.empty:
        return "unknown"
    snapshots = sorted(
        str(value) for value in dataset["dataset_snapshot"].dropna().unique()
    )
    return snapshots[0] if snapshots else "unknown"


def _training_dataset_snapshot(manifest: Mapping[str, Any]) -> str:
    value = manifest.get("source_dataset_snapshot") or manifest.get("dataset_snapshot")
    return str(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (dt.date, dt.datetime, pd.Timestamp)):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return json.loads(json.dumps(value, default=str))


def _insert_registry_row(client: bigquery.Client, row: Mapping[str, Any]) -> None:
    job = client.load_table_from_json(
        [dict(row)],
        _table_ref(MODEL_REGISTRY_TABLE_ID),
        job_config=bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND
        ),
    )
    job.result()


__all__ = ["neural_training"]
