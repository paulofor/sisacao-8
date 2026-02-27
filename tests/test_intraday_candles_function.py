from __future__ import annotations

import datetime as dt
import importlib
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_module_with_fake_bigquery():
    fake_bigquery = types.ModuleType("bigquery")

    class FakeLoadJobConfig:
        def __init__(self, write_disposition=None):
            self.write_disposition = write_disposition

    class FakeWriteDisposition:
        WRITE_APPEND = "WRITE_APPEND"

    class FakeClient:
        project = "test-project"

    fake_bigquery.Client = lambda *args, **kwargs: FakeClient()
    fake_bigquery.LoadJobConfig = FakeLoadJobConfig
    fake_bigquery.WriteDisposition = FakeWriteDisposition
    fake_cloud = types.ModuleType("cloud")
    fake_cloud.bigquery = fake_bigquery
    fake_google = types.ModuleType("google")
    fake_google.cloud = fake_cloud
    sys.modules["google"] = fake_google
    sys.modules["google.cloud"] = fake_cloud
    sys.modules["google.cloud.bigquery"] = fake_bigquery

    return importlib.reload(importlib.import_module("functions.intraday_candles.main"))


def test_json_ready_row_serializes_dates_and_datetimes() -> None:
    module = _load_module_with_fake_bigquery()

    row = {
        "candle_datetime": dt.datetime(2026, 2, 27, 10, 15, 0),
        "reference_date": dt.date(2026, 2, 27),
        "open": 10.5,
    }

    converted = module._json_ready_row(row)

    assert converted["candle_datetime"] == "2026-02-27T10:15:00"
    assert converted["reference_date"] == "2026-02-27"
    assert converted["open"] == 10.5


def test_load_rows_uses_serialized_rows(monkeypatch) -> None:
    module = _load_module_with_fake_bigquery()

    captured = {}

    class FakeJob:
        def result(self):
            return None

    class FakeClient:
        def load_table_from_json(self, rows, table_id, job_config):
            captured["rows"] = rows
            captured["table_id"] = table_id
            captured["write_disposition"] = job_config.write_disposition
            return FakeJob()

    monkeypatch.setattr(module, "client", FakeClient(), raising=False)

    module._load_rows(
        "project.dataset.table",
        [
            {
                "candle_datetime": dt.datetime(2026, 2, 27, 10, 15, 0),
                "reference_date": dt.date(2026, 2, 27),
                "close": 11.1,
            }
        ],
    )

    assert captured["table_id"] == "project.dataset.table"
    assert captured["write_disposition"] == "WRITE_APPEND"
    assert captured["rows"][0]["candle_datetime"] == "2026-02-27T10:15:00"
    assert captured["rows"][0]["reference_date"] == "2026-02-27"
