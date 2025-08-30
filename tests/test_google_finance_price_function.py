from __future__ import annotations

import importlib
import sys
import types
from types import SimpleNamespace

import pytest


class DummyRequest(SimpleNamespace):
    """Minimal request object with an ``args`` attribute."""


def test_google_finance_price_success(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")
    fake_bigquery.Client = lambda *a, **k: None
    fake_cloud = types.ModuleType("cloud")
    fake_cloud.bigquery = fake_bigquery
    fake_google = types.ModuleType("google")
    fake_google.cloud = fake_cloud
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.cloud", fake_cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)
    module = importlib.import_module("functions.google_finance_price.main")

    def mock_fetch(ticker: str, exchange: str = "BVMF", session=None) -> float:
        assert ticker == "YDUQ3"
        return 11.11

    monkeypatch.setattr(module, "fetch_google_finance_price", mock_fetch)

    captured = {}

    def mock_append(df):
        captured["df"] = df

    monkeypatch.setattr(module, "append_dataframe_to_bigquery", mock_append)

    request = DummyRequest(args={"ticker": "YDUQ3"})
    body, status = module.google_finance_price(request)
    assert status == 200
    assert body["ticker"] == "YDUQ3"
    assert body["price"] == pytest.approx(11.11)
    df = captured["df"]
    assert list(df.columns) == [
        "ticker",
        "data",
        "hora",
        "valor",
        "hora_atual",
        "data_hora_atual",
    ]
    assert df.iloc[0]["ticker"] == "YDUQ3"
    assert df.iloc[0]["valor"] == pytest.approx(11.11)


def test_google_finance_price_failure(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")
    fake_bigquery.Client = lambda *a, **k: None
    fake_cloud = types.ModuleType("cloud")
    fake_cloud.bigquery = fake_bigquery
    fake_google = types.ModuleType("google")
    fake_google.cloud = fake_cloud
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.cloud", fake_cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)
    module = importlib.import_module("functions.google_finance_price.main")

    def mock_fetch(ticker: str, exchange: str = "BVMF", session=None) -> float:
        raise ValueError("boom")

    monkeypatch.setattr(module, "fetch_google_finance_price", mock_fetch)

    request = DummyRequest(args={"ticker": "XYZ"})
    body, status = module.google_finance_price(request)
    assert status == 500
    assert "error" in body
