import datetime
import importlib
import os
import sys
import types


def import_get_stock_module(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")
    fake_bigquery.Client = lambda *a, **k: None

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
            mode=None,
        ):  # noqa: D401, ANN001
            self.name = name
            self.field_type = field_type
            self.mode = mode

    class DummyWriteDisposition:
        WRITE_APPEND = "WRITE_APPEND"

    fake_bigquery.LoadJobConfig = DummyJobConfig
    fake_bigquery.SchemaField = DummySchemaField
    fake_bigquery.WriteDisposition = DummyWriteDisposition

    class DummyQueryJobConfig:
        def __init__(self, query_parameters=None):  # noqa: D401, ANN001
            self.query_parameters = query_parameters or []

    class DummyScalarQueryParameter:
        def __init__(self, name, param_type, value):  # noqa: D401, ANN001
            self.name = name
            self.param_type = param_type
            self.value = value

    fake_bigquery.QueryJobConfig = DummyQueryJobConfig
    fake_bigquery.ScalarQueryParameter = DummyScalarQueryParameter
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


def make_candle(module, ticker="YDUQ3", date="2025-01-01", price=10.0):
    timestamp = datetime.datetime.strptime(date, "%Y-%m-%d").replace(
        tzinfo=module.SAO_PAULO_TZ
    )
    return module.Candle(
        ticker=ticker,
        timestamp=timestamp,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=1.0,
        source=module.FONTE_FECHAMENTO,
        timeframe=module.Timeframe.DAILY,
        ingested_at=timestamp,
    )


def test_get_stock_data_success(monkeypatch):
    module = import_get_stock_module(monkeypatch)

    candle = make_candle(module)
    monkeypatch.setattr(
        module,
        "download_from_b3",
        lambda tickers, date=None, diagnostics=None: {"YDUQ3": candle},
    )
    monkeypatch.setattr(
        module,
        "load_configured_tickers",
        lambda path=None: ["YDUQ3"],
    )
    captured = {}

    def fake_append(data, reference_date):
        captured["rows"] = data
        captured["date"] = reference_date

    monkeypatch.setattr(module, "append_dataframe_to_bigquery", fake_append)
    response = module.get_stock_data(None)
    assert response == "Success"
    assert captured["date"] == datetime.date.today()


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


def test_load_tickers_from_google_finance_uses_fallback_module(monkeypatch):
    module = import_get_stock_module(monkeypatch)

    def fake_import(path):  # noqa: D401
        if path == module.GOOGLE_FINANCE_MODULE:
            raise ModuleNotFoundError("functions")

        class DummyModule:
            @staticmethod
            def fetch_active_tickers():  # noqa: D401
                return ["PETR4", " VALE3 "]

        return DummyModule()

    monkeypatch.setattr(module, "import_module", fake_import)

    tickers = module.load_tickers_from_google_finance()

    assert tickers == ["PETR4", "VALE3"]


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

        def query(self, *args, **kwargs):  # noqa: D401
            return FakeJob()

        def load_table_from_json(self, rows, table_id, job_config):  # noqa: D401
            captured["rows"] = rows
            captured["table_id"] = table_id
            captured["schema"] = job_config.schema
            return FakeJob()

    monkeypatch.setattr(module, "client", FakeClient(), raising=False)

    rows = [
        {
            "ticker": "YDUQ3",
            "candle_datetime": datetime.datetime(2024, 1, 3, 0, 0),
            "reference_date": datetime.date(2024, 1, 3),
            "open": 10.0,
            "high": 11.0,
            "low": 9.5,
            "close": 10.5,
            "volume": 1000.0,
            "source": module.FONTE_FECHAMENTO,
            "timeframe": "1D",
            "ingested_at": datetime.datetime(2024, 1, 3, 18, 0),
        }
    ]

    module.append_dataframe_to_bigquery(rows, datetime.date(2024, 1, 3))

    assert captured["table_id"].endswith(
        f"{module.DATASET_ID}.{module.FECHAMENTO_TABLE_ID}"
    )
    normalized = captured["rows"][0]
    assert normalized["reference_date"] == "2024-01-03"
    assert normalized["candle_datetime"].startswith("2024-01-03")


def test_get_stock_data_skips_on_holiday(monkeypatch):
    module = import_get_stock_module(monkeypatch)

    monkeypatch.setattr(module, "is_b3_holiday", lambda date: True)

    response = module.get_stock_data(None)

    assert response == "Skipped holiday"


def test_is_b3_holiday_true_when_row_exists(monkeypatch):
    module = import_get_stock_module(monkeypatch)
    monkeypatch.setattr(module, "pd", None, raising=False)

    class FakeClient:
        project = "test-project"

        def query(self, query):  # noqa: D401, ANN001
            self.query_text = query
            return types.SimpleNamespace(
                result=lambda: [{"data_feriado": "2026-01-01"}]
            )

    fake_client = FakeClient()
    monkeypatch.setattr(module, "client", fake_client, raising=False)

    result = module.is_b3_holiday(datetime.date(2026, 1, 1))

    assert result is True
    assert module.FERIADOS_TABLE_ID in fake_client.query_text
