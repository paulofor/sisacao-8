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


def test_persist_signals_serializes_dates_before_bigquery_load(monkeypatch):
    module = import_eod_module(monkeypatch)
    module.client = types.SimpleNamespace(project="test-project")

    loaded = {}

    class FakeLoadJob:
        def result(self):
            return None

    class FakeClient:
        def __init__(self):
            self.project = "test-project"

        def load_table_from_json(self, rows, table_id, job_config=None):
            loaded["rows"] = rows
            loaded["table_id"] = table_id
            loaded["job_config"] = job_config
            return FakeLoadJob()

    module.client = FakeClient()

    signal = module.ConditionalSignal(
        ticker="PETR4",
        side="BUY",
        entry=10.0,
        target=10.7,
        stop=9.3,
        rank=1,
        x_rule="close(D)*0.98",
        y_target_pct=0.07,
        y_stop_pct=0.07,
        volume=1_000_000.0,
        close=10.2,
        score=0.8,
        ranking_key="score_v1",
        horizon_days=10,
    )

    module._persist_signals(
        "test-project.dataset.sinais_eod",
        [signal],
        dt.date(2026, 1, 10),
        dt.date(2026, 1, 13),
        dt.datetime(2026, 1, 10, 18, 30, 0),
        "snapshot",
        "local",
        run_id="run-1",
        config_version="config-v1",
    )

    assert loaded["table_id"] == "test-project.dataset.sinais_eod"
    loaded_row = loaded["rows"][0]
    assert loaded_row["date_ref"] == "2026-01-10"
    assert loaded_row["valid_for"] == "2026-01-13"
    assert loaded_row["created_at"] == "2026-01-10 18:30:00"
    assert loaded_row["job_run_id"] == "run-1"
    assert loaded_row["config_version"] == "config-v1"
