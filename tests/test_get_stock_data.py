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
        WRITE_TRUNCATE = "WRITE_TRUNCATE"

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
        lambda tickers, date=None, diagnostics=None, **kwargs: {"YDUQ3": candle},
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
    expected_reference = datetime.datetime.now(module.SAO_PAULO_TZ).date()
    assert captured["date"] == expected_reference


def test_load_tickers_from_file(monkeypatch, tmp_path):
    module = import_get_stock_module(monkeypatch)
    tickers_file = tmp_path / "tickers.txt"
    tickers_file.write_text(
        "# teste\nYDUQ3\n petr4 \nYDUQ3\n",
        encoding="utf-8",
    )
    tickers = module.load_tickers_from_file(tickers_file)
    assert tickers == ["YDUQ3", "PETR4"]


def test_load_configured_tickers_uses_bigquery_first(monkeypatch):
    module = import_get_stock_module(monkeypatch)
    monkeypatch.setattr(module, "_env_tickers_path", None, raising=False)
    monkeypatch.setattr(module, "load_tickers_from_file", lambda path=None: [])
    monkeypatch.setattr(module, "load_tickers_from_google_finance", lambda: ["FAIL"])
    monkeypatch.setattr(module, "load_tickers_from_bigquery", lambda: ["YDUQ3", "PETR4"])

    tickers = module.load_configured_tickers()

    assert tickers == ["YDUQ3", "PETR4"]


def test_load_configured_tickers_uses_google_when_bigquery_fails(monkeypatch):
    module = import_get_stock_module(monkeypatch)
    monkeypatch.setattr(module, "_env_tickers_path", None, raising=False)
    monkeypatch.setattr(module, "load_tickers_from_file", lambda path=None: [])

    def fail_bq():
        raise RuntimeError("bq indisponivel")

    monkeypatch.setattr(module, "load_tickers_from_bigquery", fail_bq)

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
            "data_pregao": datetime.date(2024, 1, 3),
            "open": 10.0,
            "high": 11.0,
            "low": 9.5,
            "close": 10.5,
            "volume_financeiro": 12345.0,
            "qtd_negociada": 1000.0,
            "num_negocios": 200,
            "fonte": module.FONTE_FECHAMENTO,
            "atualizado_em": datetime.datetime(2024, 1, 3, 18, 0),
        }
    ]

    module.append_dataframe_to_bigquery(rows, datetime.date(2024, 1, 3))

    expected_suffix = f"{module.DATASET_ID}.{module.FECHAMENTO_TABLE_ID}"
    if module.LOAD_STRATEGY.strip().upper() == "MERGE":
        expected_suffix += "_staging"
    assert captured["table_id"].endswith(expected_suffix)
    normalized = captured["rows"][0]
    assert normalized["data_pregao"] == "2024-01-03"
    assert normalized["atualizado_em"].startswith("2024-01-03")


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


def test_append_dataframe_to_bigquery_merge_strategy(monkeypatch):
    module = import_get_stock_module(monkeypatch)
    monkeypatch.setattr(module, "pd", None, raising=False)
    monkeypatch.setattr(module, "LOAD_STRATEGY", "MERGE", raising=False)

    captured = {"queries": []}

    class FakeJob:
        def result(self):  # noqa: D401
            return None

    class FakeWriteDisposition:
        WRITE_APPEND = "WRITE_APPEND"
        WRITE_TRUNCATE = "WRITE_TRUNCATE"

    monkeypatch.setattr(module.bigquery, "WriteDisposition", FakeWriteDisposition)

    class FakeClient:
        project = "test-project"

        def query(self, query, job_config=None):  # noqa: D401, ANN001
            captured["queries"].append(query)
            return FakeJob()

        def load_table_from_json(self, rows, table_id, job_config):  # noqa: D401
            captured["table_id"] = table_id
            captured["write_disposition"] = job_config.write_disposition
            return FakeJob()

    monkeypatch.setattr(module, "client", FakeClient(), raising=False)

    rows = [
        {
            "ticker": "YDUQ3",
            "data_pregao": datetime.date(2024, 1, 3),
            "open": 10.0,
            "high": 11.0,
            "low": 9.5,
            "close": 10.5,
            "volume_financeiro": 12345.0,
            "qtd_negociada": 1000.0,
            "num_negocios": 200,
            "fonte": module.FONTE_FECHAMENTO,
            "atualizado_em": datetime.datetime(2024, 1, 3, 18, 0),
        }
    ]

    module.append_dataframe_to_bigquery(rows, datetime.date(2024, 1, 3))

    assert captured["table_id"].endswith("cotacao_ohlcv_diario_staging")
    assert captured["write_disposition"] == "WRITE_TRUNCATE"
    assert any("MERGE `" in query for query in captured["queries"])


def test_load_tickers_from_bigquery(monkeypatch):
    module = import_get_stock_module(monkeypatch)

    class FakeQueryJob:
        def result(self):  # noqa: D401
            return [
                {"ticker": " yduq3 "},
                {"ticker": "PETR4"},
                {"ticker": "YDUQ3"},
            ]

    class FakeClient:
        project = "test-project"

        def query(self, *args, **kwargs):  # noqa: D401
            return FakeQueryJob()

    monkeypatch.setattr(module, "pd", None, raising=False)
    monkeypatch.setattr(module, "client", FakeClient(), raising=False)

    tickers = module.load_tickers_from_bigquery()

    assert tickers == ["YDUQ3", "PETR4"]


def test_daily_table_id_prefers_bq_table_env(monkeypatch):
    module = import_get_stock_module(monkeypatch)
    monkeypatch.setattr(
        module,
        "FULLY_QUALIFIED_BQ_TABLE",
        "ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario",
        raising=False,
    )

    table_id = module._daily_table_id()

    assert table_id == "ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario"
