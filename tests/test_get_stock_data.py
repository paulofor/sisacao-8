import datetime
import importlib
import os
import sys
import types


def import_get_stock_module(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")
    fake_bigquery.Client = lambda *a, **k: None

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
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)
    module_name = "functions.get_stock_data.main"
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_get_stock_data_success(monkeypatch):
    module = import_get_stock_module(monkeypatch)

    monkeypatch.setattr(
        module,
        "download_from_b3",
        lambda tickers: {"YDUQ3": ("2025-01-01", 10.0)},
    )
    monkeypatch.setattr(
        module,
        "load_configured_tickers",
        lambda path=None: ["YDUQ3"],
    )
    monkeypatch.setattr(
        module,
        "append_dataframe_to_bigquery",
        lambda df: None,
    )
    response = module.get_stock_data(None)
    assert response == "Success"


def test_load_tickers_from_file(monkeypatch, tmp_path):
    module = import_get_stock_module(monkeypatch)
    tickers_file = tmp_path / "tickers.txt"
    tickers_file.write_text(
        "# teste\nYDUQ3\n petr4 \nYDUQ3\n",
        encoding="utf-8",
    )
    tickers = module.load_tickers_from_file(tickers_file)
    assert tickers == ["YDUQ3", "PETR4"]


def test_load_configured_tickers_uses_google(monkeypatch):
    module = import_get_stock_module(monkeypatch)
    monkeypatch.setattr(module, "_env_tickers_path", None, raising=False)
    monkeypatch.setattr(module, "load_tickers_from_file", lambda path=None: [])
    calls = {}

    def fake_import(path):  # noqa: D401
        calls["imported"] = path

        class DummyModule:
            @staticmethod
            def fetch_active_tickers():  # noqa: D401
                calls["fetched"] = True
                return [" yduq3 ", "PETR4", "YDUQ3"]

        return DummyModule()

    monkeypatch.setattr(module, "import_module", fake_import)
    tickers = module.load_configured_tickers()
    assert calls.get("imported") == module.GOOGLE_FINANCE_MODULE
    assert calls.get("fetched") is True
    assert tickers == ["YDUQ3", "PETR4"]


def test_load_configured_tickers_fallbacks_to_file(monkeypatch):
    module = import_get_stock_module(monkeypatch)
    monkeypatch.setattr(module, "_env_tickers_path", None, raising=False)

    def fail_google():  # noqa: D401
        raise RuntimeError("boom")

    monkeypatch.setattr(
        module,
        "load_tickers_from_google_finance",
        fail_google,
    )
    monkeypatch.setattr(
        module,
        "load_tickers_from_file",
        lambda path=None: ["YDUQ3"],
    )
    tickers = module.load_configured_tickers()
    assert tickers == ["YDUQ3"]


def test_append_dataframe_to_bigquery_without_pandas(monkeypatch):
    module = import_get_stock_module(monkeypatch)
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
            "ticker": "YDUQ3",
            "data_pregao": datetime.date(2024, 1, 3),
            "preco_fechamento": 12.34,
            "data_captura": datetime.datetime(2024, 1, 3, 15, 45),
            "fonte": module.FONTE_FECHAMENTO,
        }
    ]

    module.append_dataframe_to_bigquery(rows)

    assert captured["table_id"].endswith(
        f"{module.DATASET_ID}.{module.FECHAMENTO_TABLE_ID}"
    )
    assert captured["rows"][0]["data_pregao"] == "2024-01-03"
    assert captured["rows"][0]["data_captura"].startswith("2024-01-03T15:45:00")
