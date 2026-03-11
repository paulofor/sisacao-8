import datetime as dt
import importlib
import os
import sys
import types


class DummyQueryJobConfig:
    def __init__(self, query_parameters=None):
        self.query_parameters = query_parameters or []


class DummyScalarQueryParameter:
    def __init__(self, name, param_type, value):
        self.name = name
        self.param_type = param_type
        self.value = value


class DummyLoadJobConfig:
    def __init__(self, write_disposition=None):
        self.write_disposition = write_disposition


class DummyWriteDisposition:
    WRITE_APPEND = "WRITE_APPEND"


def import_eod_module(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")
    fake_bigquery.Client = lambda *args, **kwargs: None
    fake_bigquery.QueryJobConfig = DummyQueryJobConfig
    fake_bigquery.ScalarQueryParameter = DummyScalarQueryParameter
    fake_bigquery.LoadJobConfig = DummyLoadJobConfig
    fake_bigquery.WriteDisposition = DummyWriteDisposition

    fake_cloud = types.ModuleType("cloud")
    fake_cloud.bigquery = fake_bigquery
    fake_google = types.ModuleType("google")
    fake_google.cloud = fake_cloud

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.cloud", fake_cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)

    module_name = "functions.eod_signals.main"
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_fetch_daily_frame_returns_expected_columns_when_empty(monkeypatch):
    module = import_eod_module(monkeypatch)
    module.client = types.SimpleNamespace(project="test-project")
    monkeypatch.setattr(module, "_query_rows", lambda *args, **kwargs: [])

    df = module._fetch_daily_frame(dt.date(2026, 1, 10))

    assert list(df.columns) == [
        "ticker",
        "data_pregao",
        "open",
        "close",
        "high",
        "low",
        "volume_financeiro",
        "qtd_negociada",
    ]
    assert df.empty


def test_fetch_daily_frame_sorts_by_ticker(monkeypatch):
    module = import_eod_module(monkeypatch)
    module.client = types.SimpleNamespace(project="test-project")
    monkeypatch.setattr(
        module,
        "_query_rows",
        lambda *args, **kwargs: [
            {"ticker": "VALE3", "data_pregao": dt.date(2026, 1, 10)},
            {"ticker": "PETR4", "data_pregao": dt.date(2026, 1, 10)},
        ],
    )

    df = module._fetch_daily_frame(dt.date(2026, 1, 10))

    assert df["ticker"].tolist() == ["PETR4", "VALE3"]
