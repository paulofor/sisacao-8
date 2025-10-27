from __future__ import annotations

import datetime
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


def test_append_dataframe_without_pandas(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")

    class ImportClient:
        project = "import"

        def __init__(
            self,
            *args,
            **kwargs,
        ):  # noqa: D401, ANN001
            return None

        def load_table_from_dataframe(
            self,
            *args,
            **kwargs,
        ):  # noqa: D401, ANN001
            return SimpleNamespace(result=lambda: None)

    class DummyJobConfig:
        def __init__(
            self,
            schema=None,
            write_disposition=None,
        ):  # noqa: D401, ANN001
            self.schema = schema
            self.write_disposition = write_disposition

    class DummySchemaField:
        def __init__(
            self,
            name,
            field_type,
        ):  # noqa: D401, ANN001
            self.name = name
            self.field_type = field_type

    class DummyWriteDisposition:
        WRITE_APPEND = "WRITE_APPEND"

    fake_bigquery.Client = lambda *a, **k: ImportClient()
    fake_bigquery.LoadJobConfig = DummyJobConfig
    fake_bigquery.SchemaField = DummySchemaField
    fake_bigquery.WriteDisposition = DummyWriteDisposition
    fake_cloud = types.ModuleType("cloud")
    fake_cloud.bigquery = fake_bigquery
    fake_google = types.ModuleType("google")
    fake_google.cloud = fake_cloud
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.cloud", fake_cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)

    module = importlib.reload(
        importlib.import_module("functions.google_finance_price.main")
    )

    monkeypatch.setattr(module, "pd", None, raising=False)

    captured = {}

    class FakeJob:
        def result(self):  # noqa: D401
            return None

    class FakeClient:
        project = "test-project"

        def load_table_from_json(  # noqa: D401
            self, rows, table_id, job_config
        ):
            captured["rows"] = rows
            captured["table_id"] = table_id
            captured["schema"] = job_config.schema
            return FakeJob()

    monkeypatch.setattr(module, "client", FakeClient(), raising=False)

    rows = [
        {
            "ticker": "PETR4",
            "data": datetime.date(2024, 1, 2),
            "hora": "12:34",
            "valor": 10.5,
            "hora_atual": datetime.time(12, 34),
            "data_hora_atual": datetime.datetime(2024, 1, 2, 12, 34),
        }
    ]

    module.append_dataframe_to_bigquery(rows)

    assert captured["table_id"].endswith(
        f"{module.DATASET_ID}.{module.TABELA_ID}"
    )
    assert captured["rows"][0]["data"] == "2024-01-02"
    assert captured["rows"][0]["hora"] == "12:34:00"
    row = captured["rows"][0]
    assert row["hora_atual"] == "12:34:00"
    assert row["data_hora_atual"].startswith("2024-01-02T12:34:00")
