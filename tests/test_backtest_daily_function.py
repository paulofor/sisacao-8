from __future__ import annotations

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


class DummyArrayQueryParameter(DummyScalarQueryParameter):
    pass


class DummyLoadJobConfig:
    def __init__(self, write_disposition=None):
        self.write_disposition = write_disposition


class DummyWriteDisposition:
    WRITE_APPEND = "WRITE_APPEND"


class DummyClient:
    project = "test-project"


def import_backtest_daily_module(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")
    fake_bigquery.Client = lambda *args, **kwargs: DummyClient()
    fake_bigquery.QueryJobConfig = DummyQueryJobConfig
    fake_bigquery.ScalarQueryParameter = DummyScalarQueryParameter
    fake_bigquery.ArrayQueryParameter = DummyArrayQueryParameter
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
    function_dir = os.path.join(root, "functions", "backtest_daily")
    for path in (root, function_dir):
        if path not in sys.path:
            sys.path.insert(0, path)

    module_name = "functions.backtest_daily.main"
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_parse_request_dates_supports_limited_trading_day_range(monkeypatch):
    module = import_backtest_daily_module(monkeypatch)
    monkeypatch.setattr(
        module,
        "_is_trading_day",
        lambda value: value.weekday() < 5,
    )
    request = types.SimpleNamespace(
        args={"date_from": "2026-04-20", "date_to": "2026-04-24", "limit": "3"}
    )

    dates = module._parse_request_dates(request)

    assert dates == [
        dt.date(2026, 4, 20),
        dt.date(2026, 4, 21),
        dt.date(2026, 4, 22),
    ]


def test_backtest_daily_processes_multiple_dates_in_one_invocation(monkeypatch):
    module = import_backtest_daily_module(monkeypatch)
    processed_dates: list[dt.date] = []
    reference_dates = [dt.date(2026, 4, 20), dt.date(2026, 4, 22)]

    monkeypatch.setattr(module, "_parse_request_dates", lambda request: reference_dates)
    monkeypatch.setattr(
        module, "_table_ref", lambda table_id: f"project.dataset.{table_id}"
    )

    def fake_run_backtest_for_date(reference_date, run_logger):
        processed_dates.append(reference_date)
        return {
            "status": "ok",
            "date_ref": reference_date.isoformat(),
            "processed_signals": 5,
            "trades": 5,
            "metrics": 2,
        }

    monkeypatch.setattr(module, "_run_backtest_for_date", fake_run_backtest_for_date)

    result = module.backtest_daily(types.SimpleNamespace(args={}))

    assert processed_dates == reference_dates
    assert result["processed_dates"] == 2
    assert result["ok_dates"] == 2
    assert result["processed_signals"] == 10
    assert result["trades"] == 10
    assert result["metrics"] == 4
