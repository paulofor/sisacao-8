import datetime as dt
import importlib
import os
import sys
import types

import pandas as pd


def import_predictions_module(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")
    fake_bigquery.Client = lambda *args, **kwargs: None

    class FakeQueryJobConfig:
        def __init__(self, query_parameters=None):
            self.query_parameters = query_parameters or []

    class FakeScalarQueryParameter:
        def __init__(self, name, type_, value):
            self.name = name
            self.type_ = type_
            self.value = value

    fake_bigquery.QueryJobConfig = FakeQueryJobConfig
    fake_bigquery.ScalarQueryParameter = FakeScalarQueryParameter

    fake_storage = types.ModuleType("storage")
    fake_storage.Client = lambda *args, **kwargs: None

    fake_cloud = types.ModuleType("cloud")
    fake_cloud.bigquery = fake_bigquery
    fake_cloud.storage = fake_storage
    fake_google = types.ModuleType("google")
    fake_google.cloud = fake_cloud

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.cloud", fake_cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)
    monkeypatch.setitem(sys.modules, "google.cloud.storage", fake_storage)

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)

    module_name = "functions.neural_eod_predictions.main"
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_has_reference_candles_requires_target_date(monkeypatch):
    module = import_predictions_module(monkeypatch)
    candles = pd.DataFrame(
        [
            {"ticker": "PETR4", "data_pregao": dt.date(2026, 7, 13)},
            {"ticker": "VALE3", "data_pregao": "2026-07-14"},
        ]
    )

    assert module._has_reference_candles(candles, dt.date(2026, 7, 14)) is True
    assert module._has_reference_candles(candles, dt.date(2026, 7, 15)) is False
    assert module._has_reference_candles(pd.DataFrame(), dt.date(2026, 7, 14)) is False


def test_recover_daily_candles_posts_reference_date(monkeypatch):
    module = import_predictions_module(monkeypatch)
    captured = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b"Success"

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = request.data.decode("utf-8")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(module, "DAILY_CANDLES_RECOVERY_URL", "https://daily.example")
    monkeypatch.setattr(module, "DAILY_CANDLES_RECOVERY_TIMEOUT_SECONDS", 55)

    module._recover_daily_candles(dt.date(2026, 7, 14), force=True)

    assert captured == {
        "url": "https://daily.example",
        "body": (
            '{"date_ref": "2026-07-14", "force": true, '
            '"reason": "auto-recover-before-neural-eod-predictions"}'
        ),
        "timeout": 55,
    }


def test_count_existing_predictions_uses_model_and_dates(monkeypatch):
    module = import_predictions_module(monkeypatch)
    monkeypatch.setattr(module, "_table_ref", lambda table: f"project.dataset.{table}")

    class FakeJob:
        def result(self):
            return [{"row_count": 150}]

    class FakeClient:
        def __init__(self):
            self.query_text = None
            self.job_config = None

        def query(self, query, job_config=None):
            self.query_text = query
            self.job_config = job_config
            return FakeJob()

    client = FakeClient()
    count = module._count_existing_predictions(
        client,
        dt.date(2026, 7, 15),
        dt.date(2026, 7, 16),
        "apolo-v1",
    )

    assert count == 150
    assert "reference_date = @reference_date" in client.query_text
    assert "valid_for = @valid_for" in client.query_text
    assert "model_version = @model_version" in client.query_text
    params = {param.name: param.value for param in client.job_config.query_parameters}
    assert params == {
        "reference_date": dt.date(2026, 7, 15),
        "valid_for": dt.date(2026, 7, 16),
        "model_version": "apolo-v1",
    }


def test_delete_existing_predictions_uses_model_and_dates(monkeypatch):
    module = import_predictions_module(monkeypatch)
    monkeypatch.setattr(module, "_table_ref", lambda table: f"project.dataset.{table}")

    class FakeJob:
        def result(self):
            return []

    class FakeClient:
        def __init__(self):
            self.query_text = None
            self.job_config = None

        def query(self, query, job_config=None):
            self.query_text = query
            self.job_config = job_config
            return FakeJob()

    client = FakeClient()
    module._delete_existing_predictions(
        client,
        dt.date(2026, 7, 15),
        dt.date(2026, 7, 16),
        "apolo-v1",
    )

    assert "DELETE FROM `project.dataset.neural_eod_predictions`" in client.query_text
    assert "reference_date = @reference_date" in client.query_text
    assert "valid_for = @valid_for" in client.query_text
    assert "model_version = @model_version" in client.query_text
    params = {param.name: param.value for param in client.job_config.query_parameters}
    assert params == {
        "reference_date": dt.date(2026, 7, 15),
        "valid_for": dt.date(2026, 7, 16),
        "model_version": "apolo-v1",
    }


def test_neural_eod_predictions_skips_existing_rows_without_force(monkeypatch):
    module = import_predictions_module(monkeypatch)

    class Request:
        def get_json(self, silent=True):
            return {"date_ref": "2026-07-15"}

    fake_client = object()
    monkeypatch.setattr(module, "_ensure_after_cutoff", lambda force: True)
    monkeypatch.setattr(module, "_get_client", lambda: fake_client)
    monkeypatch.setattr(
        module, "_next_trading_day", lambda client, date: dt.date(2026, 7, 16)
    )
    monkeypatch.setattr(
        module,
        "_load_registry_entry",
        lambda client, payload: {
            "artifact_uri": "gs://bucket/model",
            "model_version": "apolo-v1",
        },
    )
    monkeypatch.setattr(module, "_count_existing_predictions", lambda *args: 150)

    def fail_if_called(*args, **kwargs):  # pragma: no cover - should not be called.
        raise AssertionError("artifact should not be loaded when predictions exist")

    monkeypatch.setattr(module, "_materialize_artifact", fail_if_called)

    response, status = module.neural_eod_predictions(Request())

    assert status == 200
    assert response["status"] == "ok"
    assert response["reason"] == "existing_predictions"
    assert response["rows"] == 150
    assert response["inserted"] == 0
    assert response["model_version"] == "apolo-v1"
