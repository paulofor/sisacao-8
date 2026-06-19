from __future__ import annotations

import datetime as dt
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

    def query(self, query, job_config=None):
        self.queries.append(query)
        if "SELECT data AS holiday_date" in query:
            return _FakeQueryJob([])
        return _FakeQueryJob()

    def load_table_from_json(self, rows, table_id, job_config=None):
        self.loaded_rows.extend(rows)
        self.loaded_table_id = table_id
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
                "embargo_days": 1,
            }
        )
    )

    assert status == 200
    assert response["status"] == "ok"
    assert response["dataset_snapshot"] == "snapshot_test"
    assert response["rows"] == len(fake_client.loaded_rows)
    assert response["rows"] > 0
    assert fake_client.loaded_table_id == (
        "ingestaokraken.cotacao_intraday.neural_eod_training_dataset"
    )
    assert any("DELETE FROM" in query for query in fake_client.queries)
    first_row = fake_client.loaded_rows[0]
    assert first_row["dataset_snapshot"] == "snapshot_test"
    assert first_row["metadata_json"]["builder"].endswith("build_training_dataset")


def test_request_payload_merges_query_args_and_json_body():
    request = SimpleNamespace(
        args={"start_date": "2024-01-01"},
        get_json=lambda silent=True: {"end_date": "2024-01-31"},
    )

    payload = module._request_payload(request)

    assert payload == {"start_date": "2024-01-01", "end_date": "2024-01-31"}
