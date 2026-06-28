from __future__ import annotations

import datetime as dt
import math
from types import SimpleNamespace

import pandas as pd

import functions.neural_training_dataset.main as module


class _FakeQueryJob:
    def __init__(self, rows=None):
        self._rows = rows or []

    def result(self):
        return self._rows

    def to_dataframe(self):
        rows = []
        start = dt.date(2024, 1, 1)
        for day in range(45):
            close = 100 + day
            rows.append(
                {
                    "ticker": "TEST3",
                    "data_pregao": start + dt.timedelta(days=day),
                    "open": close - 0.5,
                    "high": close + 2.0,
                    "low": close - 2.0,
                    "close": close,
                    "volume": 1000 + day,
                    "financial_volume": close * (1000 + day),
                }
            )
        return pd.DataFrame(rows)


class _FakeLoadJob:
    def result(self):
        return None


class _FakeClient:
    project = "ingestaokraken"

    def __init__(self):
        self.queries = []
        self.loaded_rows = []
        self.loaded_table_ids = []

    def query(self, query, job_config=None):
        self.queries.append(query)
        if "SELECT data AS holiday_date" in query:
            return _FakeQueryJob([])
        return _FakeQueryJob()

    def load_table_from_json(self, rows, table_id, job_config=None):
        self.loaded_rows.extend(rows)
        self.loaded_table_id = table_id
        self.loaded_table_ids.append(table_id)
        self.load_job_config = job_config
        return _FakeLoadJob()


class _Request:
    args = {}

    def __init__(self, body):
        self._body = body

    def get_json(self, silent=True):
        return self._body


def test_neural_training_dataset_materializes_and_loads_rows(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(module, "_BQ_CLIENT", fake_client)

    response, status = module.neural_training_dataset(
        _Request(
            {
                "start_date": "2024-01-01",
                "end_date": "2024-02-14",
                "dataset_snapshot": "snapshot_test",
                "horizon_days": 3,
                "embargo_days": 3,
            }
        )
    )

    assert status == 200
    assert response["status"] == "ok"
    assert response["dataset_snapshot"] == "snapshot_test"
    dataset_rows = [
        row for row in fake_client.loaded_rows if row.get("manifest_json") is None
    ]
    assert response["rows"] == len(dataset_rows)
    assert response["rows"] > 0
    assert (
        "ingestaokraken.cotacao_intraday.neural_eod_training_dataset"
        in fake_client.loaded_table_ids
    )
    assert (
        "ingestaokraken.cotacao_intraday.neural_dataset_manifests"
        in fake_client.loaded_table_ids
    )
    assert any("DELETE FROM" in query for query in fake_client.queries)
    first_row = fake_client.loaded_rows[0]
    assert set(first_row).issubset(set(module.TRAINING_DATASET_COLUMNS))
    assert "unexpected_extra_column" not in first_row
    assert first_row["dataset_snapshot"] == "snapshot_test"
    assert first_row["metadata_json"]["builder"].endswith("build_training_dataset")
    assert first_row["metadata_json"]["protocol_version"] == "neural_eod_protocol_v1"
    assert first_row["metadata_json"]["manifest_query_hash"]
    manifest_rows = [
        row
        for row in fake_client.loaded_rows
        if row.get("dataset_snapshot") == "snapshot_test"
        and row.get("manifest_json") is not None
    ]
    assert len(manifest_rows) == 1
    assert manifest_rows[0]["feature_version"] == "feature_eod_tabular_v2"
    loaded_splits = {row["dataset_split"] for row in dataset_rows}
    assert {"train", "validation", "test"}.issubset(loaded_splits)


def test_load_dataset_filters_columns_to_bigquery_contract(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(module, "_BQ_CLIENT", fake_client)
    frame = pd.DataFrame(
        [
            {
                "ticker": "TEST3",
                "dataset_snapshot": "snapshot_test",
                "created_at": dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc),
                "holding_sessions": 2.0,
                "unexpected_extra_column": "must_not_be_loaded",
            }
        ]
    )

    inserted = module._load_dataset(fake_client, frame)

    assert inserted == 1
    assert len(fake_client.loaded_rows) == 1
    loaded = fake_client.loaded_rows[0]
    assert "unexpected_extra_column" not in loaded
    assert set(loaded) == set(module.TRAINING_DATASET_COLUMNS)
    assert loaded["holding_sessions"] == 2


def test_neural_training_dataset_returns_json_error(monkeypatch):
    def fail_impl(request):
        raise RuntimeError("load failed detail")

    monkeypatch.setattr(module, "_neural_training_dataset", fail_impl)

    response, status = module.neural_training_dataset(_Request({}))

    assert status == 500
    assert response == {
        "status": "error",
        "error_type": "RuntimeError",
        "message": "load failed detail",
    }


def test_request_payload_merges_query_args_and_json_body():
    request = SimpleNamespace(
        args={"start_date": "2024-01-01"},
        get_json=lambda silent=True: {"end_date": "2024-01-31"},
    )

    payload = module._request_payload(request)

    assert payload == {"start_date": "2024-01-01", "end_date": "2024-01-31"}


def test_load_candles_uses_daily_table_volume_columns(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(module, "_BQ_CLIENT", fake_client)

    module._load_candles(fake_client, dt.date(2024, 1, 1), dt.date(2024, 1, 31))

    query = fake_client.queries[-1]
    assert "qtd_negociada AS volume" in query
    assert "volume_financeiro AS financial_volume" in query
    assert " close * volume" not in query


def test_load_holidays_uses_published_holiday_schema(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(module, "_BQ_CLIENT", fake_client)

    module._load_holidays(fake_client, dt.date(2024, 1, 1), dt.date(2024, 1, 31))

    query = fake_client.queries[-1]
    assert "data_feriado AS holiday_date" in query
    assert "WHERE data_feriado BETWEEN @start_date AND @end_date" in query
    assert "ativo IS TRUE" in query
    assert "SELECT data AS holiday_date" not in query


def test_json_safe_value_removes_non_finite_numbers():
    assert module._json_safe_value(float("nan")) is None
    assert module._json_safe_value(float("inf")) is None
    assert module._json_safe_value(float("-inf")) is None
    assert module._json_safe_value(pd.NA) is None
    assert module._json_safe_value(1.5) == 1.5
    assert math.isfinite(module._json_safe_value(1.5))


def test_json_safe_record_casts_nullable_integer_fields():
    record = module._json_safe_record(
        {
            "days_to_event_buy": 2.0,
            "days_to_event_sell": pd.NA,
            "return_5d": 1.25,
        }
    )

    assert record == {
        "days_to_event_buy": 2,
        "days_to_event_sell": None,
        "return_5d": 1.25,
    }


def test_split_config_requires_embargo_at_least_horizon() -> None:
    try:
        module._split_config(
            {"embargo_days": 2}, module.BarrierLabelConfig(horizon_days=3)
        )
    except ValueError as exc:
        assert "embargo_days" in str(exc)
    else:
        raise AssertionError("expected ValueError")
