from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

import functions.neural_training.main as module


class _FakeQueryJob:
    def __init__(self, frame: pd.DataFrame):
        self._frame = frame

    def to_dataframe(self):
        return self._frame.copy()


class _FakeLoadJob:
    def result(self):
        return None


class _FakeClient:
    project = "ingestaokraken"

    def __init__(self, frame: pd.DataFrame):
        self.frame = frame
        self.queries = []
        self.loaded_rows = []
        self.loaded_table_id = None

    def query(self, query, job_config=None):
        self.queries.append(query)
        self.job_config = job_config
        return _FakeQueryJob(self.frame)

    def load_table_from_json(self, rows, table_id, job_config=None):
        self.loaded_rows.extend(rows)
        self.loaded_table_id = table_id
        self.load_job_config = job_config
        return _FakeLoadJob()


class _FakeBlob:
    def __init__(self):
        self.uploaded = []

    def upload_from_filename(self, filename):
        self.uploaded.append(filename)


class _FakeBucket:
    def __init__(self):
        self.blobs = {}

    def blob(self, name):
        blob = _FakeBlob()
        self.blobs[name] = blob
        return blob


class _FakeStorageClient:
    def __init__(self):
        self.buckets = {}

    def bucket(self, name):
        bucket = _FakeBucket()
        self.buckets[name] = bucket
        return bucket


def _dataset() -> pd.DataFrame:
    rows = []
    for split in ["train", "validation", "test"]:
        for idx in range(2):
            rows.append(
                {
                    "ticker": f"TST{idx}",
                    "reference_date": dt.date(2026, 1, idx + 1),
                    "valid_for": dt.date(2026, 1, idx + 2),
                    "dataset_split": split,
                    "label_class": "up" if idx % 2 else "neutral",
                    "dataset_snapshot": "snapshot_2026",
                    "feature_version": "feature_eod_tabular_v1",
                    "label_version": "label_eod_barrier_v1",
                    **{column: 1.0 for column in module.FEATURE_COLUMNS},
                }
            )
    return pd.DataFrame(rows)


class _Request:
    args = {}

    def __init__(self, body):
        self._body = body

    def get_json(self, silent=True):
        return self._body


def test_neural_training_trains_uploads_and_registers(monkeypatch, tmp_path):
    fake_client = _FakeClient(_dataset())
    fake_storage = _FakeStorageClient()
    monkeypatch.setattr(module, "_BQ_CLIENT", fake_client)
    monkeypatch.setattr(module, "_STORAGE_CLIENT", fake_storage)
    monkeypatch.setattr(module, "ARTIFACT_BUCKET", "model-bucket")

    def fake_train(dataset, artifact_dir, config):
        output_dir = Path(artifact_dir) / config.model_version
        output_dir.mkdir(parents=True)
        (output_dir / "model.keras").write_text("model", encoding="utf-8")
        (output_dir / "manifest.json").write_text("{}", encoding="utf-8")
        return {
            "model_id": config.model_id,
            "model_version": config.model_version,
            "feature_version": config.feature_version,
            "label_version": config.label_version,
            "feature_columns": list(module.FEATURE_COLUMNS),
            "label_classes": list(module.LABEL_CLASSES),
            "hyperparameters": {
                "epochs": config.epochs,
                "early_stopping": config.early_stopping,
                "class_weight": config.class_weight,
            },
            "dataset_snapshot": "content_hash",
            "dataset_rows": len(dataset),
            "metrics": {
                "validation": {"accuracy": 0.55},
                "test": {
                    "accuracy": 0.6,
                    "coverage": 0.7,
                    "directional_precision": 0.8,
                    "confusion_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                },
            },
            "created_at": "2026-06-20T15:00:00+00:00",
        }

    monkeypatch.setattr(module, "train_baseline_mlp", fake_train)

    response, status = module.neural_training(
        _Request(
            {
                "dataset_snapshot": "snapshot_2026",
                "model_version": "neural_eod_mlp_test",
                "epochs": 1,
                "batch_size": 2,
                "early_stopping": True,
                "early_stopping_patience": 3,
                "class_weight": "balanced",
            }
        )
    )

    assert status == 200
    assert response["status"] == "ok"
    assert (
        response["artifact_uri"]
        == "gs://model-bucket/neural-eod-models/neural_eod_mlp_test"
    )
    assert (
        fake_client.loaded_table_id
        == "ingestaokraken.cotacao_intraday.neural_model_registry"
    )
    row = fake_client.loaded_rows[0]
    assert row["model_version"] == "neural_eod_mlp_test"
    assert row["status"] == "candidate"
    assert row["hyperparameters_json"]["early_stopping"] is True
    assert row["hyperparameters_json"]["class_weight"] == "balanced"
    assert row["training_dataset_snapshot"] == "snapshot_2026"
    assert row["artifact_uri"] == response["artifact_uri"]
    assert row["test_accuracy"] == 0.6
    assert row["directional_precision"] == 0.8
    assert (
        "neural-eod-models/neural_eod_mlp_test/model.keras"
        in fake_storage.buckets["model-bucket"].blobs
    )


def test_load_training_dataset_filters_latest_snapshot_when_not_specified(monkeypatch):
    fake_client = _FakeClient(_dataset())
    monkeypatch.setattr(module, "_BQ_CLIENT", fake_client)

    module._load_training_dataset(fake_client, None)

    query = fake_client.queries[-1]
    assert "FROM `ingestaokraken.cotacao_intraday.neural_eod_training_dataset`" in query
    assert "dataset_split IS NOT NULL" in query
    assert "FIRST_VALUE(dataset_snapshot)" in query
