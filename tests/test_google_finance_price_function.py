from __future__ import annotations

import datetime
import importlib
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pandas as pd  # type: ignore[import-untyped]
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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
    response = module.google_finance_price(request)
    assert response.status_code == 200
    body = json.loads(response.get_data(as_text=True))
    assert body["tickers"] == ["YDUQ3", "PETR4"]
    assert body["processed"] == 2
    expected_table_id = f"{FakeClient.project}.{module.DATASET_ID}.acao_bovespa"
    expected_query = (
        "SELECT ticker FROM " f"`{expected_table_id}` " "WHERE ativo = TRUE"
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
    assert all(
        getattr(value, "tzinfo", None) is None for value in df["data_hora_atual"]
    )


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
    response = module.google_finance_price(request)
    assert response.status_code == 500
    body = json.loads(response.get_data(as_text=True))
    assert "error" in body
    assert "called" not in captured


def test_google_finance_price_uses_fallback_when_bigquery_unavailable(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")

    class FakeClient:
        project = "test-project"

        def query(self, query):  # noqa: D401, ANN001
            raise RuntimeError("unavailable")

    fake_bigquery.Client = lambda *a, **k: FakeClient()
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

    monkeypatch.setenv("FALLBACK_TICKERS", "PETR4,VALE3")
    monkeypatch.delenv("MAX_INTRADAY_TICKERS", raising=False)

    def mock_fetch(ticker: str, exchange: str = "BVMF", session=None) -> float:
        return {"PETR4": 10.0, "VALE3": 21.5}[ticker]

    monkeypatch.setattr(module, "fetch_google_finance_price", mock_fetch)

    captured = {}

    def mock_append(df):
        captured["tickers"] = list(df["ticker"])
        captured["valor"] = list(df["valor"])

    monkeypatch.setattr(module, "append_dataframe_to_bigquery", mock_append)

    request = DummyRequest(args={})
    response = module.google_finance_price(request)
    assert response.status_code == 200
    body = json.loads(response.get_data(as_text=True))
    assert body["tickers"] == ["PETR4", "VALE3"]
    assert body["processed"] == 2
    assert captured["tickers"] == ["PETR4", "VALE3"]
    assert captured["valor"][0] == pytest.approx(10.0)
    assert captured["valor"][1] == pytest.approx(21.5)


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

        def load_table_from_json(self, rows, table_id, job_config):  # noqa: D401
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
            "data_hora_atual": datetime.datetime(
                2024,
                1,
                2,
                12,
                34,
                tzinfo=datetime.timezone(datetime.timedelta(hours=-3)),
            ),
        }
    ]

    module.append_dataframe_to_bigquery(rows)

    assert captured["table_id"].endswith(f"{module.DATASET_ID}.{module.TABELA_ID}")
    assert captured["rows"][0]["data"] == "2024-01-02"
    assert captured["rows"][0]["hora"] == "12:34:00"
    row = captured["rows"][0]
    assert row["hora_atual"] == "12:34:00"
    assert row["data_hora_atual"] == "2024-01-02T12:34:00"


def test_append_dataframe_to_bigquery_drops_timezone(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")

    class DummyJob:
        def result(self):  # noqa: D401
            return None

    class DummyJobConfig:
        def __init__(self, schema=None, write_disposition=None):  # noqa: D401, ANN001
            self.schema = schema
            self.write_disposition = write_disposition

    class DummySchemaField:
        def __init__(self, name, field_type):  # noqa: D401, ANN001
            self.name = name
            self.field_type = field_type

    class DummyWriteDisposition:
        WRITE_APPEND = "WRITE_APPEND"

    captured = {}

    class FakeClient:
        project = "test-project"

        def load_table_from_dataframe(self, df, table_id, job_config):  # noqa: D401
            captured["tzinfo"] = getattr(
                df["data_hora_atual"].iloc[0], "tzinfo", "missing"
            )
            captured["table_id"] = table_id
            captured["schema"] = job_config.schema
            return DummyJob()

    fake_bigquery.Client = lambda *a, **k: FakeClient()
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

    df = pd.DataFrame(
        [
            {
                "ticker": "PETR4",
                "data": "2024-02-01",
                "hora": "12:34",
                "valor": 1.23,
                "hora_atual": "12:34",
                "data_hora_atual": datetime.datetime(
                    2024, 2, 1, 12, 34, tzinfo=datetime.timezone.utc
                ),
            }
        ]
    )

    module.append_dataframe_to_bigquery(df)

    assert captured["table_id"].endswith(f"{module.DATASET_ID}.{module.TABELA_ID}")
    assert captured["tzinfo"] is None


def test_google_finance_price_persists_partial_rows_before_timeout(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")

    class FakeClient:
        project = "test-project"

        def query(self, query):  # noqa: D401, ANN001
            return SimpleNamespace(
                to_dataframe=lambda: pd.DataFrame(
                    {"ticker": ["FAST1", "FAST2", "SLOW1"]}
                )
            )

    fake_bigquery.Client = lambda *a, **k: FakeClient()
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

    monkeypatch.setenv("GOOGLE_FINANCE_MAX_WORKERS", "3")
    monkeypatch.setenv("GOOGLE_FINANCE_BATCH_SIZE", "1")
    monkeypatch.setattr(module, "_function_deadline_seconds", lambda: 0.2)

    def mock_fetch(ticker: str, exchange: str = "BVMF", session=None) -> float:
        if ticker == "SLOW1":
            import time

            time.sleep(0.5)
        return {"FAST1": 10.0, "FAST2": 20.0, "SLOW1": 30.0}[ticker]

    monkeypatch.setattr(module, "fetch_google_finance_price", mock_fetch)

    batches = []

    def mock_append(df):
        batches.append(list(df["ticker"]))

    monkeypatch.setattr(module, "append_dataframe_to_bigquery", mock_append)

    response = module.google_finance_price(DummyRequest(args={}))

    assert response.status_code == 207
    body = json.loads(response.get_data(as_text=True))
    assert body["processed"] == 2
    assert {item for batch in batches for item in batch} == {"FAST1", "FAST2"}
    assert any(error.get("type") == "Timeout" for error in body["errors"])


def test_google_finance_price_skips_on_holiday(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")

    class FakeClient:
        project = "test-project"

    fake_bigquery.Client = lambda *a, **k: FakeClient()
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

    monkeypatch.setattr(module, "is_b3_holiday", lambda date: True)
    monkeypatch.setattr(module, "fetch_active_tickers", lambda: ["PETR4"])

    response = module.google_finance_price(DummyRequest(args={}))

    assert response.status_code == 200
    body = json.loads(response.get_data(as_text=True))
    assert body["processed"] == 0
    assert "feriado" in body["message"].lower()


def test_is_b3_holiday_returns_true_when_query_has_rows(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")

    class FakeClient:
        project = "test-project"

        def query(self, query):  # noqa: D401, ANN001
            self.last_query = query
            return SimpleNamespace(
                to_dataframe=lambda: pd.DataFrame({"data_feriado": ["2026-01-01"]})
            )

    fake_bigquery.Client = lambda *a, **k: FakeClient()
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

    result = module.is_b3_holiday(datetime.date(2026, 1, 1))

    assert result is True
    assert module.FERIADOS_TABLE_ID in module.client.last_query
