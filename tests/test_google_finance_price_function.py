from __future__ import annotations

import importlib
import sys
import types
from types import SimpleNamespace

import pandas as pd  # type: ignore[import-untyped]
import pytest


class DummyRequest(SimpleNamespace):
    """Minimal request object with an ``args`` attribute."""


def test_google_finance_price_success(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")

    class FakeClient:
        project = "test-project"

        def query(self, query):  # noqa: D401, ANN001
            FakeClient.last_query = query
            data = pd.DataFrame({"ticker": ["YDUQ3", "PETR4"]})
            return SimpleNamespace(to_dataframe=lambda: data)

    fake_bigquery.Client = lambda *a, **k: FakeClient()
    fake_cloud = types.ModuleType("cloud")
    fake_cloud.bigquery = fake_bigquery
    fake_google = types.ModuleType("google")
    fake_google.cloud = fake_cloud
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.cloud", fake_cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)
    module = importlib.import_module("functions.google_finance_price.main")

    prices = {"YDUQ3": 11.11, "PETR4": 22.22}

    def mock_fetch(ticker: str, exchange: str = "BVMF", session=None) -> float:
        return prices[ticker]

    monkeypatch.setattr(module, "fetch_google_finance_price", mock_fetch)

    captured = {}

    def mock_append(df):
        captured["df"] = df

    monkeypatch.setattr(module, "append_dataframe_to_bigquery", mock_append)

    request = DummyRequest(args={})
    body, status = module.google_finance_price(request)
    assert status == 200
    assert body["tickers"] == ["YDUQ3", "PETR4"]
    assert body["processed"] == 2
    expected_table_id = (
        f"{FakeClient.project}.{module.DATASET_ID}.acao_bovespa"  # noqa: E501
    )
    expected_query = (
        f"SELECT ticker FROM `{expected_table_id}` WHERE ativo = TRUE"  # noqa: E501
    )
    assert FakeClient.last_query == expected_query
    df = captured["df"]
    assert list(df.columns) == [
        "ticker",
        "data",
        "hora",
        "valor",
        "hora_atual",
        "data_hora_atual",
    ]
    assert list(df["ticker"]) == ["YDUQ3", "PETR4"]
    assert list(df["valor"]) == [pytest.approx(11.11), pytest.approx(22.22)]


def test_google_finance_price_failure(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")

    class FakeClient:
        project = "test-project"

        def query(self, query):  # noqa: D401, ANN001
            FakeClient.last_query = query
            return SimpleNamespace(
                to_dataframe=lambda: pd.DataFrame({"ticker": ["XYZ"]})
            )

    fake_bigquery.Client = lambda *a, **k: FakeClient()
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

    captured = {}

    def mock_append(df):  # noqa: ARG001
        captured["called"] = True

    monkeypatch.setattr(module, "append_dataframe_to_bigquery", mock_append)

    request = DummyRequest(args={})
    body, status = module.google_finance_price(request)
    assert status == 500
    assert "error" in body
    assert "called" not in captured
